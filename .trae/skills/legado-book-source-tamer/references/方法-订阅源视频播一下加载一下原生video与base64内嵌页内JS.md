# 方法：订阅源「播一下、加载一下」——裸 mp4 串 → 原生 `<video>` + base64 内嵌页内 JS

> 蓝本：91PORN 订阅源 261113 十二轮报障「视频加载缓慢，播放也卡顿，播一下连一下」。
> 上一轮（十一轮）已修「首字节慢 + 封面不显示」，本轮是**播放期间持续卡顿**，两回事。

> ⛔ **261113 十三轮最终纠正（务必先读）**：本文件记录的「正文改原生 `<video>` HTML 播放器页」
> **是引入回归的错误方案**，用户实测「点播放加载一下就停 / 一直加载不能播放」。
> 最终定案：该源 `ruleContent` 必须字节级保持 v5 的 3851B 只输出裸 mp4 URL 字符串
> （Legado 内置播放器接管），任何 HTML 包装 / 页内 JS / 规则内动态换链都会破坏播放。
> **本文件仅保留作为「base64 内嵌页内 JS 避引号冲突」「占位符撞注释」这两个纯技术点的反面案例，
> 不要照抄其结论去改播放链路**。正确做法见
> 《方法-订阅源视频源改ruleContent导致播放回归的边界.md》。


---

## 0. 结论先行

| 层 | 结论 |
|---|---|
| 不是 | 双斜杠路径、签名过期、线路慢、封面失败（这些都是上一轮已修或已排除） |
| 是 | **正文输出的是「裸 mp4 URL 字符串」而不是 HTML**；WebView 把它当纯文本/系统嗅探播放，每个 Range 分片还经 `shouldInterceptRequest` 代理转发；叠加 CDN 持续吞吐 ~0.85MB/s 而码率近 1MB/s ⇒ 缓冲永远追不上 |
| 修法 | 正文改输出原生 `<video preload="auto">` 播放器页；页内自愈 JS **base64 内嵌**（`atob` 解码执行）避免 Rhino 脚本引号冲突 |

---

## 1. 分层诊断（含反向验证组）

### 1.1 先量「持续吞吐」，不是首字节
```
同一条直链 103329209 B（103MB / 约17分钟 ≈ 1MB/s 码率）
5 个连续 512KB Range 片：
  orig(双斜杠) 292/1341/212/854/223 ms → 均 584ms ≈ 876 KB/s
  norm(单斜杠) 215/213/209/2153/210 ms → 均 600ms ≈ 853 KB/s
⇒ ① 双斜杠不是主因（两组相当）；② 都有偶发 1~2s 尖刺；③ 吞吐贴着甚至低于码率
```
`java.head` 首字节 206 只要 205~216ms，说明**不是连接建立慢，是持续供流跟不上**。

### 1.2 排除「换 CDN / 换档位」这条路
- 5 个 host 替换同一 path+签名：`la.btc620.com` 206；`cdn77` SSLHandshake；`ccm.91p52.com` PROTOCOL_ERROR；`418`/`a.26702.app` 404/SSL ⇒ **没有可用镜像**。
- `/vlk.php` 三种指纹（min/full/带 quality 参数）全都返回**同一条直链** ⇒ 无清晰度档位。
- `view_video_hd.php` 是会员页，无 mp4/m3u8/strencode2 ⇒ 无 HD 独立流。
- 详情页 `videojs720.js`、`src:{src:"g-br-cdn.kwai.net/...mp4"}` 是**广告占位**，不是正片。
- `java.cacheFile(url)` 单参 = 同步下载整文件（60s InterruptedIOException timeout）⇒ 不能做起播前预下载。
- `java.ajax(url, long)` 第二参是**超时毫秒**（100ms 就返回 timeout 堆栈串），不是字节上限。

### 1.3 源码级定案（本轮最关键）
拉 LegadoTeam master live 源码：
```kotlin
// ReadRssViewModel.clHtml —— 默认样式明确含 video：
"img{...}video{object-fit:fill; max-width:100% !important;...}body{...}"
⇒ 订阅源正文原生支持 <video> 标签

// ReadRssActivity.initLiveData：
val baseUrl = if (rssSource?.loadWithBaseUrl == false) null else url  // url=文章URL
currentWebView.loadDataWithBaseURL(baseUrl, html, "text/html", "utf-8", url)
⇒ 页面 origin 就是站方域 ⇒ 同源 XHR 重取详情页可行（站方虽无 ACAO 也不影响同源）

// shouldInterceptRequest：非主框架子资源在 Cronet 开启时
if (AppConfig.isCronet && RssWebResourceProxy.shouldProxy(...))
    return runBlocking(IO) { getProxiedResource(request) }   // 每个 Range 分片多一跳 Java 代理
```
而当前 `ruleContent` 输出的是 `https://la.btc620.com//mp43/xxx.mp4?...` **纯字符串**。
WebView 加载纯文本 → 系统嗅探/外部播放，没有 `<video>` 元素的缓冲策略，
再叠加代理转发与 CDN 吞吐不足 ⇒ 「播一下、加载一下」。

---

## 2. 修法：正文输出原生 `<video>` 播放器页

### 2.1 关键约束
- **`java` 接口只在 `hasPreloadJs=true` 时注入**（`initJavascriptInterface` 里
  `if (!viewModel.hasPreloadJs) return`）。本源未设 `preloadJs` ⇒ 页内 JS **不能**依赖 `java.ajax`。
- 站方无 `Access-Control-Allow-Origin`，但 `loadDataWithBaseURL(baseUrl=文章URL)` ⇒ 同源，
  `XMLHttpRequest` 同源 GET 可行（真机 `java.get` 近似验证：818ms 返回 45839B 完整详情页，
  含 `strencode2`/`vbG` ⇒ 页内能解出新直链）。
- 签名 `&e=` ~2h 有效，`&f=` 必需；缓存正文的旧链过期后 302 跳回被墙 cdn77 域
  ⇒ 页内 `error` / `stalled` 自愈必须重取详情页，而不是复用旧链。

### 2.2 页内自愈逻辑
```
playing  → tries=0（正常播放清零）
waiting  → 仅提示"缓冲中"
error    → recover()
stalled  → 2.5s 防抖后若 !paused && readyState<3 才 recover()
             （避开 CDN 偶发 1~2s 尖刺误触发，防抖很关键）
timeupdate → 清掉 stall 定时器

recover(): 最多 3 次；同源 XHR GET PN_CFG.page + Cache-Control:no-cache
           → 正则 strencode2(...) → decodeURIComponent → src → 规范化双斜杠
           → V.src = 新链; V.load(); V.play()
```
`PN_CFG.page = baseUrl`（随线路走，不写死域）。

### 2.3 ★★ 必须踩的坑：页内 JS 不能直接内联进 Rhino 脚本
第一次实现把页内 JS 写成 `L.push('   var mm=t.match(/strencode2\\(["\\']...` 这类
**嵌在单引号字符串里的正则**（正则本身含 `'`），Rhino 解析整个 `ruleContent` 内层时
字符串提前闭合 ⇒ 真机 WS 报：
```
com.script.ScriptException: 语法错误
Source context: 99: '   var mm=t.match(/strencode2\\(["\\']([^"\\']+)["\\']\\))/' 
```
**正解 = 页内 JS 单独成文件，构建时 `base64.b64encode` 后内嵌**：
```js
L.push('var PN_CFG=' + JSON.stringify({page: page}) + ';');
L.push('try{var s=atob("<纯base64串>");var e=document.createElement("script");'
     + 'e.textContent=s;document.body.appendChild(e);}catch(err){}');
```
Rhino 侧只出现纯 `[A-Za-z0-9+/=]` 串，**零引号冲突**；`atob` 是浏览器 API
（Rhino 里 undefined 无所谓，它只是被拼进 HTML 文本，不执行）。

### 2.4 ★ 占位符不能撞注释（本轮第二次真机抓到的坑）
`rc_v7_inner.js` 注释里写了「PN_PAGE_B64 占位符」，代码里也有一处
`atob("PN_PAGE_B64")` ⇒ `replace('PN_PAGE_B64', b64, 1)` **只换了注释里那处**，
代码里仍是字面占位符，页面 `atob("PN_PAGE_B64")` 解码出乱码、自愈失效，
而且 WS 输出看不出异常（HTML 看起来正常）。

**正解 = 精确锚点替换 + 断言**：
```python
ANCHOR = 'atob("PN_PAGE_B64")'
assert INNER_NEW.count(ANCHOR) == 1
INNER_NEW = INNER_NEW.replace(ANCHOR, 'atob("' + page_b64 + '")', 1)
assert 'atob("PN_PAGE_B64")' not in INNER_NEW
assert re.search(r'atob\("[A-Za-z0-9+/=]{100,}"\)', INNER_NEW)
```
构建后必须**解码三层 Base64 回读**，确认占位符数 0、base64 长度 >100、解出的页内 JS
含 `XMLHttpRequest`/`PN_CFG` 且**不含 `java.`**。

---

## 3. 构建与验证闭环

- 只改 3 个字段：`ruleContent`（三层 Base64 只重编码**第 2 段**）、`sourceComment`、
  `lastUpdateTime`；其余 29 项字节级不变；署名校验层/错误信息层原样。
- 双版各自基于自己落库对象生成（E 版少 `enableReadRecord`）。
- `/saveRssSources` 数组 → `isSuccess:true` → `/getRssSources` 回读 **diff 0**。
- LT WS1123 / E WS1126 终验：正文输出**完整 HTML**（`<div class="pn-box">` +
  `<video preload="auto" src="...&f=...">` + `<style>` + `var PN_CFG={...}` +
  `atob("<3420B base64>")`），**无语法错误**；E 版 `PN_CFG.page` 自动跟随 a.26702.app。
- QuickJS `new Function(pageJs)` 编译通过（页内 JS 语法预检）。
- 同源重取反向验证：`java.get(详情页, {Referer, Cache-Control})` → 818ms / 45839B /
  `CAN_RESOLVE=YES`。

### 判据（视频源 WS 全绿看什么）
- 「内容页解析完成」前必须看到**完整 HTML 输出**（不是裸 URL、不是空行）。
- `<video` 与 `preload="auto"` 都在；`src` 带 `&f=` 签名。
- `PN_CFG.page` 与实际文章链接同域（同源 XHR 前提）。
- 出现 `语法错误` / `Exception` 一律不算绿。

---

## 4. 通用铁律

1. 「播一下、加载一下」≠「首字节慢」：要量**连续多个 Range 分片**的持续吞吐与尖刺，
   只看一次 HEAD 200 会误判。
2. 订阅源正文**原生支持 `<video>`**（`clHtml` 默认样式实锤）。输出裸 mp4 字符串
   会走文本/嗅探路径，不如给完整 HTML 播放器页。
3. 页内 JS 只要含正则/引号/反斜杠，**一律 base64 内嵌**（`atob`），别直接拼进 Rhino 脚本。
4. 占位符替换必须用**唯一精确锚点**，且构建后解码回读断言；撞注释会静默只换一处。
5. `java` 接口在订阅源 WebView 里**仅 hasPreloadJs=true 注入**；页内自愈优先用
   `loadDataWithBaseURL` 带来的**同源 XHR**（站方无 ACAO 也能用），别赌跨域 fetch。
6. `stalled` 自愈必须防抖（2.5s）+ `playing` 清零重试计数，否则 CDN 偶发 1~2s 尖刺
   会触发频繁换链，反而更卡。
7. CDN 吞吐贴码率时，换 host / 换档位 / 双斜杠规范化往往都无效；先做对照实验
   排除，再从**渲染链路**找结构性优化。
8. 诊断桩/中间版每轮覆盖落库 ⇒ 最后必须重存正式版并回读（本轮 3 次）。
