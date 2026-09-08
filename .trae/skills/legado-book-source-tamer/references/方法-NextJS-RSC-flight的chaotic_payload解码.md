# 方法：Next.js RSC flight 的 chaotic_payload 解码（图片/文字通吃）

> 适用：Legado 3.0（LegadoTeam 版）书源开发。针对 **Next.js/Turbopack 前端壳 + 数据藏进 RSC flight 流并做 CJK 混淆** 的站点（NicoManga、mangavk 系等）。
> 实战案例：[examples/尼科漫画_www.nicomanga.com.md](../examples/尼科漫画_www.nicomanga.com.md)（全链路实测通过 + check_source 通过）
> 沉淀时间：2026-09-09

---

## 0. 识别特征（什么样的站是这一类）

出现以下任意 2 条，基本可判定：

1. 详情页 HTML 体积很大（200KB+）但 jsoup 里**没有任何**章节链接/图片/og 标签；
2. 源码里大量 `/_next/static/chunks/*.js`、`self.__next_f.push([1,"..."])`、`turbopack` 字样；
3. `__next_f` 拼接流里出现**超长连续 CJK 字符串**（肉眼全是生僻汉字如 `丵之与与丣…`，正常网页不可能这样）；
4. 页面有 `data-reading-mode`、`legacy-section-container`、`dangerouslySetInnerHTML` 之类"前端壳套旧后台"痕迹；
5. 站点是漫画/生肉聚合站（该类站点近年大量从 Madara PHP 主题迁移到 Next.js 壳，旧 PHP 接口仍以 `/app/manga/` 等路径保留）。

---

## 1. 侦察流水线

```
① 抓详情壳页 HTML
② 确认数据在 flight：grep "__next_f" → 提取 push 字符串 → 拼接 → 找超长 CJK run
③ 找解码算法：下载 HTML 引用的全部 /_next/static/chunks/*.js
   grep 关键字: "chaotic" / "codePointAt" / "19968" / "TextDecoder" / "charCodeAt"
   （NicoManga 的算法就在 chunks/1fzmbgwp5gzi0.js 的 decode(e, t="NicoMangaX2") 里）
④ 用 Python 离线验证解码 → 得到 payload JSON 结构（manga/chapters_list/images/…）
⑤ 把解码器移植成 Legado jsLib（Rhino 兼容版，见 §4）
⑥ 同步侦察旧后台残留接口（见 §6，搜索/简介/标签往往还走服务端渲染，不需要解码）
```

chunk 全量下载技巧：从**所有**入口 HTML（首页/详情/阅读页）提取 `/_next/static/...*.js` 路径合集再逐个下载 grep，因为 turbopack 的懒加载 chunk 不一定出现在壳页 script 标签里（本次核心 chunk 就是从首页引用里找到的）。

---

## 2. chaotic_payload 算法本质

以 NicoManga（密钥 `NicoMangaX2`）为例，通用模板：

```
编码端（服务器）：
  payloadChar[i] = String.fromCharCode( utf8Byte[i] XOR key[i % key.length] ) + 19968
解码端：
  byte[i] = (charCodeAt(payload, i) - 19968) XOR key.charCodeAt(i % key.length)
  JSON.parse( utf8_decode(bytes) )
```

三个关键推论（都可复用为特征检测）：

- `19968 = 0x4E00`（CJK 统一表意文字起点）。XOR 结果 ≤255，所以**密文字符严格落在 U+4E00–U+4EFF**。
  → 定位密文 = "取全文最长的连续 `[\u4e00-\u4fff]` 段"，天然避开真实日文/中文文本（真实 CJK 不会连续 300+ 字还恰好全在窄区间）。
- 明文全部是密文字符（BMP 内），在 JSON 字符串字面量里**不需要任何转义**，原样裸存于 HTML。
- 密文会被 Next.js **切成多段 push**：一段 `self.__next_f.push([1,"..."])` 之后跟
  `"])</script><script>self.__next_f.push([1,"` 继续。因此**必须先把所有 push 参数逐个 JSON 反转义再拼接**，
  直接在原始 HTML 上按 CJK run 匹配会被切碎（这是最常见的翻车点）。

> 变体提示：同类站（mangavk 系等）可能换密钥名/换基址（如 +0x3040 落进假名区）。方法论不变：
> 找 chunk 里的 `(e.codePointAt(a)||0)-BASE` 与 `KEY.charCodeAt(i%N)` 两个常量即可。

---

## 3. flight 流的正确拼接姿势（Python 原型）

```python
import re, json
html = open('detail.html').read()
pushes = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html, re.S)
blob = ''.join(json.loads('"' + p + '"') for p in pushes)   # 逐段反转义！
payload = max(re.findall(r'[\u4e00-\u4fff]{300,}', blob), key=len)
key = "NicoMangaX2"
out = bytes(((ord(c) - 19968) ^ ord(key[i % len(key)])) & 0xFF for i, c in enumerate(payload))
data = json.loads(out.decode('utf-8', 'ignore'))
```

注意 payload 尾部可能混入少量非 JSON 字符（段边界过冲），Python 用 `raw_decode`，
JS 端用**大括号配平截取**（见 §4 的 `bal()`），不要整段 `JSON.parse`。

---

## 4. Rhino 移植版解码引擎（jsLib，零 TextDecoder / 零 Uint8Array / 零正则字面量）

Rhino（htmlunit corejs）可靠性优先：**不依赖** `Uint8Array`、`TextDecoder`、`codePointAt`、`\u{}` 转义。
完整代码见案例文件 `examples/尼科漫画_www.nicomanga.com.json` 的 `jsLib`（该文件即 App 实测版），要点：

```javascript
var NM=(function(){
 var KEY='NicoMangaX2';
 var Q=String.fromCharCode(34);   // 双引号
 var B=String.fromCharCode(92);   // 反斜杠
 // ① recon：不用正则，indexOf 手写扫描拼接所有 push 段
 //    锚点 'self.__next_f.push([1,' → 从引号开始逐字符扫，见 B 跳两位（转义对）
 //    段内容用 JSON.parse(Q+raw+Q) 反转义
 // ② cjkRun：单遍 for + charCodeAt，统计 [19968,20223] 最长连续段（>299 才要）
 // ③ XOR：((charCodeAt-19968) ^ KEY.charCodeAt(a%11)) & 255  → 字节数组
 // ④ u8：手写 UTF-8 解码（含 4 字节代理对分支），结果 push 字符再 join('')
 //    ★绝不能 String.fromCharCode.apply(null, 20万数组)——爆栈
 // ⑤ bal：大括号配平（带 inString/escape 状态机）截取首个完整 JSON 对象
 // ⑥ decode 对外总入口；unesc 反转 &amp; 等实体；list 解析服务端渲染卡片
 return {decode:decode, list:list, unesc:unesc};
})();
```

性能参考（手机实测）：400KB 壳页全流程 ≈ 3~7s/字段。每字段独立 eval 会重复解码——Legado 无跨字段缓存手段，属可接受成本；如嫌慢可只保留 name 解码、其余字段 `put`/`cache` 缓存 payload JSON 字符串再分别取（进阶优化，案例未做）。

**规则里的 result 类型注意**：ruleToc/ruleContent 的纯 `@js:` 拿到的是**含 `<script>` 的完整源码**（组合规则 `选择器@html@js:` 才是净化后文本）——本方法完全依赖 script 内容，所以字段规则一律用**纯 @js:** 前缀。

---

## 5. Legado 解析通道：NativeObject 数组（本类站点最优解）

官方源码依据（AnalyzeRule.kt）：

- `getElements(rule)`：`Mode.Js -> evalJS(rule, result)`，结果为 **NativeArray** 时逐元素进 `List<Any>`；
- 每个元素 `setContent(item)` 后，若 item 是 **NativeObject**：
  `getString` 走 `result[sourceRule.rule]` **键值直取**（无任何 jsoup 环节）。

于是：

```json
"ruleToc": {
  "chapterList": "@js:(function(){var d=NM.decode(result); ... var a=d.chapters_list.slice(); a.reverse(); return a})()",
  "chapterName": "n",
  "chapterUrl": "ur",
  "updateTime": "t"
}
```

- 完全绕开 AnalyzeByJSoup 状态污染（同实例连调 CSS 规则串位/取空的顽疾）；
- 站点 payload 常自带理想键名（`n`/`ur`/`t`），字段规则就是一个单词；
- **顺序**：站点章节数组普遍"最新在前"，必须 `reverse()` 成升序，否则 Legado"下一章节"逻辑错乱；
- 搜索/发现列表同理：`bookList: "@js:NM.list(result)"` 一次 JS 构建 `{name,url,cover,last,time}` 对象数组，
  字段规则 `name`/`url`/`cover`… 键值直取（URL 已是绝对地址时直接给，相对地址交给 Legado isUrl 自动解析——
  注意 jsoup `absUrl` 在 Legado 恒为空，别依赖它）。

---

## 6. 别忘了旧后台：能白嫖的服务端渲染入口

这类站"新壳旧芯"，**尽量把功能分给不同入口**，能少解码就少解码：

| 功能 | 首选入口（NicoManga 实例） | 说明 |
|---|---|---|
| 搜索 | `GET /manga-list.html?n={kw}&p={page}` | **整页 SSR 卡片**，从导航栏 `<form action="/manga-list.html"><input name="n">` 发现 |
| 发现 | `/manga-list.html?pr=popular/new/az`、`/g/{base64标签}.html?p=` | 标签清单走 `/app/manga/api_genres.php`（b64 名/链接，`java.base64Decode` 解） |
| 简介 | `/api_manga_description.php?manga_id={id}&lang=en` | payload 里的 description 常是脏数据（"Updating"），必须另拉 |
| 详情/目录/正文 | 壳页 chaotic_payload 解码 | 无服务端替代品时使用 |

发现入口的线索：解码 payload 里的 `navbar_html`/`custom_js_html` 内联脚本（站点自己的 AJAX 端点、表单参数全在里面），
以及下载主题 JS（theme.js）grep `\.php`。

`exploreUrl` 用 `<js>` 动态生成按钮数组（避免手抄 40 个静态按钮 + 自动跟随站点标签更新）：

```
"<js>(function(){var s=[{title:'Popular',url:'...p={{page}}'},...],a=[];try{var j=JSON.parse(String(java.ajax('.../api_genres.php')));for(var i=0;i<j.length&&a.length<50;i++){var n=String(java.base64Decode(j[i].name)),u=String(java.base64Decode(j[i].href));if(n&&u)a.push({title:n,url:u.replace('.html','.html?p={{page}}')})}}catch(e){}return JSON.stringify(s.concat(a))})()</js>"
```

★`java.base64Decode(...)` 返回 **Java String**，任何 `.replace(正则, …)` 前必须先 `String(...)` 包一层（重载歧义坑）。

---

## 7. 图片漫画源专属

1. **类型字段**：LegadoTeam 版 `BookSource.bookSourceType`：`0文本 / 1音频 / 2图片 / 3文件 / 4视频`
   （源码 `constant/BookSourceType.kt`；注意与旧文档 1=漫画的说法不同，**以源码为准**）。
   书籍 `Book.type` 位掩码 image=64 由 App 自动派生，无需手写。
2. **UA 防盗链三连测**（决定 header 怎么写）：
   ```
   裸请求 → 403？
   +UA    → 200？  → header 只需 UA
   仅 UA+Referer 才 200 → header 加 Referer
   ```
   NicoManga 图床（ihlv1.xyz）实测**无 UA 403、Referer 不需要**。UA 是刚需时即使网页本体不拦也要设。
3. **正文输出**：`content` 返回 `<img src="url">` 序列（每图一行 `\n`，用 `String.fromCharCode(10)` 拼接，
   规则字符串内**禁止出现真实换行**）。整话图片一次给全则无需 `nextContentUrl`。
4. 图片若走 `@js:` 生成，`<img src=` 的双引号用 `String.fromCharCode(34)` 拼（同时规避 §8 的转义问题）。

---

## 8. MCP（LegadoTEAM save_source）提交大坑：双重转义 → 零转义写法

**现象**：书源 JS 里高密度 `\"`、`\\`，手抄进 MCP 字符串参数经"我的文本→JSON 传输层→server GSON"两层转义，
必坏（`MalformedJsonException: Unterminated object ...`）。

**根治法（本次一次成功）**：把整本书源 JS 改写成 **零反斜杠、零内嵌双引号**：

| 原写法 | 零转义写法 |
|---|---|
| JS 里 `"abc"` | `'abc'` |
| 正则 `/[\u4e00-\u4fff]/` | charCode 范围循环判断 |
| 正则里的 `"` | `String.fromCharCode(34)` 拼接 |
| 正则里的 `\\` 匹配 | `===String.fromCharCode(92)` |
| `'\\'`（反斜杠字符） | `String.fromCharCode(92)` |
| `bookUrlPattern` 的 `\.` `\d` | `[.]` `[0-9]` |
| jsoup `absUrl('href')` | 站点直出绝对 URL / Legado 自动拼接 |
| img 双引号属性 | `String.fromCharCode(34)` 拼 |

改完后全 JSON 里只剩 `header` 字段值的 2 对 `\"`（结构性，照抄即可）。
**校验**：写一个 python 扫描器，遍历书源所有字段值，凡出现 `\` 或 `"`（header 除外）即报警。
配合 node 把 jsLib 与每条 @js 规则用**真实页面 HTML** 全量跑一遍（§9），再提交。

---

## 9. 验证方法论（提交前本地预检 → 提交后 App 实测）

1. **node 预检**：`node --check` 查 jsLib 语法（不查 loginUi 宽容格式）；再用 `new Function(...)`/`eval` 把每条
   `@js:` 规则对**离线保存的真实 HTML** 执行，断言字段输出（本文档案例：详情/阅读/列表 6 页全断言）。
2. **debug_source 全链路**（严格串行，MCP 并行会 Session not found）：
   - 绝对 URL = 详情＋目录＋首章正文连跑（最快回归）；
   - `::URL` = 发现页；`--URL` = 正文；`++URL` = 目录。
3. **eval_js 绑定书源身份**：`source.getExploreUrl()` 取回存储值 + 手工截去 `<js>` 壳 + `eval` 验证发现按钮生成
   （`java.base64Decode` 真实可用）；★取回值先 `String()` 包装再操作（Java String 重载坑）。
4. **check_source**：MCP 客户端会超时（每字段解码耗时 3~7s × 多字段），**超时≠失败**——
   以 App 内实际为准：`get_source` 回读 `respondTime` 已写回、`bookSourceGroup` 无 ",发现规则为空" 等污染即通过。
5. **save 后必回读**：`get_source` 与本地逐字段比对（save_source 是整体替换语义，漏传字段会被清空）。

---

## 10. "站点限制"与"规则缺陷"的判定

目录疑似缺章（如柯南 1166 章只解析到 148 章）时，**先证明站点自身行为再下结论**：

1. 解码 payload 找 UI 状态字段：`chapters_per_page`、组件源码 `chapters.length`、"Show All (s)" 渲染逻辑
   ——若"全部"按钮显示的总数就 = 列表长度，则列表是站点给定的完整视图，截断发生在**服务端 payload**；
2. 试各种翻页参数（`?p=`、`?cpage=`、`?page=`）确认 payload 不随参数变化；
3. 全 chunk grep 加载更多的 fetch 端点，确认无此接口；
4. 多本书验证截断数量浮动（148/166/169 ≈ 体积/条数上限特征）而非固定值；
5. 阅读页 `list_chapters` 与详情 `chapters_list` 同为 148 → 站点 UI 也只有这些 → **站点限制**，写进 bookSourceComment。

---

## 11. 风控与登录排查结论模板

- 搜索接口连发 3~5 次看 `429/ratelimit-*` 头与返回长度突变；NicoManga 无频控、PHPSESSID 每次重发无粘性。
  即便无频控，仍设 `concurrentRate=1/1000` 做礼仪性限速（CF 站防误伤）。
- 登录必要性：匿名直接请求正文页，全部 200 且有数据 → 免登录（书签/评分功能忽略，注释写明）。
- Cloudflare：直连返回 200 非 503/挑战页 → 无 JS 挑战，java 网络栈可直连，无需 WebView。

---

## 12. 速查清单（Checklist）

- [ ] 壳页确认：__next_f 存在 + 无 og 标签
- [ ] chunk 里定位 XOR 密钥与基址常量
- [ ] Python 离线解码成功并保存样本 JSON
- [ ] jsLib：push 拼接（反转义）→ 最长 CJK run → XOR → 手写 u8 → 配平截 JSON
- [ ] 全 JS 零反斜杠零双引号改写 + node 全规则预检
- [ ] 图床/接口 UA 三连测，header 落实
- [ ] chapterList NativeArray + reverse；字段键值直取
- [ ] SSR 入口优先（搜索/发现/简介），解码兜底
- [ ] 站点上限判定（§10）写入注释
- [ ] save_source（对象形态）→ get_source 逐字段回读 → debug_source 四链路 → eval_js 验 explore → check_source 超时后看 respondTime/group
