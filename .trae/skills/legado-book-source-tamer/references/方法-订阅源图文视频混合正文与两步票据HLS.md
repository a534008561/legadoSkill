# 方法：订阅源图文+多视频混合正文、两步票据 HLS 与「URL 正则」正确落点

> 261107 `jybl26.com`（91爆料官方中转发布页 → 内容站 `*.yixuiyyj.cc`）订阅源实战提炼。
> 适用：Typecho/博客型订阅源、正文内嵌多个加密 HLS 视频、发布页泛子域线路池。
> 双版本：LegadoTeam（LT）与 legado-E 源码级比对一致。

## 一、本次首见的六个坑（按致命程度排序）

### 1. ★★★ `ruleDescription` 非空 ⇒ 完全跳过 `ruleContent`（订阅源独有，书源无此机制）

源码 `ReadRssViewModel.resolveRssReadLoadTarget`：

```kotlin
val description = article?.description
return when {
    article == null -> Url(...)
    !description.isNullOrBlank() -> CachedContent(description)   // ← 直接显示描述
    !ruleContent.isNullOrBlank() -> RuleContent(article, ruleContent)
    else -> Url(article.link, article.origin)
}
```

且 `refresh()` 里 `if (!rssArticle.description.isNullOrBlank()) return finish()`。

**症状指纹**：列表/封面/发现全正常，点开文章只显示一行「作者 • 日期 • 分类」，图文正文与所有视频都不加载，且用户点刷新无效。

**铁律**：想让 `ruleContent` 生效（尤其正文里带视频/自定义 HTML 时），**`ruleDescription` 必须留空字符串**。
列表卡片摘要由 `articleStyle` 渲染，不要塞进 description 字段。
`loadContent` 成功后会 `rssArticle.description = body` 写回（这是正文缓存，正常）。

> 验证法（App 内 eval_js 探针）：模拟 `resolveRssReadLoadTarget` 判定，
> 断言 description 为空时 target = `RuleContent`。

### 2. 「URL 正则」在订阅源里到底指什么

用户说「书源 URL 正则规则」，但**订阅源没有 `bookUrlPattern`**。源码核对：

- `RssSource.kt` 字段：`contentWhitelist` / `contentBlacklist` / `shouldOverrideUrlLoading` / `ruleLink`
- `ReadRssActivity.CustomWebViewClient.shouldInterceptRequest`（**仅非主框架子资源**）：

```kotlin
val blacklist = source.contentBlacklist?.splitNotBlank(",")
if (!blacklist.isNullOrEmpty()) {
    blacklist.forEach { if (url.startsWith(it) || url.matches(it.toRegex())) return createEmptyResource() }
} else {
    val whitelist = source.contentWhitelist?.splitNotBlank(",")
    if (!whitelist.isNullOrEmpty()) { /* 命中才放行，未命中一律空资源 */ }
}
```

→ **黑名单优先；黑名单为空时才判白名单；两者都空不拦截**。逗号分隔，每条是前缀或正则（`toRegex()` 全匹配）。

**视频播放致命配套**：黑名单里**绝不能**写 `.*/usr/plugins/.*`（站点自带 `hls.min.js` 在该路径），
也**不要**写 `.*/action/player/.*`（页内自愈虽走 App OkHttp 不经 WebView，但保守起见放行）。
白名单留空可避免误杀站点以后新增的合法资源域。

`shouldOverrideUrlLoading` 是**主框架跳转拦截**（`source.evalJS(js).toString().isTrue()`），
绑定 `url` 与 `java`(rssJsExtensions)，返回 `true` 拦截外跳广告。
注意它是 `if/else` **语句块**，靠 Rhino **完成值语义**返回结果 —— 不能用 `return (...)` 包裹求值，
真机探针必须用裸 `eval(js)` 验证（用 `new Function('return ('+js+')')` 会报语法错误，是探针写法错不是规则错）。

### 3. 两步票据 HLS 协议（前端无密钥，服务端签一次性票）

站点 `artplayer-plugin-authentication.min.js` 注释自曝协议（逆向金矿）：

```
① POST /action/player/ticket?cid=N&idx=M&_=<一次性随机>
   → {"status":0,"data":{"ticket":"...","ttl":120},"msg":"成功"}
② POST /action/player/get_play_url?cid=N&idx=M
   body: ticket=<票>&env=<指纹JSON>&_ver=v0
   → {"status":0,"data":"https://op.xxx.cn/videos5/....m3u8?auth_key=..."}
```

- **实测最小 `env={}` + `_ver=v0` 即可通过**（服务端注释明说：指纹信号只记录不拦截，
  真正限制是限频 + 播放地址短过期）。`_ver=v1` + `source_contract=dual-v1` 返回 `{primary,fallback}` 双源（HEVC/H264 降级）。
- ⚠ **取票必须 POST + URL 一次性随机串**：站点注释实锤「镜像站走 CloudFront 无视 `no-store` 缓存 GET 票据
  → 第一次播放消费掉票，后续全拿到同一张已消费票 → 永远『票据无效或已过期』」。
  `ajaxAwait` 是 GET，**不能用**；页内自愈必须用 `postAwait`（订阅源 WebView JS 桥，走 App OkHttp，无 CORS）。
- 票 ttl=120s，`auth_key` 里含 10 位时间戳 → 直链短过期。
  **订阅源正文永久缓存**（`description=body` 写回）⇒ 二次打开必用过期链接 ⇒ 必须页内自愈：
  ① 打开时按生成时间差 >90min 预刷新 ② `<video>` error 兜底 ③ 点击视频区手动刷新。
- m3u8 是标准 `#EXT-X-KEY:METHOD=AES-128`（`crypt.key` + IV），hls.js `enableSoftwareAES:true` 直接处理；
  视频域 `Access-Control-Allow-Origin: *` 且允许 Range，WebView 内 hls.js 可直连。
- hls.js 双源：优先站点自带 `/usr/plugins/ArtPlayer/assets/hls.min.js`（跟随线路），
  `onerror` 兜底 `https://s4.zstatic.net/ajax/libs/hls.js/1.6.13/hls.min.js`（实测国内可达，jsdelivr 被墙）。

### 4. `java.post` 返回 **jsoup `Response`**，不是 StrResponse、不是 String

App 内实测三态：

| 调用 | 返回 | 取正文 |
|---|---|---|
| `java.connect(url, hdr, ms)` | `StrResponse` | `.body()` / `.code()` / `.callTime()` |
| `java.post(url, body, hdr)` | `org.jsoup.helper.HttpConnection$Response` | **`.body()`** |
| `java.ajax(url)` | `String?` | 直接就是正文 |

`java.post` 的对象 `String(r)` 得到 `org.jsoup.helper.HttpConnection$Response@hash`（48 字节垃圾），
**必须 `String(r.body())`**。E 版签名 `post(urlStr: String, body: String, headers: Map<String,String>)`（Kotlin 非空参，
第三参传 JS 对象字面量/空串 body 都可用，别传 null）。

### 5. 正文「猜你喜欢/热门推荐」插在**中段**，不能「命中即截断」

Typecho Mirages 主题把 `div.guess-like-post` / `div.hot-recommend-post` 塞进 `div.post-content[itemprop=articleBody]`
**内部**，且后面还有正文继续（本站实测推荐块 @12018，全文 27280，之后还有 10+ 段正文与图片）。

- ❌ `html = html.substring(0, html.indexOf('guess-like-post'))` → 丢掉后半篇文章（实测 IMG 21→11 但 P 也少一半）
- ❌ 用 `id="body-bottom"` 作结束标记 → 它在 `</article>` **之后**，永远匹配不到
- ✅ **div 配平删除法**：从 `<div class="guess-like-post"` 起，用 `/<div\b|<\/div>/gi` 逐个计数，
  depth 归零处截断，整块删除，正文后半段完整保留。
- 判据：清理后 `<p>` 数应与原文一致（本站 43），真图数 = 全部 `z-image-loader-url` 图 **减去推荐块内的图**
  （21 - 10 = 11）。别把「图变少」直接当 bug，先数清推荐区吞了几张。

### 6. 发布页 Base64 + `java.base64Decode` 直接解出线路表

`jybl26.com` 首页是 `<script>document.write(Base64.decode('...'))</script>`，正文全在一段 base64 里：

```javascript
var raw = String(java.connect(pub, hdr, 20000).body());
var m = /Base64\.decode\(['"]([A-Za-z0-9+/=]+)['"]\)/.exec(raw);
var html = String(java.base64Decode(m[1]));   // 20623B 真实 HTML
var zz = /zz_line\s*=\s*"([^"]+)"/.exec(html);  // "yixuiyyj.cc\ncvcmneja.cc\nd3hw80p8c34pat.cloudfront.net"
```

`java.base64Decode` 在 App 规则 JS 环境可用（探针实测 `DECODE_HEAD=<!DOCTYPE html>`）。
`zz_line` 三行基础域 → `buildJumpUrl(domain, i)`：前两条加 `words.random()` 泛子域前缀，
第三条（cloudfront）不加。泛解析实测 `ability.` / `abandon.` / `access.` 任意词都 200 同后端。

## 二、完整架构（交付定式）

```
发布页(Base64 → zz_line 3域) ──登录面板──> jyFound/jyLine/jyDelayN
                                            │
sortUrl @js: 18行「名称::URL」，每行 {{page}} 路径分页 ──┤ 动态线路
searchUrl {{}} IIFE: /search/{kw}/{page}/ ─────────────┤
列表 CSS: article[itemtype="http://schema.org/BlogPosting"]（排除 8 个 ad-item 占位）
字段全 @js:（Element 走 Mode.Js，双版本通吃；ownText 去掉「热搜 HOT」尾）
ruleDescription = ''  ← ★★★ 必须空，否则跳过正文
ruleNextPage = PAGE（loadMore 用 page+1 重发含 {{page}} 的 sortUrl；空列表判停，不写死页码上限）
                                            │
ruleContent @js: 抓文章页 → 正文容器边界扫描 → 懒加载图还原 → div配平删推荐/广告
   → 解析 dplayer data-config(cid/idx/poster) → 服务端两步票据取 6 个 m3u8 直链
   → 替换成 <video> 卡片 → 输出 hls.js + 页内 postAwait 自愈脚本
                                            │
contentBlacklist（URL正则）只拦广告统计域，放行 hls.js / 视频域 / 图片域
shouldOverrideUrlLoading 放行线路/视频/图片/hls CDN，拦第三方广告外跳
```

## 三、验证流程（订阅源 MCP 无 debug 通道，靠「LAN 落库 + eval_js 真机探针」）

1. `MCP save_source` / `debug_source` **只查 BookSource**，订阅源一律报「未找到书源」。
   → 唯一落库通道 = LAN `POST /saveRssSources`，body 必须是 **JSON 数组**（单对象报「转换源失败」）；
   `GET /getRssSources` 回读逐字段比对（本次 46 字段差异数 0）。
2. App 内 eval_js 探针从 LAN 回读 JSON 里**精确切出目标源对象**（`sourceUrl` 唯一串定位），
   正则取 `ruleContent` 字段 → `JSON.parse('"'+escaped+'"')` 还原 → `new Function(...,'var __r = '+script+';return __r;')` 执行。
   ★ IIFE 完成值不会自动 return，**必须显式 `var __r = ...; return __r;`**（否则恒 `undefined`）；
   ★ 不能用 `return ('+script+')` 包裹带 `//` 注释的脚本（注释吞括号），实测会语法错。
3. 断言清单：DOCTYPE / video 数 / img 数 / m3u8 直链数 / postAwait 存在 / 广告标记全 false /
   `ruleDescription===''` → 模拟 `resolveRssReadLoadTarget` 判 target=RuleContent。
4. 页内 JS 用 `eval(ov)` 完成值语义测 `shouldOverrideUrlLoading` 的 true/false 矩阵。
5. 登录面板函数库 `new Function('source','java',...,loginJs+'\nreturn {...}')` 编译 + 逐 action/viewName 调用，
   断言 viewName 显示域名与 JY_switch 实际写入的 `jyLine` **完全一致**（随机词不能每次重算，须持久化到 jyFound）。

## 四、双版本兼容性核查（E 版）

`RssSource.kt` / `RssParserByRule.kt`（diff 为空）/ `RssSourceExtensions.sortUrls()` /
`ReadRssActivity` 白名单段 / `JsExtensions.post()` 签名 —— **E 版与 LT 版代码级一致**。
故以下写法双版本通吃：`@js:` 纯文本 sortUrl、`{{}}` IIFE、CSS 列表 + `@js:` 字段、
V1 静态 loginUi + viewName 动态文本、`contentWhite/Blacklist`、`postAwait`。

## 五、风控与限频纪律

- 用户要求「不要主动探测搜索访问频率」⇒ 只做单次搜索结构验证（`/search/偷拍/1/`），
  不连发多次试探边界；源内 `concurrentRate=1/1500`（1.5s/请求）主动降速。
- 分类分页抽样间隔 2s，视频票据逐 idx 单次（每个视频一张独立一次性票，天然不并发）。
- 线路测速只在用户**手动点「⏱测试延时」**时发生，不自动触发（避免自伤 IP）。

## 六、App 内实测清单（用户侧）

1. 订阅列表 → 「91爆料·吃瓜(订阅)」→ 发现页应见 18 个分类 tab
2. 点「📰 最新」→ 32 卡片（封面+标题+日期），底部加载更多自动翻页
3. 搜索「偷拍」→ 40 结果
4. 打开任一文章 → 图文正文 + 6 个视频卡片（poster 封面），点播放应出画面
5. 二次打开同一文章 → 若直链过期，页内应自动重取（或点视频下方文字手动刷新）
6. 登录面板：发布页输入框 → 🧭获取线路（3 条）→ ⏱测试延时（ms 写进各按钮名）→ 点线路按钮切换 → 🔍检查登录状态
7. 切线路后重新进入订阅页生效；若分类未刷新，用排序菜单「清理排序缓存」

## 七、【补充 261107 下午】LAN WebSocket 订阅源调试通道（用户提示后打通）

**用户原话**：「订阅源可以用 lan 服务进行调试」——此前记忆误以为「MCP debug_source 只找 BookSource ⇒ 订阅源无调试通道」，实际 **LAN web 服务有独立 WebSocket 调试端点**。

### 路由与握手（源码级）

- `app/src/main/java/io/legado/app/web/WebSocketServer.kt`：
  `openWebSocket()` → `"/rssSourceDebug" -> RssSourceDebugWebSocket(handshake)`
  （另有 `/bookSourceDebug`、`/searchBook`）
- **端口 = HTTP 端口 + 1**（本次 HTTP `1122` → WebSocket `1123`）。
- 握手需 `Sec-WebSocket-Protocol`（`BookSourceController.hasValidJsSourceWebSocketProtocol`）：
  - 常量：`JS_SOURCE_WEBSOCKET_PROTOCOL = "legado"`、`PREFIX = "legado.token."`
  - 值 = `legado, legado.token.<base64Url(token).trimEnd('=')>`（**两个** protocol，逗号分隔）
  - `tokenRequired=false` 时只需第一个 `legado`
  - token 就是 web 服务的 `x-legado-token`（本次 `a7894563`）
- 连上后发 **JSON `{"tag":"<sourceUrl>"}`**（`RssSourceDebugWebSocket.onMessage` → `appDb.rssSourceDao.getByKey(tag)` → `Debug.startDebug`）
- `printLog` 把逐步日志推回；`notPrintState=[10,20,30,40]` 过滤大段正文（有时能看到完整 HTML，有时看不到，属正常）

### 纯 Python socket 客户端（无 websocket 库时）

沙盒无 pip / node / websocket-client ⇒ 手写 RFC6455：
`GET /rssSourceDebug` + Upgrade 头 + 上述 protocol → 读 101 → 发 masked text 帧 → 循环解析服务端帧（处理 126/127 长度、ping、close）。
完整脚本：`/workspace/jybl91/ws_debug.py`（`python3 ws_debug.py 1123 <sourceUrl>`）。

### 用调试日志实锤的两个真机故障

1. **封面不显示**：日志 `┌获取图片url └` 为空 → 定位到 `ruleImage` 里
   `u.replace(/^https?:\/\/([^/]+)\/\/+/, ...)` 抛
   `InternalError: 对应于 JavaScript 参数类型 (object,string) 的 Java 方法 java.lang.String.replace 的选择不明确`。
   ★★ **jsoup `attr()`/`text()`/`ownText()` 返回 Java String**，对 Java String 调 `.replace(RegExp, ...)` 会命中
   `java.lang.String.replace(char,char)/(CharSequence,CharSequence)` 重载歧义 → 异常被 try/catch 吞 → 返回空。
   修法 = `String(u)` 先包成 JS 原生字符串，或用纯字符串操作（`indexOf/substring/split().join()`），别在 Java String 上用正则方法。
   站点图片 URL 常带双斜杠 `pic.hdhwqx.cn//upload_01/`（curl 200 但 Glide 路径规范化可能 404）⇒ 顺手规范化。
2. **打开正文空白**：真机 `ReadRssActivity` 走 `loadDataWithBaseURL(baseUrl, html, "text/html", ...)` +
   `clHtml()` 注入 style。两个元凶：
   - ❌ 页内 `document.write("<script src=...>")`（hls.js 兜底）：在 loadDataWithBaseURL 解析中执行会**清空整个文档**。
     改 `document.createElement('script') + appendChild` + `onload/onerror` 回调，且 hls.js 用 `<script async>` 放 head 不阻塞图文。
   - ❌ **服务端串行取 6 个视频直链**：LAN 调试计时 `[00:01.673]` → `[00:21.233]` = **21 秒空白等待**，用户直接判「空白」。
     改「服务端不取链，只输出视频骨架 → 页内 postAwait 异步取链」⇒ `[00:01.728]` → `[00:03.187]` ≈ **1.5 秒**。
     ★ 判据：调试日志「内容页解析完成」的时间戳差就是真机空白时长，>5 秒就该重构为异步。

### ★★ postAwait 是 Promise + JS_INJECTION 注入前提（双重坑）

- `WebJsExtensions.JS_INJECTION` 里 `function postAwait(...args){ return new Promise(...) }` ⇒
  **必须 `.then(resp => ...)`**；`JSON.parse(String(postAwait(...)))` 拿到 `[object Promise]` 恒失败。
- `WebJsExtensions.post(urlStr, body, header: String, timeout)` 接 **JSON 字符串 header**（内部 GSON 转 Map），返回 **`super.post(...).body()` 字符串** ⇒ `.then(t => JSON.parse(String(t)))` 正确。
- ★ **`JS_INJECTION` 只在 `hasPreloadJs`（`preloadJs` 非空）时注入**：
  `ReadRssViewModel.hasPreloadJs = !preloadJs.isNullOrBlank()` → `clHtml()` 才插 `JS_URL`(`<script src="$nameUrl">`)
  → `shouldInterceptRequest` 的 `else if (!jsInjected && url == nameUrl)` 分支才返回
  `(() => {JS_INJECTION\n$preloadJs})()`。**`preloadJs` 留空 ⇒ 页内 postAwait/ajaxAwait 全部 undefined ⇒ 视频永远取不到链**。
  修法：`preloadJs` 写一行注释即可（如 `/* enable WebView JS bridge */`）。
- `Ajax`/`connect` 系列返回类型三态（见正文第四节），`postAwait` 是第四态（Promise），别混用。

## 八、【补充】播放器增强脚本（injectJs 通用增强）

用户提供 clipboard.im 短链（`https://clipboard.im/s/qG4rhjdsXG`）里的 5666B 脚本，四个视频订阅源实测可用。
**剪贴板内容 API = `GET /api/share/{share_id}`**（不是 `/api/clipboard/{id}`；后者是编辑态剪贴板，短链映射不到返回空）。
`/s/:share_id` 前端路由由 `Share-*.js` chunk 解析，实际数据走 `/api/share/`。

脚本功能：①横/竖屏全屏自动切换（`fullscreenchange` + `body.fs-ls` CSS 旋转 + `screen.orientation.lock`）
②长按 500ms 进 3 倍速（`FAST_RATE=3.0` 可改）③拖动调进度（`touchmove` + 24ms 节流 + 时间浮层）
④**直播保护**：`if(!isFinite(dur)||dur<=0) return` —— duration 无效（直播流）时禁止 seek。

**注入机制**：`ReadRssActivity.onPageFinished` → `view.evaluateJavascript(injectJs, null)`（**晚于 DOM**，正适合绑定已存在的 video）。

**多视频源适配三处**（原版只 `querySelector('video')` 绑第一个）：
1. `querySelector` → `querySelectorAll` 遍历绑定（本源正文 6 个 `<video>`）
2. `isLS()` 改为按**当前全屏的那个 video** 判断横竖（原来固定取第一个，多视频会误判）
3. 加 `window.__jyPlayerEnhanced` 全局守卫：`injectJs` 每次 onPageFinished 都执行，原版 `setTimeout(tryBind,800)` 无限轮询会叠加多份手势监听
4. 保留 800ms 轮询以兼容 hls.js 后建/动态插入的 video

适配版：`/workspace/jybl91/player_enhance_adapted.js`，原版 `player_enhance.js`。

## 九、【补充 261107 傍晚】用户三轮实测报障后的最终定案

### 用户报障链与对应根因（三轮）

| 轮次 | 症状 | 根因 |
|---|---|---|
| 1 | 封面不显示、正文空白 | ①`ruleImage` 对 jsoup Java String 调 `.replace(RegExp)` 抛重载歧义（§七）②正文 21 秒才出（§七） |
| 2 | 封面不显示、只有文字、图片碎裂、视频获取失败 | ①`contentBlacklist` 非空 ⇒ WebView **每个子资源**都过黑名单判定 ②`preloadJs` 触发 JS 注入链 ③`postAwait` Promise + JS 桥链路易碎 ④`ajaxAll` 返回值 `.body` 取错 |
| 3 | 提示「参考樱花动漫订阅源，正文是自己构建的吧」 | 对齐成熟范式：正文自己拼 HTML，页内只播放，**不配** 黑白名单/injectJs 桥/preloadJs |

### ★★★ `java.ajaxAll` 返回值 `.body` 是**方法**不是属性（本轮最贵的一坑）

App 内 eval_js 探针实锤（同一 API 在不同重载下形态不同）：

```javascript
var res = java.ajaxAll(urls);       // res = JS 数组，元素是 java StrResponse / Response
typeof res[0].body                  // => "function"
String(res[0].body)                 // => "function body() {/* java.lang.String body() */}"  ← 垃圾
String(res[0].body())               // => '{"data":{"ticket":"..."}}'  ← 正确
```

⇒ **必须 `res[i].body()`**。写成 `JSON.parse(String(res[i].body))` 会静默失败 → 6 张票全空 → 所有视频「获取失败」。
保险写法（兼容属性/方法两形态）：
```javascript
var b = res[i].body, s = (typeof b === 'function') ? String(b.call(res[i])) : String(b);
```
（记忆里「Rhino 里 Kotlin 属性是方法」在书源测速时已出现过，订阅源 ajaxAll 上是同一类坑的复现。）

### ★★ `concurrentRate` 限速器 × `ajaxAll` ⇒ 正文 21 秒（真机空白）

- 本站 6 视频 = 6 张票 + 6 个换链 = **12 个 POST**。
- `concurrentRate=1/1500` 时 LAN WebSocket 调试计时 `[00:01.673]`→`[00:21.233]` = **21.2 秒**空白等待
  （限速器对每个请求排队 1.5s，即便 ajaxAll 并行也被限）。
- 修法两条并用：`concurrentRate` 放宽到 `1/300` + **`java.ajaxAll(urls, true)` 双参重载传 `skipRateLimit=true`**
  （记忆里「ajaxAll 双参重载可跳限速」实锤）。
- 修后 LAN 调试 `[00:02.262]`→`[00:05.945]` ≈ **3.7 秒**（含两次内容页）；App eval_js 环境 0.7 秒。
- ★ 判据：LAN 调试日志「内容页解析完成」与「≡获取成功:文章页」的时间戳差 = 真机空白时长，>5 秒必须查限速器。

### ★★ 订阅源「正文图片碎裂」= 别碰 contentWhite/Blacklist

源码 `ReadRssActivity.CustomWebViewClient.shouldInterceptRequest`：**只要黑名单或白名单任一非空，
每一个 WebView 子资源（img/video/key/ts/data:/blob:/about:blank/虚拟 nameUrl）都要过一遍判定**，
任一误判即 `createEmptyResource()` → 图片碎裂/视频黑屏。

本源正文是**自己拼的纯净 HTML**（广告/统计脚本全已剔除），根本没有需要拦的对象 ⇒
**`contentWhitelist` 与 `contentBlacklist` 都留空**，让拦截链走最简单直通路径。
用户要的「URL 正则」改由 `shouldOverrideUrlLoading`（主框架跳转拦截）承担，功能不丢、风险归零。

（若别的源确实要拦广告：白名单必须额外放行 `data:`/`blob:`/`about:blank`/`file:` 及
`WebJsExtensions.nameUrl` 那个随机假域名 `https://{random}.com/{random}.js`。）

### ★ 「樱花动漫」订阅源参考范式（用户提示）

App 里已落库的「樱花动漫」(`http://www.yinghuadm.io`) 是**成熟可靠**的订阅源正文构建写法：

```
ruleContent = "class.movurl@a@html&&class.thumb l@html&&class.info@html\n<js>\n ... result='<html><head>...<iframe ...>...' \n</js>"
```

特征：
- 用 **`<js>` 标签 + `result=` 赋值** 拼完整 HTML（不是 `@js:` IIFE return，两者都可用）
- 正文**完全自己构建**：按钮组 / tab / iframe 播放器 / 内联 `<script>` 全由规则生成
- **不配** `contentWhite/Blacklist` / `injectJs` / `preloadJs` / JS 桥 —— 链路最简
- 只配 `style`（779B CSS）控制渲染，`loadWithBaseUrl=true`
- 视频走 `<iframe src="解析页">` 交给站点播放器，不在 WebView 里跑 hls.js

⇒ 启示：**订阅源正文越「自包含」越稳**。凡是依赖 WebView JS 桥 / 子资源拦截 / 页内异步取链的，
都在真机上有额外失败面。能对服务端取好的数据，就在 `ruleContent` 里一次性取好嵌进 HTML。

### 最终定案架构（三轮修复后）

```
sortUrl @js: 18 分类 + {{page}} 路径分页 ｜ searchUrl {{}} IIFE
列表 CSS + @js: 字段（ruleDescription 必须空！）｜ ruleNextPage=PAGE
ruleContent @js: 抓文章页 → 正文容器边界 → 懒加载图还原(String() 包 Java String + 纯字符串规范化双斜杠)
                → div 配平删推荐/广告 → 解析 6 个 dplayer data-config
                → java.ajaxAll(urls,true) 两轮并行取 6 个 m3u8 直链（.body() 取值！skipRateLimit 提速）
                → 输出自包含 HTML（img + <video> + async hls.js + 页内播放脚本）
contentWhitelist/Blacklist = ''  ← 不拦任何子资源（图片碎裂修复）
preloadJs = ''  ← 不注入 JS 桥（不再需要 postAwait）
injectJs = 播放器增强（只绑手势，不影响播放）
shouldOverrideUrlLoading = URL 正则拦外跳（承担「URL正则」需求）
concurrentRate = 1/300
```

验证结论（LAN WebSocket 调试 + App eval_js + 逐字段回读）：
列表 32 条 / 封面 URL 规范化 / 正文 11 图 + 6 视频 + **6/6 直链** / 页内脚本语法 OK /
正文耗时 21.2s→3.7s / 回读 46 字段差异数 **0**。

## 十、【补充 261107 夜】★★ 图片全站 AES-128-CBC 加密 —— 「封面/正文图都不显示」的真正根因

用户第 4 轮报「视频可以播放了，但是封面图和正文图还是不显示」。前面所有 URL/黑名单/WebView 排查都不是主因。

### 定性实验（决定性，一步定位）

```
curl -D - https://pic.hdhwqx.cn/upload_01/xiao/20261105/xxx.jpeg
→ Content-Type: binary/octet-stream   （不是 image/jpeg！）
→ 文件 66688B，魔数 4f e8 97 a4 ...   （不是 FFD8FF / 89504E47 / RIFF WEBP）
```

**图片服务器返回的是加密字节**，Glide 与 WebView 都解不出图 → 列表封面空白、正文碎裂。
站点自己的 `image.0821.js`（283KB）负责解密后 `URL.createObjectURL` 显示。

### 协议逆向（`image.0821.js` 第 313-350 行）

```javascript
decryptjs: function(word, cryjs) {
  const cc = (e,o=true) => o ? cryjs.enc.Utf8.parse(e.split("_").map(a=>String.fromCharCode(parseInt(a))).join("")) : ...;
  const decrypt = cryjs.AES.decrypt(word,
      cc("102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48"), {
        iv: cc("57_55_98_54_48_51_57_52_97_98_99_50_102_98_101_49"),
        mode: cryjs.mode["CBC"], padding: cryjs.pad.Pkcs7 });
  return decrypt.toString(cryjs.enc.Base64);   // 图片原始字节的 base64
}
loaderjs: fetch(imglink).then(r=>r.blob()) → FileReader.readAsDataURL → 取 base64 部分 → decryptjs
```

数字下划线序列转 ASCII：
- KEY = `f5d965df75336270`（16B）
- IV  = `97b60394abc2fbe1`（16B）
- AES-128-CBC + PKCS7，**原始响应字节就是密文**（直接 `openssl enc -d -aes-128-cbc` 得到 FFD8FF…FFD9 完整 JPEG）。

`zzz.js` 只是 CryptoJS 库本体，不是解密入口；别在它里面找逻辑。

### ★★ 用户提示「订阅源直接有封面解密那一个输入框啊」——源码实锤

- `RssSource.kt` 有 `var coverDecodeJs: String?`
- `RssSourceEditActivity.kt:445` → `EditEntity("coverDecodeJs", rs.coverDecodeJs, R.string.cover_decode_js)`（编辑界面确有输入框）
- `ImageUtils.getRuleJs(source, isCover)`：`is RssSource -> source.coverDecodeJs`
  —— **订阅源封面解密与书源走同一个 ImageUtils.decode 通道**，`OkHttpStreamFetcher.onResponse` 里
  `ImageUtils.decode(analyzedUrl, responseBody.byteStream(), isCover=true, source)` 调它。
- 绑定：`java` / `source` / `src`(图片URL) / `result`(InputStream 或 ByteArray) / `book`；
  **要求返回 `ByteArray`**（`evalJS(...) as ByteArray`）。

⇒ 不要自己造轮子（我一度去写纯 JS AES、页内 fetch/Web Crypto），**直接用 coverDecodeJs**。

### coverDecodeJs 定式（LT/E 双版本，实测通过）

```javascript
(function () {
  try {
    var u = String(src);
    if (!u || u.indexOf('http') !== 0) return result;
    // ★ 不读 result（真机是 InputStream，Rhino 里 read(byte[]) 循环易踩 closed/类型坑）
    //   改用绑定里的 src 重新 GET：java.get 返回 jsoup Response，.bodyAsBytes() 是完整密文 byte[]
    var cipher = null;
    try { cipher = java.get(u, {'User-Agent':'Mozilla/5.0'}).bodyAsBytes(); } catch (e) {}
    if (!cipher || !cipher.length) { try { if (result && result.length) cipher = result; } catch (e2) {} }
    if (!cipher || !cipher.length || cipher.length % 16) return result;
    if (typeof java.createSymmetricCrypto !== 'function') return result;  // E 版降级
    var out = java.createSymmetricCrypto('AES/CBC/PKCS5Padding',
                 'f5d965df75336270','97b60394abc2fbe1').decrypt(cipher);
    if (out && out.length) return out;   // decrypt(ByteArray) 返回的已是 Java byte[]，直接 return
  } catch (e) {}
  return result;
})()
```

实测：`coverDecodeJs` 返回 `len=66681`、`head=-1,-40,-1`（JPEG SOI）、耗时 109ms。
★ **纯 JS AES 在 Rhino 里解 66KB 会 60 秒超时**（逐字节查表太慢），必须用 `java.createSymmetricCrypto`
（LT 版实测 359ms；E 版若无此 API 则 try/catch 降级返回原字节，不崩）。
★ `java.base64Encode(byteArray)` 会把 byte[] 当对象转字符串（得到 `[B@xxx` 的 base64），**不能用来转图片**；
   正确是 `decrypt()` 直接返回 byte[]，或 `java.base64DecodeToByteArray(纯JS拼的base64)`（后者 829ms/张，慢）。

### 正文图片（WebView 内）——不走 ImageUtils，需页内解密

`ReadRssActivity.shouldInterceptRequest` / `RssWebResourceProxy` 只转发字节、**不调 ImageUtils.decode**，
所以 `coverDecodeJs` **只管列表封面**，正文 `<img>` 得另解。

定式（对齐「樱花动漫」自构建正文范式，不引入 preloadJs/JS 桥）：
1. `ruleContent` 里把 `<img src="URL">` 输出成 `<img data-jy-enc="URL">`（不直接加载，先显示灰底占位）
2. 正文 HTML 内联一段页内脚本：`fetch(u,{mode:'cors'}).then(r=>r.arrayBuffer())`
   → `crypto.subtle.importKey('raw', KEY, {name:'AES-CBC'}, false, ['decrypt'])`
   → `crypto.subtle.decrypt({name:'AES-CBC',iv:IV}, key, buf)`
   → `URL.createObjectURL(new Blob([u8],{type:由魔数判 jpeg/png/gif/webp}))` → 赋给 `img.src`
3. 纯 JS AES 作兜底（`crypto.subtle` 不可用时）
4. `video poster` 同样加密 → 输出 `data-jy-poster`，页内用临时 `new Image()` 解密后把 blob URL 赋给 `video.poster`

前提实测：图片域 `Access-Control-Allow-Origin: *` + `Vary: Origin` ✓；
`loadDataWithBaseURL` 的 baseUrl 为 https ⇒ 安全上下文，`crypto.subtle` 可用。

### ⚠ 内联脚本里绝不能出现裸 `<script>` 字样（连注释里也不行）

页内脚本注释写了「内联在 HTML `<script>` 里」→ 浏览器把该处当**结束/开始标签**提前截断脚本，
真机表现为整段脚本语法错（`SyntaxError: 不允许的字符："。"`，中文注释从中间被切开）。
`html.split('<script>')` 探针能一次抓到（脚本段数从 2 变 3，中间段以中文开头）。
写「由 script 标签包裹」即可。

### 最终验收（第 4 轮）

LAN WebSocket 调试：列表 32 条、封面 URL 正常、内容页 3.7 秒完成；
App eval_js：正文 11 张 `data-jy-enc` + 6 个 `data-jy-poster`、2 个内联脚本段语法全 OK、6/6 视频直链；
`coverDecodeJs` 单独执行返回合法 JPEG byte[]；回读 46 字段差异数 **0**。

## 十一、【补充 261107 深夜】第 5 轮：「大部分封面不显示」+「正文视频全部一起自动播」

### 封面：coverDecodeJs 里**不要重发请求**，直接用 result

- 症状：加了 coverDecodeJs 后**只有 1 张封面显示、大部分不显示**。
- 根因：v1 版 coverDecodeJs 用 `java.get(src).bodyAsBytes()` 对每张封面**重新发一次 HTTP**；
  `RssArticlesAdapter` 一屏并发加载 32 张 ⇒ 32 个额外请求，Glide/OkHttp 连接池排队 + 超时 ⇒ 大多失败。
- 修法：**用 `ImageUtils.decode` 已给到的 `result` 字节，零额外网络请求**。
  `OkHttpStreamFetcher` 对封面调 `ImageUtils.decode(url, responseBody.byteStream(), isCover=true, source)`
  ⇒ `result` 是 **InputStream**（另有 ByteArray 重载，需两形态兼容）。

### ★★ InputStream → Java byte[] 的最快通道（Rhino 实测对照）

| 方案 | 66KB 耗时 | 结论 |
|---|---|---|
| 纯 JS AES 解密 | **60 秒超时** | ❌ 不可用 |
| `read(buf)` 循环 → JS Array → 纯 JS `toB64` → `java.base64DecodeToByteArray` | 1176 ms | 慢 |
| **`read(buf)` 循环边拼 0-255 字符串 → `java.strToBytes(s,'ISO-8859-1')`** | **7 ms** | ✅ **最优** |
| `java.createSymmetricCrypto(...).decrypt(byte[])` | 359 ms | 原生必用 |

```javascript
var CH = String.fromCharCode, buf = java.base64DecodeToByteArray(new Array(8193).join('A')); // 6144B Java byte[]
var s = '', n, i, v, guard = 0;
while (guard++ < 2048) { n = result.read(buf); if (n <= 0) break;
  for (i = 0; i < n; i++) { v = buf[i]; s += CH(v < 0 ? v + 256 : v); } }
var cipher = java.strToBytes(s, 'ISO-8859-1');   // 真 Java byte[]，仅 7ms
var out = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', KEY, IV).decrypt(cipher);
return out;   // 已是 ByteArray，直接满足 ImageUtils.decode 的 `as ByteArray`
```
★ `java.base64DecodeToByteArray(new Array(8193).join('A'))` 是「造一个 Java byte[] 缓冲」的实用技巧
（Rhino 里不能用 `Packages.java.lang.reflect.Array.newInstance` 时用它）。
★ `java.base64Encode(byteArray)` 会把 byte[] 当对象转字符串（`[B@xxx` 的 base64），**不能**用于二进制。
★ `java.bytesToStr(bytes,'ISO-8859-1')` 只能反方向（byte[]→String），`strToBytes` 才是 String→byte[]。

### 正文视频「全部一起播放」→ 改成用户点击才播

- 根因：页内 `jyBoot()` 遍历所有 `<video>` 调 `jyPlay()`，且
  `h.on(Hls.Events.MEDIA_ATTACHED, () => v.play())` ⇒ 6 个视频同时 attach + 自动播，声音/流量全炸。
- 修法（**自构建正文范式**）：
  1. `ruleContent` 输出 video 时 **不给 `controls`、不给 `src`、`preload="none"`**，
     上面盖一个 `<button class="jy-playbtn">▶ 点击播放</button>`（绝对定位居中）。
  2. 页内脚本 `jyBoot()` **只绑定 click**，绝不调 `play()`；
     hls.js 用 `autoStartLoad:false` 且只在点击时 `loadSource/attachMedia + startLoad`。
  3. `jyPlayOnClick(v,i)` 先 `jyPauseOthers(v)`（同刻只播一个）→ `jyAttach` → `v.controls=true` → `v.play()` → 隐藏按钮。
  4. 不拦截原生 `play` 事件（会与 `v.play()` 递归），靠「初始无 src / 无 controls」从根上杜绝自动播。
- 判据：正文 HTML 里 `MEDIA_ATTACHED` 出现次数 = 0、`<video ... controls` = 0、
  `class="jy-playbtn"` 数 = video 数。

### 最终验收（第 5 轮）

`coverDecodeJs` v3 真机执行返回 `len=66681, head=-1,-40,-1`（合法 JPEG byte[]，0.75s）；
正文 6 播放按钮 / 6 video / 无自动 play / 无初始 controls / 11 `data-jy-enc` / 6 `data-jy-poster` /
6-6 视频直链 / 2 段内联脚本语法全 OK；LAN 调试列表 32 条、内容页 3.9 秒；
回读 46 字段差异数 **0**。
