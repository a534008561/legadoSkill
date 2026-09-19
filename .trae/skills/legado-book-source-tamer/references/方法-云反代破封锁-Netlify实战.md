# 方法-云反代破封锁：Netlify Edge Function 实战（pixiv 小说免梯直连蓝本）

> ★2026-09-19 pixiv 书源国内免梯直连最终打通。本文是「被 GFW 封锁站点 + 书源需要 REST API」的通用云反代方案总纲，含可照搬代码、部署步骤、选型对照与故障速查。
> 蓝本：🌈pixiv小说 书源 bookSourceUrl=https://pixiv小说.luoyacheng.ip-ddns.com

## 0. 一句话总结

**给被墙站点做「国内可达的反代」：优先 Netlify Edge Function（AWS 出口，实测 pixiv 放行）——反代代码必须兼容书源「单协议格式」，且 Netlify Edge Functions 部署后必须手动设为 Public。** 家宽/手机住宅 IP 的本地反代是永远可用的保底。

## 1. 适用场景识别

- 目标站点的域名在 GFW SNI 黑名单（如 `*.pixiv.net`，TLS 握手中 SNI 即被 RST，TCP 可达但一发 ClientHello 即断）
- 书源需要访问该站点的 REST API（不是纯静态图片）
- 用户无海外 VPS/代理，但要求国内免梯直连
- 站点封锁是「网络层」（GFW）而非「站点风控」——反代出口 IP 必须不被目标站点拒绝

判据速查：
- TCP 连得通（22ms）但 TLS RST → **SNI 黑名单** → 反代可解
- TCP 超时 → **DNS 污染/段封** → 反代出口也要换
- 反代后目标返回 403 → **目标站点封反代出口 ASN** → 换平台/换住宅 IP（见 §6）

## 2. 核心结论（三大认知修正）

### 修正 1：目标站点「封数据中心 IP」≠ 封所有云
- pixiv 实测：**Cloudflare 边缘 ASN（Pages/Workers 出口）403**、**Deno Deploy 平台级封禁（ToS 禁止代理，直接 SUSPENDED）**、**i.pximg.net 自有服务器 2026-09-19 起无 SNI 请求返回 421**——但 **Netlify Edge Function（AWS 出口 ASN）pixiv 放行**！
- 教训：**不要因为一个云平台被封就放弃整条路**。云反代选型按「国内可达 → 出口 ASN → 目标站点态度」逐项试错，AWS 系/其他 ASN 值得轮换尝试。

### 修正 2：反代代码必须兼容「单协议格式」
- 书源 v4 的 pxproxy 拼装是：`'https://'+pxh+'/'+url.replace(/^https:\/\//,'')`
- → 反代收到的是 `https://<反代域名>/app-api.pixiv.net/v1/...`（**无第二层协议前缀**）
- 若反代代码要求 target 以 `https?://` 开头 → 返回 **400 "bad"**，且**书源侧可能报成 403/URL 错误**（容易误判成目标站点拒绝）
- 正解：`if(!target.startsWith('http')) target='https://'+target;` 自动补协议，单/双协议都兼容

### 修正 3：Netlify Edge Functions 默认受「Edge Access」保护
- 部署后直接访问返回 **401 Login Redirect**（指向 app.netlify.com/edge-access）→ /ping 都过不去
- 必须到 Netlify 面板把该 edge function 设为 **Public**
- 这是 2025+ 新版 Netlify 的默认安全策略，官方文档不显眼，极易踩

## 3. 反代代码模板（Netlify Edge Function，开箱即用）

文件 `netlify/edge-functions/pxrelay.ts`（Deno 运行时，语法与 CF Worker 几乎一致）：

```typescript
// Netlify Edge Function 反代（单/双协议兼容）
// 用法: 书源「代理地址」填 https://<site>.netlify.app，请求如
//   GET https://<site>.netlify.app/app-api.pixiv.net/v1/novel/recommended?... 
export default async (request: Request) => {
  const u = new URL(request.url);
  if (u.pathname === '/ping') {
    return new Response(JSON.stringify({ ok: true, time: Date.now() }), {
      status: 200,
      headers: { 'content-type': 'application/json', 'access-control-allow-origin': '*' },
    });
  }
  let target = u.pathname.startsWith('/') ? u.pathname.slice(1) : u.pathname;
  if (u.search) target += u.search;
  // ★兼容书源单协议格式（缺 https:// 前缀时自动补）
  if (!target.startsWith('http://') && !target.startsWith('https://')) {
    target = 'https://' + target;
  }
  if (!/^https?:\/\/[^/]+/.test(target)) return new Response('bad', { status: 400 });

  // 只转发白名单头（pixiv 客户端需要 x-client-time/x-client-hash 等）
  const ALLOW = new Set([
    'user-agent', 'authorization', 'cookie', 'x-client-time', 'x-client-hash',
    'accept-language', 'app-os', 'app-os-version', 'app-version',
    'content-type', 'referer', 'origin', 'accept',
  ]);
  const headers = new Headers();
  for (const [k, v] of request.headers) {
    if (ALLOW.has(k.toLowerCase())) headers.set(k, v);
  }
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
      redirect: 'manual',
    });
    const out = new Headers();
    for (const [k, v] of upstream.headers) {
      if (!['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'alt-svc', 'server-timing'].includes(k.toLowerCase())) out.set(k, v);
    }
    out.set('access-control-allow-origin', '*');
    return new Response(upstream.body, { status: upstream.status, headers: out });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, err: String(e) }), {
      status: 502,
      headers: { 'content-type': 'application/json' },
    });
  }
};
```

配套 `netlify.toml`：
```toml
[[edge_functions]]
path = "/*"
function = "pxrelay"
```

## 4. 部署四步（全程手机可操作）

1. **GitHub 建仓库**：New repository（Public）→ 依次 Add file → Create new file：
   - `netlify.toml`（上面内容）
   - `netlify/edge-functions/pxrelay.ts`（上面内容）
   - 各 Commit changes
2. **Netlify 导入**：netlify.com → Log in（GitHub 授权）→ Add new site → Import an existing project → GitHub → 选仓库 → **Deploy**（无需任何构建配置）
3. **★设为 Public**：Site → 找到该 Edge Function → 把访问权限从「受保护」改为**公开**（否则全部 401）
   - 证据：`/ping` 直接访问若返回 401 Login Redirect = 没公开
4. **验证**：浏览器访问 `https://<site>.netlify.app/ping` → `{"ok":true,...}` ✅

## 5. 书源侧接入

- 登录界面「代理地址」填 `https://<site>.netlify.app` → 「测试代理」（书源会打 `/ping` 验活）
- 书源内所有 API 请求自动改写为 `https://<代理>/<原URL去掉协议>`
- OAuth（refresh_token 刷新）同样走反代；`host` 头由反代自动设置（书源 loginUrl 里 delete headers['host']）
- 注意书源 URL 选项：反代请求路径里若出现 `,{"timeout":...}` 之类会被反代当路径一部分 → **经反代的请求不要带 URL 选项 JSON**

## 6. 云平台选型对照表（国内免梯直连视角，2026-09 实测）

| 平台 | 国内可达 | 出口 ASN | pixiv 态度 | 结论 |
|---|---|---|---|---|
| **Netlify Edge（netlify.app）** | ✅ | AWS | ✅ 放行（本案例实证） | **首选**（Edge Access 要设 Public） |
| Cloudflare Pages/Workers | pages.dev ✅ / workers.dev ❌墙 | CF 边缘 | ❌ 403 | 出局（除非 CF Worker 绑自有域名，仍可能按 ASN 403） |
| Deno Deploy（deno.dev） | ✅ | Deno 平台 | ❌ 平台 ToS 禁代理 SUSPENDED | 出局 |
| Vercel（vercel.app） | ❌ 被墙 | AWS | 未测（因不可达） | 出局（国内不可达） |
| Render（onrender.com） | ❌ 超时 | — | — | 出局 |
| Glitch（glitch.me） | ✅（已关停） | GCP | — | 2025 关停，不再推荐 |
| 阿里/腾讯云函数 | ✅ | 国内数据中心 | 未测（可试） | 备选（国内 ASN 可能不被目标拒） |
| **家宽/手机 Termux 本地** | ✅ | **住宅 IP** | ✅ 必放行 | **终极保底** |

选型口诀：**CF 系严格避免 → AWS 系（Netlify）优先 → 国内云函数可试 → 住宅 IP 永远稳**。

## 7. 周边知识速查（本案例同场实测）

### DNS 投毒矩阵（GFW 对 pixiv 域名）
| 解析方式 | 结果 |
|---|---|
| 腾讯 DoH `doh.pub/dns-query` | ✅ 真实 IP（CF 104.18.42.239；东京 CDN 210.140.139.x）|
| 阿里 DoH `223.5.5.5/resolve` | ❌ 投毒（Twitter 段假 IP）|
| 明文 UDP53 直查阿里/腾讯公共 DNS | ❌ 全部投毒 |

→ 手机「私人 DNS」(DoT) 必须填腾讯 `dns.pub`，**不能填阿里**；DoH 是拿真实 IP 的唯一可靠途径。

### Legado Cronet 相关（源码 a6839374）
- 内置 Cronet 默认关；开启后书源所有请求走 QUIC/UDP（GFW 的 TCP RST 对 UDP 无效，pixiv 暂不在 QUIC SNI 黑名单，参考 Pixiv-Shaft）
- **但** Cronet 硬编码 AsyncDNS 直发 UDP53（绕过系统 DoT）→ 手机开 DoT 大概率仍解析污染 → Cronet 直连 pixiv 不可行（此路暂死）
- `customHost()` 把 URL 域名换成自定义 Hosts 的 IP → **SNI=IP → CF 拒绝** → 自定义 Hosts 对 CF 域名有害无益
- URL 选项 `timeout/dnsIp/followRedirects` 会**移除 Cronet**（AnalyzeUrl.kt:654）

## 8. 故障速查表

| 症状 | 含义 | 处理 |
|---|---|---|
| 反代返回 `400 bad` | 协议格式不匹配（缺 https://）| 更新为单/双协议兼容版（§3）|
| 反代返回 `401 Login Redirect` | Edge Access 未公开 | Netlify 面板设 Public |
| 反代返回 `502` + err | 上游 fetch 失败 | 反代运行环境 DNS/网络问题 |
| 登录报 `403` + 反代URL | **目标站点拒反代出口 ASN** | 换平台（§6）/ 本地住宅 IP |
| `404 Not Found` + Request ID | Netlify 路由未命中（edge function 没生效）| 检查 netlify.toml 路径/文件名 |
| 书源报 `HTTP error fetching URL` | 反代返回非 2xx 被 jsoup 抛错 | 查反代实际返回码（浏览器直接访问）|

## 9. 验证方法论

1. **分层验证**：/ping（反代活）→ 经反代打目标 API 首个 GET（转发通不通知）→ POST 登录（真实业务通）
2. **浏览器直连反代 URL**（`https://<site>.netlify.app/app-api.pixiv.net/v1/...`）最快判定：JSON=转发成功；403=站点拒；400/404=代码/路由问题
3. **沙盒（大陆网络）+ 真机双测**：沙盒测代码/路由，真机（用户手机 eval_js 或书源内）测最终链路；沙盒结论不能替代真机
4. 用 App 内 HTTP 日志（get_http_logs）看实际请求 URL 与状态码

## 10. 避坑清单 K1~K14

- K1 反代不自动补协议 → 单协议格式 400 bad（最高频！）
- K2 Netlify Edge Access 默认私密 → 全 401 误判成"平台不可用"
- K3 平台选型只看国内可达，不看出口 ASN → CF 系必踩 pixiv 403
- K4 用 Deno Deploy 做代理（ToS 禁止，会被平台 SUSPENDED）
- K5 用 Vercel（.app 域被墙，部署了也连不上）
- K6 用 Glitch（2025 已关停）
- K7 经反代的 URL 带 `,{json}` 选项 → 选项被当路径传给目标 → 404
- K8 反代转发全部请求头（含 hop-by-hop/压缩头）→ 目标 404/损坏；只转发白名单
- K9 转发响应头带 `content-encoding` 但 body 已解压 → 客户端解炸；删掉再回
- K10 忘记 `/ping` 验活端点 → 书源「测试代理」永远失败
- K11 手机私人 DNS 填阿里（dns.alidns.com）→ DoT 也被投毒
- K12 自定义 Hosts 填 CF 域名 → customHost 导致 SNI=IP → 更糟
- K13 以为开了 Cronet 就万事大吉 → AsyncDNS 污染使直连仍失败
- K14 只验证登录，不验证搜索/目录/正文/图片 → 交付半截

## 11. 案例档案（pixiv 完整时间线）

- 2026-09-18 前：无SNI+Host 图片直连 200（210.140.139.x 东京 CDN）
- 2026-09-19：i.pximg.net 无SNI 退化 421（Pixiv 开始要 SNI）→ 图片改走 i.pixiv.re 图床池
- Deno Deploy 反代被平台 SUSPENDED；CF Pages 反代登录 403（当时误判成 pixiv 封 CF，实际部分原因是单协议 bug——CF Pages 版代码可能要双协议，返回 400 被 jsoup 吞成 403 报错；无论如何 CF 边缘 ASN 也被 pixiv 403，双输）
- Netlify Edge Function（AWS 出口）→ 修正单协议兼容 + Edge Access 公开 → **全程 200，登录/搜索/详情/目录/正文全通**
- 最终形态：API=pxrelay.netlify.app 反代；图片=i.pixiv.re 图床池；兜底=尾点+dnsIp；备用=Termux/电脑本地住宅 IP 反代

## 12. 备用方案：本地住宅 IP 反代（终极保底）

- 适用：云反代被目标封、或不想用第三方云
- 手机 Termux：`pkg install python` → 跑 `pxrelay_local.py`（监听 127.0.0.1:3000）→ 书源代理地址填 `http://127.0.0.1:3000`
- 电脑（手机连同一 WiFi）：`python pxrelay_local.py` → 代理填 `http://<电脑局域网IP>:3000`
- 原理：家庭宽带/手机流量出口 = 住宅 IP，目标站点一般不封
- 代码：`/workspace/pixiv_reconnect/pxrelay_local.py`（Node 版 `.js` 同目录）

## 13. 移植到其他目标站（改动清单）

1. 目标 API 域名（可能多个：主 API + OAuth + 图片）
2. 必须转发的头白名单（客户端签名头别丢：x-client-time/x-client-hash 等）
3. /ping 验活端点保留
4. 书源「代理地址」填新反代域名
5. 验证 OAuth 域名是否同走反代（书源 loginUrl 拼装）
6. 若目标站封 AWS → 换国内云函数/住宅 IP（§6）

## 14. 通用结论

1. 云反代是「国内免梯 + 目标站 REST API」的最短路径，**选型先排除 CF 系，AWS 系（Netlify）实测通过**
2. 反代代码第一行就该写协议自动补全——书源侧的 URL 拼装习惯决定了格式
3. 部署平台的新安全默认值（Netlify Edge Access）是隐形杀手，先读官方行为再调试
4. 诊断永远分层：反代活不活 → 转发通不通 → 目标拒没拒