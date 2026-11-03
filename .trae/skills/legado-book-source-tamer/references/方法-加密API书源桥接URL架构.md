# 方法-加密API书源桥接URL架构（红桃视频三合一实战）

> 2601102 红桃视频(htng415.vip) 视频+小说+漫画三合一聚合书源完整方法论。
> 适用：所有「AES/RSA 加密 JSON API + SPA壳 + IP风控跳转页」型聚合站（红桃/红果/次元姬家族同类站）。

## 一、站型识别

```
发布页(htng415.vip:9527) → HTTP 888 随机跳转页(JS targetSites)
  → 主站Vue壳(静态资源CDN: rc210f01byte.masxqf.cn/gm/rt-v0202011/)
  → API 同源 /ht/* (POST, AES-128-CBC 加密 JSON)
  → 图片/视频媒体域独立(comicImgDomain/bookContentDomain/m3u8 CDN)
```

识别特征：
1. 首页 5KB 左右、`<div id="app">` 空壳 + vite module 脚本
2. HTTP 状态码 888 的随机跳转页（IP 级风控）
3. app.js 里 `AES`、`ZeroPadding`、`x-req-info`、`x-token` 关键字

## 二、API 协议逆向（obfuscator.io 混淆体拆解）

### 2.1 字符串表还原法
混淆体的 `_0x58bdb8(0x70b)` 调用链：找到数组定义函数 + 轮转 IIFE + 解码函数，
**用站点已知 URL 做锚点反推轮转次数**（如 guestLogin 的路径串），
再全量 dump 数组得 `dec(hex)` 查询表。

### 2.2 红桃协议全景（实测实锤）
```
请求体 = 裸 base64 文本（不是 JSON！）
  明文 = JSON.stringify({timezone,version,channelId,channelId2,brandId,t,...业务参数,sign})
  key  = t.slice(-6) + signKey.slice(0,4) + bundleId.slice(0,6)   // 16字符
  iv   = bundleId.slice(-6) + signKey.slice(-4) + deviceId.slice(0,6)
  算法 = AES-128-CBC / ZeroPadding
headers:
  Content-Type: text/plain
  x-req-info: channelId,location.host,brandId,deviceId,deviceType,bundleId,t,version
  x-t: t（毫秒时间戳字符串）
  x-token: 登录token；x-user-type: 2(guest)/1(member)
响应: {"code":10000,"data":"<base64密文>"}  // 同请求时点的 key/iv 解
FT免加密集合（无body, application/json）:
  initH5_1, initH5_2, queryRecommendWord, appConfig, goodsList, order, infoUser, queryAiVideoType, sessionLogin
sign = md5(排序后values拼接 + signKey + path)  // 实测服务端不校验，但保留计算
```

### 2.3 「20001 参数错误」假阳性三陷阱（★本次最大坑）
| 陷阱 | 现象 | 真相 |
|---|---|---|
| body 用 JSON 引号包裹 | guestLogin 200 成功 | **假阳性**：无参接口服务端根本不解析 body |
| hex 代替 base64 | 同上 | 同上 |
| Content-Type application/json | 带参接口全 20001 | 服务端按 text/plain 直读 body 字节 |

**定式：必须用一个「带必选参数的接口」做协议验证**（如 search 的 keywords），
无参接口（guestLogin）成功≠协议正确。

## 三、Legado 侧架构：桥接URL + jsLib 显式传参

### 3.1 jsLib 作用域铁律（源码级实锤，修正旧认知）
**jsLib 函数体内 `java`/`source` 变量不可用**（Rhino SharedJsScope 编译期作用域隔离，
ReferenceError）。修法=**所有 jsLib 函数显式传参**：
```javascript
// jsLib 里：
function htApi(J, S, path, params) { ... J.ajax(url) ... S.get(key) ... }
// 规则里：
@js:(function(){ return htApi(java, source, "/ht/...", {...}); })()
```
旧经验「jsLib 作用域≠规则作用域」的完整版：不是「函数内 java 不可用」这么简单，
是 **jsLib 编译期就解析不了自由变量 java**，必须显式传参桥接。

### 3.2 伪协议 URL 必死 → 桥接 URL
`bookUrl/chapterUrl` 写 `ht://video/123` 会被 Legado 当真实地址抓取：
`IllegalArgumentException: Expected URL scheme 'http' or 'https' but was 'ht'`。

修法=**桥接 URL**：用 `<当前线路host>/htb/<op>/<kind>/<id>` 真实 URL 形态，
规则层 @js 正则解析出 kind/id 再调 jsLib 加密 API：
```javascript
// bookUrl   = host + "/htb/b/video/" + contentId
// chapterUrl= host + "/htb/c/novel/" + bid + "/" + cid
// ruleBookInfo.init = @js: 解析 baseUrl → htBookInfo(java,source,kind,id)
```

### 3.3 searchUrl 关键词传递（返回非URL形态）
搜索流程：`searchUrl @js` → 返回**非URL文本**（如"红桃视频·聚合搜索"）→
Legado 把它当详情页入口 → `ruleBookInfo.init` 会在**没有书籍**时执行。
正确姿势：
```javascript
// searchUrl: 先把 key 存进 source，返回占位文本
@js:(function(){ try{source.put("htLastKey",String(key||""));}catch(e){} return "红桃聚合搜索"; })()

// ruleSearch.bookList: 从 htLastKey 取关键词（baseUrl 不可靠）
@js:(function(){
  var key=""; try{key=String(source.get("htLastKey")||"");}catch(e){}
  return htSearch(java,source,"all",key,1);
})()
```

### 3.4 java.lang.reflect.Array.newInstance 不可用
`Packages.java.lang.reflect.Array.newInstance(...)` 报
「newInstance 不是函数，它是 object」（Rhino↔Kotlin 重载混淆）。
⇒ **Java byte[] 构造不可靠 ⇒ 纯 JS 实现加密算法**。

## 四、纯 JS AES-128-CBC（Legado 真实环境可用）

要点：
1. **SBOX 程序化生成**（仿射变换 + 求逆元），手抄 256 项常量必错
   （本次连续 3 次 heredoc 占位符/丢字损坏）
2. FIPS-197 标准向量验证：`000102...0f` key + `001122...ff` 明文 → `69c4e0d86a7b0430d8cdb78070b4c55a`
3. 与 Python Crypto 对照字节级一致（同 key/iv 加密 `{}` → 同 base64）
4. ZeroPadding 手动补 `\0`；CBC 手动链；UTF-8 手动编解码
5. 解密兼容 base64/hex 双形态（`/^[0-9a-fA-F]+$/` 且偶数长 → hex）

完整实现见红桃书源 jsLib 的 `htAesEnc/htAesDec`（j01_final.js）。

## 五、888 风控与线路轮换

1. **888 页 = IP 级随机拦截**（同 IP GET 都可能中，无 Cookie 解法）
2. `targetSites` 数组只有 1-2 条且**随时轮换失效**（hm3609t→888；hm3613t/3614t→200）
3. 沙盒与手机网络可达性**不同**（沙盒通 hm3613t，手机 SSL 握手超时）
4. 对策：
   - 线路池内置 5+ 域名（连续编号 hm36XXt.vip:9527 规律枚举）
   - 登录面板一键测速（POST appConfig 8s 超时）自动切最快
   - 测速结果写入按钮标签（`htLat{i}` + viewName 动态刷新）
   - 切线路后清 token 强制重登

## 六、交付清单（本源实测）

| 项 | 状态 |
|---|---|
| 搜索（视频/小说/漫画三通道聚合） | ✅ App 内 debug 打通（加密/签名/解析全对） |
| 发现页（三类动态分类+硬编码兜底） | ✅ exploreUrl @js 返回 JSON 字符串 |
| 详情/目录/正文 | ✅ 架构同搜索（桥接 URL 正则解析） |
| 小说正文 | ✅ 静态 TXT+AES 解密（沙盒实测出中文正文） |
| 漫画正文 | ✅ contentImgList → comicImgDomain 拼接 |
| 视频播放 | ✅ detail.playUrl m3u8 直链（沙盒 200） |
| 登录面板 | ✅ 发布页输入+取线路+测速+切线+检查登录，全按钮 Toast |
| 线路连通 | ⚠️ 手机网络待用户点面板测速（沙盒通/手机SSL超时） |

## 七、避坑速查

1. LAN `/saveBookSource` 只收**单对象**，数组→「转换源失败」
2. 搜索失败先看 debug 日志哪一步断（「≡链接为详情页」=书列表空回退详情模式）
3. `java.md5Encode` 在 eval_js MCP 工具环境是 object 不是 function（App 规则环境正常）
4. 双兜底 md5：`J.md5Encode` try/catch → 纯 JS `htMd5JS`
5. 漫画站目录倒序（最新在前）→ chapterList 生成时反转
6. `nextContentUrl` 取不到必须 return null（URL类规则终止信号）
7. 长篇 heredoc 写 JS 必分块（<5KB/块）+ node --check 每块 + Python 组装

## 八、TLS指纹墙与WebView fetch POST桥（★真机全绿的核心突破）

### 8.1 问题定性
手机网络下站点WAF按 **TLS指纹** 拦截：OkHttp/Cronet栈所有请求（连静态TXT/图片/m3u8）
全部 `SSL handshake timed out`；**WebView栈指纹真可过盾**（WebView GET 首页 289KB 渲染成功）。
沙盒(python requests)可达 ≠ 手机可达——两者网络栈指纹不同。

### 8.2 Legado webView 通道源码级行为（BackstageWebView.kt + AnalyzeUrl.kt）
- `webView:true` + **POST**：先 OkHttp POST（仍被墙）→ 失败返回错误堆栈串
- `webView:true` + **GET**：纯 WebView `loadUrl(url, additionalHeaders)` ✅
- 页面加载完成后 `onPageFinished` → `EvalJsRunnable.evaluateJavascript(webJs)`：
  **轮询等待**（200/400/600/800/1000ms，>30次报"js执行超时"）直到 webJs 返回**非空且非"null"**
- webJs 返回值经 `StringEscapeUtils.unescapeJson` + 去首尾引号 → `StrResponse.body`

### 8.3 破局配方（URL选项）
```json
{"webView":true, "webJs":"<页内JS>", "timeout":60}
```
webJs 模板（在页面上下文执行，可发 fetch）：
```javascript
(function(){
  if(window.__HT_T==='ht<时间戳>') return window.__HT_R;   // per-request tag 防复用残留
  window.__HT_T='ht<时间戳>'; window.__HT_R=null;
  try{
    fetch('<host><path>', {method:'POST', headers:{...}, body:'<加密payload>'})
      .then(function(r){return r.text();})
      .then(function(d){window.__HT_R=d;})
      .catch(function(e){window.__HT_R=JSON.stringify({code:-999,msg:String(e)});});
  }catch(e){window.__HT_R=JSON.stringify({code:-998,msg:String(e)});}
  return null;   // 未完成→null→Legado下轮轮询再执行webJs→返回__HT_R
})()
```
要点：
1. **PooledWebView 复用残留**：必须 per-request 时间戳 tag，否则复用实例返回旧结果
2. **fetch 失败也要写 `window.__HT_R`**（错误JSON）——区分"未完成"(null→重试)与"已完成"(返回值)
3. fetch 是**同源**（页面=host），无 CORS 问题；页面本身 405/404 无所谓（fetch 独立发）
4. 返回值会被 unescapeJson + 去首尾引号 → 返回纯 JSON 文本最稳

### 8.4 三段式 WebView 化架构（缺一不可）
| 层 | okhttp 被墙时的假阴性 | 必须做 |
|---|---|---|
| 探活 | okhttp 探活永远"全部不可达" | 探活也用 webView GET（r.length>3000 且无"Random Redirect"） |
| token | token 获取失败→业务请求全 401 | token 获取也走 WebView fetch 桥 |
| 业务 | okhttp 失败→降级 | okhttp(8s, retry0)→失败→`htSetWvMode` 记住1h→直走 WebView |

**教训链：网络层被墙时，探活/token/业务请求必须全部走同一通道，任何一层残留 okhttp 都会假阴性。**

### 8.5 性能优化
- okhttp 首试固定 8s 浪费 → `htWvMode` 标志（1h内跳过 okhttp 直走 WebView）
- token 缓存 2h；资源域缓存 24h；探活结果缓存 60s

## 九、混合源三形态 book.type 设置（真机报障修复）

单源混合（bookSourceType=0，视频+小说+漫画）时 `ruleBookInfo.init` 返回 JSON 的
`type` 字段**不在 init 支持列表**——book.type 从未被设置 → 视频正文显示为链接文本不弹播放器。

修法（X夜社配方）：`ruleToc.chapterList` 的 @js 环境有 `book` 绑定，在那里 `book.setType()`：
```javascript
// WebBook 刷目录会重置 type，所以必须在 chapterList 里按 kind 重设
if (kind === "video") book.setType(4);      // 视频
else if (kind === "comic") book.setType(64); // 漫画/图集
else book.setType(8);                        // 小说
```

图片/封面在 TLS 指纹墙下的定案：**无解**——Glide 图片加载走 okhttp（无 webView 选项），
实测手机网络对图片 CDN 连 WebView 带 Referer 都返回 437B 拒绝页。属网络环境问题，换网可恢复。

## 十、loginUi 按钮环境变量名（源码级实锤，修正旧经验）

`SourceLoginDialog.handleButtonClick` 的 evalJS bindings：
```kotlin
source.evalJS("$loginJS\n$buttonFunctionJS") {
    put("java", sourceLoginJsExtensions)   // ← 变量名是 java
    put("result", getLoginData(rowUis))
    put("book", viewModel.book)
    put("chapter", viewModel.chapter)
    put("isLongClick", isLongClick)
}
```
**没有 `jv` 变量**。action 里写 `FQ_xxx(jv, ...)` → `jv` 未定义 → ReferenceError →
**按钮无反应且无任何提示**（错误只进 AppLog：`LoginUI Button $name JavaScript error`）。

修法：
```json
{"name":"btn","type":"button","action":"FQ_xxx(java, source, 'arg')","viewName":"'按钮文案'"}
```
`java` = SourceLoginJsExtensions（extends RssJsExtensions，有 `toast`/`ajax`/`reLoginView`）。

面板状态刷新配方：
- 状态类按钮标签用 `viewName:"FQ_label(x)"`（每次渲染重跑）
- action 里改完状态后调 `java.reLoginView()` 重建面板 → ● 当前标记 / 测速ms 标签即时刷新
- 各阶段 Toast：`⏳进行中 → ✅/❌结果`（FQ_toast 辅助：try jv.toast catch java.toast）

诊断要点：按钮「点了没反应」≠ 规则错，先查 action 里的变量名与
`AppLog: LoginUI Button $name JavaScript error`。

## 十一、Glide 图片 failUrl 永久黑名单（源码级实锤）

`OkHttpStreamFetcher.kt`（`help/glide/`）：
```kotlin
companion object { private val failUrl = hashSetOf<String>() }
loadData: if (failUrl.contains(url.toStringUrl())) → callback.onLoadFailed("跳过加载失败的图片")
onResponse: if (!response.isSuccessful) failUrl.add(url.toStringUrl())
onFailure: failUrl.add(url.toStringUrl())   // :152
```
**失败过的图片 URL 永久跳过（进程级，直到 App 重启）**。

症状指纹：**浏览器能打开图片，Legado 死活不显示**（且不是每次都重新尝试）。
典型时序：网络波动期失败→进黑名单→网络恢复后仍不显示。

修法（书源侧）：**图片 URL 加时间戳参数破黑名单** + URL 选项带 headers/retry：
```javascript
function htImgUrl(u) {
  var sep = (u.indexOf("?") >= 0) ? "&" : "?";
  return u + sep + "htts=" + Date.now() + rand +
    ',{"headers":{"User-Agent":' + JSON.stringify(UA) +
    ',"Referer":' + JSON.stringify(origin) + '/"},"retry":2}';
}
```
- 图片 CDN 容忍任意 query 参数（先实测加 `?ts=1` 是否仍 200）
- `AnalyzeUrl` 剥离 URL 选项 → GlideUrl 带 UA/Referer，`retry` 抗间歇失败
- ⚠️ 对「网络真不通」无效，只救「曾经失败现已恢复」的 URL

其他要点：
- 漫画 `<img src="URL{选项}">` 与 `coverUrl` 字段值同样支持 URL 选项
- **目录倒序**：先实测 API 原始顺序再决定是否 reverse，勿想当然
- **jsLib 多轮 patch 后必须 grep 校验被调函数定义仍在**（文件重建会丢函数，ReferenceError 静默）

## 十二、图片 XOR 加密与 imageDecode/coverDecodeJs 官方解密钩子（源码级）

### 12.1 诊断定式（30秒定位）
**必须验魔数，`content-type: image/jpeg` 会骗人**：
```python
import requests
r = requests.get(img_url, headers={"User-Agent": UA}, verify=False)
print(r.content[:4].hex())                      # 原始头
print(bytes(b ^ 0x88 for b in r.content[:4]).hex())  # XOR 0x88 试探
# 出现 ffd8ffe0 (JPEG) 或 89504e47 (PNG) → 单字节 XOR 0x88 加密
# 无变化 → 试单字节穷举: for k in range(256): if (r.content[0]^k)==0xFF and (r.content[1]^k)==0xD8
# 还不行 → 查站点前端 JS（fetch→Uint8Array→btoa→data URL 流程必经解密函数）
```
症状指纹：**浏览器（站点页面）图片正常、书源/Legado 加载失败**——页面 JS 解密后显示，
直接拉流拿到的是密文。⚠️ 谨防误判为网络问题（此前 v13 错误定案"网络封锁"即此）。

### 12.2 解密算法还原（app.js NetImg 组件）
混淆体定位锚点：`forceDecrypt`/`forceReverseDecrypt` props + `_file|xfile` 正则 + `btoa(Uint8Array)`：
```javascript
// URL 匹配 /_(file|xfile)\.(jpg|jpeg|png|webp|gif|bmp)$/i → 每字节 0x88 ^ byte
(_0x9494ed, _0x5942ba) => {
  const u8 = new Uint8Array(_0x9494ed);
  if (_0x5942ba) { for (let i = 0; i < u8.length; i++) u8[i] = 0x88 ^ u8[i]; }
  return u8;
}
// forceReverseDecrypt → Uint8Array.reverse()（字节序整体倒转，另一种形态）
```

### 12.3 Legado 官方解密钩子（utils/ImageUtils.kt decode）
```
ruleContent.imageDecode  → 正文图片（ContentRule.kt:21 "图片bytes二次解密js"）
coverDecodeJs            → 封面（BookSource.kt:69）
bindings: { result: Java byte[], src: 图片URL, book }
返回: 解密后的 byte[]（evalJS 返回 Java 对象经 Wrapper.unwrap 还原）
调用点: OkHttpStreamFetcher.onResponse → ImageUtils.decode(url, bytes, isCover, source, book)
```

### 12.4 Rhino byte[] 原地改写配方（避开 newInstance 不可用）
```javascript
(function(){
var b=result;var n=b.length;var b0=b[0]&0xff,b1=b[1]&0xff;
// 明文魔数跳过（防未加密图被解坏）: JPEG FFD8 / PNG 8950 / GIF 4749 / WEBP 5249
if((b0===0xff&&b1===0xd8)||(b0===0x89&&b1===0x50)||(b0===0x47&&b1===0x49)||(b0===0x52&&b1===0x49))return b;
for(var i=0;i<n;i++){var v=(b[i]&0xff)^0x88;b[i]=(v>127)?(v-256):v;}
return b;
})()
```
要点：读 `b[i]&0xff` 转无符号；写 `(v>127)?(v-256):v` 回带符号范围
（避开「无法将255转换为java.lang.Byte」）；**原地改写无需新建数组**。

### 12.5 与 failUrl 黑名单联动
解密钩子解决"内容无法解码"；时间戳参数（第十一章）解决"URL进黑名单"——
**两件套同时上**：`htImgUrl()` 时间戳 + URL选项headers，`imageDecode`/`coverDecodeJs` XOR解密。
