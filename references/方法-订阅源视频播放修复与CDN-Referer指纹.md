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

1. 抓详情页 `<source src>` → CDN 对照实验定 Referer 指纹
2. 查正文模板有无 `referrer never`（有 → 删）
3. 查 `loadWithBaseUrl`（false → baseUrl=null，Referer 全无，改 true）
4. 查链接时效（URL 内时间戳/重取签名轮换）→ 有时效必须页内自愈
5. 查缓存机制（rssArticle.description 永久缓存 → 不能指望重进文章刷新）
6. CDN 假视频（m3u8 提示片）→ loadedmetadata 时长判据
7. 偶发超时 → URL 选项 `,{"retry":2}`
8. 图床 404 → 先确认是否站内页面同样 404（站方故障，别改源）
