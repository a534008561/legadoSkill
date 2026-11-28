# 方法 · 视频站「订阅源」自绘 hls.js 播放器 + 线路面板（黄果短剧 huangguoai.com 实战）

> 适用：给**视频站**做 Legado **订阅源（RssSource）**，列表 → 点开 → 在订阅阅读页里直接播放（多集/倍速/全屏），
> 同时带「发布页 → 线路池 → 测速 → 切换」登录面板。LT(LegadoTeam) 与 E(Luoyacheng/legado-E) 双版本兼容。
> 参考成品：`examples/黄果短剧_huangguoai.com_订阅源.json`

---

## 1. 订阅源 type 决定正文形态（源码级）

| type | 点击文章走哪 | ruleContent 要求 |
|---|---|---|
| 0 网页 | `ReadRssActivity` → WebView | `loadDataWithBaseURL(articleLink, html, …)`，**可以是完整 HTML 页面** |
| 1 图片 | PhotoDialog | 纯图片 URL |
| 2 视频 | `VideoPlayerActivity`（ExoPlayer） | **必须是纯媒体 URL**（m3u8/mp4）；给 HTML 会被当 MPD 文本 → “转一下就停” |

结论：
- 想**多集切换/自定义播放器** ⇒ `type=0` + ruleContent 输出自绘播放器 HTML。
- 只放单集 ⇒ `type=2` + 纯 m3u8，最省事但一本只能播一集。

`ReadRssActivity` 用 `clHtml(content, style)` 处理正文：
- `hasPreloadJs=false` 时**原样返回**我们的 HTML；
- 会找第一个 `</style>` 插入 `source.style`（留空即不动）；
- 不要依赖 `preloadJs`：`hasPreloadJs=false` 时 `window.java/source` 不会被注入，页面里一律用原生 `XMLHttpRequest`。

## 2. ★ruleDescription 非空会“劫持”正文（视频源必踩）

`ReadRssViewModel.resolveRssReadLoadTarget()`：

```
article.description 非空 → 直接当正文渲染（CachedContent）
否则 ruleContent 非空   → 解析内容页
否则                     → 直接 loadUrl(article.link)
```

⇒ 视频订阅源**必须把 ruleDescription 留空**，否则点开文章看到的是一行简介文字，永远不出播放器。
集数/评分这类副标题放 `rulePubDate`（列表里显示在标题下方）。

## 3. ★正文会被永久缓存进 description，播放器必须“自取直链”

`loadContent()` 成功后：`rssArticle.description = body; dao.insert()`。
之后再次打开走 CachedContent，**不会重新执行 ruleContent**。

⇒ 播放器 HTML 里**不能**写死带 `auth_key` 的 m3u8（约 3 小时过期），必须：
1. 页面加载后 `XHR POST {host}/api/videos/{id}[/episodes/{n}]/playback`（body `{}`）→ `data.streams.main`；
2. 把 `id/ep/total/title/desc/hosts` 用 `JSON.stringify` 注入 `var D = {...}`；
3. 页面里内置**候选线路数组**（hosts），一条取不到就换下一条 —— 缓存页也能抗线路轮换；
4. 详细错误显示在播放器底栏（含“去登录界面换线路”提示）。

改模板后排障：旧文章仍是旧 HTML。要么删源重加，要么换 `sourceUrl` 主键。

## 4. hls.js 优先用站点自己的

站点若自身播放器用 hls.js，通常能在静态目录找到（本例 `/static/web/js/lib/hls.js`，1.48MB）。
同源加载免翻墙、免外链，失败再回退 jsdelivr/unpkg/zstatic：

```
urls = [host+'/static/web/js/lib/hls.js',
        'https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js',
        'https://unpkg.com/hls.js@1.5.17/dist/hls.min.js',
        'https://s4.zstatic.net/ajax/libs/hls.js/1.5.17/hls.min.js']
```

播放前确认链路：
- m3u8 响应头 `Access-Control-Allow-Origin: *`（WebView 跨域必需）；
- `#EXT-X-KEY` 的 key URL 也要 `*`（AES-128 分片）；
- 分片同样 `*`。三项缺一 hls.js 就解不了。

## 4.5 ★★WebView 的 canPlayType('application/vnd.apple.mpegurl') 是假支持 —— 必须 hls.js 优先

261128 黄果短剧「不播放」根因：Android WebView 的
`video.canPlayType('application/vnd.apple.mpegurl')` 返回 **"maybe"**，
播放器若先判原生再 hls.js，就会走 `video.src = m3u8` 分支：
manifest 永不解析、画面全黑、也没有任何报错。

正确顺序（Android WebView 通用）：

```
function attach(url, autoplay){
  if (useHls(url, autoplay)) return;          // window.Hls && Hls.isSupported()
  loadHls(function(ok){
    if (ok && useHls(url, autoplay)) return;  // 站点 /static/.../hls.js → CDN 兜底
    if (v.canPlayType('application/vnd.apple.mpegurl')) { v.src = url; ... } // 最后才原生
    else show('播放器组件加载失败');
  });
}
```

- `new Hls({ enableWorker:false, lowLatencyMode:false })` 在 WebView 里更稳；
- 播放页把「线路」「倍速」都做成**一格一个按钮**（像选集）：线路按钮显示 `线路i · host`，
  倍速 1.0x/1.25x/1.5x/2.0x/2.5x/3.0x 各一格，点哪格切哪格，当前格高亮；
  `start()` 必须从 `hi` 开始试并环形兜底（否则点线路2仍会先走线路1）；
- 另加「自动连播：开/关」按钮（localStorage 记忆，默认开）：`ended` 且 `cur<total` 时自动 `start(cur+1,true)`；
  注意它与「打开页面就自动播」是两回事，用户要的是前者；
- ★`ended` 必须写成三分支，「没有下一集就停」：`cur>=total` → 只提示「已经是最后一集，播放结束」并 `return`，
  **不得再发播放请求**；`cur<total && autoOn` → 提示并 `start(cur+1,true)`；`cur<total && !autoOn` → 只提示「本集播放结束（自动连播已关）」。
  单集视频（total=1）天然走第一支，用假 DOM 跑构建产物可回归四个场景（末集/中间集开/中间集关/单集）；
- 实测探针：`java.webView(html, 文章URL, 探针JS, false)`，
  探针返回 `{useHls:1, stage:"manifest", media:"rs4 t3.41 w480 pausedfalse"}` 才算真在播
  （`readyState=4` + `currentTime>0` + `paused=false`）。

## 4.6 ★★跨线路取播放地址会被 CORS 预检挡住 → preloadJs 暴露 postAwait 原生桥

播放器页的 origin = 文章链接的线路。点「线路2」去请求另一条线路的 API 属于**跨域**：

- 预检 `OPTIONS` 只回 `Access-Control-Allow-Origin: *`，**没有 `Access-Control-Allow-Headers`**
  ⇒ 任何带 `Content-Type: application/json` 的跨域 POST 直接被浏览器拦下；
- 退成「简单请求」（`text/plain`/表单，不触发预检）时，服务端返回
  `{"status":0,"msg":"播放参数无效"}` —— 它只按 JSON 解析；
- GET 该路由是 404。

**正解＝用 Legado 注入的原生桥**（OkHttp，不受 CORS 限制）：

```js
// preloadJs —— 注意 JS_INJECTION 里的 java/source 都在 IIFE 内，页面脚本拿不到，必须显式挂到 window
window.HGJ = java;
window.HGSRC = source;
window.HGPOST = function (u, b, c) {
  return postAwait(u, b || '{}', c || '{"Content-Type":"application/json"}', 9000);
};
```

页面里：

```js
function apiPost(url, ok, bad){
  if (window.HGPOST) { window.HGPOST(url, '{}').then(t => parseStream(t, ok, bad)).catch(e => bad(e)); return; }
  /* 退回同源 XHR（只有文章所在线路能通） */
}
```

要点：
- `postAwait` 是 `JS_INJECTION` 里的 Promise 版 `java.post`，返回响应体字符串；
- `hasPreloadJs=true` 只影响主框架拦截（`data:text/html;` 直接放行）与 `clHtml` 注入 `JS_URL`，
  `JS_URL` 是**渲染时**插进 `<head>` 的，所以正文缓存里的旧 HTML 也能拿到当前 bridge；
- 桥不可用时页面自动退回同源 XHR，播放不受影响（只是不能跨线路）。

## 5. ★站点分页条会“跳 tab”，不能直接跟

本例 `/ai-duanju/` 是 **hot 第 1 页**，但页面分页条的下一页是 `/ai-duanju/2/` —— 那是 **latest 第 2 页**（实测 `data-active-tab` 变化、ID 集合完全不同）。
真正的 hot 第 N 页是 `/ai-duanju/hot/N/`。

⇒ 发现页 URL 一律用模板自拼，不跟站点 pager：

```
🎬 AI短剧::{{HG_TL_BASE(source,java)}}/ai-duanju/hot/{{page>1?page+'/':''}}
🆕 最近上新::{{HG_TL_BASE(source,java)}}/newest{{page>1?'/'+page+'/':''}}
🏷 现代::{{HG_TL_BASE(source,java)}}/tag/xiandai/{{page>1?'page/'+page+'/':''}}
```

- 第 1 页不带页码，避开 `/newest/1/ → 301 → /newest`；
- 翻页用 `ruleNextPage = "PAGE"`（LT/E 的 RssParserByRule 都认），下一页把同一模板按 `page+1` 重新求值；
- **单页频道**（排行榜）给它一个必然 404 的第 2 页：`/ranks/hot/{{page>1?'page/'+page+'/':''}}`
  ⇒ 第 2 页 0 条 → E 版 `hasMore = articles.isNotEmpty() && ruleNextPage 非空` 自然停止，避免 E 无限重复拉同一页。

## 6. jsLib 里没有 java，要显式传参

`BaseSource.getShareScope()` = `SharedJsScope.getScope(jsLib)`，规则/模板的 `java` 是**后绑定**的，
jsLib 函数体按词法作用域找不到它。⇒ 设计成 `HG_TL_BASE(source, java)`，调用处：

```
{{HG_TL_BASE(source,java)}}      // sortUrl / searchUrl 模板
```

请求期自愈（每 30 分钟一次，`robots.txt` 只有几百字节，含 `Disallow` 即判活）：

```
function HG_TL_BASE(s, j){
  var cur = s.get('hgRssLine') || DEF;                 // 面板存的线路
  if (j && Date.now() - (+s.get('hgChk_t')||0) > 1800000) {
     s.put('hgChk_t', String(Date.now()));
     if (!ok(j.connect(cur+'/robots.txt', null, 5000))) {
        // 依次探 2 条候选，成功则 s.put('hgRssLine', c)
     }
  }
  return cur;
}
```

## 7. ★java.ajaxAll 单条网络级失败会整批抛异常

`java.ajaxAll(urls, true)`（skipRateLimit 重载 LT/E 都有）遇到 `UnknownHostException` 会**整个调用抛异常**，
不是“该项返回错误”。测速必须：

1. 分批（5 条/批）；
2. 批次抛异常 → 对该批逐条 `java.connect(u, null, 5000)` 复查；
3. 判活：`code 200~399 && body.indexOf('Disallow')>=0`；
4. 按 `callTime()` 升序重排线路池，死线路排到最后（保留，方便以后重试）。

## 8. ★发布页 `subdomains` 里的英文注释撇号会污染子域

```
var subdomains = [ 'thu', ... // 西安交通大学 (Xi'an Jiaotong University)
```

用 `/['"][^'"]+['"]/g` 抓引号串会把 `an Jiaotong University` 当成子域，拼出
`an Jiaotong University.hvgbwwrxd.cc`。必须再做一次标签过滤：

```
if (!/^[a-z0-9][a-z0-9-]{0,20}$/.test(s)) continue;
```

## 9. ★RSS 列表封面**会**走 coverDecodeJs（旧结论已证伪）+ 站点 AES 图床

261128 源码级纠正：`RssArticlesAdapter.convert` 虽然只写 `ImageLoader.load(context, item.image)`，
但它前面 `RequestOptions().set(OkHttpModelLoader.sourceOriginOption, item.origin)`；
`OkHttpStreamFetcher` 在 `manga=false` 时走 `ImageUtils.decode(analyzedUrl, body.byteStream(), isCover = true, source)`，
而 `ImageUtils.getRuleJs` 对 **RssSource 恒返回 `coverDecodeJs`**。

⇒ 订阅源列表封面只要两步：
1. `ruleImage` 取卡片 `data-src` 并**剥掉 `?auth_key=`**（Glide 缓存键稳定、auth_key 过期不影响）；
2. `coverDecodeJs` 写解密（`result` 是 **InputStream**，`src` 是图片 URL）：

```
var bos=new Packages.java.io.ByteArrayOutputStream();
var buf=new Packages.java.lang.String(8192个'0').getBytes();
var n=result.read(buf); while(n>0){bos.write(buf,0,n);n=result.read(buf)}
var enc=bos.toByteArray();
if(!enc||enc.length<64)return enc;
// 已是明文(FFD8/8950/4749/5249) 或长度非16倍数 → 原样返回
var c=Packages.javax.crypto.Cipher.getInstance('AES/CBC/NoPadding');
c.init(DECRYPT_MODE, new SKS('16个ASCII字符密钥'.getBytes('UTF-8'),'AES'), new IVS(iv.getBytes('UTF-8')));
var dec=c.doFinal(enc);
// 从尾部扫 FFD9 / IEND 截掉填充垃圾，return Packages.java.util.Arrays.copyOf(dec,end)
```

本例封面 `pic.qnlycc.cn`：AES-128-CBC + NoPadding，密钥是 **16 个 ASCII 字符**
`f5d965df75336270` / IV `97b60394abc2fbe1`（不是 16 字节 hex！）。
webp 变体（`new2.qnlycc.cn + path + '.webp'`）同样是密文；裸路径（不带 auth_key）也返回密文。

App 内实测：137136B 密文 → 137122B、magic `255,216,255`、tail `217`。

**播放页封面**（HTML 里不能跑 coverDecodeJs）用页内解密：站点自己的
`/static/web/js/lib/crypto.js`（CryptoJS）+ `CryptoJS.pad.NoPadding` + FFD9/IEND 截尾 + Blob URL，
图床 `Access-Control-Allow-Origin: *` 是前提（本例实测有）。

## 10. 登录面板（V1 静态数组）+ 线路分页

21 行结构（LT/E 都能渲染，E 无 label 类型，状态行用 button 代替）：

```
text   发布页地址   action=HG_savePub()   viewName='发布页(可留空)'  default=发布页URL
button 🧭 获取线路   HG_fetch()     // 解析 var urls + var subdomains，展开 根域×子域
button ⏱ 测速排序   HG_test()      // 分批 ajaxAll + connect 复查，按 ms 排序写 hgLines
button 🔍 检查线路   HG_check()     // robots.txt + /newest 含 hg-drama-card
button 线路状态     HG_status()    viewName=HG_statusName()
button ♻ 恢复默认   HG_reset()
button 线路1..12    HG_switch(i)   viewName=HG_lineBtn(i)  // ▶当前 / host ms / ✗
button ◀上页 下页▶  HG_pagePrev/Next()
button 🔄 刷新面板  HG_refresh()   // java.reLoginView(true)
```

要点：
- `viewName` 用**表达式**（`HG_lineBtn(0)`）时长度不受 3..19 限制；纯文本要写成 `'…'`（含引号 3..19 字符）；
- 每行 `name+type+action+default` 必须唯一，否则被 `RowUi.equals` 去重；
- action 里 `result` 是文本输入的 Map（`result.get('发布页地址')`），`source` 可用，`java` = SourceLoginJsExtensions；
- 免登录源也要写 `function login(){ return 'ok' }`；
- 12 个按钮 + 翻页 = 40 条线路也能一个个点。

## 11. 调试通道

- LT：`/saveRssSources`（1122，body 数组）+ WS `1123 /rssSourceDebug`（首帧 `{"tag": sourceUrl}`）
- E：`1125` + WS `1126 /rssSourceDebug`
- **E 的 WS 不推正文大帧**：日志会显示“内容页解析完成”但没有内容帧；正文校验以 LT WS 为准，E 只验列表。
- MCP `eval_js` 不能直接绑定订阅源 → 想跑面板 JS，可临时用 LAN `/saveBookSource` 存一个 BookSource，
  把同一份 `jsLib/loginUrl` 塞进去，`eval_js(url=临时key)` 里 `eval(source.getJsLib()); eval(source.getLoginUrl())` 后直接调函数，测完删掉。
  这样能真机验证 `java.ajaxAll`、`java.connect`、排序、`source.put` 持久化。

## 12. 交付清单

1. `huangguoai_rss.json`（对象）/ `_arr.json`（数组）
2. 双端 LAN 保存 + `getRssSources` 逐字段 diff
3. LT WS 列表+正文全绿，E WS 列表绿
4. 播放器页：qjs 静态语法 + DOM 桩模拟（集数按钮、每集 URL、切换）
5. 真机点按（面板/播放/全屏）留给用户确认
