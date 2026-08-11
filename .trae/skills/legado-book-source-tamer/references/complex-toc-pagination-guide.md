# 复杂目录分页处理指南

本文档总结自 9fzw.com 书源制作过程中的实战经验，涵盖复杂目录分页、章节排序、动态链接处理等高级技术。

---

## 目录

1. [问题背景](#问题背景)
2. [遇到的问题与解决方案](#遇到的问题与解决方案)
3. [核心技术详解](#核心技术详解)
4. [完整 chapterList JS 模板](#完整-chapterlist-js-模板)
5. [经验总结](#经验总结)

---

## 问题背景

目标网站 `https://www.9fzw.com/` 具有以下结构特征：

| 特征 | 说明 |
|------|------|
| 详情页结构 | 有两个 `ul.yanqing_list`：第一个是"最新章节"（12条），第二个是"第1-100章" |
| 分页结构 | 通过 `<select>` 下拉框分页，URL 格式为 `/tetail/{bookId}/all_{page}.html` |
| 章节链接 | 详情页用 `href` 属性，分页页用 `onclick="read_tz({chapterId})"` 无 href |
| 章节顺序 | 每个分页页面内章节为**倒序**排列（最新章节在前） |
| 章节重复 | 每个分页页面都包含其他页面的章节（大量重复） |
| 幽灵页面 | `all_5.html` 返回 HTTP 200 但无有效内容，导航回环 |
| 正文加密 | 使用 `qsbs.bb()` 函数对 Base64 编码的内容进行解密 |

---

## 遇到的问题与解决方案

### 问题1：nextTocUrl CSS选择器匹配到"上一页"链接

**现象**：使用 `.page_num a[href*=all_]@href` 作为 `nextTocUrl`，同时匹配到"上一页"和"下一页"链接（两者 URL 都包含 `all_`），导致 Legado 检测到循环后提前停止翻页。

**解决方案**：改用 `.page_num a.y@href`（class="y" 的"下一页"链接），但这只是临时方案。

**最终方案**：完全放弃 `nextTocUrl`，改用 JS 在 `chapterList` 中一次性获取所有分页。

### 问题2：nextTocUrl 返回多个 URL 触发并发模式导致乱序

**现象**：使用 `select@option@value` 返回所有分页 URL（数组），Legado 进入**并发模式**，章节顺序不可控。

**根因**：根据 Legado 源码 `BookChapterList.kt`：
- `nextTocUrl` 返回**1个 URL** → 顺序模式（逐页抓取，顺序可靠）
- `nextTocUrl` 返回**多个 URL** → 并发模式（并发抓取，顺序不可控）

**解决方案**：不用 `nextTocUrl`，在 `chapterList` JS 中手动按顺序获取所有页面。

### 问题3：详情页有两个 yanqing_list，第一个是"最新章节"不需要

**现象**：详情页的 `ul.yanqing_list` 有两个：
- `ul[0]`：12条最新章节（番外等，重复内容）
- `ul[1]`：第1-100章（正文章节）

**解决方案**：在 `extractChapters` 函数中添加 `skipFirst` 参数：
```javascript
var startIdx = (skipFirst && uls.size() > 1) ? 1 : 0;
```

### 问题4：分页页面章节倒序排列 + 跨页重复

**现象**：
- 每个 `all_X.html` 页面的章节是**倒序**的（第500章在前，第1章在后）
- 每个页面都包含其他页面的章节（如 all_1 包含第1-500章的部分章节）

**解决方案**：
1. 使用 URL 去重（`seen` 对象），只保留首次出现的章节
2. 最终按 URL 中的章节 ID 数字排序，不依赖页面中的出现顺序

### 问题5：按章节名排序失败（合并章节问题）

**现象**：第173章和第174章合并为一张，标题为"第173174章"，按章节名中的数字排序会排到第173174章的位置（最后）。

**解决方案**：**按 URL 中的章节 ID 排序**，而不是按章节名排序。
```javascript
function getUrlId(url) {
    var m = String(url).match(/\/(\d+)\.html/);
    return m ? parseInt(m[1]) : 0;
}
list.sort(function(a, b) {
    return getUrlId(a.url) - getUrlId(b.url);
});
```

URL ID 与章节顺序完全对应（ID 从小到大递增），不受章节名格式影响。

### 问题6：幽灵页面 all_5.html

**现象**：`all_5.html` 返回 HTTP 200，但页面无 `selected` option，"下一页"指回详情页，形成循环。

**解决方案**：通过 `<select>` 的 option 列表确定有效页面范围，只请求 select 中列出的 URL，不盲目递增页码。

### 问题7：章节链接使用 onclick 而非 href

**现象**：详情页章节用 `href="/tetail/{bookId}/{chapterId}.html"`，但分页页面用 `onclick="read_tz({chapterId});"` 无 href 属性。

**解决方案**：在 JS 中同时处理两种情况：
```javascript
if (href && String(href).trim() != '') {
    url = href;
} else {
    var onclick = String(link.attr('onclick'));
    var m = onclick.match(/read_tz\((\d+)\)/);
    if (m && bookId) {
        url = '/tetail/' + bookId + '/' + m[1] + '.html';
    }
}
```

### 问题8：正文 Base64 加密

**现象**：正文内容通过 `qsbs.bb('base64字符串')` 函数加密。

**解决方案**：在 `ruleContent.content` 中用正则提取 Base64 字符串并解码：
```javascript
var matches = html.match(/qsbs\.bb\('([^']+)'\)/g);
var content = '';
if(matches) {
    for(var i = 0; i < matches.length; i++) {
        var b64 = matches[i].match(/qsbs\.bb\('([^']+)'\)/)[1];
        content += java.base64Decode(b64);
    }
}
result = content;
```

---

## 核心技术详解

### 技术1：JS chapterList 一次性获取所有分页

**适用场景**：网站目录分页复杂，`nextTocUrl` 无法可靠工作时。

**原理**：在 `chapterList` 规则中使用 `<js>...</js>` 包裹的 JavaScript 代码，手动获取所有分页页面，提取章节，去重排序后返回完整列表。`nextTocUrl` 留空。

**关键步骤**：
1. 从当前页 `result`（详情页 HTML）提取第一页章节
2. 查找 `<select>` option 或 `.btn-mulu` 链接获取所有分页 URL
3. 逐页 `java.ajax()` 获取，提取章节
4. URL 去重
5. 按 URL ID 排序

### 技术2：按 URL ID 排序

**适用场景**：章节名格式不统一（合并章、番外、序章等）。

**原理**：网站章节 URL 中的数字 ID 通常按发布顺序递增，比章节名中的数字更可靠。

```javascript
function getUrlId(url) {
    var m = String(url).match(/\/(\d+)\.html/);
    return m ? parseInt(m[1]) : 0;
}
list.sort(function(a, b) {
    return getUrlId(a.url) - getUrlId(b.url);
});
```

### 技术3：org.jsoup.Jsoup 在 JS 中解析 HTML

```javascript
var JsDom = Packages.org.jsoup.Jsoup;
var document = JsDom.parse(String(result));
var links = document.select('ul.yanqing_list li a');
```

### 技术4：chapterList 返回 JSON 对象数组

当 `chapterList` 规则返回 `[{text: "...", url: "..."}, ...]` 数组时，`chapterName` 和 `chapterUrl` 使用 `$.text` 和 `$.url` 提取字段。

---

## 完整 chapterList JS 模板

```javascript
var JsDom = Packages.org.jsoup.Jsoup;
var document = JsDom.parse(String(result));
var list = [];
var base = source.getKey();

function toAbs(url) {
    if (url && String(url).indexOf('http') != 0) {
        return base + (String(url).indexOf('/') == 0 ? url : '/' + url);
    }
    return url;
}

var bookIdMatch = String(baseUrl).match(/\/tetail\/(\d+)\//);
var bookId = bookIdMatch ? bookIdMatch[1] : '';

function extractChapters(doc, skipFirst) {
    var items = [];
    var uls = doc.select('ul.yanqing_list');
    var startIdx = (skipFirst && uls.size() > 1) ? 1 : 0;
    for (var u = startIdx; u < uls.size(); u++) {
        var links = uls.get(u).select('li a');
        for (var i = 0; i < links.size(); i++) {
            var link = links.get(i);
            var text = link.text();
            var href = link.attr('href');
            var url = '';
            if (href && String(href).trim() != '') {
                url = href;
            } else {
                var onclick = String(link.attr('onclick'));
                var m = onclick.match(/read_tz\((\d+)\)/);
                if (m && bookId) {
                    url = '/tetail/' + bookId + '/' + m[1] + '.html';
                }
            }
            if (text && url) {
                items.push({text: text, url: url});
            }
        }
    }
    return items;
}

function getUrlId(url) {
    var m = String(url).match(/\/(\d+)\.html/);
    return m ? parseInt(m[1]) : 0;
}

var seen = {};

// 1. 从当前页(result)提取章节
var firstChapters = extractChapters(document, true);
for (var c = 0; c < firstChapters.length; c++) {
    var key = firstChapters[c].url;
    if (!seen[key]) {
        seen[key] = true;
        list.push(firstChapters[c]);
    }
}

// 2. 获取所有分页URL
var select = document.select('select option');
var urls = [];

if (select.size() > 0) {
    for (var i = 0; i < select.size(); i++) {
        var url = toAbs(select.get(i).attr('value'));
        if (url && url != toAbs(baseUrl) && url != baseUrl) {
            urls.push(url);
        }
    }
} else {
    var btnMulu = document.select('.btn-mulu');
    if (btnMulu.size() > 0) {
        var all1Url = toAbs(btnMulu.first().attr('href'));
        var all1Html = String(java.ajax(all1Url));
        if (all1Html && all1Html != 'null' && all1Html.length > 100) {
            var all1Doc = JsDom.parse(all1Html);
            var all1Select = all1Doc.select('select option');
            for (var i = 0; i < all1Select.size(); i++) {
                var url = toAbs(all1Select.get(i).attr('value'));
                if (url && url != toAbs(baseUrl) && url != baseUrl) {
                    urls.push(url);
                }
            }
        }
    }
}

// 3. 逐页获取章节
var seenUrls = {};
for (var p = 0; p < urls.length; p++) {
    if (seenUrls[urls[p]]) continue;
    seenUrls[urls[p]] = true;
    var html = String(java.ajax(urls[p]));
    if (html && html != 'null' && html.length > 100) {
        var doc = JsDom.parse(html);
        var chapters = extractChapters(doc, false);
        for (var c = 0; c < chapters.length; c++) {
            var key = chapters[c].url;
            if (!seen[key]) {
                seen[key] = true;
                list.push(chapters[c]);
            }
        }
    }
}

// 4. 按URL ID排序
list.sort(function(a, b) {
    return getUrlId(a.url) - getUrlId(b.url);
});

list;
```

### 配套规则

```json
{
    "ruleToc": {
        "chapterList": "<js>\n上述JS代码\n</js>",
        "chapterName": "$.text",
        "chapterUrl": "$.url",
        "nextTocUrl": ""
    }
}
```

---

## 经验总结

### 何时使用 JS chapterList 替代 nextTocUrl

| 场景 | 推荐方案 |
|------|----------|
| 简单分页，下一页链接明确 | `nextTocUrl`（CSS选择器） |
| 分页有上下页链接，容易匹配错误 | `nextTocUrl`（JS 返回单个URL） |
| 分页复杂：倒序、重复、幽灵页面 | **JS chapterList**（一次性获取+排序） |
| 章节名格式不统一 | **JS chapterList** + URL ID 排序 |
| 章节链接用 onclick 而非 href | **JS chapterList**（处理 onclick） |

### 关键教训

1. **nextTocUrl 返回值数量决定模式**：1个=顺序，多个=并发（乱序）
2. **按 URL ID 排序优于按章节名排序**：不受合并章、特殊标题影响
3. **详情页可能有多个章节列表**：需要跳过"最新章节"列表
4. **幽灵页面检测**：不能靠 HTTP 状态码，要靠 select option 列表
5. **章节去重用 URL**：跨页重复章节通过 URL 去重
6. **从 result 直接提取**：避免重复 ajax 请求详情页
7. **org.jsoup.Jsoup 可在 JS 中使用**：用于解析 ajax 返回的 HTML
