# 方法：聚合搜索站 ID 偏移映射 + 手动验证码登录面板（新天禧小说篇）

> 沉淀日期：2026-11-27 ｜ 来源：www.xtxxs.com（新天禧小说）书源制作
> 关联：[方法-Base64内联搜索页与js完成值返回协议](方法-Base64内联搜索页与js完成值返回协议.md)、[方法-GoEdge盾UA白名单与搜索凭证链](方法-GoEdge盾UA白名单与搜索凭证链.md)、[Legado三个JS环境变量差异与返回值类型铁律](方法-Legado三个JS环境变量差异与返回值类型铁律.md)
> 成品：`examples/新天禧小说_www.xtxxs.com.json`

---

## 〇、站点画像（先记住它长什么样）

| 项 | 结论 |
|---|---|
| 站点 | `www.xtxxs.com` / `www.xtxxs9.com` / `www.tianxixsw.com`（三线路同模板同 ID 空间） |
| 盾 | **GoEdge WAF 图片验证码**（`307 → /WAF/VERIFY/CAPTCHA?info=...`），**只拦桌面 UA，移动 UA 放行** |
| 搜索 | **站点自身 `/search` 已被管理员关闭**：返回 `<script>alert("对不起,管理员已关闭此功能.")</script>` |
| 搜索真实通道 | 首页表单 POST 到 `sososhu.com/?s={{key}}&web=xtxxs`（聚合站），**必须登录，12 次/天/账号** |
| 搜索返回 | 书籍 JSON 先 `json_encode` 再 Base64 内联在 `<script>`：`var books=JSON.parse(d("..."))` |
| 详情 | `og:novel:*` 全字段 + `#info` + `#fmimg` |
| 目录 | `#list #content_1 a`，**分页在 `<select id="indexselect">` 的 option value**，每页 300 章 |
| 正文 | `#booktxt`，章内分页 `_2.html`，**h1 页码用全角括号（1/2）** |
| 登录 | 聚合站需登录；站点本身游客可读 |
| 发布页 | **无**（首页外链的 xintianxixs.com 无响应、shanshanyq.com 是跳转页） |

---

## 一、★★★ 核心发现：聚合搜索站与内容站的书籍 ID 存在固定偏移

### 现象
搜索能出结果，但把搜索结果里的 ID 直接拼到内容站 → **404 或串成完全不同的书**。

实测对照（同一本书）：

| 来源 | ID | 实际书籍 |
|---|---|---|
| sososhu 搜索返回 | `95143466` | 七零：早逝媳妇带龙凤胎去随军 ✅ |
| 内容站 `book/95143466/` | — | **惊鸿影**（完全不同）❌ |
| 内容站 `book/95199021/` | — | 七零：早逝媳妇带龙凤胎去随军 ✅ |
| 内容站 `book/2894/` | — | **404** ❌ |

### 结论
```
内容站ID = 完本神站ID + 55555
完本神站ID = 内容站ID - 55555
```
**14 个样本双向验证全部成立**，含小 ID 边界与大 ID 最新书：

| 完本神站 ID | +55555 | 内容站 | 书名/作者 | 验证 |
|---|---|---|---|---|
| 2894 | 58449 | ✅ | 七零之彪悍女知青/桃花露 | 正向 |
| 8471 | 64026 | ✅ | 电商穿越七零年代/恣悠悠 | 正向 |
| 5698 | 61253 | ✅ | 七零甜妻撩夫记/冬至的柚子 | 正向 |
| 2822 | 58377 | ✅ | 轮回乐园/那一只蚊子 | 正向（小 ID 边界） |
| 24743 | 80298 | ✅ | 遗忘的岁月/姜文君 | 正向 |
| 95143466 | 95199021 | ✅ | 七零：早逝媳妇…/大黑瓜瓜 | 正向 |
| 95433168 | 95488723 | ✅ | 重生九零：和闺蜜摆烂暴富/淦二沟 | **反向** |
| 95492232 | 95547787 | ✅ | 为你，明灯三千/龙叔的狸猫 | 正向（最新书） |

### 通用方法论（比记住 55555 更重要）
1. **先怀疑 ID 空间不一致，不要先怀疑规则**。症状指纹：搜索结果书名/作者/封面/简介全对，但点进去 404 或变成另一本书 ⇒ 一定是 ID 空间问题。
2. **定位偏移量的方法**：找一本在内容站确定存在的书（从站内首页/分类页/站点地图拿 ID），再用同一书名搜索，比较两个 ID，差值就是偏移量。本次 `95199021 - 95143466 = 55555` 一眼可辨。
3. **偏移量必须多方向验证**：只验正向（+55555）不够，必须验**反向**（内容站 ID - 55555 回到聚合站）和小 ID 边界（`2822 → 58377`），否则可能只是巧合。
4. **不消耗配额的取样渠道**：站点地图 `/map/`（一次 500 条书链接）、分类页 `/fenlei/N/1/`、排行榜 `/rank/allvisit/`、作者页 `/author/<名字>/` —— 这些都不走搜索接口。
5. 偏移量在 `ruleSearch.bookList` 的 @js 里做加法即可，**不要改 bookUrl 走别的域名**（会失去内容站的分页/正文结构优势）。

### 代码（ruleSearch.bookList 关键片段）
```javascript
// 结果 url = https://m.wanbenshenzhan.com/{id}/?token=...
// ★ 完本神站 ID + 55555 = 内容站 ID（14/14 样本双向验证）
var idm = String(b.url || '').match(/^https?:\/\/[^\/]+\/(\d+)\//);
var bu = idm
    ? ('https://www.xtxxs9.com/book/' + (parseInt(idm[1], 10) + 55555) + '/')
    : String(b.url || '');
```

---

## 二、★★ 登录面板：用户手动填验证码（不做自动 OCR）

用户明确要求「不用自动过验证码，让用户自己登录就行，像 38 看书网那样」。

### 协议要点（源码级，踩过两个坑）
1. **`loginUrl` 里必须有名为 `login` 的函数**，否则点登录抛：
   `com.script.ScriptException: Function login not implements!!!`
   —— 这是本次第一个报障。自定义函数名（如 `SOS_login`）不算，必须是 `login`。
2. **`login()` 无参时直接 `return true`**，否则会被自动调用走一遍登录流程。
3. **`loginCheckJs` 必须 `return result`**，返回 `undefined` 会让后续搜索页解析 NPE：
   `NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' on a null object reference`
   —— 这是本次第二个报障，排查了很久。
4. **`loginUi` 用 V1 静态 JSON 数组**（E 版唯一可用形态），按钮 `action` 直接写函数名调用。

### 面板行（9 行）
```
手机号 / 密码 / 验证码
🔄 刷新验证码（看图后手填）  ← java.startBrowser 打开 captcha_api 图片
登 录                        ← login(true)
检查登录                     ← checkLogin()
📊 剩余次数                  ← quota()（profile 接口不消耗额度）
📅 签 到                     ← checkin()
登 出                        ← logout()
```

### 关键接口
| 用途 | 接口 | 是否消耗搜索次数 |
|---|---|---|
| 取验证码图 | `GET /?action=captcha_api&t=<rand>`（PNG，**与 PHPSESSID 绑定**） | 否 |
| 登录 | `POST /?action=user_api&act=login` body=`mobile=&password=&captcha=` | 否 |
| 查配额 | `GET /?action=user_api&act=profile` → `searchMax/searchUsed/searchRemaining/signedToday` | **否** |
| 签到 | `POST /?action=user_api&act=sign_in` → `+12经验` | 否（**不解锁搜索次数**） |
| 查登录态 | `GET /?action=user_api&act=me` | 否 |

### 验证码会话绑定（决定性实验）
**验证码与 PHPSESSID 绑定，不是 IP 绑定**：
- 用会话 A 取图 → 换会话 B 提交 ⇒ `验证码已过期，请刷新重试`
- 同一 CookieJar 内取图 → 立即提交 ⇒ 成功

⇒ 所以「刷新验证码」按钮**必须用 `java.startBrowser` 打开**（走 App 的 WebView/CookieJar 通道），不能用 `java.downloadFile` 后再展示，否则会话对不上。

### 验证码响应体是 JSON 里的 BOM 前缀
所有 `user_api` 响应都带 UTF-8 BOM，`JSON.parse` 前必须：
```javascript
String(resp).replace(/^\uFEFF/, '')
```

---

## 三、★ GoEdge WAF：只拦桌面 UA

| UA | 结果 |
|---|---|
| 桌面 Chrome 131 | **307 → WAF 验证码页** |
| 移动 Chrome 131（Android） | **200 真实页面** |
| iPhone Safari | 200 |

⇒ `header` 固定移动 UA 即可，无需过盾 UI。与 [方法-GoEdge盾UA白名单与搜索凭证链](方法-GoEdge盾UA白名单与搜索凭证链.md) 的结论一致（该站同样拦桌面 UA）。

**注意**：连续高频请求会触发 TCP 层 RST/超时（`ConnectException: ENETUNREACH`），需间隔 ≥3 秒。因此 `concurrentRate` 设为 `1/1200`。

---

## 四、★ 正文三形态广告清洗（内联 + 全角伪装）

### 三种形态
| 形态 | 样例 | 位置 |
|---|---|---|
| ① 段落尾部内联 | `一道惊雷从天际闪过。本文搜：微趣小说 weiqubook.com 免费阅读` | 段尾，域名会变（微趣/502TXT…） |
| ② 首行独立 | `手机直接访问:m.wanbentxt.com` | 正文第一行 |
| ③ 末行独立 | `记不住网址，可以百度搜索:【完本神站】` | 正文最后一行 |
| ④ **全角字符伪装** | `卖力挥舞。ｘｉ#ａｎｙｕｋ*ｓ.ｃｏｍ` | 段尾，用全角字母 + 干扰符 `#*|_+-=` 拼域名 |

### 最终正则（ruleContent.content 的 `##` 后半段）
```
本文搜[：:]?\s*[^\s，。]*\s*[\w\-]+\.(?:com|net|cc|org|vip|xyz|top|info)\s*免费阅读
|手机直接访问[：:]?\s*[\w\-\.]+
|记不住网址[，,]?\s*可以百度搜索[：:]?\s*【[^】]*】
|[０-９Ａ-Ｚａ-ｚ][！-～#*|_+\-=`~\^\s\.。]{2,}[．\.。][！-～#*|_+\-=`~\^\s]{0,8}[０-９Ａ-Ｚａ-ｚ]
```

### 全角伪装的构造要点（这条最难写）
- 字符类用**全角区间**：`[０-９Ａ-Ｚａ-ｚ]` = `[\uFF10-\uFF19\uFF21-\uFF3A\uFF41-\uFF5A]`
- 干扰符区间 `[！-～]` = `[\uFF01-\uFF5E]` 覆盖全部全角标点，再并上半角 `#*|_+-=\`~^`
- 首尾必须锚定全角字母数字，中间必须含点（全角 `．` 或半角 `.` 或句号 `。`）
- **不能误伤正常正文**：中文、半角域名 `ABC.com`、正常标点都要原样保留（已逐一验证）

---

## 五、★ 三个必须踩的坑（本次报障复盘）

### 坑 1：`<js>` 返回空字符串 → 搜索页 NPE
`ruleSearch.bookList` 的 `<js>` 在「未登录/次数用完/关键词不合规」时返回 `''`，Legado 拿空结果去 `getClass()` ⇒ NPE。
**修法**：返回 `<div class='bk-empty'></div>` 这类**合法但选择不到目标元素的 HTML**，让后续 `.bk` 选择器安全返回 0 条。

### 坑 2：`tocUrl` 选择器作用域错误 → 目录 0 章
`.chapterlist` 在 `#info` **之外**（位于 `.readbtn` 里），写成 `id.info@class.chapterlist@href` 取不到 ⇒ 规则 fallback 到详情页自身 URL ⇒ 目录解析 0 条。
**修法**：改全局 `class.chapterlist@href`。
**通用教训**：写 `父@子` 前必须先用 jsoup 验证父子关系（`doc.select("#info .chapterlist").size()`），不要凭页面视觉层级猜。

### 坑 3：`nextTocUrl` 命中两个 select → 翻页重复
页面上下各有一个 `<select id="indexselect">`，`id.list@tag.select@tag.option@value` 会返回 **62 个 option**（31×2）⇒ 目录翻页重复请求。
**修法**：`id.list@tag.select.0@tag.option@value`（Legado 用 `.0` 索引，**不能用 `:first`**）。

### 附带发现：h1 页码是全角括号
正文分页判据 `（1/2）` 用**全角括号**，正则必须 `[（(](\d+)\s*\/\s*(\d+)[）)]` 兼容半角，否则永远 NO MATCH ⇒ 要么不翻页、要么末页串到下一章。

---

## 六、双版本验证结果（LT 1122 / E 1125）

| 项 | LT 版（MCP） | E 版（LAN WebSocket） |
|---|---|---|
| check_source | ✅ 1/1 通过 | — |
| 搜索（20 本） | ✅ 全字段有值 | ✅ 同 |
| 详情 | ✅ og 全字段 | ✅ |
| 目录（小书 245 章） | ✅ | ✅ 196 章（去重后） |
| 目录（大书 9176 章） | ✅ **31 页 7341 章** | ✅ **890 章 / 3 页**（95421637） |
| 正文（多页拼接） | ✅ 2 页无缝 | ✅ 2285 字 |
| 正文广告清洗 | ✅ 全清 | ✅ 无广告 |
| 登录面板 | ✅ | ✅ 9 行正常 |

### E 版兼容要点（本次实测）
- `loginUi` V1 静态数组：两版通用 ✅
- `loginUrl` 里 `login()` 函数：两版通用 ✅
- `loginCheckJs` 返回 `result`：两版通用 ✅
- 按钮 `action` 里 `java` 在 E 版被替换为 `SourceLoginJsExtensions`（**可能没有 `longToast`/`removeLoginHeader`**）⇒ 本次所有提示走 `T()` 包装（`longToast` → 失败回退 `toast`），请求走 `AJAX()` 包装（`ajax` → 失败回退 `connect`），两版都通。
- E 版 `saveBook` 的 `origin` 必须与 `bookSourceUrl` 完全一致，否则 `refreshToc` 报「未在数据库找到对应书籍」。

---

## 七、配额与风控（用户明确要求：不主动探测频率）

- 聚合站 **12 次/天/账号**，`searchUsed` 按账号计（**与出口 IP 无关**，沙盒/App/真机共用同一 PHPSESSID 都扣次数）。
- 本次调试把 12 次额度全部用完（用于验证搜索链路 + 3 轮回归），属预期消耗。
- **`profile` / `me` / `sign_in` 都不消耗额度**，做状态检查和签到可以随便调。
- 签到只加经验（+12），**不增加搜索次数**，不要误以为签到能续额度。
- 书源已设 `concurrentRate: "1/1200"`，避免触发 GoEdge WAF 的 TCP 层限频。
- **不要主动压测搜索频率**（用户明确要求），12 次额度本身已是硬限制。

---

## 八、可复用的检查清单（同类「聚合站搜索 + 独立内容站」场景）

1. 站内 `/search` 是否被关闭？看是否返回 `alert("...已关闭...")` 或 404。
2. 首页表单的 `action` 指向哪个聚合站？`site`/`web` 参数值是什么？
3. 聚合站是否需登录？查 `?action=user_api&act=profile` 的返回判断。
4. 搜索结果的结构：静态 `<a>` 还是 Base64 内联 JSON？（后者要用 `d("...")` 正则 + 去反斜杠 + `java.base64Decode`）
5. **搜索结果的 ID 空间是否等于内容站 ID 空间？** 用「已知存在的书」做双向对照，算出偏移量。
6. 偏移量多方向验证：正向 + 反向 + 小 ID 边界 + 最新书。
7. 详情/目录/正文各自的选择器先用 jsoup 验证父子关系与元素数量。
8. 目录分页：`<select>` 有几个？必须只取第 0 个。
9. 正文分页：h1 页码是半角还是全角括号？
10. 正文广告：抓 3+ 个不同章节，收集全部广告形态（含全角伪装），逐条写正则并做「不误伤」验证。
