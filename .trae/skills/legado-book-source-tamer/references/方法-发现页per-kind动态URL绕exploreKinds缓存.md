---
title: 方法-发现页per-kind动态URL绕exploreKinds缓存
date: 2026-11-28
source: 黄果短剧🔞 v12（域名轮换站发现页跟随当前线路）
tags: [exploreUrl, per-kind @js, exploreKinds缓存, {{page}}, 动态发现页]
---

# 发现页「每个入口独立 @js」= 动态 URL 且绕开缓存的正解

## 1. 问题现场

域名轮换站（黄果短剧）的发现页有 8 个入口，站点根域大约每 5~7 天迁移一代（`arj2ftl0.cc → jxqgmx5ga.cc → xxbgwypx.cc → qxeylvrkf.cc`）。
书源登录面板可以测速切换到任意存活子域（`thu.`/`pku.`/… 19 个大学前缀 × N 个根域），**但发现页的 URL 是静态字段 `exploreUrl`，切了线路它不跟着变**。

三个可选写法，实测只有第三种成立：

| 写法 | 结果 |
|---|---|
| `exploreUrl` 写静态 `title::https://thu.xxx.cc/ai-duanju/{{page}}/&&…` | 切线路后不跟随；根域一死发现页全灭 |
| `exploreUrl` 整串 `@js:` 返回 `JSON.stringify(rows)` | **被 exploreKinds 缓存住**，切线路后仍用首次解析的那条（实测：把 `hg_line` 从 thu 改成 pku 后，check_source 的发现页请求仍打 thu） |
| **静态 `title::url` 字符串，但每个 url 写 `@js:表达式`** | ✅ 每次打开发现页实时求值，跟随 `source.get('hg_line')`，且 `{{page}}` 照常替换 |

## 2. 源码依据

### 2.1 kind.url 一定支持 @js

`AnalyzeUrl.initUrl()`（LT/E 一致）：

```kotlin
fun initUrl() {
    ruleUrl = mUrl
    analyzeJs()        // 执行 @js / <js></js>
    replaceKeyPageJs() // 替换 key / page / 内嵌 {{js}}
    analyzeUrl()
}
```

`analyzeJs()` 用 `AppPattern.JS_PATTERN` 扫描整串，命中 `@js:` 则把**其后全部文本**交给 JS 引擎求值，结果替换回 `ruleUrl`。
所以 `ExploreKind.url` 里写 `@js:...` 是完全合法的，每次 explore 都会重新执行。

### 2.2 `{{page}}` 与 @js 的顺序

`analyzeJs()` 先跑，`replaceKeyPageJs()` 后跑 ⇒ **@js 里返回的字符串中带 `{{page}}`，会被后续替换成页码**。
`replaceKeyPageJs()` 里的 page 替换是 `<1,2,3>` 那一套（E 版），而 `{{...}}` 走的是 `evalJS("page")`（`AnalyzeUrl.evalJS` 的 bindings 里有 `page`）。

### 2.3 为什么整串 @js 会被缓存

`BookSourceExtensions.exploreKinds()`（E 版源码，LT 同构）：

```kotlin
val exploreKindsKey = MD5Utils.md5Encode(bookSourceUrl + exploreUrl)
exploreKindsMap[exploreKindsKey]?.let { return it }   // 内存缓存
...
val ruleStr = when {
    exploreUrl.startsWith("@js:", true) -> {
        aCache.getAsString(exploreKindsKey)?.takeIf { it.isNotBlank() } ?: run {
            ... evalJS(exploreUrl.substring(4)) ...
        }.also { aCache.put(exploreKindsKey, it) }     // 磁盘缓存
    }
    ...
}
```

缓存 key = `MD5(bookSourceUrl + exploreUrl)`。只要 `exploreUrl` 字段本身不变，缓存恒命中 ⇒ 整串 @js 只在**首次**生效。
这也解释了历史现象：「发现页 URL 明明在 @js 里读了 hg_line，切线路后却还打旧域名」。

`clearExploreKindsCache()` 只在 `setExploreUrl` 时触发，规则 JS 里拿不到，登录面板的按钮无法清它。

而 per-kind @js 时，缓存的只是 `ExploreKind.url` 这个**含 @js 的字符串**，求值发生在之后的 `AnalyzeUrl.initUrl()`，与缓存无关。

## 3. 可用配方（黄果短剧 v12 实装）

```python
FIX = "(function(){var DEF='https://thu.qxeylvrkf.cc';var DEAD=['xxbgwypx'];var cur=DEF;try{var t=String(source.get('hg_line')||'');if(t.indexOf('http')===0)cur=t}catch(e){}cur=cur.replace(/\\/+$/,'');for(var i=0;i<DEAD.length;i++){if(cur.indexOf(DEAD[i])>=0)cur=DEF}return cur})()"

exploreUrl = "&&".join([
    t + "::@js:" + FIX + ' + "' + p + '"'
    for t, p in [
        ("AI成人短剧", "/ai-duanju/{{page}}/"),
        ("热播排行榜", "/ranks/hot/"),
        ...
    ]
])
```

产出（JSON 里的实际字符串）：

```
AI成人短剧::@js:(function(){…return cur})() + "/ai-duanju/{{page}}/"&&热播排行榜::@js:(function(){…})() + "/ranks/hot/"
```

要点：
- JS 里**只用单引号**，路径用双引号包，避免与 `@js:` 段拼接打架
- 拼接表达式整体在 `@js:` 之后，所以 `analyzeJs()` 会把整段（含 `+ "…"`）当 JS 执行
- FIX 内部 `try/catch` 保证 source 不可用时也能返回默认域名
- 分隔符 `&&` 不被 JS 代码污染（别在 FIX 里写 `&&`；本次 FIX 用 `for` + `if` 而非 `&&`）

实测日志（HTTP 日志）：

```
#3534 GET https://pku.hvgbwwrxd.cc/ai-duanju/1/   ← 切了 hg_line=pku，且 {{page}} → 1
#3528 GET https://pku.hvgbwwrxd.cc/topics/hot-aiduanju/3/  ← nextTocUrl 也跟随
```

## 4. 校验清单

1. `eval(source.getExploreUrl())` 后按 `&&` 切、按 `::` 取 url、`eval(url.substring(4))` —— 确认每个 kind 返回预期域名（黄果实测 8/8）
2. HTTP 日志看发现页请求的 host 是否等于 `source.get('hg_line')`
3. 改 `hg_line` 再 check_source，日志 host 应立刻变化（缓存只在整串 @js 时拦路）
4. `{{page}}` 是否变成 `/1/` 而不是字面 `{{page}}`

## 5. 适用范围与限制

- 适用于任何「线路可切换 + 发现页需要跟随」的书源（域名轮换站、发布页选线站）
- 不适用于把整份发现列表放在 @js 里做 JSON 拼装又需要随线路变化的场景 —— 那种仍会被缓存（除非改 exploreUrl 字段本身）
- E 版同样支持（`exploreUrl.startsWith("@js:", true)` 分支 + `AnalyzeUrl.analyzeJs`），但 E 版的 `exploreUrl` 整串 @js 还有额外的 `aCache` 磁盘缓存，per-kind 写法反而更稳
