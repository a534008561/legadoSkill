# 聚合源模板级字段错位与正文广告清理（rrssk v10.4~v10.7 / 261116）

> 场景：给多域名聚合书源新增同族站点后，连续报出"发现页简介显示书名""正文混入排行榜广告"两类问题。本文记录从单站补丁 → 模板级统一修复的思路，以及正文广告的分层清理。

## 一、发现页简介显示书名：单站补丁 vs 模板级统一

### 现象
- uushuk 发现列表简介显示成书名；随后用户指出手打小说网(shoudaxsw)也一样，"这个模板可能都是"。

### 根因（Legado @css 组合链的跨站错位）
- 分类页 li 结构：`div.txtb` 下 `div.0=name(书名)`、`div.1=intro(真简介)`，真简介节点同时带 class `.intro`。
- 模板 intro 规则原为 `.txtb@div.1@text`。用 org.jsoup 看 `div.1` 确实是简介，但在 **Legado 的 `@css` 组合解析链里，这个纯索引写法在部分站上错取成书名**（debug 显示"获取简介 └书名"）。

### 修复策略的演进
1. **v10.4 单站补丁**：给 uushuk 单列 `TEMPLATES.uushuk`，其余字段沿用、intro 改 `.intro@text`。
2. **v10.5 模板级统一**（用户提醒后）：确认 shoudaxsw 模板被 6 站复用（shoudaxsw/shaonianxs/heilhxs/wenhuaxs/ttmiaoxs/zlexs），jsoup 实测 6 站 li 结构一致、`div.intro` 全命中真简介 ⇒ **直接在 shoudaxsw 模板把 intro 改成 `.intro@text`，一处改动 6 站全生效**。

### ★可复用结论
- 判断是"单站问题"还是"模板问题"：先列出所有复用该模板的域名，抽查 2~3 站的真实 DOM。结构一致 = 模板级问题，改模板一处胜过给每站建独立模板。
- `.xxx@div.N` 这种**纯位置索引规则在 Legado @css 链里易跨站错位**；优先用带 class 的无歧义规则（`.intro@text`）。
- jsoup 验证通过 ≠ Legado 解析通过；最终以 debug_source 的字段输出为准。

## 二、正文广告分层清理（.conBox 双栏 + 翻页控件）

### 现象
正文尾部混入"排行榜/推荐书"大片列表，以及"错乱章节催更！""«上一页 下一页»"等控件文字。

### 结构诊断（org.jsoup 抓真实 DOM）
- shoudaxsw 家族正文页 `.conBox` 容器内有两个子块：
  - `div.conL` = 真正文
  - `div.conR` = 排行榜/推荐书广告栏
- 旧的 `boxRule` 用 `.conBox@html` 把 conL + conR 都抓进来 ⇒ 广告混入。
- 催更块 `<div class="btnErrorW">错乱章节催更！</div>` 和翻页块 `<div class="btnW font16">上一页/下一页</div>` **嵌在 conL 内部末尾**，随 `@html` 一起混入正文。

### 两步清理
1. **v10.6 选择器精确到 conL**：家族分支 boxRule 改为
   ```
   .conBox .conL@html||.content .conL@html||.conBox@html||.content@html||article@html||#ad@html
   ```
   优先只取 conL 排除 conR；保留 `.conBox@html` 回退，防止个别页无 conL 时正文全空。
2. **v10.7 按 class 删控件块**：content 的 @js 里，拿到 mainHtml 后对家族域名删除整块：
   ```js
   mainHtml = mainHtml
     .replace(/<div class="btnErrorW"[\s\S]*?<\/div>/g, '')
     .replace(/<div class="btnW[^"]*"[\s\S]*?<\/div>/g, '');
   ```

### ★可复用结论
- 正文容器同层混有广告栏时，先 jsoup 打印容器的 children（tag.class + 文本前 40 字），定位正文子块，选择器精确到子块。
- **翻页/催更 div 嵌在正文内**：按 class 删整块，别用文本正则逐行删（易漏、易误伤正文）。
- 删除正文里的"下一页" div **不影响分页**：`nextContentUrl` 走独立的 `text.下一页@href` 从整页取，与正文清洗解耦。
- 家族级域名判断集中在一处正则（`/shoudaxsw|shaonianxs|heilhxs|wenhuaxs|ttmiaoxs|zlexs/`），增删域名只改一处。

## 三、验证
- 简介：debug_source 看"获取简介"输出是否为真简介而非书名。
- 广告：debug 正文里 grep `排行榜`/`催更`/`上一页`，应全部为 0；正文首尾完整。
- 家族通用性：至少抽验家族本体 + 1 个兄弟站（本次 shoudaxsw + heilhxs）。
- 整源 check_source 1/1 必须保持。

配套成品：`examples/rrssk聚合_51域名_v10.7.json`（最终版，含全部修复）。
