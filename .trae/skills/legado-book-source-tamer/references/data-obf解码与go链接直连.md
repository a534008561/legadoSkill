# data-obf XOR 解码 与 action=go 链接直连

## 一、data-obf 正文/简介加密（菠萝猫体系）

### 1.1 现象

菠萝猫（boluomao1.com）正文和简介不是明文：

```html
<div class="intro font16" id="bookIntro">
    <span class="obf-html font16" data-obf-html="5Kak4YiF47Cf7Z6A4rKD9oay9rGS8q+V/..."></span>
</div>
...
<div class="content">
    <p data-obf="..."></p>
    <p data-obf="..."></p>
</div>
```

`#bookIntro@text` 取出来是**空**（span 无文本节点），正文同理——明文不存在于 DOM。

### 1.2 解码算法

base64 → 字节数组 → 逐字节 XOR `((index % 127) + 1)` → UTF-8：

```javascript
function decodeObf(b64) {
  let bytes = java.base64DecodeToByteArray(String(b64));
  for (let j = 0; j < bytes.length; j++) { bytes[j] = bytes[j] ^ ((j % 127) + 1); }
  return java.bytesToStr(bytes, 'utf-8');
}
```

正文是多段 `<p data-obf>`，需逐段解码再拼接：

```javascript
let arr = java.getStringList('.content@p@data-obf');
let out = [];
for (let i = 0; i < arr.length; i++) out.push(decodeObf(arr[i]));
out.join('\n');
```

### 1.3 验证要点

- 解码后首行应为正常中文，若乱码说明 XOR 起始索引或编码假设错误
- `base64DecodeToByteArray` 与 `base64Decode(s,"ISO-8859-1")` + `charCodeAt` 逐字符异或**等价**（后者是同站另一处写法），任选其一
- 简介与正文用**同一算法**（data-obf-html 与 data-obf 属性）

## 二、action=go 链接直连（搜索结果域名迁移）

### 2.1 现象

rrssk 搜索结果的书籍链接是中转形式：

```html
onclick="window.open('?action=go&t=aHR0cHM6Ly93d3cuYm9sdW9tYW8uY29tL2Jvb2svMjkxMDI0Lmh0bWw%3D&s=Nf%2B%2BUwUUUmQ%3D&e=1787435320', '_blank')"
```

`t` 参数是 base64 编码的真实书籍地址。问题：`action=go` 会 302 到 `www.boluomao.com`，而该域名 **SSL 连接间歇性被重置**（时好时坏），镜像 `www.boluomao1.com` 稳定。

### 2.2 两个失败的尝试

| 尝试 | 失败原因 |
|------|---------|
| 对 go 链接做文本替换 `boluomao.com→boluomao1.com` | t 参数是 **base64**，明文域名在 URL 里根本不出现 |
| 解码 t 后改写再拼回 go 链接 | `s` 参数疑似对 t 的签名，篡改 t 后 go 校验不通过（且无必要） |

### 2.3 正确方案：直接解码 t，跳过中转

```javascript
"bookUrl": "onclick\n@js:\nvar s = String(result);\nvar m = s.match(/[?&]t=([^&]+)/);\nif (m) {\n  var inner = String(java.base64Decode(decodeURIComponent(m[1])));\n  s = inner.replace(/www\\.boluomao\\.com/, 'www.boluomao1.com');\n}\ns;"
```

要点：
- `decodeURIComponent` 先解 URL 编码（`%3D` → `=` 补位符），再 base64 解码
- 解码结果就是完整书籍 URL，**非 BM 域名原样返回**（replace 无命中），对全家族通用
- 附带收益：省一次 302 往返

### 2.4 附带发现

搜索结果的 `onclick` 属性值经 jsoup 解析后 `&amp;` 已自动还原为 `&`，正则直接写 `\&t=` 即可匹配，无需处理实体。

## 三、组合应用场景

| 场景 | 方案 |
|------|------|
| 菠萝猫详情页简介 | `.obf-html@data-obf-html` → XOR 解码 |
| 菠萝猫正文 | `.content@p@data-obf` 列表逐段 XOR 解码 |
| 聚合源搜索 bookUrl（全域名） | go 链接 t 解码直连 + BM 域名镜像改写 |
