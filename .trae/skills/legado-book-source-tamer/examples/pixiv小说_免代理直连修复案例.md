# 案例：🌈pixiv小说 —— 免代理直连修复（四项目拆解 + 大陆实测）

> 日期：2026-10-11 ｜ 成品：`/workspace/pixiv_direct_fix/pixiv_v54_final.json`
> 方法论文档：[方法-GFW-SNI封锁鉴别与绕过边界.md](../references/方法-GFW-SNI封锁鉴别与绕过边界.md) §24

## 一、任务

拆解四个开源项目的国内直连方式，判断哪些能移植到 Legado 书源：
- [Lopution/Parfait](https://github.com/Lopution/Parfait) — Flutter + Rust(rhttp/rustls) + ECH
- [ultranity/Pix-EzViewer](https://github.com/ultranity/Pix-EzViewer) — Kotlin + SSLSocketFactory 替换 SNI + DoH + ECH
- [SYTKILLER/PixLume](https://github.com/SYTKILLER/PixLume) — ArkTS + IP直连 + Host头 + 探测选线
- [darriousliu/PiPixiv](https://github.com/darriousliu/PiPixiv) — Compose MP + 无SNI握手 + CDN别名域

## 二、结论速览

| 通道 | 免代理直连 | 方案 |
|---|---|---|
| **图片/封面** | ✅ **已实现** | 别名域 `b/d/imgaz/source.pximg.net` 纯 URL 替换 |
| **API** | ❌ 无法实现 | 需代理，或等 App 修复 Cronet 的 DNS |

## 三、图片直连（核心成果）

### 3.1 别名域发现
```
i.pximg.net        → 污染(69.63.x/face:b00c) + SNI封锁(RST)     ❌
b.pximg.net        → 210.140.139.129-138 + SNI未封锁 + 200 ✅
d.pximg.net        → 同上 ✅
imgaz.pximg.net    → 同上 ✅
source.pximg.net   → 同上 ✅
```

### 3.2 四条硬特性（决定它优于公共图床）
1. 系统 DNS 干净 → 无需 `dnsIp`
2. SNI 未封锁 → 握手 79-100ms
3. **纯 URL 替换**（无需 Host 头）→ Glide/ImageProvider/WebView 全路径通用
4. 分辨率完全一致（3840×2160），仅 JPEG 重编码

### 3.3 压缩参数剥离（必须）
```
c/240x480_80/...  → 403  ❌
c/240x480/...     → 200  ✅（143KB，比原 41KB 更清晰）
```
正则：`u.replace(/(\/c\/\d+x\d+)_\d+(\/)/, '$1$2')`

### 3.4 性能
```
别名域 79-100ms  vs  公共图床 3200-16000ms   → 快 17-40 倍
真机：封面 632-1132ms；正文插图 1.9MB 4s
```

### 3.5 实现（jsLib 三函数）
```js
var PX_ALIAS = ['b.pximg.net','d.pximg.net','imgaz.pximg.net','source.pximg.net'];
function pxAlias(force){ /* 4候选测速选线，缓存6h */ }
function pxDirect(url){ /* URL改写 + 压缩参数剥离 */ }
function gethdi(url){ /* 直连优先 → 公共图床兜底 → 尾点+dnsIp兜底 */ }
```
+ `header` 补 `Referer: https://www.pixiv.net/`

## 四、API 免代理直连（穷尽验证）

### 4.1 TCP 层 100% 无解（12 种尝试）
真SNI→RST / 空SNI→403 / SNI替换→421 / 备用端口→RST / CDN别名域→RST /
尾点·大小写·punycode·空格→RST / 明文80→403 / TCP分片→SSLEOF / IPv6→RST / 源站直连→RST

★关键：**CF 按 SNI 路由** —— SNI=pixivision.net + Host=app-api → 403

### 4.2 QUIC/HTTP3 完全可用（沙盒大陆出口实测）
```
CF IP + 真SNI + HTTP/3：
  /v1/novel/recommended → 200 完整小说列表
  /v1/search/novel      → 200 搜索结果
  /v2/novel/series      → 200 完整目录
  /webview/v2/novel     → 200 完整HTML
  oauth /auth/token     → 400 正常业务响应
4/4 CF IP 全部第1次成功
```

### 4.3 真机 Cronet 实测（用户开启开关后）
```
✅ cloudflare-quic.com 665ms / www.pixivision.net 574ms / b.pximg.net 458ms
❌ app-api.pixiv.net 31s TIMED_OUT / pixiv.me 33s / fanbox.cc 31s
```
三个卡点（书源侧改不动）：
1. Cronet 的 `AsyncDNS` 走明文 UDP:53 → 污染 IP
2. `dnsIp` 与 Cronet 互斥 → 移除拦截器 → OkHttp(TCP) → RST
3. `HostResolverRules` 被注释（CronetHelper.kt:74）

## 五、四项目移植结论

| 项目 | 机制 | 结果 |
|---|---|---|
| Pix-EzViewer | 替换SNI/空SNI/DoH/ECH | ❌ 替换→421；空→403；ECH 需 Conscrypt 扩展（本App无）|
| PixLume | IP直连+Host头+探测 | ✅ **图片域**（已采用别名域）；❌ API域 |
| PiPixiv | 无SNI+CDN别名域+竞速 | ✅ **别名域思路**（已采用）；❌ cdn.cloudflare.net→RST |
| Parfait | ECH+DoH+阶梯(rustls) | ❌ 需 Rust 原生层 |

## 六、可复用方法论

### 6.1 别名域探测法（适用于任何 CDN 站）
1. DNS 反查同 IP 段的域名（`b.` `d.` `s.` `imgaz.` `source.` 常见前缀）
2. 三重判定：DoH 解析（DNS干净?）→ TLS握手（SNI未封?）→ GET资源（服务?）
3. 优先选**纯 URL 替换即可**的（全路径通用）

### 6.2 沙盒网络位置判据
```bash
curl https://www.cloudflare.com/cdn-cgi/trace | grep loc=   # loc=CN = 大陆
```

### 6.3 区分 DNS 问题 vs SNI 封锁
- **SNI 封锁**：TLS 握手 30-100ms 内 RST（快）
- **DNS 污染**：连到陌生 IP，超时 30s（慢）

## 七、交付

| 文件 | 说明 |
|---|---|
| `pixiv_v54_final.json` | 最终书源（80KB）|
| `build_v5.py`~`build_v54.py` | 构建链（可追溯）|
| `README.md` | 完整报告 |

**dpaste**：v5=FTF9V4U2T / v5.1=A88BRDMZB / v5.2=C8N2VYWXC / v5.3=GAZM5V2GL / v5.4=EU3RVVKH7
