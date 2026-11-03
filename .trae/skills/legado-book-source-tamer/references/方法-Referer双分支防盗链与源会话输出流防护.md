# 方法-Referer 双分支防盗链与源会话输出流防护（hanime1.life 实战）

> 261031 制作 🌸 hanime1.life 视频书源（LT 版）提炼，配合《方法-视频书源完全指南》使用。

## 一、CDN「Referer 双分支」防盗链（本次最重要的站点级发现）

### 现象
视频直链 `/jmpres/.../{id}-{q}p.mp4?secure=签名` 恒 302 → 随机 Cloudflare CDN 域（vcsheaye.cc / vcmathe.com / vcjuligi.com 系）。**CDN 按 Referer 分流**：

| 请求形态 | 返回 |
|---|---|
| 无 Referer / Referer=其他域 | `200 application/vnd.apple.mpegurl`（**HLS m3u8**） |
| **Referer=主站** | `200 video/mp4`（**MP4 直链**） |
| UA=okhttp | 403 |
| UA=浏览器 | 200 |

### 为什么致命
LT 版 legado 的 `app/build.gradle` 里 `media3.exoplayer.hls` **被注释掉**——播放器收到 m3u8 直接播放失败。

### 排查方法（对照实验定根因）
同一签名 URL，只变一个头，逐组对照：
```
A1 无Referer        -> M3U8
A2 Referer=主站      -> MP4   ← 唯一开关
A3 Referer=其他域    -> M3U8
```

### 书源侧修法
播放器 headers 来自正文 URL 的 `AnalyzeUrl.headerMap`（= 书源 `header` 字段 + URL 选项合并，源码 `VideoPlay.kt: player.mapHeadData = analyzeUrl.headerMap`）。⇒ **书源 header 里放 `"User-Agent": 浏览器UA, "Referer": "https://主站/"` 即可同时救抓页面与播放器拉流**。无需在正文 URL 上拼 URL 选项。

### 通用化
任何"浏览器能播、阅读里不能播"的视频站，先做 Referer/UA 双变量对照；遇到 m3u8 分支先确认目标 App 版本是否编译了 HLS 模块再决定是否强行拿 MP4。

## 二、详情页 init 对象的字段直取（Legado 规则机制）

`ruleBookInfo.init` 用 `@js:` 返回一个 JS 对象后，**后续字段规则的 `result` 就是该对象**（不是页面 HTML）。字段规则再写 `@js:(function(){var o=H1CUR(...)...})()` 会对 `[object Object]` 重新 jsoup.parse → 全空、不报错。

正确形态：
```
"init": "@js:H1CUR(java,source,result,baseUrl)",   // 返回 {name, author, cover, kindStr, introStr, durStr, ...}
"name": "name", "author": "author", "coverUrl": "cover",
"kind": "kindStr", "intro": "introStr", "lastChapter": "durStr"
```
init 里一次算好所有字符串字段，字段规则纯属性直取。（对比 v3.16 的"每字段重解析+内存缓存"方案，直取更简单更快。）

## 三、Rhino Java String 方法重载二义

jsoup `element.text()` 返回 `java.lang.String`，对它调 JS 正则方法：
```js
tt.replace(/^#\s*/,"")   // ✘ EvaluatorException: replace 的选择不明确 (char,char) vs (CharSequence,CharSequence)
```
修法：`String(tt).replace(/^#\s*/,"")` 先转 JS string。`.match()` 同理（已包 String 的安全）。判断指纹：报错里出现"对应于 JavaScript 参数类型 (object,string) 的 Java 方法 ... 选择不明确"。

## 四、check_source 对 `<js>` 动态 exploreUrl 的误报

`CheckSourceService.doCheckSource`：先搜后发；发现校验用 `source.exploreKinds()`。`<js>` 形态的 exploreUrl（BookSourceExtensions.exploreKinds → `evalJS(substring(4, lastIndexOf("<")))`）在校验环境里求值失败（或被 aCache 缓存了失败结果）→ 恒报「发现规则为空」，而 debug_source 全链路正常。

修法：exploreUrl 用**静态多行 `标题::URL&page={{page}}`** 形态——校验器可解析、真机稳定；线路切换的动态性交给规则环境的 jsLib（H1DOM 读 source 变量）。

另注意（源码实锤）：`<js>` 形态 exploreUrl 执行时会 `substring(4, lastIndexOf("<"))` —— `</js>` 之后的静态行**被整体丢弃**，混合形态不可行。

## 五、同站双卡片模板兼容（发现页/搜索页 0 条的头号嫌疑）

同一站点不同入口用不同卡片 DOM：
- sort/search 页：`div.video-item-container[title] > a.video-link` + `div.title` + `img.main-thumb`（广告卡**无 title 属性**，天然被选择器过滤）
- genre 页：`a[href*="/watch?v="] > div.home-rows-videos-div` + `div.home-rows-videos-title`（无 title 属性、无 video-link）

列表规则双模板扫描：先模板 A（有结果短路返回），空则回退模板 B。**离线用 BeautifulSoup 验证两条链路后**再上 App。

CSS 属性选择器含 `?` 必须加引号：`a[href*="watch?v="]`（jsoup 与 BeautifulSoup 同规）。

## 六、★会话级事故：助手输出流被注入垃圾（本条写给未来会话的执行纪律）

本次会话中，向沙盒写大段文本时输出流被反复注入垃圾（随机词替换、半截函数、重复行、残缺括号），形态包括：
- workspace_write_file 写入的 Python/JS 出现从未写过的键值对
- shell heredoc 中途被塞入无关 token，导致 python/node 语法错误
- MCP save_source 参数里的 JSON 被注入残缺代码（导致 GSON 解析失败）

**纪律（全部实测有效）**：
1. 中文一律经 `U()` 转 `\uXXXX` 转义后写入；非 BMP 字符（emoji）必须拆代理对 `\ud83c\udff3`，单写 `\u1f3f3` 是坏转义。
2. 每块写完立即校验：node `new Function`/`--check`、括号配平、md5、`grep junk` 哨兵词。
3. 单块 < 20 行逐段追加，追加后 exec/执行验证。
4. 已验证干净的文件**绝不整文件重写**，只做锚点单行 replace。
5. **MCP 参数禁止手抄长 JSON**——从磁盘文件走 LAN saveBookSource 通道（POST http://IP:1122/saveBookSource，头 x-legado-token），HTTP 200 + isSuccess=true 即落库，get_source 回读核对。
6. 校验命令本身的引号转义错误 ≠ 文件被破坏；先分离"文件内容校验"与"校验脚本语法"。

## 七、hanime1.life 站点档案（复用价值）

- 家族线路（四域同站，openresty+Laravel，无 CF）：`www.hanime1.life` / `www.hanime103.net` / `www.hanime103.com` / `www.hanime104.com`；裸域 301→www。
- `/` 返回 **HTTP 500 状态码的 gate 页**（"点击继续/visit /enter"），`/enter` 200 直达主页 ⇒ 规则 URL 一律带 `/enter` 或直接 `/search?...`。
- 搜索 `GET /search?query=&page=`、发现 `sort=`/`genre=`；分页 Laravel 标准 `rel="next"`。
- watch：`<video id="player">` + `<source size=480/720/1080 src="/jmpres/...">`；`og:video:duration`=秒；`h3#shareBtn-title`=标题；`div.single-video-tag a`=标签芯片（需滤 add/remove/new/edit 及含 `.` 的噪音）；目录=`#playlist-scroll`（PC+移动双份，需去重）。
- 关停线路跳 `x99dh.com` 发布页（AES-GCM 双层混淆，镜像 x99dh.lat/net/cc/pro/github.io；导航页**不含** hanime 线路列表——线路池以站内页脚互链为准）。
- 签名 URL 跨线路域通用（life 的 secure 在 103.net 上 302 成功）。

## 八、真机报障「发现列表有的为空/几个内容一样」的根因链（261031 实锤）

1. **HTTP 日志是第一现场**：`get_http_logs` 看 App 实际发出的 URL —— 本次抓到 `GET /search?sort=\uXXXX...` 字面转义序列被当 URL 发出。
2. 根因：构建器里 U() 生成的 `\uXXXX` 是**普通字符**写进 JSON 字符串值（`json.dumps` 不解码已有转义序列）→ exploreUrl 里存的是字面 `\u6700...`。
3. 放大器：**站点对无法识别的 sort/genre 参数不报错，静默回退默认列表**（实测 `sort=GARBAGEXYZ123` → 200 + 59 条默认列表）→「多个分类内容一样」；部分参数组合直接空列表 →「有的为空」。
4. 修法：**URL 参数一律 percent-encoding**（`urllib.parse.quote`），只有标题文字用原生中文。
5. 站点行为归档：sort 支持 最新上傳/最新上市/本日排行/他們在看；genre 支持 裏番/泡麵番/Motion Anime/3DCG/2.5D/2D動畫/AI生成/MMD/Cosplay/新番預告(9条模板B)；垃圾参数→59条默认列表(模板A)。
6. 通用判断：**"多个分类列表一样" = "参数没被服务器识别且站点静默回退"**，先查 HTTP 日志看真实发出的 URL，再对照站点参数白名单。
