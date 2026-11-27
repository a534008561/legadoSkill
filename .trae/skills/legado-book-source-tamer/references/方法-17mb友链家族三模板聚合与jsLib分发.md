---

# 17mb 友链家族三模板聚合（蔓延书城友链 9 站，rrssk 式 jsLib 分发）

## 1. 家族甄别

蔓延书城底部 29 条友链里，凡是首页引用 `/17mb/css/...`、`/17mb/js/...`、`/17mb/scripts/...` 的才是 17mb 家族；其余 `/themes/9/`、`/themes/muban-*/` 属别的 CMS，不能混进同一模板。本次可访问且同族的 9 站分三模板：

- legacy：蔓延书城、紫蓝文学、闲散阁。`#newscontent .item`/`#hotcontent .item` 发现，详情 `rel="chapter"><dd>` 内嵌目录，正文 `div#chapter`，章内分页文案「下一页」。
- boot：春竹书屋、月影小说网、鱼旧小说网、情念阁。Bootstrap `list-group-item`/`panel-chapterlist`，详情 og 全字段，正文仍在 `div#chapter`（被 `#chaptercontent > #booktxt` 包着），有「下一页」分页。
- mobile：云木故事、彩境书。WAP `sort_list_con`/`info_list`，详情 `div.info_con`，正文 `div#chapter_con`，`chaper_na5` 是「下一章」必须 return null。

三站分类路径不同，必须逐站映射（见成品 jsLib 的 exploreUrl）：legacy `4qi6rN/k4ymlN/o51eb/N_`，boot `e4j4xuN/54vp/N_/b987/N_/imcb/N_`，mobile `fenx/N_*.asp` 与 `fenbook/N/page_*.aspx`。一律用 `{{page}}`，不写死页码上限。

## 2. rrssk 式 jsLib 架构

```
jsLib = HOST_TEMPLATE_MAP + TEMPLATES + M17_HOST/M17_TMPL + M17_EXPLORE/M17_TOC/M17_CONTENT/M17_NEXT + M17_SEARCH
规则 searchUrl = @js:M17_SEARCH(java,source,cookie,key)
规则 bookList = @js:M17_EXPLORE(java,result,baseUrl)
规则 chapterList = @js:M17_TOC(java,result,baseUrl,book)
规则 content = @js:M17_CONTENT(java,result,baseUrl,book)
规则 nextContentUrl = @js:M17_NEXT(java,result,baseUrl,book)
```

`M17_HOST(u,jv,sv)` 优先从规则传入的真实 URL 推导域名，推导不到再读 `source.get('my17_site')`，最后才读 `java.get`。**不能只读 `java.get`**：规则 @js 的 java 与 eval_js/面板写入的键空间不总一致，会出现「面板显示已切换、debug 搜索仍走默认站」。但 `check_source` 的搜索上下文可能没有 `source` 绑定，所以 searchUrl 必须写成 `M17_SEARCH(java,typeof source!=='undefined'?source:java,cookie,key)`，用 typeof 守卫；否则裸写 `source` 会 ReferenceError，check_source 报「搜索失效」而 debug 正常。

## 3. 四个新坑

1. **把单站 searchUrl 的 IIFE 整段搬进 jsLib 函数时必须 `return (function(){...})();`**。只把 `(function(){...})()` 当语句放进函数体，函数返回 `undefined`，OkHttp 报 `Expected URL scheme ... but no scheme was found for null`，check_source 也报「搜索失效」。
2. **全局替换 `java.`→`jv.` 会把 `Packages.java.lang.Thread.sleep` 改成 `Packages.jv.lang...`**。异常被 catch 吞掉，重试静默失效；替换后必须把 `Packages.jv.` 修回 `Packages.java.`。
3. **搜索结果卡片 class 带 style 属性**：`<div class="item" style="height:8rem;">`。用 `<div class="item">` 精确匹配得到 0 条；用 `h.split(/<div class="item"/)` 稳定解析。
4. **详情页偶发 500**：`ruleBookInfo.init` 中检测 `result.length<8000 || 无 og:novel:book_name` 时自行 `java.ajax(baseUrl)` 重试 2 次（只重取详情，不重搜），可避免随机空详情字段。

## 4. 正文混淆还原

17mb 家族正文页引用 `/17mb/js/contentreplace.js`，用页面内联 `arrrp = [...]` 索引把混淆字还原。书源必须在 HTML 层同步做：遍历字符，遇到 `FROM` 或 `TO` 集合中的字就消费一个 arrrp 索引，替换为 `TO[arrrp[i]]`。否则 boot 站正文停留在 `N水/x1/Sh` 之类混淆字。模板打包的验证码 OCR 原始字节（`TB`/`CH`）仍可复用，三站字形实测通用，但**输出必须统一 `toLowerCase()`**：站点验证码按小写校验，模板字符表混有大写，直接回传大写会随机提交失败（check_source 偶发「搜索失效」的真实根因）。实测改小写后连续 4/4 通过。
## 5. 发现页分类按钮省略号
分类按钮不要一行塞 8 个（`layout_flexBasisPercent:0.12`），会被挤成省略号；改为一行 4 个（`0.25`）并给首项 `layout_wrapBefore:true`，分类名完整显示。

## 5. 落库与验证

成品约 61KB，MCP save_source 内联上限不够，走 LAN `POST /saveBookSource`（LT 1122 / E 1125，头 `x-legado-token`）+ `getBookSource?url=...` 单源回读 md5 闭环。验证链：`source_lint.py` → App 内 `new Function` 编译所有 @js/jsLib → `check_source` → MCP debug（legacy 搜索/详情/目录/正文、legacy boot mobile 各一条发现链路）→ E 版 WS `bookSourceDebug` 单源调试（不要读取全部书源）。

## 6. 站点侧限制

boot 四站的 `/search.html?keyword=` 在真机与沙盒都返回站点 404 页（Cloudflare 前置的 nginx 404，不是规则错）；发现/详情/目录/正文可用。成品保留该搜索入口并优雅返回 0 条，不伪造结果。

配套成品：`examples/17mb友链聚合_9站.json`。


发现页 select 的 action 也不能只写 `java.put`：必须调用 jsLib 的 `M17_SET_SITE(infoMap['线路'])`，函数内用 `this.source.put + this.java.put + this.java.refreshExplore()` 双写，确保下拉切站后搜索也跟着切；只写 java 键会导致「下拉切到紫蓝、搜索仍走蔓延」。
## 7. 全量体检补充
- mobile 模板 `/s.php` 不是免验证码接口，第一次 POST 只返回 `layer.prompt` 验证码壳；必须和 legacy 一样取 `/searchcode.php` 并 POST `keyword/code/t`，否则搜索恒 0 条。
- `bookUrlPattern` 的 mobile 分支要写 `yunmustories\.com/wenzhang/\d+`，不能只写 `wenzhang`；云木详情是 `/wenzhang/<数字>/`。
- 详情页偶发 500 会让 `M17_TOC` 返回 0 条；目录入口函数应在首次解析为 0 时用 `jv.ajax(baseUrl)` 重取详情最多 2 次再解析，避免「目录空」误报。
- 全量体检判据：9 站发现页均 >0 条；legacy/boot/mobile 各至少 1 站详情→目录→正文全绿；mobile 搜索用站内真实书名实测；E 版 WS 1126 单源 debug 通过；check_source 1/1。

## 8. 彩境书验证码独立模板库
彩境书 `/searchcode.php` 的字形与蔓延书城主模板库不通用（主库实测 0/3），但小写 ddddocr 实测准确率高。做法：只抓验证码图不提交搜索，用 ddddocr 打标，按 4 槽 bbox→16x24 二值化，按位图投票去重后打包独立 `TBCJ`（351 模板 / 22932B，base64 后约 23KB）；`decode()` 按 `BASE.indexOf('caijingbooks.com')` 选择 `TBCJ` 或主库。扩样到 88 张图后离线实测 3/3，App debug 搜索 1 条→详情→目录→正文全绿。教训：同家族不同站的验证码字形也可能完全不同，不能只靠同源站点模板，必须先做跨站解码验证。

## 9. 主模板库二次扩容
蔓延/紫蓝/云木共用的旧主库对「斗罗大陆」等关键词也会随机失败。做法与彩境书一致：只抓验证码图、不提交搜索，用 ddddocr 小写打标，119 张图归一化后得到 468 个唯一模板（base64 30576B），替换主库 TB；ocr 重试上限提到 8 次、置信度阈值提到 370。实测蔓延「斗罗大陆」148 条、彩境书「斗罗大陆」22 条，详情/目录/正文全绿。

## 10. 调试能搜但直接搜索搜不到
根因不是搜索规则，而是 OCR 在 debug 的长超时下能重试到成功码，直接搜索的短超时内还没发 POST 就被取消。HTTP 日志判据：只有连续 `/searchcode.php` 的 GET，没有 `/s6.html` 或 `/s.php` 的 POST。修法=把主模板从 16x24/49字节压成 12x12/19字节（475模板，阈值230），OCR 重试从 8 次降到 4 次、阈值135；真机 debug 搜索 POST 从 35s 降到 17s，留出直接搜索余量。彩境书保持 16x24 专用模板+8次重试，避免其 12x12 版本误码率高。
