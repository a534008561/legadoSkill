# 方法-AEGIS(ALTCHA PoW)验证与WebView通道书源

> 蓝本：69shuba.tw（69书吧·繁中,2026-09-25）— 该站 Cloudflare + 自研 AEGIS 双防线，
> 所有非浏览器客户端（含 Legado 原生网络）被 403 人机验证页永久拦截，
> 解法 = **把书源的 HTTP 传输整体挂到 Legado 后台 WebView(真实 Chromium 内核) 通道上**，
> 让验证凭据在"浏览器"内签发后复用。check_source 通过 1/1 + 全链路 debug 实测通过。

## 0 一句话总结

**凡页面请求行不通的书源，先别急着调规则——用 `java.webView(null, url, null)` 探一次：
若浏览器内核能通、原生网络 403，就把 loginCheckJs 做成「验证页 → webView 重取 → 构造 StrResponse 返回」的传输层，
上层的搜索/详情/目录/正文规则照常写。**

## 1 现象谱系（何时怀疑是 AEGIS/ALTCHA）

- 任意路径（含 /robots.txt）都返回 **403 + 3200 字节左右** 的相同页面；
- 页面 `<title>Verification</title>`，body 含 `<altcha-widget challenge='{...}'>` 和
  `/aegis_altcha_object/altcha.min.js?rule_uuid=...`、`/aegis_altcha_verify?rule_uuid=...`；
- 普通 curl/python/OkHttp 全 403；**但浏览器能正常访问**（用户不觉得网站坏了）；
- 403 页带中文文案"请稍候，正在验证…"且浏览器里秒过后自动刷新出真页。

同类报错对照：Cloudflare "Just a moment"（challenge-platform）、GoEdge `/WAF/VERIFY`、
lianaiya 的 503+"var token"——都不含 altcha-widget，别混。

## 2 协议逆向（完整流程,一次搞清）

AEGIS = 基于 altcha.org 组件魔改的 PoW 反爬。403 页内联 challenge JSON：

```json
{"parameters":{"nonce":"32hex","cost":1000,"keyLength":32,"expiresAt":1790276532,
"keyPrefix":"32hex","keySignature":"64hex","algorithm":"PBKDF2/SHA-256","salt":"32hex",
"data":{"rule_uuid":"...","ip":"客户端IP","ja4":"t13d..."}},
"signature":"64hex"}
```

求解器（widget 里 `za`/`Fa` 两个 Worker 脚本，逻辑一致，均为**定制 PBKDF2 变体**，
注意与 WebCrypto 标准 PBKDF2 不同）：

```js
password = hex(nonce) + uint32BE(counter)
i==0: data = hex(salt) + password
i>0:  data = derivedKey
derivedKey = SHA256(data).slice(0, keyLength)   // 共迭代 cost 次
// 命中条件: derivedKey 十六进制以 keyPrefix 开头
```

提交流程：`POST /aegis_altcha_verify?rule_uuid=...` body `{"altcha": base64(JSON{
challenge:{parameters,signature}, solution:{counter,derivedKey,time}})}` → Set-Cookie（如 `__ct_cya_ckt`）→ reload。

### ★判活铁律：先数 keyPrefix 位数（决定你在哪个"待遇档"）
- **keyPrefix 长达 32 hex（16 字节）＝ 永远解不出来** —— 这是给"非浏览器指纹"的 deny-by-design；
  `cost`、`expiresAt` 等其余参数照发不误，纯属诱饵。
- 浏览器档挑战前缀很短（几 hex），Worker + WebCrypto 秒级可解。
- widget 的 `G()` 只是 `JSON.parse` 内联属性，没有二次抓取接口——别幻想"拿个更简单的挑战"。
- 别指望手工/脚本 PoW：拿到 16 字节前缀就是官方劝退，正确出路是**换通道**而非硬算。

## 3 为什么 Legado 原生网络全灭（含 Cronet）

实测两级结论：
1. OkHttp 请求被 AEGIS 记下 `ja4`（TLS 指纹，非浏览器）→ 每次都发 16 字节前缀挑战；
2. **WebView 首访即过、拿到 `__ct_cya_ckt` Cookie；同一 Cookie 塞回 OkHttp 请求照样 403**——判级发生在
   每次请求的 TLS/指纹层面，浏览器 Cookie 不能给 OkHttp 栈升级。所以"登录一次拿 Cookie 存 CookieStore"这类
   常规套路在本类站无效。

## 4 正解架构：WebView 通道 + loginCheckJs 传输层

### 4.1 源码级依据（LegadoTeam/legado,已核实）
- `JsExtensions.webView(html,url,js)`: html 为 null 时走 **`BackstageWebView.loadUrl(url)` = 真 Chromium 网络栈**；
  默认 JS 常量返回 `document.documentElement.outerHTML`（`BackstageWebView.JS`）。
- `webView` 默认实现即接口方法：**规则上下文（AnalyzeUrl）、登录面板（SourceLoginJsExtensions）都能调**；
  要求后台线程（`if (isMainThread) error(...)`）；内部 `withTimeout 60s`。
- `tag = getSource()?.getKey()` → 绑定书源运行时调用时，页面加载完【自动】把 WebView CookieManager 的 Cookie
  拷进 Legado CookieStore（对这类站无用但无害——AEGIS 不太看 Cookie）。
- **`loginCheckJs` = 每次响应后的拦截器**（WebBook 搜索/详情/目录/正文五处均经过），
  返回值 cast 成 StrResponse 直接用（`analyzeUrl.evalJS(checkJs, it) as StrResponse`）；
  因此可以在拦截器内【换掉整个响应体】。
- `StrResponse(url, body)` 构造器存在，Rhino 里 `new Packages.io.legado.app.help.http.StrResponse(u, src)` 可直接建 200 响应。

### 4.2 loginCheckJs 模板（生产可用）
```js
(function(){var r=result;var b='';try{b=String(r.body());}catch(e){}
var hit=b.indexOf('altcha-widget')>-1||b.indexOf('aegis_altcha')>-1;
if(!hit){return r;}
var u=String(r.url());var src=null;
try{src=java.webView(null,u,null);}catch(e){}
if(src!=null&&String(src).length>800&&String(src).indexOf('altcha-widget')<0){
  return new Packages.io.legado.app.help.http.StrResponse(u,String(src));
}
throw new Error('引导文案：请点登录面板过盾/浏览器访问一次后重试');})()
```

### 4.3 正文规则自带兜底（双保险）
某些流（如 debug 的 --URL 入口）或验证过期瞬间，正文规则拿到的可能仍是验证页。
正文规则里再自愈一次：`div.nr_nr` 解析失败且 body 疑似验证页（含 altcha-widget 或 <4000 字节）→ `java.webView(null, baseUrl, null)` 重取一次再解析。

### 4.4 登录面板（本站无账号体系，按用户需求提供状态检查+过盾+Toast 提示词）
- loginUi 三按钮：`✅ 检查访问状态` / `🛡 网页过盾` / `🌐 打开网站`；
- 检查/过盾逻辑均 = `java.webView(null, '首页URL', null)` 后按 body 特征判档：
  不含 altcha-widget 且 >3000 字节且含 "html" → 放行档；含 altcha-widget → 拦截档；其余 → 未知档，
  三档 Toast 文案写死（用户要求的"Toast 提示词"）。
- 若该 App 版本 loginUi 走 GSON 严格 JSON，按钮数组必须标准 JSON。

## 5 性能与风控纪律
- 每页代价 ≈ 1 次无谓 403(0.5s) + 1 次 WebView 渲染(1~2s)。正文章节约 2s/章，属站点反爬的"学费"。
- `concurrentRate` 设小值（如 2/1500）；提醒用户预下载章节数保持默认/调小。
- 目录分页用 **nextTocUrl 链式单页**（读到哪抓到哪），不要一次性拉全部页（并发 WebView 会打爆风控）。
- 验证凭据过期（本站 expiresAt 约 2 天）后自动重走 webView 过盾，无需用户干预。

## 6 顺带的 App 级坑（本次实锤，可迁移）
1. `ruleContent` 正文字段名是 **`content`**（ContentRule 源码字段, 不是 `text`！写成 text 被 GSON 静默丢弃 → debug "正文规则为空"）。
2. 列表 @js 规则在【整页 body】上执行一次、必须返回**全部条目数组**；返回单对象或 String → 列表大小 0。
3. 规则上下文 `result` 可能是 Java String：`typeof result==='string'` 为 **false**！
   一律用 `typeof el.select!=='function'` 判别元素，否则 `Packages.org.jsoup.Jsoup.parse(String(el))`。
4. 该站目录章节 `<a class="js-generated-link">` 由页面 JS 把 `.protected-chapter-link`(data-cid-url) 水合而来——只有 WebView 渲染后的 DOM 才有真实链接，进一步说明必须走浏览器通道。
5. 封面 `//host/...` 协议相对链接必须在 JS 里补 `https:`（Glide 不吃 //）。
6. searchUrl 分页形态 `/search/{N}?q=` vs 首页 `/search/?q=` 两个模板、用 `{{page>1?'/N':'/?'}}` 三元拼。
7. loginUi viewName 若要显示固定文案，写**单引号包裹的字符串字面量**（长于 19 字符走异步 eval，返回即文案）。

## 7 验证方法论
- 定性实验 1：沙盒/OkHttp/Cronet 三通道 403 对照 → 确认非 UA/IP 问题；
- 定性实验 2：`java.webView(null,url,null)` 探首页 → 拿 title/长度/altcha 特征定档；
- 定性实验 3：WebView 拿到的 Cookie 回灌 OkHttp 仍 403 → 证明凭据绑定请求指纹（别恋战）；
- 生产链路：save_source → get_source 字节级回读 → debug_source 搜索/详情/目录/正文/::发现 五入口 → check_source；
- 登录面板函数离线验证：`new Function('java', loginUrl+'return {...}')` + stub java 跑三按钮（看 Toast 分档）；
- 离线规则单测：eval_js 里 webView 取真实页 + `eval(rule.substring(4))` 模拟，比反复 debug 省一倍请求。

## 8 踩坑清单 K1~K8
- K1 看到 16 字节 keyPrefix 还去写 PoW 求解器 = 纯浪费（deny-by-design）。
- K2 拿 WebView Cookie 存 CookieStore 后就以为 OkHttp 能过 = 误判（按次判级,与 Cookie 无关）。
- K3 loginCheckJs 返回 null 而不是替换后的 StrResponse → 上层解析到验证页 → 静默 0 结果。
- K4 列表规则返回单对象 → getElements 空（列表大小 0），不是选择器问题。
- K5 `typeof` 判 Java String 失效 → 规则空手而归（本项目翻车点）。
- K6 ruleContent 用 "text" 字段名被静默丢弃（本项目翻车点）。
- K7 loginUi 用 JS 宽松语法（单引号/无引号键）→ GSON 站版本按钮全消失。
- K8 webView 页面未渲染完就取数据（SPA 水合延迟）→ 用 `window.__n` 轮询计数，等 anchor 数量达标再返回。

## 9 移植清单（遇到同族站改哪些就够）
1. loginCheckJs 的验证页特征串（altcha-widget → 目标站特征）；
2. 正文/详情/目录/搜索的 URL 与选择器（模板可能完全不同）；
3. searchUrl 分页三元与 exploreUrl 入口；
4. 登录面板文案与首页判活特征（'html' 长度阈值、站点标识串如 '69書'）；
5. concurrentRate 与"过盾指引"文案。