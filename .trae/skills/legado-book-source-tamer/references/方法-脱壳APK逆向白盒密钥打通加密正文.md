# 方法：去加固 APK 逆向白盒密钥，打通「短密文」加密正文

> 261109 猫眼看书（🐈 / yutinglu.com）第三轮攻坚实战。前两轮在加固壳里爆破 43.7 万 + 840 组候选全军覆没；用户提供**去加固 APK** 后，一次反编译即定位密钥，正文从「诊断提示」升级为**完整可读正文**。
> 本文是《方法-ProxyPin抓包逆向聚合App新协议与Legado解密链路》的续篇：那篇解决「主协议 + 降级」，这篇解决「最后一块短密文」。

---

## 0. 一句话结论（先给配方）

**加密正文不要在加固壳 SO 里硬爆破；要拿到脱壳后的业务 dex，用 xref 从「加密实体字段」反查到真实解密函数，再把它翻译成 Legado jsLib。**

```
is_encrypt 字段
  └─(dex_xref)→ CatalogRepository.lambda$getArtChapterContent$4
       └─ 源码：if(is_encrypt){ setName(MkAES.decrypt(name)); content=MkAES.decrypt(content) }
            └─ MkAES: AES/CBC/PKCS5Padding, key/IV 全是硬编码常量
                 └─ 对照实验（正/反双向）→ 复现到 jsLib → 全链路打通
```

---

## 1. 为什么前两轮会卡死（根因复盘）

| 阶段 | 手里的东西 | 结论 | 为什么不够 |
|---|---|---|---|
| 第1轮 | 抓包 + 主协议 D() | 搜索/详情/目录全破，正文短密文未破 | 短密文是**另一套算法**（纯 N×16B、无 seed/IV/tail），不能套主协议 |
| 第2轮 | 加固壳 `libjiagu_a64.so` + 全熵 `Encrypt.jpg` | SOmcp 判定「360/梆梆通用壳，无 Java_* / 无 AES 常量 / strdecrypt blobCount=0」 | **壳里根本没有业务代码**；frida/unidbg 后端又不可用 ⇒ 静态路径封死 |
| 第2轮 | 43.7 万 + 840 组 key 爆破 | 零真命中 | 密钥不是从响应头/conf/站点字符串派生的，是**硬编码在业务 dex** 里，爆破空间压根没覆盖到 |
| **第3轮** | **去加固 APK**（9 dex / 34198 类） | **一次命中** | 业务类 `com.amgcyo.cuttadon.*` 全部可见，密钥/IV 是明文常量 |

★ **方法论铁律**：当「爆破量级已经很大却零命中」+「壳里无业务符号」时，不要再加大爆破规模，**优先级最高的动作是想办法拿到脱壳 dex / 运行时 hook**，而不是继续猜 key 派生路径。用户一句「工作目录已经有去掉so加固的apk文件了」直接把死局变活局。

---

## 2. 工具链与定位步骤（MTmcp2 反编译）

### 2.1 打开 APK 先确认「真的脱壳了」

```
mt_apk_list_available_apks → 顶点小说_3.2.1_去广告版.apk
mt_apk_workspace_open(temporary=false) → counts: dexEntries=9, classes=34198
```

对照旧加固包：`classes.dex` 只有 4 个类（`com.stub.StubApp` / `com.tianyu.util.*`）。**34198 类 vs 4 类** 就是脱壳成功的硬判据。看到 9 个 dex + 三万类，就别再去看 `libjiagu_*.so` 了，业务全在 dex。

### 2.2 从「加密实体字段」起手，不要从「crypto 类名」起手

```
mt_apk_search(overview, "is_encrypt")
⇒ dex_field:Lcom/amgcyo/cuttadon/api/entity/other/MkChapterContent;->is_encrypt:Z
```

`mt_apk_dex_xref` 对该字段只能拿到 getter/setter/toString（实体自引用），**信息量低**。真正有价值的是**方法名/类名搜索**：

```
mt_apk_search(dex_names, "decrypt")
⇒ 46 命中，其中三条关键：
  com.amgcyo.cuttadon.app.utils.MkShapeUtils;->decryptBook(String)     ← 名字最像正文
  com.amgcyo.cuttadon.app.utils.MkShapeUtils;->decrypt(SecretKeySpec,[B[B)
  me.jessyan.art.encrypt.MkAES;->decrypt(String)                        ← 真凶
```

★ **陷阱**：`decryptBook()` 名字最像「正文解密」，实际 xref 只有 `UserPresenter$26.onError`（用户信息解密），是干扰项。**必须靠 xref 到实际调用链判定，不能凭函数名猜**（本次若偷懒直接用 decryptBook，会拿 `SHA256("hyy001")` 去解，必然 BadPadding）。

### 2.3 决定性一步：对 `MkAES.decrypt(String)` 做 method xref

```
mt_apk_dex_xref(dex_method:...MkAES;->decrypt(String)..., dispatch)
⇒ 5 refs:
   MkCatalog.getName()                                    ← 目录章节名也用它解
   CatalogRepository.lambda$getArtChapterContent$4 ×2     ← name + content 两次
   ArtConfigUtils.getSavedMkAdBean / ReadConstant...      ← 广告/配置（旁证）
```

`mt_apk_dex_read_pseudocode` 读 lambda 得到**完整语义**：

```java
MkChapterContent r9 = (MkChapterContent) r8.getData();
String r0 = r9.getName(), r1 = r9.getContent();
if (r9.isIs_encrypt() == false) goto L5;
r9.setName(MkAES.getInstance().decrypt(r0));
r1 = MkAES.getInstance().decrypt(r1);
L5: MkFileUtils.saveEasyBookChapterContentToFile(..., r1);
```

⇒ **`is_encrypt=true` 时 name 与 content 都过 `MkAES`**，且解密后才落缓存文件。这一行同时解释了「为什么 CDN 密文是静态对象」和「为什么章节名也是密文」。

### 2.4 读 `MkAES` 拿到常量

```java
CIPHERMODEPADDING = "AES/CBC/PKCS5Padding";
skforAES = new SecretKeySpec("Pxga!h*e4@T8xfOm".getBytes("ASCII"), "AES");  // 16B → AES-128
IV = new IvParameterSpec("E&z!EHGLd$fli*8R".getBytes());                    // 16B
```

注意：Android 的 `PKCS5Padding` 与 `PKCS7Padding` 对 AES 等价，Legado 里用 `AES/CBC/PKCS5Padding` 即可。**key/IV 是纯 ASCII 常量，用 base64 硬编码进 jsLib 最省转义**（`UHhnYSFoKmU0QFQ4eGZPbQ==` / `RSZ6IUVIR0xkJGZsaSo4Ug==`）。

顺带读 `MkShapeUtils` 确认干扰项：`AES/CBC/PKCS7Padding` + `key=SHA256("hyy001")` + `IV=16×0` —— 与主协议 `D()` 又是两套，一个 APK 里三套 AES 并存，**必须逐一套 xref 归因**。

---

## 3. 对照实验：正反两组定真凶（不可省）

不要「反编译看到像的函数就直接写进书源」。用 App 内 `eval_js` 对**同一份真实密文**跑两组：

```js
// A: MkAES（xref 指向正文链路）
dec(ct, key='Pxga!h*e4@T8xfOm', iv='E&z!EHGLd$fli*8R', 'AES/CBC/PKCS5Padding')
// B: MkShapeUtils.decryptBook（名字像但 xref 不指向正文）
dec(ct, key=SHA256('hyy001'), iv=16×0, 'AES/CBC/PKCS7Padding')
```

| | content | name | 判定 |
|---|---|---|---|
| **A** | ✅ 8213B，「　　此时，绝云崖边，一块两人高的巨石侧…」 | ✅「第一卷 祸水红颜 序章」 | **真凶** |
| B | ❌ `BadPaddingException: BAD_DECRYPT` | ❌ 同上 | 排除 |

再补**第三组反向验证**：拿主协议密文（搜索响应）喂给 `MK()` → 同样 `BadPaddingException` ⇒ 证明 `D()` 与 `MK()` 必须按 `is_encrypt` 分流，不能合并成一个解密函数。

批量放大：**3 个源站 × 首/中/末章 = 9 章**全部解出，长度与响应 `num_words` 吻合；目录 `MkCatalog.getName()` 解出真实章节名。到这里才允许改书源。

---

## 4. 翻译成 Legado jsLib（沿用「jv 显式传 java」纪律）

与旧 `D(jv,c)` 同模式，**不要假设 jsLib 里有 `java`**（见 /topics/legado-js-scope-binding.md）：

```js
function MK(jv,c){
 if(!c)return '';
 var b=jv.base64DecodeToByteArray(String(c));
 var key=jv.base64DecodeToByteArray('UHhnYSFoKmU0QFQ4eGZPbQ==');
 var iv =jv.base64DecodeToByteArray('RSZ6IUVIR0xkJGZsaSo4Ug==');
 var C=Packages.javax.crypto.Cipher,
     K=Packages.javax.crypto.spec.SecretKeySpec,
     V=Packages.javax.crypto.spec.IvParameterSpec;
 var ci=C.getInstance('AES/CBC/PKCS5Padding');
 ci.init(C.DECRYPT_MODE,new K(key,'AES'),new V(iv));
 return String(new Packages.java.lang.String(ci.doFinal(b),'UTF-8'));  // ★必须 UTF-8 构造
}
function MN(jv,n,i){ // 章节名，失败按序号兜底
 if(!n)return '第'+(i+1)+'章';
 try{var t=MK(jv,n);if(t&&/[\u4e00-\u9fa50-9]/.test(t))return t.replace(/\s+/g,' ').trim();}catch(e){}
 return '第'+(i+1)+'章';
}
```

★ **坑**：`new Packages.java.lang.String(byte[])` 用平台默认编码会乱码，必须显式 `'UTF-8'`。主协议 `D()` 用逐字节 `fromCharCode` 是因为它要先 trim 控制字符再补 JSON 前缀；正文是纯 UTF-8 文本，直接构造 String 更稳。

### 正文清洗（CDN 里混了各源站站尾广告）

官方 chapter 域返回的是**源站抓取时已混入广告的正文**（如「网为你提供最快的斗破苍穹更新…免费阅读」「请退出转码页面，请下载爱阅小说app」）。逐行剔除、不要整段 replace：

```js
function MC(jv,t){
 var BAD=/免费阅读|最快.*更新|提供最快|请收藏|记住本站|一秒记住|最新网址|手机阅读|加入书签|请退出转码页面|请下载.*app|章节错误.*举报|本章未完.*下一页|www\.[a-z0-9.-]+\.(com|net|cc|la|info|org|tv)|https?:\/\//i;
 var ls=String(t).replace(/\r\n/g,'\n').split('\n'),o=[];
 for(var i=0;i<ls.length;i++){var L=ls[i];if(BAD.test(L))continue;
  if(/^[\s\u3000]*$/.test(L)){if(o.length&&o[o.length-1]!=='')o.push('');continue;}
  o.push(L.replace(/[ \t\u3000]+$/,''));}
 return o.join('\n').replace(/\n{3,}/g,'\n\n').trim();
}
```

**反向验证组不可省**：拿一章「正常无广告」正文过 `MC()`，实测 diff 仅 2 字节（首尾 trim）⇒ 证明没有误删正文。只做「广告被删掉」的正向验证会漏掉「正文被误删」的回归。

---

## 5. 书源结构改动（v2 → v3）

| 项 | v2（降级版） | v3（打通版） |
|---|---|---|
| 章节 URL | 健康域直连第三方站 / 死域走官方 chapter | **统一 `https://chapter.yutinglu.com/{path}`**，彻底废弃第三方站池 |
| 目录域 | `catalog.yutinglu.com` 打分选源 | 不变，但按章节数选最优（catalog 2121 章 > chapter 1778 章） |
| 章节名 | 密文 → 「第N章」兜底 | **`MN()` 解出真实章节名** |
| 正文 | 分类诊断提示（官方加密/403/停放/连接异常…） | **`MK()` 本地解密 + `MC()` 清洗**，兼容 `is_encrypt:false` 明文章 |
| 主协议 D() | 搜索/详情/书源 | 不动 |

`ruleToc.chapterList` 里给每个章节对象同时写 `url / officialPath / siteUrl / isContent`，方便以后换源或排查，不增加运行时请求。

★ **不要写死页码上限 / 不要写死源站白名单**：源站数量、章节数都跟随站点自身数据，打分只按「章节数多者优先」。

---

## 6. 交付踩坑：`save_source` 手敲大 JSON 的转义层数

本次 11KB 单对象 `save_source(format=json)` 报：

```
com.google.gson.stream.MalformedJsonException: Invalid escape sequence at line 1 column 4253 path $.jsLib
```

**根因**：我把 Python 生成好的 `compact.json` 手敲进 MCP 参数时，JS 正则里的 `\d` / `\.` 在「JSON 字符串 → JS 源码」两层转义里少了一层。文件本身是合法 JSON（`json.load` 通过），错在**人工转述**。

★ 与 /topics/delivery-discipline.md 的 261028 事故同源（大参数不可经我转述）。**正确做法**：

```bash
# LAN web 服务直传文件字节，零转义、零截断
curl -sS -m 30 -X POST 'http://192.168.10.7:1122/saveBookSource' \
  -H 'x-legado-token: <当次令牌>' -H 'Content-Type: application/json' \
  --data-binary @compact.json
# → {"isSuccess": true}
```

落库后按交付纪律：① `get_source` 字节级回读（本次 v3 全字段一致）② `debug_source` 全流程 ③ 不再问用户「导入了吗」。

> 备选：dpaste + `legado://import/bookSource` 深链（见 /topics/deeplink-dpaste-channel.md），但匿名公开且不必要；LAN 通道更快更私密。

---

## 7. App 内实测结果（最终判据）

```
debug_source(key="斗破苍穹")  搜索100 / 详情全字段 / 目录1659章(真实章节名「土豆三江访谈感言」) / 正文完整中文
debug_source(key="逆天邪神")  搜索100 / 详情全字段 / 目录2574章(「序章」) / 正文 2854字完整可读
eval_js 抽样 5 章(首/次/中/末) 全部 cjk=true，长度与 num_words 吻合
```

正文从「【本章为官方加密正文…需脱壳】」变成真正的章节内容，**遗留项清零**。

---

## 8. 可复用检查清单

1. [ ] 拿到 APK 先看 `dexEntries / classes` 数量，判断是真脱壳还是只有 stub（4 类 = 没脱壳）
2. [ ] `mt_apk_search(overview, "is_encrypt")` 找加密实体 → 记包名
3. [ ] `mt_apk_search(dex_names, "decrypt|aes|encrypt")` 列候选，**至少两套一起留着**
4. [ ] 对每个候选 `mt_apk_dex_xref(method, dispatch)`，看**调用方是不是正文/目录链路**（`CatalogRepository` / `MkCatalog.getName`），不看函数名像不像
5. [ ] `mt_apk_dex_read_pseudocode` 读调用方 + 解密类，抄出 `mode / key / IV / 编码`
6. [ ] App 内 `eval_js` 对真实密文跑 **A(候选真凶) / B(干扰项) / C(其它协议密文反向)** 三组对照
7. [ ] 批量放大（多书 × 多源站 × 首/中/末章）+ 正常章反向验证清洗无误删
8. [ ] jsLib 用 `jv` 显式传 `java`；`new String(bytes,'UTF-8')` 显式编码；key/IV 用 base64 常量
9. [ ] 大 JSON 落库走 LAN `--data-binary`，绝不手敲 MCP 参数
10. [ ] `get_source` 回读 + `debug_source` 全流程 + 真机阅读实测（换源/翻章）

## 9. 与既有经验的关系

- 主协议逆向 / 降级策略 / 加固壳判定：见《方法-ProxyPin抓包逆向聚合App新协议与Legado解密链路》
- jsLib 三环境绑定差异：见 /topics/legado-js-scope-binding.md
- 大文件落库通道：见 /topics/lan-web-delivery.md、/topics/delivery-discipline.md
- 对照实验驱动逆向：见《方法-对照实验驱动的接口逆向与正文排版》
- **本次新增心法**：「爆破零命中 ⇒ 换样本（脱壳 dex）而不是换 key」「xref 归因优先于函数名直觉」「一个 APK 多套 AES 并存必须逐一套调用链」「解密后正文仍含源站广告，需逐行清洗 + 正常章反向验证」

---

## 11. ★261109 晚：搜索「结果少 / 有一本打不开」= 列表字段名不一致，不是多域名

### 现象
用户报「搜索（东京）只有两个结果，且有个打不开，原 APP 有多个结果，看看是不是有多个域名」。

### 排查与实锤（先排除用户猜测，再定真因）

1. **多域名猜测排除**：脱壳 APK 里确实有第二套基础域 `xiangxung.com`（`ArtConstant.DEFAULT_DOMAIN_URL`、`ArtAppUtils` 内嵌 `https://conf.xiangxung.com/`、`ConfigDomainResolver` 有 `configBaseDomainCandidates` 候选机制）。但：
   - 当前 conf 的 `secondary_domain` 15 个字段**全空**，`urls.domain` 只有 `yutinglu.com`，`data_conf=5`；
   - 实测 `s./book./d.xiangxung.com` **全部 `UnknownHostException`**（DNS 不存在）⇒ 该套域名已退役，当前只有 `yutinglu.com` 在用。
   - `SearchService` 反编译：`GET /{api_version}/1/lists.api` 带 `Domain-Name: s`，只有 `keyword/form` 两个参数（**无 page**），另有 `auto.api`（联想）/`author.api`（按作者），没有第二个搜索域。
   - ProxyPin 抓包：官方 APP 连续点开 8 本详情（706833/631018/636089/662541/730229/759401/571279/647604），全是 `d.yutinglu.com`，且这些 ID 都在同一次搜索的 100 条里 ⇒ 原 APP 拿到的数据与书源是**同一份**，差异只在解析。

2. **真因**：`debug_source` 日志「列表大小:100」但「书籍总数:2」的反差。解密搜索响应后统计字段覆盖率：
   ```
   id      : 1   （只有第 1 条）
   book_id : 99  （其余 99 条）
   ```
   旧 `ruleSearch.bookList` 写的是 `String(o.id).slice(0,-3)+'/'+o.id+'.html'` ⇒ 99 条拼成
   `https://d.yutinglu.com/book/details/v4/undefi/undefined.html` ⇒ 被过滤/去重后只剩 2 条，其中 1 条就是「打不开」的那本。

3. **跨关键词验证**（防过拟合）：斗破苍穹 / 逆天邪神 / 玄幻 / 遮天 / 东京 五个词全部是 `id:1 + book_id:99` 的稳定模式，修复后 5/5 关键词 100/100 有效。

### 修法
```js
var bid=String(o.id||o.book_id||'');
if(!/^\d+$/.test(bid))continue;       // 不产出坏 URL
o.id=bid;                             // 统一字段，封面/详情规则无需分支
o.bookUrl='https://d.yutinglu.com/book/details/v4/'+bid.slice(0,-3)+'/'+bid+'.html';
```

验证：`debug_source(东京)` 书籍总数 **2 → 100**；`book_id` 类书（647604/571279/737217/706833/933835）详情 5/5 通；抓包里原 APP 点过的 737217 详情→519 章→正文全通；`check_source 1/1`。

★ **通用判据**：「列表大小 N」但「书籍总数 ≪ N」时，先统计**每条记录的字段覆盖率**（`id` vs `book_id` vs `bid` vs `bookId`），不要先怀疑域名/限频/去重。站点常把「首条（精确命中）」与「其余（模糊命中）」用不同序列化器输出，字段名不一致是高频坑。修完必须加**数字正则校验**，避免再产出 `undefined` URL。
