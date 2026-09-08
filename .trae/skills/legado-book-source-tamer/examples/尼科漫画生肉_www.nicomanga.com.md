# 案例：NicoManga 生肉漫画（www.nicomanga.com）—— Next.js RSC 混淆解码 + 图片源全要素

- **成品书源**：[尼科漫画生肉_www.nicomanga.com.json](./尼科漫画生肉_www.nicomanga.com.json)（App 实测版导出）
- **方法论主干**：[references/方法-NextJS-RSC-flight的chaotic_payload解码.md](../references/方法-NextJS-RSC-flight的chaotic_payload解码.md)
- **App 版本**：LegadoTeam 官方版 · 书源类型 `bookSourceType=2`（图片）
- **验证**：debug_source 搜索/详情/目录/正文/发现 五链路全通 + check_source 通过（2026-09-09）

---

## 1. 站点画像

| 项 | 结论 |
|---|---|
| 定位 | 日漫**生肉**(RAW)聚合站，英文 UI，Next.js(Turbopack) 壳 + 遗留 PHP 后端（`/app/manga/` 路径暴露血统） |
| 编码/协议 | UTF-8 / HTTPS，Cloudflare 前置但**无 JS 挑战**（直连 200，cf-ray 出口 SEA/PDX/ATL 轮换） |
| 详情/阅读页 | 纯客户端渲染壳（200~450KB），真数据在 RSC flight 流的 **chaotic_payload** |
| 列表/搜索/分类页 | **服务端渲染**（`.manga-card` 卡片直出） |
| 登录 | 内容与登录无关（书签/评分才要）→ 免登录源 |
| 搜索频控 | 无（连发实测无 429/无限流头）；仍设 `concurrentRate=1/1000` |
| 图片防盗链 | ihlv1.xyz 系图床：**无 UA 一律 403，Referer 不需要** → header 必须设 UA |

## 2. URL / 接口地图

```
详情      https://nicomanga.com/manga{mangaId}/{8位hex}.html      ← 壳页+payload
阅读      https://nicomanga.com/manga{mangaId}/{hex}/chapter-c{话号}i{章节DBid}.html
列表/搜索  GET /manga-list.html?n={kw}&p={page}                    ← 导航栏表单 name=n 发现，SSR
排序      /manga-list.html?pr=popular | pr=new | pr=az | s=last_update&st=DESC
分类      /g/{base64(标签slug)}.html?p={page}（每页30）
标签API   GET /app/manga/api_genres.php            → [{name:b64, href:b64}] × 595
联想搜索  GET /app/manga/controllers/cont.search.php?keyword={kw}  → HTML片段(上限~10条)
简介API   GET /api_manga_description.php?manga_id={id}&lang=en     → {status,description}（无UA 403）
```

## 3. chaotic_payload 破解实录

- 算法位置：`/_next/static/chunks/1fzmbgwp5gwi0.js`（ChapterSkeleton 解码器）
  ```js
  let i=(e.codePointAt(a)||0)-19968, o=t.charCodeAt(a%n); r[a]=i^o;   // t="NicoMangaX2"
  ```
  即 `密文字符 = String.fromCharCode(utf8字节 ⊕ 密钥循环) + 19968`，密文严格 ∈ U+4E00–U+4EFF。
- 密文挂在 flight 段 `17:T<hex字节数>,<CJK串>`（阅读页是 `16`/`1b`），且被 Next.js **切成多个 push 块**，
  块边界插入 `\"])</script><script>self.__next_f.push([1,\"`。
  ★ 第一版直接对原始 HTML 匹配 CJK run 失败（`markers in RAW html` 找到但 run<100 字符）就是这个原因。
- 解码链（全部移植进 jsLib `NM`，纯 Rhino 兼容）：
  1. `recon()`：indexOf 锚点扫描 + 转义对跳过，取每段字符串，`JSON.parse(Q+raw+Q)` 反转义拼接；
  2. `cjkRun()`：单遍 charCodeAt 统计 [19968,20223] 最长连续段（>299）；
  3. XOR 还原字节 → `u8()` 手写 UTF-8 解码（含代理对，**不用 apply 大数组**）；
  4. `bal()` 大括号配平截取首个完整 JSON → `JSON.parse`。
- payload 结构：
  ```
  详情页: {manga:{i,s,n,full_slug,other_name,c,a,authors_list[{n}],genres,genres_list,
               m_status,status_text,l,last_chapter_id,u,total_views,rating_score,...},
           chapters_list:[{i,chapter,n,chapter_label,views,t,ur,is_read}],   ← 最新在前，ur=绝对URL
           chapters_per_page, navbar_html, footer_html, comment_html, custom_js_html, token,...}
  阅读页: {manga, chapter, images:[整话全部图片URL], list_chapters, prev_chapter, next_chapter,
           section_html(285KB旧版阅读页HTML), ...}
  ```
- **目录上限实锤（站点限制非规则缺陷）**：柯南 1166 话 payload 仅 148（1166..1019 连续）、
   kaiji 461→169、OPM 283→166；验证了 ①UI "Show All(s)" 的 s=数组长度（chunk `ey()` 组件源码）
  ②`?p/?page/?cpage` 全无效 ③全站无 load-more fetch 端点（全 chunk grep）。

## 4. 规则设计要点

| 字段 | 写法 | 理由 |
|---|---|---|
| searchUrl | `manga-list.html?n={{key}}&p={{page}}` | SSR 整页可分页，信息比联想接口全 |
| bookList | `@js:NM.list(result)` → NativeObject 数组 | 绕 AnalyzeByJSoup 状态污染 |
| name/bookUrl/coverUrl | 键值直取 `name`/`url`/`cover` | 官方 AnalyzeRule.kt 源码支持 |
| ruleToc.chapterList | `@js:` decode→`chapters_list.slice().reverse()` | 站点最新在前，Legado 要升序 |
| chapterName/Url/Time | `n` / `ur` / `t` | payload 自带理想键名 |
| ruleBookInfo.intro | decode 取 `m.i` → `java.ajax(api_manga_description.php)` | payload 的 description 是脏数据("Updating") |
| ruleContent.content | decode→`images[]` 拼 `<img src=…>`（引号用 fromCharCode(34)） | 整话图全出，无 nextContentUrl |
| bookUrlPattern | `https?://nicomanga[.]com/manga[0-9]+/[0-9a-f]{8}[.]html` | 零反斜杠写法（只匹配详情页，不匹配章节页） |
| exploreUrl | `<js>` 动态：4 排序按钮 + `api_genres.php` b64 解码前 50 标签 | 54 按钮实测生成 500ms |
| header | `{"User-Agent": "Mozilla/5.0 ... Chrome/126"}` | 图床/API 无 UA 403 |
| bookSourceType | `2` | LegadoTeam BookSourceType.kt：2=图片 |

## 5. 踩坑记录（按代价排序）

1. **MCP save_source 双重转义**：高密度 `\"`/`\\` 的 jsLib 手抄进字符串参数必损坏（两次失败：
   `Unterminated object@comment`、`Unterminated escape@exploreUrl`，第二次还是截断——8KB 级参数超出可靠传输量）。
   → 根治：**全书源零反斜杠零内嵌双引号改写**（fromCharCode(34)/(92)、`[.]`/`[0-9]`、indexOf 手写扫描替代正则），
   体积压到 7.1KB，一次转写成功。写 python 扫描器断言"除 header 外任何字段值不含 \\ 或 \""。
2. **jsoup/Rhino Java String 重载坑**再现：eval_js 测试脚手架 `src.replace(/regex/,'')` 报
   `选择不明确(char,char/CharSequence,CharSequence)` —— `source.getExploreUrl()` 返回 Java String，
   必须 `String(...)` 包装。书源正式代码里所有正则操作前都已有 `String()` 包装，故 App 内正常。
3. **jsoup absUrl 恒为空**（已知坑）：幸而站点 payload/卡片直出绝对 URL，未踩实。
4. **规则字符串真实换行**：全部单行化；`\n` 输出一律 `String.fromCharCode(10)`。
5. **IIFE 必须显式 return**（三连坑先例）：所有 @js 字段规则用 `(function(){...return x})()` 包裹，逐条 node 验证。
6. curl 不可用的 workspace 用 python3 urllib 完成全部站点侦察（smart_request 思路：UA+gzip+编码探测）。

## 6. 实测数据（debug_source）

```
搜索 conan      → 2 本，1.8s，字段全
详情 Conan      → 书名/作者 AOYAMA Gosho/分类+状态/简介全文(340词)/封面  31s(6字段各解码)
目录 Conan      → 148 章  首章 Chapter 1019  末章 1166  顺序升序
正文 Conan      → 16 图直出
发现 pr=popular → 30 本 0.9s；点进 Shangrila Frontier → 278 章全量 + 66 图正文 ✓
发现 /g/fantasy p=2 → 翻页正常；新作 manga7602 → 30 章 + 31 图 ✓
eval_js explore → 54 按钮 500ms（base64 标签解码正确）
check_source    → MCP 客户端超时，App 内完成：respondTime=173981 写回、group 无污染 ✓
```

## 7. 维护提示

- 站点若轮换密钥：重新 grep chunk 中 `codePointAt(a)-(数字)` 与 `charCodeAt(a%N)` 两个常量即可，jsLib 只改 `KEY` 一处；
- flight 若不再分块 push，recon() 逻辑向下兼容（单块同样命中）；
- 目录上限、图片域名（ihlv1/s2/s4 子域）变更时先重跑 §2 接口地图；
- `bookSourceComment` 已内置核心机制摘要，用户可自行排错。
