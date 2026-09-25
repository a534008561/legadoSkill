# 69书吧（69shuba.tw）— AEGIS(ALTCHA PoW) 首例 · WebView 通道书源

> 案例类型：**自研人机验证(deny挑战)类站 · 传输层换通道** 
> 知识点全览：[方法-AEGIS-ALTCHA验证与WebView通道书源](../references/方法-AEGIS-ALTCHA验证与WebView通道书源.md)
> 成品：[69书吧_www.69shuba.tw.json](69书吧_www.69shuba.tw.json)（== App 内同源，check_source 1/1）

## 站点真相
69shuba.tw = 69書吧繁中镜像。Cloudflare + 自研 **AEGIS（ALTCHA PoW）** 双防线：
- 任意路径，非浏览器客户端（python / OkHttp / Cronet 全实测）一律 403 Verification 验证页；
- 挑战算法 = 定制 PBKDF2 变体 `SHA256^cost(salt‖nonce‖counter4BE)`，要求结果以 `keyPrefix` 开头；
- **判活铁律：非浏览器被签发 32hex（16字节=128bit）前缀＝数学上不可解（deny-by-design），浏览器才得短前缀**；
- 实测 WebView 拿到的 `__ct_cya_ckt` Cookie 回灌给 OkHttp 请求**仍然 403**——Aegis 按请求 TLS 指纹(ja4，就写在 challenge data 里)逐请求判级，Cookie 不能跨栈升级。

## 解法：WebView 通道传输层（书源内置，用户无感）
```
OkHttp 请求 → 403验证页 → loginCheckJs 拦截(检测 altcha-widget)
  → java.webView(null, url, null)      # 真实 Chromium 内核，Aegis 视为浏览器直接放行
  → new StrResponse(url, 页面源码)      # 整体替换响应
  → 上层的搜索/详情/目录/正文规则照常解析
```
- 正文规则再内置一层自愈兜底（解析失败且疑似验证页 → 再 webView 一次）；
- 登录面板三按钮：`✅检查访问状态 / 🛡网页过盾 / 🌐打开网站` + 三档 Toast 提示词；
- 代价：每页 = 1 次无谓 403(≈0.5s) + 1 次 WebView 渲染(1~2s)，约 2s/章；目录用 nextTocUrl 链式、concurrentRate=2/1500 防风控。

## 站点结构速查
| 功能 | URL |
|---|---|
| 搜索 | GET `/search/?searchkey={kw}&searchtype=all`，分页 `/search/{N}?searchkey=` |
| 分类/完本 | `/fenlei/{cat}/{N}/`（8类）· `/quanben/fenlei/{N}/` |
| 详情 | `/book/{id}/`（og:novel:* 齐全，tocUrl=`/indexlist/{id}/`） |
| 目录 | `/indexlist/{id}/{N?}` 每页100章，`#indexselect-top` 的 option 做分页 |
| 正文 | `/read/{bid}/{cid}` 单页（`div.nr_nr>#nr1>p`，`.reader-ad` 广告块需移除） |
| 封面 | `//p.69shuba.tw/…` 协议相对 → 需补 `https:`（Glide 不吃 //） |

## 本案例实锤的 App 级坑（可迁移）
1. `ruleContent` 正文字段名是 **`content`**（不是 `text`！写错被 GSON 静默丢弃）。
2. 列表 @js 规则在整页 body 上只执行一次 → **必须返回全部条目数组**（单对象/String→列表0）；
   ★条目要逐个 `String(JSON.stringify(item))` 转 JSON 字符串——**legado-E 对 NativeObject 条目没有 Mode.Js 分支，
   直接返回对象数组会「列表大小正常、书名及之后字段全空」**，JSON 字符串条目两版通用。
3. 规则上下文 `result` 可能是 Java String：`typeof result==='string'` 为 **false** → 判元素一律 `typeof el.select!=='function'` 后 `String(el)` 兜底。
4. 目录章节 `<a>` 由页面 JS 把 `.protected-chapter-link`(data-cid-url) 水合而来 → 只有 WebView 渲染后 DOM 才有真实链接（不走浏览器通道就拿不到目录）。
5. loginUi 在 GSON 严格解析版必须标准 JSON；按钮 viewName 两版都是**原样显示（不剥引号不求值）** → 写纯文本，别包单引号。
6. 站内搜索无间隔惩罚（唯一门槛是人机验证），但风控严重，勿高频访问、预下载调小。