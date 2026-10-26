# 方法：Legado 登录面板三协议辨析与 E 版兼容方案

> 沉淀日期：2026-10-27　｜　来源：黄果短剧登录面板「各功能失效」排查（用户要求兼容 Legado-E）
> 症状：书源有 `loginUrl` + `loginUi`，登录界面能打开，但**所有按钮点不动/输入框无效**。

---

## 0 根因速查

| 现象 | 根因 | 判定依据 |
| --- | --- | --- |
| 界面能开但**所有功能失效** | `loginUi` 字段**格式非法**（既不是 V1 JSON 数组，也不是 V2 对象）→ `GSON.fromJsonArray<RowUi>` 解析失败 | `SourceLoginDialog.loginUi(json)` → `parseLoginUi` → `GSON.fromJsonArray<RowUi>` |
| 界面空白 + 「渲染结果格式错误」 | V2 的 `loginUi(state)` 未返回 `{"rows":[...]}` | `LoginUiV2.parseRender` |
| 按钮点了没反应 | action 里的 `source` 未定义 / 函数名写错 / 抛异常被 `runCatching` 吞 | `handleButtonClick` 的 `.onFailure` 只写日志 |
| V2 报错「state 格式错误」 | `String(state)` 得到 `"[object Object]"`（state 已是 JSON.parse 后的对象） | `evalLoginActionV2` 绑定 `__loginState` |

---

## 1 三协议对照（源码级）

### V1 静态（**E 版唯一可用形态**）

```kotlin
// BaseSource.hasLoginForm()
val form = loginUi?.trim().orEmpty()
return form.isNotEmpty() && form.filterNot { it.isWhitespace() } != "[]"

// SourceLoginDialog.loginUi(json) → parseLoginUi
GSON.fromJsonArray<RowUi>(json)
```

⇒ `loginUi` 字段 = **JSON 数组字符串**。

```json
[{"name":"发布页地址","type":"text","key":"pub","default":"https://..."},
 {"name":"获取网址","type":"button","action":"FQ_go()"}]
```

### V1 动态（`<js>` 形式）

```kotlin
// BaseSource.getLoginUiJs() = extractInlineJs(loginUi)
// AppPattern.JS_PATTERN = "<js>([\\w\\W]*?)</js>|@js:([\\w\\W]*)"  ← matcher.matches() 要求整串匹配
```

`handleReUiView`：
```kotlin
val codeStr = source.getLoginUiJs()
if (codeStr != null) { renderLoginUi(source, codeStr, deltaUp, installMenu = false) }  // ★ 重新执行 JS
else { rowUis = loginUi(loginUiStr); rowUis?.let { rowUiBuilder(source, it, deltaUp) } }
```

⇒ `loginUi` = `<js>FQ_rows()</js>`，脚本返回值必须是 **JSON 数组字符串**。

### V2（**新版特性，E 版不支持**）

```kotlin
// BaseSource.evalLoginUiV2
evalJS("$loginJs\nloginUi(JSON.parse(String(__loginState)))")
// BaseSource.evalLoginActionV2
evalJS("$loginJs\nloginAction(String(__loginAction), JSON.parse(String(__loginState)), JSON.parse(String(__loginForm)))")
```

`loginUi` 字段 = `{"version":2}`（`LoginUiV2.MARKER = """{"version":2}"""`）。

`loginUrl` 里必须定义：
```js
function loginUi(state)      { return JSON.stringify({rows:[...]}); }
function loginAction(action, state, form) { return JSON.stringify({state:..., error:...}); }
```

> ⚠️ **`state` 是 JSON.parse 后的对象** → 必须 `JSON.stringify(state)`，用 `String(state)` 会得到 `"[object Object]"`。

---

## 2 ★★ V1 的 viewName = JS 动态文本（E 版兼容动态面板的关键）

源码 `SourceLoginDialog.rowUiBuilder`：

```kotlin
// text 行
if (viewName == null) { hint = name }
else if (viewName.length in 3..19 && viewName.first()=='\'' && viewName.last()=='\'') {
    hint = viewName.substring(1, viewName.length-1)
} else {
    hint = name
    execute { evalUiJs(viewName) }.onSuccess { n -> hint = n }   // ★ viewName 是 JS 表达式
}

// button 行
if (viewName == null) { textView.text = name }
else if (viewName.length in 3..19 && ...) { textView.text = n }
else {
    textView.text = name
    execute { evalUiJs(viewName) }.onSuccess { n -> textView.text = n }   // ★
}
```

### ⇒ 配方：**静态数组 + viewName 为 JS 表达式**

```json
[
 {"name":"发布页地址","type":"text","key":"pub","default":"https://huangguoai.pages.dev/publish.js"},
 {"name":"获取网址并测速","type":"button","action":"FQ_go()"},
 {"name":"线路1","type":"button","viewName":"FQ_siteName(0)","action":"FQ_pick(0)"},
 {"name":"线路2","type":"button","viewName":"FQ_siteName(1)","action":"FQ_pick(1)"}
]
```

```js
function FQ_siteName(i){
  var a = JSON.parse(String(source.get('hg_sites')||'[]'));
  if(i>=a.length) return '';
  return a[i].host+' '+a[i].ms+'ms';
}
```

**好处**：行数固定（任何版本都能解析）+ 按钮文本/输入框 hint **动态**（每次渲染执行一次 viewName JS）+ **不依赖 `reLoginView`**。

---

## 3 三个 JS 环境的绑定（源码实锤）

| 环境 | 源码位置 | `source` | `java` | `result` |
| --- | --- | --- | --- | --- |
| **规则 @js:** | `AnalyzeRule.evalJS` | ✅ | ✅ AnalyzeUrl | ✅ |
| **V1 action** | `SourceLoginDialog.handleButtonClick`<br>`source.evalJS("$loginJS\n$buttonFunctionJS"){put("java",sourceLoginJsExtensions);…}` | ✅ **有** | ⚠️ 被覆盖成 `SourceLoginJsExtensions` | ✅ getLoginData |
| **V1 loginUi JS** | `evalUiJsResult` → `source.evalJS("$loginJS\n$jsStr")` | ✅ | ✅ | ✅ |
| **V2** | `BaseSource.evalLoginUiV2/evalLoginActionV2` → `source.evalJS(...)` | ✅ | ✅ | — |

**要点**：

1. **`loginUrl` 的函数在 loginUi / action 环境全都可用**（`"$loginJS\n$jsStr"` 拼接）⇒ 定义一次，到处用。
2. `source` 在 action 里**可用**（`BaseSource.evalJS` 里 `bindings["source"] = this` 不会被 `put("java",…)` 覆盖）。
3. `java` 在 action 里 = `SourceLoginJsExtensions`，可用：`put/get`（与 `source.put/get` **同一键空间**）、`toast/longToast`、`ajax/get/post/head`、`reLoginView/reUiView`（**新版专有，可能不存在**）、`refreshExplore`、`copyText`。
4. `loginUrl` **必须**有 `function login(){}`，否则点「登录」抛 `Function login not implements!!!`（`BaseSource.login()`）。

---

## 4 并发测速（线路/镜像站选线必备）

```js
var urls = []; for(...) urls.push(host + '/');
var res = java.ajaxAll(urls);          // ★ 并发，AppConfig.threadCount
for (var i=0;i<res.length;i++){
  var code=0, ct=-1, bl=0;
  try{ code = res[i].raw.code(); }catch(e){}   // ★ 属性在 Rhino 里是方法，必须调用
  try{ ct   = res[i].callTime(); }catch(e){}
  try{ bl   = String(res[i].body()).length; }catch(e){}
  if(code>=200 && code<400 && bl>20000) rows.push({url:..., ms:ct});
}
```

### ★ Rhino 里 Kotlin 属性是方法

`StrResponse.code` / `callTime` / `body` 在 Rhino 里返回的是**方法引用字符串**（`function code() {/* int code() */}`），必须 `r.code()`、`r.callTime()`、`r.body()`。

直接 `String(r.code)` 会得到 `"function code() {...}"`（长度 ~30，**看起来像成功但判据全错**）。

### `java.ajaxTestAll(urlList, timeout)` 别用

```kotlin
fun ajaxTestAll(urlList: Array<String>, timeout: Int): Array<StrResponse> {
    ... analyzeUrl.getStrResponseAwait(isTest = true, ...)
}
```

`isTest=true` 时**不真正发请求**（返回空壳 Response，body 长度 ~48），实测 3 个 URL 98ms 返回但内容无效。

### 串行兜底

`java.ajaxAll` 不存在时（老版本）退回逐个 `java.ajax(url)` + 长度判据。

---

## 5 探针法：验证 loginUi / action 是否真的执行

`getLoginInfoMap()` 在 `loginUi` 为 `<js>` 形式时会执行该 JS（源码 `BaseSource.getLoginInfoMap`）：

```js
// 临时把 loginUi 改成 <js> 形式做验证
function FQ_probeAll(){
  var out=[];
  function t(k,fn){try{out.push({name:k,type:'text',key:k,default:String(fn())})}
                   catch(e){out.push({name:k,type:'text',key:k,default:'ERR:'+String(e).substring(0,80)})}}
  t('p_siteName0', function(){ return FQ_siteName(0); });
  t('p_cand',      function(){ return hgCand().length; });
  t('p_pick0',     function(){ FQ_hgPick(0); return 'called'; });
  return JSON.stringify(out);
}
```

**要点**：
- 返回的行**必须带 `key`**（`getLoginInfoMap` 里 `associate { it.name to (it.default ?: "") }`，无 default 的行取不到值）
- 验证完**必须还原** `loginUi` 为正式静态数组
- 探针函数名不要留在正式版（会被误当正式函数）

---

## 6 E 版兼容清单

| 特性 | E 版 | 备注 |
| --- | --- | --- |
| V1 静态 `loginUi` JSON 数组 | ✅ | **首选** |
| V1 `viewName` 为 JS 表达式 | ✅（老机制） | 动态面板的核心手段 |
| `action` = JS 函数调用 | ✅ | `action:"FQ_xxx()"` |
| `source.get/put` | ✅ | 与 `java.put/get` 同一键空间 |
| `java.reLoginView()` | ❌ 可能无 | 必须 try/catch 兜底 + 提示「重新打开面板」 |
| V2 `{"version":2}` | ❌ | 新版专有 |
| `java.ajaxAll` | ⚠️ | 老 API 大概率有，仍加串行兜底 |

**兜底话术**：测速后 toast 里带上「若按钮名未刷新，重新打开本面板即可」——因为 `viewName` 的 JS **每次渲染都会重跑**，重新打开面板即拿到最新文本。

---

## 7 排查顺序

```
1. 读 loginUi 字段 → 是合法 JSON 数组？→ 否 ⇒ 格式非法（最常见）
2. loginUrl 里有没有 function login()？→ 没有 ⇒ 点登录必抛
3. action 名与 loginUrl 里的函数名对得上？
4. action 里用了 source？→ 用 source.get/put（不是 java.get/put，虽然同键空间）
5. 依赖 reLoginView？→ try/catch 兜底
6. 探针法验证：<js> 形式 + getLoginInfoMap()
```
