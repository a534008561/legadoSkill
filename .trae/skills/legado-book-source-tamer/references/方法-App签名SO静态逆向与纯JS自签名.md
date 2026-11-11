# 方法-App 签名 SO 静态逆向与纯 JS 自签名（青橙小说 261111 蓝本）

> 适用：目标只有官方 App、接口全带 `_s`/`_p` 类签名参数、无网页版可用时的完整破解路径。
> 蓝本：青橙小说 `com.qingcheng.reader` 5.0.1.1（`goway.reader.yueyouxs.com`），
> LT 版 `check_source 1/1` + `debug_source` 全链路全绿（搜索 20 本 / 详情 / 1582&2281 章目录 / 正文 3486 字），
> E 版经 LAN 1125 落库。成品见 `examples/青橙小说_goway.json`（v3，发现页按原 APP 书城结构重组 23 类，登录面板精简为 6 行实用运维）。

## 0. 结论先行（可复用配方）

1. ProxyPin 抓包 → 定位 5 类接口路径；MT 打开 App 的 base.apk → 搜 `"&_p="` 直落签名类 `SecretUrl`。
2. 读 Java 伪代码还原**签名输入拼接式**；导出 `lib/arm64-v8a/libnative-lib.so` 读符号表 → 认出
   `hmac_sha256` / `Des_encrypt` / `base64_encode` / `get_sk` / `get_rk`。
3. **密钥是静态立即数**，无需运行 App：ELF `.rela.dyn` 还原 `.data` 指针表里的单字符片段，
   `get_sk()` 用 `ldr d0,[.rodata]` + `mov/movk` 立即数拼 32 字节 KEY，`get_rk()` 用 8 次 `strcat` 拼 8 字节 DES 密钥。
4. **黑盒校准三步**：`_p` 用 `DES/ECB/NoPadding + get_rk()` 解密 → 拿到 `R0`（设备指纹串）；
   把 `path+encodedQuery+"&"+R0+"&"+排序POST参数(解一层URL编码)` 做 HMAC-SHA256(KEY) → 与明文里的 `sign` 比对；
   命中即定案。再用 `java.ajax` 真实 POST 验证服务端 `code=0`。
5. 书源纯 JS 复现：`javax.crypto.Mac` + `javax.crypto.Cipher` + `java.net.URLEncoder` 全部在 Legado Rhino 可用；
   列表统一 `new Packages.java.util.ArrayList()` + 逐项 `JSON.stringify` + 字段 `$.key`（LT/E 双版本通吃）。

## 1. 签名协议全貌（本次实锤）

`SecretUrl.c(context,url,...,postParams,...)`：

```
_s   = MD5(deviceId + userId)                        // 固定值, 与接口无关
sign = J.j(ctx, path + encodedQuery + "&" + r0 + "&" + b(postParams))
     = HMAC-SHA256(KEY=get_sk(), 上式字符串)          // 输出 64 位小写 hex
r0   = "utId=%s&deviceId=%s&userId=%s&sex=%s&tmpToken=%s&st=%d&uth=%s&oaid=%s&udid=%s"
_p   = URLEncoder.encode( J.f(ctx, r0 + "&sign=" + sign ), "UTF-8" )
     = Base64( DES/ECB/NoPadding(DESK=get_rk(), 明文 + '\u0001' 填到 8 倍数) )
```

- `b(postParams)`：**键名排序** + 跳过空值 + `k=v&`，且值要**先解一层 URL 编码**（`%2C`→`,`）。
- `J.j`=native `h256SK`（`hmac_sha256`，密钥 `get_sk()`），`J.f`=native `denRK`（`des_crypt`→`base64_encode`，密钥 `get_rk()`）。
- `J.k`=`hmd5RK`（`hmac_md5`，生成 `uth=MD5based(token&time)`）—— 这就是为什么 **`time` 不能变**：
  `R0` 里的 `uth` 与旧 `time` 绑定，改 `time` 必须同时重算 `uth`（密钥依赖 APK 签名，纯 JS 不可得）。
  ★**实锤：固定旧 `time=1794411627` + 固定 `R0`，40 分钟后自签任意 body 仍 `code=0` ⇒ 服务端无时间窗口、无重放防护**。
  这类站点直接「冻结一张官方票据，只按 path/query/body 重算 sign」即可书架长生，不要费力去破 `uth`。

### 1.1 密钥常量还原法（无需跑 App）

- `get_rk()` 反汇编是 8 次 `malloc(9)` + `__strcat_chk(dst, [GOT符号], 9)`；
  GOT 里的 `j3..j9/k0` 指向 `.data` 的 RELATIVE 重定位 → `.rodata` 单字符池：
  `s n Y % 1 6 9 j` ⇒ **`DESK = "snY%169j"`**。
- `get_sk()` 是 `malloc(33)` + `str d0,[x0]`（`.rodata 0xb4c0` 前 8 字节 `NiozHhg/`）
  加一串 `mov/movk wN,#imm` 写 `[x0+8..31]`。用 Python `struct.pack('<I', imm|imm<<16)` 逐段还原 ⇒
  **`KEY = "NiozHhg/lMm5ja-DVEV_jzk$,t0B4*$5"`**（32 字节）。
- `_s = MD5("ylms"+"y233108512") = 0D8E1B4226B86B69A867999DE9F2C505` 与抓包完全一致（第二个交叉验证锚点）。
- 校验：把抓包的 `_p` 解密后明文末尾是 `\u0001`（1 字节填充），重加密后与抓包密文 **288 字符字节级相等**。

## 2. 五个以前没出现过的新坑（本次沉淀重点）

### 坑 1 ★★★ `bookUrlPattern` 写宽会让搜索 URL 被判成「详情页」

症状：`debug_source` 日志 `≡链接为详情页` → `┌获取书名 └`(全空) → `︽未获取到书籍`，
但 `≡获取成功` 且 URL 里 `_p` 正确、手动 `java.ajax` 返回 `code=0` 的 20 本书 JSON。

根因：`bookUrlPattern` 初版写成
`https?://(goway|dl|cdn\.p|ads|bi)\.reader\.yueyouxs\.com/.*`，
**把 `/goway/goread/app/search/v4/getBookByKeyword?...` 也匹配了**。
Legado 在 `BookList.kt` 里对「搜索结果 URL 命中 bookUrlPattern」走「搜索直达详情」分支，
于是整页 JSON 被当成一本书的详情页喂给 `ruleBookInfo.init`。

修法：正则**只匹配书籍详情 URL 的精确形态**，绝不覆盖任何接口路径：
```
https?://(?:goway|dl|...)\.reader\.yueyouxs\.com/goway/goread/app/book/detail\?bookId=[0-9]+.*
```
★ 通用铁律：**纯 API 书源的 `bookUrlPattern` 必须精确到「详情页路径 + 主键参数」，不能图省事用 `.*` 覆盖整域**。
凡是 `search/section/toc/content` 也在同一域的，宽正则必炸。

### 坑 2 ★★ 搜索关键词**必须原文中文**放进 POST body，URL 编码形式反而签名错误

`b(postParams)` 对值做**一层 URL 解码**后再拼进签名串。OkHttp 发 body 时会把中文编码成 `%E4%B8%9C...`，
服务端拿到后先解一层成中文再校验。所以书源里：
- ✅ `body = 'keyword=东京&page=1&psize=20&withRecommend=1'`（JS 字符串里就是中文）→ `code=0 LIST20`
- ❌ `body = 'keyword=%E4%B8%9C%E4%BA%AC&...'` → 签名错误
（注意这与「签名输入里 POST 值要解一层编码」不矛盾：解一层的是**抓包看到的已编码 body**，
而书源构造 body 时应交给 OkHttp 去编码，JS 侧保持原文。）

### 坑 3 ★★★ OSS 签名直链在 Legado `java.ajax` 恒 `SignatureDoesNotMatch`，改 `ossSwitch=0` 走站内直链

`downloadChapter` 默认 `ossSwitch=1&isOssed=1` 返回阿里云 OSS 直链
`yyoss-book.oss-cn-shanghai.aliyuncs.com/wap%2F...?Expires=..&OSSAccessKeyId=..&Signature=..`。
- 沙盒 Python `urllib` 同一 URL → **200 / 10282 字正文**；
- Legado `java.ajax` 同一 URL → **403 XML `<Code>SignatureDoesNotMatch`**；
- 试遍 `%2B`→`+`/`%252B`/`%2F`→`/`/`URLEncoder` 重编 / 加 UA 全部失败 ⇒ 不是编码，是 Legado HTTP 栈与 OSS 的组合问题。
- ✅ **正解：`downloadChapter` 传 `ossSwitch=0&isOssed=0`** → 返回**站内直链**
  `dl.reader.yueyouxs.com/content/getChapterContent?...&signKey=...`，`java.ajax` 直出 3486 字正文，3 次重复稳定。
- 附带发现：`book/detail?needChapter=1` 会内联 `data.book.chapterInfo.content`（首章 3484 字），可作应急兜底。

★ 通用铁律：**正文接口若同时提供「OSS/CDN 签名直链」与「站内代理直链」两种模式，优先选站内直链**；
遇到 `SignatureDoesNotMatch` 先做「沙盒 vs App」对照实验定性，不要死磕 URL 编码。

### 坑 4 ★★ `loginUrl` 环境不加载 `jsLib`，面板函数必须内联签名库副本

`eval_js` 绑定书源时只加载 `jsLib`（`QC_sign` 可见），**`loginUrl` 里的函数一个都不可见**；
而真机登录面板/action/viewName 环境执行的是 `"$loginJS\n$jsStr"`，**不含 jsLib**。
所以面板里的「签名票据自检」按钮若引用 `QC_hm/QC_ec/QC_R0`，真机点按必 `ReferenceError` 静默失效。
修法：`loginUrl` 字段 = `sign_lib.js 全文` + 面板函数，且**不引用任何 jsLib 追加函数**（`QC_url/QC_opt` 也要改成内联 `QC_sign`+`JSON.stringify(opt)`）。
探针法：`eval(String(source.getLoginUrl())); QC_selfTest(java);` 在 eval_js 里模拟 action 环境，逐函数验证（含 `login()` 必须存在）。

### 坑 6 ★ Python 生成 `@js` 规则时误把 `json.dumps` 写成字面文本（v3 发现重组踩坑）

用 Python 拼装书源 JS 规则字符串时，写成
`"...\n  var S='+json.dumps(SECS,ensure_ascii=False)+', C='+json.dumps(CLS)+';\n..."`
（少了外层引号闭合），结果 JS 里真的出现 `var S=+json.dumps(...)+...`，
`S` 变成一个 73 字符的乱码字符串 → `exploreUrl` 生成 73 个 `title='+'` 的假 kind
→ `check_source` 报 **「发现失效」**。
★ 探针法：`eval_js` 里 `var kinds=JSON.parse(String(eval(source.getExploreUrl().replace(/^@js:\s*/,''))));`
直接打印 `kinds.length / kinds[0].title / kinds[0].url`，一眼看出是「数量不对 + 首标题是 '+'」。
★ 铁律：**所有由 Python 拼进 JS 的数组/对象必须先 `json.dumps` 成字面量再拼**，
生成后用 `eval_js` 回读 kinds 数量与首元素做门禁，别等 check_source 才暴露。

### 坑 5 ★ `exploreUrl` 的 `@js` kinds 里不能嵌 `{{page}}` 做签名分页

`AnalyzeUrl.initUrl()` 顺序 = `analyzeJs()` → `replaceKeyPageJs()` → `analyzeUrl()`，
即 **JS 先跑，`{{page}}` 后替换**。若签名 URL 里留 `{{page}}`，签名算的是字面量、请求发出的是数字 → 签名错误。
本次 v3 方案（按用户要求重组为原 APP 发现页）：`section/v4/book/list` 出推荐 5 榜单+火爆完本 3227+最新好书 3228，`classify/search`（`classify=11/21&classifySecond=xxxx&page=1&psize=20`，服务端返回 `count` 724/140 等明确可翻页）出男频 8 类+女频 8 类，共 23 个 kind；`ruleExplore.bookList` 用 `@js` 同时兼容 `data=[...]` 数组与 `data.list=[...]` 两种响应形态。每个 kind 固定 `page=1` 但不写死翻页上限；
真要翻页的榜单（2747/2748/2751）实测 `page=2` 内容不同，可另建 kind 或走 `nextExploreUrl` 内容指纹终止。
★ 符合用户要求：翻页终止一律跟随站点自身信号（内容指纹重复），不写死页码上限。

## 3. 双版本兼容定式（复用既有结论，本次再验证）

- 列表 `@js:` 一律 `var list=new Packages.java.util.ArrayList(); list.add(JSON.stringify({...})); return list;`，
  字段规则统一 `$.key`。E 版 `AnalyzeRule.getElements` 无 `NativeArray→ArrayList` 分支，JS `[]` 必 ClassCastException。
- `jsLib` 只放**纯函数骨架**（`Packages.javax.crypto.*` / `java.net.URLEncoder` 可用），
  绝不引用 `java/source/book/result/baseUrl` 等规则环境绑定；需要 java 时由规则显式传参 `QC_post(...,java)`。
- `searchUrl` / `exploreUrl` 的 `@js:` 返回 `URL + "," + JSON.stringify({method,headers,body})` 形态，
  Legado 正确带 POST body 与自定义 UA（`okhttp/4.10.0` 必须，已在 `header` 钉死）。
- `loginUi` 用 **V1 静态 JSON 数组 + `viewName` JS 表达式动态文本**（E 版唯一可用形态）；
  `loginUrl` 必须有 `function login(){return 'ok';}`，否则点右上角 √ 抛 `Function login not implements!!!`。
  每个按钮 `QC_tip(jv,msg,key,val)` 做 toast + longToast + `jv.put` + `reLoginView` 三重保险，
  测速结果 ms 写进 `qcSpN` 由 `QC_btnLabel(i)` 的 viewName 回显，最快线路加 ⚡。

## 4. 风控与登录定性（本次实锤）

- **不需要登录**：全部接口走匿名游客 `userId=y233108512`，`autoLogin` 只是上报；
  搜索/详情/目录/正文/发现 `code=0` 全程无 Cookie 依赖。故不写登录校验 `loginCheckJs`，
  只在面板提供「🔍 检查登录状态」按钮（显示「游客态可用」+ 票据状态 + 延时 ms）。
- **搜索间隔**：未主动探测搜索频率（遵守用户要求）。实测连续两次不同关键词 debug 间隔 > 10 分钟均正常；
  已设 `concurrentRate=1500`（全局 1.5s 节流）并保留「搜索请勿频繁」提示，不写死更激进的探测。
- **网址发布页**：APK 内只有固定官方域（`goway/dl/cdn.p/bi/ads/reader2/h5.reader.yueyouxs.com`），
  **无发布页线路轮换**。实测只有 `goway` 承载签名接口、`dl` 承载目录/正文，其余备用域返回 404/MethodNotAllowed。
  ★**用户明确要求「去掉登录界面无用路线和发布页路线」**⇒ v3 面板精简为 6 行：状态行(viewName) / 双线路状态行(viewName) / 检查登录状态 / 测试官方API延时 / 测试目录·正文线路 / 签名票据自检；ms 写入 `qcSpeed`/`qcSpeedDl` 由 viewName 回显，不保留任何假切换按钮。

## 5. 交付闭环（本次实操）

1. `build_source.py` 用 Python `json.dump` 生成完整书源（避免手抄转义），`sign_lib.js` 单独文件便于 `node --check`。
2. **LAN 双通道落库**：`POST http://192.168.10.7:1122/saveBookSource`（头 `x-legado-token: a7894563`）
   与 `1125`（E 版免令牌）都 `isSuccess:true`；`get_source` 回读确认 jsLib 3389 字符无损。
3. `check_source` 1/1 通过；`debug_source` 用「东京」「斗破苍穹」两个关键词各跑一次全链路全绿；
   `::签名URL` 模式验证发现页 50 本 → 详情 → 459 章 → 正文。
4. 登录面板用 `eval_js` 模拟 action 逐函数验证：`QC_selfTest` 自检通过、`QC_checkLogin` 游客态 OK、
   `QC_fetchPub` 取 5 条、`QC_testMs` 只 goway 83ms 其余「不可用」、`QC_sw0` 切换、`QC_viewPub` 回显。
5. 成品 22.9KB 走 LAN（大文件通道），未用 `save_source` 手打（避免整体覆盖截断）。


## 6. ★★★ 签名绑定 POST body 的 API 如何实现 Legado 原生无限翻页（v4 新增）

**矛盾**：本源签名输入 = `path+encodedQuery+"&"+R0+"&"+排序POST参数`，任何请求参数变了都要重算 `_p`；
而 Legado 发现页翻页靠 `{{page}}`，`initUrl()` 顺序 = `analyzeJs()` → `replaceKeyPageJs()` → `analyzeUrl()`，
`@js` 先跑、`{{page}}` 后替换 ⇒ 把 `{{page}}` 留在签名 URL 里必「签名错误」；
把 `{{page}}` 放进 `UrlOption.body` 又**不会被替换**（源码 `replaceKeyPageJs` 只处理 ruleUrl，POST body 原样发出）。

**两步解法（LT/E 通用，源码级实锤）**：

1. **把页码挪到 URL query**：服务端对 `classify/v352/search` 认 query 里的 `page=N`（**同名参数覆盖 body 的 page**）。
   对照实验：body 恒 `page=1` 只改 `QC_sign(path,'page='+p,body)` 的 queryExtra，p=1/2/3/4 首本
   `最强末世进化 / 末日：零元购 / 神级刮刮卡 / 恶犬天下` 完全不同；
   而无关参数 `qcpage=p` 四次全同 ⇒ 不是「签名变化导致乱序」，是 query `page` 真生效。
2. **`UrlOption.js` 在发请求前按真实页码重签**：官方 `AnalyzeUrl.analyzeUrl()` 里
   `option.getJs()?.let { evalJS(jsStr, url)?.toString()?.let { url = it } }` —— `js` 返回值**只覆盖 URL**（不能带新选项 JSON，
   实测返回 `URL,新opt` 被当 URL 整体发出 ⇒ `鉴权参数无效`）；但 `evalJS` 绑定含
   `page`/`key`/`java`/`source`/`baseUrl`/`result`/`infoMap`，且走 `getShareScope`（**jsLib 的 `QC_sign` 可用**，已探针实锤）。
   `result` 传入的是当前 url（`{{page}}` 已替换），所以从 `result` 正则读页码比 `page` 绑定更稳（`eval_js` 裸环境 page=null）。

   kind URL 形态：
   ```
   https://host/path?page={{page}},{"method":"POST","body":"...page=1&classifySecondList=1100",
     "js":"(function(){var pg=1;try{if(page!=null)pg=parseInt(String(page))||1;}catch(e){}
            try{var m=String(result).match(/[?&]page=([0-9]+)/);if(m)pg=parseInt(m[1])||1;}catch(e){}
            return 'https://host'+QC_sign('/path','page='+pg,'固定body');})()"}
   ```
   body 固定 `page=1`，服务端用 query `page` 覆盖 ⇒ 翻页生效、签名有效、`{{page}}` 跟随站点自身、不写死上限。
   实测 `debug_source ::` 带 page=2 的 kind → 20 本《阎王下山》→ 2640 章 → 正文全绿；
   eval_js 直接把 `{{page}}` 替换成 1/2/3 三次首本各异。

★ **通用铁律**：`UrlOption.js` 是「签名类 API 接入 Legado 原生分页」的唯一正解——它发生在 `{{page}}` 替换之后、
请求发出之前，且能拿 jsLib；别试图在 `exploreUrl` 的 `@js` 里预生成多页签名（page 还未知）。

## 7. ★★ 发现页 select 男女频切换：infoMap 必须优先于 java 缓存（v4 新增）

`exploreUrl` 的 `@js` 环境注入 `infoMap`（持久化 Map，按书源存）。select 行：
`{title:'频道',type:'select',chars:['男频','女频'],default:'男频',
 action:"java.put('qcChannel',infoMap['频道']); java.refreshExplore();"}`。
- `java.refreshExplore()` 清 kinds 两级缓存并重绘（猫眼 v5 实锤比 `reUiView` 可靠），`eval_js` 裸环境
  `refreshExplore=function` / `reUiView=undefined` ⇒ 不要在 action 里用 reUiView。
- ★ **优先级坑**：v4 首版写成「先读 infoMap，再用 `java.get('qcChannel')` 兜底覆盖」，
  结果**切到女频后第一次刷新仍是男频**（缓存旧值把新 infoMap 盖了）。四场景对照实锤：
  `im=女频/cache=男频` 返回男频 ⇒ 错。正解 = `hasIm` 布尔，infoMap 有值就直接定案、
  只有完全没值时才读 java 缓存，最后兜底 `'男频'`。修正后四场景全对。
- 按频道生成 39 个 kind（男频 classify=11 / 女频 classify=21），`check_source 1/1`。

## 8. v4「更多列表」来源（ProxyPin 第二轮抓包 1000 条）

用户实际操作原 APP 分类页翻到 page=2/3/4，抓包实锤真实接口不是 v3 用的 `classify/search`，
而是 **`classify/v352/search`**，body：
`tagList=&classify={11|21}&psize=20&fullFlag={-1|0|1}&tagTypeId=0&orderBy={readers|cpsUpdateTime|createTime}&page=N&classifySecondList={二级分类id}`。
另从 `ActionUrl` 常量表挖到并实测可用的列表：`rank/v4/index`（20 本/频道，`data.bookList`）、
`clsTag/getBookList`（8 本/频道，`data[]`）、`section/v4/recommend/list`（10 本，`data.list`）、
`rank/index`（含 classifyList/topNavList 配置）。`ruleExplore.bookList` 扩展为四形态兼容。


## 9. ★★ 发现页分类折叠（91Hub 范式）与「标题去频道前缀」（v5 新增）

用户要求「优化发现规则，去掉例如（都市人生）前面男频两字；热度更新新书收拢到都市人生标题下」。

- **折叠条** = `{title:(isOpen?'▾ ':'▸ ')+纯分类名, url:'', type:'button', action:..., style:{layout_wrapBefore:true}}`；
  子项（热度/更新/新书）只在 `isOpen(key)` 时 push，标题**不带频道前缀**、不带分类名（避免「男频·都市人生·热度」长串）。
- **action 三件套**（技能库《方法-发现页本源搜索框与可伸缩分组列表》实锤）：
  `var c=JSON.parse(String(source.getVariable()||'{}'))||{}; c.__K__=c.__K__?0:1; source.setVariable(JSON.stringify(c)); java.refreshExplore();`
  ★**必须解析原串只翻转本次 key**，不能 `c={}` 覆盖用户已有变量；★**必须 `java.refreshExplore()`**（少这步点了没反应）。
  折叠键按频道+分类 ID 命名（`qc_11_1100`/`qc_21_2100`），男女频状态互不串。
- **求值端** `isOpen(k,def) = (cfg[k]===undefined)?def:(cfg[k]!==0)`；`getVariable` 整段 try/catch 防 `check_source` 裸环境抛错。
- ★**默认态设计**：折叠全收起时 kinds 仍要有**常驻非空 url 首项**（否则 `CheckSourceService` 报「发现规则为空」）⇒
  7 榜单 + 3 新列表 + 3 状态筛选常驻（均有 url），分类折叠条 url 空；另让**第一个分类默认展开**（`def=(i===0)`）提升首次体验。
  实测默认 26 项 / 16 url / 「▾ 都市人生」+「热度·更新·新书」3 子项，切女频自动变「▾ 现代言情」。
- **布局**（用户此前纠正过的铁律）：子项一律 `style:{}`（零 basis/零 grow，Legado 自动按文字宽度折行），
  只给 select/状态行/折叠条写 `layout_wrapBefore:true` 独占整行；**不要手工算字数/basis**。
- 真机翻转实测：`{}` → 点击 `{"qc_11_1100":1,...}` → 重绘 26 项、标题 ▸→▾、+3 子项 → 再点 `{"qc_11_1100":0,...}` 收起；
  诊断后 `source.setVariable('{}')` 清理污染。`check_source 1/1`、五关键词搜索全链路全绿。


## 10. ★★ 情节/角色标签规则 + 满格分组标题（v6 新增）

用户要求「不需要折叠，例如都市人生（满格）下面，热度更新新书；另：增加情节，角色标签规则」。

- **去掉折叠**：不再用 `source.getVariable/setVariable` 与 ▾/▸，改为**满格独占整行的纯标题行**：
  `{title:'都市人生', url:'', type:'button', action:"java.toast('都市人生')",
    style:{layout_flexBasisPercent:1, layout_wrapBefore:true, layout_flexGrow:0}}`
  其下**直接常驻**「热度/更新/新书」3 个 `paged()` 子项（不再判 isOpen）。
  ★`type:button` + url 空**不会进分类 Tab 栏**（Tab 只收 type==url 且 url 非空），`check_source` 靠常驻的
  7 榜单/3 新列表 url 项通过（仍需至少一个非空 url）。子项 `style:{}` 自动宽度。
- **标签数据源**：`classify/v4/index?classify={11|21}` → `data.list[男生|女生].tagTypeList` =
  `[{id:1,name:'情节',list:[{id,name,type:1},...]},{id:2,name:'角色',list:[...]}]`；
  男女频各 **12 情节 + 12 角色**（男：乡土/系统/重生…、高手下山/赘婿/兵王…；女：甜宠/先婚后爱…、总裁/萌宝/女强…）。
  `classify/index?classify=21` 的 `items.tagList/roleList` 也能拿到（带 id）。
- ★★ **标签参数不是 ID 是中文名**：把标签 `id` 塞 `tagList=520` 返回 `count:0`；
  ProxyPin 第三轮抓包（用户实操 17:36，requestSize 132B vs 分类页 100B）实锤真实 body
  `tagList=%E6%89%93%E8%84%B8%E9%80%86%E8%A2%AD&classify=41...` ⇒ **`tagList=标签中文名`**。
  实测 `tagList=乡土/系统/赘婿/甜宠/总裁/打脸逆袭` 分别 `count=166/748/204/1197/1353/54` 全出 20 本；
  `tagTypeId` 填 0/1/2 结果一致（服务端按名字匹配）。
- **中文进签名**：OkHttp 把 `tagList=系统` 编码成 `%E7%B3%BB%E7%BB%9F`，签名 `QC_dec1` 解一层成 Latin-1 字节串，
  服务端校验链一致 ⇒ 中文标签签名正常、翻页正常（情节[系统] page=1/2/3 首本各异）。
- 终态 75 项/频道：61 url 项 / 51 带 `{{page}}` / 12 满格标题；`check_source 1/1`；
  角色[赘婿] `debug_source` 20本→2333章→正文全绿；五关键词搜索全链路全绿。


## 11. ★ 四频道（男频/女频/短篇/图书）接入（v7 新增）

用户要求「增加短篇，图书频道」。原 APP `bookStore/v4/getMain` 本就是 4 频道，`classify/index`/`classify/v4/index`
的顶层 id 分别是 **11 男频 / 21 女频 / 41 短篇 / 31 图书**。

- **select 扩成 4 项**：`chars:['男频','女频','短篇','图书']`，`CHS` 字典按频道给
  `c`(classify 号)/`cls`(二级题材)/`plot`(情节标签中文名)/`role`(角色标签中文名)/`common`(是否挂通用榜单)。
- **短篇 41**：`classify/index?classify=41` → 7 题材（4100 现实情感/4102 家庭婚姻/4103 热血青春/4104 治愈成长/4105 奇闻怪谈/4106 悬疑脑洞/4107 古风言情）+ 9 情节标签（出轨/反转/婚姻/家庭/打脸逆袭/治愈/白月光/虐恋/重生），**无角色标签**；`classify/v4/index` 的 tagTypeList 只列 3 个（家庭/打脸逆袭/虐恋）⇒ **以 classify/index 的 tagList 为准更全**。
- **图书 31**：6 题材（3104 学习强国/3102 文学小说/3103 古代典籍/3105 名家名作/3101 出版读物/3108 史家专著），**无情节/角色标签**。
- ★★ **通用列表不能无脑挂全频道**：实测 `rank/v4/index?classify=41/31` 与 `clsTag/getBookList?classify=41/31`
  返回的是**与男频完全相同的书**（首本都是《麒麟神相》）⇒ 接口忽略 classify。故 `common` 只给男/女频，
  短篇/图书只挂该频道专属的分类/标签/状态（这些走 `classify/v352/search` 且认 `classify=41/31`，实测出书正常）。
- ★ **短篇/图书仍要有常驻非空 url 首项**：它们没有榜单，`check_source` 靠「3 状态筛选」与「分类热度」的 url 项通过
  （`CheckSourceService` 只要求 firstOrNull 非空 url）。
- 实测：短篇 45 项/33 url 全带 `{{page}}`、图书 31 项/21 url 全带 `{{page}}`；短篇[打脸逆袭] p1/p2 首本不同、
  短篇[现实情感·热度] p1/p2 不同、图书[学习强国·更新] 出 6 本；短篇[现实情感·热度]
  `debug_source` 20本《始乱终不弃》→35章→正文全绿；4 频道各有首个 url 项出书、`check_source 1/1`。


## 12. ★ 榜单名必须取 `getMain` 的 `items` 模块 displayName，不能按首本书名起（v7.1 校正）

用户纠正「没有离婚前夜榜和抬龙棺榜吧，参考proxypin抓包数据」——我 v3~v7 把
`sectionId=2748` 首本《离婚前夜，顾总的小娇妻重振妻纲》起成「离婚前夜榜」、
`2751` 首本《抬龙棺》起成「抬龙棺榜」，**都是编的**。

- ★ **`bookStore/v4/getMain` 的 `data[推荐].list[].items` 是嵌套 JSON 字符串**，必须
  `json.loads(items)` 才能拿到模块级真实名；只遍历 `bookId/sectionId` 那些书对象
  是拿不到 `displayName` 的（它们的 name 为空）——这正是我最初漏掉的根因。
- 真实映射（ProxyPin 抓包实锤）：
  `3066=热门风向标`、`3068=满级神作`、`2747=热门追更榜`、
  **`2748=完结精品库`**、**`2751=异军突起`**；
  金刚区 `jumpUrl=yueyou://bookStore/section/3227→火爆完本`、`3228→最新好书`。
- 第四轮抓包（用户点「完整书单/更多」18:04）确认只有这 5 个 sectionId
  （body 带 `data={"8001":"..."}&priorityBookIds=...` 个性化参数），无更多榜单 id。
- ★ 通用铁律：**发现页分类/榜单标题一律取站点自身字段**（`displayName`/`name`/`jumpUrl`），
  禁止按返回的首本书名臆造；用户说「参考抓包数据」时先回到原始响应取权威字段。
