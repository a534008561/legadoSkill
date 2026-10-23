# 案例：桔纸书屋（m.juzhishuwu.net）

> 杰奇CMS 手机站 · GBK · 2026-10-23 制作，App 内 MCP 全链路实测通过
> 成品：`examples/桔纸书屋_m.juzhishuwu.net.json`

## 1. 站点概况

| 项 | 值 |
|---|---|
| 主域 | `https://m.juzhishuwu.net`（`.com` 会 **301** 到 `.net`） |
| 编码 | GBK（`<meta charset="gbk">` + `Content-Type: text/html; charset=gbk`） |
| 模板 | 杰奇CMS（jieqiCMS）小说系统，`themes/qu` |
| 详情页 | `/xs/{bookId}.html` |
| 目录页 | 详情页即第 1 页；后续 `/xs/{bookId}/{page}/` |
| 正文页 | `/xs/{bookId}/{chapterId}.html`，章内分页 `_{n}.html` |
| 登录 | 有（`/login.php`），但**全站免费、无需登录** |
| 搜索限频 | **有**，IP 级，30 秒滑动窗口 |

## 2. 搜索

### 2.1 接口

```
GET /modules/article/search.php?searchkey=<GBK URL编码>&searchtype=articlename&page={page}
```

`searchUrl` 必须带 `charset`：

```json
"searchUrl": "https://m.juzhishuwu.net/modules/article/search.php?searchkey={{key}}&searchtype=articlename&page={{page}},{\"charset\":\"gbk\"}"
```

⚠ 不加 `charset:gbk` 会得到 `%E5%AE%8C...`（UTF-8），站点返回乱码或 0 条。

### 2.2 两种响应形态

**多结果** → 表格：

```html
<table class="grids">
<caption>搜索结果</caption>
<tr align="center"><th>文章名称</th><th>最新章节</th><th>作者</th><th>字数</th><th>更新</th><th>状态</th></tr>
<tr id="nr">
  <td class="odd"><a href="https://m.juzhishuwu.com/xs/184831561.html">万古神帝</a></td>
  <td class="even"><a href="...">第五千零六十三章 血染丹青！</a></td>
  <td class="odd">第一神</td>
  <td class="even">48894K</td>
  <td class="odd" align="center">26-09-10</td>
  <td class="even" align="center">连载</td>
</tr>
...
```

**单结果** → 站点直接 **302** 跳详情页（不返回列表）。必须靠 `bookUrlPattern` 兜底：

```json
"bookUrlPattern": "https?://m\\.juzhishuwu\\.(?:com|net)/xs/\\d+\\.html"
```

`BookList.analyzeBookList` 里 `baseUrl.matches(bookUrlPattern)` 命中就走 `getInfoItem` 详情兜底分支。

### 2.3 结果链接是 `.com` 域（坑）

表格里 `href` 全是 `https://m.juzhishuwu.com/xs/...`，而 `.com` 301 到 `.net`。
实测每次详情多等 **7 秒**（`[00:01.888] → [00:09.018]`）。

修法：`bookUrl` 加替换

```json
"bookUrl": "td:nth-of-type(1) a@href##^https?://m\\.juzhishuwu\\.com##https://m.juzhishuwu.net"
```

修后详情 0.03 秒。

### 2.4 假分页

`page=2/3` 返回与第 1 页**完全相同**的内容（页内 `<strong>1</strong>` 也不变）。
必须短路，否则无限翻页：

```js
"bookList": "@js:(function(){var m=String(baseUrl).match(/[?&]page=(\\d+)/);if(m&&parseInt(m[1])>1)return[];var J=Packages.org.jsoup.Jsoup;var doc=(typeof result==='string')?J.parse(result):result;return doc.select('tr#nr');})()"
```

### 2.5 限频

详见 [[方法-搜索限频伪装的间歇性错误页]]。
简言之：HTTP 200 + 974 字节「出现错误！」页，清 cookie / 换 UA / 伪造时间戳全部无效，
静默 30~45 秒可恢复。**写进 comment，不做重试**。

## 3. 详情页

```html
<div class="detail-box">
  <div class="imgbox"><img src="https://m.juzhishuwu.net/files/article/image/1/1972/1972s.jpg"></div>
  <div class="info">
    <div class="top"><h1>唐人的餐桌</h1>
      <div class="fix">
        <div class="xs-show"><p>《唐人的餐桌》</p></div>
        <p>作&nbsp;&nbsp;者：孑与2</p>
        <p class="xs-show">类&nbsp;&nbsp;别：网游小说</p>
        <p class="opt">动作：开始阅读 加入书架 投推荐票 直达底部 连载中</p>
        <p>最后更新：2024-07-17 11:38:58</p>
        <p>最新章节：<a href="...">正文 第二一八章目的达成</a></p>
      </div>
    </div>
  </div>
  <div class="desc xs-hidden">简介正文…</div>
</div>
<div class="m-desc xs-show"><strong>简介:</strong>简介正文…</div>
```

`div.fix` 恒为 5 个 `p`（`div.xs-show` 也占 nth-of-type 位）：

| 规则 | 值 |
|---|---|
| `name` | `div.info h1@text` |
| `author` | `div.info div.fix > p:nth-of-type(1)@text##作\s*者[：:]\s*` |
| `kind` | `div.info div.fix > p:nth-of-type(2)@text##类\s*别[：:]\s*` |
| `lastChapter` | `div.info div.fix > p:nth-of-type(5) a@text` |
| `intro` | `div.desc@text\|\|div.m-desc@text##简\s*介[:：]\s*` |
| `coverUrl` | `div.imgbox img@src` |

⚠ 部分书 `div.desc` 是**空的**（如《从赘婿开始建立长生家族》《任务又失败了》），
`div.m-desc` 里只有 `简介:` 四个字。此时 `intro` 为空 —— 属站点数据缺失，不是规则问题。

⚠ `intro` 的 `||` 两侧**不能有空格**（见 [[方法-服务端忽略页码参数与||分支空格陷阱]]）。

## 4. 目录

### 4.1 结构

详情页里有两个 `ul.section-list`：

```
ul0（9 条）= 最新章节
ul1（45 条）= 全部目录第 1 页
```

`#first` 是「全部目录」的 `h2` 锚点，`#first + div.section-box` 精确命中第 2 个盒子：

```json
"chapterList": "#first + div.section-box ul.section-list li",
"chapterName": "a@text",
"chapterUrl": "a@href"
```

⚠ 不要用 `ul.section-list:nth-of-type(2)` —— 两个 `ul` 的父级 `div.section-box` 是两个独立元素，
`:nth-of-type` 会各自算成第 1 个。用 `#first +` 兄弟选择器最稳。

### 4.2 分页（关键）

分页条只显示**当前页 ±10 页**：

```
第 11 页：2 3 4 … 10 【11】 12 … 20
第 20 页：11 12 … 19 【20】 21 … 29
第 42 页：33 34 … 41 【42】
```

⇒ 靠 `ul.pagination a` 找「下一页」会**在第 11 页断掉**（没有第 1 页、也没有第 43 页）。

正确做法：解析「当前第X页，共Y页」，**只返回「下一页」1 个 URL**：

```js
"nextTocUrl": "@js:(function(){var m=String(result).match(/当前第\\s*(\\d+)\\s*页[，,]\\s*共\\s*(\\d+)\\s*页/);if(!m)return null;var cur=parseInt(m[1]),total=parseInt(m[2]);if(cur>=total)return null;var bm=String(baseUrl).match(/^(https?:\\/\\/[^\\/]+)\\/xs\\/(\\d+)/);if(!bm)return null;return [bm[1]+'/xs/'+bm[2]+'/'+(cur+1)+'/'];})()"
```

要点：

1. **只返回 1 个 URL，末页 `return null`** —— 这是源码 `when(nextUrlList.size)` 结构决定的强制要求，详见 [[方法-目录分页nextTocUrl只返回单URL的源码级机制]]。
2. **从 `baseUrl` 提 bookId**，不能 `replace(/\/\d+\/?$/,'')` —— 会把 bookId 一起删掉（本次踩坑：得到 `/xs/2/`、`xs/3/`）。
3. 返回**数组**，不要返回字符串。
4. 实测：《完美世界》49 页 2162 章，串行 3.9 秒；《我的师父是仙子》2 页 73 章，0.2 秒。

> ⚠ **历史错误结论（勿再采用）**：早期版本「一次性推算 `1..Y` 全部页 URL」。
> 该书源上线后用户实测《我的师父是仙子》**目录排序错乱**：首章显示「第四十六章」，末章却是「第四十五章」，目录总数仍是 73。
> 根因：2 页目录的书第 1 页只返回 1 个 URL → 走**串行**分支 → 第 2 页再求值一次又返回第 1 页 → 第 1 页被重复抓取 → 经 `reverse → LinkedHashSet 去重 → reverse` 后顺序被**轮转**。
> 同时，一次返回多个 URL 的书走**并发**分支，`mapAsync` 按**完成顺序** emit，长篇小说目录同样会乱序。
> 模拟验证：`无重复 first=1 last=73` vs `重复page1 first=46 last=45`。

## 5. 正文

### 5.1 结构

```html
<div class="content" id="content">
  &nbsp;&nbsp;&nbsp;&nbsp;天山上的雪很白…<br />
<br />
&nbsp;&nbsp;&nbsp;&nbsp;前年看是这样…<br />
...
&nbsp;&nbsp;&nbsp;&nbsp;…让战马突进敌          ← 被硬截断
<br/><a href="javascript:;" class="btn-addbs">『加入书签，方便阅读』</a>
<br/>
<a class='btn btn-info' href=".../20052470_2.html">-->> 本章未完，点击下一页继续阅读(第1页/共2页)</a>
</div>
```

- 段落 = `<br>` 分隔 + 段首 4 个 `&nbsp;` 缩进
- 章内分页 = `a.btn-info` 的 `href`（末页该元素消失）

### 5.2 三个坑

| 坑 | 现象 | 处置 |
|---|---|---|
| **跨页断句** | 第 1 页尾 `突进敌`，第 2 页头 `阵，打乱…` | 段首无 `&nbsp;` → 判为续行，直接粘合 |
| **跨页断实体** | 第 1 页尾 `&nbsp;&nbsp;&amp;n`，第 2 页头 `bsp;&nbsp;…` | 拼接后 `.replace(/&(?:amp;)?n\s*bsp;/g,'&nbsp;')` |
| **整章重复输出** | 《完美世界》序章 85 行 = 同一章 5 份 | 遇第 2 个分页标记即 break + 整页判重 |

详见 [[方法-正文跨页重复输出与整页去重]]。

### 5.3 为什么不能用 nextContentUrl

`nextContentUrl` 是「逐页取 + 换行拼接」，必然产生断句：

```
这……周明
瑞顿时倒吸了口凉气
```

必须在 `@js` 里自己控制抓页循环，**无缝粘合**。

### 5.4 广告行

| 广告 | 覆盖关键词 |
|---|---|
| `你现在阅读的是< "https:" >` | `您现在阅读的是` + `DOM` 里 `https?:\s*"` |
| `< "https:">提供的《书名》…(第N页)` | 判据 A 截断 |
| `【请收藏，wjiwenxue.com 努力为你分享更多好看的小说】` | `请收藏` / `wjiwenxue` |
| `恋上你看书网 630bookla ，最快更新XXX最新章节！` | `恋上你看书` / `bookla` |
| `【首发起点读书，请支持正版阅读】` | `首发起点` / `支持正版` |
| `看清爽的小说就到` | `看清爽的小说就到` |

⚠ **`作者有话要说…` 不是广告**，必须保留（实测 5 章都有）。
⚠ `< "https:" >` 里**没有 `//`**，`/https?:\/\//` 匹配不到，要写 `/https?:\s*"/`。

## 6. 发现页

### 6.1 三个模板

| 类型 | URL | 结构 | 条数 |
|---|---|---|---|
| 分类 | `/list/{1-7}_{page}.html` | `ul.txt-list-row5 li`（5 个 span） | 30/页 |
| 完本 | `/wanben/1_{page}` | `ul.txt-list-row5 li`（同分类） | 30/页 |
| 榜单 | `/paihangbang.html` | `div.row-rank div.tab-bd ul.txt-list-row3 li`（3 个 span） | 133（去重后） |

分类页 `span` 结构：

```html
<li>
  <span class="s1">[玄幻小说]</span>
  <span class="s2"><a href="/xs/65155.html">玄幻都市之盖世大帝</a></span>
  <span class="s3">第四百三十八章 后羿射日的命</span>
  <span class="s4">水中鱼儿</span>
  <span class="s5">02-20</span>
</li>
```

榜单页 `span` 结构（**只有 3 个**，`s1` 是名次数字）：

```html
<li><span class="s1">1</span> <span class="s2"><a href="...">万古神帝</a></span> <span class="s5">11-01</span></li>
```

### 6.2 统一 bookList（兼容两种）

```js
@js:(function(){var J=Packages.org.jsoup.Jsoup;var m=String(baseUrl).match(/[?&]page=(\d+)/);if(m&&parseInt(m[1])>1)return[];var doc=J.parse(result);var lis=doc.select('ul.txt-list-row5 li');if(lis.size()===0){lis=doc.select('div.row-rank div.tab-bd ul.txt-list-row3:not([style*=none]) li');}var seen={},out=[];for(var i=0;i<lis.size();i++){var li=lis.get(i);var a=li.select('span.s2 a').first();if(a==null)continue;var h=a.attr('href');if(!h||seen[h])continue;seen[h]=1;out.push(li);}return out;})()
```

- `ul.txt-list-row5` 优先（分类/完本），空则退化到榜单选择器
- `:not([style*=none])` 排除隐藏 tab（榜单每块有「总/月/周」3 个 ul，只有 1 个可见）
- `seen[h]` 去重（榜单 8 个块有重复书，207 → 150 → 跨块去重后 133）

### 6.3 kind 规则（榜单 s1 是数字）

```js
"kind": "@js:(function(){var a=result.select('span.s1');if(a.size()===0)return '';var t=String(a.first().text()).replace(/[\\[\\]]/g,'').replace(/^\\s+|\\s+$/g,'');return /^\\d+$/.test(t)?'':t;})()"
```

分类页 → `玄幻小说`；榜单页 → 空（名次数字被过滤）。

### 6.4 榜单页是静态单页

`/paihangbang.html?page=1/2/3` 返回**完全相同**内容（133 条）。
用假参数 `?page={{page}}` + bookList 里 `page>1 → []` 短路，让发现页翻到底自然停。

## 7. 最终配置

```json
{
  "bookSourceUrl": "https://m.juzhishuwu.net",
  "searchUrl": "...?searchkey={{key}}&searchtype=articlename&page={{page}},{\"charset\":\"gbk\"}",
  "bookUrlPattern": "https?://m\\.juzhishuwu\\.(?:com|net)/xs/\\d+\\.html",
  "enabledCookieJar": false,
  "concurrentRate": "",
  "respondTime": 180000
}
```

- `enabledCookieJar: false` —— 无登录态需求，关掉避免误带脏 cookie
- `concurrentRate: ""` —— 目录并发 41~48 页未触发风控（实测最快 0.4 秒抓完 41 页）

## 8. 验收记录（App 内 MCP）

| 环节 | 命令 | 结果 |
|---|---|---|
| 搜索（多结果） | `debug_source key="遮天"` | 30 条，0.8 秒 |
| 搜索（单结果 302） | `debug_source key="唐人的餐桌"` | 302 → 详情兜底 → 1846 章 |
| 详情 | `key=URL` | 书名/作者/分类/简介/封面/最新章节 全对 |
| 目录（42 页） | `key=URL` | 1846 章，5 秒 |
| 目录（48 页） | `key=URL` | 2162 章，串行 3.9 秒 |
| 目录（2 页，短篇） | `key=xs/28516.html` | 73 章，串行 0.2 秒 |
| 目录顺序（回归） | 全量 dump | 两书均**零重复、严格单调递增** |
| 正文（跨页断句） | `--URL` | 74 行，无缝 |
| 正文（重复 5 份） | `--URL` | 85 行 → 16 行 |
| 正文（广告行） | `--URL` | 0 残留噪声 |
| 发现（分类） | `::/list/1_2.html` | 30 条 |
| 发现（完本） | `::/wanben/1_2` | 30 条 |
| 发现（榜单） | `::/paihangbang.html?page=1` | 133 条 |
| 发现（榜单第2页） | `::/paihangbang.html?page=2` | 0 条（短路生效） |
| 自检 | `check_source` | 通过 1/1 |

## 9. 已知限制

1. **搜索限频**：IP 级 30 秒滑动窗口，连续搜必失败，书源层无解。
2. **搜索无分页**：服务端忽略 `page`，最多拿到第 1 页 30 条。
3. **部分书简介为空**：站点数据缺失（`div.desc` 空且 `div.m-desc` 只有「简介:」）。
4. **榜单页只 1 页**：静态单页 133 本。
5. **`_N.html` 越界返回 200**：`_3.html`（实际只有 2 页）返回空正文 + 无 `a.btn-info`，循环靠 `next` 为 null 自然终止，不会死循环。
6. **`上架感言!!!` / `完结感言` 排在目录末尾**：站点自身的章节顺序（详情页「最新章节」也显示它），不是书源问题。若某本书的感言夹在目录中间，同样以站点顺序为准。
7. **目录串行抓取比并发慢**：49 页从并发的约 0.7 秒变为串行约 3.9 秒，但换来**顺序绝对正确**，这个交换是必须的。
