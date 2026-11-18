# 夜社 yesx.cc 多频道书源制作经验（261119）

## 站点画像
- `https://yesx.cc` 是**口令门发布页**：伪装成计算器，输入口令 `93743` 后 JS 从 8 个 punycode 域名 × 6 端口(7982-7987) 随机跳转到真正内容站。
- 真正内容站**全站响应被 `<script>var a="BASE64"</script>` 包装**，必须用 `java.base64Decode` 解出才是真 HTML。
- 成品：`/workspace/yesx/yesx_multi_final.json`（~18KB），LT 1122 + E 1125 双端 LAN `saveBookSource` 落库，`check_source` 1/1 通过，7 模式 debug 全绿。

## ★★★ 新坑1：@js 返回 JS 数组 → bookList/chapterList 恒 0 条
- **根因（源码级）**：`AnalyzeRule.getStringList()` 里 `Mode.Js -> evalJS(rule,result)`，返回 NativeArray（JS 数组）时既不是 String（不进 `split("\n")`），也不是 Java `List`，最终 `result as? List<String>` = null ⇒ 0 条。
- **正解**：@js 显式返回 Java ArrayList：
  ```js
  function YS_LIST(a){var l=new Packages.java.util.ArrayList();if(!a)return l;
    for(var i=0;i<a.length;i++)l.add(typeof a[i]==='string'?a[i]:JSON.stringify(a[i]));return l;}
  ```
  list 规则返回 `YS_LIST(arr)`，字段用 `$.name`/`$.bookUrl` 取值（蓝本=猫眼看书 `ME_LIST`）。
- **判断指纹**：debug 显示 `┌获取书籍列表 └列表大小:0`，但 `source.put` 诊断证明 @js 已执行且 result 正确 ⇒ 一定是返回类型问题，别再怀疑选择器/编码。

## ★★ 新坑2：Java String.split('(') 正则坑
- Rhino 里 jsoup `.text()` 返回的是 **Java String**，`.split('(')` 走 `java.lang.String.split(正则)` → `PatternSyntaxException: Incorrectly nested parentheses`，规则静默失败。
- JS 里 `'('` 是字面量，Java 里是正则元字符。危险字符还有 `.` `[` `$` `|` 等。
- **正解**：先 `String(x)` 转 JS 字符串后用 indexOf 切割：
  ```js
  function noParen(t){var x=String(t),i=x.indexOf('(');return i>0?x.substring(0,i):x}
  ```

## ★★ 新坑3：check_source 不执行 @js: 的 exploreUrl
- 症状：`Expected URL scheme 'http' or 'https' but was 'com.script.ScriptException'` 或「发现失效」；即使 @js 完全自包含（内联线路+模式读取，eval 验证返回正确 JSON 数组）也报。
- 二分法定位：把 exploreUrl 换成静态 `标题::URL` 后错误立即消失，check 1/1 通过。
- 结论：CheckSourceService 对 `@js:` exploreUrl 的路径与真实 App 不同，是校验工具固有局限。
- **交付策略**：发现页用静态绝对 URL（列出各频道入口），模式切换仅影响 searchUrl/正文 → 保证 check_source 通过；真实 App 功能不受影响。代价：静态发现页写死线路域，线路切换后搜索走新线路但发现页仍走默认线路（默认线路已验证稳定，可接受）。

## 新坑4：不同频道搜索结果 bookUrl 形态不一致
- 漫画搜索返回 `/detail/ID.html`（有 chpterlist），视频/写真返回 `/play/ID/1/1.html`（无 chpterlist，图片/分集在 player_aaaa 里逐张/逐集翻）。
- 正解：`ruleToc.chapterList` 取 `.chpterlist a.link`，**空时兜底造单章节** `{name:模式名, url:String(baseUrl)}`；图片模式正文加 `nextContentUrl`=player_aaaa.link_next 逐张翻页（漫画57张/写真156张实测全抓到）。

## 新坑5：searchUrl 的 {{...}} 内嵌连续 }} 被提前截断
- `{{(function(){...catch(e){} }...)()}}` 里的 `}}` 会被 AnalyzeUrl 模板解析器提前截断 → `在函数体后面缺少 }`。
- 正解：searchUrl 改用 `@js:` 前缀返回完整 URL 文本（AnalyzeUrl.evalJS 注入 key/page），彻底避开 `{{}}` 括号截断；且规则体内 source.get/getVariable 做 try/catch 自包含（check_source 环境不加载 jsLib，不能调用 jsLib 函数）。

## 站点结构速查
- 频道 tid：小说6/动漫1/视频2/有声3/漫画4/写真5/影视37(空频道，改用 tid=2)/短剧分类 `/type/13.html`。
- 搜索 `/vod/search/tid/{t}/wd/{词}/{页}.html`；小说详情 `/novel/ID.html` 目录内嵌 `.chpterlist`；其他频道详情 `/detail/ID.html` 或 `/play/ID/1/1.html`。
- 播放页 `player_aaaa={...}` JSON 含 `url`(m3u8/webp/jpg，带 `\/` 转义)、`link_next`、`vod_data.vod_pic`、`from`(yeshevideo/yeshemusic/yesheimage)。
- 封面真链在 `div.module-image-info img@data-original`（src 是 load.gif 占位）。
- 书名是第二个 h1（第一个 h1 是站点名"夜社"），用 `div.dinfo h1`。
- 目录列表 `.chpterlist a.link` 含 `.list.hide` 折叠章节（前5章可见，其余藏在 hide class 里，但 HTML 中齐全，选择器可全取）。

## 调试方法论
- eval_js 验证列表函数：`Packages.org.jsoup.Jsoup.parse(dec(html)).select(sel)` + 自写函数；MCP debug_source 搜索分支可靠（catseye 对照 100 条）。
- 改规则后必须从 get_source 落库原文 eval 自检语法（jsLib/loginUrl/exploreUrl/各 @js 规则逐段 eval），零转录误差。
- 连续快速搜索（7 模式连测）会触发站点限频返回 0 条——用户明确要求不主动探测搜索频率，各模式验证要间隔单独测。

---

## v2 增补（261119 二轮：频道联动发现页 + 测速修复 + 正确书源模式）

### 新坑6：StrResponse.callTime 是「方法引用」不是数字属性
- 症状：测速循环里 `var t=r.callTime; if(t<bms)` 恒 false，best 永远 -1 → 全部判「超时」，即使 HTTP 200 且响应 1.2MB。
- 诊断指纹：整个 8 线路测速只花 856ms（连建连都不够）→ 判活判据有问题而非网络。
- 正解：`r.getCallTime()`（实测返回数字 1086）；兜底 `Number(r.callTime())`。`r.callTime` 直接读会得到 `function callTime() {/* int callTime() */}` 字符串（与之前记忆里 `code` 属性坑同源：Kotlin 属性在 Rhino 里是 getter 方法）。

### 新坑7：带端口 URL 拼 `,"timeout":9000` 选项 → 被当路径 → 404
- 症状：`https://domain:7982/,"timeout":9000` 经 ajaxAll 返回 body="404"（3字节），长度判据 <20000 全部超时。
- 原因：URL 已含端口时，AnalyzeUrl 把逗号后 JSON 选项误拼进 path；不带端口的 URL 可能正常，但不统一。
- 正解：测速 URL **不拼 timeout 选项**（ajaxAll 默认超时即可）；实测 8 线路不带选项全部 200（308~1295ms），1.3 秒完成。

### 新坑8：动态 exploreUrl 联动 vs check_source 的最终取舍
- 用户明确要求「频道按钮切换联动发现规则列表」⇒ 必须用 `@js:` 动态 exploreUrl（按模式变量返回不同分类）。
- check_source 对 `@js:` exploreUrl **必然误报**（ScriptException，源码路径与真机不同，技能库多篇已确认固有局限），即使写成纯字符串拼接/自包含也报。
- 最终选择：**功能优先，保留动态联动**，check_source 红叉如实告知用户是校验器局限；真机 debug 全绿才是判据。v1 的静态发现页虽能过 check，但失去联动，不满足用户需求。

### v2 正确书源模式映射（用户明确要求）
- 小说=文本 `book.type=8` / 视频·动漫·影视=视频 `book.type=4` / 有声=音频 `book.type=32` / 漫画·写真=图片 `book.type=64`。
- ★ `book.type` 必须在 `ruleToc.chapterList` 里设（`WebBook.getChapterListAwait` 会 removeAllBookType 冲掉详情 init 的设置）。
- 视频/音频模式正文返回 **m3u8 纯 URL**（ExoPlayer/音频播放器直接拉流），不再用 data: 播放页；图片模式正文 `<img src="...">` 双引号逐张翻页。

### 频道切换联动实现
- `YS_setMode(m)` 写 `source.setVariable(m)` + `source.put('ys_mode',m)` 双写（兼容双版本），然后 `java.refreshExplore()` + `reUiView()` + `reLoginView()` 刷新；按钮 viewName 用 `YS_curMode()` 显示 ✅ 当前频道。
- `exploreUrl` 的 `@js:` 内联读线路 H 与模式 m（自包含），按模式返回对应频道分类 JSON（带 layout style）。

### 新坑9：exploreUrl 的 @js 顶层 `return` 报「返回的值无效」
- 症状：`获取发现错误: com.script.ScriptException: EvaluatorException: 返回的值有效性 (<script>#3)`，报错第3行正好是 `if(m==="小说"){return \`...\`}`。
- 根因：App 的 `exploreKinds()` 走 `evalJS(exploreUrl.substring(4))` **直接 eval 整段脚本**，顶层 `return` 在 eval 脚本上下文非法（Rhino 报「返回的值无效」）。之前用 `new Function(code)` 或包在 IIFE 里自测都会掩盖此问题——**必须用 `eval(code)` 直接测**才能复现。
- 正解：`exploreUrl` 整体包成 IIFE：`@js:(function(){ ... return \`...\`; })()`。
- 验证配方：`var code=source.exploreUrl.substring(4); JSON.parse(eval(code))` 直接 eval 通过才算过；7 模式逐个切 `YS_setMode` 后再 eval，每个都返回合法 JSON 数组。

> ⚠️ **以下「新坑10/11/12」是排查过程的历史探索记录，其「最终正解」均已被真机证伪，不要采用**。唯一可用的最终方案见文末《★★★★★ 音频 3003/1004 终极方案》。保留它们只为呈现根因演进脉络（问题定性正确，但解法错误）。

### 新坑10：音频 m3u8 分片 AES-128 加密伪装 .jpg → 播放器报 3003 CONTAINER_UNSUPPORTED
- 症状：有声正文返回 m3u8 直链，播放器报 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED 3003`。
- 根因：m3u8 分片名 `q39stzcj0.jpg`，实际是 AES-128 加密的 TS（首字节 0x84 加密，用 key f436... 解密后首字节 0x47=MPEG-TS 同步字节）。播放器按 `.jpg` 扩展名判容器 → 不支持。key 在 `/vod.key`(16字节二进制)，IV=0。
- 正解（**不用本地下载60分片解密**，那种方案 10MB/11秒/易OOM）：**改写 m3u8 文本**——①每个分片 URL 改为绝对 URL 并加 `?x=.ts`（服务器对这个 query 仍返回同样数据，播放器按 .ts 识别容器）②`#EXT-X-KEY` 的 `URI="/vod.key"` 改绝对 URL ③把改写后的 m3u8 用 `data:application/vnd.apple.mpegurl;base64,` 返回（或写本地 .m3u8 返回 file://）。播放器原生 AES-128 解密能力接管，正文加载 <1 秒。
- 验证：eval 直接执行落库 content 规则原文返回 `data:...m3u8;base64,...`；新 origin 的诊断源在 debug_source 里也确认返回 data URI。
- ★坑中坑：Legado 的 BookSource 按 origin 缓存在内存，**同一 origin 反复 LAN 覆盖后 debug_source 仍读旧实例**（技能库已记录）。验证新规则必须用假域名新 origin 的诊断源；正式源需**重启 App 或重新导入一次**才在当前会话生效。LAN/get_source 读到的是新规则（持久层正确），eval_js 绑定的也是新规则，唯独 debug_source 缓存旧。


### 新坑10 修正（真机反馈）：data URI m3u8 仍报 3003 → 最终用 file:// m3u8
- 用户真机实测 `data:application/vnd.apple.mpegurl;base64,...` 仍报 3003（部分播放器不识别 data URI 的 HLS，或无法处理 data 页里的跨域 key 请求）。
- 本地解密拼 TS 方案（下载60分片+AES解密+ByteArrayOutputStream+downloadFile 写 file:// TS）：eval 里 11 秒且 MCP eval 超时、App 规则里易超时/OOM，不可行。
- **最终正解**：改写 m3u8 后写成本地 `.m3u8` 文件返回 `file://`：
  1. 抓原始 m3u8（含当前有效分片名，分片名会轮换，如 q39stzcj0.jpg→sdhv9hfj0.jpg，必须每次现抓）
  2. 分片 URL 改绝对 + 加 `?x=.ts`（服务器对该 query 仍返回同样加密TS数据，播放器按 .ts 识别容器）
  3. `#EXT-X-KEY` 的 `URI="/vod.key"` 改成绝对 URL（播放器原生 AES-128 解密）
  4. 改写文本用 hex 经 `java.downloadFile(hex,'ysa_xxx.m3u8,{"type":"m3u8"}')` 写本地文件，返回 `file://缓存目录/路径`
- 实测：写入+返回 417ms；新 origin 诊断源 debug 正文确认返回 `file://...m3u8`；分片加 ?x=.ts 裸请求返回正确加密TS（首字节0x84，解密后0x47）。
- ★分片裸请求（不带书源header）也能拿到数据——之前测到188字节错误页是因为用了过期分片名，不是header问题。用当前m3u8里的分片名即可。


### 新坑11：E版报 1004 RUNTIME_CHECK，LT版正常 — file:// 缓存目录硬编码包名
- 症状：同一书源 LT 版音频正常，E 版报 `ERROR_CODE_FAILED_RUNTIME_CHECK 1004`。
- 根因：YS_cacheDir 用 `java.readFile('/')` 异常消息提路径（LT=com.legado.app.release），但拼 file:// 时若回退到硬编码 LT 包名，E 版实际缓存目录是 `io.legado.app` → 文件不存在 → 1004。技能总纲铁律：file:// 必须动态探测当前 App 真实缓存目录，硬编码包名跨版本必挂。
- ★跨版本通用正解：`java.io.tmpdir` 系统属性 = `/data/user/0/<包名>/cache`，`split('/')` 取**倒数第2段**得到包名（LT=com.legado.app.release / E=io.legado.app），再拼 external cache 绝对路径 `/storage/emulated/0/Android/data/<包名>/cache`（java.downloadFile 的实际写入目录）。零反斜杠写法：
  ```js
  var tmp=String(Packages.java.lang.System.getProperty('java.io.tmpdir')||'');
  var parts=tmp.split(String.fromCharCode(47));
  var pkg=parts[parts.length-2];
  var d='/storage/emulated/0/Android/data/'+pkg+'/cache';
  ```
- 保留 java.readFile('/') 异常提取作兜底，最后才硬编码 LT 路径。

### 新坑12：E版 file:// m3u8 报 1004 — 两版 HLS 检测差异，E版分支返回原始 http m3u8
- 症状：LT 版 file:// m3u8 正常播，E 版同规则报 `ERROR_CODE_FAILED_RUNTIME_CHECK 1004`。改动态缓存路径（新坑11）后仍报。
- 定性：1004=运行时检查失败；ExoPlayer troubleshooting 指出"最常见原因=HLS/DASH 内容被播放器按普通媒体处理"。E 版对 file:// URI 的 .m3u8 不做 HLS 识别（或 FileProvider 限制），LT 版做。这是**两版播放器实现差异**，不是路径问题。
- 用户选择方案 A：E 版走独立返回形态——**E 版返回原始 http m3u8 URL**（播放器按 http HLS 正常识别，绕过 file:// 1004），LT 保持改写 file://。版本判断用 `java.io.tmpdir` 倒数第2段包名含 `io.legado` = E 版。
- 注意：E 版返回原始 m3u8 后分片仍是 AES 加密 .jpg，若之后报 3003 需另做 E 版分片方案；但至少先绕过 1004。
- 跨版本分流范式（可复用）：同一规则里 `if(pkg.indexOf('io.legado')>=0){return E版形态} else {return LT版形态}`，用 java.io.tmpdir 判版本，零反斜杠。

---

## ★★★★★ 音频 3003/1004 终极方案（261119 最终定案，整合覆盖此前所有音频方案）

> **本节是本站点音频播放的唯一权威方案**。历史上依次尝试并被真机证伪的方案（不要再用）：
> ①原始 http m3u8 直返 → 3003（分片是加密 .jpg，容器识别失败）
> ②改写 m3u8 加 `?x=.ts`、data URI m3u8 → 真机仍 3003
> ③file:// .m3u8 → E 版 1004
> ④本地 AES 解密拼 TS 用 `java.ajax/ajaxAll` + `UTF-16LE` 还原 + `NoPadding` 解密 → 3003（数据损坏，见下）
> ⑤file:// .ts 裸字符串 → E 版仍 1004（DataSource 不支持）
> 以下最终方案逐条给出源码级/数据级根因，全部经 LT+E 双端真机规则环境验证。

### 根因链（三个叠加问题，缺一不可解）

**问题1：E 版播放器 DataSource 不支持 file://（1004 根因）**
- E 版 `AudioPlayService.kt` L238 `if (url.isJsonArray())` 是播放路径分水岭：
  - 普通 URL → `setMediaItem(getMediaItem())` → E 版 `ExoPlayerHelper` 的 CacheDataSource **upstream=OkHttpDataSource（仅 http/https）** → `file://` 报 `ERROR_CODE_FAILED_RUNTIME_CHECK 1004`。
  - JSON 数组 `["url",...]` → `getMediaSource()` → `DefaultDataSource.Factory(context)`（支持 file://）→ 1004 消失。
- LT 版 L312 同款分流且额外有 `localMediaItem()`（也支持 file://），所以 LT 裸 file:// 能播、E 版不行；E 版无 localMediaItem ⇒ **返回 JSON 数组是 E 版播 file:// 的唯一正解**。
- ★正解：`ruleContent` 返回 `JSON.stringify(["file:///...ts"])`，强制 `isJsonArray()=true`。

**问题2：`java.ajax/ajaxAll` 取二进制必 fffd 损坏（3003 数据根因之一）**
- `java.ajax/ajaxAll` 把二进制密文按字符串解码，非法字节永久变 U+FFFD（charCode=0xfffd），信息不可逆丢失。铁证：同一批加密分片，无 fffd 的解密正常（`4740` TS头），含 fffd 的解密成垃圾（`deff/7268/ad24/e503`）；**60/60 分片全中招**。
- charset 选项（ISO-8859-1/UTF-8/UTF-16LE/windows-1252）全无效（响应头 charset 定死）；`java.connect().raw()`/`ajaxAll元素.raw()` 的 body 都已 closed（`IllegalStateException: closed`）。
- ★唯一无损通道 = **okhttp3 原生同步请求直接拿 byte[]**（key 和分片都要）：
  ```js
  function YS_rawBytes(url){var C=Packages.okhttp3.OkHttpClient,R=Packages.okhttp3.Request;
    var client=new C();return client.newCall(new R.Builder().url(String(url)).build()).execute().body().bytes();}
  ```
- 注意：`UTF-16LE CharsetEncoder` 还原只对**恰好无非法字节**的数据成立（如 key），对真正随机 AES 密文必失败——这是曾被误当成"终极正解"的原因，已证伪。

**问题3：AES padding 导致 TS 包错位（3003 数据根因之二）**
- 加密分片尾部是 `04 04 04 04` / `08×8` = **PKCS#7 padding**。
- `AES/CBC/NoPadding` 会保留 padding（每片 mod188=4/8/12/16），拼接后 TS 的 188 字节边界同步字节 53102/56080 错误 → 3003。
- ★正解：`AES/CBC/PKCS5Padding`，Cipher 自动去 padding → 每片 mod188=0、首字节 `0x47`、拼接后 56078 个 188 边界同步全部正确（syncBad=0）。

### 最终实现 YS_audioLocal（要点）
1. `player_aaaa.url` 拿 m3u8；抓文本按内容 MD5 做缓存 key（`source.get('ysok_'+md5)` 命中直接返回）。
2. `YS_rawBytes(origin+'/vod.key')` 拿 16 字节 key，IV=16 个 0。
3. 逐片 `YS_rawBytes(segUrl)` → `Cipher.getInstance('AES/CBC/PKCS5Padding')` 解密 → `ByteArrayOutputStream` 累积。
4. 校验 `all[0]===0x47 && all.length%188===0`，否则回退原 URL。
5. `BigInteger(1,all).toString(16)` 转 hex（**禁用 JS `hx+=` 逐字节拼 16MB，O(n²) 会 OOM**），`java.downloadFile(hex, name+',{"type":"ts"}')` 写本地。
6. 返回 `JSON.stringify(['file://'+YS_cacheDir(J)+path])`；`YS_cacheDir` 用 `java.io.tmpdir` 倒数第2段取包名（E=io.legado.app.release / LT=com.legado.app.release），零硬编码。

### 双端真机验证数据
- LT：首次 64.5s，返回 JSON 数组，`len=10542664 mod188=0 syncBad=0/56078 head=4740`。
- E：首次 31.9s，`fp=file:///storage/emulated/0/Android/data/io.legado.app.release/cache/...ts`，`len/mod/syncBad/head` 全绿。
- 二次缓存命中秒开（m3u8 分片名轮换后缓存自然失效重下）。

### 性能权衡（可复用认知）
- okhttp 原生请求是唯一无损通道，但 Rhino 无法桥接 Java Thread 并发（`JavaAdapter` 报 can't load class），okhttp `enqueue` 回调曾致 App 崩溃（MCP 端口 ECONNREFUSED）⇒ 只能串行 60 片，首次 32~64 秒，靠持久化缓存补偿。
- 若未来找到 Rhino 安全的并发 byte[] 下载方式（如 `ExecutorService.invokeAll` + 可用 Callable 桥），可把首屏压到 10 秒内，但**数据通道绝不能退回 java.ajax**。

### 跨版本/跨站通用铁律（本节提炼）
1. Legado 规则里拿二进制 = okhttp `body.bytes()`，不是 `java.ajax`（后者 fffd 损坏）。
2. AES 加密 HLS 分片先看尾部 padding 判 NoPadding/PKCS5Padding；TS 拼接必须 mod188=0 且 188 边界同步全对才算有效。
3. 把本地文件交给 E 版播放器 = JSON 数组 `["file:///..."]`（触发 DefaultDataSource），LT 裸 file:// 可播但统一用数组更稳。
4. file:// 缓存目录动态探测：`java.io.tmpdir` 倒数第2段取包名，零硬编码。
5. E 版规则环境 `java.getJsLib` 不存在（jsLib 函数已全局注入直接调用）；`java.ajaxAll` 元素有 `.body()`，单个 `java.ajax` 没有。
