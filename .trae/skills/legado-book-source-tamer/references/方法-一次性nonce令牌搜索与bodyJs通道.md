# 方法：一次性 nonce 令牌搜索 + bodyJs 通道（趣书吧 39shuwu 实战）

## 适用场景

站点搜索**不是普通 GET/POST**，而是：

1. 先打开搜索页，服务端在 HTML 里内联下发一串 `var xxx = "..."` 令牌（含签名 `sign`）
2. 前端 JS 把这些令牌 + 关键词 POST 到 `/api/search`
3. 令牌**每次请求都变**（一次性 nonce），不可硬编码、不可缓存复用

典型指纹：搜索页 HTML 里有 20~40 个随机命名的 `var`，且其中一个叫 `sign`（32 位 md5 形态）。
另一个指纹：`common.js` 里有 `search_before()` 之类会 `bgt = bgt.slice(0, bgt.length-1)` 的函数——说明某个令牌是"尾字符校验"型。

## 核心难点：为什么不能直接 `@js:` 返回 JSON

**这是最容易踩的坑，浪费最多时间。**

```jsonc
// ❌ 错误写法
"searchUrl": "@js:(function(){ ...POST...; return jsonText; })()"
```

`AnalyzeUrl.analyzeJs()` 会把 `@js` 的返回值**当作 URL**，拼回 `ruleUrl`，
然后 `analyzeUrl()` 再拿它去请求：

```
GET https://wap.39shuwu.com/{"code":0,"msg":"","data":{...}}  -> 404
```

HTTP 日志里能看到这条荒唐的请求，这就是确诊依据。

`@js:` 只能返回 **URL 字符串**或 **URL + URL选项JSON**，不能返回响应体。

## 正确方案：真实 URL + URL选项 bodyJs

```jsonc
"searchUrl": "https://site.com/user/search.html?q={{java.encodeURI(key)}},{\"bodyJs\":\"<内联脚本>\"}"
```

机制（源码 `AnalyzeUrl.executeStrRequest`）：

1. 框架先 GET 这个真实 URL → 拿到搜索页 HTML（里面有令牌）
2. 请求成功后，若 `bodyJs != null`：`evalJS(bodyJs, it.body)` → **返回值替换 body**
3. `bodyJs` 环境里有 `result`（= 响应体字符串）和 `key`、`page`、`java`、`baseUrl`

所以在 `bodyJs` 里可以：读令牌 → POST → 返回 JSON 字符串。

### 关键坑：bodyJs 里必须内联，不能调 jsLib 函数

```jsonc
// ❌ 错误
"searchUrl": ".../search.html?q={{key}},{\"bodyJs\":\"FQ_doSearch()\"}"
// ReferenceError: "result" 未定义

// ✅ 正确：全部内联
"searchUrl": ".../search.html?q={{key}},{\"bodyJs\":\"var _p=String(result||''); ... _txt\"}"
```

原因：`jsLib` 里的函数在 `SharedJsScope` 里预编译，其闭包作用域**不包含**本次 `evalJS` 的
`result`/`key` 等局部绑定。所以 jsLib 函数只能接收显式参数，不能读这些隐式绑定。

> 登录按钮等场景可以用 jsLib（因为传的是 `java` 显式参数）；
> 但 `bodyJs`/`loginCheckJs`/规则 `@js:` 这类依赖隐式绑定的，必须内联或把值当参数传进去。

### 完整模板

```jsonc
"searchUrl": "https://site.com/user/search.html?q={{java.encodeURI(key)}},{\"bodyJs\":\"var _ua='<UA>';var _page=String(result||'');var _q=java.encodeURI(String(key));var _re=/var\\\\s+([A-Za-z_$][\\\\w$]*)\\\\s*=\\\\s*\\\"([^\\\"]*)\\\"/g;var _m,_tk={};while((_m=_re.exec(_page))!==null){_tk[_m[1]]=_m[2];}if(!_tk['sign']){throw new Error('搜索令牌未获取到');}var _body='q='+_q;for(var _k in _tk){if(_k!=='sign'){_body=_body+'&'+_k+'='+encodeURIComponent(_tk[_k]);}}_body=_body+'&sign='+_tk['sign'];var _resp=java.post('https://site.com/api/search',_body,{'User-Agent':_ua,'Referer':'https://site.com/user/search.html?q='+_q,'Origin':'https://site.com','X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded'});var _txt=String(_resp.body());if(!_txt){throw new Error('接口无响应');}if(_txt.indexOf('太频繁')>=0){throw new Error('⏳限频，请稍候');}if(_txt.indexOf('\\\"code\\\":0')<0){throw new Error('搜索失败: '+_txt.substring(0,120));}_txt\"}"
```

注意 JSON 转义层级：`searchUrl` 本身是 JSON 字符串，`bodyJs` 又是它的嵌套字符串，
所以正则里的 `\s` 要写成 `\\\\s`，引号 `"` 要写成 `\\\"`。
**写完一定要用 `json.load()` 校验，再看 App 里实际解析出来的字符串是否与预期一致。**

## `java.post` vs `java.ajax` 的返回值差异

| API | 返回 | 取文本 |
|---|---|---|
| `java.ajax(url)` | String | 直接用 |
| `java.ajax(url, headers)` | ❌ 不存在此重载 | — |
| `java.post(url, body, headers)` | jsoup `Connection.Response` | **必须 `.body()`** |

`java.post` 直接 `String(resp)` 会得到 `org.jsoup.helper.HttpConnection$Response@xxx`。

## 限频的真相：服务端按 IP 记账

**对照实验（含反向验证组）**：

| 组 | 条件 | 结果 |
|---|---|---|
| E1 | 新会话 + 完整令牌 + Origin 头 + 等 75s | 太频繁 |
| E2 | 正确 sign | 太频繁 |
| E3 | **错误** sign（反向验证） | 太频繁（同消息） |
| E4 | 缺 sign | 太频繁 |
| E5 | **全新连接、零 cookie** | 太频繁 |

结论：
1. **cookie/sign/UA 都不是限频维度**——E5 把 cookie 全清（比 `removeCookies` 更彻底）仍然被限
2. 限频判定在**签名校验之前**（E2~E4 同消息）
3. 失败请求会**刷新冷却窗口**，所以连续试探只会把惩罚期越拖越长
4. 沙盒出口 IP 被惩罚 ≠ 用户手机被限（用户手机是独立 IP）

**因此：不要试图用 `removeCookies`/换 UA/换 sign 绕过 IP 级限频，这是无效的。**
正确做法是 `concurrentRate` 约束 + 触发时给出清晰提示。

## 关联坑：StrResponse.body 是方法引用

`loginCheckJs` 的 `result` 是 `StrResponse` 对象。在 Rhino 里：

```javascript
typeof result.body   // "function"  ← 方法引用，不是文本！
String(result.body)  // "function body() { java.lang.String body() }"
result.body()        // ✅ 才是文本
```

原因：`StrResponse` 同时有 `var body: String?` 属性和 `fun body()` 方法，Rhino 优先解析成方法。

另外 `loginCheckJs` 的 `evalJS` 是**顶层脚本**，`return` 非法（`EvaluatorException: 返回的值无效`）。
必须用末尾表达式语句把值交回：

```javascript
var _b=String(result.body());
if(_b.indexOf('请登录')>=0){throw new Error('未登录');}
result          // ← 末尾表达式，不是 return result;
```

## 配套坑：jsoup `:eq()` 是文档级索引

```jsonc
// 详情页 article .info 下有 6 个 p（0空白/1作者/2类别/3状态/4更新/5最新）
"author": "article .info p:eq(1)@text##作者：##"   // ✅
```

`:eq(n)` 不是"当前上下文的第 n 个"，在 article 上下文里 `p:eq(0)` 会取不到、`p:eq(1)` 才是第一个 p。
**必须先用 `Jsoup.parse` 实测确认索引**，不能凭 HTML 顺序猜。

## 配套坑：`##` 是替换不是拼接

```jsonc
// ❌ 想把详情页 URL 变目录页 URL
"tocUrl": "##mulu.html"        // 结果: URL + 整个HTML
// ✅
"tocUrl": "@js:baseUrl + 'mulu.html'"
```

## 配套坑：exploreUrl 格式

`exploreKinds()` 只认两种：

- JSON **数组**：`[{"title":"分类","url":"/x/"},...]`
- `标题::url&&标题2::url2`

```jsonc
// ❌ JSON 对象不被识别 → check_source 报「发现失效」
"exploreUrl": "{\"分类\":\"/x/\"}"
```

## 排查顺序（照做可省数小时）

1. **看 HTTP 日志**。若出现 `GET https://site/{"code":0...}` 这种把 JSON 当 URL 的请求 → `@js:` 返回了 body
2. `eval_js` 里单独跑令牌抓取 + POST，确认接口本身通
3. 若接口通但列表为 0 → 检查 `ruleSearch.bookList` 的 JSONPath，用 `Packages.com.jayway.jsonpath.JsonPath` 直连验证
4. 若详情/目录字段是整段 HTML → 是 `p@text` 多匹配，改 `:eq(N)`（先实测索引）
5. 若 `tocUrl` 拼出 `URL+HTML` → 是 `##` 误用，改 `@js:`
6. 若 `check_source` 报发现失效 → 先查 `exploreUrl` 格式

## 本源最终结构（可作模板）

- 搜索：`/user/search.html?q=` + `bodyJs` → `POST /api/search`
- 详情：`article .info p:eq(N)` + `.introbar` + `.image img@src`
- 目录：`ul.chapter li a`（单页全量，1263 章实测无分页）
- 正文：`#text p@text`（无广告、无章内分页）
- 发现：`#list article`，6 分类 + 13 榜单
- `concurrentRate: 1/1500`

---

## 追加：loginUi 显示 "null" 的根治（viewName 陷阱）

### 现象
登录界面出现 `null` 字样（输入框 hint 或按钮文字）。

### 源码实锤（SourceLoginDialog.rowUiBuilder）

```kotlin
// button
Type.button -> { rowView.text = rowUi.viewName ?: rowUi.name }

// text
if (viewName == null) {
    it.textInputLayout.hint = name                      // ✅ 安全
} else if (viewName.length in 3..19
           && viewName.first() == '\'' && viewName.last() == '\'') {
    it.textInputLayout.hint = viewName.substring(1, viewName.length - 1)  // ✅ 字面量
} else {
    it.textInputLayout.hint = name
    execute { evalUiJs(viewName) }
        .onSuccess { n ->
            if (n.isNullOrEmpty()) it.textInputLayout.hint = "null"   // ← 元凶
            else it.textInputLayout.hint = n
        }
        .onError { _ -> it.textInputLayout.hint = "err" }              // ← 元凶
}
```

三条路只有两条安全。**`viewName` 只要非 null、又不是 `'xxx'` 字面量形式，就会走 eval，
求值为空直接显示 `"null"`，抛错显示 `"err"`。**

`evalUiJs` 执行的是 `"$loginUrl\n$viewName"`：
```javascript
https://site.com/user/login.html      // ← 被 Rhino 当标签语句+除号/正则，纯属碰巧不报错
'点击上方按钮检查'                      // ← 末尾表达式才是返回值
```
这段能跑通纯属侥幸；一旦 `loginUrl` 写成函数体、或 `viewName` 里有变量，就会炸成 `err`/`null`。

### 修法（最稳，推荐）

**`loginUi` 里 button / text 一律不写 `viewName`。**

```jsonc
"loginUi": "[{\"type\":\"button\",\"name\":\"①检查登录状态\",\"action\":\"FQ_checkLoginState(java)\"},{\"type\":\"button\",\"name\":\"②打开登录页\",\"action\":\"FQ_openLoginPage(java)\"},{\"type\":\"text\",\"name\":\"登录状态\"}]"
```

效果：
- button 显示 `name`
- text 用 `name` 作 hint（走 `viewName == null` 分支，**绝不 null**）

想让按钮文字更醒目就把文案写进 `name`（如上例的 ①②）。

### 配套：结果回写必须对齐 name

```javascript
jv.upLoginData({ '登录状态': msg });   // key 必须 === text 行的 name
```
不一致的话结果写不进去，界面还是空。

### 配套：三重提示保险

`upLoginData` 在某些版本/场景可能被吞，所以三个都发：

```javascript
try { jv.upLoginData({ '登录状态': msg }); } catch (e1) {}
try { jv.toast(msg); } catch (e2) {}
try { jv.longToast(msg); } catch (e3) {}
try { jv.reLoginView(false); } catch (e4) {}   // 刷新面板
```

### 配套：登录判定别用宽泛词

```javascript
// ❌ '退出' —— 页面 JS/样式里常有该字样，误判为已登录
if (s.indexOf('退出') >= 0) msg = '已登录';

// ✅ 用页面上真正只出现在已登录态的文案
if (s.indexOf('退出登录') >= 0 || s.indexOf('修改密码') >= 0) msg = '已登录';
else if (s.indexOf('请登录') >= 0) msg = '未登录';
else msg = '状态未知';
```

### 排查清单
1. 看到 `null` → 检查 `loginUi` 里每条 `viewName`，**全部删掉**
2. 看到 `err` → 同上，或 `loginUrl` 被写成非法 JS
3. 点按钮有 toast 但输入框不变 → `upLoginData` 的 key 与 text 行 `name` 不一致
4. 点按钮完全没反应 → `action` 里引用了 `source`（该环境无 `source` 绑定），只能用 `java`
5. 判定结果总是"已登录" → 判定词太宽泛（如 `'退出'`），换精确词

---

## 追加：登录面板 `jv.ajax(url, headers)` 重载不存在

### 现象

```
检查失败:InternalError: 找不到方法
  "io.legado.app.ui.rss.read.RssJsExtensions.ajax(string,object)"
```

### 源码实锤（JsExtensions.kt）

```kotlin
fun ajax(url: Any): String?                        // ✅ 只有这个和下面一个
fun ajax(url: Any, callTimeout: Long?): String?    // ← 第二个参数是「超时毫秒」，不是 headers！
fun get(urlStr: String, headers: Any?): Connection.Response   // ← 带 header 的是 get
fun post(urlStr: String, body: String, headers: Any?): Connection.Response
fun head(urlStr: String, headers: Any?): Connection.Response
```

**`ajax` 根本没有 headers 重载。** 传 object 进去 Rhino 找不到匹配方法就抛 `InternalError`。

继承链确认（登录面板里 `jv` 的实际类型）：
```
SourceLoginJsExtensions : RssJsExtensions : JsExtensions
```
所以 `jv` 能用 `JsExtensions` 的全部方法，但签名必须严格对上。

### 三种正确写法对比

| 写法 | 返回 | 带自定义 header | 走书源 CookieJar | 推荐度 |
|---|---|---|---|---|
| `jv.ajax(url)` | String | ❌（用书源 header） | ✅ | ⭐⭐⭐ 首选 |
| `jv.get(url, headers)` | `Connection.Response` | ✅ | ❌ 直连 Jsoup | ⭐⭐ 兜底 |
| `jv.post(url, body, headers)` | `Connection.Response` | ✅ | ❌ 直连 Jsoup | 提交表单时用 |

**首选 `jv.ajax(url)`**：它内部走 `AnalyzeUrl(urlStr, source = getSource())`，
会自动套用书源的 `header` 和 **cookie jar**，登录态天然能带上。

`jv.get` 走 `Jsoup.connect(...).headers(requestHeaders)`，是**直连**：
- 不读 CookieStore（只带你手写的 header）
- `followRedirects(false)`，302 要自己处理
- 返回 `Connection.Response`，必须 `.body()` 取文本

### 稳健写法（双通道 + 明确兜底）

```javascript
function FQ_checkLoginState(jv) {
  var msg = '';
  try {
    var s = '';
    try {
      s = String(jv.ajax('https://site.com/user/userinfo.html') || '');   // 首选
    } catch (e1) {
      try {
        s = String(jv.get('https://site.com/user/userinfo.html', {}) || ''); // 兜底
      } catch (e2) { s = ''; }
    }
    if (!s) msg = '检查失败: 无响应';
    else if (s.indexOf('退出登录') >= 0 || s.indexOf('修改密码') >= 0) msg = '已登录';
    else if (s.indexOf('请登录') >= 0) msg = '未登录';
    else msg = '状态未知(未登录或页面结构变更)';
  } catch (e) {
    msg = '检查失败:' + e;
  }
  try { jv.upLoginData({ '登录状态': msg }); } catch (e3) {}
  try { jv.toast(msg); } catch (e4) {}
  try { jv.longToast(msg); } catch (e5) {}
  try { jv.reLoginView(false); } catch (e6) {}
}
```

### 反向验证（确认根因，不做无根据推断）

```javascript
// 错误写法 —— 复现同样的报错
java.ajax('https://site.com/x.html', {'User-Agent':'x'});
// → InternalError: 找不到方法 "...BookSource.ajax(string,object)"

// 正确写法 —— 正常返回
String(java.ajax('https://site.com/x.html'));
// → 200，len=2924
```

注意报错里的类名前缀会随调用环境变化（`RssJsExtensions` / `BookSource` / `AnalyzeUrl`），
**但根因一致：第二个参数类型不匹配。**

### 排查清单
1. 报「找不到方法 xxx.ajax(string,object)」→ `ajax` 传了第二参数，删掉或改 `get`
2. 报「找不到方法 ...ajax(string,number)」→ 传的是 number，会被当 callTimeout，**能跑通但语义错了**（不会报错，更隐蔽）
3. `jv.get` 拿不到登录态 → 它不读 CookieStore，改回 `jv.ajax(url)` 或用 `cookie.getCookie()` 手动塞 header
4. `jv.get` 返回 302 空体 → 它 `followRedirects(false)`，需自己跟或换 `jv.ajax`

---

## 追加：loginUrl 必须是 JS 函数（"Function login not implements!!!"）

### 现象

点登录面板右上角 ✓：

```
登录出错
Function login not implements!!!
Source context:
  1: https://wap.39shuwu.com/user/login.html
> 2: if (typeof login=='function') { login.apply(this); } else { throw('Function login not implements!!!') }
```

### 源码实锤（SourceLoginDialog.login）

```kotlin
val loginJS = loginUrl
if (!loginJS.isNullOrBlank()) {
    val buttonFunctionJS =
        "if (typeof login=='function'){ login.apply(this); } else { throw('Function login not implements!!!') }"
    runScriptWithContext {
        source.evalJS("$loginJS\n$buttonFunctionJS") {
            put("java", sourceLoginJsExtensions)
            put("result", loginData)      // ← loginUi 各输入的 Map，key 就是 name
            put("book", viewModel.book)
            put("chapter", viewModel.chapter)
            put("isLongClick", false)
        }
    }
}
```

**`loginUrl` 不是"登录页地址"，而是一段 JS 脚本。**
写成纯 URL，`typeof login` 就是 `undefined`，直接抛这个错。

> 注意：`loginUrl` 同时被 `BaseSource.getLoginJs()` 使用：
> ```kotlin
> fun getLoginJs(): String? {
>     val loginRule = loginUrl?.trim()
>     if (loginRule.isNullOrBlank()) return null
>     return extractInlineJs(loginRule) ?: loginRule   // <js>…</js> 则提取内部，否则原样当 JS
> }
> ```
> 所以裸 JS 直接写即可，不需要包 `<js>`。

### 前置条件：loginData 不能为空

```kotlin
val loginData = getLoginData(rowUis)
if (loginData.isEmpty()) {
    source.removeLoginInfo()
    dismiss()          // ← 直接关掉，根本不执行 loginUrl
    return
}
```
所以 `loginUi` 里**至少要有一个 text/password 输入**，否则点 ✓ 只会静默关闭。

### 正确写法

```jsonc
"loginUi": "[{\"type\":\"text\",\"name\":\"用户名\"},{\"type\":\"password\",\"name\":\"密码\"},{\"type\":\"text\",\"name\":\"登录状态\"}]",
"loginUrl": "function login() {\n  var u = String(result['用户名'] || '').replace(/^\\s+|\\s+$/g, '');\n  var p = String(result['密码'] || '').replace(/^\\s+|\\s+$/g, '');\n  if (!u) { java.longToast('请填写用户名'); return; }\n  if (!p) { java.longToast('请填写密码'); return; }\n  var resp = java.post('https://site.com/api/login',\n    'username=' + encodeURIComponent(u) + '&password=' + encodeURIComponent(p),\n    {'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest'});\n  var txt = String(resp.body());\n  var jo = JSON.parse(txt);\n  if (String(jo.code) === '0') {\n    java.upLoginData({ '登录状态': '✅ 登录成功' });\n    java.longToast('✅ 登录成功');\n  } else {\n    java.upLoginData({ '登录状态': '❌ ' + (jo.msg || '登录失败') });\n    java.longToast('❌ ' + (jo.msg || '登录失败'));\n  }\n}"
```

要点：
1. `result['xxx']` 的 key **必须等于** `loginUi` 里那一行的 `name`
2. 脚本末尾不需要 `login()` 调用——外层会自动 `login.apply(this)`
3. 不要写 `return` 在函数外；`function login(){...}` 内部 return 是合法的

### 追加坑：登录成功但 cookie 没保存

`java.post` 走 `Jsoup.connect(...).execute()` **直连**，不经过 Cronet：

```kotlin
fun post(urlStr: String, body: String, headers: Any?, timeout: Int?): Connection.Response {
    val requestHeaders = if (getSource()?.enabledCookieJar == true) {
        headerMap.toMutableMap().apply { put(cookieJarHeader, "1") }
    } else headerMap
    val response = rateLimiter.withLimitBlocking {
        Jsoup.connect(urlStr)...execute()      // ← 纯 Jsoup，无拦截器
    }
    return response
}
```

而 `cookieJarHeader`（值 `"CookieJar"`）只在 **Cronet** 链路里被识别：
- `CronetInterceptor`：`if (newReq.header(cookieJarHeader) != null) newReq = CookieManager.loadRequest(newReq)`
- `AbsCallBack`：`saveCookiesFromHeaders(...)`

`Jsoup.connect` 只会把它当普通 header 发给服务器。**所以 Set-Cookie 不会落库。**

同理 `CookieManager.saveResponse(Connection.Response)` 在 JS 里**调不通**
（`CookieManager.INSTANCE` 在 Rhino 里是 JavaPackage，不是实例）。

**解决**：登录成功后手动解析并写回：

```javascript
var sc = resp.header('Set-Cookie');
if (sc) {
  // 注意 Expires 里也有逗号，按「逗号 + 后面紧跟 k=v」切分
  var arr = String(sc).split(/,\s*(?=[A-Za-z0-9_]+=)/);
  for (var i = 0; i < arr.length; i++) {
    var mm = arr[i].match(/(^|;\s*)SID=([^;]+)/);
    if (mm) { cookie.setCookie('https://site.com/', 'SID=' + mm[2]); break; }
  }
}
```

`cookie.setCookie(url, "k=v")` 是**合并写入**（实测：写入 `FQ_TEST=1` 后原 `SID` 仍在）。

### 排查清单
1. `Function login not implements!!!` → `loginUrl` 写成了 URL，改成 `function login(){...}`
2. 点 ✓ 后无声关闭 → `loginUi` 没有 text/password，`loginData` 为空
3. 提示登录成功但检查仍是未登录 → cookie 没保存，加 `cookie.setCookie` 手动写
4. `result['用户名']` 取不到 → key 与 `loginUi` 的 `name` 不一致
5. 想用 `java.ajax` 登录 → 它没有 POST 重载，必须用 `java.post`
