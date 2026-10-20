# 方法：登录UI V2 动态渲染 + useweb/usehtml/md + 发现页交互控件 + UrlOption 全字段

> 本文覆盖 Legado 相对较新、文档稀少的一批能力。全部结论来自 **App 源码逐行核对 + App 内 eval_js 实测**。
> 目标：把"能做什么 / 怎么写 / 边界在哪 / 怎么排错"一次讲清。

---

## 一、登录 UI V2：协议化的动态登录面板

### 1.1 是什么

传统 `loginUi` 是一个 **JSON 数组**（静态行）。V2 是**协议对象**：

```jsonc
"loginUi": "{\"version\":2}"
```

只要有 `version: 2`，App 就走 V2 分支（`LoginUiV2.isV2`）。
此时 `loginUi` 只当"标记"，真正的界面由 **`loginUrl` 里的 `loginUi()` 函数动态返回**。

### 1.2 判定与校验（源码 LoginUiV2.kt）

```kotlin
const val MARKER = """{"version":2}"""

fun isV2(loginUi: String?): Boolean {
    val text = loginUi?.trim() ?: return false
    if (!text.startsWith("{")) return false        // 必须以 { 开头
    val obj = GSON.fromJsonObject<JsonObject>(text).getOrNull() ?: return false
    return runCatching { obj.get("version")?.asInt == 2 }.getOrDefault(false)
}
```

**实测判定表**：

| loginUi | isV2 |
|---|---|
| `{"version":2}` | ✅ true |
| `{"version":2,"rows":[]}` | ✅ true（rows 内容被忽略） |
| `[{"type":"text"}]` | ❌ false（是数组，走 V1） |
| `{"version":1}` | ❌ false |

> 注意：**V2 的 loginUi 里写的 rows 不会被渲染**。真正的 rows 来自 `loginUi()` 的返回值。
> 所以 loginUi 只写 `{"version":2}` 即可，别塞多余内容。

### 1.3 两个必须实现的函数

`loginUrl` 里要同时定义 `loginUi` 和 `loginAction`（源码 `BaseSource.evalLoginUiV2` / `evalLoginActionV2`）：

```javascript
// 渲染：入参 state，返回 {rows:[...]} 的 JSON 字符串
// 源码实际执行： "$loginJs\nloginUi(JSON.parse(String(__loginState)))"
function loginUi(state) {
  return JSON.stringify({ rows: [ ... ] });
}

// 动作：入参 (action名, state, form)，返回命令对象 JSON 字符串
// 源码实际执行： "$loginJs\nloginAction(String(__loginAction), JSON.parse(String(__loginState)), JSON.parse(String(__loginForm)))"
function loginAction(action, state, form) {
  ...
  return JSON.stringify({ ... });
}
```

**绑定变量**（V2 环境）：

| 变量 | 内容 |
|---|---|
| `__loginState` | state JSON 字符串（首次渲染是空/`{}`） |
| `__loginAction` | 当前点击的 action 名 |
| `__loginForm` | 表单当前值 JSON |
| `book` / `chapter` | 当前书籍/章节 |
| `java` / `source` | JsExtensions / 书源 |

> 注意：**`result` 在 V2 里不存在**，别沿用 V1 的 `result['用户名']` 写法。

### 1.4 RowUi 字段全表

```kotlin
data class RowUi(
    val name: String = "",              // 显示名（text 作 hint）
    val type: String = "text",          // text/password/button/label/toggle/select
    val action: String? = null,         // 按钮点击的 action 名
    val chars: Array<String?>? = null,  // (V1 兼容字段)
    val default: String? = null,
    var viewName: String? = null,       // 覆盖显示文案
    val style: FlexChildStyle? = null,  // 布局
    val key: String? = null,            // ★表单键名（V2 新增，text/password/select/toggle 必填）
    val hint: String? = null,           // ★输入框占位提示（V2 新增）
    val value: String? = null,          // ★初始值（V2 新增）
    val options: List<String>? = null,  // ★select 选项（V2 新增）
    val countdown: Int? = null,         // ★按钮倒计时秒数（V2 新增）
)
```

### 1.5 校验规则（parseRender 不通过 → 整个面板渲染失败）

| 条件 | 要求 |
|---|---|
| `name` | 不能为空（所有类型） |
| `text` / `password` | **必须有 `key`** |
| `select` | 必须有 `key` **且** `options` 非空 |
| `toggle` | 必须有 `key`；`value` 只能是 `"true"`/`"false"`/null；`action` 若存在不能为空白 |
| `button` | **必须有 `action`** |
| `label` | 只需 `name` |
| 未知 `type` | 直接判无效 |
| 重复 | 所有 `key` 不能重复；所有 `action` 不能重复 |
| `countdown` | 不能为负 |

**实测校验表**（用纯 JS 复现源码逻辑）：

| 输入 | 结果 |
|---|---|
| 完整合法（6 行） | ✅ OK (keys=user,pass,line,remember actions=doLogin) |
| select 缺 options | ❌ `select 缺 options` |
| text 缺 key | ❌ `row[0] text 缺 key` |
| 未知 type=foo | ❌ `row[0] 未知 type=foo` |
| key 重复 | ❌ `key 重复` |

> 一旦校验失败，`parseRender` 返回 `null` → 面板显示"渲染错误"。
> **这是 V2 最容易踩的坑：少一个 key 就整页白屏。**

### 1.6 返回值协议（loginAction 的返回）

```kotlin
val knownCommands = setOf("state", "error", "login", "close")

data class ActionResult(
    val stateJson: String? = null,   // 新 state，驱动重渲染
    val error: Map<String, String>? = null,  // key→错误文案，标红对应字段
    val loginJson: String? = null,   // 登录成功时保存的登录信息
    val close: Boolean = false,      // 关闭面板
    val unknownKeys: List<String>,   // 未知命令，忽略并记日志
    val malformed: Boolean = false,  // 格式错误 → 提示"无效命令"
)
```

**命令语义**：

| 命令 | 类型 | 作用 |
|---|---|---|
| `state` | object | 更新状态并重渲染（做多步登录/验证码流程） |
| `error` | object | `{"字段key": "错误文案"}`，对应输入框标红 |
| `login` | object | 保存为登录信息（等价 V1 的 `putLoginInfo`） |
| `close` | boolean | `true` 关闭面板 |

**类型不合法直接判 malformed**：`state`/`error`/`login` 必须是 JSON **object**，`close` 必须是 **boolean**。

### 1.7 完整模板（可直接改用）

```javascript
// loginUrl
function loginUi(state) {
  var err = (state && state.err) ? state.err : '';
  return JSON.stringify({
    rows: [
      { type: 'label', name: err ? ('❌ ' + err) : '请输入账号密码' },
      { type: 'text',     name: '账号', key: 'user', hint: '手机号/用户名', value: (state && state.user) || '' },
      { type: 'password', name: '密码', key: 'pass', hint: '不少于6位' },
      { type: 'select',   name: '线路', key: 'line', options: ['电信', '联通', '移动'] },
      { type: 'toggle',   name: '记住账号', key: 'remember', value: 'true' },
      { type: 'button',   name: '登 录', action: 'doLogin' }
    ]
  });
}

function loginAction(action, state, form) {
  if (action !== 'doLogin') return JSON.stringify({ error: { user: '未知动作' } });
  var u = String(form.user || '').replace(/^\s+|\s+$/g, '');
  var p = String(form.pass || '');
  if (!u) return JSON.stringify({ error: { user: '请填写账号' } });
  if (!p) return JSON.stringify({ error: { pass: '请填写密码' } });
  try {
    var resp = java.post('https://site.com/api/login',
      'username=' + encodeURIComponent(u) + '&password=' + encodeURIComponent(p),
      { 'Content-Type': 'application/x-www-form-urlencoded' });
    var jo = JSON.parse(String(resp.body()));
    if (String(jo.code) === '0') {
      return JSON.stringify({ login: { user: u, pass: p }, close: true });
    }
    return JSON.stringify({ error: { pass: String(jo.msg || '登录失败') } });
  } catch (e) {
    return JSON.stringify({ error: { user: '网络错误:' + e } });
  }
}
```

配套：

```jsonc
"loginUi": "{\"version\":2}",
"loginUrl": "<上面两个函数>"
```

### 1.8 V1 / V2 选择建议

| 场景 | 推荐 |
|---|---|
| 固定几个输入框 + 一个登录按钮 | **V1**（更简单，loginUi 直接写数组） |
| 需要下拉选择（线路/分区） | V2（V1 没有 select） |
| 需要多步流程（先发验证码再登录） | **V2**（`state` 驱动重渲染） |
| 需要字段级错误提示 | **V2**（`error` 映射） |
| 需要按钮倒计时（防重复点/验证码冷却） | **V2**（`countdown`） |
| 需要纯文字说明行 | V2（`label`） |

---

## 二、`<useweb>`：简介里嵌入真实网页

### 2.1 是什么

`ruleBookInfo.intro` 返回值以 `<useweb>` 开头时，App 会把中间内容当 **HTML 交给一个真实 WebView 渲染**，
并注入 `java`/`source`/`cache` 三个桥对象。

### 2.2 三种前缀（BookInfo.kt:125）

```kotlin
if (introTrimS.startsWith("<usehtml>") ||
    introTrimS.startsWith("<md>") ||
    introTrimS.startsWith("<useweb>")) {
    book.intro = introTrimS        // 原样保存
} else {
    book.intro = HtmlFormatter.formatIntro(intro)   // 普通文本净化
}
```

| 前缀 | 渲染方式 | 能力 | 适用 |
|---|---|---|---|
| 无 | TextView 纯文本 | 最弱 | 普通简介 |
| `<usehtml>` | TextView + Html 解析 | 富文本、`<button @onclick>`、`<img>` | 简介排版 + 交互按钮 |
| `<md>` | **Markwon** Markdown | 标题/列表/**表格**/代码/图片 | 结构化简介 |
| `<useweb>` | **真 WebView** | 完整 HTML/CSS/JS | 复杂布局、需要执行页面 JS |

### 2.2.1 正文里的 `<usehtml>`（另一条链路）

`ruleContent.content` 里也可以嵌 `<usehtml>...</usehtml>`，由 `ContentProcessor` 单独处理：

```kotlin
val useHtmlMap = mutableMapOf<String, String>()
if (AppConfig.adaptSpecialStyle) { // ← 受此开关控制
    mContent = AppPattern.useHtmlRegex.replace(mContent) { matchResult ->
        val placeholder = "特殊格式的占位不应该被看见${useHtmlMap.size}。"
        useHtmlMap[placeholder] = "\n${matchResult.value.replace("\n","")}\n"
        placeholder
    }
}
// ...替换净化...
useHtmlMap.forEach { (placeholder, originalContent) ->
    mContent = mContent.replace(placeholder, originalContent)
}
```

关键点：

1. **`adaptSpecialStyle` 默认是 `true`**（`AppConfig.kt:71` `getPrefBoolean(PreferKey.adaptSpecialStyle, true)`）
2. 正文的 `<usehtml>` 是**成对闭合**的 `<usehtml>…</usehtml>`（与简介的"开头 + 结尾 `<`"不同！）
3. 先替换成占位符 → 跑替换净化 → 再还原，**避免净化规则破坏 HTML**
4. 用户若在 App 设置里关掉「适应特殊样式」，这些标签会被当普通文本处理

> 简介用 `<usehtml>`（无闭合），正文用 `<usehtml>…</usehtml>`（有闭合）。两处语法不同，别混。

### 2.3 `<useweb>` 的截断规则（易错）

```kotlin
val lastIndex = intro.lastIndexOf("<")
if (lastIndex < 8) { /* 当作普通文本 */ }
val html = intro.substring(8, lastIndex)     // 去掉前 8 字符 "<useweb>" 和最后 '<'
```

- 前 8 字符固定是 `<useweb>`（8 个字符）
- **末尾必须有 `<`**（`lastIndexOf("<")` 取最后一个 `<` 之前的内容）
- 所以标准写法是：`<useweb>...html...<`

```jsonc
// ruleBookInfo.intro
"<useweb><div style='padding:8px'>这里是 HTML</div><"
```

> 同理 `<usehtml>` 是 `substring(9, lastIndex)`（9 字符），`<md>` 是 `substring(4, lastIndex)`（4 字符）。
> **三者都要以 `<` 结尾。**

### 2.4 useweb 里能用的 JS（源码 WebJsExtensions）

App 注入三个**随机命名**的全局对象（防站点嗅探）：

```javascript
java     // WebJsExtensions
source   // 书源对象
cache    // CacheManager
```

> 变量名是随机的（`getRandomLetter() + uuid + uuid2`），但 App 会额外注入一段
> `getInjectionString = "try{var cache=$nameCache,source=$nameSource,java=$nameJava;}catch(e){}"`
> 把随机名**映射到固定的 `java`/`source`/`cache`**。
> 所以在 useweb 页面里**直接用 `java`/`source`/`cache` 即可**。

### 2.5 useweb 的 Promise 化 API 全表

这些是 `JS_INJECTION` 注入的，**都返回 Promise**：

| 函数 | 用途 |
|---|---|
| `run(jsCode)` | 在书源规则环境执行 JS |
| `ajaxAwait(url[, timeout])` | GET 请求 |
| `getAwait(url, headers)` | GET（带 header） |
| `headAwait(url, headers)` | HEAD |
| `postAwait(url, body, headers)` | POST |
| `connectAwait(url, method, timeout)` | 通用连接 |
| `webViewAwait(url, ...)` | 用 WebView 加载（可执行页面 JS） |
| `webViewGetSourceAwait(url, ...)` | WebView 加载并取源码 |
| `decryptStrAwait(...)` | 解密 |
| `encryptBase64Await(...)` | Base64 加密 |
| `encryptHexAwait(...)` | Hex 加密 |
| `createSignHexAwait(...)` | 生成签名 Hex |
| `downloadFileAwait(url)` | 下载文件 |
| `readTxtFileAwait(path)` | 读文本文件 |
| `importScriptAwait(url)` | 导入外部脚本 |
| `getStringAwait(...)` | 取字符串资源 |

用法示例（在 `<useweb>` 的 HTML 里）：

```html
<script>
ajaxAwait('https://site.com/api/info').then(function(txt){
  var jo = JSON.parse(txt);
  document.getElementById('vip').innerText = jo.isVip ? 'VIP会员' : '普通用户';
}).catch(function(e){
  document.getElementById('vip').innerText = '读取失败';
});
</script>
```

### 2.6 useweb 的硬约束（源码实锤）

```kotlin
val webJsExtensions = WebJsExtensions(it, null, webView)
//                                      ↑ activity = null
```

- **`activity = null`** → `java.startBrowser` / `java.openVideoPlayer` 等需要 Activity 的方法**静默失效**
- `webView.loadDataWithBaseURL(bookUrl, html, "text/html", "utf-8", bookUrl)`
  - baseUrl 取 `bookUrl.substringBefore(",")`（去 URL 选项）
  - 所以**页面里的相对路径会按书籍 URL 解析**
- WebView 来自 `WebViewPool`（池化复用，5 分钟闲置销毁）
- 简介区高度有限，`<useweb>` 内容过高会被裁切（`introCanCollapse = false`）

### 2.7 `<md>` 的渲染细节

```kotlin
Markwon.builder(context)
    .usePlugin(GlideImagesPlugin.create(...))   // 图片
    .usePlugin(HtmlPlugin.create())             // 内嵌 HTML
    .usePlugin(TablePlugin.create(context))     // ★表格
    .build()
```

**支持表格**是 `<md>` 相对 `<usehtml>` 的独特优势。

```jsonc
"intro": "@js:'<md>## 内容简介\\n\\n' + result + '\\n\\n| 项目 | 值 |\\n|---|---|\\n| 状态 | 连载 |\\n< '"
```

> 注意结尾要有 `<`。

### 2.8 三者选型决策树

```
需要执行页面 JS / 复杂 CSS 布局？
├─ 是 → <useweb>（注意 activity=null 的限制）
└─ 否
   ├─ 需要表格 / Markdown 语法？
   │  ├─ 是 → <md>
   │  └─ 否
   │     ├─ 需要按钮交互（@onclick）/ 富文本排版？
   │     │  ├─ 是 → <usehtml>
   │     │  └─ 否 → 普通文本
```

---

## 三、发现页交互控件：select / toggle / text / button / label

### 3.1 ExploreKind 字段全表

```kotlin
data class ExploreKind(
    val title: String = "",         // 显示名，同时是 infoMap 的 key
    val url: String? = null,        // 分类 URL（type=url 时）
    val type: String = "url",       // url/text/button/toggle/select
    val action: String? = null,     // 点击时执行的 JS
    val chars: Array<String?>? = null,  // select/toggle 的选项数组
    val default: String? = null,    // 默认值
    var viewName: String? = null,   // 覆盖显示文案
    val style: FlexChildStyle? = null,
)
```

### 3.2 五种 type 的行为对照

| type | 渲染 | 取值存放 | action 触发时机 |
|---|---|---|---|
| `url` | 可点击的分类项 | — | — |
| `text` | 输入框（hint=title） | `infoMap[title]` | **输入后 600ms 防抖** |
| `button` | 按钮 | — | 点击时 |
| `toggle` | 可点击文字，循环切换 chars | `infoMap[title]` | 每次切换 |
| `select` | **下拉选择框（Spinner）** | `infoMap[title]` | 选中项变化时 |

### 3.3 select 的源码细节（ExploreAdapter.kt:487）

```kotlin
Type.select -> {
    val sl = getFlexboxChildSelect(flexbox)
    flexbox.addView(sl)
    kind.style().apply { ... }                    // 布局
    // viewName 三态：null→title；'xxx'→字面量；其它→evalUiJs
    val chars = kind.chars?.filterNotNull() ?: listOf("chars","is null")
    val adapter = ArrayAdapter(context, R.layout.item_text_common, chars)
    selector.adapter = adapter
    // 初始值：infoMap[title] 优先，否则 kind.default，否则 chars[0]
    val infoV = infoMap[title]
    val char = if (infoV.isNullOrEmpty()) {
        (kind.default ?: chars[0]).also { infoMap[title] = it }   // ← 自动写入默认值
    } else infoV
    selector.setSelectionSafely(chars.indexOf(char))
    selector.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
        var isInitializing = true
        override fun onItemSelected(...) {
            if (isInitializing) { isInitializing = false; return }  // 忽略初始化
            infoMap[title] = chars[position]
            if (kind.action != null) { evalButtonClick(kind.action, ...) }
        }
    }
}
```

**关键点**：

1. `chars` 为空时显示占位 `["chars","is null"]`（**不是崩溃，是提示你没配**）
2. **初始化时会自动把 `default`（或首项）写进 `infoMap[title]`**，所以不用 action 也能拿到值
3. 首次选中被 `isInitializing` 跳过，**不会触发 action**
4. 用户切换才触发 action

### 3.4 infoMap 是什么（InfoMap.kt）

```kotlin
class InfoMap(val sourceUrl: String): MutableMap<String, String> {
    init {
        val cache = CacheManager.get("infoMap_${sourceUrl}")
        actualMap = GSON.fromJsonObject<MutableMap<String, String>>(cache).getOrNull() ?: mutableMapOf()
    }
    fun save(time: Int = 0, need: Boolean = true) { ... }
    fun saveNow() { CacheManager.put("infoMap_${sourceUrl}", json, saveTime) }
}
```

- **按书源持久化**（key = `infoMap_${bookSourceUrl}`）
- 退出发现页时 `onPause()` 批量 `saveNow()`
- 所以**用户选过的值下次进来还在**

### 3.5 怎么在规则里用 infoMap 的值

`exploreUrl` / 分类 URL 里用 `{{ }}` 模板：

```jsonc
"exploreUrl": "@js:JSON.stringify([...])"   // 或静态字符串
```

URL 里的写法（实测通过）：

| 写法 | 结果 |
|---|---|
| `{{infoMap['线路']}}` | ✅ 取值 |
| `{{infoMap.分类}}` | ✅ 取值（中文属性名可用） |
| `{{infoMap['线路'] || '默认'}}` | ✅ 支持 `||` 兜底 |
| `{{page}}` | ✅ 页码（在 `{{}}` 里可用） |

**完整示例**：

```jsonc
"exploreUrl": "[{\"title\":\"玄幻\",\"url\":\"/list?cat=xuanhuan&line={{infoMap['线路']}}\"},{\"title\":\"修真\",\"url\":\"/list?cat=xiuzhen&line={{infoMap['线路']}}\"},{\"title\":\"线路\",\"type\":\"select\",\"chars\":[\"电信\",\"联通\",\"移动\"],\"default\":\"电信\",\"style\":{\"layout_flexBasisPercent\":0.4}}]"
```

### 3.6 `exploreUrl` 支持 `@js:` / `<js>` 动态生成（重要新特性）

源码 `BookSourceExtensions.exploreKinds()`：

```kotlin
val ruleStr = when {
    exploreUrl.startsWith("@js:", true) -> { ...evalJS(exploreUrl.substring(4))... }
    exploreUrl.startsWith("<js>", true) -> { ...evalJS(exploreUrl.substring(4, lastIndexOf("<")))... }
    else -> exploreUrl
}
if (ruleStr.isJsonArray()) {
    GSON.fromJsonArray<ExploreKind>(ruleStr)          // ← JSON 数组
} else {
    ruleStr.split("(&&|\n)+").forEach { ... }          // ← 标题::url 文本
}
```

**这意味着**：

1. `exploreUrl` 可以是 JS，动态返回分类列表（可读 `infoMap`、可发请求）
2. 返回值可以是 **JSON 数组**（能用 select/toggle/style 全套）或 `标题::url&&...` 文本
3. **有缓存**：`aCache.getAsString(exploreKindsKey)`，`refreshExplore()` 会 `clearExploreKindsCache()`

```jsonc
"exploreUrl": "@js:(function(){var line=infoMap['线路']||'电信';var arr=[{title:'玄幻',url:'/list?cat=1&line='+line}];return JSON.stringify(arr);})()"
```

> **坑**：`@js:` 返回**裸 JS 代码串**（而非求值结果）会静默失败。必须返回**分类配置的 JSON 文本**。

### 3.7 分组标题行 / 布局控制

```jsonc
// 独占整行的分组标题
{"title":"分类","url":"","style":{"layout_flexBasisPercent":1,"layout_wrapBefore":true,"layout_justifySelf":"flex_start"}}
```

FlexChildStyle 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `layout_flexGrow` | Float | 放大比例（默认 0） |
| `layout_flexShrink` | Float | 收缩比例（默认 1） |
| `layout_alignSelf` | String | auto/flex_start/flex_end/center/baseline/stretch |
| `layout_flexBasisPercent` | Float | 宽度占比（-1 = 自动；1 = 整行；0.4 = 40%） |
| `layout_wrapBefore` | Boolean | 是否换行到下一行 |
| `layout_justifySelf` | String | 内部对齐：auto/flex_start/flex_end/center/right |

### 3.8 select/toggle 的 viewName 三态（与 loginUi 完全一致）

```kotlin
if (viewName == null) { 显示 title }
else if (viewName.length in 3..19 && 首尾单引号) { 显示字面量 }
else { 显示 title; 异步 evalUiJs(viewName); 空→"null"，错→"err" }
```

**同样建议留空 viewName**，避免出现 `null`/`err`。

---

## 四、UrlOption：URL 后接 JSON 控制请求

### 4.1 语法

```
URL,{"method":"POST","body":"a=1","headers":{...}}
```

分隔符是 **`,\s*(?=\{)`**（逗号 + 空白 + 紧跟 `{`）。

### 4.2 全字段表（AnalyzeUrl.kt:832~880）

| 字段 | 类型 | 说明 |
|---|---|---|
| `method` | String | **只认 POST/HEAD，其它一律 GET**（含 DELETE/PUT 会静默降级！） |
| `charset` | String | 响应编码 |
| `headers` | Object/String | 请求头 |
| `body` | String/Object/Array | 请求体；对象/数组会自动 JSON 序列化 |
| `origin` | String | 源 URL（影响相对路径解析） |
| `retry` | Int | 重试次数 |
| `type` | String | 响应类型（如 hex） |
| `webView` | Any | 是否用 WebView（`true`/`"true"` 生效） |
| `webJs` | String | **WebView 里执行的 JS** |
| `timeout` | Long | 读取超时（毫秒） |
| `followRedirects` | Any | 是否跟随重定向 |
| `dnsIp` / `resolveIp` | String | 自定义域名 IP |
| `js` | String | **解析完 URL 后执行，返回值覆盖 URL** |
| `bodyJs` | String | **拿到响应后执行，返回值替换 body** |
| `serverID` | Long | 服务器 ID |
| `webViewDelayTime` | Long | WebView 加载完成后延迟（毫秒） |

### 4.3 `js` vs `bodyJs` 的关键区别

```
请求前：URL --[js]--> 新URL --请求--> 响应 --[bodyJs]--> 新body
```

| 字段 | 时机 | 返回什么 | 典型用途 |
|---|---|---|---|
| `js` | URL 解析后、发请求前 | **新 URL 字符串** | 动态拼接签名参数 |
| `bodyJs` | 收到响应后 | **新 body 字符串** | 二次请求、解密、格式转换 |

**`bodyJs` 环境变量**：`result`（响应体字符串）、`key`、`page`、`java`、`baseUrl`

> 重要：`bodyJs` 里**不能调用 jsLib 函数**（SharedJsScope 闭包拿不到本次 `result`），必须内联。

### 4.4 `js` 返回 JSON 会被当 URL（血泪坑）

```jsonc
// ❌ 错误：@js 返回 JSON 字符串
"searchUrl": "@js:(function(){...return jsonText;})()"
// → GET https://site.com/{"code":0,...}  → 404

// ✅ 正确：真实 URL + bodyJs
"searchUrl": "https://site.com/search?q={{key}},{\"bodyJs\":\"<内联脚本>\"}"
```

---

## 五、`webView` 请求通道：让 App 帮你跑页面 JS

### 5.1 用法

```jsonc
"url": "https://site.com/page,{\"webView\":true,\"webJs\":\"document.querySelector('.x').innerText\"}"
```

### 5.2 机制

1. 先正常请求 URL
2. 把响应 HTML 交给 `BackstageWebView` 加载
3. 执行 `webJs`，返回值作为 body

### 5.3 适用场景

- 页面内容由 JS 渲染（SPA）
- 需要过 JS 挑战（非 CF 验证码类）
- 需要执行页面里的加密函数

### 5.4 限制

- 需要后台 WebView，**较慢**（`webViewDelayTime` 可加延迟）
- 部分环境（无 WebView 可用）会失败
- 不能替代真正的登录态（除非 cookie 已同步）

---

## 六、速查：本次新增特性清单

| 特性 | 位置 | 关键点 |
|---|---|---|
| **登录UI V2** | `loginUi: {"version":2}` + `loginUrl` 里 `loginUi()`/`loginAction()` | rows 动态返回；key/options/action 校验严格；支持 state/error/login/close |
| **RowUi 新字段** | V2 rows | `key`/`hint`/`value`/`options`/`countdown` |
| **`<md>` 简介** | `ruleBookInfo.intro` | Markwon 渲染，**支持表格**；结尾要 `<` |
| **`<useweb>` 简介** | 同上 | 真 WebView；注入 java/source/cache；**activity=null** |
| **`<usehtml>` 简介** | 同上 | TextView 富文本 + `<button @onclick>` |
| **正文 `<usehtml>`** | `ruleContent.content` | 受「适应特殊样式」控制，**默认开启** |
| **发现页 select** | `exploreUrl` JSON 数组 | `chars` 选项、`default` 初值、自动写 `infoMap` |
| **发现页 toggle** | 同上 | 循环切换 `chars`，写 `infoMap` |
| **发现页 text** | 同上 | 600ms 防抖 action |
| **`exploreUrl` 动态** | `@js:` / `<js>` | 返回 JSON 数组或 `标题::url` 文本 |
| **infoMap 持久化** | 自动 | 按书源存 `infoMap_${sourceUrl}` |
| **`{{infoMap.xxx}}`** | 任何 URL 模板 | 支持 `||` 兜底 |
| **UrlOption 全字段** | URL 后 `,{...}` | `js`/`bodyJs`/`webView`/`webJs`/`dnsIp`/`serverID` 等 15 个 |
| **`webView`+`webJs`** | URL 选项 | 后台 WebView 执行 JS 取内容 |

---

## 七、排查清单

| 现象 | 首查 |
|---|---|
| V2 面板白屏/渲染错误 | `parseRender` 校验：每个 text/select/toggle 有 `key`？select 有 `options`？key/action 不重复？ |
| V2 点按钮没反应 | `action` 名与 `loginAction` 里判断的一致？返回的是 JSON 字符串？ |
| V2 字段标红但不显示文案 | `error` 的 key 与 row 的 `key` 一致？ |
| `<useweb>` 显示成一行文字 | 结尾缺 `<`；或 `lastIndex < 8` |
| `<useweb>` 里 `java.startBrowser` 无效 | `activity = null`，这个通道不支持 |
| `<md>` 表格没渲染 | 结尾缺 `<`；或语法不标准（Markwon 用 GFM 表格） |
| 正文 `<usehtml>` 被净化掉 | 用户关掉了 App 设置 →「适应特殊样式」（**默认开启**） |
| select 显示 `chars` / `is null` | `chars` 没配或全是 null |
| select 选了不生效 | URL 里没写 `{{infoMap['标题']}}`，或 key 名不匹配 |
| `exploreUrl` 的 `@js:` 无效果 | 返回了裸 JS 代码串而非求值后的分类 JSON |
| UrlOption 的 DELETE 无效 | 只支持 POST/HEAD，其它静默降级 GET |
