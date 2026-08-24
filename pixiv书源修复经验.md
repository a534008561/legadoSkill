# Pixiv 书源免VPN修复经验总结

> 适用于 Legado(阅读) 3.x 及各fork版本。当Pixiv书源登录失败时，按此文档排查和修复。

---

## 一、问题根因

### 2026年pixiv基础设施变更

| 变更项 | 影响 |
|---|---|
| oauth.secure.pixiv.net 迁移到 Cloudflare | 老的"域名替换成210.140.139.155再POST"方案失效 |
| GFW 对 *.pixiv.net 做SNI重置 | 即使DNS正确，TLS握手时SNI包含"pixiv.net"就会被RST |
| nginx 对 HTTP/2 连接强制校验SNI↔Host一致性 | Legado的HTTP栈(java.connect/jsoup)协商h2 → 返回421 Misdirected Request |

### 关键发现（核心知识点）

```
纯HTTP/1.1（无ALPN扩展）→ nginx宽松按Host头路由 → 可达后端 ✓
HTTP/2（ALPN含h2）    → nginx强制SNI↔Host校验     → 421拒绝 ✗
```

Legado所有HTTP方法（java.connect/java.post/jsoup）都会协商h2，
这就是为什么在规则里直接调用会挂起或返回421。

---

## 二、解决方案：原始TLS套接字直连

### 原理

用 `Packages.javax.net.ssl.SSLSocketFactory` 创建原始TLS连接：
- URL为IP地址 → 不发送SNI → 绕过GFW DPI
- 不协商ALPN → 避免HTTP/2 → 走HTTP/1.1宽松路由
- 手写HTTP/1.1报文 → Host头路由到oauth虚拟主机
- 证书为Google Trust Services公共证书（含*.pixiv.net SAN），系统默认信任

### 可用的东京源站IP

```
210.140.139.155  ← 主要使用
210.140.139.152
210.140.139.158
210.140.139.161
```

这些IP属于pixiv东京源站段，能通过default vhost伺服pixiv各域名。

---

## 三、自包含 pxOauth 函数（复制即用）

以下函数不依赖任何 `java.xxx()` 扩展方法，兼容所有Legado版本/fork。
时间格式化用纯JS实现，MD5用Java核心API MessageDigest。

```javascript
function pxOauth(postBody) {
    // --- 时间格式化(UTC+8, 纯JS) ---
    var nowMs = Date.now() + 28800000;
    var d = new Date(nowMs);
    function pad(n){ return ('0' + n).slice(-2); }
    var time = d.getUTCFullYear()+'-'+pad(d.getUTCMonth()+1)+'-'+pad(d.getUTCDate())
        +'T'+pad(d.getUTCHours())+':'+pad(d.getUTCMinutes())+':'+pad(d.getUTCSeconds())+'+00:00';

    // --- MD5 (Java核心API, 所有版本必有) ---
    var md = Packages.java.security.MessageDigest.getInstance("MD5");
    md.update(new Packages.java.lang.String(time + '28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c').getBytes("UTF-8"));
    var digestBytes = md.digest();
    var hashStr = '';
    for (var hi = 0; hi < digestBytes.length; hi++) {
        var bVal = digestBytes[hi] & 0xFF;
        hashStr += (bVal < 16 ? '0' : '') + bVal.toString(16);
    }

    // --- 构建HTTP/1.1报文 ---
    var req = 'POST /auth/token HTTP/1.1\r\nHost: oauth.secure.pixiv.net\r\n'
        + 'User-Agent: PixivAndroidApp/5.0.166 (Android 14; RMX3366)\r\n'
        + 'content-type: application/x-www-form-urlencoded\r\n'
        + 'x-client-time: ' + time + '\r\nx-client-hash: ' + hashStr + '\r\n'
        + 'accept-language: zh-CN\r\napp-os: Android\r\napp-os-version: Android 14\r\napp-version: 5.0.166\r\n'
        + 'Content-Length: ' + postBody.length + '\r\nConnection: close\r\n\r\n' + postBody;

    // --- 原始TLS套接字直连 ---
    var sf = Packages.javax.net.ssl.SSLSocketFactory.getDefault();
    var ips = ['210.140.139.155', '210.140.139.152', '210.140.139.158', '210.140.139.161'];
    var sock = null, lastErr = '';
    for (var pi = 0; pi < ips.length; pi++) {
        try {
            var addr = Packages.java.net.InetAddress.getByName(ips[pi]);
            sock = sf.createSocket(addr, 443);
            sock.setSoTimeout(12000);
            var os = sock.getOutputStream();
            os.write(new Packages.java.lang.String(req).getBytes('UTF-8'));
            os.flush();
            var rd = new Packages.java.io.BufferedReader(new Packages.java.io.InputStreamReader(sock.getInputStream(), 'UTF-8'));
            var sb = new Packages.java.lang.StringBuilder();
            var line;
            while ((line = rd.readLine()) != null) { sb.append(line); sb.append('\n'); }
            return String(sb.toString());
        } catch (e) {
            lastErr = e;
            try { if (sock != null) sock.close(); } catch (e2) {}
        }
    }
    throw lastErr == '' ? 'oauth直连失败' : lastErr;
}
```

在 login() 中调用方式：

```javascript
// 在login()中，构造好body之后：
try {
    var rr = pxOauth(body);
    // rr 包含 HTTP响应头+JSON体，需要剥离头部
    if (rr.indexOf('{') >= 0) rr = rr.substring(rr.indexOf('{'));
    var atk = rr.match(/"access_token":"([^"]+)"/)[1];
    source.putLoginHeader(atk);
    // ... 后续处理
    return; // 成功直接返回
} catch(e) {
    java.log('px oauth直连失败：' + e);
    // 回退到常规请求路径...
}
```

---

## 四、timemd5 兼容性修复

原始 timemd5 依赖 `java.md5Encode`，部分Legado版本没有这个方法。
添加自动降级链：优先用扩展方法，失败则降级到Java核心API。

### 修复前（仅部分版本可用）
```javascript
function timemd5(time) {
    const {java, source} = this;
    let salt = '28c1fdd...';
    let hash = java.md5Encode(time + salt);  // ← 部分版本报错
    return hash;
}
```

### 修复后（全版本兼容）
```javascript
function timemd5(time) {
    var saltStr = time + '28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c';
    try {
        var jv = this.java || (typeof java !== 'undefined' ? java : null);
        if (jv && jv.md5Encode) return jv.md5Encode(saltStr);
    } catch(e) {}
    // 回退：Java核心API
    var md = Packages.java.security.MessageDigest.getInstance("MD5");
    md.update(new Packages.java.lang.String(saltStr).getBytes("UTF-8"));
    var dg = md.digest();
    var hx = '';
    for (var di = 0; di < dg.length; di++) {
        var bv = dg[di] & 0xFF;
        hx += (bv < 16 ? '0' : '') + bv.toString(16);
    }
    return hx;
}
```

---

## 五、翻译功能修复要点

### 微软免费认证端点已全球停用

`edge.microsoft.com/translate/auth` 返回404（海外也一样），不是GFW问题。
这意味着源2原有的免费微软翻译通道彻底死亡。

### 替代方案

| 方案 | 端点 | 密钥 | 国内可达 | 质量 |
|---|---|---|---|---|
| **Azure官方API** | api.cognitive.microsofttranslator.com | 需要（F0免费档月200万字符） | ✅ 378ms | ★★★ |
| **腾讯TranSmart** | transmart.qq.com/api/imt | 不需要 | ✅ 233ms | ★★ |
| **MyMemory** | api.mymemory.translated.net/get | 不需要 | ✅ 1360ms | ★ |

### ⚠️ 关键教训：腾讯API必须用 java.post 而非 java.connect

`java.connect()` 在阅读器解析线程中调用外部API时会挂起。
改用 `java.post()` 后立即正常（233ms返回）。

```javascript
// ✗ 挂起
let r = java.connect(url + ',' + JSON.stringify({method:'POST', body:..., headers:{...}}));

// ✓ 正常
let r = java.post(url, reqBody, {'content-type':'application/json', 'referer':'...'});
```

### 腾讯 TranSmart 请求格式

```
POST https://transmart.qq.com/api/imt
Content-Type: application/json

{
    "header": {"fn": "auto_translation", "session": "", "client_key": "browser-chromium-131.0.0.0"},
    "type": "plain",
    "model_category": 1,
    "text_domain": 0,
    "source": {"lang": "ja", "text_list": ["日文1", "日文2"]},
    "target": {"lang": "zh"}
}
```

响应：
```json
{
    "header": {"ret_code": "succ", ...},
    "auto_translation": ["中文1", "中文2"],
    "src_lang": "ja",
    "tgt_lang": "zh"
}
```

实测批量12条完美对齐、R18内容无审核拦截。

---

## 六、排查清单

当Pixiv书源失效时，按以下顺序排查：

### 1. 登录失败
```
□ pxOauth函数是否存在且为自包含版（检查是否含 MessageDigest）
□ 东京IP列表是否最新（210.140.139.155/152/158/161）
□ token是否过期（access_token有效期3600秒，过期应自动刷新）
□ refresh_token是否已失效（invalid_grant → 需重新获取token）
```

### 2. 搜索/详情/目录/正文失败
```
□ gethd() 是否正常（依赖 timemd5 → java.md5Encode 或 MessageDigest回退）
□ access_token 是否有效（loginCheckJs 应在400时自动刷新）
□ 直连IP 210.140.139.155 是否仍可达
```

### 3. 翻译失败
```
□ 微软密钥(Azure)是否填写 → 有则走官方API
□ 无密钥时走腾讯通道 → 检查 java.post 是否可用
□ 腾讯接口是否被限流 → 尝试减少批量条数
□ 如果全部超时 → 暂时关闭翻译(trans=0)，等接口恢复
```

---

## 七、技术原理详解

### 为什么不发SNI就能绕过GFW？

GFW的DPI（深度包检测）在TLS ClientHello阶段读取SNI扩展字段。
如果SNI包含被封锁的域名（如*.pixiv.net），立即注入RST断开连接。

当URL为IP地址时，JSSE/OkHttp不会发送SNI扩展（RFC 6066不允许IP作为SNI）。
因此整个TLS握手中不存在明文的"pixiv.net"字符串，GFW无从匹配。

### 为什么不带ALPN能避免421？

nginx对HTTP/2连接实施严格的连接复用安全策略：
- TLS握手时通过ALPN协商出h2协议
- h2连接上收到请求时，nginx校验请求的:authority（或Host）是否与TLS握手的SNI一致
- 不一致则返回421 Misdirected Request

而HTTP/1.1没有这种校验机制，Host头可以自由指定。
所以只要确保ALPN中不出现"h2"，就能以HTTP/1.1模式绕过校验。

### 为什么证书验证能通过？

210.140.139.155 返回的默认证书：
- Subject: CN=pixiv.net
- SAN: DNS:pixiv.net, DNS:*.pixiv.net, DNS:oauth.secure.pixiv.net, ...
- Issuer: Google Trust Services (WR1)

这是公共CA签发的正规证书，Android系统信任库默认包含Google Trust Services根证书。
因此 `SSLSocketFactory.getDefault().createSocket()` 创建的连接可以通过标准证书链验证。

---

## 八、相关文件

| 文件 | 说明 |
|---|---|
| 源1_兼容修复版.json | 🌈pixiv小说 原版（基础阅读） |
| 源2_兼容修复版.json | 🌈pixiv小说🙈 自动翻译版（需Azure密钥启用翻译） |
| 源3_兼容修复版.json | 🌈pixiv小说 漫画+小说双支持版 |

