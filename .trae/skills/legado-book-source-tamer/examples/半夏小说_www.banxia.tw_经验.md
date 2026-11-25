# 半夏小说(www.banxia.tw)书源制作经验

日期：2026-11-25

## 站点画像
- 繁体 UTF-8 小说站，页面结构：
  - 搜索 `GET /search/?searchkey={{key}}`
  - 详情 `/book/{id}/`
  - 目录独立页 `/indexlist/{id}/`，翻页 `/indexlist/{id}/{N}/`，末页按钮 `#index-next-top` 消失
  - 正文 `/read/{id}/{cid}.html`
  - 发现 `/fenlei/{pinyin}/{page}/`（9 分类）
- 无账号体系，无需登录；但全站被 AEGIS-ALTCHA 盾保护。

## 坑 1：AEGIS-ALTCHA 盾（原生网络全灭）
- 真机 `java.ajax`/原生请求全部 `403 + x-mitigated: challenge + <altcha-widget>` 验证页。
- 常规 `java.webView(null,url,null)`（无 js 默认 900ms delay）取回的仍是验证页。
- **正解**：`java.webViewGetSource('', url, null, '', false, 5000)`（html 传空串 `''`，传 null 会 NPE），delay=5000ms 真机稳定过盾。
- 采用「被动拦截式」：`loginCheckJs` 一处判断 `altcha-widget`/`aegis_altcha` 哨兵 → WebView 带 delay 重取 → `new StrResponse(u, t)` 替换响应体，覆盖搜索/详情/目录/正文/发现全链路，避免逐入口配置遗漏。
- 过盾后 WebView Cookie 复用，后续正文页 delay=0 也能过，但生产保留 5000 保证首次稳定。
- `concurrentRate: '2/1500'` 降频防风控。

## 坑 2：ruleToc 翻页字段名是 nextTocUrl（不是 nextContentUrl）
- **本次踩坑**：把目录翻页写在 `ruleToc.nextContentUrl`，`save_source` 后 App 回读该字段被静默丢弃（GSON 未知字段不报错），调试时目录只有 100 章、无「获取目录下一页列表」日志。
- **正解**：目录翻页字段 = `ruleToc.nextTocUrl`；正文翻页字段 = `ruleContent.nextContentUrl`。两者不可混用。
- 判断指纹：save 后回读 `ruleToc` 里没有你写的字段 = 字段名写错。

## 坑 3：正文假分页（_2.html 正文完全重复）
- 站点正文标题显示 `（1 / 1）`，但手工访问 `/read/{id}/{cid}_2.html` 标题变 `（2 / 1）`，**正文内容与第 1 页逐字相同**。
- 若按 `nextContentUrl` 跟随章内分页会造成整章重复。
- **正解**：不抓章内分页；`ruleContent.nextContentUrl` 只跟随真正的下一章链接。

## 坑 4：末章 linkNext 指向详情页（串章陷阱）
- 末章正文页 `#linkNext` 的 href 是 `/book/{id}/`（书页），不是 `/read/...`。
- **正解**：`@css:a#linkNext[href*=read]@href` 用属性选择器排除；末章取不到链接返回 null 自然终止。

## 坑 5：无结果搜索页用热门推荐填空（假成功）
- 搜索无结果时页面仍渲染 12 条 `.keywords > .bookbox` 热门推荐。
- **正解**：`bookList` 用直接子选择器 `.content.book > .bookbox`，热门推荐在 `.keywords` 内不会被选中。

## 坑 6：多个同级 .author / .blue 导致字段带多余行
- 搜索页 `.bookinfo div.author` 有作者、阅读量等多个；详情 `.booktag span.blue` 有字数、阅读数多个。
- `@text` 会拼成多行。
- **正解**：`##正则##` 一次删掉多余行：`@css:.bookinfo div.author@text##作者：|\n[^\n]*`、`@css:.booktag span.blue@text##\n[^\n]*`。
- 注意 `||`/`&&` 是规则组合符（两侧不可有空格），正则里的单个 `|` 不受影响。

## E版兼容问题（261125 已解决）
- 用户反馈：LT正常，E版(legado-E最新main)搜索/发现全0、面板按钮报错、打开网站验证页卡住。
- **根因链**：①E版 `loginCheckJs` 里 `java.webViewGetSource('',u,null,'',false,5000)` 第3参 js 传 null 时，E版不能稳定走默认JS → 返回验证页/失败；显式传 `'document.documentElement.outerHTML'` 即稳定过盾（诊断源实测 len=6893、altcha=-1、真结果页 title）。②原 loginCheckJs 过盾失败 `throw new Error` 时，E版 WebBook.kt 的 getOrElse 会拿 errResponse 二次调用再 throw → 搜索整体崩→0本+白屏。③面板按钮在UI线程调 webView 会触发E版 `isMainThread` error。
- **修复**：loginCheckJs 显式传JS字符串、不throw（失败降级返回原响应）；面板检查/BX_pass 用 `webViewGetSource('',url,'document.documentElement.outerHTML','',false,5000)`（action环境有java绑定），打开网站用 startBrowser。
- 排查教训：E版WS调试(1126)在解析阶段必断连（清空规则也断），不可作判据；用「诊断源把异常/返回拼进搜索结果书名」的水印法一次定位（诊断源 https://www.banxia.tw#e_errprobe）。
- 已排除：StrResponse构造器/包名、webViewGetSource 6参签名、loginCheckJs `as StrResponse` 两版一致；UA/Client Hints 对 deny 无关（判级看TLS指纹），但E版WebView本身是浏览器档能过盾。

## 交付
- 成品：`banxia.json`（5909 字节）；构建辅助 `build_source.py`；说明 `README.md`
- 保存：MCP save_source（LT）+ LAN 1122/1125 双端 saveBookSources
- 验证：check_source 1/1 通过；debug 搜索4本/详情/目录翻页总页数2/正文全绿；末章 linkNext BLOCK 验证；发现页 boxes=30
