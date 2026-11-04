# 方法 - OmoFun 发布页多线路视频源（MACCMS 过盾 + 第三方播放器 AES 直链 + 双版本兼容）

> 案例：`fb.omoo.tv` 发布页 → 4 条线路（omofuns / 233dm / 211dm / agekkkk），动漫视频站。
> 成品：`/workspace/omoo_build/OmoFun_fb.omoo.tv.json`（25KB），LT 版 `check_source` 通过，
> E 版真机 `/refreshToc` + `/getBookContent` 实测通过。
> 本文只记**本次首次出现 / 与既有经验不同**的难点，站点结构本身不展开。

---

## 1. ★两类字段的 JS 前缀形态完全不同（最耗时的一坑，debug 连报 4 次语法错）

`AppPattern.JS_PATTERN = <js>([\w\W]*?)</js>|@js:([\w\W]*)`，
`AnalyzeUrl.analyzeJs()` 用 `jsMatcher.group(2) ?: group(1)` 剥离标记后 `evalJS`。
但**不是所有含 JS 的书源字段都走 `analyzeJs()`**：

| 字段 | 执行路径 | 是否剥离标记 | 正确写法 | 写错的报错 |
|---|---|---|---|---|
| `searchUrl` / `exploreUrl` / 任何 URL 规则 | `AnalyzeUrl.initUrl() → analyzeJs()` | ✅ 剥离 | **`@js:` + IIFE**（单行，前缀后紧跟代码） | 裸 IIFE 会被**当 URL 字符串直接发出**（debug 日志 `≡获取成功:(function(){...})()`） |
| `loginCheckJs` | `WebBook.getBookList/getChapterList/...` 直接 `analyzeUrl.evalJS(checkJs, res) as StrResponse` | ❌ 不剥离 | **裸 IIFE**（无任何前缀） | 写 `@js:` → Rhino `在语句前面缺少 ";" (<script-N>#1)`，报错源第 1 行就是 `@js:(...)` |
| `loginUrl` | 登录对话框拼 `$loginJS\n$jsStr` | App 自己剥 `<js>` | `<js>...</js>` | 面板内函数不进 jsLib，`eval_js(url)` 单独调不到（需手动拼 loginUrl + viewName 验证） |
| `ruleContent.content` / `ruleToc.chapterList` / `ruleBookInfo.init` | `AnalyzeRule.getString/getElements` | ✅ 识别 `@js:` | `@js:` + IIFE | 订阅源首行 `//` 无 `@js:` 会被当 XPath（既有经验） |

- **`<js>...</js>` 在 URL 类字段不能用**：Rhino 把剩余 `<` 当 E4X XML 字面量，堆栈出现 `Parser.xmlInitializer`，报 `语法错误 (<script-N>#3)`。
- **`@js:` 后换行也不行**：`@js:\n(function(){...})()` 整串进 compile，报 `在语句前面缺少 ";"`。
- **排查顺序**：看报错的 `Source context` 第 1 行是哪个字段的内容 → 就能定位是「标记没剥」还是「根本不该带标记」，不要两类字段一起改（本次来回改了 4 轮才分清楚）。
- 附带铁律：`loginCheckJs` 必须 `return result`（StrResponse），返回 Boolean/String 直接 ClassCastException（既有经验，本次再次确认）。

## 2. ★MACCMS「系统安全验证」过盾：时间戳 XOR + 纯 JS Latin-1 base64

搜索页 / 分类页偶发 200 + 5193 字节 `系统安全验证 - OmoFun动漫`，
页面内联混淆脚本 `refresh()` 的真实算法：

```
ts = String(Date.now())
key = [0x4e,0x3f,0xa9,0xc2,0x12,0x7d,0x88,0xef,0x55,0xaa,0x0b,0xcd,0xde,0xad,0xbe,0xef]
plain[i] = ts.charCodeAt(i) ^ key[i % 16]        // Latin-1 字节串
token = base64_latin1(plain)
POST {line}/index.php/ajax/verify_check?type=search|show
body = "i=" + encodeURIComponent(token)
headers: Content-Type: application/x-www-form-urlencoded, X-Requested-With: XMLHttpRequest,
         Referer/Origin, UA
→ {"code":1,"msg":"ok"} + Set-Cookie: PHPSESSID=...  → 同域全站放行
```

- **全新会话直接 POST 即可过盾**，不必先访问盾页（实测 clean session 直接 `code:1`）。
- 盾页的 `maccms.aid` 与 type 无关：`search` 页 aid=13、`show` 页 aid=12，但 `type=search` 过盾后 Cookie 对全站（搜索/分类/详情/播放页）生效，无需按 type 分别过。
- **★坑：Rhino 的 `java.base64Encode(byte[])` 会把 byte[] 对象整体字符串化成 `[B@5eab753`**（16 字节 base64 `W0JAN...` = `[B@N...`），`java.hexEncodeToString(byte[])` / `java.base64Decode(byte[])` 同样中招；`java.base64Encode(String)` 又按 **UTF-8** 编码，对含高位字节的 Latin-1 串会膨胀（13B→20B）。
  ⇒ **必须纯 JS 实现 Latin-1 base64**（3 字节→4 字符，`charCodeAt(i)&255`），不能依赖 Java 桥。
- 错误 token 的服务端响应是 `{"code":1003,"msg":"invalid_token"}`（不是 403/验证码），很好判。
- 架构：**过盾统一放 `loginCheckJs`**，只在 `body 含「系统安全验证」且 len<8000` 时触发 `OM_pass`，避免每个请求都 POST；`ruleContent` 里对播放页验证页做一次兜底。
- 站点本身**免登录**（无登录墙），但用户要求"如需登录写检查登录状态按钮" ⇒ 登录面板里做「✅ 检查登录状态（免登录/过盾状态）」，探活 + 过盾 + Toast 三态提示。

## 3. ★第三方播放器 AES 直链：官方 `createSymmetricCrypto(ByteArray,ByteArray)` 绕过 IV 的 UTF-8 膨胀

播放页 `var player_aaaa={"encrypt":1,"url":"%62%61..._2", ...}`，
`player.js` 把 `unescape(url)` 作 `MacPlayer.PlayUrl`，
`/static/player/mp4.js` 拼 iframe：`https://art.v2player.top:8989/player/?url=&dmid=&sid=&nid=&...`，
该页内联 `playData('cipherB64','ivHex32')`，`common.js` 里：

```
key = "ABABEF777999CCCD"   // 混淆字符串拼接还原，16 字节 ASCII
AES/CBC/PKCS7Padding, key=Utf8(key), iv=Hex.parse(ivHex32), data=base64 cipher
→ 明文 = https://v16-tiktokcdn-com.akamaized.net/...video_mp4...
```

- **★官方源码实锤**（`app/help/JsEncodeUtils.kt`）：
  `aesDecodeToString(str,key,transformation,iv)` → `createSymmetricCrypto(transformation, key:String, iv:String)`
  → 内部 **`key.encodeToByteArray()` / `iv.encodeToByteArray()` 按 UTF-8**。
  32 位 hex IV 若传字符串：Kotlin 直接把 32 个 ASCII 当 32 字节 → `IV must be 16 bytes long`；
  即使先 hex→16 字节 Latin-1 字符串，经 Rhino→Java 又被 UTF-8 编码成 20+ 字节 → 同样报错。
  ⇒ **`aesDecodeToString` 系列（4 参 String 重载）无法承载二进制 IV**。
- ✅ 正解 = **ByteArray 重载**：
  ```js
  var keyBytes = java.strToBytes("ABABEF777999CCCD");         // 16B
  var ivBytes  = java.hexDecodeToByteArray(ivHex);            // 16B（E 版实测可用）
  var c = java.createSymmetricCrypto('AES/CBC/PKCS7Padding', keyBytes, ivBytes);
  var u = String(c.decryptStr(cipher));                       // hutool 自己 base64 解码 + UTF-8 出串
  ```
  `c.decrypt(cipherBytes)` 也可（返回 byte[]，但 Rhino 里转字符串又会踩 `[B@` 坑，不推荐）。
- **`c.decryptStr(cipher)` 的字符串重载会让 hutool 自己 base64 解码**，比手动 `base64DecodeToByteArray` 干净。
- **每次请求 cipher/iv 都不同**（带时效签名），必须**播放时现场请求播放器页 + 现场解密**，不能缓存直链。
- 播放器高峰期偶发返回 **16 字节 `<!DOCTYPE html>` 空页** ⇒ `ruleContent` 加 3 次重试（每次 `&_r=ts_n` 破缓存 + 400ms 间隔），E 版实测连续 3 个不同章节全出直链。
- 明文偶发带伪装协议头 `org.h://`（首次 eval 见到，后续正常 `https://`），统一 `if(u.indexOf('org.h://')===0) u='https://'+u.slice(8)`。
- `bookSourceType=4` + `ruleContent.content` 的 `@js:` **直接返回 http mp4 直链**即可播放（与花都动漫/红果短剧形态一致，无需 `downloadFile`/`file://`）。

## 4. ★多线路站各线路「随机混淆类名不同」→ 语义锚点列表规则

发布页 4 条线路：
- `www.omofuns.com` / `cn.211dm.com` / `cn.agekkkk.com` 是同款 MACCMS，但**每套模板的 class 是随机混淆串**：
  `BIaC_ACJijja`（omofuns 首页/搜索）、`daFJ_aFEaJA`（211dm 搜索）……
- `cn.233dm.com` 返回 978 字节 WAF JS 跳转挑战页（`redirect_url()`），**不是可用线路**（测速判活正确标"超时/异常"）。
- 同一本书在**不同线路 hash 不同**（`9a94cfa6...` vs `74a17ef5...`），但 URL 结构一致。
- ⇒ **任何 `class.xxx` / `@css:ul.XXX li` 列表规则换线路即 0 条**（本次实测切到 211dm 后 `列表大小:0`）。
- ✅ 双版本 + 跨线路通吃配方：
  ```
  a[href*=/anime/][data-original][title]          // 语义锚点，与类名无关
  去重 href → 每项 JSON.stringify({name,bookUrl,coverUrl,kind,lastChapter})
  kind/lastChapter 从 a.closest('li').select('span b') 取首尾
  返回 Packages.java.util.ArrayList（见 §5）
  ```
  实测：omofuns 搜索 22 / 211dm 搜索 4 / dayhot 发现 96，三模板全通。
- **相对 URL 自愈**：`bookList.bookUrl` 返回 `/anime/xxx.html`，Legado 按当前请求域拼绝对 URL ⇒ 切线路后书架/目录自动跟随（既有"bookUrl 相对化自愈"经验再次验证）。
- 发布页本身是 obfuscator.io 字符串轮转 + `encodedLinks` 数组（base64|标签），
  在 Rhino 里 `eval` 页面 `<script>` 后直接读 `encodedLinks` 即可（浏览器 DOM 用 stub `window/document` 占位），
  不必还原 `C()`/`X()` 解码函数。

## 5. ★E 版 TocEmptyException 的精确根因与双版本列表协议（用户报障驱动）

**症状**：LT 版全链路正常，E 版 `TocEmptyException: 目录列表为空`。

**E 版源码实锤**（`Luoyacheng/legado-E` `AnalyzeRule.kt`）：
```kotlin
fun getElements(ruleStr: String): List<Any> {
    ... Mode.Js -> evalJS(rule, result) ...
    result?.let { return it as List<Any> }     // ★没有 NativeArray 分支
    return ArrayList()
}
fun getString(...): String {
    if (result is NativeObject) { result = result[sourceRule.rule]?.toString() }  // ★键值直取，无 Mode.Js
    else if (result is LinkedTreeMap<*, *>) { result = result[ruleList.first().rule]?.toString() }
    else { ... Mode.Json -> JsonPath ... }      // ★字符串走 JsonPath
}
```
- LT 版 `getElements` 末尾有 `is NativeArray -> ArrayList<Any>(...)` 显式分支，E 版没有
  ⇒ `@js:` 返回 **Rhino 原生数组 `[]` 或 `NativeArray`** → E 版 `as List<Any>` ClassCastException
  → 上层吞掉 → 空列表 → `TocEmptyException`。
- **★双版本通吃定式（本次最终形态）**：
  ```js
  var out = [];                                  // 先攒 JS 数组
  out.push(JSON.stringify({n:..., u:...}));     // ★每项必须是 JSON 字符串，不是 JS 对象
  var list = new Packages.java.util.ArrayList();
  for (var j=0;j<out.length;j++) list.add(out[j]);   // ★Java List，两版都能 as List<Any>
  return list;
  ```
  字段规则用 `$.n` / `$.u`：E 版字符串走 `Mode.Json → JsonPath`，LT 版同样走 JsonPath。
  **不要** `return out`（JS 数组，E 挂）、**不要** `return JSON.stringify(out)`（整体字符串，两版都当单条）。
- 记忆里「E 版列表条目协议修复：JS 数组勿整体 stringify」与本次结论一致但更精确：
  **逐项 stringify + 整体包 Java ArrayList**，缺一不可。
- **E 版真机验证法**（MCP 只连 LT 时的唯一通道，本次全部跑通）：
  ```
  POST http://<手机IP>:1125/saveBookSource       (单对象 + x-legado-token)
  POST /saveBook                                (bookUrl + origin + type=4)
  GET  /refreshToc?url=&origin=                 → 看是否还 TocEmpty
  GET  /getChapterList?url=&origin=             → 79668B / 219 章
  GET  /getBookContent?url=&origin=&index=N    → 每次换未取过的 index（正文缓存按 bookUrl+chapter）
  ```
  ★E 版 `java.hexDecodeToByteArray` 在封面链路曾报"调用抛异常"（既有经验），
  但**本次 `ruleContent` 里同一 API 实测正常**（3 个章节全出直链）⇒ 该坑限于 `coverDecodeJs`/`imageDecode` 作用域，
  不要一刀切禁用；按作用域实测。

## 6. 登录面板：V1 静态 + viewName 动态文本（发布页运维全套）

- `loginUi` 必须是 **JSON 数组字符串**（V1 静态，E 版唯一可用形态）；
  `viewName` 写 `OM_lineLabel(source,0)` 这类 JS 表达式 → 每次渲染自动重跑（不依赖 `reLoginView`）。
- 13 行：发布页输入框（`key=om_pub`，E 版输入框用 `name` 作存取键）、当前状态（viewName）、
  一键取线、测试延时、**8 个线路按钮（各网站一个，viewName 显示 `⚡241ms`）**、检查登录状态。
- 每个 action 显式传 `java`/`source` 实参（`OM_actSpeed(java,source)`），避开 jsLib 作用域差异。
- 各阶段 Toast：⏳开始 → ✅成功 / ❌失败 / ⚠降级 → ℹ 若按钮文字未刷新请重开面板（`reLoginView` try/catch）。
- 测速：`java.ajaxAll(urls,true)` 并发（两版通吃）+ 三判据（code 200-399 + body>20000 + 非异常堆栈串），
  结果 `source.put('om_spN','⚡241ms')`，最快线路加 ⚡ 并自动切 `om_line`。
- 实测：取线 4 条 / 测速 ⚡241ms、超时、271ms、271ms / 切到 `cn.211dm.com` 后全链路跟随 / 状态检查全通过。

## 7. 搜索节流：只做搜索链路，不做全局限速

- 用户要求"搜索不要过于频繁、避免风控，且不要主动探测搜索访问频率" ⇒ 不压测、不发多余搜索。
- **不设 `concurrentRate`**（全局限速会拖慢 200+ 集目录与正文，书海阁已有教训），
  改为 `searchUrl` 的 `@js:` 内 `source.get('om_search_last')` + `Thread.sleep(3000-Δ)`，
  仅两次搜索之间最多等 3 秒，目录/正文零影响；`check_source` 实测通过无限频误报。
- 搜索结果本身**单页全量**（22/17/4 条），无分页链接 ⇒ 不做 `page` 循环。

## 8. 交付与验证清单（本次实际跑过的）

| 项 | 结果 |
|---|---|
| LT `debug_source` 关键词 斗破 / 一拳超人 / 仙逆 | 搜索 22/17/4 → 详情 → 目录 219/13/165 → mp4 直链 ✅ |
| LT `debug_source ::https://www.omofuns.com/dayhot/` | 发现 96 → 详情 → 目录 364 → mp4 直链 ✅ |
| 切到 `cn.211dm.com` 后全链路 | ✅（语义锚点规则跨模板） |
| `cn.agekkkk.com` 验证页 → 过盾 → 正常搜索页 | 5193B → `code:1` → 51496B ✅ |
| `bookUrlPattern` | 详情 URL 命中 / 搜索页·播放页排除 ✅ |
| 10 个 JS 块 `qjs new Function` 语法 | 全 OK |
| 禁用写法 `:contains()` / `:first-child` / `prevContentUrl` | 全部 0 |
| 登录面板 4 类 action + viewName 拼接作用域 | 全通过 |
| LT `check_source` | 通过 1/1 |
| E 版 `/refreshToc` + `/getChapterList` | 79668B 正常目录，TocEmptyException 消失 ✅ |
| E 版 `/getBookContent` index 0/5/12/30 | 4/4 返回 mp4 直链 ✅ |
| LAN `/saveBookSource` 单对象（25KB） | LT 1122 + E 1125 双端无损落库，`get_source` 回读字节级一致 ✅ |

## 9. 复用清单（换到同类发布页多线路视频站要改什么）

1. 发布页 `encodedLinks` 混淆脚本结构 → 改 `OM_fetchLines` 的 eval 提取与 base64 解码。
2. 盾页 `refresh()` 的 XOR 密钥 / token 生成 → 改 `OM_token`，`verify_check?type=` 按站点实际。
3. `player_aaaa` 字段名 / 播放器 iframe host / `playData` 密钥 → 改 `ruleContent`。
4. 列表语义锚点 `a[href*=/anime/][data-original][title]` → 按目标站详情 URL 形态换。
5. 线路按钮数量（本次 8 位固定）→ 改 `loginUi` 行数与 `OM_saveLines` 上限。
6. 搜索节流 3000ms → 按站点风控松紧调（不要主动压测）。

## 10. 风险与未验证项

- 第三方播放器 `art.v2player.top:8989` 与 CDN 直链均为**短时效签名**，高峰期可能连续 3 次解析失败（已有可读提示 + 重试）；直链本身有 `l=2026110...` 时效参数，**不能加入书架缓存长期复用**。
- `cn.233dm.com` 是 WAF 挑战页，测速会标"超时/异常"，不建议手动切到该线路。
- E 版播放链路（ExoPlayer 实际起播）未在本环境真机点播验证，仅验证到 `/getBookContent` 返回合法 https mp4 URL；LT 版同形态（花都动漫等）已验证可播。
- 站点免登录，登录面板只做线路运维；若未来站点加登录墙，需在 `OM_actCheck` 补齐登录态判据与 `login()` 实现。
