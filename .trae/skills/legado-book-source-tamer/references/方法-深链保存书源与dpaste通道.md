# 方法：深链保存书源与 dpaste 通道

## ——从「上传中转」到「唤起导入」的完整闭环（书源 / 订阅源 / TTS 三件套）

> 沉淀日期：2026-09-16　｜　来源：**本轮真机端到端实测**（书源 545B 含 emoji/中文/反斜杠/双引号/换行/制表 → dpaste → 深链唤起 → 落库字段 md5 完全一致；订阅源正/反向双验证；TTS 单对象验证）
> 关联：[方法-书源交付质量闭环](方法-书源交付质量闭环.md)（第 9 节本文是它的完整展开）、[方法-详情页交互按钮选型树](方法-详情页交互按钮选型树.md)、[方法-HttpTTS朗读引擎与音色切换面板](方法-HttpTTS朗读引擎与音色切换面板.md)

---

## 目录

0. [一句话](#零一句话)
1. [★怎么唤起导入（本方法的核心，别只上传不唤起）](#一怎么唤起导入本方法的核心别只上传不唤起)
2. [三类资源的深链与格式差异（书源/订阅源/TTS）](#二三类资源的深链与格式差异书源订阅源tts)
3. [深链协议全谱（源码级）](#三深链协议全谱源码级)
4. [端到端链路拆解](#四端到端链路拆解)
5. [dpaste 中转通道（API 契约实测）](#五dpaste-中转通道api-契约实测)
6. [三条投递通道对照](#六三条投递通道对照)
7. [端到端实测记录（含反向验证）](#七端到端实测记录含反向验证)
8. [避坑清单 K1~K28](#八避坑清单-k1k28)
9. [可复用脚本](#九可复用脚本)
10. [验收 checklist](#十验收-checklist)
11. [案例档案](#十一案例档案)

---

## 零、一句话

完整交付是**两步**，缺一不可：

```
① 上传（中转）  → 把 JSON 变成一个可访问的 URL（dpaste 等）
② 唤起（导入）  → 用 legado:// 深链让 App 去拉这个 URL 并导入
```

**只做①不做② = 任务没完成。** 上传完只是得到一条链接，App 什么都不会发生。
②的实体就是这一行（书源）：

```javascript
java.openUrl('legado://import/bookSource?src=' + java.encodeURI(rawUrl));
```

一句话记：**深链是「投递」，dpaste 是「中转」，md5 是「验收」。**

---

## 一、★怎么唤起导入（本方法的核心，别只上传不唤起）

### 1.1 三步走

```
第一步  造文件       my_source.json                     （本地文件）
第二步  上传中转     POST https://dpaste.com/api/v2/    → https://dpaste.com/XXXX.txt
第三步  唤起导入     legado://import/bookSource?src=<encoded>   ← ★就是这一步
```

### 1.2 深链字符串怎么拼（只有两行）

```javascript
// rawUrl = dpaste 返回的 URL + ".txt"
var rawUrl = 'https://dpaste.com/BLDA6NNWY.txt';

// ★path 按资源类型换：bookSource / rssSource / httpTTS
var deepLink = 'legado://import/bookSource?src=' + java.encodeURI(rawUrl);

// 唤起
java.openUrl(deepLink);
```

★**`java.encodeURI` 不能省**。不编码时，URL 里的 `:` `/` 能侥幸过关，但一旦含 `#`、`&`、中文就会截断参数 → App 拿到半截 URL → 拉取失败或导入报错。

### 1.3 在 MCP `eval_js` 里唤起（照抄，最常用）

```javascript
// 工具调用：eval_js  { js: "...", url: "<任意已存在的书源URL即可，仅用于绑定运行时身份>" }
var raw = 'https://dpaste.com/BLDA6NNWY.txt';
var dl  = 'legado://import/bookSource?src=' + java.encodeURI(raw);
java.openUrl(dl);
JSON.stringify({ deeplink: dl, called: true });
```

**实测输出**：

```json
{"deeplink":"legado://import/bookSource?src=https%3A%2F%2Fdpaste.com%2FBLDA6NNWY.txt","called":true}
```

执行后手机屏幕会**弹出导入对话框**，用户点「确定」即完成落库。

> 注：`eval_js` 的 `url` 参数只是给脚本一个运行时身份，**不要求与被导入的源有任何关系**，随便填一个已存在的书源 URL 即可。

### 1.4 在书源规则里唤起（让别人一键导入你的另一个源）

`java.openUrl` 对 `legado://`/`yuedu://` 走**特判分支，直接 startActivity，不弹外部浏览器确认框**（`JsExtensions.kt:1252`）：

```javascript
// ① 详情页简介按钮（<usehtml> + <button @onclick:...>）
// ② 正文虚拟章节（ruleContent 里返回 java.openUrl(...)）
// ③ 订阅源 ruleContent 里
java.openUrl('legado://import/bookSource?src=' + java.encodeURI(raw));
```

前置条件（否则**静默无反应**）：
- 设置项 `blockSourceNavigation`（"阻止书源网页/视频跳转"）必须为**关**（`AppConfig.kt:41`，**默认关**）；
- 长度 `< 64 * 1024`（`openUrl` 有 `require`）。

### 1.5 唤起成功的证据链（怎么证明②真的发生了）

| 证据 | 命令 | 期望 |
|---|---|---|
| ★**HTTP 日志** | `get_http_logs` | 出现 `GET https://dpaste.com/XXXX.txt -> 200` |
| 弹窗 | 用户肉眼 | 出现「导入书源」对话框，条目数正确 |
| 落库 | `list_sources` / `get_source` | 能查到该源，字段与本地一致 |

**HTTP 日志是硬证据**——本轮实测：

```
#2351 2026-09-16T08:17:41.860Z GET https://dpaste.com/9Y2L4VJV6.txt -> 200 1147ms
#2353 2026-09-16T08:22:12.531Z GET https://dpaste.com/BLDA6NNWY.txt -> 200 1109ms
#2355 2026-09-16T08:26:44.680Z GET https://dpaste.com/BHFX2GBQF.txt -> 200 1273ms
```

看到这条 `GET ... -> 200`，就说明深链生效、App 已经去拉了。

### 1.6 手动唤起（不写代码的兜底）

| 方式 | 操作 | 吃什么 |
|---|---|---|
| **网络导入** | 书源管理 → ⋮ → 网络导入 → 粘贴 | raw URL **或整段 JSON**（★小源最快） |
| **扫码** | 书源管理 → ⋮ → 从二维码导入 | 扫到的**文本**直接当 source 传入 → QR 里放 **raw URL** |
| 外部浏览器 | 地址栏输入深链 | 需系统允许打开 App |

---

## 二、三类资源的深链与格式差异（书源/订阅源/TTS）

★★**这是最容易翻车的地方：三类资源的 URL 分支解析规则不同。**

| | 书源 | 订阅源 | TTS 朗读引擎 |
|---|---|---|---|
| **深链 path** | `/bookSource` | `/rssSource` | `/httpTTS` |
| **必需字段** | `bookSourceUrl` | `sourceUrl` | 无 URL 必需项，靠 `id` 主键 |
| **JSON 单对象** | ✅ 可以 | ❌ **报错**（见下） | ✅ 可以 |
| **JSON 数组** | ✅ 可以 | ✅ **必须** | ✅ 可以 |
| **`{"sourceUrls":[...]}`** | ✅ | ✅ | ❌ 不支持 |
| **URL 分支解析** | `isJsonObject \|\| isJsonArray` 都判 | ★**直接 `fromJsonArray`** | `isJsonObject` / `isJsonArray` 分别判 |
| **JS 源文本** | ✅ 支持 | ❌ | ❌ |
| **file:// URI** | ✅ | ✅ | ✅ |

### 2.1 ★订阅源：单对象会直接报错（本轮反向验证实锤）

`ImportRssSourceViewModel.importSourceUrl` 的 URL 分支**只调 `GSON.fromJsonArray`**，所以**订阅源哪怕只有一个，也必须写成数组**：

```kotlin
private suspend fun importSourceUrl(url: String) {
    ...
    okHttpClient.newCallResponseBody { ... }.decompressed().byteStream().use { body ->
        val sources = GSON.fromJsonArray<RssSource>(body).getOrThrow()   // ★必须是数组
        sources.forEach { source -> source.requireSourceUrl() }
        allSources.addAll(sources)
    }
}
```

**实测报错原文**（真机复现）：

```
ImportError:java.lang.IllegalStateException: Expected BEGIN_ARRAY but was BEGIN_OBJECT
at line 1 column 2 path $ See https://github.com/google/gson/blob/main/Troubleshooting.md#unexpected-json-structure
```

**正确写法**：

```json
[{"sourceUrl":"https://example.com","sourceName":"我的订阅源","enabled":false,
  "ruleArticles":"@js:[]","ruleTitle":"@js:''","ruleLink":"@js:''","ruleContent":"@js:''"}]
```

> 注意首尾的 `[` `]`。写成 `{...}` 就是上面那条报错。

**为什么会有这个差异**：订阅源在 App 里天然是"列表型"资源（一页多条），官方在 URL 通道上直接假定了数组；而书源/TTS 的单对象与数组分别判断。

### 2.2 TTS：单对象即可，靠 `id` 主键

```json
{"id":1789000000001,"name":"🔊我的TTS","url":"https://api.example.com/tts?text={{speakText}}",
 "contentType":"audio/mpeg","concurrentRate":"1/200","enabledCookieJar":false}
```

- `id` 是 `@PrimaryKey`，**建议显式给**（不给会取 `System.currentTimeMillis()`，每次导入都变成新条目）；
- 同名旧条目的更新判据：`source.lastUpdateTime < it.lastUpdateTime`；
- 深链：

```javascript
java.openUrl('legado://import/httpTTS?src=' + java.encodeURI('https://dpaste.com/HQUB2YAHN.txt'));
```

### 2.3 三件套速查

```javascript
// 书源
java.openUrl('legado://import/bookSource?src=' + java.encodeURI(raw));
// 订阅源（★内容必须是 JSON 数组）
java.openUrl('legado://import/rssSource?src='  + java.encodeURI(raw));
// TTS 朗读引擎
java.openUrl('legado://import/httpTTS?src='    + java.encodeURI(raw));
```

---

## 三、深链协议全谱（源码级）

### 3.1 格式

```
legado://import/{path}?src={urlencode(内容)}
yuedu://import/{path}?src={urlencode(内容)}      ← 等价别名
```

源码注释原文（`OnLineImportActivity.kt`）：

```kotlin
/**
 * 网络一键导入
 * 格式: legado://import/{path}?src={url}
 */
```

AndroidManifest（`exported="true"` + `BROWSABLE` 才能被外部唤起）：

```xml
<activity android:name=".ui.association.OnLineImportActivity"
    android:exported="true"
    android:theme="@style/AppTheme.Transparent">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="legado" />
        <data android:scheme="yuedu" />
    </intent-filter>
</activity>
```

### 3.2 path 全表（`onActivityCreated` 的 `when (it.path)`）

| path | 目标 | 备注 |
|---|---|---|
| `/bookSource` | 书源 | ★**万能入口**：JSON / JS 源 / URL / 内联文本通吃 |
| `/rssSource` | 订阅源 | ★URL 分支必须是数组（§2.1） |
| `/replaceRule` | 替换净化 | |
| `/textTocRule` | 目录规则 | 回调 key 叫 `txtRule` |
| `/httpTTS` | 朗读引擎 | |
| `/dictRule` | 词典规则 | |
| `/theme` | 主题 | |
| `/autoTask` | 定时任务 | |
| `/auto` | 自动嗅探 | ★**只吃 JSON / zip 备份，不吃 JS 源** |
| `/readConfig` | 阅读配置 | 有二次确认弹窗 |
| `/addToBookshelf` | 加书架 | 见[选型树](方法-详情页交互按钮选型树.md) |
| `/importonline` | 旧式 | 再按 `it.host` 分 `booksource`/`rsssource`/`replace` |
| 其它 | 兜底 | 一律走 `determineType` |

### 3.3 `src` 能塞什么（`importSource` 源码）

| src 形态 | 走向 | 说明 |
|---|---|---|
| 单对象 JSON `{...}` | `parseBookSourceJson` | 书源/TTS ✅，订阅源 ❌ |
| 数组 JSON `[{...}]` | 同上 | 三类通吃 |
| `{"sourceUrls":["url1","url2"]}` | 递归 `importSourceUrl` | 书源/订阅源；`allowSourceUrls` 为真时可用 |
| 绝对 URL | `importSourceUrl` | 下载后再判 JSON/JS |
| `file://` / `content://` | `isUri()` → `inputStream()` | 本地文件也能走深链 |
| 其它文本 | `JsSourceConfig.extract` | **JS 源**（仅书源） |

**`#requestWithoutUA` 后缀**：URL 末尾加它，导入器会把 UA 设为字符串 `"null"`。实测经 `encodeURI` 后该后缀仍存活。

```kotlin
if (url.endsWith("#requestWithoutUA")) {
    url(url.substringBeforeLast("#requestWithoutUA"))
    header(AppConst.UA_NAME, "null")
}
```

### 3.4 谁能唤起深链（源码确认的 5 处）

| 触发方 | 位置 |
|---|---|
| ★**规则 JS** | `JsExtensions.openUrl` 特判 `legado://`/`yuedu://` |
| 内置浏览器 | `WebViewActivity.shouldOverrideUrlLoading` |
| 详情页/底部浏览器/视频页 | `BookInfoActivity:640`、`BottomWebViewDialog:1217`、`VideoPlayerActivity:279` |
| 订阅源阅读页 | `ReadRssActivity.handleCommonSchemes` |
| `eval_js` / MCP | 同 `JsExtensions` |

★`java.openUrl` 的深链分支**直接 startActivity，不弹确认框**；普通 http(s) 会走 `OpenUrlConfirmActivity`（有确认框）。

---

## 四、端到端链路拆解

```
[点击/调用] legado://import/bookSource?src=<encoded>
   ↓  Android Intent.ACTION_VIEW（exported + BROWSABLE）
OnLineImportActivity
   ├─ intent.data.getQueryParameter("src")
   │     └─ ★src 为空 → 直接 finish()（无任何提示，最容易误判"深链不生效"）
   └─ when (it.path)
        "/bookSource" → ImportBookSourceDialog(src, finishOnDismiss = true)
   ↓
ImportBookSourceViewModel.importSource(text)
   ├─ isJsonObject / isJsonArray → parseBookSourceJson
   ├─ isAbsUrl                   → importSourceUrl  ← 拉 dpaste 就是这条
   ├─ isUri                      → inputStream
   └─ else                       → JsSourceConfig.extract（JS 源）
   ↓
comparisonSource()：与本地库比对 lastUpdateTime
   ├─ 本地没有 → isNew    → 默认勾选
   └─ 本地更旧 → isUpdate → 默认勾选（同 bookSourceUrl 会 REPLACE）
   ↓
用户点「确定」→ 落库
```

★**导入必然是「拉一次 HTTP + 弹窗 + 人点确定」**，所以它是半自动。想要全自动（不弹窗）只能走 MCP `save_source`。深链做不到，也不要承诺能做到。

---

## 五、dpaste 中转通道（API 契约实测）

### 5.1 API 契约（2026-09-16 逐项实测）

```
POST https://dpaste.com/api/v2/          ← ★必须带尾斜杠！漏了返回 API 文档 HTML（200）
参数：
  content       必填，粘贴正文（UTF-8）
  syntax        可选，如 json / text
  title         可选
  expiry_days   可选，整数，★范围 1~365
返回：
  201 Created
  Location 头 / 响应体 = https://dpaste.com/XXXXXXXXX
  raw 链接 = 上面 + ".txt"     ← ★不是 .raw
```

**实测结果矩阵**：

| 请求 | 结果 |
|---|---|
| `expiry_days=365` | 201 ✅ |
| `expiry_days=3650 / 1000 / 0 / -1` | 400 `{"errors":[{"expiry_days":"* expiry_days must be between 1 and 365"}]}` |
| `expiry_days=abc` | 400 `Enter a whole number.` |
| **不传** `expiry_days` | 400 `{"errors":[{}]}`（★匿名必须显式给） |
| 传 `expiration_days=30`（**拼错键名**） | **201 但静默按默认 7 天**——页面显示 "expires in 7 days"（对比 `expiry_days=30` 显示 30 days）★最阴的坑 |
| 不传 `content` | 400 `Missing required field 'content'` |

**其他实测事实**：

- **字节保真**：545B 源（中文 + emoji😀 + 反斜杠 + 双引号 + 换行 + 制表）上传后回读 **545B / md5 完全一致**，无 BOM、无追加尾换行、`Content-Type: text/plain; charset=utf-8`。
- **限频**：ToS 要求「带 User-Agent 且 ≤1 请求/秒」。实测快速连续 GET raw 第 4、5 次返回 **429 + HTML**。
- **匿名粘贴公开且无法删除**（删除 `DELETE /api/delete/<ID>` 需 API token 且必须是发布者）→ **别往 dpaste 放含账号密码/Cookie/私有 token 的源**。
- 裸 URL 返回 HTML 页面（13KB）；`.txt` 才是纯文本。

### 5.2 ★429 为什么报「XML 语法错误」

这是本通道**最经典的误诊**，本轮把机制打通了：

```
src 指向的 URL 返回 429 的 HTML
   ↓ importSourceUrl 下载（不校验状态码，429 也照收）
   ↓ importSourceText：内容不是 JSON
   ↓ JsSourceConfig.extract → RhinoScriptEngine.eval(HTML)
   ↓ org.htmlunit.corejs.javascript.Parser 解析 HTML
   ↓ 抛 InternalError: XML 语法格式错误      ← 实测原文
```

实测对照（`Parser().parse()`）：

| 内容 | 报错 |
|---|---|
| 429 的 HTML | `InternalError: XML 语法格式错误` |
| `{"bookSourceName":"x"}` | `InternalError: 在语句前面缺少 ";"` |

所以看到「XML 语法错误」先问：**src 那个 URL 是不是返回了 HTML？**（429 / 404 / 登录墙 / CF 挑战页都会）

**对策**：dpaste 的 raw **只拉一次**；要复核就间隔 ≥2 秒，或直接看 HTTP 日志。

### 5.3 谁在用

| 场景 | 做法 |
|---|---|
| 89KB hanime1 源 | dpaste + 深链导入（MCP 传参必坏） |
| aaawz 字体映射表（运行时加载） | dpaste 托管 365 天，规则里 `java.ajax` 拉取 + 变量缓存 |
| 小源（<10KB） | 直接 `save_source`，不必绕 |

---

## 六、三条投递通道对照

| | A 深链 | B 网络导入 | C 扫码 |
|---|---|---|---|
| 入口 | `legado://import/...` | 书源管理 ⋮ → **网络导入** | 书源管理 ⋮ → **从二维码导入** |
| 源码 | `OnLineImportActivity` | `showImportDialog()`（`menu_import_onLine`） | `qrResult.launch()`（`menu_import_qr`） |
| 需要 | 有人能点一下 | 手动粘贴（★有历史记录） | 一张 QR 图 |
| 能塞什么 | URL / JSON / 数组 / sourceUrls / file URI | 同左（hint="url"，**也吃整段 JSON**） | 扫到的**文本**直接当 source |
| 适用 | 分享、跨设备、书源内按钮 | **最稳，零外部依赖**（排障首选） | 跨设备、给别人 |

**两个实用推论**：

1. **C 通道扫到的文本直接喂 `ImportBookSourceDialog`** → QR 里放 **raw URL** 就行，**不必**放 `legado://`（放了反而可能被 `isUri()` 分支误吞）。QR 容量有限（App 自己会报 `text_too_long_qr_error`），**永远只放 URL，别放 JSON**。
2. **B 通道 = 内联通道**：输入框接受整段 JSON。dpaste 挂掉时的兜底就是「复制 JSON → 网络导入粘贴」。

---

## 七、端到端实测记录（含反向验证）

### 7.1 书源（正向 ✅）

```
① 造源 545B，故意塞满转义敏感字符
   {"bookSourceName":"🔗深链通道测试源", ...
    "bookSourceComment":"字节校验:中文/emoji😀/反斜杠\\/双引号\"/单引号'/换行\n第二行\t制表"}
② 上传  POST https://dpaste.com/api/v2/ (syntax=json, expiry_days=365)
   → https://dpaste.com/BLDA6NNWY.txt
③ 沙盒校验  545B / md5 47418196301fad64d364a86df1091c8c ↔ 远端一致 ✅
④ 唤起  java.openUrl('legado://import/bookSource?src=' + encodeURI(raw))
⑤ 证据  HTTP 日志 #2353 GET https://dpaste.com/BLDA6NNWY.txt -> 200 1109ms
        list_sources → 出现「🔗深链通道测试源」，enabled=false（与文件一致）
⑥ ★字节级验收  eval_js 回读 bookSourceComment
   本地 39 字符 / 86 字节 / md5 d6de8c6ec64b23b4877f48668358ada8
   真机 40 字符 / 86 字节 / md5 d6de8c6ec64b23b4877f48668358ada8  ✅ 字节完全一致
   （字符数差 1 = emoji 在 Rhino 里占 2 个 UTF-16 单元，见 K18）
   emoji / 反斜杠 / 双引号 / 换行 / 制表 全部 has_* = true
```

### 7.2 订阅源（★反向 + 正向）

| 用例 | 内容 | 结果 |
|---|---|---|
| **反向** 单对象 `{...}` | 227B → `dpaste.com/BHFX2GBQF.txt` | ❌ `ImportError: java.lang.IllegalStateException: Expected BEGIN_ARRAY but was BEGIN_OBJECT at line 1 column 2 path $` |
| **正向** 数组 `[{...}]` | 301B → `dpaste.com/3MT87CHZU.txt` | ✅ 弹窗正常，可导入 |

**反向验证的价值**：它证明了 §2.1 的源码推断——**订阅源的 URL 分支强制数组**。先跑预期失败的用例，再跑修正后的用例，才能确认「修的是对的那个原因」。

### 7.3 TTS 朗读引擎（正向 ✅）

```
239B → https://dpaste.com/HQUB2YAHN.txt
java.openUrl('legado://import/httpTTS?src=' + encodeURI(raw))  → 弹窗正常
（单对象即可，与订阅源相反）
```

### 7.4 本轮实测的三条深链（留档）

```javascript
// 书源
legado://import/bookSource?src=https%3A%2F%2Fdpaste.com%2FBLDA6NNWY.txt
// 订阅源（内容必须是数组）
legado://import/rssSource?src=https%3A%2F%2Fdpaste.com%2F3MT87CHZU.txt
// TTS 朗读引擎
legado://import/httpTTS?src=https%3A%2F%2Fdpaste.com%2FHQUB2YAHN.txt
```

---

## 八、避坑清单 K1~K28

### 唤起（最容易漏）

| # | 坑 | 对策 |
|---|---|---|
| K1 | ★**只上传 dpaste 不唤起** → App 毫无反应，任务等于没做 | 上传后必须再发深链（§1.3） |
| K2 | `src` 忘写/为空 → Activity 直接 `finish()`，**毫无提示** | 先确认 `?src=` 存在且非空 |
| K3 | src 里的 `#`、`&`、中文没编码 → 参数截断 | 一律 `java.encodeURI`（JS）/ `quote(raw, safe="")`（Python） |
| K4 | path 写错（如订阅源写成 `/bookSource`） | 按 §2.3 速查表 |
| K5 | `path` 用 `/auto` 却传 JS 源 | `/auto` 只嗅探 JSON/zip；**JS 源用 `/bookSource`** |
| K6 | 以为 `/bookSource` 只吃 JSON | 它 JSON / JS / URL / file URI 全吃，**万能入口** |
| K7 | 以为深链能全自动 | 深链**必然弹窗等人点**；全自动走 `save_source` |
| K8 | 设置的 `blockSourceNavigation` 打开后书源内 `java.openUrl` 静默失效 | 默认关；排障先查该开关 |
| K9 | `java.openUrl` 参数 ≥64KB | 深链里塞 URL，别塞整份 JSON |
| K10 | 别的 App 抢注 `legado://` | 少见；用 B 通道兜底 |
| K11 | 唤起后不复核 | 看 HTTP 日志 + `get_source` 比对 |

### 格式（按资源类型分）

| # | 坑 | 对策 |
|---|---|---|
| K12 | ★**订阅源用单对象** → `Expected BEGIN_ARRAY but was BEGIN_OBJECT` | 订阅源**永远写数组** `[{...}]` |
| K13 | 书源/TTS 写成数组却只想导一个 | 可以，三类都吃数组 |
| K14 | TTS 不写 `id` → 每次导入都是新条目 | 显式给固定 `id`（主键） |
| K15 | `{"sourceUrls":[...]}` 用在 TTS | TTS 不支持该形态 |
| K16 | 订阅源缺 `sourceUrl` | 报「不是订阅源」 |

### dpaste 侧

| # | 坑 | 对策 |
|---|---|---|
| K17 | API 漏尾斜杠 → 返回 API 文档 HTML（200） | 一律 `https://dpaste.com/api/v2/` |
| K18 | 用 `expiration_days`（拼错）→ **201 但只有 7 天** | 正确键名 `expiry_days`，范围 **1~365** |
| K19 | 匿名不传 `expiry_days` → 400 | 显式给 `365` |
| K20 | 用 `.raw` 拿原文 | 是 `.txt` |
| K21 | 快速重复 GET → 429 HTML | ≤1 请求/秒；**raw 只拉一次** |
| K22 | 匿名粘贴**无法删除**且公开 | 含账号/密码/Cookie/token 的源不要上 dpaste |
| K23 | 365 天到期链接失效 | 长期分发自建托管；本地留 JSON 备份 |
| K24 | 「XML 语法错误」当成源写坏了 | 先看 src 是否返回 HTML（429/404/CF 页），见 §5.2 |

### 校验/工程侧

| # | 坑 | 对策 |
|---|---|---|
| K25 | **`java.md5Encode(byte[])` 不存在** → 传 byte[] 得到**错误结果**（实测 `6fb5e9b4…` ≠ 正确 `504744b9…`，且不报错） | 只传 String；`MD5Utils` 只有 `(String?)`/`(InputStream)` 两个重载 |
| K26 | 用 `String.length` 比长度 | Rhino 是 **UTF-16**，emoji 差 1；**只比 UTF-8 md5 与字节数** |
| K27 | 以为 `getBytes('UTF-8')` 能用 | 必须 `new Packages.java.lang.String(s).getBytes(Charset.forName('UTF-8'))` |
| K28 | 沙盒能拉 ≠ 手机能拉 | dpaste 一般可达；被墙时用 B 通道内联粘贴 |

---

## 九、可复用脚本

### 9.1 `scripts/dpaste_upload.py`（上传 + 字节校验 + 生成深链，一把梭）

```bash
# 书源（默认）
python3 scripts/dpaste_upload.py my_source.json

# 订阅源（★内容记得写成数组）
python3 scripts/dpaste_upload.py my_rss.json --path rssSource

# TTS 朗读引擎
python3 scripts/dpaste_upload.py my_tts.json --path httpTTS

# 已有 raw URL，只为它生成深链（不重传）
python3 scripts/dpaste_upload.py --deeplink-only https://dpaste.com/XXXX.txt --path rssSource
```

输出：

```
file    : my_source.json (545 bytes)
dpaste  : https://dpaste.com/BLDA6NNWY
raw     : https://dpaste.com/BLDA6NNWY.txt
local   : 545 bytes md5 47418196301fad64d364a86df1091c8c
remote  : 545 bytes md5 47418196301fad64d364a86df1091c8c ct=text/plain; charset=utf-8
VERIFY  : PASS ✅ 字节级一致
deeplink: legado://import/bookSource?src=https%3A%2F%2Fdpaste.com%2FBLDA6NNWY.txt

手机侧唤起（MCP eval_js）：
  java.openUrl('legado://import/bookSource?src=https%3A%2F%2Fdpaste.com%2FBLDA6NNWY.txt');
之后用 get_http_logs 看 GET .../BLDA6NNWY.txt -> 200 作为深链生效的硬证据。
结果已留档: dpaste_result.json
```

**脚本会直接把「唤起那一行」打印出来**，复制进 `eval_js` 即可。

### 9.2 手机侧唤起（MCP `eval_js`）

```javascript
var raw = 'https://dpaste.com/BLDA6NNWY.txt';
java.openUrl('legado://import/bookSource?src=' + java.encodeURI(raw));
```

### 9.3 导入后字节级复核（MCP `eval_js`，绑定刚导入的源）

```javascript
var out = {};
function gv(o,k){ var f=o[k]; return (typeof f==='function') ? f.call(o) : f; }   // Kotlin 属性双兼容
var c = String(gv(source,'bookSourceComment'));
out.bytes = new Packages.java.lang.String(c)
              .getBytes(Packages.java.nio.charset.Charset.forName('UTF-8')).length;
out.md5   = String(java.md5Encode(c));      // ★只传 String（K25）
out.chars = c.length;                        // UTF-16，别用来判一致（K26）
JSON.stringify(out);
```

---

## 十、验收 checklist

**上传阶段**

- [ ] `POST https://dpaste.com/api/v2/`（尾斜杠）
- [ ] 带 `content` + `syntax=json` + `expiry_days=365`
- [ ] 拿到 201 与 URL，raw = URL + `.txt`
- [ ] **沙盒侧比对字节数 + md5**
- [ ] 订阅源内容**是数组**（`[{...}]`）
- [ ] 内容不含账号/密码/Cookie/token

**唤起阶段**

- [ ] ★**已发出深链**（不是只上传）
- [ ] `src` 存在、已 `encodeURI`、path 与资源类型匹配
- [ ] `get_http_logs` 看到 `GET <raw> -> 200` ← **硬证据**
- [ ] 弹窗里条目数/名称符合预期

**落库阶段**

- [ ] 用户点「确定」，能查到（`list_sources` / 订阅源列表 / 朗读引擎列表）
- [ ] 字段与本地文件一致（`get_source` / 回读 md5）
- [ ] `check_source` 通过（书源）
- [ ] 清理测试源

---

## 十一、案例档案

| 站点/项目 | 资源 | 通道 | 规模 | 关键点 |
|---|---|---|---|---|
| **本轮测试源** | 书源 | dpaste + 深链 | 545B | 转义敏感字符全覆盖，md5 端到端一致 |
| **本轮测试源** | 订阅源 | dpaste + 深链 | 301B | ★反向验证：单对象必失败，必须数组 |
| **本轮测试源** | TTS | dpaste + 深链 | 239B | 单对象即可 |
| hanime1.me 视频源 | 书源 | dpaste + 深链 | 89KB | 超过 MCP 舒适区，深链是唯一稳的方式 |
| aaawz.cc 字体映射表 | 数据托管 | dpaste | 20KB+ | 运行时 `java.ajax` 拉取 + 哨兵校验 + 变量缓存 |
| ppxsw / nicomanga / wn10 | 书源 | 直连 `save_source` | 8~12KB | MCP 体积/转义上限附近；>10KB 建议转 dpaste |
| zhaoshu.la | 书源 | 深链（加书架） | — | `/addToBookshelf` 形态 |

---

> **一页口诀**
> **上传只是半程，唤起才算交付。**
> `java.openUrl('legado://import/{path}?src=' + java.encodeURI(raw))`
> path 三兄弟：`bookSource` / `rssSource` / `httpTTS`。
> ★订阅源永远写数组，书源 TTS 单对象也行。
> `api/v2/` 带尾斜杠，`expiry_days` 1~365；raw 是 `.txt` 且**只拉一次**。
> 429 会伪装成「XML 语法错误」。
> 硬证据 = HTTP 日志里的 `GET .../xxx.txt -> 200`。
> `md5Encode` 只吃 String，长度只比字节。
> 深链必弹窗等人点，全自动还得 `save_source`。
