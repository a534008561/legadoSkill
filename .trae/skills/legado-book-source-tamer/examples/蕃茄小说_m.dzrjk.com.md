# 蕃茄小说 m.dzrjk.com 书源案例

> 完成日期：2026-10-21　｜　`check_source` 通过 1/1
> 配套方法论文档：[方法-搜索签名失败伪装成空结果](../references/方法-搜索签名失败伪装成空结果.md)

## 一、站点概况

| 项 | 值 |
|---|---|
| 手机站 | https://m.dzrjk.com |
| PC 站 | https://www.dzrjk.com（会跳转到手机模板，同一套后端） |
| 编码 | UTF-8 |
| 类型 | 服务端渲染 HTML + 少量 JSON API |
| 反爬 | 搜索接口 31 个混淆变量 + sign 签名 + IP 级 3 秒限频 |

## 二、核心难点：搜索接口

### 接口

```
POST https://m.dzrjk.com/api/search
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Referer: https://m.dzrjk.com/user/search.html?q=<urlencode(keyword)>
```

### 参数

`/user/search.html?q=关键词` 页面 `<head>` 内联 31 个变量：

```
vw abw ru jrt van fw cwl gpr uyoo tz euu tsn eju um fp dvm jpk deblkx ht azy sna wqx fpp rup jwj bgt qp yf cw wq + sign
```

名字固定、值每次随机 → 必须现场抓取。

### ★ 致命陷阱：bgt 要截断末位

站点 `common.js`：

```js
function search_before() {
    if (document.cookie != "") {
        bgt = bgt.slice(0, bgt.length - 1);   // ← 有 cookie 就砍掉最后一个字符
    }
    ...
}
```

浏览器必然带 `SID` cookie，所以真实请求的 `bgt` 永远是截断过的。
原样回传 → 签名校验失败 → 服务端返回 `{"code":0,"msg":"","data":{"search":[]}}`，
**伪装成"没有搜到"而不是报错**，极易误判成接口失效。

### 限频

同一 IP 3 秒内二次搜索返回 `{"code":1,"msg":"搜索太频繁，请在 3 秒后再重新搜索"}`。

### 搜索词

分词匹配，超长精确书名返回空：搜「斗破苍穹之无上之境」(11 字) → 0 条；搜「无上之境」→ 1 条。

## 三、页面结构

### 详情页 `/html_wap/{bid}/`

```html
<div id="main"><article>
  <div class="image"><img src="/img/24/24524.jpg"></div>
  <div class="info">
    <h2 class="title">书名</h2>
    <p>作者：xxx</p><p>类别：<a>都市小说</a></p>
    <p>状态：连载</p><p>更新：2026-10-21 14:25</p>
    <p class="newest">最新：<a><em>章节名</em></a></p>
  </div>
  <div class="introbar">简介：xxx（站点自身截断 + "..."）</div>
  <ul class="chapter"><li><a href="/html_wap/24524/13599606.html">第一章：...</a></li></ul>
</article></div>
```

- 目录**一次性全量输出**，实测 988 / 1875 / 2458 / 5461 章都在单页 → 不需要 `nextTocUrl`
- 末章偶发重复前一章链接 → Legado 自动去重

### 正文页 `/html_wap/{bid}/{cid}.html`

```html
<div id="content"><div id="text"><p>段落1</p><p>段落2</p>...</div></div>
```

- 无章内分页 → 不需要 `nextContentUrl`
- 个别老章节末尾混有 `id"booktexts">` 残留文本 → 用 `replaceRegex` 清掉

### 发现页

- 分类：`/{xuanhuan|xiuzhen|dushi|chuanyue|kehuan|wangyou}_wap/1.html`
- 排行榜：`/paihang_wap/{weekvisit|monthvisit|allvisit|dayvote|weekvote|monthvote|allvote|goodnum|size|postdate}/1.html`
- 全本：`/quanben_wap/{同上}/1.html`
- 列表：`#list article`，书名 `h2.title`，作者 `p.0`，链接 `a.0@href`，封面 `.image img@src`，简介 `p.intro`

**URL 里的数字不是页码**：`1.html` / `2.html` / `100.html` 内容完全相同，每个分类固定 30 本。
所以 `exploreUrl` 固定写 `1.html`，不带 `{{page}}`。

## 四、关键规则

```json
"searchUrl": "@js:var base='https://m.dzrjk.com'; ... base + '/api/search,' + JSON.stringify(opt)",
"ruleSearch": {
  "bookList": "$.data.search[*]",
  "name": "$.book_name",
  "author": "$.author",
  "bookUrl": "$.book_list_url",
  "coverUrl": "$.cover",
  "intro": "$.intro",
  "kind": "$.cate_name",
  "lastChapter": "$.latest_chapter_name"
},
"ruleBookInfo": {
  "name": "h2.title@text",
  "author": "p.0@text##^作者：",
  "coverUrl": ".image img@src",
  "intro": ".introbar@text##^简介：|本站提示.*$",
  "kind": "p.1@text##^类别：",
  "status": "p.2@text##^状态：",
  "updateTime": "p.3@text##^更新：",
  "lastChapter": ".newest a@text"
},
"ruleToc": {"chapterList": "ul.chapter li a", "chapterName": "text", "chapterUrl": "href"},
"ruleContent": {"content": "#text@html", "replaceRegex": "##id.booktexts.>##"},
"concurrentRate": "1/2000",
"bookUrlPattern": "https?://(m|www)\\.dzrjk\\.com/html(_wap)?/\\d+/?",
"header": "{\"User-Agent\":\"Mozilla/5.0 (Linux; Android 12; SM-G991B) ... Mobile Safari/537.36\"}"
```

## 五、踩过的坑

| 问题 | 原因 | 修正 |
|---|---|---|
| `concurrentRate: "1/2"` 形同不限流 | 源码单位是**毫秒** | 改 `"1/2000"` |
| 搜索 0 结果造出假书 | 列表空且无 `bookUrlPattern` 时回落"按详情页解析" | 加 `bookUrlPattern` |
| `replaceRegex` 写 `"##<p>id...>"` 正文变空 | 执行在 HTML 净化后，`<p>` 已剥离；不以 `##` 开头被当 CSS 选择器 | 写 `##id.booktexts.>##` |
| `replaceRegex` 用 `^...$` 不生效 | Java `String.replace` 无 MULTILINE | 去掉锚点 |
| MCP `save_source` 字段含双引号被吞 | 解析失败静默丢弃 | 用 `.` 代替 `"` |

## 六、验收

| 关键词 | 结果 | 详情 | 目录 | 正文 |
|---|---|---|---|---|
| 神箭遗恨 | 1 条 | ✅ | 988 章 | ✅ |
| 斗破 | 12 条 | ✅ | 280 章 | ✅ |
| 遮天 | 26 条 | ✅ | 1875 章 | ✅ |
| 凡人修仙传 | 2 条 | ✅ | 2458 章 | ✅ |
| 无上之境 | 1 条 | ✅ | 5461 章 | ✅ |
| 斗破苍穹之无上之境 | 0 条（分词限制） | - | - | - |
| 发现页 玄幻小说 | 30 条 | ✅ | 217 章 | ✅ |

`check_source`：**通过 1/1**

## 七、已知限制

1. 搜索词过长返回空（分词匹配）
2. 发现页无法翻页（站点分类页无分页机制）
3. 简介被站点截断（约 60 字 + "..."）
4. IP 级限频：3 秒内二次搜索报「搜索太频繁」

## 八、关键 Legado 特性验证

| 特性 | 结论 |
|---|---|
| `searchUrl` 用 `@js:` 返回 `url,{json}` | ✅ 正常，JSON 需规范格式 |
| `bookUrlPattern` 防空结果 | ✅ 生效。不加时列表为空会「按详情页解析」把 API 地址当书，生成假书 |
| `concurrentRate` | ✅ 生效（源码 `ConcurrentRateLimiter`，**单位毫秒**，`1/2` 形同不限流，须 `1/2000`） |
| `java.ajax` 走 AnalyzeUrl | ✅ 会带 cookie jar、会应用书源 header（所以抓 token 页要用它，不能用 `java.get`） |
| 目录自动去重 | ✅ `BookList` 末尾 `LinkedHashSet` 去重 |
| `ruleContent.replaceRegex` | ✅ 须 `##正则##` 开头，且在 HTML 净化后执行（详见方法文档 §九） |

## 九、复现命令

```bash
# 抓 token 页 → 拼 body → POST /api/search
python3 - <<'PY'
import requests, re, urllib.parse
UA="Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
order="vw abw ru jrt van fw cwl gpr uyoo tz euu tsn eju um fp dvm jpk deblkx ht azy sna wqx fpp rup jwj bgt qp yf cw wq".split()
kw="遮天"; q=urllib.parse.quote(kw)
s=requests.Session(); s.headers.update({"User-Agent":UA})
r=s.get(f"https://m.dzrjk.com/user/search.html?q={q}",timeout=20)
v=dict(re.findall(r'var\s+([a-zA-Z]+)\s*=\s*"([^"]*)"',r.text))
d={k:(v[k][:-1] if k=='bgt' else v[k]) for k in order if k in v}   # ★ bgt 截断末位
d['sign']=v['sign']; d['q']=kw
h={"X-Requested-With":"XMLHttpRequest","Referer":f"https://m.dzrjk.com/user/search.html?q={q}",
   "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"}
print(s.post("https://m.dzrjk.com/api/search",data=d,timeout=25,headers=h).text[:500])
PY
```

> 注意：沙盒出口 IP 容易被站点限频，返回 `{"code":1,"msg":"搜索太频繁..."}`。
> 设备侧（Legado App）出口 IP 不同，通常正常。
