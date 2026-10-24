# 方法 - 封面 Glide 链路与 IP+Host 头直连（封面修复通用范式）

> 依据：哔咔漫画 v84 封面修复（2026-10-24），LegadoTeam 官方源码逐行核对 + 真机（legadoT）全链路实测 + 对照实验。
> **一句话**：封面和正文走**两条不同的网络链路**，正文的 `dnsIp` 选项对封面**完全无效**——这是「正文能显示但封面全灰」的通用根因。

---

## 1. 两条链路的源码级差异

| | 正文图片 | 封面 |
|---|---|---|
| 入口 | `BookHelp.fetchImage` → `AnalyzeUrl.getByteArrayAwait()` | `CoverImageView.load()` → `Glide` → `OkHttpStreamFetcher` |
| URL 选项 | **完整生效**（method/timeout/retry/**dnsIp**/headers） | **只保留 url + headerMap**（`AnalyzeUrl.getGlideUrl()`） |
| dnsIp | ✅ 生效 | ❌ **被丢弃** |
| headers | ✅ 生效 | ✅ 生效（`GlideHeaders(headerMap)` 原样传给 OkHttp） |
| 结论 | 正文可救 | 封面只能靠 **URL 里写 IP + Host 头** |

**源码坐标**（LegadoTeam/legado）：
- `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt:795` → `fun getGlideUrl(): GlideUrl = GlideUrl(url, GlideHeaders(headerMap))`
- `app/src/main/java/io/legado/app/help/glide/OkHttpStreamFetcher.kt:75` → `AnalyzeUrl(url.toString(), source=source, ...).getGlideUrl()`
- `app/src/main/java/io/legado/app/help/glide/ImageLoader.kt:66` → `path.isAbsUrl() -> requestManager.load(path)`（**整个 URL 串原样交给 Glide**）

★ **推论**：封面 URL 写成 `http://<IP><path>,{"headers":{"Host":"xxx"}}` 时，
OkHttp 收到的是「URL 主机=IP + 显式 Host 头=域名」⇒ **既绕过系统 DNS（IPv6 不可达），又让 CDN 认出虚拟主机**。
实测对照（真机）：带 Host 头 157780 字节真实图片 ✅ / 不带 Host 头 `error code: 1003` ❌ / 走域名 `SocketTimeoutException`（IPv6 优先不可达）❌。

---

## 2. 判据方法：真实 Glide 链路怎么验

沙盒/Python 直连 **不能代表真机 Glide**。两个可靠通道：

| 通道 | 说明 |
|---|---|
| **LAN `/cover` 端点** | App 内 `BookController.getCover` → `ImageLoader.loadBitmap` ⇒ **走完整 Glide 链路**，返回 PNG 编码的 Bitmap |
| **`eval_js` + `java.ajax`** | 与 Glide 同一条 OkHttp/OkHttpClient，但**不经 Glide 的 failUrl 黑名单与二次解密** |

★ **判据坑**：`/cover` 返回的是 **PNG**（App 内部把 Bitmap 转 PNG），**不能用 JPEG 魔数 `\xff\xd8` 判成功**。
正确做法：**先取一张必然失败的 URL 作为「占位图基准」（md5 + 字节数），再比对每个用例的 md5**——不同即真实图片。

```python
n0, h0 = get_cover("http://127.0.0.1:1/x.jpg")   # 必然失败 → 占位图基准
n,  h  = get_cover(case_url)
verdict = "✅真实图片" if (h != h0 and n > 3000) else "❌占位图(失败)"
```

---

## 3. 封面 URL 的形态归一（tobeimg 陷阱）

站点常见的 `thumb.path` 有三种形态，**必须分别处理**：

| 形态 | 含义 | 正确 URL |
|---|---|---|
| `tobeimg/<hash>/rs:fill:W:H:0/g:sm/<base64>` | **302 重定向服务**；base64 里是**真实图片 URL** | 先 base64 解码 → 取 `/static/` 后的路径（避开 302 跳 `img.picacomic.com`，该域 Connection reset） |
| `tobs/<file>` | 旧式路径 | **去掉 `tobs/` 前缀** → `/static/<file>`（实测带前缀会 301 到去前缀地址，去前缀直接命中） |
| `<file>` | 普通路径 | `/static/<file>` |

★ base64 解码坑：payload 长度**不一定**是 4 的倍数，需 `while (pay.length % 4 !== 0) pay += "="` 补齐；
用 `Packages.android.util.Base64.decode(pay, 0)` + `new Packages.java.lang.String(bytes, "UTF-8")`
（jsLib 内 `java.base64Decode` **不可用**，jsLib 无 java 绑定）。

---

## 4. 分形态路由：按「解码后的真实托管域」决定走哪条通道

**不要用 `fileServer` 判断真实归属**——`tobeimg` 的 `fileServer` 与 base64 里的真实 host 可能不同，
必须**以 base64 解码出的 host 为准**。哔咔实测 320 本样本：

| 真实托管域 | 占比 | 可用通道 |
|---|---|---|
| `storage-b.picacomic.com` | 41.6% | ✅ `http://<CF-IP><path>` + `Host: storage-b.picacomic.com`（**Cloudflare IP 池，实测 8/8 通**） |
| `storage1.picacomic.com` | 58.4% | ❌ **该域在真机完全不可达**（DNS 只给 1 个轮换 IP，测遍 CF 池 + 自身 IP 全超时），且其 tobeimg 文件**服务端已 404/502**（不是网络问题） |

★ **结论**：不是所有封面都能救。**上游数据本身失效的部分（storage1 的 tobeimg）书源层无解**，
应如实告知用户，而不是继续换通道试错浪费用户时间。

---

## 5. 手动 Host 头的安全性

- OkHttp `BridgeInterceptor` **只在缺失时**补 Host ⇒ 显式 Host **不会被覆盖**；
- Legado 的登录头只发给**同站**（`AnalyzeUrl.isLoginHeaderSite` 按二级域名判定），
  跨域 CDN **不会带上 authorization** ⇒ 手动 Host 不会导致 token 外泄；
- 但**不要**给 CDN 请求塞 `authorization`，参考源的 `Header()` 就是这么做的（`source.getLoginHeader()` 拼进所有头），
  属于**不必要且有风险**的做法，自包含源应只在 API 请求里带 token。

---

## 6. 交付纪律：先建测试源，再覆盖正式源

**本轮用户明确要求**（沙盒与真机环境差异大，沙盒结论不可信）：

1. 用**独立 bookSourceUrl**（如 `https://picaapi.picacomic.com#t84`）新建**测试源**，**不动正式源**；
2. 测试源在真机 App 内跑通：搜索→详情→目录→正文→发现页→面板按钮；
3. `check_source` 测试源 1/1 通过后，才用 LAN `/saveBookSource` **覆盖正式源**
   （LAN 保存同一 bookSourceUrl 会**保留 enabled / customOrder / weight / bookSourceGroup**）；
4. 覆盖后 `GET /getBookSource` 回读做**逐字段 md5 比对**；
5. 最后**删除测试源**。

★ 测试源的**登录态与正式源不共享**（token 按 `getKey()`=bookSourceUrl 存 CacheManager），
测试前必须在测试源身份下重新登录，否则报 `401 unauthorized`。

---

## 7. 顺带实锤的一个通用坑：JS 规则漏了 `<js>` 包裹

`ruleExplore.bookList` 的内容**没有 `<js>…</js>` 包裹** ⇒ Legado 把它当 **CSS 规则**解析 ⇒
`RuleAnalyzer.chompBalanced` 抛 **`后未平衡`** ⇒ 校验器报「**网站失效**」。

- 源码：`app/src/main/java/io/legado/app/model/analyzeRule/RuleAnalyzer.kt:229 / :286`
- 判据：**所有纯 JS 规则必须整体包在 `<js>…</js>` 里**；
- 自检脚本应加一条：JS 规则 `strip()` 后必须 `startswith("<js>") && endswith("</js>")`。
- ⚠ 该错误在 `debug_source` 里**看不出来**（搜索链路正常），只有 `check_source` 跑**发现页**时才暴露。

---

## 8. 本轮附带实锤的其他机制

| 机制 | 实锤结论 |
|---|---|
| **签名过期窗口** | `time` 偏移 ≤300s 正常；≥600s → `400 error 1029 time is not synchronize`（容差 5 分钟） |
| **现签 URL** | `@js:` 表达式每次请求重新求值 ⇒ 签名永不过期；但**规则文本里禁止出现字面 `@js:`**（`AnalyzeRule.splitSourceRule` 会当 JS 规则立即求值），须用 `String.fromCharCode(64,106,115,58)` 拼 |
| **现签 IIFE 必须是单行字符串字面量** | 多行会让 `'...'` 字符串字面量变成语法错误（Node `--check` 能抓到） |
| **ajax 失败不抛异常** | `JsExtensions.ajax` 失败时返回**异常堆栈字符串**（"java.net..."开头）⇒ `JSON.parse` 报 `Unexpected token: j` ⇒ **判据必须先看首字符是否为 `{`** |
| **Official init 接口** | `http://68.183.234.72/init` 返回 `{"status":"ok","addresses":["104.19.53.76"],...}` ⇒ 官方源站 IP 直连用 `dnsIp` 而非改域名 |


---

## 9. ★同一站点「普通浏览能看图、漫画浏览看不了图」的根因（v85 实锤）

**用户症状**：阅读设置里打开「漫画浏览」后正文图片加载失败；关掉漫画浏览、用普通浏览则正常。

**根因（源码级）**：Legado 有**两条图片链路**，对 URL 选项的处理完全不同：

| 模式 | 链路 | dnsIp | headers |
|---|---|---|---|
| 普通浏览 | `BookHelp.fetchImage` → `AnalyzeUrl.getByteArrayAwait()` | ✅ 生效 | ✅ 生效 |
| **漫画浏览** | `MangaVH` → `BookCover.loadManga` → Glide → `OkHttpStreamFetcher`(manga=true) → `AnalyzeUrl.getGlideUrl()` | ❌ **丢弃** | ✅ 生效 |

漫画模式链路（`app/src/main/java/io/legado/app/ui/book/manga/recyclerview/MangaVH.kt:79`）：
`BookCover.loadManga(context, mangaImagePath(imageUrl), ...)` → `ImageLoader.load` → Glide
→ `OkHttpStreamFetcher`（`mangaOption=true`）→ `AnalyzeUrl(...).getGlideUrl()`
→ **只保留 url + headerMap** ⇒ `dnsIp` 选项被丢弃 ⇒ 回落到系统 DNS ⇒ IPv6 优先不可达 ⇒ 15s 超时。

**真机对照实验（LAN /cover 走完整 Glide 链路，含反向验证组）**：

| 组 | 结果 |
|---|---|
| **新格式** `http://<CF-IP><path>` + `{"headers":{"Host":"storage-b.picacomic.com"}}` | ✅ 真实图片 22071B / 0.4s |
| **旧格式** `https://storage-b...` + `{"dnsIp":"..."}`（普通模式能用） | ❌ **占位图（失败）** |
| **反向组** 裸域名（= 漫画模式丢弃 dnsIp 后的等价形态） | ❌ **占位图（失败）** |
| **反向组** IP 但无 Host 头 | ❌ 占位图（失败） |

★ 这正好复现用户症状：普通浏览（dnsIp 生效）能看图，漫画浏览（dnsIp 丢弃）看不了图。

**★ 修复的通用结论（比 v84 更进一步）**：
**图片 URL 必须把「IP 直连能力」直接写进 URL 本身**（`http://<IP><path>` + Host 头），
**不能**依赖 URL 选项里的 `dnsIp` —— 因为只要走 Glide（封面 or 漫画模式），dnsIp 一定被丢。
这样**同一个 URL 在两条链路上都能加载**，不需要按模式分别产出。

v85 实现：`picac_img(media, SRC)` 与 `picac_cover(media, SRC)` 共用 `picac_imgUrl()`，
正文规则改为 `<img src="' + picac_img(x.media, source) + '">`（**外层不再追加 dnsIp**）。

**★ 副作用与注意点**：
- 正文图 URL 里带 `,{"headers":{...}}` ⇒ `BookHelp.getImage(book, src)` 的
  **缓存文件名用 `MD5(src)`**（src 含选项串），与旧缓存文件名不同 ⇒ **旧书正文缓存要清/删书重加**；
- `UrlUtil.getSuffix` 走 `CustomUrl(str).getUrl()`（会先剥掉 `,{...}`）⇒ 文件后缀仍是 `jpg`，不会错；
- **不要再在 `<img src>` 外层套 dnsIp**（会变成双层选项 ⇒ `GSON.fromJsonObject<UrlOption>` 解析失败
  ⇒ 回退裸 URL ⇒ 又超时），这是 v63 的老坑，本轮同源再现。

**★ 排查口诀**：站点「A 模式能看图、B 模式看不了」⇒ 先查 B 模式是不是走 Glide
（封面 / 漫画浏览 / 预览缩略图都是 Glide），Glide 路径 ⇒ URL 必须自带 IP+Host。
