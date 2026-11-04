# 方法-WP翻译站视频书源与发布页加密跳转解析（xanimu）

> 2601104 会话产出。站点：xanimu.art / xanimu.ws（WordPress+KOTAK "age-by-nosotros" 主题视频站，WP 翻译插件把 `/page/` 汉化成 `/有关详细信息，请查看此页面。/`）。成品：`/workspace/xanimu/xanimu_v1.json`（16.3KB，check_source 1/1，搜索/发现/详情/目录/正文五链路 App 实测全绿）。

## 1. WordPress 翻译站（zh-CN 泛解析语言站）结构识别

- **URL 形态**：`/zh-CN/` 前缀 + 详情 `/{id}-{slug}/` + 分类 `/{分类slug}/`（嵌套分类 `父/子/`）
- **★分页路径被翻译插件汉化**：WP 的 `page` 分页段变成了 URL 编码的中文 `%E6%9C%89%E5%85%B3...`（"有关详细信息，请查看此页面。"）。识别方法：抓列表页第2页链接的 `<link rel="next">` 或 pagination 区第一跳转
- **分页两种等价形式**（都实测 200）：
  - `{catPath}/{pageSlug}/{N}/`（站内链接形态）
  - `{catPath}/?paged=N`（WP 原生参数）
- **⚠不要用 `?filter=X&page=2`**：实测 `?filter=latest&paged=2` 组合会挂起超时（App/沙盒均复现）；正确组合 = `{catPath}/{pageSlug}/2/?filter=latest`（381ms 秒回）
- **bookUrlPattern 必须锚定详情页数字前缀**：`/zh-CN/\d+` — 放宽到 `(/.*)?` 会把**搜索页也当详情页**（源码 `BookList.kt`：`baseUrl.matches(bookUrlPattern)` 命中 → 整页走 getInfoItem，搜索列表被吞。debug 指纹 = 「≡链接为详情页」）

## 2. 搜索页与列表页规则

- 搜索表单：`GET /zh-CN/?s=关键词`；结果卡片 `div.video-block`
- 字段规则用 Legado 默认 jsoup 规则（`class.video-block`/`class.title@text`/`tag.a.0@href`/`tag.img.0@data-src||tag.img.0@src`）——列表卡片里 `data-src` 懒加载与 `src` 直载并存，双规则兜底
- 分类页排序参数：`?filter=latest|most-viewed|longest`
- 搜索页和分类页结构完全一致 → **ruleSearch 与 ruleExplore 可共用**

## 3. ★★发布页 x99dh.com 三态识别与「从发布页获取线路」正确语义

发布页不是简单页面，而是**三态混合体**（实测）：
1. **x99dh.com / .lat**：HTTP 500 + hex 混淆层。hex 解码后是一段 JS：先 `AES-GCM(key=XOR(b64,b64), iv=16B独立, ct+tag)` 解出第二层 JS，第二层里 `uk=XOR(Uint8Array,Uint8Array)` + `sealed=[iv12+ct+tag16,...]` 解出**发布页自身镜像域列表**（x99dh.lat/net/cc/pro/github.io——是发布页自己的跳转镜像，**不是站点线路**！）
2. **x99dh.github.io / .lat（直开时）**：HTTP 200 静态导航页，含 `const encodedData = 'base64'`；解码链 = base64 → `decodeURIComponent` → JSON 数组（31 站点导航数据，`Xanimu: https://xanimu.ws/zh-CN/` 在其中）
3. **跳转服务**：500 页 JS `location.replace(target)` 自动跳转

**★语义定案**：「从发布页获取网址路线」对**导航型发布页**应提取**站点自身线路**（导航 JSON 里 url 含站点关键字的项），而不是发布页自身镜像域。实现：`XA_navSites(pub)`（encodedData→b64→unquote→JSON.parse→filter url 含 'xanimu'）+ `XA_linesFromPub`（多发布域轮询 + 兜底内置线路表）。

### App 端 JS 实现 AES-GCM（LT/E 双版通用，E 版无 createSymmetricCrypto）
```js
var BAOS = Packages.java.io.ByteArrayOutputStream;   // 唯一可靠 byte[] 构造器(反射Array.newInstance在eval_js不可调用)
var kb = new BAOS(); kb.write((a[i]&0xff) ^ (b[i]&0xff));  // 逐字节写, write(int) 自动截断
var key = new Packages.javax.crypto.spec.SecretKeySpec(kb.toByteArray(), 'AES');
var cipher = Packages.javax.crypto.Cipher.getInstance('AES/GCM/NoPadding');
cipher.init(Packages.javax.crypto.Cipher.DECRYPT_MODE, key, new Packages.javax.crypto.spec.GCMParameterSpec(128, ivBytes));
var pt = cipher.doFinal(ctBytes);            // 返回真 Java byte[]
var str = java.bytesToStr(pt);               // JsExtensions 转 String
```
- **eval_js/规则环境可用**：`Packages.java.io.ByteArrayOutputStream`、`javax.crypto.*`、`java.base64DecodeToByteArray`、`java.bytesToStr`
- **不可用**：`new java.lang.String(...)`（Packages 链断）、`java.lang.reflect.Array.newInstance`（TypeError 不是函数）、`new Packages.java.lang.String(bytes,'UTF-8')`（在 eval_js 环境返回值异常）
- **baos.write() 恒写低 8 位** → 不需要手工 `&0xff` 也能用，但写了更稳

## 4. ★★沙盒 403 ≠ App 403：跨栈网络差异的对照实验纪律

本次最大反转：**视频 CDN（xcdn1/st1.nosofiles.com）在沙盒 requests 下 403（Cloudflare "Just a moment"），App 网络直连 200 真MP4**。反过来主站 xanimu.art 在沙盒 200、App 下 60s 超时（DNS/出口差异）。
**纪律**：
1. 沙盒测出的 CDN 拦截**不能直接下结论**，必须 `java.connect` 走 App 网络复测（connect 返回 StrResponse，`code()`/`body()`）
2. 站点主域与 CDN 域的可达性**在不同出口各自评估**（App 内文本栈 Cronet/OkHttp 与 Glide 图片栈路径也可不同——jmtt 记忆已有）
3. 对照矩阵要包含：沙盒-主站、App-主站、沙盒-CDN、App-CDN、App-CDN-带/不带Referer
4. **双域线路设计**：同站多域名（.ws/.art）在 App 网络下速度差 30-60 倍（.ws 165ms vs .art 9-16s），**默认线路选 App 实测最快的**，面板留切换

## 5. ★搜索限频风控的指纹与对策（未主动探测，从故障反推）

- **指纹**：同一 URL 之前 200（0.6s/155KB），被风控后 `code=200` 但 body 挂起 → 60s 读超时（`InterruptedIOException`）；**约 2.5 分钟后自动解除**（未做主动探测，等 150s 后恢复）
- **不要连续 debug 搜索**：两次 debug_source 搜索间隔 <60s 即触发。debug 关键词要换着用，check_source 前后留窗口
- **concurrentRate 防御值**：`1/30000`（30s 才放行第二个搜索请求），宁慢勿封
- searchUrl 追加 URL 选项 `,{"retry":2}` 应对偶发超时（选项 JSON 可拼在 @js 返回值字符串尾部，paramPattern 正常切分）

## 6. ★@js 与 {{}} 双段模板（searchUrl/exploreUrl 通用）

`AnalyzeUrl.initUrl()` 顺序 = `analyzeJs()`（@js 求值）→ `replaceKeyPageJs()`（{{}} 求值）→ `analyzeUrl()`。
**@js 返回值里可以内嵌 `{{...}}` 模板**（求值发生在 @js 之后）——这是「@js 里动态构造 + {{page}} 分页」的正确组合：
```js
@js:(function(){var b='https://xanimu.ws';try{var v=String(source.get('xaHost')||'');if(v.indexOf('http')===0)b=v}catch(e){}
return b+"/zh-CN/{{page === 1 ? '' : '/%E6%9C%89...%E3%80%82/' + page + '/'}}?s="+encodeURIComponent(String(key||''))})()
```
- `{{}}` 内是完整 JS（三元/拼接/比较都行），绑定含 `key`/`page`/`source`
- page=1 时返回空串 → URL 干净；N>1 拼中文页路径
- **debug_source 的发现调试传 `::URL` 前缀**（`::` = 发现入口；裸关键词 = 搜索；裸 URL = 详情）

## 7. V1 静态 loginUi + viewName 动态文本面板（E 版兼容）

- loginUi JSON 数组：`text` 行（xaHost 主站线路输入框 / xaPub 发布页输入框）+ `button` 行（📡获取线路 / ⏱测延时 / ○线路切换）
- **每个 action 都有 Toast 阶段提示**；测速用 `java.connect`（StrResponse `code()`/`body()`，非 `java.ajax`——ajax 返回 body 字符串无 code/callTime）
- viewName 函数返回动态标签：`XA_statusLabel()`（当前线路）/ `XA_lineLabel(i,def)`（●当前 ○其它 + 延时 ms + ⚡最快标记）
- E 版兼容已核：viewName 求值 = `source.evalJS("$loginJS\n$jsStr")`（E 版 SourceLoginDialog 同款）；action 环境 `result`=getLoginData map、`java`=SourceLoginJsExtensions（`put/get` 转发 source）、`source` 可用（LT 实测；E 版 action 无 source → **所有写操作先 source.put 再 try java.put 兜底**）
- **`function login(){return 'ok';}` 必须有**（右上角√关闭面板）

## 8. 调试工程化经验（本次新坑）

1. **输出流污染防护**：长 heredoc/长 MCP 参数会被环境输出流干扰混入乱码碎片（`?0:0`、半截标识符）。对策：**构建物一律小段 cat >> 追加 + 每段 node --check**；MCP save_source 手打大 JSON 必损 → **走 LAN web 服务**（POST /saveBookSource，Content-Type: application/json，头 x-legado-token）单对象无损
2. **LAN 保存后必须 get_source 回读**逐字段比对（本次抓到 exploreUrl 丢 `@js:` 前缀——裸 JS 会被 BookSourceExtensions 当文本 `标题::url` 解析成 1 个错误分类）
3. **save_source 残缺覆盖事故复现与自愈**：MCP save_source 传手打残缺 JSON 会立即整体替换 App 内书源；Gson 拒绝非法 JSON（MalformedJsonException）则无副作用。恢复 = LAN 通道重传完整版
4. **check_source 是全链路唯一裁判**：debug 分链路绿 ≠ check 绿；check 的搜索链路走完整 searchUrl 求值链
5. **node 模拟 Rhino**：`new Function('source','java','result', jsBody + '\nreturn XXX();')` 完美模拟登录函数库；`@js:` 前缀 strip 后 IIFE 末表达式即返回值（Rhino 求值语义），node 需显式 `return` 包裹

## 9. xanimu 站点档案（复盘速查）

- 搜索 `GET /zh-CN/?s=`；分类页排序 `?filter=latest|most-viewed|longest`；分页 `{path}/{pageSlug}/{N}/`（pageSlug=URL编码的"有关详细信息，请查看此页面。"）
- 详情页关键数据：`<h1>` 标题、`<video poster src>`、`<source>`×2（high/low）、`toStore` JSON（views/likes/length）、LD-JSON VideoObject（keywords/datePublished/contentUrl）
- 正文 = `<video src>` MP4 直链（verify 签名 URL，App 直连 200；免 verify 的 LD-JSON contentUrl 403）
- 无需登录；无 CF 盾（主站）；无搜索验证码
- 发布页：x99dh.com（500+hex 混淆）| x99dh.github.io（200 静态导航，31 站点 JSON）
- 分类总表：/zh-CN/分类/ 177 个（cats.json 已存档，书源内置 30 热门）
