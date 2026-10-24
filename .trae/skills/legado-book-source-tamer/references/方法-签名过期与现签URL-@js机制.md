# 方法：签名过期型 API 的「现签 URL」机制 —— `@js:` 动态签名、URL 稳定性与去重陷阱

> 2026-10-24 实战沉淀（蓝本：哔咔漫画自包含书源 v76 → v83）
> 关联：[[方法-图片CDN间歇阻断与Legado重试语义]]、[[方法-URL模板与DNS选线]]、[[方法-LAN-Web服务保存书源与全端点手册]]、[[方法-书源交付质量闭环]]

---

## 0. 一句话结论

对于「**每次请求都需要新签名**」的 API（如 HMAC + time + nonce），把签名**写进 URL** 会必然过期，而把签名**写进 header** 又拿不到请求上下文。
本轮实锤的可行解是：**用 `@js:` 让 URL 在【每次请求时】重新求值并现签**，但必须同时解决三个坑：

| 坑 | 现象 | 解法 |
|---|---|---|
| 坑1 | 规则文本里出现字面 `@js:` → 被 `splitSourceRule` 误判为 JS 规则段**立即求值** | 用 `String.fromCharCode(64,106,115,58)` 运行时拼接 |
| 坑2 | 签名 IIFE 写成**立即执行** → 在目录规则阶段就跑了一次（result 是别的响应体） | 必须是**字符串字面量**，只由 `@js:` 触发 |
| 坑3 | URL 每次都不同 → App 的 `nextUrlList.contains()` 去重失效 → 同页请求两次 → 第二次签名已消费 → 400 | 终止值用 `"javascript:void(0)"`（`getAbsoluteURL` 对 `javascript` 前缀返回空串） |

---

## 1. 【根因】签名会过期（实测判据）

哔咔服务端行为（2026-10-24 实测）：

| 请求形态 | 服务端响应 |
|---|---|
| 缺 time/nonce/signature | `400 error "必須更新！" message "--"` |
| time 过期（老 3600s） | `400 error 1029 "time is not synchronize"` |
| 签名正确但 path 不匹配 | `200 "success"` 但 **data 为空**（伪装形态！） |
| 全部正确 | `200 success` + 完整 data |

**判据速查**：
- `400 必須更新` → 缺签名头
- `400 1029 time is not synchronize` → 签名过期
- `200` 但无 data → **path 算错**（最容易误判成"接口没数据"）

> ★ 签名放在 URL 的 query 里**无效**（实测仍返回 400 必須更新）——服务端只认 header。

---

## 2. 【核心机制】`@js:` 的 `result` 绑定 = URL 前缀

`AnalyzeUrl.analyzeJs()`（源码 `AnalyzeUrl.kt:188`）：

```kotlin
private fun analyzeJs() {
    var start = 0
    var result = ruleUrl                       // 初始 = 整条 URL
    val jsMatcher = AppPattern.JS_PATTERN.matcher(ruleUrl)
    while (jsMatcher.find()) {
        if (jsMatcher.start() > start) {
            ruleUrl.substring(start, jsMatcher.start()).trim().let {
                if (it.isNotEmpty()) { result = it.replace("@result", result) }
            }
        }
        result = evalJS(jsMatcher.group(2) ?: jsMatcher.group(1), result).toString()
        start = jsMatcher.end()
    }
    ...
    ruleUrl = result
}
```

`AnalyzeUrl.evalJS` 的绑定里 `result` = 传入的累积结果。

**实测结论**：

| URL 形态 | `@js:` 里 `result` 的值 |
|---|---|
| `"@js:EXPR"`（整条只有 @js 段） | `"@js:EXPR"` 自身（**拿不到 path**） |
| `"https://host/path?page=1@js:EXPR"` | `"https://host/path?page=1"` ✅ **含 path** |

⇒ **正确用法**：URL 写成 `"https://host/<path>@js:EXPR"`，EXPR 里用 `String(result)` 取 path。

`analyzeJs()` 在 `initUrl()` 里执行，而 `initUrl()` **每次请求都会跑** ⇒ `@js:` 表达式**每次请求都重新求值** ⇒ 签名天然新鲜。

---

## 3. 【坑1】规则文本里的字面 `@js:` 会被立即求值

`AnalyzeRule.splitSourceRule()`（`AnalyzeRule.kt:593`）用 `JS_PATTERN` 扫描**整条规则串**：

```kotlin
val jsMatcher = JS_PATTERN.matcher(ruleStr)
while (jsMatcher.find()) {
    ...
    ruleList.add(SourceRule(jsMatcher.group(2) ?: jsMatcher.group(1), Mode.Js))
}
```

`JS_PATTERN = <js>([\w\W]*?)</js>|@js:([\w\W]*)`（`AppPattern.kt:7`）

⇒ **规则文本里只要出现字面 `@js:`，该段就被当成 JS 规则并立即求值**。
本轮 v77 失败现象：目录规则里的章节 URL 变成
`.../pages?page=1@js:https://picaapi.picacomic.com/  "code": 200, "message": "success", ...`
（`@js:` 后面被替换成了**目录页的响应体**）。

**解法**：用 `String.fromCharCode(64,106,115,58)` 在运行时拼接 `@js:`，彻底规避文本扫描。

```js
var _at = String.fromCharCode(64,106,115,58);   // "@js:"
url: "https://host/comics/x/order/1/pages?page=1" + _at + _sg
```

验证：`"@js:" 的码点 = 64,106,115,58` ✅

---

## 4. 【坑2】签名 IIFE 必须是字符串字面量

```js
// ✘ 错：立即执行 —— 目录规则求值时就跑了一次，那次 result 是【目录页响应体】
var _sg = (function(){ ... 用 result 算签名 ... })();

// ✔ 对：字符串字面量 —— 只在被 @js: 触发（即真正发请求）时才执行
var _sg = '(function(){ ... 用 result 算签名 ... })()';
```

v78 失败现象：章节 URL 后面直接拼上了整段 JSON 响应体。
v79 修正后：章节 URL 正确保留 `@js:` 表达式原文 → 请求时才求值 → `code=200` + 40 张图 ✅

**同时注意**：`@js:` 表达式**不能引用外部变量**（它在 `AnalyzeUrl` 作用域执行，外部作用域不可见）⇒ 密钥/apiKey/池等必须**全部内联**。

---

## 5. 【坑3】URL 每次不同会破坏 App 的翻页去重

`BookContent.analyzeContent`（`BookContent.kt:63`）：

```kotlin
val nextUrlList = arrayListOf(redirectUrl)
...
if (contentData.second.size == 1) {
    var nextUrl = contentData.second[0]        // ← nextContentUrl 规则的输出
    while (nextUrl.isNotEmpty() && !nextUrlList.contains(nextUrl)) {
        if (!mNextChapterUrl.isNullOrEmpty() && ... == ...) break
        nextUrlList.add(nextUrl)               // ← 存的是【规则输出】
        val analyzeUrl = AnalyzeUrl(mUrl = nextUrl, ...)   // ← 这里才求值 @js:
        ...
    }
}
```

**去重比较的是 `nextContentUrl` 规则的输出**。若该规则输出的是**已求值的 URL**（含随机 nonce），每次都不同 ⇒ `contains()` 永远 false ⇒ 同一页被反复请求 ⇒ 第二次签名已消费 ⇒ `400` ⇒ 末尾报"正文获取失败"。

**另一处陷阱**：`AnalyzeRule.getStringList(isUrl=true)` → `NetworkUtils.getAbsoluteURL(redirectUrl, str)`：

```kotlin
if (relativePathTrim.isAbsUrl()) return relativePathTrim
if (relativePathTrim.isDataUrl()) return relativePathTrim
if (relativePathTrim.startsWith("javascript")) return ""     // ★ javascript 前缀 → 空串
...
val parseUrl = URL(baseURL, relativePath)                      // ★ 空串 → 返回 baseURL 本身！
```

⇒ **`nextContentUrl` 返回空串是错的**：空串会被解析成"当前页 URL"，App 认为还有下一页 ⇒ 重复请求。
⇒ **必须返回 `"javascript:void(0)"`**：`getAbsoluteURL` 明确返回空串 ⇒ 循环正常终止。

本轮 v81 实测：6 页正文一次跑完（40+40+40+40+40+32 = 232 张），`◇本章总页数:6`，无重复请求、无异常。

---

## 6. 【@js: 环境的三个限制】（踩坑清单）

| 限制 | 现象 | 替代 |
|---|---|---|
| `java` = **AnalyzeUrl**（不是 BookSource） | `java.getLoginHeader` → "找不到函数" | 用 `source.get("picab_token")`（登录时写入） |
| 外部变量不可见 | `API_KEY is not defined` | 全部内联进 `@js:` 表达式 |
| `Packages.javax.crypto.*` 可用 | — | `Mac`/`SecretKeySpec` 正常（Rhino 里 `java.*` 才不行） |

**多层转义陷阱**：密钥里的 `\` 在「Python 字符串 → JSON → 书源 → `@js:` → JS 字符串」多层传递中会丢。
**必须用 `String.fromCharCode(92)` 拼反斜杠**（本轮实测：同一 raw 用 `\\RK` 与 `\RK` 算出**不同签名**，服务端 200 但无 data）。

---

## 7. 【发现页专用坑】kind.url 的 `@js:` 不能调用 jsLib

`ExploreKind.url` 支持 `@js:` 形式（`AnalyzeUrl.analyzeJs` 求值）。
**但该求值发生在 `AnalyzeUrl` 环境** ⇒ `java` 是 AnalyzeUrl ⇒ jsLib 里 `picab_opt()` 内部调 `JV.ajax()` **不存在** ⇒ 抛错 ⇒ 请求发出的是**无签名裸 URL** ⇒ `400 必須更新` ⇒ 发现页解析失败。

**症状链（实测）**：
```
kind.url = "@js:picab_opt('comics?page=1&c=大家都在看&s=dd', ...)"
  → @js 求值时 picab_opt 调 java.ajax 失败
  → 实际请求 comics?page=1&c=...（裸 URL，无签名）
  → 400「必須更新」→ 发现页 bookList 抛 "发现页失败: --"
  → 校验器回退 baseUrl → 详情规则拿到 baseUrl = 分类列表 URL
  → 详情规则取不到 id → "invalid baseUrl: .../comics?page=1&c=大家都在看&s=dd"
  → check_source 失败
```

**解法**：`kind.url` 用**完全内联**的 `@js:` 表达式（自算签名，不依赖 jsLib 的任何函数）。

```js
function _mk(path) {
  return "https://picaapi.picacomic.com/" + path + _at + _sg;   // _at/_sg 均内联
}
```

---

## 8. 【URL 取 id 的健壮性】不要用贪婪正则

旧实现：

```js
s = s.replace(/.*comics\//, "");     // 贪婪
s = s.replace(/[/?#].*$/, "");
```

对 `https://host/comics?page=1&ca=abc`（**不含 `comics/`**，如发现页骑士榜条目）→ 第一条不匹配 → 第二条把域名截成 **`https:`** → 详情请求 `comics/https:` → `400 error 1022 invalid id`。

**正解**：

```js
var m = s.match(new RegExp("comics/([0-9a-fA-F]{24})"));
if (m) { return m[1]; }
m = s.match(new RegExp("^([0-9a-fA-F]{24})$"));
return m ? m[1] : "";
```

**通用教训**：从 URL 取标识符时**用精确正则 + 格式校验**，不要用"删前缀 + 删后缀"。

---

## 9. 【check_source 失败的分层定位法】

`CheckSourceService` 的校验顺序（源码）：

1. `checkSearch`：`source.getCheckKeyword(CheckSource.keyword)` → 搜索 → `searchBooks.first().toBook()` → `checkBook`
2. `checkDiscovery`：`source.exploreKinds().first { !it.url.isNullOrBlank() }?.url` → `exploreBookAwait` → `exploreBooks.first().toBook()` → `checkBook`
3. `checkBook`：`getBookInfoAwait`（详情）→ `getChapterListAwait`（目录）→ `getContentAwait`（正文）

**定位技巧**：
- 打开 HTTP 日志（`set_http_log_recording`），跑一次 `check_source`，看**最后一条失败请求的 URL** —— 直接暴露是哪个环节、哪个 URL 错了。
- 本轮就是靠日志 `GET https://picaapi.picacomic.com/comics/https: -> 400` 一眼定位到 `picab_bookid` 返回了 `https:`。
- 错误文案来自**服务端 message**（如 `invalid id` / `time is not synchronize`）还是**书源自己 throw**，要分清：
  - 服务端 message → 说明请求发出了但参数/签名错 → 看日志的 URL 与请求头；
  - 书源 throw（如 `invalid baseUrl`）→ 说明书源规则拿到的输入本身就错 → 看 baseUrl 的来源。

---

## 10. 本轮完整修复链（v76 → v83）

| 版本 | 修复 | 实测 |
|---|---|---|
| v76 | 正文图片 dnsIp 10 节点 + **按图轮换首选顺序** + 移除对 IOException 无效的 retry | 40/40 图，1.8s/张 |
| v76 | `nextContentUrl` 取 `baseUrl` 的 order（原来取 `book.tocUrl` 永不匹配） | 6 页翻完 |
| v81 | `nextContentUrl` 终止值改 `"javascript:void(0)"` | 无重复请求 |
| v82 | `picab_bookid` 改 24 位 hex 精确匹配 | 消除 `comics/https:` |
| v83 | 发现页 `kind.url` 改为完全内联现签 | **check_source 通过 1/1** |

**最终实测**：
- 搜索 20 条 → 详情 → 目录 12 章 → 正文 6 页 **232 张图**（40×5 + 32）
- 异常计数 **0**（无"正文获取失败"、无 ScriptException）
- `check_source` **通过 1/1**
- LAN 落库回读 11 个关键字段 md5 全一致
- HTTP 日志：搜索/详情/目录/正文 6 页/发现页 **全部 200**

---

## 11. 可复用结论清单

| 编号 | 结论 |
|---|---|
| S1 | `@js:` 表达式里 `result` = URL **前缀**（含 path），但整条只有 `@js:` 段时 result = 该段自身 |
| S2 | `@js:` 每次请求都重新求值 ⇒ 天然解决"签名过期" |
| S3 | 规则文本里禁止出现字面 `@js:` → 用 `String.fromCharCode(64,106,115,58)` |
| S4 | 签名 IIFE 必须是**字符串字面量**，不能立即执行 |
| S5 | `@js:` 表达式内不能引用外部变量 ⇒ 全部内联 |
| S6 | `@js:` 环境 `java` = AnalyzeUrl（无 `getLoginHeader`/`ajax`）⇒ token 用 `source.get(...)` |
| S7 | 多层转义会丢反斜杠 ⇒ 用 `String.fromCharCode(92)` |
| S8 | `nextContentUrl` 终止值必须是 `"javascript:void(0)"`，**不能是空串**（空串 = 当前页 URL） |
| S9 | URL 每次不同会破坏 `nextUrlList.contains()` 去重 ⇒ 同页重复请求 ⇒ 签名二次消费 ⇒ 400 |
| S10 | 从 URL 取 id 用**精确正则 + 格式校验**，禁用"删前缀+删后缀" |
| S11 | `kind.url` 的 `@js:` 不能调用 jsLib（`java.ajax` 不存在）⇒ 必须完全内联 |
| S12 | 签名放 query 无效（服务端只认 header） |
| S13 | 服务端"200 但 data 为空" = **path 算错**的伪装形态，别误判成"接口没数据" |
| S14 | 排障先看 HTTP 日志最后一条失败请求的 URL，可直接定位环节与错值 |

---

*本文源码引用均来自 LegadoTeam 官方源码（AnalyzeUrl.kt、AnalyzeRule.kt、BookContent.kt、BookList.kt、BookChapterList.kt、NetworkUtils.kt、CheckSourceService.kt、AppPattern.kt、BaseSource.kt），实验数据来自 2026-10-24 App 内 MCP + LAN Web 服务实测。*
