# 方法：AnalyzeByJSoup 状态污染与绕开总表
## ——列表页字段"神秘取空/串位"的唯一权威排查手册

> 沉淀日期：2026-09-14　｜　来源：63sg、fdxrz、rrssk聚合(7shuw/lwenxsw)、zhaoshu.la、m.lzjxx.net、wn10.shop、黑岩、hanime1 共 **8+ 个生产源反复再现**
> 关联：[方法-静默失败定位与探针法](方法-静默失败定位与探针法.md)、[方法-legado各版本行为差异对照](方法-legado各版本行为差异对照.md)

---

## 目录

1. [一句话结论](#一一句话结论)
2. [现象谱系：同一种病的三张脸](#二现象谱系同一种病的三张脸)
3. [源码级机制：实例缓存](#三源码级机制实例缓存)
4. [复现与证明：新旧实例对照法](#四复现与证明新旧实例对照法)
5. [解法阶梯（四级，按优先级）](#五解法阶梯四级按优先级)
6. [列表字段 @js 直取标准模板](#六列表字段-js-直取标准模板)
7. [result 的类型陷阱（Element vs String）](#七result-的类型陷阱element-vs-string)
8. [跨版本注意](#八跨版本注意)
9. [避坑清单](#九避坑清单)
10. [案例档案表](#十案例档案表)

---

## 一、一句话结论

**在同一次解析里，对同一份 content 连续执行多条 CSS 索引规则时，Legado 的 jsoup 解析通道会串位或返回空——这不是你规则写错了。**

只要看到下面任一症状，第一反应就该是状态污染，而不是继续改选择器：

- 明明解析出 20/30 条，`书籍总数: 1`
- `name` 对、`author` 对、`kind` 空、`bookUrl` 空
- 探索页作者列显示成更新时间、书链指向最新章节
- 单独手工测每条规则全对，合进书源就错

---

## 二、现象谱系：同一种病的三张脸

### 脸 1：取空 → 回退 → 条目被去重合并（最常见）

**症状**：`书籍总数: 1`（列表明明有 20 条）。

**链路**：`bookUrl` 取到空 → Legado 用 `baseUrl` 兜底 → 20 条书的 URL 全部相同 → `LinkedHashSet` 按 `BookChapter.equals`（只比 url）合并成 1 条。

**首发案例**：63sg（`dt@a@href` 单独测正确，同实例连调返回 `[]`）。

### 脸 2：串位 → 字段张冠李戴（最迷惑）

**症状**：作者列显示成"2026-09-07 12:33"，点书进去却到了章节页。

**链路**：`li.3@text` 取到了第 5 列；`li.1@a@href` 取到了最新章节的链接 → `bookUrl` 指向阅读页 → 详情页 `init` 的正则 `match()` 返回 `null` → `TypeError` → 用户看到的报错是"**目录获取失败**"（错误信息完全指不到真因）。

**首发案例**：rrssk 聚合的 7shuw 探索页（`修复说明_260907b.md`），用户报的"作者规则显示"就是这个。

### 脸 3：文本节点合并 → 分隔符被吞

**症状**：XPath `label/text()` 拿到的多行文本，`split('\n')` 失灵，全部粘在一行。

**首发案例**：wn10.shop 详情页 `kind`；同族问题在 m.lzjxx.net（`xx li` 前缀标签匹配）也出现过。

**加重表现**：`kind` 是唯一走 `getStringList()` 的字段（`BookList.kt:230`），尾部 `result as? List<String>` 强转与 `getString` 的 `toString()` 路径不同 → 复杂拼接值在真机 debug 里静默变空，离线模拟又正常。
解法：**`kind` 只放纯 jsoup `.text()` 直取，状态文案并入 `intro`**（`intro` 走 `getString`，任意 JS 拼接值都安全）。

---

## 三、源码级机制：实例缓存

`AnalyzeRule.kt`（LegadoTeam 版，源码实锤）：

```kotlin
private var analyzeByJSoup: AnalyzeByJSoup? = null          // :80

private fun getAnalyzeByJSoup(o: Any): AnalyzeByJSoup {     // :151
    return if (o != content) {
        AnalyzeByJSoup(o)                                   // 新 content → 新实例
    } else {
        if (analyzeByJSoup == null) {
            analyzeByJSoup = AnalyzeByJSoup(content!!)      // ★ 同一 content → 复用
        }
        analyzeByJSoup!!
    }
}
```

而 CSS 通道的每一条规则都是：

```kotlin
internal fun getElements(rule: String) = getElements(element, rule)   // :39
```

**结论（已证）**：`BookList.getSearchItem()` / `BookInfo` / `Explore` 逐字段连调时，只要 `result` 没被换掉，全部 CSS 规则打在 **同一个 `AnalyzeByJSoup` 实例** 上；`setContent()` 里 `analyzeByJSoup = null`（:110）是唯一的复位点。

**结论（未证，诚实标注）**：具体是哪个内部可变状态泄漏，**至今没有定位到**。`ElementsSingle` 是 `data class`、`SourceRule` 是每次新建的 `inner class`，按代码看都不该跨调用残留——但实测就是会。
所以：**不要试图"修正规则以适配污染"**，直接换通道。这条已浪费过我们 63sg 一次十余种写法的试错（`a.cover@href`、`tag.a.0@href`、`@CSS:dt a@href`、`||` 组合……在污染实例上全部失败）。

> 另有一个**独立的、已定位**的坑常与此并发：`tag.meta[property=...]@content` 恒失效——`ElementsSingle` 对 `tag.` 前缀走 `getElementsByTag(整串)`，把 `meta[property=og:novel:xxx]` 当标签名。og meta 必须写 `meta[property=og:novel:xxx]@content` 走 jsoup select。（fdxrz 实锤，与污染无关，别混淆）

---

## 四、复现与证明：新旧实例对照法

**这是本手册最有价值的一段。** 判定"是规则错还是污染"，只需两步，不消耗站点配额、不用改书源。

### 步骤 1：新建实例建基线

在 `eval_js`（绑定该书源）里：

```javascript
var AR = Packages.io.legado.app.model.analyzeRule.AnalyzeRule;
var html = String(java.ajax('https://site/list.html'));
var ar = new AR();                      // 全新实例
ar.setContent(html);
ar.getString('dt@a@text');              // ✓ 书名
ar.getString('dd.1@a@text');            // ✓ 作者
ar.getString('dd.1@span@text');         // ✓ 分类
ar.getString('dt@a@href');              // ✓ 书链 —— 全对，说明规则没写错
```

### 步骤 2：同实例按真实执行顺序连调，复现

```javascript
var ar2 = new AR();
ar2.setContent(html);
// 必须按 BookList.getSearchItem 的真实字段顺序！顺序变了结果可能不同
[ 'dt@a@text', 'dd.1@a@text', 'dd.1@span@text', 'dd.0@text',
  'img@data-src', 'dt@a@href' ].forEach(function(r){
  java.log(r + ' => ' + String(ar2.getString(r)));
});
// kind => []   ← 空
// dt@a@href => []  ← 空，而单独调用全对 = 污染实锤
```

### 补充手段：反射直调内部解析

```javascript
var inst = new (Packages.io.legado.app.model.analyzeRule.AnalyzeByJSoup)(element);
inst.getStringList$legado_app_appRelease.call(inst, rule);
```

- Kotlin `internal` 方法名带 `$legado_app_appRelease` 后缀，用 `for (var k in inst)` 枚举可发现。
- `getClass()` 在 Rhino 里返回 `null`，不可用。

### 列表页专用：直接模拟 BookList 全流程

对搜索/探索结果，可 `new AnalyzeRule() + setContent(item) + getString(逐字段)`，完整复现 `getSearchItem`，一步看清哪个字段在哪个位置崩。

---

## 五、解法阶梯（四级，按优先级）

### L1 ★列表字段全改 `@js:` 直取 jsoup（首选，最稳）

`Mode.Js` 通道完全不碰 CSS 解析路径，从根上绕开。适用：`bookList`/`chapterList` 条目的 `name`/`author`/`kind`/`intro`/`coverUrl`/`bookUrl` 六件套、以及 `ruleExplore` 全部字段。

见下一节标准模板。**这是 8 个源验证下来的最终答案。**

### L2 ★XPath 通道免疫（改动最小）

实测：**同一被污染实例连续调用 6 条 XPath 全部正确**（rrssk 7shuw 实锤）。列表结构规整（如 `<li>` 表格行）时优先用：

```
"bookList": "tag.tr[1:]",
"name":     "//li[2]/a/text()",
"author":   "//li[4]/text()",
"kind":     "//li[1]/text()",
"lastChapter": "//li[3]/a/text()",
"bookUrl":  "//li[2]/a/@href"
```

注意：`@css:` 前缀**不能**用在 `||` 组合段内；`tag.tr[1:]` 用于跳过表头行。

### L3 顺序/结构规避（不推荐，仅供 L1/L2 都不便时）

- 把易崩字段挪到 `||` 组合的首位；
- 用 `select` 的后代选择器替代索引简写：`[data-aid="${id}"] li||[data-aid="${id}"] option`（简写 `[data-aid="x"]@li` 只匹配**直接子元素**，嵌套结构匹配不到——rrssk 目录失败根因之一）；
- 详情页 `kind` 用 `property~=category|status|update_time` 拼接后，务必 `##\s+##` 清换行。

### L4 微型测试源验证

改规则前，做一个只含目标页面 + 3 个字段的极小书源 `__s7test`，用 `debug_source` 跑 `::URL`，验证通过再回填大源。**别忘了带移动 UA header，否则吃 GoEdge WAF；验证完删掉测试源。**

---

## 六、列表字段 @js 直取标准模板

**核心纪律：零内嵌双引号、零反斜杠、相对链接交给 AnalyzeRule 拼。**

```javascript
// ruleSearch.bookUrl —— @js 直取，绕开 CSS
@js:
var Q = String.fromCharCode(34);
var d = (typeof result.select === 'function')
        ? result
        : Packages.org.jsoup.Jsoup.parse(String(result));   // ★双兼容
var a = d.select('div.item h3 a').first();
if (!a) { ''; }
String(a.attr('href'));                                     // ★必须是 attr 不是 absUrl
```

**三条铁律**：

1. **`attr('href')` 而不是 `absUrl('href')`**。`Jsoup.parse` 不带 `baseUri`，`absUrl` 在 Legado 里**恒为空** → `bookUrl` 退化 → 全列表回退 baseUrl 去重 → "书籍总数:1"。留相对路径，交给 `AnalyzeRule.getString(rule, isUrl=true)` 自动拼。
   （若确需在纯 JS 里拼绝对地址：`baseUrl.split('/')` 取 `ps[0]+'/'+ps[1]+'/'+ps[2]` 得 origin。**别用 `^(https?:[^/]+)` 正则取 origin，恒 null**——`https:` 后紧跟 `//`，`[^/]+` 匹配不到首字符。）
2. **`String(...)` 包一层再 `.replace()`**。jsoup 的 `.text()`/`.html()` 返回 `java.lang.String`，直接 `.replace(正则,串)` 报"选择不明确 char,char / CharSequence,CharSequence"。`trim()` 和 `indexOf(String)` 单重载不受影响。
3. **IIFE 必须有 `return`**。`(function(){ ...; 表达式; })()` 返回 `undefined` → 字段静默空。详见[探针法篇](方法-静默失败定位与探针法.md)。

**返回数组还是 JSON 字符串数组？**

- 只在本版本内用：`@js` 返回 `NativeObject` 数组可以（`AnalyzeRule` 源码 `Mode.Js → NativeArray → getString` 键访问）。
- **要跨版本分发（LT + legado-E）→ 必须返回 JSON 字符串数组 + 字段规则用纯键名 `$.name`/`$.url`**。E 版 `getString` 没有 `Mode.Js` 分支，`NativeObject` 条目会把规则当键名直取失败 → 条目全被过滤。见[版本差异篇](方法-legado各版本行为差异对照.md)。

---

## 七、result 的类型陷阱（Element vs String）

同一个 `result` 名字，在不同规则位置类型完全不同：

| 位置 | result 实际类型 | 正确用法 |
|---|---|---|
| `ruleSearch.bookList` 的每条条目 | **Element** | `result.select(...)` |
| `ruleExplore.bookList` 的每条条目 | **Element** | 同上 |
| `ruleToc.chapterList` / `ruleBookInfo.*` | **HTML 字符串** | `Jsoup.parse(String(result))` |
| `ruleContent.content` 纯 `@js:` | 净化后的字符串 | 直接处理 |
| 组合规则 `选择器@html@js:` | **净化后**（script 被剥离） | 要拿完整源码必须用纯 `@js:` |

**通用双兼容写法（必备）**：

```javascript
var d = (typeof result.select === 'function')
        ? result
        : Packages.org.jsoup.Jsoup.parse(String(result));
```

> "组合规则 result 被净化、纯 @js: 才拿到完整源码"——ymxwx 的正文 base64 提取就是靠这个区别才成功（`qsbs.bb('base64')` 在 `<script>` 里，组合通道拿不到）。

---

## 八、跨版本注意

- **AnalyzeByJSoup 的污染行为在两版都存在**（LT/E 共用同源 jsoup 通道），所以 L1/L2 解法跨版本通用。
- 但**列表返回值的类型协议两版不同**（见上），这是分发时唯一的额外功课。
- `check_source` 对**动态 `exploreUrl` 的聚合源**会报 `no scheme /list-`，是校验器固有现象非故障，以 `debug_source` 为准。

---

## 九、避坑清单

| # | 坑 | 症状 | 对策 |
|---|---|---|---|
| 1 | 同实例连调 CSS 索引规则 | 字段空/串位 | 改 `@js:` 或 XPath |
| 2 | 用手工单条测试判定"规则没错" | 修不动 | 必须**按真实字段顺序连调**复现 |
| 3 | `absUrl('href')` | 书籍总数:1 | 用 `attr('href')` |
| 4 | `.replace()` 未 `String()` 包裹 | "选择不明确" | 先 `String()` |
| 5 | `tag.meta[...]@content` | og 标签全空 | 改 `meta[property=...]@content` |
| 6 | `[data-aid=x]@li` 简写只匹配直接子 | 目录空 | 改后代选择器 `[data-aid=x] li` |
| 7 | `kind` 用复杂 JS 拼接 | debug 里静默空 | 只放纯 `.text()`，文案并入 `intro` |
| 8 | 组合规则里找 `<script>` 内容 | 正则 match null | 改纯 `@js:` |
| 9 | `@css:` 写在 `\|\|` 段内 | 整条规则失效 | 拆成纯 CSS 或纯 XPath |
| 10 | 反复换选择器试图"适配"污染 | 时间黑洞 | 立刻换通道，别恋战 |

---

## 十、案例档案表

| 源 | 表现脸 | 真因落点 | 采用解法 |
|---|---|---|---|
| 63sg | 脸1 书籍总数:1 | `bookUrl`/`kind` 取空 | L1 六字段全 `@js:` |
| rrssk 7shuw | 脸2 作者显示成时间 | 探索页串位 → 目录获取失败 | **L2 XPath 全字段**（免疫实锤） |
| rrssk lwenxsw | 目录失败 | 简写只匹配直接子元素 | 后代选择器 + 移动UA回退 |
| fdxrz | 脸1 | 搜索 `@href` 空 | L1；`tag.tr[1:]` 跳表头 |
| zhaoshu.la | 脸1 | `absUrl` 恒空 | `attr('href')` + origin 拼接 |
| m.lzjxx.net | 脸3 `kind` 空 | `getStringList` 强转 | `kind` 纯 `.text()` |
| wn10.shop | 脸3 行分隔符被吞 | `label/text()` | `kind` 改纯 `@js:` + jsoup |
| 黑岩 | 脸1/串位 | 卡片 `ownText()` 吞并进状态 | L1 + 标签词前瞻边界正则 |
| hanime1 | — | `SourceRule` 是 inner class | 未涉污染，但类型协议同族 |

---

## 附：一分钟自检口诀

> **总数为一先查 URL，URL 空了别改选择器；**
> **作者成时间就串位，单测对连测错是污染；**
> **CSS 不行换 XPath，XPath 再错走 @js；**
> **attr 不是 absUrl，String 包好 replace，**
> **kind 只放 text 值，IIFE 千万要 return。**
