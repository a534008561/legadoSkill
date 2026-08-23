# GOEDGE WAF 应对策略 —— UA 指纹与 POST 请求头

> 适用：boluomao1.com、rrssk 部分站点（x630xsw/369shuba）等使用 GOEDGE 防护的站点

## 一、两种触发模式（实测）

### 模式1：UA 指纹拦截（GET 也拦）
- okhttp 默认 UA / Windows 桌面 Chrome UA → 302 跳转 `/WAF/VERIFY/CAPTCHA`（图片验证码）
- **移动端 UA 直接放行**（Android Chrome / 夸克 UA 实测均通过）

```json
{"User-Agent": "Mozilla/5.0 (Linux; U; Android 13; zh-Hans-CN; PFJM10 Build/TP1A.251121.001) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.4896.58 Quark/10.0.6.960 Mobile Safari/537.36"}
```

**教训**：聚合源里 `header` 字段是桌面 UA 的，所有请求都会被 WAF 拦截且表现为"列表为空"——用 HTTP 日志看实际发出的 UA 才能定位（Legado 分析请求的 UA 可能与 JS 里 java.get 的 UA 不同源）。

### 模式2：裸 POST 拦截
GET 全部放行，但**无 Referer 的 POST** 会被 307 到验证码页（x630xsw/369shuba 的 loadChapterPage 接口实测）。补三个头即可：

```javascript
let hd = JSON.stringify({
  "Referer": host + "/",
  "Origin": host,
  "X-Requested-With": "XMLHttpRequest",
  "Content-Type": "application/x-www-form-urlencoded"
});
let url = host + "/index.php?action=loadChapterPage," + JSON.stringify({
  "body": "data=" + cipher, "method": "POST", "headers": hd
});
```

## 二、识别特征

| 响应特征 | 判断 |
|---------|------|
| 302/307 Location 含 `/WAF/VERIFY/CAPTCHA` | WAF 拦截 |
| 响应体含 `GOEDGE_WAF_CAPTCHA_ID` / `Verify Yourself` | WAF 验证码页 |
| GET 正常但 POST 被拦 | 缺 Referer/Origin |

## 三、调试技巧

1. **开 HTTP 日志**对比"JS 里 java.get 的请求"与"分析器发的请求"的 UA/Cookie 差异
2. Legado 的 `source.header` 只作用于分析器请求；**JS 里 java.get/ajax 必须自己传 headers 对象**，否则用默认 UA
3. 验证码页是死路（需要人肉识图），策略是**预防触发**而不是解验证码
4. 频率也是触发因素：连续快速请求可能临时触发风控，稍等重试即可

## 四、清单

- [ ] 书源 header 使用移动端 UA
- [ ] JS 内所有请求显式传移动端 UA headers
- [ ] POST 请求带 Referer + Origin + X-Requested-With
- [ ] enabledCookieJar 开启（会话 Cookie 自动携带，WAF 放行标记依赖它）
