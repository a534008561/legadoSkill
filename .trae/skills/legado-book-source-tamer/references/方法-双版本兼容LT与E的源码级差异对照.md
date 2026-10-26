# 方法：LT 版与 E 版（legado-E）源码级差异对照与双版本兼容改造

> 沉淀日期：2026-10-27　｜　来源：黄果短剧书源「E 版目录加载失败」报障
> 对照源码：`gedoor/legado`（下文称 LT）vs `Luoyacheng/legado-E`（下文称 E）
> **E 版源码可用 GitHub API 下载**（`api.github.com` 可达，`github.com` 443 被墙）：
> `GET /repos/Luoyacheng/legado-E/contents/<path>?ref=main` → base64 解码

---

## 0 一句话

**E 版不是「功能少一点的 LT」，而是在 Rhino 包装层做了不同取舍的分支实现。**
最致命的一处：**E 版 `AnalyzeRule.getElements` 末尾是 `it as List<Any>` 强转，没有 LT 版的 `is NativeArray ->` 显式分支**
⇒ 任何 `@js:` 返回 JS 数组的 `chapterList` / `bookList` 在 E 版 **ClassCastException**。

---

## 1 ★★ 头号杀手：`getElements` 的 NativeArray 处理

### LT 版（`AnalyzeRule.kt:483-501`）

```kotlin
when (val value = result) {
    is List<*> -> { ... return value as List<Any> }
    is Array<*> -> { ... }
    is NativeArray -> {                       // ★★ 显式分支
        val values = ArrayList<Any>(value.length.toInt())
        for (index in 0 until value.length.toInt()) {
            val item = value.get(index, value)
            if (item != null && item !== Scriptable.NOT_FOUND) values.add(item)
        }
        return values
    }
}
return ArrayList()
```

### E 版（`AnalyzeRule.kt:436-439`）

```kotlin
result?.let {
    return it as List<Any>      // ★★ 直接强转，NativeArray 不是 java.util.List ⇒ CCE
}
return ArrayList()
```

### 后果与症状

| 书源写法 | LT 版 | E 版 |
| --- | --- | --- |
| `chapterList = @js:... return list;`（JS 数组） | ✅ | ❌ **ClassCastException → 「目录加载失败」** |
| `chapterList = @js:... return new Packages.java.util.ArrayList();` | ✅ | ✅ |
| `bookList` = CSS 选择器 | ✅ `getAnalyzeByJSoup().getElements()` → `List<Any>` | ✅ 同 |

**实测症状指纹**：搜索/详情/发现全正常，**唯独目录加载失败** —— 因为只有目录走 `getElements`。

### ✅ 修法（两版通用，零副作用）

```js
// ❌ JS 数组
var list=[];
list.push(a); list.push(b);
return list;

// ✅ Java List
var list=new Packages.java.util.ArrayList();
list.add(a); list.add(b);
return list;
```

**注意 Java List 的方法名是 `add` 不是 `push`** —— 改完实测报错「找不到函数 push」，属正常演进。

**为什么 Java List 两版都通**：

- Rhino 把 Java 对象包成 `NativeJavaObject`（**是 `Wrapper`**）
- `RhinoCompiledScript.eval` → `engine.unwrapReturnValue(ret)` → `Wrapper.unwrap()` → 还原成 `java.util.ArrayList`
- 两版 `getElements` 的 `it as List<Any>` / `is List<*>` 都能过

**⚠️ `Packages` 在 `eval_js` MCP 工具环境不可用**（报「无法调用 null 的方法 getName」），**但规则 JS 环境可用** —— 别在沙盒里下结论，要用 `debug_source` 实测。

---

## 2 ★★ 次号杀手：`getString` 对 JS 对象的处理

### LT 版（`AnalyzeRule.kt:325`）

```kotlin
if (result is NativeObject) {
    result = when {
        sourceRule.mode == Mode.Js   -> evalJS(sourceRule.rule, result)     // ★
        sourceRule.mode == Mode.Json -> getAnalyzeByJSonPath(result).getString(sourceRule.rule)  // ★
        sourceRule.getParamSize() > 1 -> sourceRule.rule
        else -> result[sourceRule.rule]
    }
}
```

### E 版（`AnalyzeRule.kt:311`）

```kotlin
if (result is NativeObject) {
    result = if (sourceRule.getParamSize() > 1) {
        sourceRule.rule
    } else {
        result[sourceRule.rule]?.toString()   // ★ 只有键值直取
    }
}
```

⇒ **E 版对 JS 对象（NativeObject）只能按键名直取**，`@js:` 与 `$.x` 都取不到。

### 双版本通吃的写法

| 列表条目类型 | 字段规则 | LT | E |
| --- | --- | --- | --- |
| CSS 选出的 **Element** | `@js:...` | ✅ `else` 分支 → `Mode.Js` | ✅ `else` 分支 → `Mode.Js` |
| CSS 选出的 Element | `$.x` | ✅ | ✅ |
| **JS 对象**（`@js:` 返回） | `@js:...` | ✅ | ❌ |
| JS 对象 | `$.x` | ✅ | ❌ |
| JS 对象 | 纯键名 `name` | ❌ | ✅ |

⇒ **首选「CSS 选择器 + `@js:` 字段」组合**，两版都走 `else` 分支 → `Mode.Js`。
（`else` 分支的进入条件：result 不是 `NativeObject`、不是 `LinkedTreeMap` ⇒ Element / String / List 都进。）

⚠️ E 版 `else` 分支有条件：`if (rule.isNotBlank() || sourceRule.replaceRegex.isEmpty())`。

---

## 3 E 版 API 存在性清单（逐个源码核对）

### ✅ E 版**有**（可直接用）

| API | 位置 | 备注 |
| --- | --- | --- |
| `coverDecodeJs` | `BookSource.kt:70` | **在 BookSource 里，不在 BaseSource**（在 BaseSource 里搜会误判为缺失） |
| `java.ajaxAll(urls)` | `JsExtensions.kt:124` | 并发测速可用 |
| `java.ajaxTestAll(urls, timeout)` | `JsExtensions.kt:143` | `isTest=true` 不真正发请求，**不可用于测速** |
| `StrResponse.code()/callTime()/body()` | `StrResponse.kt:67/54/65` | ✅ E 版直接是方法 |
| `SourceLoginJsExtensions.reLoginView()` | `SourceLoginJsExtensions.kt:40` | ✅ E 版有 |
| `SourceLoginJsExtensions.upLoginData()` | `:35` | ✅ |
| `{{}}` 模板求值 | `AnalyzeRule.kt:714 makeUpRule` | 走 `evalJS` → 绑定含 `source` ✅ |
| `source.get(key)` / `source.put(k,v)` | `BaseSource.kt:284/275` | ✅ |
| `source.getBookSourceUrl()` | `BookSource.kt:35 var bookSourceUrl` | Kotlin `var` 生成 `getBookSourceUrl()` ✅ |
| `book.setType(4)` | `Book.kt:74 var type: Int` | Kotlin `var` 生成 `setType(int)` ✅ |
| 视频播放 | `ui/video/VideoPlayerActivity.kt` 等 | ✅ `BookType.video = 0b100 = 4` |
| `bookSourceType=4` | `BookSource.kt:42` | ✅ |

### ❌ E 版**没有**（LT 版有）

| API | 影响 | 规避 |
| --- | --- | --- |
| `AnalyzeRule.getElements` 的 `is NativeArray ->` 分支 | `@js:` 返回 JS 数组 → CCE | 返回 `Packages.java.util.ArrayList` |
| `getString` 的 NativeObject 分支里的 `Mode.Js`/`Mode.Json` | JS 对象的 `@js:`/`$.x` 取不到 | 列表用 CSS 选择器 + 字段用 `@js:` |
| `BaseSource.getLoginUiJs()` / `isLoginUiV2()` / `evalLoginUiV2` / `evalLoginActionV2` | V2 登录面板不可用 | 用 **V1 静态 JSON 数组** |
| `RowUi.key` / `.hint` / `.value` / `.options` 字段 | Gson 静默忽略 | 输入框一律用 **`name`** 作存取键 |
| `JsSourceEngine.normalizeJsResult` | `evalUiJs` 直接 `.toString()` | JS 返回值必须是 String |

### ⚠️ E 版 `RowUi` 与 LT 版字段差异

```kotlin
// E 版
data class RowUi(
    val name: String = "", val type: String = "text", val action: String? = null,
    val chars: Array<String?>? = null, val default: String? = null,
    var viewName: String? = null, val style: FlexChildStyle? = null
)
// ↑ 无 key / hint / value / options
```

`getLoginData` 两版都用 `loginData[rowUi.name] = ...` ⇒ **用 `name` 当键天然双版本兼容**。

---

## 4 登录面板双版本配方（V1 静态数组 + viewName 动态文本）

E 版 `SourceLoginDialog` 与 LT 版**同样支持** `viewName` 三分支：

```kotlin
if (viewName == null) { hint = name }
else if (viewName.length in 3..19 && viewName.first()=='\'' && viewName.last()=='\'') { hint = viewName.substring(1, len-1) }
else { hint = name; execute { evalUiJs(viewName) }.onSuccess { hint = it } }   // ★ JS 表达式
```

E 版 `evalUiJs`：`source.evalJS("$loginJS\n$jsStr")` ⇒ **loginUrl 的函数在 loginUi 环境可用** ✅
E 版 `handleButtonClick`：`source.evalJS("$loginJS\n$buttonFunctionJS"){ put("java", sourceLoginJsExtensions); … }`
⇒ **`source` 仍绑定、`java` 被覆盖成 SourceLoginJsExtensions**（两版一致）。

**⇒ 配方：静态 JSON 数组 + 12 个固定线路位 `viewName:"FQ_siteName(i)"`**
（`FQ_siteName` 读 `source.get('hg_sites')` 第 i 项显示 host+延迟）⇒ E 版动态面板可用。

---

## 5 排查流程（E 版报障专用）

```
1. 先分清「哪一步失败」：
   搜索/发现失败 → bookList 或字段规则问题
   目录失败     → chapterList 返回类型问题（头号杀手）
   正文失败     → content 规则 / 解密
2. 拿 E 版源码对照（GitHub API 下载，不用 clone）：
   GET /repos/Luoyacheng/legado-E/contents/<path>?ref=main
3. diff 关键函数：AnalyzeRule.getElements / getString / getStringList
   + webBook/BookList.kt + webBook/BookChapterList.kt + webBook/BookContent.kt
   + data/entities/BaseSource.kt + data/entities/BookSource.kt
4. 逐个 API 存在性核对（★ 字段可能在子类 BookSource 里，别只看 BaseSource）
5. 静态审查表：列全部规则 → 判每条走 E 版的哪个分支
6. LT 版 debug_source 回归（改 E 版兼容不能坏 LT 版）
```

---

## 6 ★ 通用铁律

1. **`@js:` 返回值类型决定两版生死**：
   - 列表/目录元素 → 返回 **String**（最安全，两版都走 `else` 分支）
   - `chapterList` 整体 → 返回 **`java.util.List`**（不是 JS 数组）
   - 列表字段取值对象 → **别用 JS 对象**（E 版键值直取会失败）
2. **`Packages.java.util.*` 在规则 JS 可用**，在 `eval_js` MCP 工具不可用 —— 用 `debug_source` 实测。
3. **Java List 的方法是 `add` 不是 `push`**。
4. **E 版源码从 GitHub API 下载**（`github.com` 被墙时唯一出路）。
5. **Kotlin `var` 会生成 `getXxx()`/`setXxx()`** ⇒ LT 版的 `source.getBookSourceUrl()` / `book.setType(4)` 在 E 版照样能用（别误判缺失）。
6. **字段可能在子类**：`coverDecodeJs` 在 `BookSource` 而非 `BaseSource`。
