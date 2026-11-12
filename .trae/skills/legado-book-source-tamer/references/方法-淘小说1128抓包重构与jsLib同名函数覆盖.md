# 方法：淘小说 11.2.8 抓包重构与 jsLib/loginUrl 同名函数覆盖

> 蓝本：淘小说 `com.martian.ttbook` v11.2.8（2026-11-12）
> 工具链：ProxyPin 抓包 + MT管理器 APK 静态分析 + LegadoTEAM MCP + LAN web 服务（1122/1125）
> 兼容目标：LegadoTeam(gedoor) + legado-E(Luoyacheng)

---

## 0. 本次交付结论（先看结果）

| 链路 | 接口 | 规则 | 实测 |
|---|---|---|---|
| 搜索 | `/authopt/ty/search_books` | `$.data.bookList` | 10 本，翻页 `page-1` 正常 |
| 详情 | `/tf/book?bid=` | `init=$.data` | 全字段（含 latestChapter / tagList / roleList） |
| 目录 | `/tf/chapter_list?bid=&retry=0` | `$.data.chapterList` | **302 → 免签名 CDN**，463 / 4811 章均正常 |
| 正文 | `/tf/chapter_content?bid=&cid=&autoBuy=true` | `$.data.content` | 完整无乱码，无章内分页 |
| 发现 | `book_rank` / `search_by_category` / `channel_books` / `search_recommend` | `$.data.bookList||$.data.books` | 67 项，10 本/页 |

LT 版 `debug_source` 搜索/发现全链路两次全绿；E 版 `saveBook→refreshToc→getChapterList→getBookContent` 整源集成全绿。

---

## 1. sign 算法：抓包「离线碰撞」定协议，零额外请求

所有请求带 `sign`（32 位大写 HEX）。不要靠猜加密方式，用**已抓到的请求做离线字典碰撞**：

```python
# 112 条 ProxyPin 抓包 URL，全部命中同一构造
pairs = urllib.parse.parse_qsl(query)          # 值自动 URL 解码
pairs = [(k,v) for k,v in pairs if k!='sign']
s = '&'.join(f'{k}={v}' for k,v in sorted(pairs, key=lambda x:x[0]))
sign = hashlib.md5((s + '&key=mibook_123456').encode()).hexdigest().upper()
```

**112/112 全命中**，且 App 内 `java.md5Encode(...)` 复算一致。

三条铁律：
1. **按 key 字典序排序**（不是 URL 里的原始顺序）。抓包 URL 里业务参数在前、设备参数在后，但签名串是排序后的；只有恰好已按字典序排列的 8 条才会「原始顺序也命中」，别被这 8 条骗了。
2. **`key=mibook_123456` 追加在末尾**，不参与排序（若业务参数本身含 `key`，不要重复追加）。
3. 签名用的是**解码后的明文值**（`category=游戏` 而非 `%E6%B8%B8%E6%88%8F`，`model=MI 8` 而非 `MI%208`）；URL 里才 `encodeURIComponent`。

**方法论价值**：逆向签名优先「抓包样本离线碰撞」，而不是读加固壳的 SO。本 APK 是 Epic/爱加密加固（主 dex 只有 2 个壳类，真实代码在 `assets/cxapkDex/*.Epic`），静态逆向成本极高，而 112 条真实样本已经把算法完全确定下来。**碰撞命中率 100% 才写规则，99% 都要继续找第二种构造**。

---

## 2. ★新坑（本次首次遇到）：凭证校验「按接口分层」，不能一次实验下结论

初步实验：「伪造 uid/token + 正确 sign」打 `/book_mall/book_rank` → `errcode:0`，
于是差点下结论「游客凭证不绑定、可以自造」。但换到搜索接口立刻打脸：

| 组 | 接口 | 凭证 | sign | 结果 |
|---|---|---|---|---|
| A | `/book_mall/book_rank` | 伪造 | 正确 | `errcode:0` ✅ |
| B | `/book_mall/book_rank` | 真实 | **错误** | `errcode:201 Invalid sign` ❌ |
| C | `/authopt/ty/search_books` | **伪造** | 正确 | `errcode:205 Invalid token xxx with uid xxx` ❌ |
| D | `/authopt/ty/search_books` | 真实 | 正确 | `errcode:0` ✅ |

**结论**：榜单 / 详情 / 目录 / 正文只校验 `sign`，`token↔uid` 随便填；
**唯独搜索接口额外校验 `token↔uid` 是否成对**。

→ 书源必须使用**真机抓包到的那组配对凭证**，禁止随机生成 / 自造 UUID。
→ 这是「对照实验必须含反向验证组」的又一次胜利：B 组（错 sign）证明服务端确实在验签，
   C 组（伪造凭证搜索失败）证明结论不能从榜单外推到搜索。

**通用警示**：同一 host 下不同 path 的鉴权强度可以完全不同。逆向时**每个接口族都要单独做一次凭证对照**，
至少覆盖「搜索」和「非搜索」两类。

---

## 3. ★新坑：目录接口从「直出 JSON」改成「302 → 免签名 CDN」

旧源（Yiove 🍮淘小说 v8.1.9）把 `/tf/chapter_list` 当直出 `$.data.chapterList`，
catch 分支还兜底 `tfbook-1251592799.file.myqcloud.com/chapters/bid=xxx.json`。

11.2.8 实测：
- `/tf/chapter_list?...&sign=...` → **HTTP 302**，`Location: http://scdn.taoyuewenhua.net/app/chapters/{bid}.json`
- CDN 返回纯静态 JSON（gzip，901KB / 4064 章），**无 sign、无设备参数**
- 旧 myqcloud 兜底 → **HTTP 403 AccessDenied，已废弃，必须删掉**
- Legado 网络栈（LT 和 E 都）**自动跟随 302**，`debug_source` 日志会打
  `≡检测到重定向(302) ┌重定向后地址 └http://scdn...` —— 看到这行就是正常的，不是错误

**覆盖率实测**：对 12 个不同 CP 前缀的 bid（`yw_` / `zl_` / `judian_` / `wd_` / `fengdu_` / `hy_` / `gaishi_` / `siji_`）
逐个请求 CDN，`"chapterList"` 全命中。所以目录可以稳定走「签名 API → 302 → CDN」，无需为不同书源分支。

**另一个反直觉点**：极简参数（只 `bid` + `t` + `sign`）打 `/tf/chapter_list` 返回
`{"errcode":202,"errmsg":"Empty app id"}` —— 302 跳转本身也要求带**完整 appid 设备参数集**。
所以 `ruleBookInfo.tocUrl` 不能省参数，必须走 `TX_dev()` 全套。

---

## 4. ★★新坑（最隐蔽）：jsLib 与 loginUrl 同名函数互相覆盖

**症状**：`🔍 检查登录状态` 按钮判定「异常」，但 `debug_source` 全链路正常、
`java.ajax('/auth/account.do?...')` 手工请求也 200。

**根因**：`jsLib` 里定义了 `function TX_host(sv)`（读 `source.get('txApiHost')` 取当前 API 线路），
`loginUrl` 里又定义了 `function TX_host(u)`（从 URL 里正则抠 host 用于按钮文案）。
`SourceLoginDialog` 的求值方式是 `source.evalJS("$loginJS\n$jsStr")`，而 `eval_js` 预演里
`eval(loginUrl)` 后，**后定义的那个覆盖了共享 scope 里的同名函数**。
于是 `TX_checkLogin()` 调 `TX_host()` 时命中「抠 host」版本 → 无参传入 → 返回 `'undefined'`
→ 拼出 `undefined/auth/account.do?...` → 判活失败。

**修法（生产定式）**：
- `jsLib` 与 `loginUrl` 的**所有函数名加命名空间前缀区分**，例如
  `TX_host(sv)`（jsLib，取线路） vs `TX_of(u)`（面板，抠 host）。
- 落库前必须 grep：把 `jsLib` 里所有 `function NAME` 与 `loginUrl` 里所有 `function NAME`
  取交集，**交集非空即拒绝发布**。
- 面板函数里需要「当前 API 线路」时**不要复用 jsLib 同名函数**，直接
  `TX_gv('txApiHost', DEFAULT)` 读 `source` 变量，语义最清楚。

**为什么以前没踩到**：以往书源要么只有 jsLib 没有复杂 loginUrl，要么面板函数都加了站点前缀
（`PN_*` / `H1*` / `FQ_*`）。本次两边都用了 `TX_` 前缀却没做函数名去重。

**排查手法**：在 `eval_js` 里 `eval(String(source.getLoginUrl()))` 后逐个 `typeof 函数名` 打印，
再打印 `viewName` 求值结果，能一次定位「函数存在但返回值不对」这类覆盖问题。

---

## 5. ★新坑：站点判活不能用「根路径 + 长度阈值」

面板测速首版用 `GET https://tybook.taoyuewenhua.net/` + `body.length < 40 → 内容异常`。
实测根路径返回 **恰好 39 字节**：

```json
{"errcode":202,"errmsg":"Empty app id"}
```

站点完全健康，只是没带参数。于是正常 API 线路被标成「✗ 内容异常」。

**修法**：判活按线路类型走**该线路真实可用的业务路径**，并用**内容特征**而非长度：

| 线路类型 | 判活 URL | 成功判据 |
|---|---|---|
| API 域 | 现算 sign 的 `/auth/account.do` | `"errcode":0` |
| CDN 域 | 免签名 `/app/chapters/{已知bid}.json` | `"chapterList"` |
| 官方落地页 | 根路径 HTML | `length > 500` |

`java.connect` 失败时返回异常堆栈串而非抛异常（`runCatching` 包 body），仍须显式排除
`Exception` / `timeout`。**测速绝不调用搜索接口**（用户明确要求不主动探测搜索频率），
只打账户探针 / 静态目录 / 落地页。

另一条：`https://app.taoyuewenhua.net` 在 manifest 里是 `assetlinks.json` 域（`android:autoVerify`），
**根路径实测 403**，不能作为 API 备选线路放进池子误导用户。APK 资源里出现的域名
≠ 可用于业务的域名，必须逐个实测。

---

## 6. 面板「各阶段 Toast」与 ms 回填的生产配方

V1 静态 `loginUi`（E 版唯一可用形态）+ `viewName` JS 表达式：

```json
{"name":"路线1","type":"button","action":"TX_switch(1)","viewName":"TX_lineBtn(1)",
 "style":{"layout_flexBasisPercent":0.48,"layout_flexGrow":1}}
```

- **`viewName` 为 JS 表达式时求值结果「原样显示、不剥引号」**（源码 `normalizeJsResult`）⇒
  函数返回**纯文本**，禁止自带外层单引号。只有 3..19 长度且首尾单引号的**静态字面量**才被剥引号。
- `viewName` 求值环境不保证注入 `java` ⇒ 视图函数只读 `source`，不要调 `java.*`。
- action 环境 `java` 是 `SourceLoginJsExtensions`；`java.get/put` 与 `source.get/put` **同一键空间**（实测）。
- `loginUrl` 必须有 `function login(){return 'ok';}`，否则点右上角 √ 抛 `Function login not implements!!!`。
- 测速后 `source.put('txDelay'+i, ms+'ms')` → `java.reLoginView(false)`（try/catch 兜底）→
  按钮名变成 `● tybook.taoyuewenhua.net ⚡42ms`。
- **分阶段 Toast**：开始 / 中间（每条线路一条） / 写入 / 完成 / 失败兜底，全部走
  `java.longToast` → `java.toast` 双保险。
- ★**排查完必须清空诊断桩**：面板按钮会把 `txFound/txDelay/txLine/txLoginCheck` 写进 source 变量，
  这些会随书源一起留着。交付前逐个 `source.put(k,'')` 还原出厂态，再重存正式版。

---

## 7. 双版本兼容（LT + E）本源具体做法

| 风险点 | 本源做法 |
|---|---|
| E 版 `getElements` 无 `NativeArray` 分支 → `ClassCastException` | 列表全部用**纯 JsonPath** `$.data.bookList`（`AnalyzeByJSonPath.getList()` 返回 Java `List`），**不写 `@js` 返回 JS 数组** |
| E 版 `getString` 对 `NativeObject` 只做键值直取 | 字段规则用 `$.xxx` / `{{}}`，不依赖 JS 对象走 `Mode.Js` |
| jsLib 共享 scope 无 `java/book/source/result/baseUrl` | jsLib **只放纯函数骨架**，一律 `function X(jv, sv, ...)` 由规则 `@js` 显式传 `java, source` |
| E 版登录面板只认 V1 静态 | `loginUi` = JSON 数组字符串；不用 V2 / `<js>` 动态 |
| `loginCheckJs` 必须返回 `StrResponse` | 本源游客态无需登录，`loginCheckJs` 留空（不写比写错安全） |
| E 版 `java.post(url,body,null)` 抛 NPE | 本源全 GET，不涉及 |

**E 版无 MCP 的验证通道**（web 服务 1125，免令牌）：
```
POST /saveBookSource            (单对象，整体替换)
POST /saveBook                  {bookUrl, origin, name, type}
GET  /refreshToc?url=&origin=   → 确认 302→CDN 的 baseUrl 被识别
GET  /getChapterList?url=       → 463 章 / 532KB
GET  /getBookContent?url=&index=0  → 正文
```
E 版 `/searchBook` `/getExplore` **未实现**（返回字面路由名），故搜索/发现的 E 版验证只能靠
「LT 版全绿 + 静态审计（纯 JsonPath 列表两版分支一致）」保证，交付时要如实说明。

---

## 8. 交付纪律（本次复用有效）

1. 大文件（45KB）走 `POST http://192.168.10.7:1122/saveBookSource` + 头 `x-legado-token`，
   **单对象 JSON**（不是数组）→ `isSuccess:true`，`get_source` 回读字段一致。
2. `debug_source`：`裸关键词`=搜索、`::签名URL`=发现页、`裸详情URL`=详情。
   ★发现页不能塞无签名裸 URL（会返回 `errcode:201` 导致「未获取到书籍」的假阴性），
   必须用 `@js` 现算签名的完整 URL。
3. `eval_js` 带 `url` 参数可绑定**已保存书源**的运行时身份（含 jsLib），
   用来预演规则函数、面板函数，纯计算零网络请求。
4. `bookUrlPattern` 用 Python `re` 先跑正反例再落库；组合符 `||` 两侧不加空格（本源
   `$.data.bookList||$.data.books` 合规）。

---

## 9. 站点事实清单（2026-11-12 实测，供后续维护）

- 主 API：`https://tybook.taoyuewenhua.net`；目录 CDN：`https://scdn.taoyuewenhua.net`（http/https 都 200）
- 官方落地页：`https://m.taoyuewenhua.com/`（200 / 7069B，无线路跳转，**不是发布页/多线路轮换站**）
- 设备 UA = `okhttp/5.1.0`（11.2.8 抓包一致；旧源用 `okhttp/3.12.1`）
- `t` **无时效校验**：2022 年旧时间戳 / 未来时间戳 / 当前时间戳三组均 `errcode:0`；
  但规则仍每次用 `Date.now()`，避免日志侧异常
- 游客态 `/auth/account.do` 返回 `isVip:false`，**全链路无需登录**
- 榜单 `brtype`：100 推荐 / 110 完本 / 10 人气 / 80 热搜 / 20 收藏 / 30 阅读；
  `ctype`：1 男 / 2 女（来自 `/public/mioptions` 的 `bookRankTabs` / `bookMallTabs`）
- 分类 `categoryId`、标签 `tags`、`from`（2/5/13）、`mcid`/`seed` 均以抓包与旧源真实参数为准
- 发现页**不写死页码上限**：`page` 由 Legado 递增，终止靠站点返回空 / 内容重复
- 搜索有 `concurrentRate=1/1500` 温和护栏；未主动做过任何频率探测

---

## 10. 【v2 增补 261112】发现页改 select 切 5 频道 + 完善发现列表

用户追加要求原话「发现改成select切换频道男女完结新书阅文好书 / 增加完善发现列表」。

### 频道映射（不能臆造，从站点配置接口取）
`/public/mioptions` 的 `bookMallTabs` 实锤：
`男生 tid=1 / 女生 tid=2 / 完结 tid=5 / 新书 tid=6 / 阅文好书 tid=4`
（另有 `发现 tid=0`、`漫剧 tid=7`，用户没要求故不收）。
`bookRankTabs` 实锤 brtype：`100 推荐 / 110 完本 / 10 人气 / 80 热搜 / 20 收藏 / 30 阅读`。

### 三种接口的分工（逐个实测过，别混用）
| 接口 | 返回结构 | 能否翻页 | 用途 |
|---|---|---|---|
| `/authopt/book_mall?tid=&ctype=&count=&seed=` | `data.channelList[].bookList`（**嵌套多模块**） | ❌ `page>=1` 返回非 JSON | 只用来**挖各频道真实 mcid/标题**，不做发现项 |
| `/book_mall/channel_books?mcid=&page=&pageSize=` | `data.bookList` | ✅ page 递增首本不同 | 各频道「精选模块」可翻页项 |
| `/book_mall/book_rank?brtype=&ctype=` | `data.bookList` | ✅ | 各频道排行榜 |
| `/ty/search_by_category` | `data.bookList` | ✅ | 分类 / 标签 |
| `/authopt/search_recommend` | `data.books` | — | 全站搜索发现（`ruleExplore.bookList` 用 `\|\|` 兼容） |

★**`channel_books` 必须带 `page`/`pageSize`**：漏了返回 `errcode:9001` 且 `bookList` 空，
极易误判成「mcid 无效」。补上参数后 17/19 个 mcid 全部 `errcode:0` 出 10 本
（`男生 -1000010` 异常不收）。**负数 mcid 是合法的**（`-1000006/-1000005/-1000016/-1000004`）。

### ★新坑：`tags` 搜索只认站点真实题材标签
按语义自造的「甜宠/马甲/团宠/萌宝/女强/王妃/嫡女/皇后/农家女/白月光/破镜重圆/
名著/神作/经典/完结/高分/新书/连载」实测**全部 0 本**，
而「末世/系统/穿越/重生/无敌/签到/爽文/打脸/赘婿/战神/神医/奶爸/脑洞/网游/同人/
无限流/种田/都市」freeType=1 下 **18/18 全出 10 本**；
freeType=2（女生）实测出书的是「重生/穿越/年代/娱乐圈/系统/爽文/种田」。
→ **铁律：发现页标签名一律取站点自身返回的 `tagList` 值，禁止按语义起名字**。
（与青橙 v7.1「发现页标题一律取站点 displayName，别按返回首本书名起」同源。）
→ 「完结/新书/阅文好书」是**书城频道**不是题材，标签别写这三个词。

### 动态 exploreUrl 的生产配方（LT + E 双版通吃）
```
exploreUrl = "@js:\n(function(){ ... return JSON.stringify(out); })()"
```
- **必须 `JSON.stringify(out)`**（`BookSourceExtensions.exploreKinds()` 用 `isJsonArray()` 判断，
  返回 JS 对象数组会 `toString()` 成 `[object Object]` → 「发现规则为空」）。
- **返回的是「类别数组」不是「书列表」**，`ruleExplore.bookList` 仍保持纯 JsonPath
  `$.data.bookList||$.data.books`，两版 `getElements` 分支一致，零兼容风险。
- select 行：
  `{title:'频道',type:'select',chars:NAMES,default:'男生',action:"...java.refreshExplore();..."}`
  - 读取选中值：`infoMap['频道']` 优先 → `result.get('频道')` 兜底 → 都没有则**保持原频道不写 undefined**；
  - 写 `java.put('txChannel', v)` + `java.toast('✅ 已切换到频道：'+v)`；
  - **`java.refreshExplore()` 是关键**（清 sourceKinds + aCache 两级缓存并重绘，
    只 `reUiView` 切了不刷新）；E 版无 `refreshExplore` 时 try/catch 退 `java.reUiView(true)`。
  - 求值端 `infoMap` 优先 / `java.get('txChannel')` 兜底，缺 infoMap 的版本也能用。
- 每个发现项的 `url` 仍是 `"@js:\nTX_explore(java, source, path, extra, page);"`，
  `page` 由 Legado 递增，**不写死页码上限**；终止靠站点返回空 / 内容重复。
- 分组标题行用 `type:'button'` + `url:''` + `layout_flexBasisPercent:1,layout_wrapBefore:true`
  （`type:'button'`+空 url 不进分类 Tab 栏）。
- ★**动态 JS 别在 Python 里多层拼接**：本次首版把 `'...'+JSON.stringify(...)+'...'` 跨行拼
  导致 `SyntaxError: unterminated string literal`。改成**独立 `.js` 模板文件 + 占位符替换**
  （`__CH_CFG__` → `json.dumps(CH_CFG)`），一层替换零转义，一次构建通过。

### v2 终态与验证
| 频道 | 模块 | 榜单 | 分类 | 标签 | 总行数 | 可翻页 url 项 |
|---|---|---|---|---|---|---|
| 男生 | 2 | 6 | 12 | 18 | 46 | 39 |
| 女生 | 2 | 6 | 9 | 7 | 41 | 34 |
| 完结 | 4 | 5 | 6 | 10 | 32 | 25 |
| 新书 | 4 | 4 | 6 | 10 | 31 | 24 |
| 阅文好书 | 6 | 4 | 6 | 10 | 33 | 26 |

- `eval_js` 逐个写 `txChannel` 后 eval 整段 `@js`，5 频道各返回合法 JSON 数组、各含 1 个 select。
- `check_source` **1/1 通过**（动态 exploreUrl 也能过校验器）。
- `debug_source ::签名URL`：**男生**「推荐榜」10本→1310章→正文全绿；**女生**「推荐榜」10本→1158章→正文全绿。
- 轻量抽查 10 组（5 频道分类/榜单各 1）**10/10 出书**；翻页 page2 首本不同（真翻页）。
- E 版换一本未缓存的书 `yw_17415658605564304` 整源集成：`refreshToc` 识别 302→CDN、
  `getChapterList` 1.32MB/1158 章、`getBookContent(index=3)` 正文完整。
- LT/E 双版 `POST /saveBookSource` 落库 + `getBookSource` 回读 `exploreUrl` 字节级一致。
