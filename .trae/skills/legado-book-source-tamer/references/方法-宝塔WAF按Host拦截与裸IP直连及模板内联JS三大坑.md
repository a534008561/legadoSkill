# 方法：宝塔 WAF 按 Host 拦截与裸 IP 直连、模板内联 JS 环境三大坑

> 蓝本：261108 修复 `http://www.ijjxs.org/`（久久小说 / 笔趣阁Bootstrap模板）书源。
> 环境：LegadoTeam(gedoor) 制作，需求兼容 legado-E(Luoyacheng)；MCP debug_source + LAN /saveBookSource 落库。
> 成品：`/workspace/ijjxs/ijjxs_fixed.json`（单对象）与 `ijjxs_fixed_array.json`（数组），13.9KB。

---

## 0. 三十秒速查

| 现象 | 一句话结论 |
|---|---|
| 域名访问返回「宝塔防火墙」图形验证码页，App/沙盒/第三方代理出口全一样 | WAF **按 Host 请求头拦截**，与出口 IP、UA、频率无关；首次访问即拦，不是被封 |
| 同一台服务器 `http://裸IP/` 返回真实页面 | **WAF 按域名 Host 生效，裸 IP 无 Host 规则 → 直接到源站**；把线路切成裸 IP 即免验证 |
| `Set-Cookie: server_session_xxx; ...; Secure` 但站点 443 连不上（只开 HTTP） | Secure Cookie 在 HTTP 下不会回传 ⇒ 过盾会话永远保存不住；`webView:true` 自动过盾对**图形码**无效（必须人工输入），别在验证码上浪费时间 |
| `{{IJ_search()}}` 返回值里写 `{{key}}` | **不会二次展开**：HTTP 日志实锤 POST body 字面 `searchkey={{key}}`；`replaceKeyPageJs` 只做一轮 innerRule 替换 |
| 在 `{{}}` 内联 JS 里调 `cookie.removeCookie(url)` 清限频 Cookie | **静默失效**：请求仍带 `Cookie:`；真机 `eval_js` 绑定源环境里同一句能清空 Cookie ⇒ 是环境绑定差异，不是 API 不存在 |
| 正确清 Cookie 位置 | **searchUrl 的 URL 选项 `js` 字段**（请求前置 JS 环境，绑定 CookieStore）：`"js":"try{cookie.removeCookie('http://线路/')}catch(e){}"` |
| 站点 200 + `<script>alert("搜索间隔: 30 秒")</script>` | **会话级配额**（`ss_search_delay` 键存在即拒，隔 2 分钟仍拒；清 Cookie 换新会话立即成功），与等待时间无关；不要连发探测频率 |

---

## 1. 宝塔 WAF「按 Host 拦截」的分层定性法（本次最大堵点）

### 1.1 症状
- `http://www.ijjxs.org/` 在 **App 出口、沙盒出口、allorigins 第三方代理出口** 全部返回 6314B「宝塔防火墙」页；
- 页面 JS：`/get_btwaf_captcha_base64?captcha=<ts>` 取 320×120 扭曲 PNG 图形码 → `/Verification_auth_btwaf?captcha=<用户输入>` 校验 → 成功后 `location.href=location.href` 重载；
- 换 UA（移动 Chrome / Baiduspider / Googlebot / PC Chrome / Legado）、换 `X-Forwarded-For`/`X-Real-IP`/`CF-Connecting-IP`、加 Referer 全部无效；
- `get_http_logs` 显示部分请求 403、部分 200，**只是 WAF 验证码页在两种 UA 下的不同布局（移动 6314B / PC 6216B），不是被封禁**。

### 1.2 定性实验（对照 + 反向验证）
| 组 | 请求 | 结果 | 结论 |
|---|---|---|---|
| 正向 | `http://www.ijjxs.org/`（Host=域名） | 200 验证码页 | 域名被拦 |
| 反向 | `http://177.5.49.192/`（Host=IP，**同一 A 记录**） | **200 真实首页 42120B**「笔趣阁_官方正版网站」 | ★WAF 只对域名 Host 生效 |
| 对照 | `http://177.5.49.192/` + `Host: www.ijjxs.org` 手工头 | 200 验证码页 | 坐实按 Host 而非 IP/链路 |
| 对照 | `https://www.ijjxs.org:443` | ConnectException（443 未开放） | Secure Cookie 与 HTTP-only 站点冲突 |
| 对照 | WAF 会话协议：无 Cookie 取码→故意填错码→再访问 | `{"status":false,"msg":"验证码错误"}`，仍回验证码页 | 图形码必须人工，delay/webView 自动过盾路线不适用 |

> 方法论：**看到「宝塔防火墙/人机校验」先做一次「裸 IP + 默认 Host」对照**；若真实页返回，直接把书源线路池设计为「域名 + 裸IP」双线路，默认裸 IP，域名留给面板切换/测速。不要先去逆验证码或换 UA。

### 1.3 落地配方
- `bookSourceUrl` 保持用户给的域名（主键不漂移）；
- `jsLib` 放 `IJ_base()` 读 `source.get('ijLine')`，默认 `http://177.5.49.192`；
- **所有入口 URL 必须带动态线路前缀**：`searchUrl` 用 `{{IJ_action()}}`（返回 `IJ_base()+form action`），`exploreUrl` 每条写 `{{IJ_base()}}/class/{{page}}/`。
  ★踩坑：发现页若写相对路径 `/class/{{page}}/`，Legado 会用 `bookSourceUrl` 的域名补全 → 又撞 WAF。
- 真实页面里的绝对路径（封面 `http://177.5.49.192/static/...`、章节 href）天然跟随线路，无需重写。

---

## 2. `{{}}` 内联 JS 的三个环境级坑

### 2.1 `{{key}}` 不会在 JS 返回值里二次展开
`searchUrl = "{{IJ_search()}}"` 且 JS 返回 `...body":"searchkey={{key}}"...` 时，HTTP 日志实锤：

```
POST http://177.5.49.192/search7e.html
searchkey={{key}}
→ 200 <title>{{key}}搜索结果_笔趣阁</title>  （0 本，服务端把模板串当关键词）
```

`AnalyzeUrl.replaceKeyPageJs` 只对**静态模板文本**做一轮 `{{}}` 求值，JS 求值结果不再递归展开。
★正解：`{{key}}` 必须留在**静态模板**里，动态部分只返回纯字符串：

```
searchUrl = {{IJ_action()}},{"method":"POST","body":"searchkey={{key}}","headers":{...},"js":"{{IJ_cookieJs()}}"}
```
- `{{IJ_action()}}`：返回纯 URL（动态取首页 `action='/search7e.html'`，防 action 后缀轮换）；
- `{{key}}`：Legado 在 body 里替换（实测 `searchkey=剑来` 正确发出）；
- `{{IJ_cookieJs()}}`：返回**纯 JS 代码串**给 `js` 选项。

> 注意：URL 选项 JSON 用**单大括号** `{...}`，不要写成 `{{...}}`（会被当模板求值）。

### 2.2 `{{}}` 内联 JS 环境根本不注入 `cookie` 绑定（★含一次自我误判的完整纠正）

**先把结论说准**：不是「API 失效」，也不是笼统的「环境差异/时机」，而是 **`AnalyzeUrl.evalJS`（`{{}}` 内联 JS 求值环境）没有 `cookie` 绑定**，调用直接抛 `ReferenceError: "cookie" 未定义。`，被 `try/catch` 吞掉后表现为静默失效。诊断办法 = 把 `typeof cookie` 与异常拼进返回的 URL 查询串（debug 日志会打印完整 URL）：

```
≡获取成功:.../search7e.html?diag=cookie%3Dundefined_removeERR_getAERR_callERR%3DReferenceError%3A%20%E2%80%9Ccookie%E2%80%9D%20%E6%9C%AA%E5%AE%9A%E4%B9%89%E3%80%82_getBERR,{"method":"POST",...}
```

| 组 | 操作 | 结果 |
|---|---|---|
| 误判组 | 手动 `clear_cookies` 后 debug 出 26 本 | 我一度宣称「js 选项自愈生效」——**错**：Cookie 本来就空，落库不会执行 js 选项，把时序当因果 |
| 反向验证组 | `set_cookie` 人为植入 `ss_search_delay=1` → 去掉 `js` 选项、把 `removeCookie` 放进 `{{}}` 内联 JS（移到 ajax 前后都试） | 0 本 + 限频页 + 日志 `Cookie: [redacted]` + `get_cookies` 仍带键 ⇒ 内联 JS 里没清掉 |
| 诊断组 | 内联 JS 里打印 typeof/异常 | `cookie=undefined` + `ReferenceError` ⇒ 坐实绑定缺失 |
| 修复组 | 恢复 URL 选项 `js`，**同一污染态、全程不手动清** | HTTP 日志请求头 `Cookie:` 整行消失（只剩 `CookieJar: 1`）、响应真实 26 本结果页（非 alert 限频页）⇒ **本次请求不携带旧会话键，服务端按新访客放行** |

★**精确语义**（别再夸大）：`js` 选项里的 `cookie.removeCookie(url)` 作用于**本次请求的会话 Cookie 栈**；`get_cookies` 事后仍显示 `ss_search_delay=1;...` 是因为那是 `set_cookie` 写入的**持久层**，且搜索响应又 `Set-Cookie` 重新下发。所以正确表述是「让本次搜索请求不带旧键」，不是「把设备持久层抹干净」。排查完必须 `clear_cookies` 清掉人为注入的脏数据，并**重存正式版**（诊断版会覆盖落库）。
★方法论：**「A 之后 B 成功」不等于「A 导致 B」**；凡涉及 Cookie/会话的结论，必须用「人为污染 + 不手动清 + 反向验证组」的干净对照，不能承接上一步手动操作留下的状态。

★正解（`jsLib` 生成代码串 → 塞进 `js` 选项）：
```js
function IJ_cookieJs(){
 return "try{cookie.removeCookie('"+IJ_base()+"/')}catch(e){}";
}
```
```
"js":"{{IJ_cookieJs()}}"
```
实测 debug 日志：
```
≡获取成功:...,"js":"try{cookie.removeCookie('http://177.5.49.192/')}catch(e){}"
└列表大小:26   （斗破苍穹，全链路 详情/目录641/正文2页 全绿）
```
★必须清**实际线路域**（裸 IP），不是 `source.getKey()`（www.ijjxs.org）——旧源 `cookie.removeCookie(source.getKey())` 的方向对，但换线路后清错域等于没清。

### 2.3 jsLib 里手写 JSON 字符串会触发 Rhino「字符串文字没有限制」
首版 `var hdrs='{"Content-Type":"...","Referer":"'+IJ_base()+'/"}';` 落库后 debug 直接：
```
EvaluatorException: 字符串文字没有限制 (<script-79>#19)
```
多层引号拼接在 JSON→App→Rhino 三道转义后必炸。★铁律：**URL 选项一律 `JSON.stringify({...})` 构造**，或干脆写静态模板，绝不手写带引号的 JSON 串。

---

## 3. 会话级搜索限频（不主动探测频率的破解法）

- 站点提示「搜索间隔: 30 秒」是**伪装**：隔 2 分钟再搜仍返回同一 alert 页；`get_cookies` 显示 `ss_search_delay=1` + `server_session_abb9659c=...`；
- `clear_cookies('http://177.5.49.192/')` 后**立即**搜索 → 48 本成功（反向验证组：不清 Cookie 等再久都没用）；
- 与 xsbook「每会话 1 次配额」、shoujixs「Cookie 键级限频」同型 ⇒ **唯一解 = 每次搜索前清线路域 Cookie 换新会话**；
- 用户要求「不要主动探测搜索访问频率，降低被风控风险」⇒ 全程**只做一次失败→查 HTTP 日志响应体→一次清 Cookie 对照→一次修复验证**，绝不连发多词/多时间间隔；
- `loginCheckJs` 只做**提示**（检测 `搜索间隔: 30 秒` / `宝塔防火墙` 给 Toast），不改写 StrResponse（避免 `as StrResponse` ClassCastException 风险）；
- 不设 `concurrentRate` 全局限速：书海阁教训（长目录被全局限速拖死），节流只做在搜索链路的会话自愈，目录/正文不受影响。

---

## 4. 站点改版导致的规则全量失效（旧源 7 个错）

| 字段 | 旧源（2025.7 夜明空） | 真实站点（2026.11 实测） |
|---|---|---|
| 搜索 | GET `/search/?searchkey=` | **POST `/search7e.html`**（form action 数字后缀，动态取），旧 GET 404 |
| 搜索列表 | `.item` / `dt` / `dd` / `img@data-original` | `#bookcon tr:gt(0)` 表格，`td.1@a@text` / `td.2@a@text` / `td.1@a@href` |
| 详情 | `og:novel:*` meta | **无 og meta**：`.info2 h1` / `.info2 h3 a` / `.info1 img` / `.info3 p.0` / `.info3 p.2 a` |
| 目录 | `dl > dt:contains(最新章节) ~ a:not(...)`（**技能明令禁止 `:contains()`**） | 详情页 `ul.list-charts` 三段：最新9 / **全部章节276** / 推荐6 ⇒ `@js` 选「a 最多」的 ul + 数字章节 href 过滤，返回 `java.util.ArrayList` + 逐条 `JSON.stringify({n,u})`，字段 `$.n`/`$.u`（LT/E 双版本定式） |
| 正文 | `#booktxt@html` + `text.下一页@href` | `.content-body@p@html` + `#next_url@href`（`_2.html` 章内分页，实测 2 页拼接） |
| 发现 | `ruleExplore: {}` **空对象**（发现必然 0） | `.media`（分类/全本25本）`||` `#bookcon tr:gt(0)`（排行50本）双模板合并 |
| 其他 | 无 UA / 无 `bookUrlPattern` / 每次 `removeCookie(source.getKey())` 清错域 | `header` 移动 Chrome UA、`bookUrlPattern` 同时匹配域名+裸IP、清线路域 Cookie |

---

## 5. 登录面板（V1 静态，E 版兼容）与发布页判定

- 站点 `/login/`、`/bookcase/` 存在，但**搜索/详情/目录/正文实测全不需要账号**（`user.js` 里 `ss_username` 只影响书架按钮）⇒ 按用户「可不写登录UI」不写账号表单；
- 用户要求「如须登录需写检查登录状态按钮」：虽不须登录，仍写了 `🔍 检查登录状态` 按钮（同时检查线路连通性 + 是否登录 + WAF 状态），各阶段 Toast ①②③ 齐全；
- **发布页判定**：目标站真实页面无「发布页/备用网址/防走失」；同族 `ijjxsxzw.com` 的「最新上传备用网址 jjjjxsw.com」是 TXT 下载站的备用域，不是本在线阅读站的线路发布页 ⇒ 按「如有」条件**不强行造发布页池**，但保留面板完整运维件：发布页输入框 + 应用 + 🧭一键获取路线（解析 http(s) URL + 内置域名/裸IP兜底）+ ⏱测速（`ajaxAll(urls,true)` 并发，`callTime()` 写 ms 到 `ijDelayN`，`viewName` 动态按钮文字显示）+ 6 个线路按钮（点击切换 `ijLine`，下一次请求即时生效）+ 🌐打开线路；
- `viewName` 动态文本函数 `IJ_btn(source,n)` 在 V1 静态面板的 `evalUiJs` 环境里 `source` 可用（实测编译 + 单测：`━━ 线路1 未获取 ━━` 正常返回）；`loginUrl` 必须含 `function login(){return 'ok';}`；
- 面板 JS 用 `new Function(loginUrl+...)` 在 App Rhino 内编译验证：16 个函数全部定义、每个 button action 引用的函数零缺失、①×4 ②×5 ③×2 Toast 阶段覆盖。

---

## 6. 交付前验证清单（MCP 实测，非模拟）

1. `debug_source(key='剑来')`（清 Cookie 对照后）→ 搜索 48 → 详情 → 目录 276 → 正文 2 页全绿；
2. `debug_source(key='::http://177.5.49.192/class/1/')` → 发现 25 → 详情 → 目录 468 → 正文 2 页全绿；
3. `debug_source(key='斗破苍穹')`（前置 `js` 自愈生效，未手动清）→ 搜索 26 → 目录 641 → 正文 2 页全绿；
4. `check_source` → 通过 1/1；
5. `get_source` 回读逐字段核对（LAN `/saveBookSource` 单对象直传 13.9KB 无损，`lastUpdateTime=0` 属 LAN 通道特性，功能不受影响）；
6. 静态审查 19 项：URL 正则（`https?://(?:www\.)?ijjxs\.org/\d+_\d+/?|https?://177\.5\.49\.192/\d+_\d+/?` 实测书籍 URL 匹配、首页/外站排除）、无 `:contains()` / `:first-child`、有 `nextContentUrl` 无 `prevContentUrl`、发现不写死页码上限、E 版 `ArrayList` 定式、`loginCheckJs` 原样 `return result`。

---

## 7. 复用清单（下次遇到同类站照做）

```
宝塔验证码页 → 裸IP+默认Host 对照 → 双线路池(域名/裸IP)，默认裸IP
所有入口 URL 加 {{IJ_base()}} 前缀（相对路径会回退到 bookSourceUrl 域名撞WAF）
搜索 form action 动态取：{{IJ_action()}} 返回纯 URL
{{key}} 留在静态 body 模板，绝不塞进 {{}} JS 返回值
会话级限频 → URL 选项 js 里 cookie.removeCookie(实际线路域)，不在 {{}} 内联 JS 里清
目录多段 ul → @js 选 a 最多的段 + 数字章节过滤 + java.util.ArrayList/JSON.stringify
面板 V1 静态 + viewName 动态 ms + login() 空实现 + 各阶段 Toast
不主动探测频率：失败一次→查 HTTP 日志响应体→一次对照→一次修复验证
```

---

## 8. ★★ 追加堵点：登录面板「换路线失败」——jsLib 闭包冻结 + 三环境键空间差异（261108 二次修复）

用户报障「换路线失败」。不靠猜，先在 App 内读状态，再逐层做对照实验，最终实锤 **两个独立根因**。

### 8.1 症状与初判
- 面板按钮 `IJ_switch(java,n)` 执行后，`source.get('ijLine')`/`java.get('ijLine')` 都显示新值（写入成功，函数编译与调用无异常）；
- 但 `IJ_base()`（jsLib 函数）仍返回旧值 `http://177.5.49.192`，搜索/发现 URL 不跟随切换。
- ★**先排除「按钮没触发」**：变量确实被写了，问题在「读侧」。

### 8.2 根因 A：jsLib 函数编译期捕获 `source` 快照，写入后不刷新
| 实验 | 结果 |
|---|---|
| 同一次 eval_js 里 `source.put('ijLine',域名)` → 立即 `source.get` | 域名（实时） |
| 同一次里调 `IJ_base()` | **仍裸IP**（冻结） |
| 跨 eval_js 调用再读 `source.get` / `IJ_base()` | `source.get`=域名、`IJ_base()`=裸IP |
| `new Function(source.getJsLib()+'\nreturn IJ_base();')()` **重新编译同一份文本** | 域名（实时） |
| `new Function('return String(java.get("ijLine"))')()` | 域名（实时） |

⇒ 结论：**jsLib 的函数在书源会话初始化时编译进共享作用域，其闭包捕获的是那一刻的变量视图；`source.put/java.put` 写持久层实时可见，但已编译函数不会重新加载**。任何「面板写变量 → jsLib 函数读变量」的线路切换架构都会冻结。

### 8.3 根因 B：`{{}}` 内联 JS 与 eval_js 的键空间不同（我改错方向的一次）
按 A 我先把入口改成 `{{}}` 内联 IIFE 里 `java.get('ijLine')`（因为 eval_js 里 `java.get`/`source.get` 互通），结果切换后 URL **仍裸 IP**。用「把诊断值拼进 URL」的探针实锤：

```
::.../rank/allvisit/?probe={{...}}  →  ≡获取成功:...?probe=jg%3D%3Bsg%3Dhttp%3A%2F%2Fwww.ijjxs.org%3Bt%3Dfunction
```
即 **`jg=`（java.get 空）**、**`sg=http://www.ijjxs.org`（source.get 实时）**。把 `ijLine` 切回裸IP再探针，`sg` 跟着变 ⇒ 内联环境 `source.get` 是实时的。

★**三环境绑定表（本次三环境差异的补全，修正 /topics/legado-js-scope-binding.md 的粗粒度结论）**：

| 环境 | `source.get` | `java.get` | `cookie` | 备注 |
|---|---|---|---|---|
| `{{}}` 内联 JS（`AnalyzeUrl.evalJS`） | **实时可用** | 恒空 | **未注入**（调 `removeCookie` 抛 ReferenceError） | 入口 URL 动态线路必须放这里、用 `source.get` |
| URL 选项 `js`（请求前置 JS） | — | — | **可用**（绑定 CookieStore） | 清会话 Cookie 唯一正确位置 |
| `eval_js` MCP / 规则 `@js` 全量绑定 | 实时 | 实时互通 | 可用 | 三者互通，不能用它给内联环境下结论 |
| **jsLib 已编译函数** | **冻结快照** | 冻结 | — | 禁止在其中读「面板可写」的动态变量 |

### 8.4 正解配方
```
面板 action: source.put('ijLine', v)                     // 写（同一键空间）
入口 URL:    {{(function(){var L='';try{L=String(source.get('ijLine')||'')}catch(e){}
              if(!L||...)L='默认裸IP';return L.replace(/\/+$/,'')})()}}/class/{{page}}/
searchUrl:   {{(function(){...source.get...;java.ajax(L+'/')抓form action...})()}},{...选项...,"js":{{...source.get...生成removeCookie代码...}}}
jsLib:       只放不依赖动态变量的纯函数，或干脆不用
```
★ 动态线路**不要经过 jsLib 函数**；`{{}}` 内联 IIFE 里 `source.get` 每次请求重新求值，天然绕开闭包冻结。

### 8.5 双向验证（必须含反向组）
| 组 | `ijLine` | debug 日志 URL / Referer / js 域 | 结果 |
|---|---|---|---|
| 反向 | `http://www.ijjxs.org` | 全部变成域名 | 0 本（撞宝塔WAF验证码页，符合预期）⇒ 证明**切换真的生效**，不是仍走默认裸IP |
| 正向 | `http://177.5.49.192` | 全部变回裸IP | 48 本 → 详情 → 目录276 → 正文2页 全绿 |

★方法论：用户报「切换失败」时，**先确认变量写入成功，再区分「读侧冻结」与「环境键空间」**；切到「必定失败」的线路（域名撞WAF）是比切到「本来就能用」的默认线路更强的反向验证组。

---

## 9. ★ 261108 三次修复：触发宝塔人机验证时「弹验证码 → 用户填 → 返回继续搜索」

用户需求：切到被 WAF 拦的域名线路时，不要只 Toast，要**弹出验证码让用户填，过盾后自动继续本次请求**。

### 9.1 图片没显示的根因（先排掉自己的锅）
首版探针用 **1px 透明 PNG** 的 `data:` URI 调 `java.getVerificationCode`，弹窗一片空白 ⇒ 用户报「验证图片加载失败或没显示」。
★源码实锤（GitHub Contents API 拉 `master` 原始文件）：
- `JsExtensions.getVerificationCode(imageUrl: String): String` → `SourceVerificationHelp.getVerificationResult(getSource(), imageUrl, "", false, …)`；
- `waitForVerification()` 里 `putExtra("imageUrl", url)` **原样**传给 `VerificationCodeActivity/Dialog`；
- `ImageLoader.loadBitmap(context, path, sourceOrigin)` 的 when 分支含 **`path.isDataUrl() -> requestManager.load(path)`** ⇒ `data:image/png;base64,<真图>` 直接由 Glide 加载，无需落盘/无需图床；
- `require(url.length < 64*1024)`：站点验证码 base64 约 13-16KB，安全。

★**用站点真图**（`/get_btwaf_captcha_base64?captcha=<ts>` 返回 `{"status":true,"msg":"iVBORw0KGgo..."}`，320×120 PNG）弹窗真机实测：**用户输入 `kxjq` 后函数正常返回**（29s），弹窗/图片/输入框全工作。铁律：**测试弹窗必须用真图，1px 透明图只会显示空白**。

### 9.2 `loginCheckJs` 环境能力（临时探针落库 + debug 读 `source.put` 实锤）
```
result=object | body=6084 | url=http://www.ijjxs.org/search7e.html | code=200
method=POST | reqUrl=... | reqBody=okhttp3.RequestBody... | buffered=searchkey=剑来
key=string=剑来 | page=number | java.ajax=function | java.getVerificationCode=function | cookie=object
```
⇒ 能拿：原响应、`result.raw().request()` 的 method/url/headers/body（`new Packages.okio.Buffer()` + `rb.writeTo(B)` 读回 POST body）、搜索词 `key`、弹窗 API、CookieStore。
★`loginCheckJs` 必须返回 `StrResponse`；`new Packages.io.legado.app.help.http.StrResponse(url, body)` 两参构造可用（实测 `body()/url()/code()` 正常、能被 jsoup 解析），因此**可以返回「重放后的新响应对象」让上游规则继续解析**，而不是只回原 `result`。

### 9.3 完整链路（放进 `loginCheckJs`，搜索/详情/目录/正文通用）
1. `String(result.body())` 含 `宝塔防火墙|Verification_auth_btwaf|请输入验证码` → 判定 WAF 页；
2. `root = result.url()` 抠 `^(https?://[^/]+)`；
3. `java.ajax(root+'/get_btwaf_captcha_base64?captcha='+Date.now())` → `JSON.parse().msg` 取 base64 PNG，校验 `iVBOR` 前缀；
4. `java.getVerificationCode('data:image/png;base64,'+cap)` **弹真图等用户填**，空串=取消则终止；
5. `java.ajax(root+'/Verification_auth_btwaf?captcha='+encodeURIComponent(code))`，`JSON.parse().status===true` 判成功（错误返回 `{"status":false,"msg":"验证码错误"}`）；
6. 从 `result.raw().request()` 取 method/url/headers/body，**原样重放**（`java.ajax(reqUrl+','+JSON.stringify({method,headers,body}))`）；
7. 重放仍是验证页 → Toast「浏览器过盾或切裸IP」并回原响应；成功 → `new StrResponse(reqUrl, replay)` 返回，上游继续解析。
8. 各阶段 Toast：①取图 ②收码提交 ③通过继续 / ✗取图失败、✗弹窗失败、✗取消、✗码错、✗重放失败、⚠票未生效、✗重建失败。

★协议验证（低频一次）：取图 → `cookie.getCookie(root)` 含 `server_session_...` → 提交错码 → 返回「验证码错误」（不是「无法获取验证码」）⇒ **Cookie 会话连续，填对码即可过盾**；且 `enabledCookieJar=true` 下 `java.ajax` 自动携带/写回会话 Cookie。
★注意：域名线路 443 未开 + `Set-Cookie: ...; Secure`，HTTP 下浏览器/WebView 过盾票不落地；但 **App 的 CookieStore 在本次会话内可连续**（本次协议验证实锤），所以弹码链路可用；若服务端仍不发真实页，按 7 的降级提示让用户切裸IP。

### 9.4 方法论
- 用户报「弹窗没图」先检查**自己传的图是不是真图**，再查 `ImageLoader` 分支；
- 「过盾后继续」不要试图改 `result`（不可变），而是**返回新的 StrResponse 对象**；
- 重放 POST 必须读回原 body（`okio.Buffer`），否则搜索词丢失；
- `loginCheckJs` 里 `java.ajax` 返回**字符串**（不是 StrResponse），直接拿它当新响应 body 即可。

---

## 10. ★★★ 261108 四次修复「填验证码后没继续搜索」：同一 A 记录按 Host 分发两套完全不同的站

### 10.1 现象（HTTP 日志逐条实锤，不是猜）
```
#333 POST www.ijjxs.org/search7e.html      -> 200 宝塔WAF验证码页
#334 GET  .../get_btwaf_captcha_base64     -> 200 真图 base64
#335 GET  .../Verification_auth_btwaf?captcha=syto -> 200 {"status":true,"msg":"验证成功"}
#336 POST www.ijjxs.org/search7e.html      -> 404 Tengine 标准404「URL: .../search7e.html」
```
用户填码是**对的**、验证**成功了**（不再返回 WAF 页），但重放 `/search7e.html` 得到 404 ⇒ 搜索没继续。三轮（cxzm/iqmv/syto）全部同样 404。

### 10.2 根因：Host 分发两套站（本次最大认知修正）
`#332`（过盾后 GET `http://www.ijjxs.org/`）返回的是**完全不同的另一套模板**：

| | 域名 `www.ijjxs.org`（过盾后） | 裸IP `177.5.49.192`（默认Host） |
|---|---|---|
| 站名/标题 | 「久久小说网-好看的小说-免费小说阅读网」 | 「笔趣阁_官方正版网站,无弹窗小说阅读」 |
| CSS | `/static/ijjxs/style.css` | Bootstrap `/web/css/bootstrap.min.css` |
| 搜索 | **GET `/search/?searchkey=`** | **POST `/search7e.html`**（form action 数字后缀） |
| 搜索列表 | `.item` 卡片（dt/dd/.btm/img@data-original） | `#bookcon tr` 表格 |
| 详情 | `og:novel:*` meta | `.info2/.info3` |
| 目录 | `dl` 内 a | `ul.list-charts` |
| 正文 | `#booktxt@html` + `text.下一页` | `.content-body@p@html` + `#next_url` |
| 旧源对应 | ✅ 正是「久久小说-夜明空」那套规则 | ❌ 旧源规则全失效 |

★ **同一个 IP `177.5.49.192`，按 HTTP Host 头分发两套完全不同的站点模板**。之前我把裸 IP 抓到的「笔趣阁」规则当成全站规则，域名过盾后重放 `/search7e.html` 必然 404。
★ 过盾票是**短时/IP 会话**：验证后隔几分钟再请求域名又回 WAF 页（Cookie 带 Secure + 443 未开导致不持久化），所以**必须在 `loginCheckJs` 里验证成功后立刻重放**，那个窗口有效（#336/#354 都证明票当时生效）。

### 10.3 修法
1. `loginCheckJs` 重放按 Host 分派：`root.indexOf('ijjxs.org')>=0` → `GET root+'/search/?searchkey='+encodeURIComponent(kw)`（kw 从 `key` 绑定或原 POST body 的 `searchkey=` 取）；裸IP侧仍原样 POST；
2. **不再把 `req.headers()` 全量回填**到 `opt.headers`（#336 日志里出现重复 `Connection/Keep-Alive/Cache-Control` 与多余 `Cookie` 头），只带 method/body；
3. 重放结果判据增加 `404 Not Found` → 明确 Toast「过盾成功但重放地址不存在」；
4. **规则全量双模板兼容**：`ruleSearch/ruleExplore` 用 `.item||.media||#bookcon tr:gt(0)` 三支、详情 og meta 兜底、正文 `.content-body||#booktxt`、目录 `@js` 里 `ul.list-charts` 为空时回退 `dl`；
5. 属性选择器 `[class="blue visible-xs"]` 在 Legado Default 规则里会被当**数组索引语法**（书海阁教训），改纯 class 写法 `class.blue.visible-xs@text`。

### 10.4 最终真机验证（含用户填码）
```
#349 POST 域名/search7e.html -> WAF页
#350 GET  取码 -> 200
#353 GET  Verification_auth_btwaf?captcha=www8 -> 200 {"status":true,"msg":"验证成功"}
#354 GET  域名/search/?searchkey=剑来 -> 200 真实搜索结果(48本)
#355 GET  域名/222_222965/ -> 200 详情
#356 GET  域名/222_222965/3247210.html -> 200 正文
#357 GET  ..._2.html -> 200 正文第2页
```
debug_source 输出：搜索 48 本 → 详情（作者/分类/最新章节/简介全出）→ 目录 277 章 → 正文 2 页拼接，全链路继续完成。裸IP侧回归也全绿（26本/641章/2页），双模板规则未破坏原链路。

### 10.5 方法论
- 「验证成功但没继续」**先查 HTTP 日志的重放状态码**：200 WAF页=票没生效；404=接口/模板不对；
- 同一 IP 多 Host 分发多套模板时，**过盾后的真实首页要逐字读**（#332 的 `<form action>` 就是分派证据），不要把另一条 Host 的规则套过来；
- 一个书源要兼容两套模板时，规则用 `||` 多支 + `@js` 兜底，且**先做裸IP侧回归**确保老链路不坏；
- 用户填码验证是稀缺操作：**一次填码要同时验证「票生效」与「重放接口正确」**，别浪费在探针上。

---

## 11. ★ 261108 五次修复「目录排序错误：最新章节显示在前面」

### 11.1 两套模板的目录段结构（App jsoup 逐元素实锤）
| | 裸IP「笔趣阁」 | 域名「久久小说网」 |
|---|---|---|
| 容器 | 3 个 `ul.list-charts` | **1 个 `dl`**（`#list`） |
| 段 | `[0]` 最新9条**倒序** / `[1]` 全部277条正序 / `[2]` 推荐6 | `dt[0]`「…最新章节」→ 9条倒序 / `dt[1]`「…全部章节目录（共277章）」→ 277条正序（其中 `dt[2]`「点击展开更多章节」把后段 `a.hc` 分段，仍正序）/ **末尾又重复最新9条** |
| 我原规则 | 选 a 最多的 ul → 正确 | 兜底 `doc.select('dl')` **全收 289 个 a** ⇒ 最新章节置顶 + 尾部重复 |

### 11.2 修法（`@js` 双分支）
- **裸IP侧**：仍选「`a[href*=.html]` 最多」的 `ul.list-charts`；
- **域名侧**：从 `dt` 文本含 **「全部章节目录」** 的锚点之后，遍历 `dl.children()` 收所有匹配 `/\/\d+_\d+\/\d+\.html/` 的 a（含 `dt[2]` 之后的 `a.hc` 段，顺序仍正序）；
- **统一按 href 去重（保先出现）**：域名侧末尾重复的最新9条因此被丢弃；裸IP侧各段互不重叠不受影响；
- 返回 `java.util.ArrayList` + 逐条 `JSON.stringify({n,u})`（LT/E 双版本定式不变）。

### 11.3 验证（单测 + 双真机 debug）
- App 内 jsoup 单测：域名 `total=277 first=第1章… last=第277章… 含最新277章在前?=false`；裸IP 同样 277 正序；
- `debug_source(域名详情页 URL)`：列表 277、首章「第1章 浩然天下第一大剑仙」、正文第1章 2页拼接；
- `debug_source(裸IP详情页 URL)`：列表 277、首章「第1章」、正文 2 页；老链路未破坏。

★方法论：目录「最新章节置顶」不要试图 `reverse()` 或按章号排序（站点章节号可能跳号/分卷），**按页面自身的「全部章节目录」锚点切段 + href 去重**最稳；与 xsbook「最新段倒序重复、保后去重」是同一类病的不同形态（那里用保后、这里用保先，取决于正序段在前还是在后，必须先看真实 DOM 顺序再定）。
