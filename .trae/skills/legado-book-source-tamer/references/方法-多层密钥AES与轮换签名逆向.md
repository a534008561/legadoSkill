# 方法：多层密钥 / AES 信封 / 轮换签名 逆向手册
## ——把"看不懂的前端加密"拆成可复现的规则，并在密钥每天换的情况下活下去

> 沉淀日期：2026-09-14　｜　来源：s.wendulou.com（双层体系）、jjwxc.net（DES + 响应头派生）、rrssk/lwenxsw/qmzw5（AESCrypt + 每日签名）、aaawz（LZString）、ppxsw/ymxwx（随机对象名 base64）
> 关联：[方法-加密解密](方法-加密解密.md)、[方法-晋江书源高级技术拆解](方法-晋江书源高级技术拆解.md)、[方法-APP接口聚合书源拆解](方法-APP接口聚合书源拆解.md)、[方法-静默失败定位与探针法](方法-静默失败定位与探针法.md)

---

## 目录

1. [第一步永远是"分型"](#一第一步永远是分型)
2. [密钥定位四法](#二密钥定位四法)
3. [体系 A：动态种子信封（wendulou）](#三体系-a动态种子信封wendulou)
4. [★IV 构造铁律与"首块乱码"定位法](#四iv-构造铁律与首块乱码定位法)
5. [体系 B：固定密钥 + 文件名随机化](#五体系-b固定密钥--文件名随机化)
6. [体系 C：固定 DES + 响应头派生第二层密钥（晋江）](#六体系-c固定-des--响应头派生第二层密钥晋江)
7. [每日轮换签名的兼容提取：花括号配平法](#七每日轮换签名的兼容提取花括号配平法)
8. [base64/字符串解密的"随机对象名"通用套路](#八base64字符串解密的随机对象名通用套路)
9. [★破坏性单变量实验：找出真正被校验的那一项](#九破坏性单变量实验找出真正被校验的那一项)
10. [Legado 侧解密 API 速查](#十legado-侧解密-api-速查)
11. [避坑清单](#十一避坑清单)

---

## 一、第一步永远是"分型"

密文长相决定路线，别一上来就读 JS：

| 密文特征 | 大概率是 | 入口 |
|---|---|---|
| `A-Za-z0-9+/=`，长度 4 的倍数 | **base64**（可能只是编码，不是加密） | `java.base64Decode` |
| 以 `~` / 大量 `_$()` 特殊符号开头 | **LZString**（`compressToEncodedURIComponent`） | 规则里无原生 API → 需 JS 解压或找明文旁路 |
| 长度 16 倍数、含 `+/-`、服务端下发 | **AES/CBC** | `java.aesBase64DecodeToString` 等 |
| 长度 8 倍数、有 `accesskey/keystring` 响应头 | **DES/CBC + 头派生**（晋江式） | 见第六节 |
| 只是汉字读不通 | **字体置换**，不是加密 | 见[字体反爬篇](方法-字体反爬三代方案演进.md) |
| JSON 里字段名是 `content`/`data` 且整段一长串 | 信封（key/iv 常藏在**同一响应**里） | 见第三、五节 |

---

## 二、密钥定位四法

1. **JS 文件枚举**：抓页面所有 `<script src>`，逐个搜特征串
   `AESCrypt` / `CryptoJS` / `_keyStr` / `atob` / `decrypt` / `iv` / `mode:`。
   特征串（`var (\w+)=\{_keyStr`）比"已知对象名"稳，因为**对象名每本书随机变化**（ppxsw 的 `rgr.owes` / `vypflhij.atyffy`）。
2. **文件名随机化 → 强制回源**：qmzw5 的密钥 JS 文件名是随机 32 位（`/templates/js/{随机32}.js`）。CDN 会缓存旧文件 → 详情页请求 URL 加 `?_=` + `Date.now()` 强制回源，否则拿到过期密钥。
3. **响应头/响应体旁路**：晋江把第二层密钥材料放在 **HTTP 响应头** `accesskey` / `keystring`（`headers:` 规则取头、`<js>:getCookie()` 取 Cookie，顺序不能颠倒）。
4. **同响应信封自解**：wendulou 的 key/iv 种子**就在密文里**（见第三节），不需要抠 JS——这类站点最省事，但最容易看走眼。

---

## 三、体系 A：动态种子信封（wendulou）

```
响应 content（base64）
  └─ java.base64Decode(content) 得到字节流：
       [ 16B key 种子(ASCII) ][ AES-256-CBC 密文体 ][ 16B IV 种子 ]
                                                ↑ 前后各 16 字节，中间是密文

key = SHA256( keySeed 的 hex 字符串 )  → 32 字节
IV  = md5( ivSeed ).hexdigest()        → 32 个 hex 字符
      取其 getBytes() 的【前 16 个 ASCII 字符】
      再逐位 ⊕ 种子 ⊕ 0xFF
```

**两条最容易写错的地方**：

- `java.md5Encode(s)` 返回的是 **hex 字符串**，不是 raw digest！Python 侧习惯 `hashlib.md5(x).digest()`，两边直接对不上。
- key 用的是"种子的 **hex 字符串**"再做 SHA256，不是原始 16 字节。少一步 hex，全表错。

**Python 复现注意**：`base64` 缺 `=` 填充时 hutool 宽容、Python 严格 → **必须手工补齐**：

```python
s += '=' * (-len(s) % 4)
```

---

## 四、★IV 构造铁律与"首块乱码"定位法

CBC 模式下错误的影响面是**确定性**的，这条规律能省掉大量试错：

```
密钥错   → 全部明文乱码
IV 错    → 只有【第一个 16 字节块】乱码，其余全对
填充/截断错 → 末尾乱码 或 BadPaddingException
```

**wendulou 实测**：Python 用 raw digest 当 IV → **仅首块 16 字节乱、其余正常** ⇒ 立刻定位到"IV 构造方式不对"，而不是去怀疑密钥。

> 拿到"首块乱其余好"就去做这一件事：核对 IV 是不是被当成 hex 字符串的 ASCII 字节、是否需要 ⊕/截断。

---

## 五、体系 B：固定密钥 + 文件名随机化

rrssk 家族（lwenxsw / 7shuw 等）：

```
密钥位置：详情页引用的 /templates/js/{随机32位}.js
内含：    class AESCrypt { key: '...', iv: '6051140156343299', mode: CBC }
用途：    ① 目录分页 POST /index.php?action=loadChapterPage
            body = AES({id, page})           ← 请求也要加密！
         ② 章节内容返回 AES 密文
特点：    key 定期轮换（不是每次），文件名随机变化只是 CDN 层面伪装
```

工程做法：

```javascript
// 1) 详情页里抠出密钥 JS 地址（文件名随机 → 用特征而不是常量名）
var m = String(html).match(/\/templates\/js\/[0-9a-f]{32}\.js/);
// 2) 加 ?_=时间戳 强制回源（qmzw5 血泪：不加会拿到缓存里的旧密钥）
var js = String(java.ajax(origin + m[0] + '?_=' + Date.now()));
// 3) 花括号配平法抠对象（见第七节），别用脆弱正则
// 4) 请求体也要加密时，用 java.aesEncryptToBase64 / 手工 javax.crypto
```

**Legado 四参解密（最常用）**：

```javascript
java.aesBase64DecodeToString(result, key, 'CBC', iv)
//                              ↑密文base64  ↑密钥        ↑模式   ↑IV
```

**兼容新旧格式**：站点把密钥从"平铺常量"改成 `class AESCrypt { ... }` 时，老正则失配。正确做法是**先按新结构提取，失败再退回旧常量**（rrssk 已验证的兼容写法）：

```javascript
var key = null;
try { var blk = braceBalance(html, 'class AESCrypt'); key = /key\s*[:=]\s*['"]([^'"]+)['"]/.exec(blk)[1]; } catch(e){}
if (!key) { key = /(?:var|const)\s+\w+\s*=\s*['"]([0-9a-fA-F]{16,32})['"]/.exec(html)[1]; }
```

---

## 六、体系 C：固定 DES + 响应头派生第二层密钥（晋江）

晋江是**双层密钥**的教科书案例（完整拆解见[晋江篇](方法-晋江书源高级技术拆解.md)），此处只留骨架：

```
第一层（固定）：DES/CBC  key=KW8Dvm2N  iv=1ae2c94b
第二层（动态）：从 HTTP 响应头 accesskey / keystring 派生
取头：  headers:<js>:getCookie():<tag.meta<...>@content>   ← 顺序不能颠倒
拼装：  密钥材料 + 请求头参数共同决定正文可读性
```

**通用启示**：只要正文解密失败但接口返回 200 且有内容，**立刻去翻响应头**。第二层密钥材料放头里是很常见的做法（accesskey / keystring / x-encrypt-key / sign）。

---

## 七、每日轮换签名的兼容提取：花括号配平法

rrssk 家族的搜索签名**每天换**：`GET /?action=signJs&v={日期}` 返回一段 JS，内含签名函数。

**错误做法**：写死函数体正则，或写死签名串。
**正确做法**：把"要执行的代码"从响应里**结构化切出来**，`eval` 后调用。

```javascript
// 花括号配平提取：从起始 { 开始计数，配平即止（兼容任意格式化/注释/嵌套）
function braceSlice(s, from) {
  var i = s.indexOf('{', from), d = 0, j = i;
  for (; j < s.length; j++) {
    var c = s.charAt(j);
    if (c === '{') { d++; }
    else if (c === '}') { d--; if (d === 0) { return s.substring(i, j + 1); } }
  }
  return null;
}
var src = String(java.ajax(base + '/?action=signJs&v=' + today));
var body = braceSlice(src, src.indexOf('function sign'));   // ★配平，不靠结尾正则
var f = eval('(' + body + ')');                              // 拿到函数对象
var sign = f(kw, ts);
```

**为什么必须配平而不是正则**：站点每天重新混淆/换变量名/改空白，但 `{}` 结构不会变。这一招让**同一份规则跨 30+ 天不需要改**（rrssk 实锤）。

同类应用：

- 抠 `class AESCrypt {...}`（第五节）；
- 抠 `var cfg = {...}` 里的密钥/开关；
- 抠 `<script>` 里的分页数组（lianaiya 的 `nav_xxx`、ymxwx 的 `hhekgsv`）。

> 注意 `eval` 的作用域：**函数作用域内 `eval(code)` 声明的 `function` 不会外泄**。要么 `return eval(...)`，要么把 `code + '\n' + 测试代码` 拼成一段一起 eval（zhaoshu 实测技巧）。

---

## 八、base64/字符串解密的"随机对象名"通用套路

ppxsw：`div.txt` 内是 `xxx.yyy('base64…')`，**对象名每本书随机**（`rgr.owes` / `vypflhij.atyffy`）。
ymxwx：`qsbs.bb('base64')`，同理。

用**函数特征**匹配，不匹配名字：

```javascript
// 特征：形如 var NAME={_keyStr:"ABC…="}  —— _keyStr 是 base64 表的黄金特征
var m = String(html).match(/var\s+(\w+)\s*=\s*\{_keyStr/);
var obj = m[1];
// 再用 obj.method('串') 提取；或直接扫所有 '…' 长 base64 串本地解
var b64 = /['"]([A-Za-z0-9+\/=]{40,})['"]/.exec(html);
var text = String(java.base64Decode(b64[1]));
```

三条通用守则：

1. **纯 JS 提取 + `java.base64Decode`**，不要在规则里 eval 站点那段 base64 实现（ymxwx 实测可行且更稳）；
2. 用**长度阈值 + 字符集**筛候选串，避免抓到无关字符串；
3. **组合规则拿不到 script**：`选择器@html@js:` 的 `result` 是**净化后**内容（script 被剥），只有**纯 `@js:`** 才拿到完整源码——这类站点必须走纯 `@js:`（ymxwx 核心发现）。

---

## 九、★破坏性单变量实验：找出真正被校验的那一项

wendulou 的鉴权逆向是范例：接口带 `sign` / `pt` / `time` / `package` / `UA` 五个可疑参数，看起来"必须算签名"。

**做法：一次只破坏一项，看响应变不变。**

| 实验 | 输入 | 结果 | 结论 |
|---|---|---|---|
| 1 | `sign = deadbeef` | **照常返回数据** | sign **完全不校验** |
| 2 | 删 `pt` / `time` | 照常 | 装饰参数 |
| 3 | 删 UA 尾部的 `_{package}` | `books = 0` | ★**真鉴权在这** |
| 4 | 改 `package` 头 | 换内容分发 | package 决定书库 |

→ 整个"签名生成器"根本不用实现，只要把 UA 拼对。**省掉 90% 工作量。**

**纪律**：

- 必须**单变量**（同时改两项就什么都证明不了）；
- 每项至少两个反例（改了变 / 改了不变）；
- 注意副作用：**实验本身会改变环境状态**（米游社清域那次删掉了配对必需键，把后续判断全带偏）。排查时意识到"自己也是变量"；
- 结论要区分"**服务端不校验**"和"**当前未被发现需要校验**"——写进文档时标注实测日期。

---

## 十、Legado 侧解密 API 速查

| 需求 | API |
|---|---|
| AES 解 base64 → 明文 | `java.aesBase64DecodeToString(str, key, mode, iv)` |
| AES 加密 → base64 | `java.aesEncode` / `java.aesBase64EncryptToBase64` 系（按需） |
| base64 → 字符串 | `java.base64Decode(str)` |
| MD5（hex 小写） | `java.md5Encode(str)`；站点用大写/16 位要自己截 |
| RSA / 自定义 | `java.rsaEncode`；复杂场景直接 `Packages.javax.crypto.Cipher` |
| 自定义 JS 函数库 | 书源 `jsLib`（但**本 App 里 jsLib 内不能发网络请求**，见版本差异篇） |
| hex ↔ byte | 手工：`parseInt(pair,16)` / `Integer.toString(b&0xff+0x100,16).substring(1)`；**Java byte 有符号**，要 `& 0xFF` |
| 响应头取值 | `headers:` 规则 + `<js>`，`<js>` 在前 |

---

## 十一、避坑清单

| # | 坑 | 后果 | 对策 |
|---|---|---|---|
| 1 | 把 `md5Encode` 当 raw digest | 全表错 | 它返回 **hex 字符串** |
| 2 | 用原始种子而非 hex 串做 SHA256 | 首块/全乱 | 严格照 JS 侧步骤复现 |
| 3 | 乱码就怀疑密钥 | 其实 IV 错 | **首块乱其余好 = IV 问题** |
| 4 | 不补 base64 `=` 填充 | Python 侧解码失败 | `s += '=' * (-len(s)%4)` |
| 5 | 密钥 JS 走 CDN 缓存 | 拿到过期密钥 | `?_=` + `Date.now()` 强回源 |
| 6 | 正则抠轮换后的 JS | 次日失配 | **花括号配平 + eval** |
| 7 | 写死随机对象名 | 换本书就挂 | 用 `_keyStr` 等**特征**匹配 |
| 8 | 组合规则里找 script | `match` 返回 null | 改纯 `@js:`（净化前内容） |
| 9 | 照着"看起来必填"的参数硬算签名 | 白干 | 破坏性单变量实验先定性 |
| 10 | 实验过程改坏 Cookie/变量 | 后续判断全错 | 意识到自己也是变量；留回退备份 |
| 11 | 函数作用域内 `eval` 后调函数 | 找不到函数 | `return eval(...)` 或拼一起 eval |
| 12 | Java byte 直接 `parseInt` 反推 | 负数错位 | `& 0xFF` |
| 13 | 解密成功但正文仍"内容为空" | 规则链断在下游 | 逐段 `java.log`；见探针法篇 |

---

## 附：一页速查决策树

```
密文长啥样？
├─ base64 特征 ──► java.base64Decode 试一把
│                   ├─ 出明文 → 完事（只是编码）
│                   └─ 出乱码 → 当 AES 处理，去抠 key/iv
├─ 长度 16 倍数 ──► AES/CBC：定位密钥 JS（文件名随机 → ?_= 回源）
│                   解出来"首块乱" → 查 IV 构造（hex？⊕？截断？）
├─ 长度 8 倍数 + 有响应头 key ──► DES + 头派生（晋江式），headers 规则取头
├─ LZString 特征 ──► 找明文旁路（接口/缓存/其他线路），别在规则里实现解压
└─ 全汉字读不通 ──► 字体置换，见字体反爬篇
需要签名/参数？
└─ 先做破坏性单变量实验 → 只实现"真被校验"的那部分
```
