# 玄幻文学 m.xhwx8.com 书源案例

- **书源文件**：[玄幻文学_m.xhwx8.com.json](./玄幻文学_m.xhwx8.com.json)
- **站点**：`https://m.xhwx8.com`（手机站，PC 站 `www.xhwx8.com` 内容一致）
- **验证结果**：`check_source` 1/1 通过；搜索 / 详情 / 目录 / 正文 / 发现 全链路 APP 内实测通过

## 一、站点画像

| 项 | 结论 |
|---|---|
| 类型 | 传统小说站（非 CMS 通名，模板自定义） |
| 渲染 | 纯静态 HTML，无 JS 渲染正文 |
| 反爬 | 无验证码、无 CF 挑战、无登录墙；`access_baseinfo.js` 是空 IIFE |
| 编码 | UTF-8 |
| 登录 | 有登录页（`/login/`，带验证码 `/ext/mews`），但**全站阅读免登录**，未写登录 UI |
| 干扰 | 每页注入 `\\x` 混淆的挖矿脚本（`position_value=2` 分支），不影响解析 |

## 二、五条链路

### 2.1 搜索：POST /search（GET 假成功）

```json
"searchUrl": "https://m.xhwx8.com/search,{\"method\":\"POST\",\"body\":\"kw={{key}}&page={{page}}\"}"
```

| 请求 | 结果 |
|---|---|
| `POST /search` `kw=剑来` | 200，15 条 ✓ |
| `GET /search?kw=剑来` | 200，**0 条**（页面只有搜索框，无结果列表） |
| `POST` 不存在的词 | 200，`<ul class="lis"></ul>` 空，0 条 ✓（无假成功） |
| `page=12` | 14 条；`page=13` | 0 条（共约 12 页 × 15 条） |

`_token` 字段可省略（不带 token 与带 token 结果一致）。

列表结构（搜索结果与分类页共用）：

```html
<ul class="lis">
  <dl><li>
    <span class="s1">[其他]</span>
    <span class="s2"><a href="https://m.xhwx8.com/qita/581567.html" title="...">二十四剑图</a></span>
    <span class="s3">沐华炙</span>
  </li></dl>
</ul>
```

```json
"ruleSearch": {
  "bookList": "ul.lis dl",
  "name": "a@text",
  "author": "span.s3@text",
  "kind": "span.s1@text##[\\[\\]]",
  "bookUrl": "a@href"
}
```

> `name` 用 `a@text` 而非 `span.s2 a@text`：`title` 属性含 `<em>` 高亮残留（`&lt;em&gt;遮天&lt;/em&gt;`），
> 但 `@text` 取的是渲染文本，干净。

### 2.2 详情：og: 协议全字段

```json
"ruleBookInfo": {
  "name": "meta[property=og:novel:book_name]@content",
  "author": "meta[property=og:novel:author]@content",
  "kind": "meta[property=og:novel:category]@content",
  "lastChapter": "meta[property=og:novel:latest_chapter_name]@content",
  "updateTime": "meta[property=og:novel:update_time]@content",
  "coverUrl": "meta[property=og:image]@content",
  "intro": "meta[property=og:description]@content@js:(...)"
}
```

`og:description` 带固定前缀 `简介：    书名：《xxx》 简介：` + 结尾多一个 `！`，
用 IIFE 剥掉：

```js
@js:(function(){
  var t=String(result||"");
  t=t.replace(/^\s*简介[：:]\s*/,"");
  t=t.replace(/^\s*书名[：:]\s*《[^》]*》\s*/,"");
  t=t.replace(/^\s*简介[：:]\s*/,"");
  t=t.replace(/[\s！!]+$/,"");
  return t;
})()
```

`tocUrl` 留空 → 复用详情页 HTML 抓目录，**省一次请求**（详情页就是目录页）。

### 2.3 目录：`:nth-of-type(2)`

详情页有**两个** `ul.chapter`：第 1 个是「最新章节」6 条，第 2 个才是全量正文。

```json
"ruleToc": {
  "chapterList": "ul.chapter:nth-of-type(2) li",
  "chapterName": "a@text",
  "chapterUrl": "a@href",
  "nextTocUrl": "div.listpage span.right a.onclick@href"
}
```

| 写法 | 条数 |
|---|---|
| `ul.chapter:nth-of-type(2) li` | **101** ✓ |
| `ul.chapter:eq(1) li` | 0 |
| `ul.chapter:nth-child(2) li` | 0 |
| `ul.chapter[1] li` | 0 |

目录分页：每页 100 章，`div.listpage span.right a.onclick` 是「下一页」；
末页该 `<a>` 无 `href`（只剩 `<a class="before">下一页</a>`）→ 规则取空 → 干净终止。
实测 3294（5039 章）分 51 页，全部抓全。

### 2.4 正文：`#nr1` + 数字后缀分页

```json
"nextContentUrl": "@js:(function(){var h=String(src||\"\");if(h.indexOf(\"本章未完\")<0)return null;var u=String(baseUrl||\"\");var m=u.match(/^(.*?)(?:_(\\d+))?\\.html$/);if(!m)return null;var n=m[2]?parseInt(m[2],10)+1:2;return m[1]+\"_\"+n+\".html\";})()"
```

- 章内分页 URL：`{chapterId}_2.html`、`_3.html`…
- 终止判据：页面含 `<p><br />本章未完，点下一页继续阅读。>>></p>` 才继续
- **坑**：超出末页的 `_N.html` 仍返回 200 + 与末页**逐字节相同**的内容
  （实测 `_5`/`_6`/`_7` 长度全 491），所以不能靠"页面存在"判断终止
- 对比实验：`_2.html` 的 `pb_next` 指向 `{chapterId}.html`（上一页），
  另有混淆 URL `TAGPZ...html` 与 `_3.html` **内容逐字节相同** → 同一页两种写法，用数字后缀即可

### 2.5 正文清洗（九步，顺序不能乱）

见 [方法-服务端忽略页码参数与||分支空格陷阱.md](../references/方法-服务端忽略页码参数与||分支空格陷阱.md) §5。

摘要：

| 步骤 | 目标 |
|---|---|
| ① | `<p>` 含「榴弹怕水提醒您 / 向你推荐他的其他作品 / 最新章节网址」整段 |
| ② | 畸形 `<iclass="lb_top2">`（HTML 残缺，`x` 被吞） |
| ③ | `<p class="pages">您所看到的内容#中间#有#缺失…` |
| ④ | `<p><br />本章未完…` |
| ⑤ | `<p>` 含 `xhwx` / `#中#间#有#缺#失` / `请退` |
| ⑥ | `「如章节缺失请退#出#阅#读#模#式」` |
| ⑦ | 去外壳 `^<div…>` / `</div>[\s\S]*$` |
| ⑧ | 空段落 `<p>\s*</p>` |
| ⑨ | 末尾「！」（**必须在 ⑧ 之后**） |

实测 5 本书 9 个章节，清洗后 `xhwx`/`请退`/`</div>` 命中数均为 0。

### 2.6 发现页：三模板合一

```json
"ruleExplore": {
  "bookList": "ul.lis dl,ol.popular-list li.popular-book,div.block ul > li",
  "name": "span.s2 a@text||a.popular-title@text||a.black@text",
  "author": "span.s3@text||span.popular-author@text",
  "bookUrl": "span.s2 a@href||a.popular-title@href||a.black@href",
  "kind": "@js:(function(){var t=(result&&result.text)?result.text():String(result);var m=t.match(/\\[([^\\]]+)\\]/);return m?m[1]:\"\";})()"
}
```

三个模板：

| 页面 | 列表选择器 | 书名 | 作者 | 分类 |
|---|---|---|---|---|
| 分类页（玄幻/仙侠…） | `ul.lis dl` | `span.s2 a` | `span.s3` | `span.s1` = `[仙侠]` |
| 热门榜 hot.html | `ol.popular-list li.popular-book` | `a.popular-title` | `span.popular-author` | `a.popular-category` |
| 首页 / 排行榜 | `div.block ul > li` | `a.black` | `span.s3` | **裸文本 `[都市]`** |

⚠ **`||` 两侧绝对不能有空格**（详见方法篇 §2）。
`kind` 用 JS 兜住「裸文本 `[分类]`」与「`span.s1`」两种形态。

### 2.7 发现页假分页（站点缺陷）

`?page=N` 在手机站与 PC 站**全部返回第 1 页同一集合**（实测 p1==p2==p3==p592）。
⇒ 分类列表物理上只有 20 本/类，书源层无法修复。

**替代入口补书量**：

| 入口 | 数量 |
|---|---|
| 热门榜 `/hot.html` | 467 本（单页全量，无分页） |
| 排行榜 `/paixingbang.html` | 84 本（7 分类 tab 同页） |
| 首页 `/` | 66 本 |
| 全本 `/quanben.html` | 20 本 |
| 7 个分类页 | 各 20 本 |

## 三、交付配置

```json
"bookUrlPattern": "https?://(?:m|www)\\.xhwx8\\.com/(?:book|[a-z]+)/\\d+\\.html$",
"concurrentRate": "2/1000",
"header": "{\"User-Agent\":\"Mozilla/5.0 (Linux; Android 13; Pixel 6) ... Mobile Safari/537.36\"}"
```

- `bookUrlPattern` 结尾必须 `$` 锚定，且**不能带 `(?:_\d+)?`**
  —— 否则目录页 `_2.html`、正文页 `/{cat}/{id}/{cid}.html` 也会被当详情页
- `concurrentRate` 用 `"2/1000"`（2 次/1000ms）：目录分页 51 页 + 正文 5 页串行请求，
  限速后仍能在 10s 内完成单章

## 四、验收记录

| 项 | 结果 |
|---|---|
| `check_source` | **1/1 通过** |
| 搜索「剑来」 | 15 条，书名/作者/分类/链接全对 |
| 搜索「辰东」 | 15 条，首条《夜无疆》✓ |
| 搜索「人间至宝」 | 15 条，精确命中 ✓ |
| 搜索不存在词 | 0 条，正常报「未获取到书籍」 |
| 详情 | 8 项全对（书名/作者/分类/字数空/最新章节/简介/封面/目录链接） |
| 目录 3294（5039 章） | 51 页 → 全量 |
| 目录 131755（722 章） | 8 页 → 全量 |
| 目录 581567（237 章） | 3 页 → 全量 |
| 正文 5 页章节 | `◇本章总页数:5`，拼接无重复无缺失 |
| 正文无分页章节 | `nextContentUrl` 返回 null，零多余请求 |
| 发现页 10 个入口 | 全部通过（分类 7 + 热门榜 + 排行榜 + 全本） |

## 五、已知限制

1. **分类页无法翻页**（站点 `?page=N` 无效），每类只有最新 20 本。
2. 热门榜 467 本单页全量，`?page=2` 同样无效。
3. 部分"章节"是作者公告/活动番外，通篇广告，清洗后为空 →
   App 报「内容为空」，属正确行为。
4. 无登录功能（站点有登录页但阅读不需要）。
