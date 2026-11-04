# xanimu 成人动漫视频书源（xanimu.ws / xanimu.art）

## 案例价值（可复用方法论）
1. **WordPress 多语言翻译站**（zh-CN 泛语言前缀）：分页路径被翻译插件汉化 → `{path}/{pageSlug}/{N}/`，pageSlug=URL编码的「有关详细信息，请查看此页面。」。分页模板用 `{{page === 1 ? '' : '/{pageSlug}/' + page + '/'}}` 拼在 @js 返回值里（@js+{{}} 双段求值，AnalyzeUrl.initUrl 顺序=analyzeJs→replaceKeyPageJs→analyzeUrl）。
2. **bookUrlPattern 收紧铁律**：尾巴 `(/.*)?` 会把搜索页也当详情页（源码 BookList.kt `baseUrl.matches(bookUrlPattern)` 命中→搜索列表被吞，debug 指纹=「≡链接为详情页」）。详情页锚定数字前缀 `/zh-CN/\d+`。
3. **沙盒 403 ≠ App 403**：视频 CDN 沙盒 requests 403（CF Just a moment）但 App java.connect 直连 200 真MP4；主站 xanimu.art 反向（沙盒 200 / App 60s 超时）。**跨栈对照矩阵=沙盒/App × 主站/CDN，沙盒结论必须 App 复测**。
4. **双域线路**：.ws 在 App 网络 165ms vs .art 9-16s（30-60 倍差）——默认线路选 App 实测最快，登录面板可切+测延时。
5. **发布页 x99dh 三态识别**：①com/.lat=500+hex 混淆双层 AES-GCM（解出的是发布页自身镜像域，≠站点线路）；②github.io=200 静态导航页（encodedData→b64→unquote→JSON.parse 31 站，Xanimu→xanimu.ws）；③「从发布页获取线路」=导航 JSON filter 站点关键字，App 实测取回 xanimu.ws。
6. **App 端 JS AES-GCM**（LT/E 双版，E 版无 createSymmetricCrypto）：`Packages.java.io.ByteArrayOutputStream`（唯一可靠 byte[] 构造器，write(int) 低 8 位自动截断）+ `javax.crypto.Cipher/GCMParameterSpec/SecretKeySpec` + `java.bytesToStr`；**不可用**：new java.lang.String、reflect.Array.newInstance、JS 数组直传 SecretKeySpec。GCM 两布局：L1 独立 iv16B+ct+tag；L2 sealed=iv12+ct+tag16。
7. **搜索限频风控指纹**：风控后 code=200 但 body 挂起→60s 读超时，约 2.5min 自愈；两次 debug 搜索间隔<60s 即触发；concurrentRate=1/30000 + searchUrl 追加 `,{"retry":2}`。
8. **E 版兼容**：@js 列表返回 JS 数组、字段 `$.键`、目录条目 JSON 字符串；面板 V1 静态 loginUi+viewName 动态文本（●○+ms+⚡）；`function login(){}` 必须有。

## 交付状态（v1.0，2601104）
- check_source 1/1；debug 发现/搜索/详情/目录/正文五链路全绿；App 端发布页取线/面板函数实测通过
- LAN web 服务（POST /saveBookSource）保存+get_source 回读一致
- 完整方法文档：`references/方法-WP翻译站视频书源与发布页加密跳转解析.md`

## 规则速查
- 搜索 `GET /zh-CN/?s={key}`；分类排序 `?filter=latest|most-viewed|longest`（分页=pageSlug 形式，勿与 paged 组合——`?filter&paged` 会挂起）
- 详情数据源：`<h1>`、`<video poster/src>`、`<source>`×2、toStore JSON、LD-JSON VideoObject
- 正文=`<video src>` MP4 直链（verify 签名 URL App 直连 200；免 verify 的 LD-JSON contentUrl 403）；无分页
