# AES 加密目录接口逆向 —— 密钥藏在书籍页模板 JS 里

> 适用：rrssk 聚合家族全站点（kelexs/x630xsw/369shuba/qpmk/dadawx 等）

## 一、机制分析

这类站点目录**不在 HTML 里**，而是加密 API：

```
POST {host}/index.php?action=loadChapterPage
body: data=<AES_CBC_PKCS7(JSON.stringify({id: 书籍id, page: 页码}))的URL编码>
返回: {"data": [{chaptername, chapterurl, chapterorder, ...}, ...]}
```

密钥（secretKey 32位 + ivKey 16位）**每日/每站随机**，藏在书籍页引用的某个模板 JS 里：

```html
<script src="/templates/js/P2eLpItHT9sN7DemGZtMHuxrKWTjl5xA.js"></script>
```

JS 内容形如：

```javascript
class AESCrypt {
    constructor(secretKey) {
        this.secretKey = CryptoJS.enc.Utf8.parse(secretKey);
        this.iv = CryptoJS.enc.Utf8.parse('8007732341530941');
    }
    ...
}
```

## 二、三个坑

### 坑1：密钥 JS 不一定是第一个
部分站点（x630xsw/369shuba）页面引用多个 `/templates/js/*.js`，第一个是无密钥的公共文件（addons.js/common.js）。**必须遍历全部候选直到命中**：

```javascript
let regex = /src="(\/templates\/js\/[a-zA-Z0-9]{1,}\.js)"/g, m, found = false;
while ((m = regex.exec(result)) !== null) {
  let resp = String(java.ajax(sourceUrl + m[1]));
  let secretKey = (resp.match(/AESCrypt\('(.*?)'\);/) || [])[1];
  let ivKey = (resp.match(/parse\('(.*?)'\);/) || [])[1];
  if (secretKey && ivKey) {
    cache.put(sourceUrl, JSON.stringify({ secretKey, ivKey }));  // 按域名缓存
    found = true; break;
  }
}
```

### 坑2：bookId 与 SEO URL 不同
书籍页 URL 可能是 `/book/eftdep.html`（SEO 串），但目录接口用的 id 是 `/book/eft-1.html` 里的 `eft`。从 meta 提取：

```javascript
let bookId = result.match(/content=".*\/book\/(.*?)\.html"/)[1];  // og:url 里的才是真 id
```

### 坑3：目录页数未知
先请求书籍页/章节页，数 `[data-aid="{id}"]` 元素个数得到总页数，再循环 POST：

```javascript
let pages = java.getElements('[data-aid="' + id + '"]@li||[data-aid="' + id + '"]@option').length;
for (let page = 1; page <= pages; page++) {
  let cipher = java.createSymmetricCrypto("aes/cbc/pkcs7padding",
    java.strToBytes(secretKey), java.strToBytes(ivKey))
    .encryptBase64(JSON.stringify({ id, page }));
  let url = host + "/index.php?action=loadChapterPage," + JSON.stringify({
    "body": "data=" + encodeURIComponent(cipher), "method": "POST",
    "headers": JSON.stringify({"Referer": host + "/", "Origin": host,
      "X-Requested-With": "XMLHttpRequest"})   // 防WAF，见GOEDGE文档
  });
  // 返回 JSON 的 .data 数组逐章 push
}
```

## 三、缓存策略

密钥按域名存 `cache.put(sourceUrl, ...)`，目录 JS 里 `cache.get(server)` 读取——同一站点多次取目录不重复请求密钥 JS。注意**密钥会轮换**，若接口突然返回非 JSON（HTML），需清缓存重跑 init。

## 四、验证清单

- [ ] bookId 从 og:url 提取（非地址栏 SEO 串）
- [ ] 密钥 JS 遍历命中（日志输出"密钥来源: xxx.js"）
- [ ] POST 带 Referer/Origin/X-Requested-With（GOEDGE WAF 会拦裸 POST）
- [ ] 返回 JSON 解析 `.data` 数组，按 `chapterorder` 排序
