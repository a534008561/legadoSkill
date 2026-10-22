# 天空书屋（m.tkshuw.com）书源案例

> 沉淀日期：2026-10-22　｜　成品：[天空书屋_m.tkshuw.com.json](./天空书屋_m.tkshuw.com.json)
> 方法论：[方法-假表单搜索接口与列表内联文本提取](../references/方法-假表单搜索接口与列表内联文本提取.md)
> 状态：MCP 全链路调试通过（搜索/详情/目录/正文/发现 5 类页面 × 多本书）

---

## 一、站点画像

| 维度 | 实际情况 |
|---|---|
| 站点 | `m.tkshuw.com`（天空书屋手机站，PC 站 `www.tkshuw.com` 同后端但模板完全不同） |
| 模板 | 纯静态 HTML，无 JS 渲染、无加密参数、无验证码、无登录 |
| 防护 | Cloudflare 前置，`cfCacheStatus: DYNAMIC`，**无 JS 挑战** |
| 登录 | **无**（`login.html`、`/user/` 均 404），全站免登录 → 未写登录 UI / `loginCheckJs` |
| 章内分页 | 有，`{序号}_2.html`、`{序号}_3.html`… |

### URL 结构

```
搜索   GET  /search.html?nf=关键词                （无分页，单页最多 100 条）
详情   /nf_{id}/   或   /nf_{id}.html             （两者内容一致）
目录   /nf_{id}/all.html                          （全量单页，4058 章也不分页）
正文   /nf_{id}/{章节序号}.html
       章内分页 = {章节序号}_2.html
发现   /hots.html                最近更新（81 条）
       /                        首页推荐（126 条）
       /sort/{cid}_0_0_0/?page=N 分类（60 条/页）
```

分类 ID：20 仙侠 / 21 都市 / 22 历史 / 23 言情 / 24 网游 / 25 科幻 / 26 武侠 / 62 侦探 / 64 校园 / 72 综合

---

## 二、四个关键坑（都是实测才暴露的）

### 坑 1：假表单 —— 声明 POST 实则 404

同站四个页面的 `<form>` 有**三种不同声明**：

```html
首页   <form class="searchForm anfa" action="/search.html">          <!-- 无 method，name=nf -->
分类页 <form class="searchForm" method="post" action="/search.html"> <!-- POST，name=s -->
搜索页 <form class="searchForm" method="get" action="/search.html"> <!-- GET，name=nf -->
```

实测：

| 请求 | 结果 |
|---|---|
| `GET ?nf=xxx` | 正常 |
| `POST` + `s=xxx` | **404** |
| `GET ?s=xxx` | **200 + 100 条默认推荐列表，与关键词无关（最危险）** |

**双向验证法**（本例定式）：

```
① 搜"老不死"     → 结果里必须出现 /nf_255656/
② 搜"zzqqxx不存在的书名abc" → 必须 0 条（输出「没有关于(xxx)的内容」）
```

只做第 ① 步会漏掉 `?s=` 这种假成功；两步都过才说明参数名对。

---

### 坑 2：列表内联裸文本

`div.s_list` 里**没有任何子标签**，三种页面三种形态：

```html
搜索结果页 <div class="s_list"><a href="/nf_109837/" title="最新章节：第238章 重塑金身">凡人修仙传之翻倍之能</a> / 冬柳无叶</div>
分类页     <div class="s_list">[仙侠]<a href="/nf_685431/">娘子，你不会真的给我下药了吧</a> / 桃公旺</div>
首页       <div class="s_list"><a href="/nf_193246/">关山风雷</a>/ 清风辰辰</div>
```

- 分隔符 `/` 前后空格**不固定**（模板差异）
- `[分类]` 前缀**只有分类页有**
- `title` 属性**只有搜索结果页有** → 发现页的 `lastChapter` 必然为空，属正常

**定式**（比正则稳，因为书名可能含 `/`）：

```javascript
author: "@js:var t=result.text();var i=t.lastIndexOf('/');i<0?null:t.substring(i+1).trim()"
kind:   "@js:var t=result.text();var m=t.match(/^\s*\[([^\]]*)\]/);m?m[1]:null"
```

**容器差异**：搜索结果页有 `div.wrap-box` 包裹，分类页没有 → `ruleSearch` 与 `ruleExplore` 的 `bookList` **必须分开写**：

```
ruleSearch.bookList  = div.wrap-box div.s_list
ruleExplore.bookList = div.s_list
```

**封面**：列表页无封面图，但 URL 有严格 id 规律 → 从 bookUrl 抽 id 拼：

```
coverUrl: "a@href##/nf_(\d+)/.*##https://www.tkshuw.com/image/nf_$1.jpg"
```

---

### 坑 3：`@js:` 里 `result` 是 Element 不是字符串（静默失败）

第一版写成 `String(result)`，调试日志表现为：

```
[00:00.496] ┌获取分类
[00:00.496] └            ← 空，不报错
```

源码级根因：`AnalyzeRule.getString()` 里 `result` 的类型由**上游规则返回类型**决定。
`@js:` 紧跟 CSS 规则（`div.s_list`）时 `result` 是 jsoup `Element`，
`String(element)` 得到 `org.jsoup.nodes.Element@1a2b3c4d`，`match` 匹配不到 → 返回 null，**不报错**。

**判断指纹**：调试日志有 `┌获取xxx` / `└` 但 `└` 后为空 = 静默失败，不是"没匹配上"。

```javascript
// 防御式（元素/字符串两种都可能时）
@js:var t=(result&&result.text)?result.text():String(result);var m=t.match(...)
```

---

### 坑 4：`nextContentUrl` 取不到要 `return null` 不能 `return ''`

`--` 正文调试时完全正常，但走完整链路时日志异常：

```
[00:04.922] ┌获取正文下一页链接
[00:04.922] └https://m.tkshuw.com/nf_30050/0.html   ← 拼回了当前页
             （◇本章总页数 那行消失）
```

源码级（`AnalyzeRule.getStringList` + `BookContent.kt:63`）：

```kotlin
if (result == null) return null                       // null：零请求，干净
if (result is String) { result = result.split("\n") } // "" → [""]
if (isUrl) { getAbsoluteURL(redirectUrl, url) }       // 空串拼成当前页
val nextUrlList = arrayListOf(redirectUrl)            // 初始已含当前页，去重挡下
```

`''` **不会死循环**（去重挡），但会**白发一次当前页请求** + 日志行消失。

```javascript
// 末态转 null
@js:var h=String(result||"");var m=h.match(/id="pb_next"[^>]*href="([^"]+)"/);
    var u=(m&&/^\d+_\d+\.html$/.test(m[1]))?m[1]:"";u?u:null
```

**`\d+_\d+\.html$` 同时挡住三种伪装**：

| 场景 | `pb_next` href | 处理 |
|---|---|---|
| 章内还有页 | `0_2.html` | 跟随 |
| 章内最后一页 | `1.html`（下一章） | 拒绝 |
| 全书最后一章 | `/nf_255656.html`（详情页） | 拒绝 |
| 章节已删除 | `/nf_255656.html` | 拒绝 |

---

## 三、站点自身问题（非书源问题，勿误判）

### 1. `_2.html` 与主页内容完全相同

```
nf_30050/0.html   -> len 1243, md5 826881f3d034830cb70faf900e234926
nf_30050/0_2.html -> len 1243, md5 826881f3d034830cb70faf900e234926  一致
nf_30050/0_3.html -> 404
```

正文结尾有 `（本章未完，请翻页）` → 该书的第 2 页内容站点没入库。
`nextContentUrl` 会正确抓到 `_2.html`，Legado 不做内容去重 → 这段会重复一遍。
**书源层无法修。** 实测 `nf_438195`/`nf_9185217`/`nf_255656` 均正常，属个别书的数据问题。

### 2. 目录含死章节

```html
<div class="s_list">... 第60章 无效章节,已被删除 ...</div>
```

正文页是 `章节内容加载失败，请重新刷新页面！`，`htmlContent` 只有空格。
目录页看起来完全正常，**书源层无法识别**。用户读到会看到空白章。

---

## 四、交付配置

```json
{
  "concurrentRate": "1/1500",
  "header": "{ User-Agent: Android Chrome 移动 UA, Accept, Accept-Language, Referer }",
  "bookUrlPattern": "https?://(?:m|www)\\.tkshuw\\.com/nf_\\d+(?:/|\\.html)?$",
  "loginUrl": "", "loginUi": "", "loginCheckJs": ""
}
```

| 配置 | 取值 | 理由 |
|---|---|---|
| `concurrentRate` | `1/1500` | 全站每 1.5s 最多 1 次请求。搜索为服务端检索（1~3s），本身不快；这个值既压搜索频率也保护正文抓取。想更快改 `1/800`，想更保守改 `1/3000`。**单位是毫秒** |
| UA | Android Chrome 移动 | 本站是 m 站；实测桌面 UA 也能取到同样结构，但移动 UA 更贴近真实访问。python UA 也返回 200（无 UA 风控） |
| `bookUrlPattern` | `nf_\d+(?:/\|.html)?$` | 同时兼容 `/nf_{id}/` 与 `/nf_{id}.html` 两种详情 URL；**不匹配** `/nf_{id}/all.html`（末尾是 `all.html`）和 `/nf_{id}/{n}.html` |
| 登录三件套 | 全空 | 站点无登录入口，写了反而在部分版本导致登录界面异常 |

> **`bookUrlPattern` 别写成 `nf_\d+`**（不带结尾锚定）——会把 `all.html` 目录页和 `{n}.html` 正文页也当详情页。
> 本例用 `(?:/|\.html)?$` 精确锚定，`all.html` 的 `l` 不在白名单里故不匹配。

---

## 五、验证记录（MCP 实测全绿）

| 环节 | 输入 | 结果 |
|---|---|---|
| 搜索 | `老不死` | 24 条；书名/作者/最新章节/封面/详情链接全对 |
| 搜索 | `zzqqxx不存在的书名abc` | 0 条，正常报"未获取到书籍" |
| 详情 | `og:*` meta | 书名/作者/分类/简介/封面/更新时间/最新章节/目录链接 8 项全对 |
| 目录 | `all.html` | 298 / 558 / 1147 / 616 / 4058 章均**单页抓全**，无 `pages` div |
| 正文+分页 | `nf_255656/0.html` | `nextContentUrl` -> `0_2.html`，`本章总页数:2`，两页内容正确拼接 |
| 正文无分页 | `nf_30050/0.html` | 返回 `null`，干净终止，无额外请求 |
| 正文末章 | `nf_255656/57_2.html` | `pb_next` 指向详情页 -> 拒绝，无串章 |
| 发现-分类 | `sort/20_0_0_0/?page=1` / `?page=3` | 各 60 条，`{{page}}` 翻页正常 |
| 发现-首页 | `/` | 126 条 |
| 发现-最近更新 | `/hots.html` | 81 条 |
| `nextContentUrl` 三态单测 | `eval_js` 5 组用例 | 全对（见方法论第五节） |
| `exploreUrl` JSON | 12 个分类 | 解析正常 |

---

## 六、复用价值

这个案例本身技术含量不高（纯静态站），但**四个坑全部具有跨站通用性**：

1. **假表单** → 任何模板站都可能声明与实现不符；双向验证法是通用纪律
2. **列表内联裸文本** → 笔趣阁类模板站的 `s_list` 都是这个形态；`lastIndexOf('/')` 定式可直接抄
3. **`@js:` 的 `result` 类型** → 影响**所有** `@js:` 规则，与站点无关，是 Legado 机制问题
4. **`return null` vs `return ''`** → 影响 `nextContentUrl` / `nextTocUrl` / 所有 URL 类规则，源码级结论

> 第 3、4 条已回头修正了技能库既有文档（《方法-目录顺序与章节去重铁律》第八节原写"返回 `''` 安全"，
> 实为"安全但非零成本"）。
