# 方法：全加密 API 书源逆向与客户端可信重放

## ——把「浏览器能看、脚本抓不到」的整站加密协议拆成可复现的 Legado 规则

> 沉淀日期：2026-10-09　｜　来源：zjread.cc（纸间）全站加密协议书源（两个并存源：`纸间` / `zjread（纸间）`）
> 关联：[方法-多层密钥AES与轮换签名逆向](方法-多层密钥AES与轮换签名逆向.md)、[方法-切片签名头与响应加密状态漂移](方法-切片签名头与响应加密状态漂移.md)、[方法-正版App协议逆向与本地缓存书源-QQ阅读](方法-正版App协议逆向与本地缓存书源-QQ阅读.md)、[方法-对照实验驱动的接口逆向与正文排版](方法-对照实验驱动的接口逆向与正文排版.md)、[方法-静默失败定位与探针法](方法-静默失败定位与探针法.md)

---

## 目录

0. [一句话总结与适用识别](#0-一句话总结与适用识别)
1. [★分型：五级加密强度阶梯](#1-分型五级加密强度阶梯)
2. [协议解剖七层模型](#2-协议解剖七层模型)
3. [纸间协议全貌（实测）](#3-纸间协议全貌实测)
4. [★密钥派生：HKDF 双键与「参数顺序反直觉」](#4-密钥派生hkdf-双键与参数顺序反直觉)
5. [★两种 key_mode：会话密钥 vs 章节密钥](#5-两种-key_mode会话密钥-vs-章节密钥)
6. [请求信封与五头签名](#6-请求信封与五头签名)
7. [★破坏性单变量实验：把校验强度问到底](#7-破坏性单变量实验把校验强度问到底)
8. [★人机验证的本地自助：ALTCHA PoW](#8-人机验证的本地自助altcha-pow)
9. [独立加密子通道（封面类）](#9-独立加密子通道封面类)
10. [★跨阶段参数传递：把 GET 明文接口当载体](#10-跨阶段参数传递把-get-明文接口当载体)
11. [★缓存与自愈设计（四级）](#11-缓存与自愈设计四级)
12. [★java 与 source 是同一个对象（实测反直觉）](#12-java-与-source-是同一个对象实测反直觉)
13. [错误码分级与重试编排](#13-错误码分级与重试编排)
14. [两个并存源的分工策略](#14-两个并存源的分工策略)
15. [Legado 侧 API 速查（本协议用到的）](#15-legado-侧-api-速查本协议用到的)
16. [★验证方法论：六步实测清单](#16-验证方法论六步实测清单)
17. [避坑清单 K1~K26](#17-避坑清单-k126)
18. [移植到新站的改动清单](#18-移植到新站的改动清单)
19. [案例档案](#19-案例档案)
20. [通用结论](#20-通用结论)

---

## 0. 一句话总结与适用识别

**这类站点的共同特征**：整个业务 API 全部密文 + 签名，抓包只能看到一坨 base64；但**加密逻辑全部在前端 JS 里**，而 Legado 的 Rhino 能跑完整 `javax.crypto`——所以**客户端能算的，书源都能算**，不需要破解服务端，只需要**忠实重放客户端的加密行为**。

**适用识别信号**（命中任意两条就该走本文路线）：

| 信号 | 观察方式 |
|---|---|
| 抓包响应体是 `{"data":"<长base64>","nonce":"..."}` 这种信封 | 看任意 API 响应 |
| 请求头出现 `X-Signature` / `X-Nonce` / `X-Timestamp` / `X-Key-Version` | 看任意 API 请求头 |
| 首页/搜索页 HTML 里没有书籍数据（纯 SPA 壳） | `view-source` |
| 存在一个"看起来没用"的明文 GET（如 `/api/bootstrap`、`/api/config`） | 遍历 JS 里的接口常量 |
| 站点有 `altcha` / `turnstile` / `captcha` 且返回的是 **challenge 参数**（非图片） | 看验证码接口响应 |

**不适用**：密钥在服务端下发且随机会话无关（如纯 session 表）、需要 WebAssembly 且无法在 Rhino 复现的算法、依赖硬件指纹/TPM 的通道。

---

## 1. ★分型：五级加密强度阶梯

不要一上来就读 JS。先判断落在哪一级，决定投入：

| 级别 | 特征 | 破解难度 | 典型手法 |
|---|---|---|---|
| **L1 只编码** | base64/hex，肉眼可辨 | 5 分钟 | `java.base64Decode` |
| **L2 固定密钥对称加密** | 密钥硬编码在 JS | 30 分钟 | 抠常量 → `java.aesDecodeToString` |
| **L3 动态密钥但同响应可解** | key/iv 与密文同包 | 1 小时 | 信封自解（见 [多层密钥篇](方法-多层密钥AES与轮换签名逆向.md) 体系 A） |
| **L4 握手派生 + 请求签名** | 独立握手接口 + 每请求签名头 | **半天~一天** | **本文主线**（纸间属此级） |
| **L5 客户端证明/硬件绑定** | 需 WASM/设备指纹/TPM | 通常放弃 | 找明文旁路或降级 |

**纸间实测 = L4**，且是 L4 里**最完整的一种**：握手派生双键 + 每请求五头签名 + 章节级密钥重派生 + 本地 PoW 人机验证。

> ★分型的价值：L1~L3 有现成 API 可抄；L4 必须自己实现密码学栈；判断错级别会浪费大量时间在错误方向上。

---

## 2. 协议解剖七层模型

拿到 L4 站点后，按这七层自上而下拆，**每层独立验证**：

```
① 握手层    —— 从哪里拿到种子？（明文 GET）
② 派生层    —— 种子如何变成密钥？（HKDF / KDF / 直接哈希）
③ 信封层    —— 请求体怎么包？（GCM/CBC + nonce + 版本号）
④ 签名层    —— 请求头怎么签？（签哪些字段、什么顺序、什么分隔符）
⑤ 响应层    —— 响应怎么解？（哪个密钥、有无 key_mode 分支）
⑥ 校验层    —— 服务端到底校验哪些项？（破坏性实验）
⑦ 会话层    —— 有效期多久？失效如何自愈？
```

**每一层都要有独立的实测证据**，不能靠"读 JS 猜"。本文档后续每章对应一层。

---

## 3. 纸间协议全貌（实测）

```
【握手】GET /api/bootstrap  (明文，唯一)
        → {expires_at, key_id:"v1", key_material(base64 32B), session_id(32字符)}
            TTL = 21600s = 6 小时

【派生】HKDF-Expand 单轮 L=32，两条独立链：
        会话链：PRK=HMAC(key=sid, msg=km)
                aesKey  = HMAC(key=PRK, msg="novel-api-aes-v1"||0x01)
                hmacKey = HMAC(key=PRK, msg="novel-hmac-v1"||0x01)
        章节链：PRK=HMAC(key=ikm, msg=km)
                chapterKey = HMAC(key=PRK, msg="novel-chapter-aes-v1"||0x01)

【信封】请求体 = {"version":1,"algorithm":"AES-256-GCM","data":b64, "nonce":b64(12B)}
        算法 = AES/GCM/NoPadding，GCMParameterSpec(128, nonce)，无 AAD

【签名】X-Signature = b64(HMAC-SHA256(hmacKey,
            "POST\n{path}\n{ts}\n{nonce}\n{sha256hex(body)}\n{sid}"))
        五头：X-Session-ID / X-Timestamp / X-Nonce / X-Signature / X-Key-Version

【响应】{"version":1,"algorithm":"AES-256-GCM","data":..,"nonce":..,
         "key_mode":"session"|"chapter", "book_id":..,"chapter_id":..,
         "code":0,"message":..}

【校验】全字段强校验（签名/nonce/ts/sid/版本 任一篡改 → 401）
        时间戳容差 < 300 秒

【人机】ALTCHA：GET challenge → 本地 PoW → POST verify → captcha_token(300s)

【封面】独立通道：GET /api/cover?session_id=..&data=..&nonce=..（无签名，仅校验会话）
```

**四个业务接口**（全部 POST + 加密）：
| 接口 | 参数 | key_mode |
|---|---|---|
| `/api/search` | `{keyword, page}` | session |
| `/api/book/detail` | `{book_id}` | session |
| `/api/book/catalog` | `{book_id}` | session |
| `/api/book/content` | `{chapter_id, captcha_token}` | **chapter** |

---

## 4. ★密钥派生：HKDF 双键与「参数顺序反直觉」

### 4.1 读 JS 时的陷阱：嵌套函数把参数顺序转了个身

纸间 JS 里有三个层层套娃的函数：

```js
function v(e,r){ Mac=Mac.getInstance("HmacSHA256"); Mac.init(new SecretKeySpec(e,"HmacSHA256"));
                 return Mac.doFinal(r) }               // v(A,B) = HMAC(key=A, msg=B)
function h(e,r){ return v(e,r) }                       // h(A,B) = HMAC(key=A, msg=B)
function y(e,r,t){ ... }                               // HKDF-Expand(PRK=e, info=r, L=t)
function l(e,r,t,n){ return y(h(r,e), t, n) }          // ★ h(r,e) → HMAC(key=r, msg=e)
```

**关键**：`l(e,r,t,n)` 里调的是 `h(r, e)` 而不是 `h(e, r)`。所以：

- 调用处 `l(km, sid_bytes, "novel-api-aes-v1", 32)`
- 实际展开 = `HKDF(PRK = HMAC(key=sid_bytes, msg=km), ...)`

**如果按"参数顺序就是自然顺序"去猜，会得到 `HMAC(key=km, msg=sid)`，然后解密永远 AEADBadTagException。**

> ★教训：**嵌套一层的函数必须把参数顺序在纸上展开一次**。别用"名字看起来对"来判断。纸间这里我第一次就猜反了，两次 BAD_DECRYPT 才回头读源码。

### 4.2 HKDF-Expand 的单轮实现（L=32 时只跑一轮）

```js
function y(e,r,t){                       // e=PRK, r=info, t=输出字节数
  for(var n="", a=null, i=1; n.length < 2*t; ){
    var s = Mac.getInstance("HmacSHA256");
    s.init(new SecretKeySpec(e,"HmacSHA256"));
    if(a!==null) s.update(a);            // T(i-1)
    s.update(r);                         // info
    s.update(i);                         // 计数器（单字节）
    n += c(a = s.doFinal());             // ★ c() = 转 hex 字符串
    i++;
  }
  return o(n.substring(0, 2*t));         // o() = hexDecode → bytes
}
```

**语义**：`T(i) = HMAC(key=PRK, msg = T(i-1) || info || i)`，累加成 hex 字符串再截断。
L=32 时只跑 1 轮，`T1 = HMAC(PRK, info || 0x01)`。

★注意 `n += c(...)` 是**字符串拼接**（hex），最后统一 `hexDecode`。如果误以为 `n` 是字节数组会算错长度判断。

### 4.3 复现验证法（必做）

```js
// 手工复现 vs jsLib 结果，必须逐字节相等
var Mac=Packages.javax.crypto.Mac, SKS=Packages.javax.crypto.spec.SecretKeySpec;
var m1=Mac.getInstance('HmacSHA256'); m1.init(new SKS(M.a(sess.sid),'HmacSHA256'));
var prk=m1.doFinal(sess.km);
var m2=Mac.getInstance('HmacSHA256'); m2.init(new SKS(prk,'HmacSHA256'));
var baos=new Packages.java.io.ByteArrayOutputStream();
baos.write(M.a('novel-api-aes-v1')); baos.write(1);
var manual=M.c(m2.doFinal(baos.toByteArray()));
var lib   =M.c(sess.aesKey);
(manual === lib)   // 必须 true
```

**实测结果**：`2bd2e7919ddb56badbbd0d15d18f876921a1257336c983a54a89659325118484` == lib ✔

> ★**为什么必须做这一步**：派生公式错一位，症状是"解密报错"而不是"算出另一个值"，无法从错误信息反推。只有手工复现对比才能定位。

---

## 5. ★两种 key_mode：会话密钥 vs 章节密钥

这是纸间最精巧的设计：**同一个接口，根据上下文切换两套密钥**。

### 5.1 响应携带密钥模式

```json
{"version":1,"algorithm":"AES-256-GCM","data":"...","nonce":"...",
 "key_mode":"chapter",            // ← 决定用哪个密钥
 "book_id":"b~...",               // ← 仅 chapter 模式出现
 "chapter_id":"c~...",            // ← 仅 chapter 模式出现
 "code":0,"message":""}
```

解密方必须：
```js
var key = sess.aesKey;
if (resp.key_mode === 'chapter') {
  var nf = b64Decode(resp.nonce);
  key = chapterKDF(sess.km, resp.book_id, resp.chapter_id, resp.version, nf);
}
plain = AES_GCM_Decrypt(key, nf, b64Decode(resp.data));
```

### 5.2 章节密钥的 ikm 构造（★双层 hex）

```js
function w(km, bookId, chapterId, version, nonceBytes){
  return HKDF(
    PRK = HMAC(key = ikm, msg = km),
    info = "novel-chapter-aes-v1",
    L = 32
  );
}
// ikm = hexDecode( hex(bookId + "\n" + chapterId + "\n" + version) + hex(nonceBytes) )
```

**★陷阱**：`ikm` 不是 `bookId+chapterId` 的原始字节，而是**它俩的 hex 字符串再当 ASCII 字节**。
即：`"b~abc"` → hex `"627e616263"` → ikm 里是 **10 个 ASCII 字符 `6,2,7,e,...`**。

实测 ikm 长度 = `53+1+64+1+1+12 = 132` 字节 ✔（book_id 53 字符、chapter_id 64 字符、version 1 字符、nonce 12 字节）

> ★这个双层 hex 是**故意设计的混淆**（也让日志里的密钥材料看起来更长）。识别方法：算一遍预期长度，对不上就说明构造错了。

### 5.3 降级行为（★实测发现）

| 场景 | key_mode | 响应含 book_id/chapter_id | code |
|---|---|---|---|
| 正文 + **有效** captcha_token | `chapter` | ✅ | 0 |
| 正文 + **缺失/无效** captcha_token | `session`（降级） | ❌ | **4001** |

**这意味着**：解析器不能写死"正文一定是 chapter 模式"。必须**读响应里的 key_mode 决定**。

> ★通用启示：**凡是响应里带 `key_mode` / `mode` / `variant` 这类字段，就是设计者在告诉你"用哪套规则"**。写死任何一套都会在降级路径上炸。

---

## 6. 请求信封与五头签名

### 6.1 请求体（AES-256-GCM）

```js
function envelope(obj, aesKey){
  var nonce = randomBytes(12);                        // ★ 12 字节，GCM 标准
  var ct = AES_GCM_Encrypt(aesKey, nonce, UTF8(JSON.stringify(obj)));
  return JSON.stringify({version:1, algorithm:"AES-256-GCM",
                         data: b64(ct), nonce: b64(nonce)});
}
```

**要点**：
- 明文是 `JSON.stringify(参数对象)`，**不是** form-urlencoded
- `nonce` 每次请求随机（12B），**绝不复用**（GCM 复用 nonce = 密钥流复用 = 灾难）
- 无 AAD（`GCMParameterSpec(128, nonce)` 只给 tag 长度和 IV）

### 6.2 五头签名（★签的是 6 个字段的拼接）

```js
function sign(path, body, sess){
  var ts    = String(Math.floor(Date.now()/1000));
  var nonce = b64(randomBytes(18));                    // ★ 18 字节，独立于 body nonce
  var sha   = sha256hex(body);                         // body 的 SHA-256 hex（64 字符）
  var msg   = ["POST", path, ts, nonce, sha, sess.sid].join("\n");   // ★ 6 段，\n 分隔
  var sig   = b64(HMAC_SHA256(sess.hmacKey, UTF8(msg)));
  return {"Content-Type":"application/json",
          "X-Session-ID":  sess.sid,
          "X-Timestamp":   ts,
          "X-Nonce":       nonce,
          "X-Signature":   sig,
          "X-Key-Version": "1",
          "User-Agent":    UA};
}
```

**★三个易错点**：

1. **`sha` 是 hex 字符串**（64 字符），不是原始字节。签的是 hex 文本。
2. **`nonce` 用的是 base64 后的字符串**（`p()` 输出），不是原始字节。
3. **签名 nonce 与 body nonce 是两个独立随机值**（18B vs 12B），不要图省事复用一个。

**实测验证**：手工复现签名 = `ZbwAazJzFp+oGbKEoktAT41DBy6aGr6X3TAnn2bJnB0` vs lib = 同串 + `=` ✔

> ★base64 细节：JS 侧手写 base64 用无填充变体（`p()`），但服务端接受带填充的。实测两者都 200。**签名对比时要注意填充符差异不算错**。

### 6.3 路径参数用「相对路径」

签名里的 `path` 是 `/api/search` 这种**相对路径**（不含域名）。如果签名时用了完整 URL，会 401。

---

## 7. ★破坏性单变量实验：把校验强度问到底

**这是 L4 站点最重要的一步**：不搞清楚服务端校验哪些项，就不知道哪些可以省、哪些必须精确。

### 7.1 实验设计

固定其余全部变量，每次只改一项，观察 HTTP 状态：

```js
function tryReq(tag, mut){
  var body = envelope({keyword:'凡人',page:1}, sess.aesKey);
  var hdr  = sign('/api/search', body, sess);
  mut(hdr);                                    // ← 只改这一项
  try { return tag+': '+post(URL, body, hdr).statusCode(); }
  catch(e){ return tag+': '+e; }
}
```

### 7.2 纸间实测结果（11 组）

| 篡改项 | 结果 | 结论 |
|---|---|---|
| baseline | 200 | — |
| `X-Signature` 改全 A | **401** | 签名真校验 |
| `X-Signature` 删除 | **401** | 不可省 |
| `X-Nonce` 改值 | **401** | nonce 参与签名 |
| `X-Timestamp` = 1000000000 | **401** | ts 参与签名 |
| `X-Timestamp` = now+300 | **401** | 容差 < 300s |
| `X-Timestamp` = now-300 | **401** | 容差 < 300s |
| `X-Timestamp` = now-3600 | **401** | — |
| `X-Session-ID` 改 deadbeef | **401** | sid 参与签名 |
| `X-Key-Version` = "2" | **401** | 版本号校验 |
| `X-Key-Version` = "0" | **401** | 版本号校验 |

**结论**：**全字段强校验，无任何一项可省**。这是"设计良好"的签名方案。

### 7.3 为什么这个实验必须做

三种可能的结果对应三种不同的实现策略：

| 实验结果 | 实现策略 |
|---|---|
| 某些字段删了也 200 | 可以省略该字段的计算 → 代码更简单，且**减少出错面** |
| 全字段强校验 | 必须精确实现每一项，**任何一项算错都表现为统一 401**（难定位） |
| 只校验签名不校验时间 | 可以做长缓存（如缓存整个签名） |

> ★**"全 401"是最难调试的情形**：错误信息无法区分是哪一项错了。这时**唯一出路是手工复现对比**（见 §4.3），而不是反复改规则试。

### 7.4 时间戳容差的正确用法

纸间容差 < 300 秒。这意味着：
- **不能缓存签名**（几分钟后失效）
- **不能离线预生成**
- 每次请求都要现算 → 时间戳必须取设备当前时间

★如果设备时间被用户改过（时区/手动），签名会**整体失败**。这是排查"规则明明对却全 401"时要问的第一个问题。

---

## 8. ★人机验证的本地自助：ALTCHA PoW

**ALTCHA** 是一个开源的反爬 PoW 方案，特征是 challenge 接口返回 `algorithm/salt/nonce/cost/keyPrefix`。

### 8.1 协议

```
GET /api/captcha/altcha/challenge → 200 明文
{"parameters":{"algorithm":"SHA-256","nonce":"111f24f7...","salt":"7a77f2b3...",
               "cost":80,"keyLength":32,"keyPrefix":"c886ab45c8495edd27a01a5dffacb0d0",
               "expiresAt":1791475895},
 "signature":"349b6805..."}
```

### 8.2 PoW 算法（客户端本地求解）

```
for counter in 0..200000:
    h = SHA256( hexDecode( salt + hex8(counter) ) )
    for i in 1..cost-1:
        h = SHA256(h)
    if hex(h)[0 : len(keyPrefix)] == keyPrefix:
        return {counter, derivedKey: hex(h)[0 : 2*keyLength]}
```

**关键细节**：
- `hex8(n)`：counter 的 8 位 hex（大端；JS 里 `for(r=24; r>=0; r-=8) t += hex8((n>>>r)&255)`）
- **先 hexDecode 再 SHA256**：即 `salt` 与 `hex8(counter)` 拼成 hex 字符串后**解码成字节**再哈希
- `cost` 是**迭代次数**（这里是 80），不是难度
- `keyLength` 是**输出 hex 长度的一半**（32 → 64 个 hex 字符）

### 8.3 实测

```
cost=80 → 求解耗时 ~1.2 秒，counter=33 命中
derivedKey = "231443dda383a15ae789686b9a38c8376eb5c76a13319575a2a6cee11c13c361"
keyPrefix  = "231443dda383a15ae789686b9a38c837"   ← 前 32 字符匹配 ✔
```

### 8.4 提交（★注意 payload 是裸 base64，不是加密信封）

```js
POST /api/captcha/altcha/verify
body = { payload: b64(JSON.stringify({
          challenge: <原始 challenge 对象>,
          solution: {counter, derivedKey, time: 耗时毫秒}
        })) }
→ {captcha_token: "...", expires_in: 300}
```

★**这个 payload 没有走 §6 的加密信封**（它本身就是 base64）。识别方法：看 JS 里调的是 `b64()` 还是 `envelope()`。

### 8.5 缓存与失效

```js
source.put('zj_captcha_v1', {token, exp: now+expires_in, sid});
// 命中条件：同 sid && token 非空 && now < exp-30
```
**实测**：命中时 0ms 返回；失效或 `verify` 失败时清空缓存重取。

> ★**ALTCHA 的工程价值**：把"人机验证"降级成了"本地算力问题"。**只要 challenge 参数是明文的，PoW 就能在书源里跑**。
> 对比：图形验证码/滑块必须人工（见 [登录注册验证码与限频破解](方法-登录注册验证码与限频破解.md)）；Cloudflare Turnstile 需要真实浏览器（见 [AEGIS-ALTCHA 篇](方法-AEGIS-ALTCHA验证与WebView通道书源.md)）。

---

## 9. 独立加密子通道（封面类）

纸间的封面**不是**直接给 URL，而是要在客户端本地生成加密 URL：

```
GET /api/cover?session_id={sid}&data={b64url(AES-GCM(aesKey, nonce, JSON{book_id,size}))}&nonce={b64url(nonce)}
```

**特点**：
- **无签名头**（只有会话校验）—— 因为它是 GET，无法放 body
- **参数走 URL**，所以 base64 要转 URL-safe（`+`→`-`，`/`→`_`，去掉 `=`）
- 明文是 `JSON.stringify({book_id, size})`

**实测**：
- 正确 URL → 200，**77466 字节真实 JPEG**（magic `ffd8ff`）
- 改 `session_id=INVALID` → **401**
- 搜索响应里的 `cover` 字段给的是**明文相对路径** `/api/cover?bookId=...&size=180`，直接请求 → **401**（不能直接用！）

> ★**"响应里给的 URL 不能直接用"是加密站的常见陷阱**。识别方法：拿响应里的 URL 直接请求一次，看是否 401/403。

---

## 10. ★跨阶段参数传递：把 GET 明文接口当载体

### 10.1 问题

Legado 的书源流程是**多阶段**的：搜索 → 详情 → 目录 → 正文。每个阶段的数据（book_id / chapter_id）必须**写进 URL**，因为 Legado 靠 URL 传递阶段间状态。

但纸间的 id 是 `b~jUwff02tXeE5W4ZNwMRWSIQT-BOMvhtefH4-4YiOH1ftJi1on3s` 这种**不透明长串**，直接拼成 `/api/book/detail` 又需要 POST + 加密。

### 10.2 解法：用明文 GET 接口做"参数容器"

```js
function zjUrl(param, value){
  return ZJ_BASE + "/api/bootstrap?" + param + "=" + encodeURIComponent(String(value));
}
function zjParam(url, param){
  var m = String(url||"").match(new RegExp("[?&]" + param + "=([^&]+)"));
  return m ? decodeURIComponent(m[1]) : "";
}
```

生成的 URL 长这样：
- 详情：`https://www.zjread.cc/api/bootstrap?zjb=b~jUwff...`
- 目录：`https://www.zjread.cc/api/bootstrap?zjb=b~jUwff...`（同详情）
- 章节：`https://www.zjread.cc/api/bootstrap?zjc=c~C-ivQ...`
- 搜索：`https://www.zjread.cc/api/bootstrap?zjk=%E5%87%A1%E4%BA%BA&zjp=1`

### 10.3 为什么这个设计很聪明

1. **不产生额外请求**：详情页 URL 本身**永远不会被请求**（因为详情靠 `ruleBookInfo.init` 执行，init 只读 baseUrl 参数）
2. **天然支持编码**：用 `encodeURIComponent` 编码，特殊字符安全
3. **复用同一个明文接口**：不需要新增端点
4. **参数名区分阶段**：`zjb`=book、`zjc`=chapter、`zjk`=keyword、`zjp`=page

**实测往返**：`b~A+B/C=D&E?F#G` → `b~A%2BB%2FC%3DD%26E%3FF%23G` → 解回原值 ✔

> ★通用模式：**任何"需要 POST + 加密"的站点，都可以借一个明文 GET 接口当参数载体**。
> 备选载体：站点根路径带 query（`https://site/?b=xxx`）、静态资源路径（`https://site/static/b/xxx`）。
> 只要**该 URL 不会被实际请求**，就是安全的。

---

## 11. ★缓存与自愈设计（四级）

加密协议书的**核心矛盾**：握手有成本（一次请求 + 派生计算），但会话会过期。设计好缓存是可用性的关键。

### 11.1 纸间的三级缓存

| 键 | 内容 | TTL 策略 | 失效自愈 |
|---|---|---|---|
| `zj_session_v1` | `{sid, km, aes, hmac}` | **不存过期时间** | 401 → 强制重建 |
| `zj_captcha_v1` | `{token, exp, sid}` | `exp-30s` 主动判 | verify 失败 → 清空重取 |
| `zjd` | 详情页字段 JSON | 无 | 每次 init 覆盖 |

### 11.2 ★会话缓存为什么不存过期时间

服务端给了 `expires_at`（6h），但 JS **故意不存**。理由：

- 存了要处理"快过期时提前刷新"的复杂逻辑
- 不存则**依赖 401 自愈**：反正过期后第一次请求会 401，重试时 `k(true)` 强制重建
- **更简单且更健壮**（服务端改 TTL 也不用改规则）

```js
function zjPost(path, body){
  var err = null;
  for (var a=0; a<2; a++){
    var r = K( k(a===1), path, body );     // ★ a=0 用缓存会话，a=1 强制新建
    if (r.plain !== undefined) return r.plain;
    err = r.err;
    if (!r.retry) throw "zjPost 失败("+path+"): "+err;
  }
  throw "zjPost 失败("+path+"): "+err;
}
```

> ★**"重试时换条件"是重试设计的关键**。同一条件重试两次等于没重试。这里的条件切换是**会话来源**（缓存 → 新建）。

### 11.3 ★缓存校验的三条件（防污染）

```js
if (c && c.length===32 && s && s.length===32 && u && u.length>0) return {...};
```

**实测 4 种污染场景全部自愈**：

| 污染形态 | 结果 |
|---|---|
| 长度不对（4 字符） | 重建 ✔ |
| 完全垃圾 JSON（`not-json-at-all`） | 重建 ✔ |
| 空字符串 | 重建 ✔ |
| 缺 `km` 字段 | 重建 ✔ |

> ★**为什么必须校验**：书源缓存可能被用户手动清、被其他版本覆盖、被 `##` 后缀源交叉污染。
> 校验**长度**比校验内容便宜且足够——密钥材料长度是固定的（32 字节）。

### 11.4 ★双源隔离（`##` 后缀的妙用）

```
A 源键：v_https://www.zjread.cc_zj_session_v1
B 源键：v_https://www.zjread.cc##_zj_session_v1
```

因为 `BaseSource.put(k,v)` 的实际键是 `v_{getKey()}_{k}`，而 `getKey()` 返回**完整 bookSourceUrl**。

**实测**：A 写入 `zj_iso_test`，B 读不到 ✔

> ★**这就是 `##` 后缀在书源里的第二个用途**（第一个是防重复导入）。同一个站点做多个变体源时，**用 `##` 后缀天然隔离所有缓存**，避免两个源互相污染会话/验证码。

---

## 12. ★java 与 source 是同一个对象（实测反直觉）

### 12.1 实测

```js
java === source      // → true
String(java)         // → "BookSource(bookSourceUrl=https://www.zjread.cc, bookSourceName=纸间, ...)"
```

### 12.2 源码依据

```kotlin
// app/src/main/java/io/legado/app/data/entities/BaseSource.kt:64
interface BaseSource : JsExtensions {
    @JavascriptInterface
    fun put(key: String, value: String): String {
        CacheManager.put("v_${getKey()}_${key}", value)      // ★ 键含 getKey()
        return value
    }
    @JavascriptInterface
    fun get(key: String): String {
        return CacheManager.get("v_${getKey()}_${key}") ?: ""
    }
}
```

`BookSource` 实现 `BaseSource`，而 `BaseSource` 继承 `JsExtensions`。规则 JS 里绑定的 `java` 就是这个 BookSource 实例。

### 12.3 三个推论

1. **`java.put` 与 `source.put` 完全等价**（同一对象、同一方法、同一键空间）
2. **`java.ajax` / `java.get` / `java.md5Encode` 等"工具函数"也是 BookSource 的方法**（继承自 JsExtensions）
3. **跨字段传值可以借道缓存**：`ruleBookInfo.init` 里 `java.put('zjd', ...)`，其他字段 `java.get('zjd')` 读

### 12.4 ★跨字段传值的风险

纸间的 `zjd` 键**不含书籍 ID**，所以：

**实测**：书1 写入 `{name:"讓仙門再次偉大"}` → 书2 写入 `{name:"以神通之名"}` → 再读书1 的字段，拿到的是**书2 的数据**。

**什么时候安全**：
- Legado 读详情页时是**顺序执行所有字段规则**（init 先跑，其余字段紧跟）→ 单线程下安全
- 用户快速切换书籍时可能交错 → 有串数据风险

**更安全的替代**（推荐）：把键名带上书籍 ID，如 `java.put('zjd_'+id, ...)`。

> ★**这是"能用但不完美"的典型**：原作者为了简洁用了全局键，代价是并发场景的脆弱性。
> 做书源时如果发现字段偶发串数据，先查这类全局缓存键。

---

## 13. 错误码分级与重试编排

### 13.1 纸间的错误分级

```js
function K(sess, path, body){
  try { r = post(...); } catch(e){ return {err:"请求异常: "+e, retry:true}; }
  if (s===401) return {err:"HTTP 401（会话/签名被拒）", retry:true};
  if (s===403) return {err:"HTTP 403 人机验证未通过", verify:true};
  if (s<200||s>=300) return {err:"HTTP "+s, retry:true};
  a = JSON.parse(u);
  if (a.code===401) return {err:"业务 401", retry:true};
  if (a.code===403 || a.code===4001) return {err:"人机验证失败 code="+a.code, verify:true};
  if (a.code!==0) return {err:"业务错误 code="+a.code+" "+a.message};
  if (!a.data || !a.nonce) return {err:"响应缺密文", retry:false};
  // 解密
  return {plain: decrypt(a)};
}
```

**三级分类**：

| 分类 | 触发条件 | 上层动作 |
|---|---|---|
| `retry:true` | 网络异常 / HTTP 401 / 业务 401 / 5xx | **重建会话**后重试一次 |
| `verify:true` | HTTP 403 / 业务 403 / 4001 | **清 captcha 缓存**后重试一次 |
| 无标记（终态） | 业务 code≠0 / 响应缺字段 | **直接抛错**，不重试 |

### 13.2 ★实测错误消息质量

```
无效 book_id    → zjPost 失败(/api/book/detail): 业务错误 code=400 无效书籍
无效 chapter_id → zjPost 失败(/api/book/content): 业务错误 code=400 无效章节
无效 book_id（目录） → zjPost 失败(/api/book/catalog): 业务错误 code=400 无效书籍
```

**每个错误都带**：接口路径 + 业务码 + 服务端中文消息。这是**可直接展示给用户**的质量。

### 13.3 重试编排

```
zjContent(chapterId):
  for a in 0..1:                          ← 最多 2 轮
    sess = k(a===1)                       ← 第2轮强制新建会话
    try { token = C(sess) }               ← 取/换 captcha token
    catch { 清 captcha 缓存; continue }    ← 验证失败 → 下一轮
    r = K(sess, '/api/book/content', {...})
    if (r.plain) return parse(r.plain)
    if (r.verify) 清 captcha 缓存
    if (!r.retry && !r.verify) throw r    ← 终态错误立即抛出
  throw 最后错误
```

> ★**"重试预算"是必须的**。没有预算的重试在站点故障时会变成请求风暴（记忆 91 的 STV 限流教训）。
> 纸间用 `for a in 0..1` 硬编码 2 轮，简单有效。

---

## 14. 两个并存源的分工策略

纸间有两个源，**不是重复而是互补**：

| 维度 | A「纸间」 | B「zjread（纸间）」 |
|---|---|---|
| `bookSourceUrl` | `https://www.zjread.cc` | `https://www.zjread.cc##` |
| `enabledExplore` | **true** | false |
| `exploreUrl` | `@js:zjExplore()` | 无 |
| `ruleExplore` | 完整 | `{}` 空 |
| `updateTime` 字段 | 无 | **有** |
| 繁转简 `z()` | **有**（书名/作者/简介/章节名/正文） | 无（繁体直出） |
| `jsLib` 长度 | 7934 | 7381（差 553） |
| `bookSourceComment` | 无 | **有**（协议说明） |
| 缓存隔离 | `v_..._cc_...` | `v_..._cc##_...` ✔ |

### 14.1 分工逻辑

- **A 源**：面向**阅读体验**（简体 + 发现页），适合日常用
- **B 源**：面向**协议存档**（含完整 comment 说明 + updateTime 字段），适合做参考

### 14.2 ★为什么"繁体/简体"要做成两个源而不是一个开关

- 简体转换是**不可逆的信息损失**（`著` → `着`，但原文的 `著` 可能是"著作"）
- 有些用户就喜欢看繁体原文
- 两个源可**同时存在**，用户按需切换

> ★**通用启示**：当站点数据有"要不要加工"的分歧时，**做成两个源比做一个开关更好**——
> 开关需要 UI（登录界面按钮），而两个源零成本且可并存。类似案例见 [单源多模式切换](方法-单源多模式切换书源制作.md)（那个场景内容形态差异太大，才需要开关）。

---

## 15. Legado 侧 API 速查（本协议用到的）

| 用途 | API | 实测备注 |
|---|---|---|
| 字节编解码 | `java.strToBytes(s)` / `java.bytesToStr(b)` | UTF-8 |
| hex | `java.hexEncodeToString(s)` / `java.hexDecodeToByteArray(hex)` | 注意 hexDecode 返回 ByteArray |
| base64 | `java.base64Encode(s)` / `java.base64DecodeToByteArray(s)` | base64Decode 返回 ByteArray |
| 摘要 | `java.digestHex(data, "SHA-256")` | 返回 64 字符 hex |
| HMAC | `java.HMacHex(data, algo, key)` / `java.HMacBase64(...)` | **只接受 String 参数** |
| 对称加密 | `java.createSymmetricCrypto(...)` | 高级封装，GCM 不支持 |
| 底层密码学 | `Packages.javax.crypto.*` | **本文主力**（GCM/HKDF 必须用它） |
| 随机数 | `Packages.javax.crypto.KeyGenerator.getInstance("AES")` | 书源用此法生成随机字节 |
| 繁转简 | `java.t2s(s)` / `java.s2t(s)` | 实测可用 |
| 缓存 | `source.put(k,v)` / `source.get(k)` | 键 = `v_{bookSourceUrl}_{k}`，持久化 |
| 网络 | `java.get(url, headers)` / `java.post(url, body, headers)` | headers 是 JSON 对象 |

### ★随机字节的生成（书源没有 `SecureRandom` 直接绑定）

```js
function randomBytes(n){
  var out = "";
  while (out.length < 2*n) {
    var kg = Packages.javax.crypto.KeyGenerator.getInstance("AES");
    kg.init(128);
    out += hex(kg.generateKey().getEncoded());   // 16 字节 → 32 hex
  }
  return hexDecode(out.substring(0, 2*n));
}
```

**实测**：生成的 12B / 18B nonce 服务端全部接受。

> ★**为什么不用 `new java.security.SecureRandom()`**：Rhino 里 Java 构造器要写 `new Packages.java.security.SecureRandom()`，实测可行但 KeyGenerator 更省事且同样是密码学安全随机源。

### ★GCM 的调用方式（无现成封装）

```js
function aesGcmDecrypt(key, nonce, ct){
  var Cipher = Packages.javax.crypto.Cipher;
  var c = Cipher.getInstance("AES/GCM/NoPadding");
  c.init(Cipher.DECRYPT_MODE,
         new Packages.javax.crypto.spec.SecretKeySpec(key, "AES"),
         new Packages.javax.crypto.spec.GCMParameterSpec(128, nonce));  // 128 = tag 位数
  return c.doFinal(ct);
}
```

★**GCM 认证失败会抛 `AEADBadTagException`**（不是返回乱码）。这是好事——**能立刻知道密钥/IV 错了**，比 CBC 的"静默乱码"友好得多。

---

## 16. ★验证方法论：六步实测清单

拆完 L4 协议后，按这六步验证，每步都要有**可打印的证据**：

### 第 1 步：握手明文可读
```js
var r = java.get(BASE+'/api/bootstrap', {UA});
r.statusCode()      // 200
JSON.parse(r.body()) // 有 session_id / key_material
```

### 第 2 步：密钥派生逐字节对比
```js
manualKey === libKey    // 必须 true（见 §4.3）
```

### 第 3 步：破坏性实验确认校验强度
```js
// 逐项篡改，记录状态码（见 §7）
```

### 第 4 步：端到端全链路（模拟 Legado 真实调用顺序）
```js
searchUrl → zjParam 提取 → 搜索 → 取第一条 → zjUrl 生成 bookUrl
→ zjParam 反解 → 详情 → 目录 → 章节 URL → 正文
```
**纸间实测**：搜索 24 条 → 详情 → 目录 460 章 → 正文 4069 字 ✔

### 第 5 步：缓存污染自愈
```js
// 依次注入 4 种污染，验证都能自愈（见 §11.3）
```

### 第 6 步：错误路径
```js
// 无效 ID / 缺 token / 错签名，验证错误消息可读（见 §13.2）
```

> ★**第 4 步是关键**：前面五步都对，不代表端到端能跑通。
> 纸间实测时我先把 1~3 步做完了，第 4 步才发现 `zjCoverUrl` 在缓存失效时返回空串。

---

## 17. 避坑清单 K1~K26

### 派生与密码学
- **K1** 嵌套函数的参数顺序必须纸上展开（`l(e,r)` 里可能是 `h(r,e)`）—— 纸间首次猜反，两次 BAD_DECRYPT
- **K2** HKDF 的 `info` 可能不是字符串而是 `hex(...) + hex(nonce)` 的**双层 hex**
- **K3** `y()` 累加的是 **hex 字符串**不是字节数组，长度判断用 `n.length < 2*t`
- **K4** 章节密钥的 ikm 长度要**先算预期值**（`len(bid)+1+len(cid)+1+len(ver)+len(nonce)`），对不上就是构造错
- **K5** GCM 的 nonce 是 **12 字节**，不是 16
- **K6** 签名用的 nonce 与 body 用的 nonce 是**两个独立随机值**（纸间 18B vs 12B）
- **K7** 签名消息里的 body 哈希是 **hex 字符串**（64 字符），不是原始字节
- **K8** 签名消息里的 nonce 是 **base64 字符串**，不是原始字节
- **K9** base64 对比时**填充符差异不算错**（JS 手写实现常省略 `=`）
- **K10** 签名的 path 用**相对路径**（`/api/search`），不含域名

### 请求与响应
- **K11** 请求体明文是 `JSON.stringify(参数)`，不是 form 编码
- **K12** 响应必须**读 `key_mode` 决定用哪个密钥**，不能写死
- **K13** `key_mode=chapter` 时 `book_id/chapter_id` **在响应里**（不在请求里）
- **K14** 响应里给的 cover 明文 URL **直接请求会 401**，必须本地生成加密 URL
- **K15** 独立加密子通道（GET 类）的 base64 要转 **URL-safe**（`+`→`-`、`/`→`_`、去 `=`）
- **K16** 业务错误码在**解密后的 JSON 里**（不是 HTTP 状态码），必须先解密才能判断
- **K17** 有些接口会用 `code=4001 + key_mode=session` 表示"验证失败降级"，别当正常响应解

### 缓存与状态
- **K18** 会话缓存**不存过期时间**是刻意设计，靠 401 自愈更健壮
- **K19** 缓存校验至少验**长度**（`aes.length===32`），否则污染数据会一直用
- **K20** 重试时**必须换条件**（缓存会话 → 新建会话），同条件重试等于没重试
- **K21** 跨字段传值的全局键（如 `zjd`）**不带书籍 ID 会串数据**
- **K22** `##` 后缀源与主源**缓存天然隔离**（`getKey()` 含完整 URL）

### 环境与调试
- **K23** `java === source` 是同一个 BookSource 对象，`java.put` ≡ `source.put`
- **K24** 设备时间不准会导致**全部签名 401**——排查"规则对却全 401"先问时间
- **K25** `eval(jsLib)` 在嵌套函数调用里会丢作用域（`hexDecodeToByteArray` 找不到），测试要用 `new Function(...)` 显式传参
- **K26** Rhino 里 `java` 变量会遮蔽 `java.*` 包名，必须写 `Packages.java.lang.String`

---

## 18. 移植到新站的改动清单

遇到另一个 L4 站点时，**90% 的骨架不用改**，只改这些：

| 位置 | 改什么 |
|---|---|
| `ZJ_BASE` / `ZJ_UA` | 域名与 UA |
| 握手接口路径 | `/api/bootstrap` → 新路径 |
| 派生 info 常量 | `"novel-api-aes-v1"` / `"novel-hmac-v1"` / `"novel-chapter-aes-v1"` |
| 信封版本号 | `version:1` → 新值 |
| 签名消息格式 | 6 段 `\n` 拼接 → 新格式（**先做破坏性实验确认**） |
| 签名头名 | `X-Session-ID` 等五头 → 新头名 |
| 业务接口路径与参数 | 4 个接口 |
| `key_mode` 判定 | 新站可能没有，或字段名不同 |
| 验证码协议 | ALTCHA → 可能没有 / 换方案 |
| 错误码表 | `400/401/403/4001` → 新表 |
| 参数载体 | `zjUrl/zjParam` 的参数名（`zjb/zjc/zjk/zjp`） |

**不需要改**：HKDF 实现、GCM 封装、随机数生成、重试编排、缓存自愈、繁转简包装。

---

## 19. 案例档案

| 站点 | 加密级别 | 核心手法 | 关键坑 |
|---|---|---|---|
| **zjread.cc（纸间）** | **L4** | 握手派生双键 + 五头签名 + 章节级密钥重派生 + ALTCHA PoC | 嵌套函数参数顺序反直觉；章节 ikm 双层 hex；响应 key_mode 降级 |
| s.wendulou.com | L3 | 动态种子信封（key/iv 同包） | IV 用 `md5().hexdigest()` 前 16 字符的 ASCII |
| jjwxc.net | L3+ | 固定 DES + 响应头派生第二层 | 顺序不能颠倒（先取头再取 Cookie） |
| aaawz.cc | L2+ | LZString + 字体置换 | 需要字形位图匹配 |
| 网易云 weapi | L4（失败） | AES+RSA 双层 | 服务端策略层拒绝，改走明文旁路 |
| QQ阅读 | L4+ | 设备指纹 + 自实现密码学栈 + tar 容器 | 见 [QQ阅读篇](方法-正版App协议逆向与本地缓存书源-QQ阅读.md) |

---

## 20. 通用结论

1. **"客户端能算的，书源都能算"**。L4 站点的安全性建立在"脚本环境没有密码学库"这个假设上——而 Legado 的 Rhino **有完整的 `javax.crypto`**。这个假设在书源场景下不成立。

2. **分型决定投入**。L1~L3 有现成套路（1 小时内），L4 需要完整实现密码学栈（半天到一天），L5 应该直接放弃找旁路。判断错级别会浪费大量时间。

3. **每层都要独立验证**。七层模型里任何一层猜错，症状都是统一的"401"或"解密失败"，无法从错误信息反推。**手工复现逐字节对比**是唯一可靠的定位手段。

4. **破坏性实验是必修课**。不搞清楚服务端校验哪些项，就不知道哪些可以省、哪些必须精确。11 组实验换来的是"知道自己在做什么"。

5. **响应里的模式字段是设计者的善意**。`key_mode` 这类字段明确告诉你"用哪套规则"，写死任何一套都会在降级路径上炸。

6. **重试必须换条件**。缓存会话失败 → 新建会话重试；验证失败 → 换 token 重试。同条件重试是无效功。

7. **缓存校验的最低标准是长度**。长度对不上直接重建，比重试和容错都便宜。

8. **`##` 后缀是缓存隔离的免费午餐**。同站多源时用它，零成本避免会话/验证码互相污染。

9. **跨字段传值要带 ID**。全局键（`zjd`）在单线程下能用，但并发场景会串数据。

10. **错误消息质量决定可维护性**。纸间的 `zjPost 失败(/api/book/detail): 业务错误 code=400 无效书籍` 是可直接展示给用户的质量——**做书源时应该主动把错误分类翻译成中文**，而不是让用户看到 `AEADBadTagException`。

11. **两个并存源比一个开关源更好**（当差异只是"要不要加工数据"时）。开关需要 UI，两个源零成本且可并存。

12. **人机验证的自动化程度取决于 challenge 是否明文**。ALTCHA（明文参数 + 本地 PoW）= 全自动；图形码/滑块 = 必须人工；Turnstile = 需要真浏览器。
