# 图标字体反爬破解 —— icon-uniEXXX 占位符与 PUA 映射还原

> 症状：正文"漏字"。网页显示完整，抓取后某些字消失。
> 典型：kelexs.com/book/H0G0FK-1393.html 单章 48 处占位符。

## 一、原理

站点把敏感词/常用字替换为**图标字体占位符**：

```html
<i class="icon icon-uniE021"></i>
```

`icon-uni` 后的 4 位 hex（E001~E101）对应 **Unicode 私有区（PUA）** 码位。浏览器加载站点自定义字体，把 PUA 码位渲染成真实汉字；抓取时 `<i>` 标签被丢弃 → 对应的字全部消失，即"漏字"。

## 二、破解（三步）

```javascript
// 1) <i> 占位符 → PUA 字符
let html = String(result).replace(/<i class="icon icon-uni([0-9a-fA-F]{4})"><\/i>/g,
  function(_, p1) { return String.fromCharCode(parseInt(p1, 16)); });

// 2) PUA → 真字映射表（站点前端逻辑同款，第43位特殊：单字符放不下"AV"）
const CHARS = "内暴强情缝肏插逼操潮喷阴艳裸乳荡穴鸡淫苞奸胸射嫩肉骚性蒂茎...秘破";
const rep = CHARS.split('');
rep[43] = 'AV';   // E02A+43-1... 注意：索引43位置是双字符"AV"

// 3) 全文扫描替换
let out = [];
for (let k = 0; k < html.length; k++) {
  let code = html.charCodeAt(k);
  out.push(code >= 0xE001 && code <= 0xE101 ? rep[code - 0xE001] : html.charAt(k));
}
java.setContent(out.join(''));          // 塞回分析器
java.getString('.content@html');        // 再按常规容器提取
```

## 三、关键细节

| 细节 | 说明 |
|------|------|
| 码位区间 | `0xE001 ~ 0xE101`，共 257 个位置；映射串长度需覆盖 |
| `rep[43]='AV'` | 映射表第 43 项是双字符，`split('')` 会拆散，必须整体回填 |
| 先解码后提取 | 必须对**原始 HTML 全文**做字符级扫描（PUA 字符可能落在任意标签间隙），再 `setContent` + 容器提取；先提取后替换会丢字 |
| `java.setContent` | Legado 分析器上下文中可用，塞入新内容后 `java.getString/getElements` 即分析新内容 |
| 映射表版本 | 站点可能更新映射表——再次"漏字"时去 `/templates/js/` 最新 JS 里对照新表 |

## 四、验证方法

```javascript
// 统计占位符与还原数是否一致
let before = (html.match(/<i class="icon icon-uni[0-9a-fA-F]{4}"><\/i>/g)||[]).length;
// 解码后 PUA 计数应 === before，且正文抽样比对无空缺
```

实测：H0G0FK-1393 章 48 个占位符全部还原，逐字对照原网页一致。

## 五、适用范围

kelexs / shuhaoxs / xuanshukan / zhaoshuba / qpmk 等同模板站点。对无占位符的页面是空操作，可无脑全局启用。
