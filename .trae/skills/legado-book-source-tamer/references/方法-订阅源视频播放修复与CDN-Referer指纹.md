# 方法-订阅源视频播放修复与CDN-Referer指纹

> 来源：avjoy.top 订阅源「无法播放」修复实战（2026-10-30）。所有结论均经对照实验与 Legado 源码实锤。

## 一、案例背景

- 站点：`cn.avjoy.top`（AV视频站，JAVEngine系列镜像壳，同一后端 `en.avjoy.me`）
- 源类型：RSS 订阅源（type=0），正文用 `@js:` 生成 HTML + `<video>` 标签播放
- 故障现象：订阅源列表正常，点开视频无法播放
- 修复版本：v2.2（保存于 Legado App + `/workspace/avjoy_v2.json`）

## 二、根因链（三类根因 + 一类外部故障）

### 根因A：正文模板 `referrer never` → CDN 拒发真视频（本次主凶）

原模板 HTML head 里有：
```html
<meta name="referrer" content="never"/>
```
这会让 WebView 播放视频时**不发送 Referer**。而视频 CDN 有 Referer 指纹校验：

| Referer | 响应 |
|---|---|
| 无 / 空串 / 无关域(google.com) / `en.avjoy.me` | **200 + `application/vnd.apple.mpegurl`，内容是 10 秒提示片 m3u8**（`#EXTM3U` → `https://player.centercdn.top/tip.ts` → `#EXT-X-ENDLIST`），仅 143 字节 |
| `https://cn.avjoy.top`（origin 形式） | 200 + `video/mp4`，真视频（2.4GB，支持 Range 206） |
| `https://cn.avjoy.one`（同后端备用域） | 200 + `video/mp4`（通过） |

**排查指纹法**：视频"能播但只有几秒就结束"或"黑屏秒结束"，先抓 CDN 返回的 `Content-Type`：
- `video/mp4` = 真视频
- `application/vnd.apple.mpegurl` + 极短 body（143B）= 假 m3u8 提示片

**修法**：删除 `referrer never`。Legado RSS 正文渲染链（源码 `ReadRssActivity.initLiveData`）：
```kotlin
val baseUrl = if (rssSource?.loadWithBaseUrl == false) null else url
currentWebView.loadDataWithBaseURL(baseUrl, html, ...)
```
`loadWithBaseUrl=true` 时 WebView 子资源（`<video src>`）自动带 baseUrl（视频页 URL）为 Referer → CDN 校验通过。

### 根因B：正文永久缓存 × MP4 签名链接 2 小时过期

源码实锤（`ReadRssViewModel.kt`）：
```kotlin
// loadContent 成功后
rssArticle.description = body
appDb.rssArticleDao.insert(rssArticle)   // 永久入库
// refresh(): if (!rssArticle.description.isNullOrBlank()) return finish.invoke()  // 有缓存直接跳过
```
而 MP4 链接内嵌 10 位时间戳（`/(\d{10})/`），实测**约 2 小时过期**，且详情页每次请求返回的 CDN 域与签名都轮换（`vckeepw.top`/`vcjuligi.com`/`vcsheaye.cc`…同 IP 不同域）。⇒ 二次打开文章必然用缓存的过期链接。

**修法（页内自愈三件套，写进正文模板的 `<script>`）**：
1. **过期预检**：`urlTime(u)` 正则抽 URL 内时间戳，`Date.now()-t > 90min`（提前 30min 余量）→ 自动 recover
2. **假视频检测**：`loadedmetadata` 事件里 `video.duration < 30s`（正片至少 5 分钟，提示片 10s）→ recover
3. **error 兜底**：`video error` 事件 → recover

recover 实现（CORS fetch，已实测主站 `ACAO:*` 回显任意 Origin）：
```js
fetch(PAGE, {credentials:"omit", cache:"no-store"})
  .then(r=>r.text())
  .then(t=>{ var m=t.match(/<source[^>]*src="([^"]+)"/); ... })
```
- fetch 的 Referer = 当前页面 origin = 主站域 → CDN 校验通过（fetch 语义：跨域请求默认 `strict-origin-when-cross-origin`，发 origin）
- 主站详情页响应 `ACAO: *`（实测回显任意 Origin），fetch 可行
- 手动自救：双击标题区（`dblclick` 且 `clientY<60`）重置重试计数再 recover

### 根因C：搜索/列表请求偶发读超时

轮询测试 3 轮有 1 轮 read timeout（20s）。**修法**：sortUrl/searchUrl 每条追加 URL 选项 `,{"retry":2}`。
源码机制（`AnalyzeUrl`）：`paramPattern = \s*,\s*(?=\{)` 切分 URL 与选项，`replaceKeyPageJs` 先求值 `{{}}` 模板再切选项——`{"retry":2}` 紧跟在模板后不破坏解析（实测验证）。

### 外部故障：缩略图图床站方级 404

列表页全部缩略图域 `jre1*.7132p.net` 404（连 `sprite.jpg`/`logo.png` 都 404，站内所有页面如此）。这是站方图床故障/迁移，**源端无法修复**，仅能 `sourceComment` 注明 + 容错（Legado 封面 404 显示默认图，不影响功能）。判断技巧：**对比站内页面上该域的引用率**——站内页面自己引用的图都 404 = 站方故障，不是源的问题。

## 三、CDN Referer 指纹校验的通用排查法

1. 抓视频直链（详情页 `<source src>`）
2. 对照实验矩阵（requests stream 读 64 字节判断）：
   ```python
   tests = [
       ('无任何header', {}),
       ('仅UA', {'User-Agent': UA}),
       ('UA+Referer=主站origin', {'User-Agent': UA, 'Referer': 'https://主站'}),
       ('UA+Referer=主站完整路径', ...),
       ('UA+Referer=无关域', ...),
       ('UA+Referer=空串', {'User-Agent': UA, 'Referer': ''}),
   ]
   ```
3. 判据：`Content-Type=video/mp4` + 首 32 字节含 `ftyp` = 真视频；`#EXTM3U` 开头 = 假播放列表
4. 结论落法：
   - Referer 通过 → WebView 直接播（baseUrl 机制自动带），正文模板**不要**输出 referrer never
   - Referer 不通过 → 正文模板里用 CORS fetch 取流（需 CDN `ACAO:*`，先 OPTIONS/GET 验证）

## 四、RSS 订阅源（type=0）播放链路源码速查

```
列表: Rss.getArticles → AnalyzeUrl(sortUrl,page,key) → RssParserByRule.parseXML
      ruleNextPage=="PAGE"(不区分大小写) → nextUrl=sortUrl(带{{page}}模板,loadMore自动page+1)
      getItem() 里 title.isBlank() → 该条目被丢弃（可做过滤器）
正文: ReadRssViewModel.loadContent → Rss.getContentAwait → AnalyzeRule.getString(ruleContent)
      结果存 rssArticle.description 永久缓存（⚠️ 有时效内容必须页内自愈）
渲染: clHtml(content, style) → loadDataWithBaseURL(baseUrl=文章link, html)
      style 注入到第一个 </style> 之后；源 style 若无 </style> 则整体 append
WebView: upWebviewSettings 用 headerMap 的 UA（<js> header 求值结果）；enableJs 开 JS
注入: preloadJs 非空才注入 WebJsExtensions 桥（java.request('run',...)）；
      injectJs 在页面加载完后 evaluateJavascript（原源手势脚本找 id="video"）
登录: RssSource 继承 BaseSource，loginUrl/loginUi 与书源同协议（V1静态数组+viewName动态文本）
      ReadRssActivity 菜单 menu_login 可见性 = loginUrl 非空
保存: POST /saveRssSources（body=RssSource JSON 数组）/getRssSources 回读
```

## 五、修复版关键设计（可直接抄的模板骨架）

```javascript
@js:
var m = src.match(/<source[^>]*src="([^"]+)"[^>]*>/);   // 抓站方 source 标签
var vsrc = m ? m[1] : '';
var mh = src.match(/<h1[^>]*>([\s\S]*?)<\/h1>/);          // 标题（h1.0 也可用规则取）
var pageUrl = String(baseUrl).split('?')[0];              // 自愈用详情页地址
var html = [ '<!DOCTYPE html>', ...,
  '<video id="video" ...>',                                // id 必须 video（兼容原 injectJs 手势）
  '<script>',
  'var VURL=' + JSON.stringify(vsrc) + ';',               // JSON.stringify 转义防注入
  'var PAGE=' + JSON.stringify(pageUrl) + ';',
  // 过期预检 + 假视频检测 + error 兜底 + 双击手动刷新（见上文"页内自愈三件套"）
  '<\/script>' ].join('\n');
result = html;
```

⚠️ 注意：`<script>` 在 JS 数组字符串里必须写 `<\/script>`，否则提前闭合 HTML。

## 六、验证方法论（本次全链路五步模拟）

```python
# 1. 列表页 → 2. 详情页(抓<source>) → 3. <video>子资源请求(带视频页Referer) 
# → 4. fetch自愈(origin Referer) → 5. 自愈重取详情页(签名轮换确认)
# 全部断言 Content-Type=video/mp4 且字节头 ftyp
```
node 侧验证模板 JS：`new Function(...bindings, jsBody)` 模拟 Rhino 绑定求值，断言产物 HTML 的 12 项特征（VURL 嵌入/PAGE 常量/无 referrer/脚本闭合…）。

## 七、可复用清单（下次遇到"订阅源视频无法播放"）

### ★★番外二（261030 三轮·终版）：测速返回 0ms + 日志 InterruptedIOException

上一版用 `java.ajax` 测速仍有隐藏错误，用户实测反馈「0ms + timeout 日志」定位：

- **根因**：`java.ajax` 源码签名返回 **`String?`（响应体）**，不是 StrResponse！对返回值调 `.body()`/`.callTime()`：
  - String 上无此方法 → Rhino 抛异常 → catch 兜底 `String(r)` 恰好拿到 body（判活歪打正着通过）
  - `callTime` 恒 0 → **指纹 = 「成功域返回 0ms，失败域显示 ✗」**
  - 日志 `ajax(url) error + InterruptedIOException: timeout` 只是死域（icu/vip）的 AppLog 噪音，不是 bug 本身
- **正确测速原语 = `java.connect(url, headerStr, callTimeoutLong)` 返回真 StrResponse**：
  - `code()/body()/callTime()` 全部有效
  - 失败时 connect **不抛异常**，而是返回 body=异常堆栈文本的 StrResponse → 用 `indexOf('Exception')>-1||indexOf('timeout')>-1` 识别，取前 60 字符做诊断串
- **终版 probe 四路判定**：①connect 抛异常→`E:消息` ②堆栈识别→`E:诊断` ③HTTP 码非 200/500→`E:HTTPxxx` ④body<500→`E:内容异常`；活线返回 `callTime()` 毫秒
- **教训（通用）**：`java.ajax`(String?) / `java.connect`(StrResponse) / `getStrResponse` 系列返回类型必须逐个查源码签名，**凭直觉猜返回类型必然翻车**；mock 验证要覆盖"成功/超时堆栈/HTTP错误码/抛异常/多域聚合"五路
- 诊断串截断 60 字符（36 会把 "timeout" 尾巴切掉），换行用 `split(String.fromCharCode(10)).join(' ')`（避免正则转义被 Python/JSON 链路吃掉）

1. 抓详情页 `<source src>` → CDN 对照实验定 Referer 指纹
2. 查正文模板有无 `referrer never`（有 → 删）
3. 查 `loadWithBaseUrl`（false → baseUrl=null，Referer 全无，改 true）
4. 查链接时效（URL 内时间戳/重取签名轮换）→ 有时效必须页内自愈
5. 查缓存机制（rssArticle.description 永久缓存 → 不能指望重进文章刷新）
6. CDN 假视频（m3u8 提示片）→ loadedmetadata 时长判据
7. 偶发超时 → URL 选项 `,{"retry":2}`
8. 图床 404 → 先确认是否站内页面同样 404（站方故障，别改源）


## 八、番外三（261124 Jable 视频书源 type=4）：tip.ts 假片同源机制在「播放器直连 m3u8」场景的修法

> 来源：x99dh.github.io 导航 Jable 站 18 条线路的视频书源。与根因A同一 CDN 指纹，但触发链路不同——这次不是 WebView `referrer never`，而是**书源正文输出给 GSY/ExoPlayer 的 m3u8 URL 没带 Referer**。

### 站点链路
- 发布页 `x99dh.github.io` 的 `encodedData` → base64 → decodeURIComponent → JSON（32站）；`name==='Jable'` 取 18 条 `urls[]`（url 形如 `https://jable02.net/enter`，需剥 `/enter` 才得到线路根）。
- 列表 `.video-img-box`；搜索 `/search/{encodeURIComponent(key)}/{page}/`；分页 `/{path}/{page}/`。
- 详情页内联 `var hlsUrl = 'https://{line}/pumpres/{n},{token}/hls/{sig}/{ts}/{cat}/{id}/{id}.m3u8'`；同域 `/pumpres/` **302 到随机 CDN 子域**（每次不同：vcmathe.com / vcsheaye.cc 等）；重定向后是标准 AES-128 HLS（`#EXT-X-KEY`）。

### ★根因（同一 URL 只变 Referer 的严格对照实验）
| 请求 | 结果 |
|---|---|
| 裸 GET hlsUrl（App java.connect / 沙盒 curl 均然） | **200 + 143B**：`#EXTM3U` → `https://player.centercdn.top/tip.ts` → `#EXT-X-ENDLIST`（10秒假片） |
| 带 `Referer: https://jable02.net/videos/xxx/` 或 `https://jable02.net/` | **200 + 54062B**：`#EXT-X-KEY:METHOD=AES-128,...` 真片 |

与 avjoy 的 143B tip.ts 指纹完全一致 ⇒ 同一 CDN 防盗链家族。**关键差异**：type=4 视频源不经 WebView，Referer 必须进 `AnalyzeUrl.headerMap` 才会被 `player.mapHeadData = analyzeUrl.headerMap`（源码 VideoPlay.kt:154/285）注入播放器。

### 修法（正文 URL 选项注入 Referer，LT/E 双版通用）
```js
// ruleContent.content：
@js:(function(){
  var h=String(result);
  var m=h.match(/var hlsUrl = '([^']+)'/); if(!m||!m[1])return '';
  var u=m[1]; if(u.indexOf('http')!==0)return '';
  var ref=JB_base.call(this)+'/';   // 当前线路根，切线路后 Referer 自动跟随
  return u+',{"headers":{"User-Agent":"Mozilla/5.0 ... Chrome/124...","Referer":"'+ref+'"}}';
})()
```
★URL 选项必须**单花括号**（双花括号 `{{}}` 会被当模板二次 eval）；选项里的逗号是合法分隔符，AnalyzeUrl 按逗号拆出 headerMap。App 内 `java.ajax(带选项URL)` 实测返回 54062B 真片（tip 消失、`#EXT-X-KEY` 存在），debug_source 正文输出形态正确。

### 另一坑：目录污染（单视频站的相关推荐）
详情页有 23 张 `.video-img-box` 相关推荐卡；若 `ruleToc.chapterList` 用列表选择器会生成 23 章"别的视频"。正解 = `@js` 返回 `Packages.java.util.ArrayList`，只放 1 条本片 `{title, url:baseUrl}`，chapterName=$.title / chapterUrl=$.url。

### 验证纪律
- 探测 m3u8 真假的判据是**内容特征**（`indexOf('#EXT-X-KEY')>=0` 且无 `tip.ts`），不是 HTTP 200、不是 body 长度>0。
- 换线路/换视频后 Referer 必须跟随新域名——用 `JB_base()` 动态拼，别把主域写死。
- 未主动探测搜索频率；搜索间隔未设 `concurrentRate`（站方无已知限频）。
