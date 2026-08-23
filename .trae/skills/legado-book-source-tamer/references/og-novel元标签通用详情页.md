# og:novel 元标签通用详情页 —— 一套选择器覆盖整个站点家族

## 一、发现过程

为 rrssk 聚合家族（21站）补全详情页时，逐站检查书籍页 `<head>`，发现所有家族站都输出**完整的 og:novel 系列元标签**：

```html
<meta property="og:type" content="novel" />
<meta property="og:title" content="女神召唤：开局召唤麦晓雯！" />
<meta property="og:description" content="简介全文..." />
<meta property="og:image" content="http://www.kelexs.com/templates/default_cover.jpg" />
<meta property="og:novel:category" content="玄幻小说" />
<meta property="og:novel:author" content="千早十三香" />
<meta property="og:novel:book_name" content="女神召唤：开局召唤麦晓雯！" />
<meta property="og:novel:read_url" content="http://www.kelexs.com/book/AKKJGHF.html" />
<meta property="og:novel:status" content="全本" />
<meta property="og:novel:update_time" content="2026-08-23 04:42:45" />
<meta property="og:novel:latest_chapter_name" content="第43章 混战（二合一）" />
<meta property="og:novel:latest_chapter_url" content="http://www.kelexs.com/book/AKKJGHF-43.html" />
```

比解析正文 DOM 稳定得多——DOM 结构各站微调，meta 标签从不缺。

## 二、选择器写法的坑（重点）

### 2.1 属性值含冒号

`og:novel:author` 直接写 `[property=og:novel:author]` 或加反斜杠 `[property=og\:author]` 在 Legado 默认规则里**匹配失败**（实测 jsoup 直调 0 命中）。

### 2.2 解决：用结尾匹配 `$=` 避开冒号

| 字段 | 选择器 | 实测命中 |
|------|--------|---------|
| 书名 | `[property$=book_name]@content` | ✅ |
| 作者 | `[property$=author]@content` | ✅ |
| 简介 | `[property$=description]@content` | ✅（注意 twitter:description 是 name 属性不是 property，不冲突） |
| 封面 | `[property$=image]@content` | ✅ |
| 最新章节 | `[property$=chapter_name]@content` | ✅ |
| 分类/状态/更新时间 | `[property~=category\|status\|update_time]@content` | ✅（`~=` 配 `\|` 多值 OR 是原源已验证写法） |

### 2.3 jsoup 直调验证代码

```javascript
var doc = org.jsoup.Jsoup.parse(html);
doc.select("[property$=book_name]").size()   // 1
doc.select("[property$=author]").first().attr("content")  // "千早十三香"
```

## 三、多家族分支（菠萝猫例外）

菠萝猫书籍页**没有** og:novel 系列（只有 og:title/og:image/og:description），且简介是 data-obf 加密。用 @js 按域名分支：

```javascript
"name": "@js:
if (GET('server').indexOf('boluomao') >= 0) {
  java.getString('h1@text');
} else {
  java.getString('[property$=book_name]@content');
}",
"author": "@js:
if (GET('server').indexOf('boluomao') >= 0) {
  java.getString('@css:.bookTitleLeft a.author@text');
} else {
  java.getString('[property$=author]@content');
}",
"intro": "@js:
if (GET('server').indexOf('boluomao') >= 0) {
  // data-obf 解码，见专门文档
  let bytes = java.base64DecodeToByteArray(String(java.getString('.obf-html@data-obf-html')));
  for (let j = 0; j < bytes.length; j++) { bytes[j] = bytes[j] ^ ((j % 127) + 1); }
  java.bytesToStr(bytes, 'utf-8');
} else {
  java.getString('[property$=description]@content');
}",
"lastChapter": "@js:
if (GET('server').indexOf('boluomao') >= 0) {
  java.getString('@css:.info a.latest-link@text');
} else {
  java.getString('[property$=chapter_name]@content');
}"
```

封面 `og:image` 两套体系都有，**无需分支**：`"[property$=image]@content"`。

## 四、字数提取的坑

各站字数展示位置混乱：
- kelexs：`.t_c.2@text`（统计框，无"字数："前缀，直接"91.74万字"）
- dadawx/ishuku：同选择器取到的是"累计人气值"（垃圾数据）
- x630xsw/369shuba：页面根本没有字数

**通用方案：正则直取，取不到就留空**

```javascript
var m = String(result).match(/([\d.]+\s*万字)/);
m ? m[1] : '';
```

比猜 DOM 位置可靠得多——"XX万字"格式全站统一，且不会误匹配人气值。

## 五、实测数据

| 域名 | 书名 | 作者 | 最新章节 | 简介 | 封面 |
|------|------|------|---------|------|------|
| kelexs.com | ✅ | ✅ | ✅ 第43章 混战（二合一） | ✅ | ✅ |
| shoudaxsw.com | ✅ | ✅ 午夜深更人 | ✅ 第111章 | ✅ | ✅ |
| shuwuwan.com | ✅ | ✅ | ✅ | ✅ | ✅ |
| xinghuowxw.com | ✅ | ✅ | ✅ | ✅ | ✅ |
| x630xsw.com | ✅ | ✅ | ✅ | ✅ | ✅ |
| dadawx.com | ✅ 女总裁的神级保镖 | ✅ 霉干菜烧饼 | ✅ 第765章 大结局 | ✅ | ✅ bookimg/291.jpg |
| boluomao1.com | ✅(h1) | ✅(分支) | ✅(分支) | ✅(解码) | ✅ |
