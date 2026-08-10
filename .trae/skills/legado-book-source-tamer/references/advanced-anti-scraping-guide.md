# 高级反爬与加密实战指南

> 本文档汇总实战中遇到的高级反爬技术、加密方案和修复策略，补充基础技能文档中未覆盖的内容。
>
> 这些知识点均来自真实书源开发实战，基础技能文档（如 `方法-加密解密.md`、`javascript-guide.md` 等）中已有覆盖的通用知识不再重复。

---

## 目录

1. [AES 密钥零填充模式](#1-aes-密钥零填充模式)
2. [跨域搜索架构（bookUrlPattern）](#2-跨域搜索架构bookurlpattern)
3. [onclick 属性多层 URL 解码](#3-onclick-属性多层-url-解码)
4. [PUA 私有区字体反爬（索引映射法）](#4-pua-私有区字体反爬索引映射法)
5. [动态 AES 密钥/IV 提取与缓存](#5-动态-aes-密钥iv-提取与缓存)
6. [AJAX 403 回退策略：内容页爬取法](#6-ajax-403-回退策略内容页爬取法)
7. [select 下拉框分页计数法](#7-select-下拉框分页计数法)
8. [javax.crypto 直接调用模式](#8-javaxcrypto-直接调用模式)
9. [Jsoup.connect() 批量请求](#9-jsoupconnect-批量请求)
10. [动态密钥派生：MD5(UA + num)](#10-动态密钥派生md5ua--num)
11. [OG meta 标签提取模式](#11-og-meta-标签提取模式)
12. [result.attr() 属性访问](#12-resultattr-属性访问)
13. [网站结构变更检测与迁移](#13-网站结构变更检测与迁移)

---

## 1. AES 密钥零填充模式

### 场景

许多小说网站使用 AES-CBC 加密搜索关键词，但密钥长度不足 32 字节（AES-256 要求）。常见做法是将短密钥用 `\0`（空字符）填充到 32 字节。

### 技术要点

- AES-256-CBC 需要 32 字节密钥 + 16 字节 IV
- 网站常使用 16 字符的字符串作为密钥，用 `\0` 填充至 32 字节
- IV 通常也使用相同字符串的前 16 字节（或同样零填充至 16 字节）
- 基础技能文档已覆盖 `createSymmetricCrypto` 的标准用法，但未涉及零填充扩展

### 代码示例

```javascript
// searchUrl 中的 AES 加密
var keyStr = 'lzxHpH8PLGXcrCIQ';  // 16字符密钥
var key32 = keyStr;
while (key32.length < 32) {
    key32 += String.fromCharCode(0);  // 零填充至32字节
}
var crypto = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', key32, keyStr);
var enc = crypto.encryptBase64(key);
var url = 'https://example.com/?keyword=' + java.encodeURI(enc) + '&page=' + page;
url
```

### Python 验证

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

key_str = b'lzxHpH8PLGXcrCIQ'
key32 = key_str + b'\x00' * (32 - len(key_str))  # 零填充
iv = key_str + b'\x00' * (16 - len(key_str))     # IV同样零填充

cipher = AES.new(key32, AES.MODE_CBC, iv)
encrypted = cipher.encrypt(pad(keyword.encode('utf-8'), AES.block_size))
enc_b64 = base64.b64encode(encrypted).decode('utf-8')
```

### 注意事项

- `java.createSymmetricCrypto` 接受字符串参数，内部会自动处理编码
- 零填充是 `String.fromCharCode(0)`，不是空字符串
- PKCS5Padding 和 PKCS7Padding 在 AES 中等价（块大小 16 字节）

---

## 2. 跨域搜索架构（bookUrlPattern）

### 场景

搜索引擎网站（如 rrssk.com）提供搜索功能，但书籍详情和内容在另一个域名（如 kelexs.com）。搜索结果的 bookUrl 指向 kelexs.com，而 bookSourceUrl 是 rrssk.com。

### 技术要点

- `bookSourceUrl` 保持搜索引擎域名
- `searchUrl` 指向搜索引擎
- 搜索结果的 `bookUrl` 解码后指向内容站域名
- **必须设置 `bookUrlPattern`** 匹配内容站 URL，否则 Legado 无法正确识别书籍归属

### 配置示例

```json
{
    "bookSourceUrl": "https://www.rrssk.com/",
    "bookUrlPattern": "https?://www\\.kelexs\\.com/book/\\w+\\.html",
    "searchUrl": "<js>...搜索URL生成...</js>",
    "ruleSearch": {
        "bookUrl": "<js>...解码得到kelexs.com URL...</js>"
    },
    "ruleBookInfo": {
        "name": "meta[property=og:novel:book_name]@content"
    }
}
```

### 注意事项

- `bookUrlPattern` 是正则表达式，需要正确转义
- 如果不设置 `bookUrlPattern`，Legado 可能无法将搜索结果书籍与书源关联
- 跨域时 `header` 字段尤为重要，需确保两个域名都能正常访问

---

## 3. onclick 属性多层 URL 解码

### 场景

网站将书籍 URL 隐藏在 `onclick` 属性中，经过多层编码：URL 编码 -> 提取参数 -> URL 解码 -> Base64 解码。

### HTML 结构示例

```html
<div class="book-card" onclick="window.open('%3Faction%3Dgo%26t%3DaHR0cHM6Ly93d3cua2VsZXhzLmNvbS9ib29rL0FIR0ZHQTAuaHRtbA%253D%253D', '_blank')">
```

### 解码流程

```
原始onclick值: %3Faction%3Dgo%26t%3DaHR0cHM6Ly93d3cua2VsZXhzLmNvbS9ib29rL0FIR0ZHQTAuaHRtbA%253D%253D
    ↓ URL解码
?action=go&t=aHR0cHM6Ly93d3cua2VsZXhzLmNvbS9ib29rL0FIR0ZHQTAuaHRtbA%3D%3D
    ↓ 提取t参数
aHR0cHM6Ly93d3cua2VsZXhzLmNvbS9ib29rL0FIR0ZHQTAuaHRtbA%3D%3D
    ↓ URL解码
aHR0cHM6Ly93d3cua2VsZXhzLmNvbS9ib29rL0FIR0ZHQTAuaHRtbA==
    ↓ Base64解码
https://www.kelexs.com/book/AHGFGA0.html
```

### 代码示例

```javascript
// ruleSearch.bookUrl
var oc = '';
try {
    oc = result.attr ? result.attr('onclick') : String(result);
} catch(e) {
    oc = String(result);
}
var m = oc.match(/open\('([^']+)'/);
if (m) {
    var path = decodeURIComponent(m[1]);
    var t = path.match(/t=([^&]+)/);
    if (t) {
        var b64 = t[1];
        try { b64 = decodeURIComponent(b64); } catch(e) {}
        result = String(java.base64Decode(b64));
    } else {
        result = '';
    }
} else {
    result = '';
}
```

### 注意事项

- `result.attr('onclick')` 在 JS 规则中可获取元素属性（详见 [result.attr() 属性访问](#12-resultattr-属性访问)）
- 多层 URL 编码需要多次 `decodeURIComponent`
- Base64 的 `=` 号在 URL 中会被编码为 `%3D`，需要先 URL 解码再 Base64 解码
- `java.base64Decode()` 返回的是字节数组，需要 `String()` 包装

---

## 4. PUA 私有区字体反爬（索引映射法）

### 场景

网站将敏感词替换为自定义字体图标 `<i class="icon icon-uniEXXX"></i>`，通过 PUA（Private Use Area）码位 U+E001 ~ U+E101 显示。需要将 PUA 码位映射回真实字符。

### 与 queryTTF/replaceFont 的区别

基础技能文档 `方法-JS扩展类.md` 已覆盖 `queryTTF` + `replaceFont` 的字体反爬方法（需下载字体文件自动解析映射）。本节介绍的是**索引映射法**，适用于已知映射表的场景。

| 方法 | 适用场景 | 优势 | 劣势 |
|------|----------|------|------|
| `java.queryTTF` + `java.replaceFont` | 有字体文件 URL，自动解析映射 | 自动化，通用 | 需要下载字体文件 |
| 索引映射法 | 已知映射表，PUA 码位范围固定 | 快速，无需下载 | 需要预先分析字体获取映射表 |

### 技术要点

- 敏感词被替换为 `<i class="icon icon-uniXXXX"></i>` 标签
- 字体文件将 PUA 码位映射到自定义字形
- 解码方法：提取 `uniXXXX` 的十六进制码位 -> 用 source 字符串按索引替换
- 特殊位置可能需要特殊映射（如位置 43 映射为 "AV"）

### 代码示例

```javascript
// ruleContent.content
var html = String(result);
var source = "敏感词暂时替换破";  // 257字符的映射表
var replacementChars = source.split("");
replacementChars[43] = "AV";  // 位置43特殊映射为两个字符

// 步骤1：将 <i class="icon icon-uniXXXX"></i> 替换为对应字符
html = html.replace(/<i class="icon icon-uni([0-9a-fA-F]{4})"><\/i>/g, function(_, p1) {
    return String.fromCharCode(parseInt(p1, 16));
});

// 步骤2：将PUA码位(U+E001~U+E101)映射回真实字符
var decoded = [];
for (var i = 0; i < html.length; i++) {
    var code = html.charCodeAt(i);
    if (code >= 0xE001 && code <= 0xE101) {
        decoded.push(replacementChars[code - 0xE001]);
    } else {
        decoded.push(html.charAt(i));
    }
}
html = decoded.join('');

// 步骤3：用Jsoup解析提取正文
var doc = Packages.org.jsoup.Jsoup.parse(html);
var contentDiv = doc.selectFirst('div.content');
// ... 提取段落文本
```

### 注意事项

- ES5 兼容：必须用 `var` 不用 `let/const`，用 `function` 不用箭头函数，用 `for` 循环不用 `Array.from`
- source 字符串的长度和内容因网站而异，需要从字体文件分析获取
- 位置 43 映射为两个字符 "AV" 是特殊情况，需要根据实际字体调整
- `Packages.org.jsoup.Jsoup.parse()` 可在 JS 中直接解析 HTML

---

## 5. 动态 AES 密钥/IV 提取与缓存

### 场景

网站的章节数据加密使用的 AES 密钥和 IV 不是固定的，而是动态生成并嵌入在外部 JS 文件中。需要先获取 JS 文件，用正则提取密钥和 IV，然后缓存供后续使用。

### 技术要点

- 基础技能文档已覆盖 `cache.put/cache.get` 的基本用法，本节侧重**实战中动态密钥提取+缓存+兜底的完整模式**
- 密钥和 IV 存储在外部 JS 文件中（如 `/templates/js/xxxxx.js`）
- JS 文件中包含 `new AESCrypt('32位密钥')` 和 `CryptoJS.enc.Utf8.parse('16位IV')`
- 使用 `cache.put()` 缓存密钥，设置 24 小时过期（86400 秒）
- 缓存未命中时重新获取，并提供硬编码兜底值

### 代码示例

```javascript
// ruleBookInfo.tocUrl 中预提取密钥
var tocUrl = baseUrl.replace('/book/', '/chapter/');
try {
    var html = java.ajax(book.bookUrl);
    if (html) {
        // 从HTML中提取JS文件路径
        var jsMatch = html.match(/src="(\/templates\/js\/[A-Za-z0-9]+\.js)"/);
        if (jsMatch) {
            var jsUrl = 'https://www.kelexs.com' + jsMatch[1];
            var jsContent = java.ajax(jsUrl);
            if (jsContent) {
                // 正则提取AES密钥和IV
                var keyMatch = jsContent.match(/new AESCrypt\('([A-Za-z0-9]{32})'\)/);
                var ivMatch = jsContent.match(/CryptoJS\.enc\.Utf8\.parse\('(\d{16})'\)/);
                if (keyMatch) {
                    cache.put('kelexs_key', keyMatch[1], 86400);
                }
                if (ivMatch) {
                    cache.put('kelexs_iv', ivMatch[1], 86400);
                }
            }
        }
    }
} catch(e) {}
tocUrl
```

### 兜底策略

```javascript
// ruleToc.nextTocUrl 中使用缓存密钥
var keyStr = cache.get('kelexs_key');
var ivStr = cache.get('kelexs_iv');

// 缓存未命中时重新获取
if (!keyStr || !ivStr) {
    try {
        var html = java.ajax(book.bookUrl);
        // ... 提取逻辑同上
    } catch(e) {}
}

// 硬编码兜底
if (!keyStr) { keyStr = 'fx2zcphhn3MhznJlrfGMXN7ZefBa6eny'; }
if (!ivStr) { ivStr = '5486678252717425'; }
```

### 注意事项

- `cache.put(key, value, expireSeconds)` 第三个参数是过期时间（秒）
- `cache.get(key)` 返回 null 表示缓存未命中
- 硬编码兜底值会过期，需要定期更新
- 密钥提取正则要根据实际 JS 代码调整

---

## 6. AJAX 403 回退策略：内容页爬取法

### 场景

网站的 AJAX 章节分页接口被 CDN 封锁（返回 403 Forbidden），无法直接使用。回退策略是逐个请求内容页 `/book/{ID}-{N}.html`，从每个页面提取 `<h1>` 标题作为章节名。

### 技术要点

- AJAX 接口返回 403 时，改用 HTML 页面爬取
- 内容页 URL 格式通常为 `/book/{bookId}-{chapterNum}.html`
- 使用 `Packages.org.jsoup.Jsoup.connect()` 直接请求（绕过 Legado 的 ajax 封装）
- 分批处理（每批 30 章），避免请求过多
- 通过 `Math.min(maxKnown, totalPages * 100)` 限制总章节数

### 代码示例

```javascript
// ruleToc.chapterList - 内容页爬取法
var html = String(result);
var doc = Packages.org.jsoup.Jsoup.parse(html);
var chapters = [];
var chapterMap = {};

// 步骤1：从目录页提取已知章节
var chapterLinks = doc.select('.chapListBody li a');
for (var i = 0; i < chapterLinks.size(); i++) {
    var a = chapterLinks.get(i);
    var chUrl = String(a.attr('href'));
    var chName = String(a.text());
    if (chUrl && chName) {
        var numMatch = chUrl.match(/-(\d+)\.html/);
        if (numMatch) {
            chapterMap[parseInt(numMatch[1])] = chName;
        }
    }
}

// 步骤2：确定总章节数
var dropDown = doc.selectFirst('.dropDown');
if (dropDown) {
    var aid = String(dropDown.attr('data-aid'));
    var pageItems = doc.select('.dropDown li[data-p]');
    var totalPages = pageItems.size();
    var knownNums = Object.keys(chapterMap).map(Number);
    var maxKnown = Math.max.apply(null, knownNums);
    var maxChapter = Math.min(maxKnown, totalPages * 100);

    // 步骤3：找出缺失章节
    var missing = [];
    for (var n = 1; n <= maxChapter; n++) {
        if (!chapterMap[n]) {
            missing.push(n);
        }
    }

    // 步骤4：分批爬取缺失章节标题
    var batchSize = 30;
    for (var b = 0; b < missing.length; b += batchSize) {
        var batch = missing.slice(b, b + batchSize);
        for (var bi = 0; bi < batch.length; bi++) {
            var chNum = batch[bi];
            var fullUrl = 'https://www.kelexs.com/book/' + aid + '-' + chNum + '.html';
            try {
                var conn = Packages.org.jsoup.Jsoup.connect(fullUrl)
                    .userAgent('Mozilla/5.0 (Linux; Android 12; Pixel 6) ...')
                    .timeout(5000)
                    .get();
                var h1 = conn.selectFirst('h1');
                var title = h1 ? String(h1.text()).trim() : '';
                if (title) {
                    chapterMap[chNum] = title;
                }
            } catch(e) {}
        }
    }

    // 步骤5：按序号排序生成章节列表
    chapters = [];
    var nums = Object.keys(chapterMap).map(Number).sort(function(a, b) { return a - b; });
    for (var ni = 0; ni < nums.length; ni++) {
        var num = nums[ni];
        var url = '/book/' + aid + '-' + num + '.html';
        var name = chapterMap[num] || ('第' + num + '章');
        chapters.push('<li><a href="' + url + '">' + name + '</a></li>');
    }
}

'<html><body><ul>' + chapters.join('') + '</ul></body></html>';
```

### 注意事项

- `Jsoup.connect()` 需要设置 User-Agent 和 timeout（详见 [Jsoup.connect() 批量请求](#9-jsoupconnect-批量请求)）
- 批量请求会增加加载时间，需告知用户"目录加载时间较长"
- `Math.min(maxKnown, totalPages * 100)` 避免请求过多无效章节
- 此方法是 AJAX 被封后的回退方案，优先尝试 AJAX 接口

---

## 7. select 下拉框分页计数法

### 场景

网站的章节目录使用 `<select>` 下拉框分页，没有明确的"下一页"按钮。需要从 select 的 option 数量判断总页数，自动翻页。

### 技术要点

- 章节目录页有 `<select>` 下拉框，每个 `<option>` 代表一页
- 从 `baseUrl` 解析当前页码
- 从 option 数量确定最大页数
- 当前页 < 最大页时，生成下一页 URL

### 代码示例

```javascript
// ruleToc.nextTocUrl
var m = baseUrl.match(/[?&]page=(\d+)/);
var cur = m ? parseInt(m[1]) : 1;
var opts = result.match(/<option\s+value="(\d+)"/g);
if (opts) {
    var mx = 0;
    for (var i = 0; i < opts.length; i++) {
        var om = opts[i].match(/"(\d+)"/);
        if (om) {
            var p = parseInt(om[1]);
            if (p > mx) mx = p;
        }
    }
    if (cur < mx) {
        var base = baseUrl.replace(/[?&]page=\d+/, '');
        result = base + '?page=' + (cur + 1);
    } else {
        result = '';
    }
} else {
    result = '';
}
```

### 注意事项

- `result` 在 nextTocUrl 中是当前页面的 HTML 内容
- `baseUrl` 是当前请求的 URL
- 返回空字符串 `''` 表示没有下一页，停止加载
- option 的 value 属性可能是页码数字，需要用正则提取

---

## 8. javax.crypto 直接调用模式

### 场景

当 `java.createSymmetricCrypto` 无法满足需求时（如需要从加密数据中提取 IV、使用非标准密钥派生），直接调用 Java 的 `javax.crypto` 包。

### 常用 Java 类

```javascript
var Cipher = Packages.javax.crypto.Cipher;
var SecretKeySpec = Packages.javax.crypto.spec.SecretKeySpec;
var IvParameterSpec = Packages.javax.crypto.spec.IvParameterSpec;
var MessageDigest = Packages.java.security.MessageDigest;
var Arrays = Packages.java.util.Arrays;
var Base64 = Packages.android.util.Base64;
var JString = Packages.java.lang.String;
```

### 加密示例

```javascript
function encrypt(data, keyStr, ivStr) {
    var keyBytes = new JString(keyStr).getBytes('UTF-8');
    var ivBytes = new JString(ivStr).getBytes('UTF-8');
    var secretKey = new SecretKeySpec(keyBytes, 'AES');
    var ivSpec = new IvParameterSpec(ivBytes);
    var cipher = Cipher.getInstance('AES/CBC/PKCS5Padding');
    cipher.init(Cipher.ENCRYPT_MODE, secretKey, ivSpec);
    var encrypted = cipher.doFinal(new JString(data).getBytes('UTF-8'));
    return String(Base64.encodeToString(encrypted, 2));  // 2 = NO_WRAP
}
```

### 解密示例（IV 从密文提取）

```javascript
function decrypt(encStr, keyBytes) {
    var allBytes = Base64.decode(encStr, 0);  // 0 = DEFAULT
    var iv = Arrays.copyOfRange(allBytes, 0, 16);    // 前16字节是IV
    var ct = Arrays.copyOfRange(allBytes, 16, allBytes.length);  // 剩余是密文
    var secretKey = new SecretKeySpec(keyBytes, 'AES');
    var ivSpec = new IvParameterSpec(iv);
    var cipher = Cipher.getInstance('AES/CBC/PKCS5Padding');
    cipher.init(Cipher.DECRYPT_MODE, secretKey, ivSpec);
    var decrypted = cipher.doFinal(ct);
    return String(new JString(decrypted, 'UTF-8'));
}
```

### MD5 哈希（手动实现）

```javascript
function md5Hex(str) {
    var md = Packages.java.security.MessageDigest.getInstance('MD5');
    md.update(new JString(str).getBytes('UTF-8'));
    var digest = md.digest();
    var hex = '';
    for (var j = 0; j < digest.length; j++) {
        var b = digest[j] >= 0 ? digest[j] : digest[j] + 256;
        hex += (b < 16 ? '0' : '') + b.toString(16);
    }
    return hex;
}
```

### 与 java.createSymmetricCrypto 的对比

| 方式 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| `java.createSymmetricCrypto` | 简洁，自动处理编码 | 不够灵活，无法处理特殊填充 | 标准AES/DES加密 |
| `Packages.javax.crypto` 直接调用 | 完全控制，可处理特殊填充 | 代码冗长 | 非标准加密、自定义IV提取 |

### 注意事项

- Java 的 `byte` 类型是有符号的（-128~127），需要 `+ 256` 转换为无符号
- `Base64.encodeToString(bytes, 2)` 中 `2` = NO_WRAP（不加换行符）
- `Base64.decode(str, 0)` 中 `0` = DEFAULT
- `Arrays.copyOf(bytes, length)` 用 `\0` 填充不足部分
- `Arrays.copyOfRange(bytes, from, to)` 提取子数组（包含 from，不包含 to）

---

## 9. Jsoup.connect() 批量请求

### 场景

需要在 JS 规则中发起多个 HTTP 请求（如批量获取章节标题），使用 `Packages.org.jsoup.Jsoup.connect()` 直接调用 Jsoup 库。

### 代码示例

```javascript
var conn = Packages.org.jsoup.Jsoup.connect(fullUrl)
    .userAgent('Mozilla/5.0 (Linux; Android 12; Pixel 6) ...')
    .timeout(5000)
    .get();
var h1 = conn.selectFirst('h1');
var title = h1 ? String(h1.text()).trim() : '';
```

### 与 java.ajax 的区别

基础技能文档已覆盖 `java.ajax()`、`java.connect()`、`java.get()` 等网络请求方法。本节补充 `Jsoup.connect()` 的直接调用方式。

| 方法 | 返回值 | 优势 | 劣势 |
|------|--------|------|------|
| `java.ajax(url)` | 字符串（HTML/JSON） | 简单，自动处理编码 | 无法设置 UA/timeout |
| `java.connect(url, header)` | StrResponse 对象 | 可设置 header | 返回值需额外处理 |
| `Jsoup.connect(url)` | Document 对象 | 可直接用 CSS 选择器，可设置 UA/timeout | 需要导入 Packages |

### 注意事项

- `Jsoup.connect()` 返回的是 Jsoup 的 Document 对象，可直接用 `.select()` 和 `.selectFirst()`
- 必须设置 `.userAgent()` 和 `.timeout()`，否则可能被网站拒绝
- 批量请求时使用分批处理（每批 30 个），避免请求过多
- 用 `try-catch` 包装每个请求，单个失败不影响整体
- `String()` 包装 Jsoup 返回的文本，确保是 JS 字符串类型

---

## 10. 动态密钥派生：MD5(UA + num)

### 场景

网站将搜索结果中的书籍 URL 加密，解密密钥由 `MD5(UserAgent.toLowerCase() + num)` 动态生成，其中 `num` 从页面 JS 中 Base64 解码获取。

### 技术要点

- 解密密钥 = `MD5(UA.toLowerCase() + numStr)`，转小写十六进制
- `numStr` 从页面内嵌 JS 中提取，通常是 Base64 编码的字符串
- 加密后的 URL 前 16 字节是 IV，剩余部分是密文
- 使用 AES-CBC 解密

### 代码示例

```javascript
// jsLib 中的解密函数
function decSearchUrl(encStr, numStr) {
    var ua = 'Mozilla/5.0 (Linux; Android 12; Pixel 6) ...';
    // 密钥 = MD5(UA小写 + num) 的十六进制字符串
    var keyStr = String(java.md5Encode(ua.toLowerCase() + numStr)).toLowerCase();
    var keyBytes = new Packages.java.lang.String(keyStr).getBytes('UTF-8');
    
    // 加密数据 = Base64解码(encStr)，前16字节为IV
    var allBytes = Packages.android.util.Base64.decode(encStr, 0);
    var iv = Packages.java.util.Arrays.copyOfRange(allBytes, 0, 16);
    var ct = Packages.java.util.Arrays.copyOfRange(allBytes, 16, allBytes.length);
    
    var Cipher = Packages.javax.crypto.Cipher;
    var SecretKeySpec = Packages.javax.crypto.spec.SecretKeySpec;
    var IvParameterSpec = Packages.javax.crypto.spec.IvParameterSpec;
    var secretKey = new SecretKeySpec(keyBytes, 'AES');
    var ivSpec = new IvParameterSpec(iv);
    var cipher = Cipher.getInstance('AES/CBC/PKCS5Padding');
    cipher.init(Cipher.DECRYPT_MODE, secretKey, ivSpec);
    var decrypted = cipher.doFinal(ct);
    return String(new Packages.java.lang.String(decrypted, 'UTF-8'));
}
```

### num 提取逻辑

```javascript
// 从页面JS中提取num参数
var scripts = doc.select('script');
for (var i = 0; i < scripts.size(); i++) {
    var sc = String(scripts.get(i).data());
    var idx = sc.indexOf('num');
    if (idx >= 0) {
        var eqIdx = sc.indexOf('=', idx);
        // ... 提取引号内的Base64字符串
        var b64 = sc.substring(qi + 1, qe);
        var bytes = Packages.android.util.Base64.decode(b64, 0);
        numStr = String(new Packages.java.lang.String(bytes, 'UTF-8'));
        break;
    }
}
```

### 注意事项

- UA 必须与书源 `header` 中的 User-Agent 完全一致
- `MD5` 返回 32 字符十六进制字符串，作为 AES 密钥（32字节）
- `Arrays.copyOfRange(bytes, from, to)` 提取字节数组的子数组
- `Base64.decode(str, 0)` 中 `0` 表示 DEFAULT 模式

---

## 11. OG meta 标签提取模式

### 场景

部分网站使用 OpenGraph meta 标签提供书籍元数据，这是最可靠的提取方式之一。

### 技术要点

- OG 标签格式：`<meta property="og:novel:author" content="作者名">`
- 使用 CSS 选择器 `meta[property=og:novel:author]@content` 提取
- 常见 OG 小说标签：book_name、author、category、description、image、latest_chapter_name

### 代码示例

```json
{
    "ruleBookInfo": {
        "name": "meta[property=og:novel:book_name]@content",
        "author": "meta[property=og:novel:author]@content",
        "coverUrl": "meta[property=og:image]@content",
        "intro": "meta[property=og:description]@content",
        "kind": "meta[property=og:novel:category]@content",
        "lastChapter": "meta[property=og:novel:latest_chapter_name]@content"
    }
}
```

### 注意事项

- 不是所有网站都提供完整的 OG 标签
- OG 标签通常比 HTML 结构选择器更稳定（网站改版时 OG 标签较少变化）
- 可与 `||` 运算符配合使用：`meta[property=og:novel:author]@content||.author@text`
- `meta[property=og:image]@content` 提取的封面 URL 可能需要补全域名

---

## 12. result.attr() 属性访问

### 场景

在 JS 规则中需要访问当前元素的 HTML 属性（如 onclick、data-id 等）。

### 技术要点

- `result` 在规则上下文中代表当前匹配的元素
- `result.attr('属性名')` 获取元素属性值
- 需要用 `try-catch` 包装，因为 `result` 可能不是元素对象

### 代码示例

```javascript
// 获取 onclick 属性
var oc = '';
try {
    oc = result.attr ? result.attr('onclick') : String(result);
} catch(e) {
    oc = String(result);
}

// 获取 data-id 属性
var id = '';
try {
    id = result.attr('data-id');
} catch(e) {
    // 回退：从HTML中正则提取
    var html = String(result);
    var m = html.match(/data-id="([^"]+)"/);
    if (m) id = m[1];
}
```

### 注意事项

- `result` 的类型取决于规则上下文（可能是元素、字符串、JSON 对象等）
- `result.attr` 可能不存在（字符串类型没有 attr 方法）
- 总是用 `try-catch` 和 `String()` 包装保证安全
- 备选方案：将 result 转为字符串后用正则提取

---

## 13. 网站结构变更检测与迁移

### 场景

网站更新后，搜索 URL 格式变化（如 `k-{enc}.html` 变为 `?action=result&keyword={enc}`），HTML 结构变化（如 `.rankIBox.searchIBox` 变为 `.book-card`），导致原有书源失效。

### 检测方法

1. **测试原有 URL 格式**：访问旧 URL，检查是否返回 404 或空页面
2. **分析新页面结构**：获取当前搜索结果 HTML，对比旧的选择器是否匹配
3. **检查分页格式**：查看分页链接的 URL 格式是否变化
4. **验证加密方式**：确认搜索关键词的加密方式是否变化

### 修复流程

```
1. 获取原始书源 JSON
2. 测试旧 searchUrl -> 确认 404 或空结果
3. 分析网站新搜索流程：
   a. 在网站搜索框输入关键词
   b. 观察跳转后的 URL 格式
   c. 分析搜索结果 HTML 结构
4. 更新 searchUrl（新URL格式）
5. 更新 ruleSearch（新CSS选择器）
6. 更新 bookUrl 提取规则（如onclick解码方式变化）
7. 添加缺失字段（如 header、bookUrlPattern）
8. 实时验证修复效果
```

### 常见变更模式

| 变更类型 | 旧格式 | 新格式 | 影响字段 |
|----------|--------|--------|----------|
| URL 格式变更 | `k-{enc}.html` | `?action=result&keyword={enc}&page={page}` | searchUrl |
| HTML 结构变更 | `.rankIBox.searchIBox li` | `.book-card` | ruleSearch.bookList |
| URL 提取变更 | `upclick('id')` | `window.open('encoded_url')` | ruleSearch.bookUrl |
| 分页方式变更 | URL 路径分页 | URL 参数分页 | searchUrl, nextTocUrl |

### 注意事项

- 修复时保持非搜索规则不变（ruleBookInfo、ruleToc、ruleContent 通常不受影响）
- 添加 `header` 字段确保请求头正确
- 添加 `bookUrlPattern` 确保跨域 URL 匹配
- 在 bookSourceComment 中记录修复版本和变更内容

---

## 总结

### 知识点分类

| 类别 | 知识点 | 难度 |
|------|--------|------|
| 加密/解密 | AES零填充、javax.crypto直接调用、动态密钥派生MD5(UA+num) | 高 |
| 反爬绕过 | PUA字体索引映射、onclick多层解码、动态密钥提取缓存 | 高 |
| 架构设计 | 跨域搜索bookUrlPattern、AJAX 403内容页爬取回退 | 中 |
| 分页处理 | select下拉框计数 | 中 |
| 规则技巧 | OG meta标签、result.attr()属性访问 | 低 |
| 维护策略 | 网站结构变更检测与迁移 | 中 |

### 实战经验

1. **加密方案优先用 `java.createSymmetricCrypto`**，不满足时再用 `javax.crypto` 直接调用
2. **跨域搜索必须设置 `bookUrlPattern`**，否则书籍无法正确关联
3. **动态密钥必须缓存**，避免每次请求都重新获取 JS 文件
4. **AJAX 被封时优先尝试修改请求头**，无效再考虑内容页爬取回退
5. **网站变更修复时只改搜索相关规则**，详情/目录/正文规则通常不受影响
6. **PUA 字体反爬需要预先分析字体文件**获取映射表，然后硬编码在规则中

---

## 与现有技能文档的关系

| 现有文档 | 已覆盖内容 | 本文档补充内容 |
|----------|-----------|---------------|
| `方法-加密解密.md` | `createSymmetricCrypto` 基本用法 | AES 零填充扩展、javax.crypto 直接调用 |
| `javascript-guide.md` | `cache.put/get`、`jsLib`、网络请求方法 | 动态密钥提取+缓存+兜底完整模式、Jsoup.connect() |
| `方法-JS扩展类.md` | `queryTTF` + `replaceFont` 字体反爬 | PUA 索引映射法（无需下载字体文件） |
| `书源规则：从入门到入土.md` | `\|\|` 运算符基本用法 | （已覆盖，不再重复） |
| `api-discovery-guide.md` | API 发现流程 | （已覆盖，不再重复） |
| `skill-tips-guide.md` | 基本调试技巧 | 网站结构变更检测与迁移 |
| 本文档新增 | - | bookUrlPattern、OG meta、result.attr()、onclick多层解码、select分页、MD5(UA+num)密钥派生 |
