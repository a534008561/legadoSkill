# 方法：Base64(JSON) 内联型搜索页修复 与 `<js>` 完成值返回协议（261115 38看书/搜搜书蓝本）

> 适用：搜索结果页静态 HTML 里「看不到任何书籍链接」，但页面 title 有关键词、`#list` 是空 div；
> 或书源用了 `webView:true` 却依然列表为空；或 `<js>` 里解出数据但 debug 显示「列表大小:0」。

## 一、站点形态：结果数据是 Base64 内联在 `<script>`，不是静态 DOM

`sososhu.com/?s=关键词&web=38kanshu`（38看书的外包搜索）返回 36KB 页面：

```html
<title>斗破苍穹 - 搜搜书搜索结果</title>
<div id="s-no-result" ...>没有找到相关书籍</div>
<div id="s-list"></div>          <!-- 空壳 -->
<div id="s-pagination"></div>
<script>(function(){
function d(b64){var bin=atob(b64);...return new TextDecoder('utf-8').decode(bytes);}
var books = JSON.parse(d("W3sidXJsIjoi..."));   // 18155 字符 Base64 = 20 本书
var meta  = JSON.parse(d("eyJrZXl3b3JkIjoi...")); // 220 字符 = {total:95,totalPages:5,page:1,...}
// 循环拼 <div class="book-card"> 填充 #s-list，并生成 &page=N 分页
})();</script>
```

**判据三连**：①`<title>` 含关键词（服务端确实认了这次搜索）②页面里有一个巨大的 `d("...")`/`atob(`/`TextDecoder` ③静态 `a[href]` 里没有任何书目链接。

### 旧规则为什么必然空
旧 `bookList` 用 `org.jsoup.Jsoup.parse(result).select("a[href*=38ksw]")` —— DOM 里根本没有 `<a>`（除了导航），且真实结果域名是 `m.wanbenshenzhan.com` 不是 38ksw，双重落空。

### `webView:true` 不是解药，反而是坑
- 数据**服务端已经内联在 HTML**，普通 `java.ajax` 一次 GET 就能拿全，根本不需要执行页面 JS；
- WebView 是**独立 Cookie 栈**。本例登录态是登录面板 `source.putLoginHeader("PHPSESSID=...")` 写进书源请求头的；实测无 Cookie 访问搜索页返回 3.5KB「🔐 需要登录才能搜索」空壳页（0 段 Base64），WebView 若没同步这个头就永远只拿到空壳；
- 结论：**内联数据型页面一律去掉 webView，改普通请求**（登录头/CookieJar 自动带上）。

## 二、★★★ 隐藏坑：json_encode 把 `\/` 混进 Base64 串

站方是「先 `json_encode`（默认转义 `/` 为 `\/`）→ 再 Base64」，导致 books 段里混进 **67 个反斜杠**（第 642、647、745… 位都是 `\\/`）。

- 用严格字符类正则 `d\("([A-Za-z0-9+/=]+)"\)` → **只抓到 meta 那 220 字符的一段**，books 段因第一个 `\` 被截断/漏配；
- 直接把含反斜杠的串喂 `java.base64Decode` → Rhino 报 `SyntaxError: Unexpected token: <乱码>`；
- **正解**：宽松正则 `[^"]+` 抓全段 → `segs[0].replace(/\\/g,'')` 去所有反斜杠 → 再解码。三种清洗（去全部反斜杠 / 仅 `\/`→`/` / 去非 base64 字符）实测等价，取最简的第一种。

`java.base64Decode(base64Str)` 在 Rhino 里**直接返回 UTF-8 解码后的字符串**（已实测中文 `斗破苍穹` 无损），配 `JSON.parse(String(...))` 即可；`base64DecodeToString` 不存在，`base64DecodeToByteArray` 返回 `[B@xxx`，不要用。

## 三、★★★ 通用机制铁律：`<js>` 的返回值是整段脚本的 eval 完成值

源码 `AnalyzeRule.evalJS()`（Kotlin 参考源码在技能库 `debugger/engine/kotlin_reference/AnalyzeRule.kt:828`）：

```kotlin
val script = compileScriptCache(jsStr)
val result = script.eval(scope, coroutineContext)
return result          // ← 返回 Rhino Script.eval 的完成值，不是 bindings["result"]！
```

`getElements` 里 `Mode.Js -> evalJS(rule, result)` 直接拿这个返回值当下一轮 `result`。

**血泪现场**：我把解码脚本包成 `(function(){ ...; result = out.join('\n'); })();`（末尾只赋值、无 return）→ IIFE 完成值 `undefined` → 下一段 `.book-item` 拿到 null → 真机 debug `└列表大小:0`，尽管 App 内单测同一段逻辑明明解出 20 本。日志线索：`┌获取书籍列表`→`└列表大小:0` 之间**有 0.8s 耗时**（脚本里的 profile 请求确实跑了），说明 JS 执行了但返回值丢了。

**三种合法收尾（任选其一）**：
1. 顶层语句，最后一行为表达式：`...; out.join('\n');`（完成值=该字符串）
2. 顶层语句，最后一行赋值：`...; result = out.join('\n');`（赋值表达式完成值=右值，旧书源常用）
3. IIFE **必须显式 return**：`(function(){...; return out.join('\n');})()` ← 本次采用，变量隔离最干净

> 与既有「`@js:` 顶层 return 非法」不冲突：那条说的是整个规则串顶层；**函数体内的 return 永远合法**。
> 与「`<js>` 里 `result=xxx` 供下一段读取」也不冲突：那是**同一 eval 内** bindings 变量与完成值恰好同值的巧合；一旦包了无 return 的 IIFE 就彻底分开。

## 四、聚合结果 host 重写：一套规则复用到底

books 里 `url = https://m.wanbenshenzhan.com/{id}/?token=<uid|时间戳|sha256>`，跟随 2 次 301 后落到完本神站模板（`.chapter-list`），与书源现有的 38看书模板（`.recommend .directoryArea` / `#chaptercontent`）完全不同。

**实测不变量**：把 3 个不同 ID（672 / 94017428 / 93997678）拼成 `https://www.38ksw.com/{id}/`，返回的都是**同一本书、同一模板**（title 一致、两个 `directoryArea` 都在）。⇒ 正解 = 解出 ID 后**重写 host 回本书源主键域名**，详情/目录/正文/发现规则一个字都不用改。

> 方法论：聚合搜索站给「带 token 的第三方域名」时，先验证「同 ID 在本源域名是否存在且同模板」；成立就重写 host，不要为第三方站另写一套规则。token 是一次性跳转凭证（`用户id|unix时间戳|签名`），跟随重定向后自动丢弃，不用保留。

## 五、分页跟随站点自身信号（不写死页数上限）

`meta = {total:95, totalPages:5, page:1}`、渲染脚本里 `var base='/?s='+kw+'&web='+webCode` + `&page=N`。
`searchUrl` 保留 `if(page>1) url+='&page='+page;`，**不写死 5 或任何上限**；站方以后加数据 `totalPages` 变大，翻页自然继续。

## 六、账号级搜索配额：排查时的「零消耗纪律」（重要教训）

本例 `profile` 接口返回 `searchMax:12, searchUsed:N, searchRemaining:...`，是**账号级配额、按 PHPSESSID 追踪、与出口 IP 无关**：
- 沙盒 `curl` 带同一 Cookie、App 内 `java.ajax`、真机 `debug_source` **全部都扣次数**；
- 我排查中反复抓同一个搜索页，把用户「已用 1 次」一路打到 **12/12 用完**，导致当天无法再真机验证。

**纪律**：
1. 用户提醒「次数有限」时，**先抓一次完整 HTML 存成沙盒文件**，后续全部离线分析（解码/正则/结构），不要重复请求搜索接口；
2. 区分「零消耗接口」：`?action=user_api&act=profile`（查配额/登录态，**不扣**）、`act=sign_in`（签到）、登录接口——这些可以随便调；搜索接口才是计费点；
3. 真机 `debug_source` 每次搜索扣 1 次，且会连带跑详情/目录/正文（那些走本站不扣搜索额度），**只在规则定稿后跑一次**，不要拿来当探针；
4. 「无 Cookie 对照实验」用沙盒做（返回需要登录页、不扣额度），别在 App 里做。

## 七、顺手修的另两类通用小坑

1. **Default 规则链只认 `@` 分段**：旧 `coverUrl: "class.synopsisArea_detail tag.img@src"` / `lastChapter: "class.lastchapter tag.a@text"` 用**空格**分段 → jsoup 当整体选择器 → 详情页封面/最新章节恒空。改成 `class.synopsisArea_detail@tag.img@src` / `class.lastchapter@tag.a@text` 即全绿（全书源扫描只这两处）。官方规则文档第 33 行：`▲ @为分隔符`。
2. **分页末页广告要单独看末页**：正文 `nextContentUrl` 拼了 4 页，广告「搜索【看书助手】官方地址…」只在 `_4.html` 出现，第 1 页 `indexOf` 查不到。补清洗分支 `|<p>\s*搜索【看书助手】[^<]*</p>` 追加到现有单 `##` 正则末尾（App 内 eval_js 正反验证：广告 59B 被删、正文完好）。注意 `##` 只能出现在整条组合规则最后，追加分支用 `|` 连接、两侧不留空格。

## 八、验证闭环（本次真机 debug 结果）

```
搜索 列表大小:20（书名/作者/分类/字数/最新章节/简介/封面/详情链接全有值）
详情 封面 http://www.38ksw.com/images/... 、最新章节 第2941章…
目录 50章/页 → 59页 → 2352章
正文 4页拼接、广告清洗干净
```

## 九、排查顺序速查

`页面为空` → ①看 HTTP 状态码/响应体大小（200+3.5KB「需要登录」= 登录态丢了，不是规则错）→ ②看静态 DOM 有没有书目 `<a>`（没有就去翻 `<script>` 里的 `atob/JSON.parse/d("...")`）→ ③解 Base64 前去反斜杠 → ④`<js>` 收尾必须有完成值（IIFE 要 return）→ ⑤结果 URL 域名不对就验证同 ID 本源域名能否重写 → ⑥额度有限时全程离线分析、只跑一次真机 debug。
