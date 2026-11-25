# 方法：书海阁 SSR 站书源制作与规则语法四坑

> 沉淀日期：2026-11-04　｜　最近更新：2026-11-25（v3 二次改版：API 断供 / 正文回滚）　｜　蓝本：`book.washai.net`（书海阁）
> 适用：全站 SSR 服务端渲染 / 无 form 搜索 / 详情与目录分离 / 目录 100 章一页且分页 URL 双形态 / 正文页恒含隐藏 VIP 面板 / 需兼容 legado-E 的小说站
> 关联：[书源规则易错点](书源规则易错点.md)、[方法-Legado三个JS环境变量差异与返回值类型铁律](方法-Legado三个JS环境变量差异与返回值类型铁律.md)、[方法-限速器与测速提速](方法-限速器与测速提速.md)、[方法-书源交付质量闭环](方法-书源交付质量闭环.md)

---

## 0. 一句话

SSR 站不要去找 JSON API：`?k=` 搜索页、分类页、排行页、目录页、正文页全都是服务端直出完整 HTML，CSS 选择器一把梭；四个真正的坑全在 **Legado 规则语法与站点隐藏 DOM**，不在网络层。

---

## 一、站点契约（实测 2026-11-04）

| 项 | 结论 |
|---|---|
| 编码 / 防护 | UTF-8；Cloudflare（首页 `server: cloudflare`，`set-cookie: novel_presence_device_id`）；`robots.txt Allow: /` |
| 渲染 | 全站 SSR。`go-novel-seo-rendered` meta；JS 只是渐进增强（换一批 / 翻页走 `/book/searchByPage` 但不影响首屏） |
| 搜索 | **页面无 `<form>`**。站点 `common.js` 的 `searchByK()` 明确 `window.location.href='/book/bookclass.html?k='+encodeURIComponent(keyword)` ⇒ `searchUrl="/book/bookclass.html?k={{key}}"`，SSR 直出 `#bookList` |
| 备用 API | `/book/searchByPage`（分类/首页换一批）、`/book/listRank`、`/friendLink/listIndexLink`（返回 400 无效）。**不要引入 API**：多一层风控面，还得带 `X-Browser-Token` / `X-Requested-With` |
| 登录 | 游客可读搜索·详情·目录·正文。《网游之纵横天下》末章（大结局）与另一本后期章节实测 `needBuy=false` + `readChapterAppendBody` 有 2800~3900 字正文 ⇒ **无需登录，不写登录 UI / 登录状态按钮** |
| 发布页 | 首页/详情/页脚无「发布页/备用/网址/线路/镜像」字样；`washai.net` / `www` / `m` 三个根域 DNS 均无记录；sitemap 仅 `book.washai.net` ⇒ **无发布页，不写线路管理面板** |

### 页面形态与 URL

```
详情   /book/<bid>.html                       #bookName #bookAuthor #bookCoverImg
                                             #bookCatBadge #bookWordCount
                                             #bookLastUpdateTime #lastIndexLink
                                             #allIndexLink（★没有章节列表）
  │  tocUrl = id.allIndexLink@href
  ▼
目录   /book/indexList-<bid>.html            第 1 页
      /book/indexList/<bid>/<N>.html        第 2 页起（★两种 URL 形态）
      <ul id="bookIndexList"> 每页 100 个 <li data-index-id>
      <div class="indexPager" data-page="2" data-total="1173">
        <a class="pgBtn">上一页</a><a class="pgBtn">下一页</a>   ← 第 2 页起两个都有
  │
  ▼
正文   /book/<bid>/<cid>.html
      #showReading > section.readChapterPrimaryBlock > div.readChapterAppendBody（<p> 段落）
      flipPageProgress = 1/1（无章内分页）
```

---

## 二、四坑（全部实测复现 + 定案）

### 坑 1★ 详情页「SEO 套话简介」会覆盖搜索结果真简介 → 故意不写 `intro`

- 搜索卡片 `p.classBookDesc` 是**真简介**（「失落叶网游三部曲之纵横天下…」）。
- 详情页 `#bookDesc` 是站方生成的 SEO 套话（「《X》是 Y 创作的小说，本站提供 X 最新章节及全文阅读。最新章节为《Z》，更新于…」），毫无阅读价值。
- 源码 `BookInfo.kt:123-132`：

```kotlin
val intro = analyzeRule.getString(infoRule.intro)
...
HtmlFormatter.formatIntro(intro).let {
    if (it.isNotEmpty()) book.intro = it   // ★只在非空时写入
}
```

⇒ **`ruleBookInfo.intro` 留空不会清空 book.intro**，搜索阶段取到的真简介会保留进书架。
debug_source 日志特征：详情页「┌获取简介 └」为空，但书架简介仍是真简介——这是**设计**不是故障。

> 通用配方：详情页简介是 SEO 模板 / 广告 / 空时，`ruleBookInfo.intro` 一律不写；只有详情页简介确实优于列表简介时才写。

### 坑 2★★★ Default 规则的 `[...]` 是数组索引语法，不是 CSS 属性选择器

- 部分书目录第 1 页混有 **卷标题行** `<li class="catalogVolumeHeading"><h4>第一卷：太虚清修</h4></li>`（无 `<a>`）。
- 单纯 `id.bookIndexList@tag.li` → debug 报 `⇒目录0未获取到url,使用baseUrl替代`，产生幽灵章节（列表 101 条 / 总章数虚高）。
- 想筛掉写 `id.bookIndexList@tag.li[data-index-id]` → **`└列表大小:0` → `TocEmptyException: 目录列表为空`**。
- **对照实验（决定性）**：同一 HTML 在 App Rhino 里 `org.jsoup.Jsoup.parse(h).select('#bookIndexList li[data-index-id]')` = **100 条**；`li:has(a)` / `li:not(.catalogVolumeHeading)` 也都 100 条 ⇒ jsoup 本身没问题，是 Legado **Default 规则解析器**把 `[data-index-id]` 当成了索引筛选。
  官方文档原文：「格式如 `[index,index,...]` 或 `[!index,index,...]`」「区间 `[start:end:step]`」「允许索引作为 @ 分段后每个部分的首规则」。

**两条正解：**

```
① 属性选择器必须显式 @css: 前缀
   "chapterList": "@css:#bookIndexList li[data-index-id]"

② 更稳（两版 List 协议都通，推荐）：直接选 a 元素
   "chapterList": "id.bookIndexList@tag.li@tag.a"
   "chapterName": "text##\s*\[[^\]]*\]$"     // 去掉 [免费] 尾巴
   "chapterUrl":  "href"
```
卷标题 `li` 里没有 `<a>`，自动被排除；`getElements` 返回 `List<Any>`（不是 NativeArray），**legado-E 也兼容**。

### 坑 3★★★ `##正则##替换` 与 `||` 组合符混写，替换段会吞掉后半段规则

想让分类卡与榜单卡共用 `wordCount`，写了：

```
"wordCount": "class.classBookMeta@text##.*?·\s*([^\s]+)\s*$##$1||class.rankCardMeta@text##.*?·\s*([^\s]+)\s*$##$1"
```

debug 实测输出：

```
┌获取字数
└5767.98万字||class.rankCardMeta@text
```

即第一支的「替换内容」把 `||` 之后整段当成替换文本的一部分输出了。`RuleAnalyzer` 先按 `##` 切 replaceRegex / 替换内容，替换内容里的 `||` 不再被当组合符切分。

**对照（正常工作）**：`##` 只出现在整个组合规则**最后一支之后**时没问题，例如

```
"author": "class.classBookAuthor@tag.a@text||class.rankCardAuthor@tag.a@text##^榜单第[一二三四五六七八九十\d]+$"
```

（用于清掉榜单 type=1/3 首本站方占位数据「榜单第一」；实测 4 个榜单各 30 本，只有 type=1/3 各 1 条命中。）

**正解：需要「多模板 + 正则清理」时改 `@js:`，从 result（jsoup Element）双分支取值**

```js
@js:(function(){
  var t='';
  try{
    var e=result;
    var x=e.select('p.classBookMeta');
    if(x.size()===0) x=e.select('p.rankCardMeta');
    if(x.size()>0) t=String(x.get(0).text());
  }catch(err){}
  var m=t.match(/·\s*([^\s]+)\s*$/);
  return m?m[1]:'';
})()
```
实测分类页 `5767.98万字`、榜单页 `507.26万字`，与详情页 `471.46万字` 各分支一致。

> 铁律：**`##` 只能出现在整个 `||`/`&&` 组合规则的最后一支之后**；否则改 `@js:`。

### 坑 4★★★ 正文页恒含「隐藏 VIP 购买面板」，大容器选择器必污染正文

```
<div class="txtwrap" id="readPanel">
  <div id="showReading" class="readBox">
    <section class="readChapterAppendBlock readChapterPrimaryBlock" ...>
      <div class="readChapterAppendBody"><p>…</p>…</div>   ← 真正文
    </section>
  </div>
  <div class="txtwrap is-initially-hidden" id="vipPanel">
    <div id="showBooking" class="orderBox">
      <h3>此章为VIP章节，需要订阅后才能继续阅读</h3> …购买…
    </div>
  </div>
</div>
```

- `id.readPanel@html` 会把「此章为VIP章节，需要订阅」一起带进正文，**即使 `needBuy=false` 游客能读**（面板只是 `is-initially-hidden` 隐藏，DOM 仍在）。
- 定案：`id.showReading@class.readChapterAppendBody@html##<script[\s\S]*?</script>|<style[\s\S]*?</style>`
- 实测 `--URL` 打《网游之纵横天下》最后一章（大结局）正文完整 3854 字、无购买文案。
- 无章内分页（页面 `flipPageProgress=1/1`）；「下一章」按钮是独立章节 URL 且已被目录覆盖 ⇒ **不写 `nextContentUrl`**，防止串章。

> 通用判别法：正文页同时出现「阅读容器」与「订阅/购买/登录容器」时，先查 `needBuy` 字段与容器 class（`is-initially-hidden` / `hidden`），再决定选择器深度；「页面里存在 VIP 面板」≠「需要登录」。

### 附：全局 `concurrentRate` 会拖慢分页目录 → debug 假超时

`concurrentRate="1/2000"` 是**整源全局**限速（`ConcurrentRateLimiter(source)` 按 `source.getKey()` 记窗口，`AnalyzeUrl.getStrResponseAwait` 每个请求都 `withLimit`），不是只作用于搜索。`nextTocUrl` 串行翻 23 页 ⇒ 23×2s ≈ 46s，加详情/正文/RTT，`debug_source ++URL` 实测 60.0s `InterruptedIOException: timeout`。

- 判据：日志出现 `◇目录总页数:N` 前有一段 ≈(N−1)×间隔 的静默 = 限速等待，不是规则错。
- 应对：① `timeoutSec` 给 180~300（本次 23 页实测 56s 全绿）；② 按「不要频繁搜索」的本意把节流做在**搜索链路**（searchUrl 的 @js 时间戳门槛），目录/正文不受拖累；③ 折中 `1/600~1/1000`。
- `skipRateLimit=true` 只在 `AnalyzeUrl.getStrResponseAwait` 内部签名 / `java.ajaxAll(urls,true)` 可用，普通书源 URL 规则**无法**通过 URL 选项跳过书级限速。

---

## 三、目录分页（`nextTocUrl`）定案

第 2 页起 `a.pgBtn` 有「上一页」「下一页」**两个**，直接取第一个会回环。必须按文案过滤，且末页 `return null`（源码级铁律见 [legado-rule-mechanism-gotchas](/topics/legado-rule-mechanism-gotchas.md) ⑨）。

```js
@js:(function(){
var h='';try{h=String(src||'');}catch(e){}
if(h.indexOf('pgBtn')<0){try{h=String(result||'');}catch(e2){}}
var u=null;
try{var d=org.jsoup.Jsoup.parse(h);var a=d.select('a.pgBtn');
for(var i=0;i<a.size();i++){
  if(String(a.get(i).text()).indexOf('\u4e0b\u4e00\u9875')>=0){
    var x=String(a.get(i).attr('href'));if(x){u=x;break;}
  }
}}catch(e3){}
if(!u){var m=h.match(/href="([^"]+)"[^>]*>\u4e0b\u4e00\u9875</);if(m)u=m[1];}
return u||null;
})()
```

要点：
- `\u4e0b\u4e00\u9875` = 「下一页」，用码点写法避开书源 JSON 传输层中文转义问题；
- `src` 优先（AnalyzeRule 内容环境绑定 `src` = 原始 HTML 字符串），`result` 兜底（某些版本 nextTocUrl 的 result 是 String）；
- jsoup `select('a.pgBtn')` + 文案过滤比正则稳；末页无「下一页」⇒ `u=null` ⇒ `return null` 干净终止；
- **只返回 1 个 URL**（返回 ≥2 会走 `mapAsync` 并发分支导致章节乱序）。

实测：《网游之纵横天下》12 页 1173 章、《仙界闭关小能手》23 页 2289 章，均零重复、零幽灵章节。

---

## 四、UA / URL 正则 / 发现 / 双版本兼容

```json
"header": "{\"User-Agent\": \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\", \"Accept\": \"text/html,...\", \"Accept-Language\": \"zh-CN,zh;q=0.9\"}",
"bookUrlPattern": "^https?://book\\.washai\\.net/book/(?:indexList-\\d+\\.html|indexList/\\d+/\\d+\\.html|\\d+\\.html|\\d+/\\d+\\.html)(?:\\?.*)?$"
```

- **字段名是 `header` 不是 `headerMap`**（写错被 Gson 静默丢弃 → UA 从未生效）。
- `bookUrlPattern` 用 `^...$` 锚定，覆盖 4 种书籍 URL + 目录页两种形态 + 可带 `?atIndexId=...&order=asc` 查询串；既防换源串站，也让目录 URL 能被本源识别。

发现 16 项（`exploreUrl` 静态 JSON 数组字符串，避免 E 版 `@js` 缓存坑）：

| 分组 | URL |
|---|---|
| 全部作品 | `/book/bookclass.html?page={{page}}` |
| 8 分类 | `/book/bookclass.html?c=1..8&page={{page}}`（玄幻/武侠/都市/历史/科幻/网游/女生/次元） |
| 4 榜单 | `/book/book_ranking.html?type=0..3`（人气/新书/更新/评论，**单页 30 本无分页**） |

`ruleExplore` = `ruleSearch` 共用双模板：

```
"bookList": "id.bookList@class.classBookCard||id.bookRankList@class.rankCard"
```
（`||` 两侧**不留空格**；分类/搜索页与榜单页两套卡片 class 不同。）

**legado-E 兼容静态审查**：
- 列表规则全部 CSS/Default 选择器 → `getAnalyzeByJSoup().getElements()` 返回 `List<Any>`，不触发 E 版 `NativeArray` 强转 ClassCastException；
- 字段规则用 `@js:` 时 result 是 jsoup Element/String（走 `else → Mode.Js` 分支），不返回 JS 对象数组；
- `nextTocUrl` 用 IIFE 返回 `String` / `null`，两版 URL 规则协议一致；
- 未用 V2 loginUi / `getElements` JS 数组 / `java.hexDecodeToByteArray` 等 E 版差异 API；
- `bookUrlPattern` 加 `^$` 锚点不影响 E 版（字段两版一致）。

---

## 五、交付闭环（本次实测记录）

| 步骤 | 结果 |
|---|---|
| 构建脚本 `build_source.py` → JSON（8.7KB） | 静态断言：无 `:contains()` / `:first-child` / `prevContentUrl` / `headerMap`；`||` 无空格；pattern 6 正例 + 2 反例 |
| MCP `save_source` 落库 + `get_source` 回读 | 已保存，字段一致 |
| LAN `POST /saveBookSource`（`x-legado-token`） | `isSuccess:true`，19 字段零差异（后续改动全部走 LAN 字节级直传，杜绝手抄损坏） |
| `debug_source` 关键词「网游之纵横天下」 | 搜索 1 本 → 详情 → 目录 12 页 1173 章 → 正文全通 |
| 反向验证「绝无此书xyzqwer987654」 | 0 条（排除假表单/参数名错） |
| `::URL` 分类第 2 页 / 榜单 type=0,1 | 20 本 / 30 本，字段齐全 |
| `--URL` 末章（大结局） | 正文完整，无 VIP 面板污染 |
| `++URL` 长篇目录专项 | 23 页 2289 章，零幽灵章节 |
| `check_source` | 通过 1/1 |
| 最终 LAN 回读 | 19 字段 diff=[]，关键字段 md5 双侧一致 |

---

## 六、Checklist（同类 SSR 站照抄）

- [ ] 先抓首页 JS 找 `searchByK()` 之类的跳转逻辑，**不要因为「没有 form」就臆造 `/search.php`**
- [ ] 抓 4 类页面（搜索/详情/目录/正文）比对 DOM id/class，确认 SSR 直出
- [ ] 详情页简介是 SEO 套话 ⇒ `ruleBookInfo.intro` 留空（源码只在非空时写入）
- [ ] 目录 `chapterList` 直接选 `a` 元素，别用 `tag.li[...]`（Default 的 `[]` 是索引）
- [ ] `nextTocUrl` 按「下一页」文案过滤 + 只返 1 个 URL + 末页 `return null`
- [ ] 正文选择器深入到 `readChapterAppendBody`，避开隐藏 VIP 面板；确认无章内分页再决定不写 `nextContentUrl`
- [ ] `##` 只放组合规则最后；需要多模板+清理就改 `@js:` 读 jsoup Element
- [ ] UA 写在 `header`；`bookUrlPattern` 覆盖所有书籍/目录 URL 形态
- [ ] 游客态实测末章 `needBuy=false` 再定「无需登录」；有 VIP 面板 ≠ 要登录
- [ ] 查发布页：首页文案 + 根域 DNS + 友情链接接口三处都无 ⇒ 不写线路面板
- [ ] 按用户要求不主动探测搜索频率；**不要无脑加 `concurrentRate`**（全局限速会乘倍拖慢 PoW/翻页目录，11-19 已移除）；长篇目录调试给足 `timeoutSec`
- [ ] 落库后 LAN 回读逐字段比对；`debug_source` 五入口（关键词 / `::` / 裸URL / `++` / `--`）+ `check_source`

---

## 七、2026-11-25 二次改版：JSON API token 断供 + 正文 PoW 读门回滚（v3）

> 站点会反复改版。**11-19 的 PoW 方案在 11-25 已失效，不要照抄旧规则**；成品 `书海阁_修复版_v3_20261125.json`，全链路 debug 全绿。

### 版本沿革

| 版本 | 搜索 | 正文 | 状态 |
|---|---|---|---|
| 11-04 v1 | SSR `?k=` | SSR `#showReading .readChapterAppendBody` | 可用 |
| 11-19 v2 | JSON API `searchByPage`（提速 0.5s，需 `X-Browser-Token`） | SHA-256 PoW 读门（challenge→proof→unlock→queryReadPage） | 当时可用，**现已失效** |
| 11-25 v3 | **回退 SSR `?k=`** | **回退 SSR 内嵌正文** | 当前可用，全绿 |

### 根因对照实验（每步都做了反向验证）

1. `debug_source` 搜索「获取成功但列表 0」⇒ `eval_js java.ajax` 直调 API 返回 `{"code":403,"msg":"请求无效"}`；无 token 变 400，说明 **token 校验失败**而非参数错。
2. 参数对照：`page` / `curr+limit` / 换参数顺序 / 补 `Cookie` 头 / 最小头集合——**全部 403**，排除参数名变更。
3. token 对照：token 内时间戳 `1795121315` 比当时 `Date.now()/1000` 早 5 天；`clear_cookies` 后冷启动首页 → **token 仍为空**（SSR 页不再 `Set-Cookie` 下发）；详情/目录/章节页同样空。⇒ 站点改了 token 获取机制，书源无法再凭游客态拿到 token。
4. 前端 JS 版本戳是改版信号：首页 script 里 `common.js?v=20261125_1`、`mini-layui.js?v=20261123_1`——**排查站点改版先看 JS 的 `v=` 时间戳**。
5. 正文反向验证：清 Cookie 后 `#showReading` **直接内嵌完整正文**；`readPageBootstrap` 已无 `readLocked`；新版 `book_content_page.js` 全文找不到 `read/challenge`/`unlock`/`token`。⇒ PoW 读门已下线，旧 @js 规则只会因无 token 失败。
6. SSR 搜索页 `?k=` 仍有服务端直出结果（首屏 3 本）；但 `&page=2` 返回 404「页面未找到」⇒ **搜索只有首屏**（前端分页靠已失效的 JSON API），属站点限制，不加 `{{page}}` 以免第二页 404。

### 修复要点（可复用到任何"API 突然 403 + SSR 还在直出"的站）

- **优先找 SSR 回退**：只要 `?k=` 搜索页、`#bookList` 卡片、正文页仍服务端直出，就把 `@js`/JSONPath 规则换回 CSS；纯 CSS 规则在 LT 与 E 版都稳。
- **不要试图伪造 token**：清 Cookie 冷启动都拿不到，说明下发链路被站点收回；硬猜签名是死路。
- **正文回滚选择器**：`id.showReading@class.readChapterAppendBody@html##<script[\s\S]*?</script>|<style[\s\S]*?</style>`；实测页面只有 1 个 `readChapterAppendBody`，不会混入下一章。
- **注释写清楚失效原因**：书源 `bookSourceComment` 里记下"API 403 / token 不下发 / PoW 下线"，避免下次维护又走回头路。

### v3 交付验证

| 项 | 结果 |
|---|---|
| MCP `save_source` + `get_source` 回读 | 保存成功，searchUrl/ruleSearch/ruleContent 与本地 v3 一致 |
| `debug_source` 关键词「斗破苍穹」 | 搜索 3 本 → 详情 → 目录 17 页 1663 章 → 正文完整 2500 字 |
| 发现页 Jsoup 抽测 | 分类页 20 本、榜单 30 本，`ruleExplore` 双模板匹配正常 |
