# 方法-CF盾双版本行为差异与书源运行时自适应

> 261029 西瓜书屋实战提炼。跨站通用经验：**同一份书源 JSON 要同时服务 LT(gedoor/legado) 与 E(Luoyacheng/legado-E) 两个 App，而两版的网络栈行为、CF 判定、WebView 引擎指纹都可能不同**。本文给出「运行时探测版本 → 分通道路由」的完整方法论，以及 CF 盾在两版上的行为矩阵。此前技能库从未沉淀过「同一站点在两版上反爬行为相反」的场景。

---

## 一、核心场景：同一 CF 站，两版行为完全相反（实锤数据）

西瓜书屋（www.xiguashuwu2.com，CF managed challenge）真机实测：

| 搜索通道 | LT 版 | E 版 |
|---|---|---|
| OkHttp 直连 | ❌ 403（指纹被挑战） | ❌ 403（同） |
| **webView:true 通道** | ✅ **直出结果，不弹窗** | ❌ **60s 超时** `TimeoutCancellationException: Timed out waiting for 60000 ms` |
| **startBrowserAwait 人工过盾** | ❌ **死循环**（弹窗直进页面、无验证过程，过多少次都没用） | ✅ **过一次长期有效** |

### 1.1 为什么 LT 弹窗直进页面（无验证过程）？
CF 只按 TLS/HTTP2 指纹挑战 OkHttp；LT 的系统 WebView 指纹被 **无感放行**。关键：**无感放行不签发 cf_clearance**（没有挑战就没有"盾票"）⇒ 人工过盾路线永远死循环：弹窗→WebView 被放行→关窗→OkHttp 重新请求→又被指纹挑战→又弹窗。旧源 `cookie.removeCookie` 会加剧（把偶然拿到的票也删掉）。

### 1.2 为什么 E 的 webView 通道超时？
E 的 WebView 栈/UA/引擎参数与 LT 存在差异（两版 WebViewActivity、请求头注入逻辑源码级不同），CF 对 E 的 WebView 指纹**判挑战**→挑战页在无人工交互的 BackstageWebView 里永远过不去→60s 超时。而 E 的人工过盾窗口（startBrowserAwait）是真交互 WebView，过一次 cf_clearance 落库且**会话保持好**。

### 1.3 行为矩阵速查（排查 CF 站先对号入座）
| 现象 | 定性 | 通道选择 |
|---|---|---|
| 弹窗即进真实页面、无验证过程、反复弹 | 指纹放行型（LT 常见） | webView:true，禁走人工过盾 |
| 弹窗出现真验证（转圈/勾选） | 交互挑战型 | 人工过一次，长期有效 |
| webView 通道恒超时、人工过盾有效 | E 型 WebView 被挑战 | OkHttp+loginCheckJs 人工过盾 |
| OkHttp 与 WebView 都通 | 无 CF 或已持票 | 默认通道即可 |

---

## 二、通用解法：searchUrl 运行时探测版本，分通道路由

### 2.1 版本探针
`source.getLoginUiJs` **LT 独有**（BaseSource.kt:111 `fun getLoginUiJs()`），E 的 BaseSource 无此方法（源码级实锤）。`typeof` 判断天然安全，方法不存在也不炸。

### 2.2 书源 searchUrl 模板（开箱即用）
```
@js:(function(){
var u='/search/'+encodeURIComponent(String(key||''));
var isLT=false;
try{isLT=(typeof source.getLoginUiJs==='function');}catch(e){isLT=false;}
if(isLT){
  return u+',{"webView":true,"webViewDelayTime":1800,"timeout":30000,"retry":1}';
}
return u+',{"timeout":30000,"retry":1}';
})()
```
- LT → webView 通道（BackstageWebView 直载搜索页，CF 放行即得结果 DOM；`webViewDelayTime` 给 CF 探测+页面动态渲染留时，动态渲染结果的站别低于 1500ms）
- E → OkHttp 通道，被 CF 拦时 loginCheckJs 弹**带关键词的 baseUrl** 人工过盾
- **其余规则（详情/目录/正文）不需要路由**——它们通常不被 CF 拦（CF 规则只针对搜索类路径时），只有被拦的通道才需要 webView/人工过盾

### 2.3 loginCheckJs 配套（兜底+透传）
```
(function(){
var b='';
try{b=String(result.body()||'')}catch(e){b=String(result||'')}
var u=String(baseUrl||'');
if(b.indexOf('Just a moment')>=0||b.indexOf('_cf_chl_opt')>=0||b.indexOf('challenges.cloudflare')>=0){
  java.toast('触发CF盾，弹出浏览器验证');
  return java.startBrowserAwait(u,'站点·人机验证');
}
if(b.indexOf('请不要频繁操作')>=0){java.toast('站点限频，请稍后重试');}
return result;
})()
```
铁律：**绝不 removeCookie**；弹窗 URL 必须是 `baseUrl`（本次带关键词的真实请求），过盾后 refetch 才会重放关键词搜索；必须 `return result`（E 的 `as StrResponse` 硬强转）。

---

## 三、搜索通道技术要点（本次新增机制认知）

1. **@js: searchUrl 必须 IIFE**——顶层 `return` 报「返回的值无效」（EvaluatorException），两种合法形态：IIFE 或末表达式
2. **AnalyzeUrl.evalJS 绑定**（两版一致）：`java/source/key/page/baseUrl/result/infoMap`；`initUrl()` 顺序 = analyzeJs → replaceKeyPageJs → analyzeUrl ⇒ JS 先执行、`{{key}}` 与 JS 内 `key` 变量都可用；JS 返回的字符串里可以带 `{{page}}` 模板（后续阶段替换）
3. **webView:true 的执行链**：GET+webView → `BackstageWebView(url).getStrResponse()`——后台 WebView 直接加载 URL（不经 OkHttp），Cookie 由 onPageFinished 自动落 CookieStore；**无注入 JS 时默认只等 900ms**，页面有 JS 动态渲染必须显式 `webViewDelayTime`
4. **webView 通道请求不进 OkHttp HTTP 日志**（走系统 WebView 网络栈）——排查搜索问题时在日志里找不到 `/search/` 请求是正常的，别误判"请求没发出"
5. URL 选项布尔解析：`webView` 为 `null/""/false/"false"` 才算关，其它一律 true——所以 `{"webView":"true"}` 也有效
6. **json.dumps 构造含引号的 JS 行**：build 脚本里写 `"searchUrl": '@js:...'` 会被 JS 内单引号打断，用 Python `json.dumps()` 生成整行最稳

---

## 四、Rhino 正文 JS 两条铁律（本次真机实锤）

### 4.1 IIFE + return 是唯一可靠输出结构
content `<js>` 里**顶层裸语句 + 末尾表达式返回**会在真机丢返回值：探针实测算法各步全对、变量有值 3415 字节，`getString` 却拿到空 → `ContentEmptyException` 且无任何报错。IIFE+return 版直接成功。写法：
```
<js>
(function(){
  ...
  return out;
})()
</js>
```

### 4.2 跨 try/catch 的变量必须顶部 var 声明
catch 里引用 try 内首次赋值的变量时，若异常发生在赋值前 → 变量未声明 → `ReferenceError: "out" is not defined`（直接冒给用户）。**所有跨 try/catch 的变量在 IIFE 顶部 `var` 声明**。

### 4.3 测试桩必须与生产同源
沙盒 node 测试桩手抄算法时**顺手补了 `var out=''`** → 沙盒全绿、真机炸。**测试桩必须从书源 JSON 里提取 JS 原文执行**（`new Function('src','result','java', 'return eval(...)')` 包装，注入桩 java 对象），不要手抄。

---

## 五、正文多形态站点的「行为判据优先」原则（第四形态新增）

站点会在页面埋**全套反爬标记**（随机容器 id、meta client、codeurl、newcon 密文）但**真正文在容器里明文躺着**（密文只是空壳载荷）。按「页面有哪些标记」路由会静默输出乱序错文（不报错，比炸更危险）。

**判据要落在「容器内有没有明文」**。四层判据模板（按顺序匹配）：
```
1. nid=='C0NTENT'                      → 静态拼块
2. plainLen<10 且有 newcon=decodeURI…  → AES 解密（空壳干扰页）
3. b64序号数==块数 且 plainLen>=10     → UpWz 乱序还原 slots[v-(i+1)%code]
4. 否则（有明文无乱序特征）            → 直接拼块
```
plainLen = 容器内所有块去标签去空白后的总字符数。**单章每页独立判定**——同一章可以 p1 静态/p2 乱序/p3 明文干扰/p4 乱序混用（实测 17686B 四页无缝拼接）。

---

## 六、工程纪律（本次新增）

1. **双 App 部署 = 双端点**：LAN web 服务 LT:E 两个端口并存（如 :1122/:1125），推送时**两个都推**并各自回读 `searchUrl`/`loginCheckJs` 特征确认落库
2. **E 的 /getHttpLogs 不可用**（返回非 JSON），LT 可用——E 上要拿网络证据只能靠书源探针（throw new Error 回传 errorMsg）或用户截图
3. **App 内探针法**（无需 MCP）：content/规则 JS 临时换成 `throw new Error('XG '+变量1+' | '+变量2)`，`/getBookContent` 的 errorMsg 会带回全部中间值——比看日志快
4. **正文按 bookUrl+index 落盘缓存**：改规则后旧章仍读缓存，验证要用没读过的 index（`deleteBook` 不清内容缓存文件，同名书重加无效）
5. check_source 对 CF 站必报 FAILED `source verification cancelled`——校验器无 UI 通道，`startBrowserAwait` 必被取消，**预期行为不是书源错**，CF 站最终判定以真机为准

---

## 七、与既有文档的关系
- CF Turnstile 人工过盾流程：见 `/topics/legado-cf-turnstile.md` 记忆与 cf登录检测参考
- 双版本 API 差异总表：`references/方法-legado各版本行为差异对照.md`（本文补充的是**网络栈/CF 行为差异**维度）
- WAF 家族分型：`references/方法-WAF与CF间歇故障及站点判活.md`（本文补充「指纹放行型」这一新分型）
