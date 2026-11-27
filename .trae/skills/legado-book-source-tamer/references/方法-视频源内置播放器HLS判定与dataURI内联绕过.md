# 方法：视频源内置播放器 HLS 判定与 data URI 内联绕过（Sigma 法）

> 沉淀日期：2026-11-28 ｜ 来源：2048ai2（Sigma 视频）拆解 + 麻豆短剧对照；Legado-team / Legado-E 双端实测正常
> 关联：[方法-视频书源完全指南.md](方法-视频书源完全指南.md)、[方法-视频书源播放本地解密完全指南.md](方法-视频书源播放本地解密完全指南.md)、[方法-proxy类接口path必须相对路径与SPA逆向API域.md](方法-proxy类接口path必须相对路径与SPA逆向API域.md)

## 〇 一句话

内置 ExoPlayer 判 HLS 只看 **URI path 后缀 / mimeType**；Legado 的 `createMediaItem` 没有 `setMimeType`，所以只看 path。  
当站点只给 `/m3u8/proxy?path=xxx.m3u8` 这类 **path 不以 `.m3u8` 结尾**的取流接口时，在 `ruleContent` 里把已经取到的 m3u8 文本 base64 成：

```text
data:/stream.m3u8?;base64,<m3u8文本>
```

让 URI 的 **path 段以 `.m3u8` 结尾**，内置播放器就会走 HlsMediaSource。  
**不需要 WebView、不需要 hls.js、不需要本地解密、不需要代理。**

> 结论修正：旧版《方法-视频源正文构造HTML播放器页绕过内置ExoPlayer限制》认为“内置 ExoPlayer 认不了非常规 URL，只能外置/WebView”——该结论已被 2048ai2（Sigma 视频）证伪。内置播放器仍可用，正解就是本文件的 data URI 内联 HLS。

---

## 一、源码级根因

### 1.1 HLS 判定只看两样东西

```kotlin
// Legado ExoPlayerHelper.kt
fun createMediaItem(url: String, headers: Map<String, String>): MediaItem {
    val formatUrl = url + SPLIT_TAG + GSON.toJson(headers, mapType)
    return MediaItem.Builder().setUri(formatUrl).build()
}
```

- 只 `setUri(formatUrl)`，**没有 `setMimeType`**。
- Media3 `DefaultMediaSourceFactory` 的规则：
  - URI path 以 `.m3u8` 结尾，或
  - `mimeType == MimeTypes.APPLICATION_M3U8`
  - → `HlsMediaSource`；否则 → `ProgressiveMediaSource`。
- Android 官方文档明确：URI 不以 `.m3u8` 结尾时，必须显式 `setMimeType(MimeTypes.APPLICATION_M3U8)`。Legado 没设，所以**只能靠 path 后缀**。

### 1.2 本站为什么必然不播

```text
https://mdaiapi.2346dv1m.work/api/v1/m3u8/proxy?path=jpd/.../xxx.m3u8
```

- `Uri.path` = `/api/v1/m3u8/proxy`
- `.m3u8` 只在 query 里
- `getLastPathSegment()` = `proxy`
- → `ProgressiveMediaSource` → 把 m3u8 文本当普通媒体文件解析 → 加载一下就停。

### 1.3 旧归因纠正

之前把“弹窗能播、内置不播”归因成三域分离 / `auth_key` 时效 / CORS，**均非根因**：

- 原生 ExoPlayer / OkHttp **不做浏览器 CORS 检查**；
- KEY 与 TS 在 m3u8 文本里都是绝对 `https://` URL；
- `auth_key` 是取正文时现生成的，不是缓存旧签名；
- 决定性对照：**同一份 m3u8 文本，直接给 URL 不播，包成 data URI 就播**。

CORS 只卡 WebView 里的 hls.js，不卡原生播放器。两者不要混为一谈。

---

## 二、首选解法：data URI 内联 HLS（Sigma 法）

### 2.1 五步链路

```text
ruleToc 归一化每集 URL（path 不必是 .m3u8，只要能返回 m3u8 文本）
  → Legado 请求该 URL，result = m3u8 正文
  → ruleContent 校验 #EXTM3U / KEY / 分片 / 体积
  → 返回 data:/stream.m3u8?;base64,<payload>
  → VideoPlay 交给 ExoPlayer
  → path=/stream.m3u8 ⇒ HlsMediaSource
  → DataSchemeDataSource 解码 base64
  → KEY/TS 是绝对 URL，直接由原生网络栈加载
```

### 2.2 URI 解剖（最关键的一条）

```text
data:/stream.m3u8?;base64,I0VYVE0zVQo...
└scheme┘ └──path──┘ └──query──┘
```

- `Uri.parse()` 后 `path = /stream.m3u8`，`getLastPathSegment() = stream.m3u8`；
- Legado 追加的 `🚧{headers}` 在 query 末尾，**不影响 path 后缀**；
- `ResolvingDataSource` 会剥掉 `🚧{headers}`，还原 data URI；
- `DefaultDataSource` 对 `data:` scheme 使用 `DataSchemeDataSource` 解码 base64。

**反例：**

```text
data:application/vnd.apple.mpegurl;base64,...
```

它的 path 是 `application/vnd.apple.mpegurl`，**没有 `.m3u8` 后缀**，依然会被当 Progressive。  
所以必须写成 `data:/stream.m3u8?;base64,...`。

### 2.3 `ruleContent` 模板

```js
@js:(function(){
  var u = String(baseUrl || '').trim();

  // 已经是 .m3u8 / .mp4 直链：交回原 URL，让播放器自己判
  if (!/^https?:\/\//i.test(u) || /\.(m3u8|mp4)$/i.test(u.split(/[?#]/)[0])) {
    return u;
  }

  var body = String(result || '').replace(/^\uFEFF/, '');

  // 必须是 m3u8 文本，且不能太大（Sigma 实测用 256KB 上限）
  if (!/^#EXTM3U(?:[\r\n]|$)/.test(body) || body.length > 262144) {
    return u;
  }

  var lines = body.split(/\r?\n/);
  var hasMedia = false;

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim();
    if (!line) continue;

    if (line.charAt(0) !== '#') {
      // data URI 是 opaque origin，相对分片无法解析，必须绝对 https
      if (!/^https:\/\//i.test(line)) return u;
      hasMedia = true;
    } else {
      // KEY / SERVER-URI 也必须绝对 https，否则回退
      var m = line.match(/(?:^|[:,])\s*(?:URI|SERVER-URI)\s*=\s*"?([^",]+)"?/i);
      if (m && !/^https:\/\//i.test(m[1])) return u;
    }
  }

  if (!hasMedia) return u;

  var b64 = String(java.base64Encode(body) || '').replace(/\s+/g, '');
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(b64)) return u;

  // ★ path 必须是 /stream.m3u8
  return 'data:/stream.m3u8?;base64,' + b64;
})()
```

### 2.4 `ruleToc` 归一化模板

目标不是让章节 URL 直接可播，而是让 Legado 取正文时拿到**纯 m3u8 文本**：

```js
function toM3u8TextUrl(v) {
  var u = String(v || '').trim();
  if (!u) return '';

  if (/^\/\//.test(u)) u = 'https:' + u;

  var raw = u.replace(/^https?:\/\/[^/?#]+/i, '');
  var m = raw.match(/[?&]path=([^&#]+)/);
  var path = m ? decodeURIComponent(m[1]) : raw.split(/[?#]/)[0];
  path = path.replace(/^\/+/, '');

  // mp4 直链：走 Progressive，原样返回
  if (/\.mp4$/i.test(path)) return u;

  if (!/\.m3u8$/i.test(path)) return '';

  // 已经是 .m3u8 直链
  if (/^https?:\/\//i.test(u) && !m) return u;

  // 换成目标站“能返回 m3u8 文本”的接口
  return 'https://<站点取流网关>/m3u8/decode/by/path?path=' + encodeURIComponent(path);
}
```

> 若站点同时提供 `/m3u8/proxy?path=` 与 `/m3u8/decode/by/path?path=`，两者返回结构通常一致；选一个能稳定返回 m3u8 文本的即可。  
> 2048ai2 实测：两者返回同结构（KEY/TS 均绝对 URL），差别只在返回形态，不在接口。

### 2.5 四个硬约束

1. **path 必须含 `.m3u8`**：`data:/stream.m3u8?;base64,...`，不能写成 `data:application/vnd.apple.mpegurl;base64,...`。
2. **KEY / TS 必须绝对 `https://`**：data URI 没有可用的 base URI，相对地址无法解析。
3. **体积可控**：m3u8 文本太大（Sigma 用 256KB 上限）时回退，避免把超长内容塞进章节正文。
4. **只包 m3u8 文本**：`.mp4` 直链直接 return；HTML/JSON 错误页绝不包。

### 2.6 为什么不需要 CORS / 本地文件 / 代理

| 关注点 | HTML + hls.js | data URI 内联 HLS |
|---|---|---|
| 播放器 | WebView 内 hls.js | 原生 ExoPlayer |
| CORS | 必须 ACAO / 真实 Origin | 原生 OkHttp 不查 CORS |
| Origin | 必须 `startBrowser` 三参给真实域 | 不涉及 |
| 本地文件 | 可选（解密 TS/MP4） | 不需要 |
| 代理 | 可选中转 | 不需要 |
| 选集 | 页面按钮 | 内置播放器章节列表 |

### 2.7 实测记录

- 2048ai2（Sigma 视频）：`bookSourceType=4`，`ruleToc` 走 `gwbe.../m3u8/decode/by/path?path=`，`ruleContent` 返回 `data:/stream.m3u8?;base64,...`；Legado-team 与 Legado-E **双端正常**。
- 同一站点、同一份 m3u8：早期 type=4 直接返回 proxy URL → 不播；最终 type=0 + WebView hls.js → 能播但走 WebView；data URI 内联 → 内置播放器正常。
- 结论：差别只在**正文返回形态**，不在接口、不在域名、不在 `auth_key`。

---

## 三、备选解法：HTML 播放器页（需要自定义 UI 时）

### 3.1 什么时候用

- 需要选集网格、倍速按钮、自定义样式；
- m3u8 含相对 KEY/TS 且无法改写成绝对；
- 需要前端解密 / 特殊播放器（hls.js、h265web.js 等）；
- 内置播放器的章节列表不足以满足交互。

### 3.2 三条通道

1. **`java.startBrowser(url, title, html)` 三参**：`WebViewActivity` 直接渲染 HTML，Origin = 传入的真实站点域；CORS 最可控，首选。
2. **详情页简介 `ruleBookInfo.intro` 用 `<useweb>`**：点开详情页即显示播放器，绕开正文/内置播放器；HTML 末尾补一个 `<` 作为终止符。
3. **type=0 文本源正文 `startBrowser` 三参**：文本阅读器正文 context 不被 `blockSourceNavigation` 拦截；但阅读器预加载会重复执行，必须做时间窗口去重。

### 3.3 关键坑（本案例踩过）

- `data:text/html` 是 **opaque origin（Origin: null）**，跨域 m3u8/key 会被 CORS 拦；**不要再用 data URI HTML 做播放页**。
- **HTTP 日志 200 ≠ WebView 能用**：CORS 拦截发生在响应到达后；必须用 headless webView 同步 XHR 实测目标 Origin。
- hls.js **必须 CDN 外链**，禁止内联（LissAV 内联 543KB 导致 App 崩溃前科）。
- 模板占位符与替换代码必须逐字符核对；debug 看 `var EPISODES=` 后面必须是真实数组，不能是 `__EPISODES__` 字面量。
- 预加载去重：`source.get/put` + 8 秒时间窗口；`source.get` 返回 null 是 JsNull（truthy），必须 `String(x||'')` 归一化。
- `coverDecodeJs` 给 Java `byte[]` 元素赋值 255 会抛“无法将 255 转换为 java.lang.Byte”；用 `ByteArrayOutputStream.write(int)`。

### 3.4 为什么不要把它当首选

HTML 方案链路长（WebView / hls.js / CORS / Origin / 预加载去重 / 占位符），调试成本远高于 Sigma 法。  
**先判断能否用 data URI 内联 HLS；能用就不要再上 WebView。**

---

## 四、决策树

```text
视频源不播
├─ chapterUrl path 以 .m3u8 结尾，KEY/TS 绝对
│  → 直接 return URL 给内置播放器
├─ chapterUrl 是代理接口，result 是 m3u8 文本
│  ├─ KEY/TS 绝对
│  │  → ★ data URI 内联 HLS（首选）
│  └─ KEY/TS 相对
│     → 先按已知 host 改写绝对；改不了再走 HTML/外置
├─ result 是 master playlist，变体是相对地址
│  → 改写绝对后包装；否则回退
├─ 需要自定义选集/倍速 UI
│  → HTML 播放器页（startBrowser 三参 / useweb / type=0）
├─ H265 / bytevc2 / 非标准容器
│  → 外置播放器或本地解密 file://
└─ 以上都不满足
   → 不要硬闯内置播放器
```

---

## 五、排查清单（视频源不播 8 步）

1. `debug_source` 看 **chapterUrl 的 path**，不是看 query 里有没有 `.m3u8`。
2. 看 `result` 是否以 `#EXTM3U` 开头。
3. 看 KEY 行 `URI=` 与 TS 行是否绝对 `https://`。
4. 同一份 m3u8 文本做对照：直接 return URL vs data URI 包装。
5. 检查 data URI 是否是 `data:/stream.m3u8?;base64,...`（path 必须 `.m3u8`）。
6. 检查 m3u8 体积是否超过上限、是否是 master playlist。
7. 检查 source header 的 Referer/UA 是否被 KEY/TS 需要。
8. LT / E 双端真机实测；HTTP 200、debug 成功都不等于播放成功。

---

## 六、反模式

- 把 `/m3u8/proxy?path=xxx.m3u8` **直接 return** 给内置播放器。
- 因为不播就归因 `auth_key` 时效 / 三域分离 / CORS。
- 写成 `data:application/vnd.apple.mpegurl;base64,...`（path 没有 `.m3u8`）。
- data URI m3u8 里保留相对 KEY/TS。
- 在 `bookSourceType=4` 正文里用 `startBrowser` / `<useweb>`（会被 VideoPlay 拦截）。
- 内联大段 hls.js（内存崩溃前科）。
- 用 `data:text/html` 做播放页（Origin: null，CORS 拦截）。

---

## 七、适用边界

- **适用**：标准 HLS（TS + AES-128），KEY/TS 绝对可达，m3u8 体积可控。
- **不适用**：H265 / bytevc2 / DRM-CENC / 需要前端解密的流 / master playlist 相对变体未改写。
- **缓存提醒**：data URI 内容随章节正文缓存；若站点 `auth_key` 极短效，重播可能用到旧文本，需要刷新正文或缩短缓存。
- **最终验证**：Legado-team + Legado-E 双端真机；本方法已在 2048ai2（Sigma 视频）双端实测正常。
