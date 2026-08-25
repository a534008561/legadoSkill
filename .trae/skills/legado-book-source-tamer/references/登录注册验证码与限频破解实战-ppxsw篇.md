---
name: "legado-auth-source-master"
description: |
  Legado 阅读 APP 书源「登录·注册·验证码·反爬」高阶实战技能（基于 lyc 修改版 App + ppxsw.cc / wanbenshenzhan.com 真实战例沉淀）。

  适用场景：
  - 为需要登录的书源制作登录 UI（账号/密码/验证码/按钮）
  - 处理图形验证码（弹窗方案选型、内置浏览器看图方案、会话绑定问题）
  - 分析站点登录/注册接口与密码加密算法（JS 逆向）
  - 破解搜索限频（search_time 类 Cookie 校验）
  - 排查"手动验证通过但 App 内失效"类诡异问题（UA 双模板）
  - 正文 base64 反爬解码（动态对象名）、目录乱序修复、分页泛化匹配
  - 使用 MCP 工具链（debug_source / eval_js / get_http_log）调试书源

  触发关键词：登录UI、验证码、注册、限频、search_time、setCookie、putLoginHeader、getVerificationCode、startBrowser、乱序、双模板、tocUrl、base64解码
---

> 📌 本文档为 [方法-登录注册验证码与限频破解](./方法-登录注册验证码与限频破解.md) 的**深度补充**：完整推导过程、对照实验数据、逐坑分析。快速上手请先读主干。

# Legado 书源认证与反爬大师（V1.2）

> 实战来源：ppxsw.cc（皮皮小说，登录+MD5+验证码+限频+base64+双模板全要素）
> 与 wanbenshenzhan.com（完本神站，成熟登录范式参照）
> App 环境：Legado 阅读 3.0 lyc 修改版（与官方版存在大量行为差异）

---

## 0. 核心结论速查表（30秒版）

| 问题 | 一句话结论 |
|---|---|
| 验证码怎么弹？ | **别指望对话框内弹窗**。loginUi 加"验证码"text 框 + "刷新验证码"button(action=`refreshCaptcha()`)，函数内 `java.startBrowser(codeImgUrl,'验证码')` 开内置浏览器看图，用户返回后手填 |
| `java.getVerification` | 官方 API，**lyc 版不存在** |
| `java.getVerificationCode` | lyc 版存在，但**仅在独立 eval_js 环境可弹窗**；loginUrl/loginUi 对话框上下文调用不弹窗（静默返回空）|
| 改单个 Cookie 键 | `cookie.setCookie(url,str)` 是**整体替换**！必须 `getCookie全文 → 正则删/改键 → setCookie回写全文` |
| 搜索限频 | 先做对照实验判断服务端校验依据。ppxsw 案例：**只查请求是否携带 search_time Cookie**，删掉即无限搜，干等/重试反而重置倒计时 |
| tocUrl 写在哪 | **ruleBookInfo 内**！（ruleToc 无此字段，写了会被静默丢弃）|
| tocUrl 能用 `\|\|` 兜底吗 | **不能**，整串会被当 URL 发出去 |
| 手动验证 OK 但 App 失效 | 高度怀疑 **UA 双模板**：分类页/目录页按 UA 返回移动/PC 两套 DOM。用 `get_http_log` 看 App 实际收到的响应体再写规则 |
| 目录乱序 | 阅读按出现顺序去重**不排序**。"最新章节倒序区"排在列表最前就会乱序 → 用 li 的 class 特征（如 br-b-1）过滤正序区 |
| loginCheckJs 返回什么 | result 是 StrResponse，**必须原样 return result**；返回 Boolean 会 ClassCastException |
| 注册接口怎么接 | 参数名与登录**不同**(`name/pass/pass2/mobile/code`)；复用 loginUi 加手机框+注册按钮，结果 toast 原文 |

---

## 1. 登录接口分析三步法

### 第一步：找表单与提交端点
抓登录页 HTML，定位 `<form>` 与提交按钮绑定的 JS 函数：

```html
<form id="novel_search" method="post" action="/search.html">...</form>
<button onclick="login('')">确认登录</button>
<script src="/yanqing/m/js/common_xxx.js"></script>
```

### 第二步：下载提交 JS 找真实请求
在 common.js 中提取 login 函数，得到端点/参数名/响应格式：

```js
function login(lg_url){
    user_pass = qsskel(document.getElementById("user_pass").value); // ← 密码被加密!
    jq.post('/qs_login_go.php', {user_name, user_pass, user_code}, function(data){
        data.split("|")[0] == "1"  // ← '1|xxx' 表示成功
    })
}
```

要点：
- 记录**成功判定标记**（如 `1|`前缀）与**错误消息格式**（如 `0|验证码错误`）
- 用"故意填错验证码"探测法确认服务端各校验环节的先后与文案

### 第三步：逆向加密函数
把站点 JS 加密函数整体抠出来放进 QuickJS/Rhino 跑一遍，与标准算法比对：

```python
# python 对照
hashlib.md5("a7894563".encode()).hexdigest()
# = fd26f013d2c05c33c6ab53e654b8bf97
```
```js
// eval_js 里实跑站点函数
qsskel("a7894563") === "fd26f013d2c05c33c6ab53e654b8bf97" // true → 就是标准 MD5 hex 小写
```
若一致，书源里直接用 Legado 内置 `java.md5Encode(pwd)`，无需内联整段 JS。

> 经典识别特征：`function xxx(o){... E(w(V,W),U) ... return (G(T)+G(S)+G(R)+G(Q)).toLowerCase()}` 结构 = Paul Johnston 风 JS-MD5。

---

## 2. lyc 版登录 UI 黄金模式（完本神站范式）

### 结构总览
```json
"loginUrl": "function getHost(){return 'https://site.example';}\n\nfunction refreshCaptcha(){\n  var url=getHost()+'/code.jpg?'+Math.random();\n  java.startBrowser(url,'验证码');\n}\n\nfunction login(b){\n  if(b==undefined) return true;          // 打开UI时的预执行守卫\n  var info=result;                        // ★ result 就是 UI 键值 map\n  var user=info['账号'], pass=info['密码'], code=info['验证码'];\n  if(!user||!pass||!code){java.toast('请完整填写');return;}\n  var body='user_name='+encodeURIComponent(user)\n          +'&user_pass='+java.md5Encode(pass)\n          +'&user_code='+encodeURIComponent(code);\n  var post=JSON.stringify({method:'POST',body:body,headers:{\n      'Content-Type':'application/x-www-form-urlencoded',\n      'Referer':'https://site.example/login.html',\n      'X-Requested-With':'XMLHttpRequest'}});\n  var resp=String(java.ajax(getHost()+'/qs_login_go.php,'+post));\n  if(resp.indexOf('1|')>=0){\n      var ck=java.getCookie(getHost());\n      if(ck) source.putLoginHeader(ck);   // 登录头持久化(第二重保险)\n      java.toast('登录成功');\n  }else{\n      java.toast('登录失败:'+resp);\n      refreshCaptcha();                    // 失败自动换一张码\n  }\n}\n\nfunction logout(){\n  source.removeLoginHeader();\n  cookie.removeCookie(getHost());\n  result['账号']='';result['密码']='';result['验证码']='';\n  source.putLoginInfo(JSON.stringify(result));\n  java.toast('已登出');\n}",
"loginUi": "[{\"name\":\"账号\",\"type\":\"text\"},{\"name\":\"密码\",\"type\":\"password\"},{\"name\":\"验证码\",\"type\":\"text\"},{\"name\":\"刷新验证码\",\"type\":\"button\",\"action\":\"refreshCaptcha()\"},{\"name\":\"登 录\",\"type\":\"button\",\"action\":\"login(true)\",\"style\":{\"layout_flexGrow\":1,\"layout_flexBasisPercent\":0.5}},{\"name\":\"登 出\",\"type\":\"button\",\"action\":\"logout()\",\"style\":{\"layout_flexGrow\":1,\"layout_flexBasisPercent\":0.5}}]"
```

### 五个铁律
1. `loginUrl` 是**顶层具名函数集合**，不加 `@js:` 前缀；按钮 action 直接写函数调用名（`refreshCaptcha()` / `login(true)`），不要塞 IIFE 大段代码（对话框上下文里易炸且难排错）
2. `login(b)` 内 `result` 就是 UI 输入的键值 map（等价 `source.getLoginInfoMap()`，但更直接）
3. `if(b==undefined) return true;` 守卫必须有（App 打开登录界面时会无参预执行一次）
4. AJAX 提交记得带 `X-Requested-With: XMLHttpRequest` 与正确 Referer，部分站校验
5. 成功后 `source.putLoginHeader(java.getCookie(host))` —— 即使 CookieJar 会话丢失，登录头仍可兜底

### 验证码三种方案选型树

```
需要验证码？
├─ 你的环境是官方版 Legado？
│   └─ 是 → java.getVerification(imgUrl)  // 弹图+输入框一体
├─ lyc 修改版 + 独立 eval_js/调试环境？
│   └─ java.getVerificationCode(imgUrl)   // 存在且能弹（实测17s交互成功）
└─ lyc 修改版 + loginUrl/loginUi 对话框上下文？
    └── ★ 黄金方案：java.startBrowser(imgUrl,'验证码')
        内置浏览器看图 + loginUi 验证码 text 框手填
        (getVerificationCode 在对话框上下文调用不弹窗、静默返 null)
```

> 判定技巧：怀疑某 API 不存在/不可用时，先在 eval_js 里 `typeof java.xxx` 探测，再用 try-catch 实调一次看返回。注意 eval_js 可弹窗 ≠ 登录对话框内可弹窗——**上下文决定一切**。

### 注册流程实战（qs_register_go.php）

ppxsw 的注册与登录是**两套参数名体系**，且注册多一个"手机号"字段。实战源直接复用同一个 loginUi 承载（加一个 text 框 + 一个按钮），无需另开界面：

| | 登录 `/qs_login_go.php` | 注册 `/qs_register_go.php` |
|---|---|---|
| 账号 | `user_name` | `name` |
| 密码 | `user_pass`（MD5 小写） | `pass` **和** `pass2`（两次均 MD5） |
| 验证码 | `user_code` | `code` |
| 手机号 | 无 | `mobile` |
| 成功判定 | `1\|` 前缀 | 文案不固定 → **toast 原文**让用户自行判断 |

可拷模板：

```js
function zc() {                                   // 注册按钮 action 直接写 zc()
    cookie.removeCookie(source.key);              // ① 先重置会话再取码,保证图与会话同源
    res = source.getLoginInfoMap();               // ② 取 UI 值的另一风格(返回 Java Map)
    use = res.get("帐号"); pwd = res.get("密码"); sj = res.get("手机");
    code = java.getVerificationCode(getHost()+'/code.jpg?'+Math.random()); // 或改 startBrowser 黄金方案
    body = `name=${use}&mobile=${sj}&pass=${java.md5Encode(pwd)}&pass2=${java.md5Encode(pwd)}&code=${code}`;
    html = String(java.ajax(getHost()+'/qs_register_go.php,'+JSON.stringify({
        method:'POST', body:body,
        headers:{'Content-Type':'application/x-www-form-urlencoded',
                 'X-Requested-With':'XMLHttpRequest','Referer':getHost()+'/'}
    })));
    java.longToast(html);                         // ③ 结果文案各异,toast 原文最稳
    Packages.java.lang.Thread.sleep(3000);        // 给 toast 留展示时间;此 App 无 java.sleep!
}
```

注册特有注意事项：
- **UI 取值双风格**：`login(b)` 里 `result` 直接就是 UI 键值 map；按钮 action 函数里也可用 `source.getLoginInfoMap()`（Java Map，用 `.get(key)` 取）。二者等价可任选，但**同一函数内别混用**。
- 注册成功后**不必** `putLoginHeader`——站点通常不自动登录，提示用户"用刚注册的账号走一次登录"即可。
- `pass2` 漏传或与 `pass` 不一致时部分站只回"非法访问"；建议先用浏览器手动注册一遍，记录各错误分支的正常响应文案做基准。
- 延迟只能用 `Packages.java.lang.Thread.sleep(ms)`——此 App **没有 java.sleep**，写了直接炸整个函数。
- 完整双函数参考实现见 examples/`皮皮小说网ppxsw_注册版参考.json`。

> ⚠️ 该参考源在按钮 action 中直接调 `java.getVerificationCode(...)`。按本环境实测（上文方案树），lyc 版对话框上下文中该 API **不弹窗**；若运行时点按钮无反应即踩中此坑，改用 `java.startBrowser` 黄金方案即可。保留此源的价值在于**注册接口的参数体系样本**。

---

## 3. 验证码会话绑定原理（为什么你填的码总是错）

典型实现：`GET /code.jpg?rand` 的响应同时做两件事：
1. 返回图片字节
2. `Set-Cookie: <混淆名session>=<值>` 下发会话

之后登录 POST 必须**携带同一会话 Cookie**，服务端才能把"你输入的码"与"发给你的那张图"对上号。

推论与坑：
- 用户拿手机浏览器开图片地址 → 图对应的是**浏览器的会话**，App 提交时带的是 App 的会话 → 必错
- `java.startBrowser` 方案在该 lyc 版可用，是因为其 WebView Cookie 已与 CookieJar 打通（完本神站实测）；换其他 App 版本需先验证这一点
- 抓包验证法：请求图片后立刻打印 `cookie.getCookie(host)`，确认出现了新 session 键

---

## 4. Cookie 三大巨坑（血泪）

### 坑一：setCookie 是整体替换，不是合并！
```js
// ✗ 错误：这一句会把该域名下所有 Cookie 清空只剩这一个
cookie.setCookie(u, "search_time=123");

// ✓ 正确：取全文 → 正则改键 → 回写全文
var c = String(cookie.getCookie(u)).replace(/search_time=\d+/, "");
cookie.setCookie(u, c);
```
症状：改一个键后突然全部 302 到登录页——就是登录态被抹了。

### 坑二：验证码绑定会话
见第 3 节。看图与提交必须同会话；失败自动 `refreshCaptcha()` 换码。

### 坑三：限频 Cookie 的"删键即破"
ppxsw 案例：服务端**只检查请求是否携带 `search_time` Cookie**——带就拒（返回12条推荐书+倒计时提示），不带就当首次放行；服务端从不更新该值。
- 干等无效：倒计时按"最近一次请求时刻"计，**每次失败的尝试都会重置**（实测 P1=122s → 等26s → P2=122s，递减量=0）
- 改值为过去时间无效：校验不看值
- **删除即破**：
```xml
<!-- searchUrl -->
<js>
var U="https://www.ppxsw.cc/";
var c=String(cookie.getCookie(U)).replace(/search_time=\d+/,"");
cookie.setCookie(U,c);
"/search.html,{\"method\":\"POST\",\"body\":\"s=\"+encodeURIComponent(key)+\"\"}"
</js>
```
放在 searchUrl 前置 JS 里 = **每次请求前都删**，首搜即成功（实测连续两次搜索均37条真结果）。

> 方法论：遇到限频先做四组对照实验——①立即连发两次看提示变化（判断是否重置计时）②静默等待后单发（判断纯时间因素）③改 Cookie 值再发（判断是否看值）④删键再发（判断是否只查存在性）。ppxsw 四组实验做完，机制自然水落石出。

---

## 5. loginCheckJs 的正确契约

lyc 版中 loginCheckJs 是**响应拦截器**风格：每个书源请求完成后执行，`result` 为 StrResponse 对象。

```json
"loginCheckJs": "(function(){try{var b=String(result.body());if(b.indexOf('<title>用户登录')>=0){throw new Error('xx·登录已失效，请重新登录');}}catch(e){if(String(e).indexOf('重新登录')>0){throw e;}}return result;})()"
```

铁律：
- **必须 `return result`**（返回 Boolean 会 `ClassCastException: Boolean cannot be cast to StrResponse`）
- 自身异常要 try-catch 包裹，只让"掉线提示"冒泡，其余异常吞掉透传，避免污染正常请求
- `.body()` 是方法调用（lyc 版），不是属性

---

## 6. UA 双模板陷阱（"手动验证过但 App 失效"的头号元凶）

同一 URL，站点按 User-Agent 返回**两套完全不同的 DOM**：

| 页面 | 移动 UA（App 实际） | 桌面 UA（部分工具默认） |
|---|---|---|
| 分类页 `/list/N-N.html` | `.dv1 > a.list > .fmy(h4/.info)` 卡片 | `ul.list_l2 li (span.s1/.s2/.s4)` 表格 |
| 目录页 `/index/{b}/{N}/` | `ul.ph_list`（最新倒序区+正序区） | `div.info_dv3` 结构 |

后果：你在桌面环境的工具里验证规则命中 30 条，App 里却是 0 条。

### 标准诊断流
1. `set_http_log_recording(true)` 开启 MCP HTTP 日志
2. 触发一次 App 侧请求（debug_source 或校验）
3. `get_http_logs` 找到目标请求 → `get_http_log(id)` **看响应体原文**
4. 按 App 实际收到的 DOM 写规则，而不是按你抓到的 DOM

### 显式 UA 取移动版页面（eval_js 内）
```js
var MUA="Mozilla/5.0 (Linux; Android 14; ...) Mobile Safari/537.36";
var h=String(java.get(url,{"User-Agent":MUA}).body());
```
> 注意：lyc 版 eval_js 里裸 `java.ajax(url)` 走桌面默认 UA，与 App 规则请求不同源！

### 附赠发现：排序开关参数
某站目录页自带正序/倒序切换链接 `/index/{b}/N/desc.html`。排查乱序时优先看有没有这类原生参数。

---

## 7. 目录乱序修复（阅读不去重也不排序）

移动版目录 ul#0 典型三段结构：
```
[0~13]  最新14章倒序   ← li 无 class（乱序元凶）
[14+]   第1章起正序    ← li class="br-b-1"
[尾部]  推荐书区（另一个 ul.ph_list）
```

阅读按出现顺序去重保留首次 → 最新区排在最前 = 乱序。

**修复**：只取正序区
```json
"chapterList": "class.ph_list.0@class.br-b-1@tag.a"
```
- `.ph_list.0` 只取第一个列表（第二个是推荐书）
- `.br-b-1` 精确过滤最新倒序区
- 跨分页时每页的最新区都被同样滤掉，各页正序天然拼接有序（实测首章=第1章）

> 定位方法：遍历 li 统计 class 分布 + 打印边界索引处的条目文本，找出正序区的 DOM 特征。

---

## 8. tocUrl 字段位置与写法大坑

- **位置**：`tocUrl` 属于 **ruleBookInfo**！放进 ruleToc 会被反序列化静默丢弃（症状：日志"获取目录链接"永远是详情页本身）
- **不支持 `||` 兜底**：`A||B` 整串会被当 URL 请求
- **通用写法**（og:url 全书籍恒存在时）：
```json
"tocUrl": "[property=og:url]@content##/([a-z]+)/$##/index/$1/1/"
```
把详情页 `/mcwk/` 正则重组为目录 `/index/mcwk/1/`。
- 详情页文字入口链接可能**只有部分书有**（如完结书没有"查看更多章节"），勿单独依赖
- 文字匹配注意省略号：页面是"查看更多章节..."，规则写 `text.查看更多章节` 匹配失败

---

## 9. 正文 base64 反爬（动态对象名）

移动版正文形如：
```html
<div class="txt" id="txt">
<script>document.writeln(rgr.owes('PHA+4oCc...'));</script>
<script>document.writeln(rgr.owes('PHA+55yL...'));</script>
```
对象名/方法名**每本书随机**（`rgr.owes` / `vypflhij.atyffy`…），但三大恒定特征：
1. 定义处 `var (\w+)=\{_keyStr:"ABC...xyz0123456789+/="`（标准 Base64 字母表）
2. 调用处 `<obj>.<method>('Base64串')`
3. 解码结果以 `<p>` 段落组织（PHA+ 就是 `<p>` 的编码头）

**动态解码模板**（content 规则，纯 @js: 保证 result 为完整源码）：
```js
@js:(function(){var s=String(result);
var vo=s.match(/var\s+(\w+)=\{_keyStr/);
if(!vo){return '';}
var re=new RegExp(vo[1]+"\\.[A-Za-z]+\\('([A-Za-z0-9+\\/=]+)'\\)","g");
var m,out='';
while((m=re.exec(s))!==null){out+=java.base64Decode(m[1]);}
return out.length<10?'【正文获取失败】':out;})()
```
> 简化替代：直接全局匹配 base64 特征 `/PHA\+[A-Za-z0-9+/]+={0,2}/g`（PHA+ 即 `<p>` 编码头），参考源采用此法，缺点是段落不以 `<p>` 开头的站会漏。

**分页泛化匹配**（nextContentUrl）：
```js
@js:(function(){var m=String(result).match(/='(\/[a-z]+\/[a-z]+\_[0-9]+\.html)'/);return m?m[1]:'';})()
```
分页变量形如 `var hhekgv='/book/chap_2.html'`。末页时变量指向下一章或书首页（不含 `_N.html`）→ 自动不匹配 → 无需同章校验。锚点变量名随机没关系，匹配的是**赋值形态**而非变量名。

---

## 10. MCP 调试方法论

| 场景 | 工具/手法 |
|---|---|
| 规则在 App 里失效但手动验证正常 | `get_http_log(id)` 看 **App 实际收到的响应体**（UA双模板/CDN缓存差异一锤定音） |
| debug_source 超时（含 sleep/重试的长链路） | 改用 `eval_js` 绑定书源 url 分段模拟；MCP 客户端超时约 120s，长等待拆多段 |
| 校验器报"XX失效"但手动正常 | 连续快速请求触发站点限频所致；先解决限频再校验，或以手动单请求为准 |
| 需要看响应头 Set-Cookie / 缓存命中 | `set_http_log_recording(true)` + `get_http_log(id)`，关注 `X-Cache-Status: HIT from Lx`（CDN 按 UA 分桶缓存也是双模板诱因） |
| 验证"失败尝试是否重置限频计时" | probe→sleep→probe 对比倒计时读数（递减≈间隔则不重置；不变则每次尝试都重置） |
| 探测登录端点各校验环节 | 固定 session + 故意错码 → 看返回文案区分"非法访问/码错/密错"的先后 |

---

## 11. 可复用片段速拷

**搜索前置去限频（删指定 Cookie 键）**
```xml
<js>
var U="https://www.site.com/";
var c=String(cookie.getCookie(U)).replace(/LIMIT_KEY=\d+/,"");
cookie.setCookie(U,c);
"/path,{\"method\":\"POST\",\"body\":\"k="+encodeURIComponent(key)+"\"}"
</js>
```

**封面从书籍URL推导**（页面无图时）
```json
"coverUrl": "href##.*\\/([A-Za-z0-9]+)\\/$##/img/$1.jpg"
```

**登录态自检（配合 loginCheckJs 透传契约）**
见第 5 节模板。

---

## 12. 检查清单（交付前过一遍）

- [ ] loginUrl 为具名函数集，按钮 action 仅写函数调用
- [ ] login(b) 有 `b==undefined` 守卫；result 取 UI 值
- [ ] 成功路径有 `source.putLoginHeader(java.getCookie(host))`
- [ ] logout 三清（登录头/Cookie/UI缓存）
- [ ] 验证码方案与 App 上下文匹配（对话框内一律 startBrowser+手填）
- [ ] AJAX 头齐全（X-Requested-With / Referer / Content-Type）
- [ ] 密码加密已逆向比对确认
- [ ] 所有 Cookie 写操作均为"取全文→改→回写"
- [ ] tocUrl 位于 ruleBookInfo 且无 `||`
- [ ] chapterList 已过滤最新倒序区/推荐区（防乱序）
- [ ] content/nextContentUrl 的 JS 已在**移动 UA 页面**上验证
- [ ] respondTime ≥ 实测最长耗时（慢站设 180000）
- [ ] bookSourceComment 写明使用前提（需登录/限频说明）

---

*V1.3 · 基于 2026-08-25 ppxsw.cc 全要素实战（登录/**注册**/验证码/限频/乱序/base64/双模板）与完本神站成熟范式整理。V1.3 增补：注册流程实战(qs_register_go.php 参数体系)、loginUi 取值双风格对比(getLoginInfoMap vs result)、Thread.sleep 唯一延迟手段提醒。*
