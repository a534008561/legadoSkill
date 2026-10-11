# 方法：GFW SNI 封锁的鉴别、绕过边界与架构级天花板

> 沉淀日期：2026-09-18 ｜ 来源：pixiv 书源直连修复（真机 60+ 次探测）
> 关联：[方法-WAF与CF间歇故障及站点判活.md](方法-WAF与CF间歇故障及站点判活.md)、[方法-URL模板与DNS选线.md](方法-URL模板与DNS选线.md)、[方法-图片不显示排查总表-加密之外的三条路.md](方法-图片不显示排查总表-加密之外的三条路.md)

## 〇 一句话
**TCP 通 ≠ 能连**。当 TCP 几十毫秒就通、但 TLS 握手瞬间被重置（不是超时！）时，
基本就是 SNI 封锁。**先做「同一 IP 换 SNI」对照实验**，30 秒定性，别急着改规则。

## 一 现象谱系：三种封锁长什么样

| 现象 | 耗时特征 | 判定 | 处置 |
|---|---|---|---|
| **DNS 污染** | 连到陌生 IP（`face:b00c`/Twitter段/Facebook段），超时 30s | 解析被投毒 | `{"dnsIp":"真实IP"}` |
| **SNI 封锁** | TCP 通（10~200ms），**TLS 握手 30~100ms 内 RST** | 域名黑名单 | **多数无解**（见五） |
| **IP 封锁/路由黑洞** | TCP 就超时（`ENETUNREACH`） | 换 IP / 换线路 | `dnsIp` 池 failover |
| CF error 1034 | TCP+TLS 都通，CF 回环 | 节点问题 | 换 IP |

**关键鉴别点**：SNI 封锁的失败**极快**（几十毫秒），因为 RST 是主动发的；
而超时类故障都是 5~30 秒。看耗时就能初步区分。

## 二 决定性实验（30 秒定性）

**同一 IP，只换 SNI**：

```js
function t(ip, sni, hostHdr, path, label){
  let t0 = Date.now();
  let res;
  try{
    let sf = Packages.javax.net.ssl.SSLSocketFactory.getDefault();
    let raw = new Packages.java.net.Socket();
    raw.connect(new Packages.java.net.InetSocketAddress(ip,443), 5000);
    let s = sf.createSocket(raw, sni, 443, true);   // ★ sni 是变量
    s.setSoTimeout(8000);
    let subj = String(s.getSession().getPeerCertificates()[0]
                      .getSubjectX500Principal().getName()).substring(0,40);
    let rq = 'GET '+path+' HTTP/1.1\r\nHost: '+hostHdr+'\r\n'
           + 'User-Agent: Mozilla/5.0 (Linux; Android 14)\r\nConnection: close\r\n\r\n';
    let os = s.getOutputStream();
    os.write(new Packages.java.lang.String(rq).getBytes('UTF-8')); os.flush();
    let rd = new Packages.java.io.BufferedReader(
               new Packages.java.io.InputStreamReader(s.getInputStream(),'UTF-8'));
    let sb='', line, n=0;
    while((line=rd.readLine())!=null && n<20){ sb+=line+'\n'; n++; }
    s.close();
    let st = (sb.match(/HTTP\/1\.[01] (\d+)/)||[])[1];
    res = (st||'?')+' cert='+subj;
  }catch(e){
    res = 'FAIL('+(Date.now()-t0)+'ms) '+String(e).replace(/.*Exception[:\s]*/,'').substring(0,50);
  }
  return label.padEnd(42)+' -> '+res;
}

// 同一 CF IP，换不同 SNI
t('104.18.42.239','cloudflare.com',  'cloudflare.com',  'SNI:cloudflare.com');
t('104.18.42.239','example.com',     'example.com',     'SNI:example.com');
t('104.18.42.239','www.pixiv.net',   'www.pixiv.net',   'SNI:www.pixiv.net');   // ← 目标
t('104.18.42.239','discord.com',     'discord.com',     'SNI:discord.com');
```

**判读**：
- 无关 SNI **成功** + 目标 SNI **极快失败** → **SNI 域名黑名单**
- 所有 SNI **都失败** → IP 封锁/路由黑洞
- 所有 SNI **都成功但 Host 不匹配报 421** → CF 的 SNI↔Host 校验（不是墙）

### 配套：TCP 层单独测
```js
let s = new Packages.java.net.Socket();
s.connect(new Packages.java.net.InetSocketAddress('104.18.42.239',443), 5000);
// 22ms 就 OK → TCP 没被封，问题在 TLS
```

## 三 手机侧 DNS 真相速查

| 解析器 | 可用性 | 可信度 |
|---|---|---|
| `doh.pub` / `sm2.doh.pub` | ✅ 国内可达 | 高（实测与权威一致） |
| `1.12.12.12` / `120.53.53.53` | ✅ | 高 |
| `223.5.5.5` / `223.6.6.6` / `dns.alidns.com` | ✅ | ⚠️ **被投毒**（pixiv 返回 Twitter 段） |
| `dns.google` / `cloudflare-dns.com` | ❌ 国内不可达 | — |
| `dns.quad9.net` / `doh.opendns.com` | ❌ | — |

**用法**：多解析器交叉比对，**多数一致的那个才是真相**。
```js
java.get('https://doh.pub/resolve?name=app-api.pixiv.net&type=A',
         {'accept':'application/dns-json'});
```
⚠️ 注意：**`doh.pub` 也可能给出 CF IP 而站点实际已迁走**——解析结果要配合连通性实测。

## 四 已被证伪的 9 种「SNI 绕过」写法（勿再试）

| # | 写法 | 结果 | 说明 |
|---|---|---|---|
| 1 | IP直连 + Host头 | 403/421 | 服务端虚拟主机路由，与墙无关 |
| 2 | **尾点 SNI** `x.com.` | 通常 RST | ⚠️ **例外**：对**未被列入黑名单**的域有效（见案例） |
| 3 | 全大写 / 混合大小写 | RST | 规范化后匹配 |
| 4 | 双尾点 `x.com..` | RST | |
| 5 | 尾空格 / 前导空格 | RST | |
| 6 | punycode `xn--` | RST | |
| 7 | **白名单 SNI 跨域**（`cloudflare.com` + Host:目标） | **421** | CF 强制 `SNI == Host` |
| 8 | `dnsIp` 绕 DNS 污染 | RST | 只解决 DNS，救不了 SNI |
| 9 | **空 SNI**（`setServerNames(空)`） | RST | CDN 必须靠 SNI 路由 |

**唯一例外（重要）**：**尾点 SNI 对「不在黑名单的域名」有效**。
案例：`i.pximg.net` → 原 SNI 被 RST，`i.pximg.net.` **成功 200**。
说明部分域名只是被**顺带**匹配，或黑名单规则是精确串。

## 五 ★架构级天花板：ECH

**为什么有些 App 能直连而 Legado 不能**：
| | TLS 栈 | ECH 支持 |
|---|---|---|
| pixez-flutter | **Rust reqwest** | ✅ `enableEch:true, requireEch:true` |
| Legado | Android **Conscrypt/OkHttp** | ❌ |

**ECH (Encrypted Client Hello)** 把 SNI 加密进 ESNI 记录，GFW 看到的是外层
`cloudflare-ech.com` 之类，无法按域名封锁。**这是当前唯一有效的无代理方案**。

**结论**：
> 当目标域名被 SNI 黑名单且**必须靠 SNI 路由**（CDN 站）时，
> **Legado 侧无解** —— 只能：
> ① 用户配代理 ② 换非 CF 的源站域名 ③ 放弃该域名。

**判断流程**：
```
SNI 对照实验确认是域名黑名单
   ├─ 目标非 CDN（有自己的 IP）→ 试「IP直连 + Host头」，可能绕过（Host 路由不走 SNI）
   ├─ 目标是 CDN（CF 等）→ SNI 必须正确 → 无解，引导代理
   └─ 目标只是「顺带被封」→ 试尾点 SNI、试换 IP 段
```

## 六 图片域的特殊价值

**媒体域（图床/CDN）常与 API 域命运不同**：
- 案例：pixiv API 全封，但 `i.pximg.net` 只需「尾点 SNI + dnsIp」即可 200
- 原因：媒体域往往是独立 CDN，未被列入 API 黑名单

**修复公式**：
```js
// 域名加尾点 + dnsIp 直连节点
'https://i.pximg.net.' + path + ',{"dnsIp":"ip1,ip2,ip3","timeout":20000,"headers":{...}}'
```
实测 10 个节点全通、约 500ms。

**但注意 Glide 的天花板**（源码依据）：
```
OkHttpStreamFetcher.loadData()
  → AnalyzeUrl(url).getGlideUrl()
      → getGlideUrl() 只做 setCookie() + 构造 GlideUrl
        ★不走 getClient()  → dnsIp 被忽略
```
且 Glide 请求的 hostname **不带尾点** → SNI 仍是裸域名 → RST。
⇒ **封面（coverUrl）无法用此方案修复**，只能：
① 列表/详情内用 `@js:` 转 `data:image/...;base64,` ② 引导用户配 App 级「自定义 Hosts」

**而正文图片走 AnalyzeUrl（`ruleContent` 产出 HTML）→ `dnsIp` 生效 → 可修**。

## 七 诊断清单（照做即可）

```
1. get_http_logs 看失败请求的最终 URL 与状态码
2. 看耗时：几十 ms 失败 → 疑似 SNI 封锁；数十秒 → DNS/超时
3. TCP 单独测那个 IP:443 → 通？→ 已排除 IP 封锁
4. 同一 IP 换 SNI（cloudflare.com 做对照）→ 定性 SNI 黑名单
5. 多 DoH 交叉查真实 IP（doh.pub / 1.12.12.12）
6. 若是 CDN 站 → 判断为无解，转向代理方案
7. 若是媒体域 → 试「尾点 SNI + dnsIp」
```

## 八 避坑清单

| # | 坑 | 说明 |
|---|---|---|
| K1 | 拿**超时**当 SNI 封锁 | 超时是 DNS/IP 问题；SNI 封锁是**快速 RST** |
| K2 | 只测一个 DoH 就下结论 | alidns 系被投毒，多源交叉 |
| K3 | 相信 `dnsIp` 能救一切 | 它只改 DNS，不改 SNI |
| K4 | 在沙盒/海外网络复现 | **海外不经过 GFW，结论会完全反** |
| K5 | 白名单 SNI 跨域 | CF 会 421；不是墙的问题 |
| K6 | 空 SNI | CDN 靠 SNI 路由，一定失败 |
| K7 | 忘了 Glide 独立 DNS | 封面修不好，别在 `coverUrl` 上耗时间 |
| K8 | 认为「TCP 通就行」 | TCP 通只说明没被 IP 封 |
| K9 | 改规则试图解决网络层封锁 | 浪费时间，应及早判定为架构天花板 |
| K10 | 不看参考项目的**技术栈** | pixez 能行是因为 Rust+ECH，不是规则写得好 |

## 九 兜底话术（给用户的明确提示）

```js
if (rc == '0') {
    throw '⛔ API 在大陆已被 SNI 封锁（站点已迁 Cloudflare，GFW 拦截其 SNI）。'
        + '请在「设置→其他设置→代理」配置可用代理后重试；图片通道已单独优化可直连。';
}
```
**价值**：把「静默失败 → 空列表 → 用户困惑」变成「明确告知原因 + 解决路径」。
这是网络层无解时**最有价值的交付**。

## 十 案例档案

| 站点 | 封锁类型 | API 结果 | 图片结果 | 最终方案 |
|---|---|---|---|---|
| pixiv（2026.09） | DNS污染 + SNI黑名单 + 迁CF | ❌ 无解（CF强制SNI，Legado无ECH） | ✅ 尾点SNI+dnsIp | 探测+提示；图片优化 |
| hanime1 | dnsIp 救不了播放器 | — | — | 换 CDN 原生主机名 |
| ggd8.cc | CF 节点抖动（误判失效） | ✅ 复测通过 | — | 多时点复测 |

---

# 补充（2026-09-18 第二轮）：IllustFerry / Pixiv-Shaft 技术拆解

> 用户提供两个可直连的参考项目，逐一复现其机制后的结论。

## 十一 ★「无 SNI」技术：真正的绕过手段（已验证有效）

### 原理（IllustFerry `LocalPixivProxy.createUpstreamTlsSocket` 源码注释）
```kotlin
// peerHost 必须传 IP literal：JSSE 看到 IP 就会把 SNI 扩展整个略掉（RFC 6066
// 不允许 SNI 是 IP）。GFW 的 SNI DPI 没有 www.pixiv.net 可匹配，就不会注 RST。
// 一旦把 hostname 传进去或者显式 serverNames = SNIHostName(host)，墙立刻命中。
val dialHost = upstream.inetAddress.hostAddress ?: host
val socket = clientSslContext.socketFactory.createSocket(upstream, dialHost, port, true)
```

**关键**：`createSocket(sock, peerHost, port, autoClose)` 的 **peerHost 传 IP 字面量**
→ JSSE 按 RFC 6066 省略 SNI 扩展 → **GFW 无域名可匹配 → 不注入 RST**。

### 对照实验（真机实测，决定性）
| 调用方式 | 结果 |
|---|---|
| `createSocket(up, "210.140.139.152", 443, true)` | ✅ **TLS 握手成功** |
| `createSocket(up, "app-api.pixiv.net", 443, true)` | ❌ **RST**（GFW 命中）|

同一 IP、同一时刻，**只差 peerHost 是 IP 还是域名** → 铁证。

### 适用边界（重要）
| 场景 | 无 SNI 是否可用 |
|---|---|
| **自身 IP + default vhost 能服务** | ✅ 可用（如 `i.pximg.net` Tokyo CDN） |
| **CDN（CF 等）靠 SNI 路由** | ❌ 不可用（IllustFerry 注释原话：「CF 节点没有 SNI 是无法路由的」） |
| 源站 IP 但 vhost 已摘除 | ❌ 403（服务端拒绝，与墙无关） |

**判别法**：无 SNI 握手后看响应码——
- `403` → 该 IP 上**没这个 vhost**（不是墙的问题，换 IP 也没用）
- `404` / `200` / `301` → vhost 存在，可用
- `421` → nginx 要求 SNI（该节点不接受无 SNI）

## 十二 DoH 穿透 DNS 污染（IllustFerry 同款）

```
GET https://api.sb6.me/getdnsipv4?host=<域名>&isCN=0
→ ["210.140.139.137","210.140.139.133",...]
```
- `isCN=0` 参数：要求**非墙内视角**解析
- 服务端 PHP：`dns_get_record($host, DNS_A)` 只返回 A 记录
- **必须做 bogon 过滤**（IllustFerry `isValidPublicIpv4`）：拒 `127./10./192.168./169.254./0./224+`
  —— 因为该 DoH 偶尔也被投毒，返回 `127.0.0.1` 会让拨号打到本机

**实测有效**：
| 域名 | 结果 |
|---|---|
| `public-api.secure.pixiv.net` | `210.140.139.152/155/158/161`（Tokyo） |
| `i.pximg.net` | `210.140.139.129-138`（Tokyo CDN） |
| `app-api.pixiv.net` | `104.18.42.239 / 172.64.145.17`（CF，无 SNI 不可路由） |

## 十三 ★ 完整 vhost 映射表（无 SNI + 逐个换 Host，@Tokyo 210.140.139.152）

| Host | 响应 | 判定 |
|---|---|---|
| `public-api.secure.pixiv.net` | **404 + `application/json`** | ✅ **唯一活着的 API 服务** |
| `novel.pixiv.net` | 404（web） | ✅ 活 |
| `pixiv.net` / `touch.pixiv.net` | 301 | ✅ 重定向 |
| **`app-api.pixiv.net`** | **403** | ❌ **vhost 已被摘除** |
| `oauth.secure.pixiv.net` | 403 | ❌ |
| `accounts` / `source` / `www` / `imgaz` | 403 | ❌ |
| `spapi` / `api` / `app` / `secure` | 421 | 不存在 |

**结论**：pixiv 已把主力 API vhost 从 Tokyo 摘到 Cloudflare，
IllustFerry 的「用 `public-api` 的 IP 承接 `app-api` 流量」策略
**依赖 vhost 仍存在**，现已失效。

## 十四 已废弃端点的识别：`426 Upgrade Required`

```
/v1/search/novel?word=test  ->  426 Upgrade Required（Content-Length: 16，无 Upgrade 头）
/v1/search/illust           ->  426
/v1/search（裸）             ->  301
其他所有 /v1/*               ->  404
```
**鉴别要点**：标准 426 必须带 `Upgrade:` 响应头（RFC 7231）。
**没有 `Upgrade` 头的 426 = 固定的「端点已停用」拦截**，不要误以为是协议升级需求。

## 十五 三种「图片获取」实现对比

| 方案 | 实现 | 优点 | 缺点 |
|---|---|---|---|
| **尾点域名 + dnsIp** | `https://i.pximg.net./x.png,{"dnsIp":"ip"}` | 走 Legado 原生栈，一行搞定，能进 `<img>` | 依赖「尾点恰好未入黑名单」 |
| **无 SNI 握手** | `createSocket(up, ip, 443, true)` + 手读字节 | 不依赖尾点变体，更彻底 | 需自己解析 HTTP 头、转 base64；只能用于能拿到字节的场景 |
| **远程图片代理** | 如 IllustFerry 用 `https://i.yuki.sh` | 完全绕开 | 依赖第三方可用性 |

**实践建议**：书源里**两者都写**——主路径用尾点+dnsIp（简单、能进 Glide 之外的 `<img>`），
备用路径留无 SNI（应对尾点变体被封的情况）。

## 十六 补入避坑清单（K11~K16）

| # | 坑 | 说明 |
|---|---|---|
| K11 | 以为「无 SNI」万能 | CDN（CF）靠 SNI 路由，无 SNI 必失败；只对源站 IP 有效 |
| K12 | 看到 403 就以为是被墙 | 403 = **该 IP 上没有此 vhost**（服务端拒绝），换 IP 无用 |
| K13 | 把无 `Upgrade` 头的 426 当协议升级 | 那是「端点已停用」的固定拦截 |
| K14 | 不做 bogon 过滤就用第三方 DoH | 会被投毒成 `127.0.0.1`，拨号打到本机 |
| K15 | 以为引用项目能直连＝自己也能 | 要看它依赖的**服务端 vhost 是否还在**（会随时间变化） |
| K16 | 忘了无 SNI 需要**先连 IP 再包 TLS** | 顺序：`Socket.connect(ip)` → `sf.createSocket(up, ip, 443, true)` |

---

# 补充二（2026-09-18 晚）：Legado Cronet(QUIC) 实测与上游缺陷

## 十七 ★★★ Legado 自带 Cronet，且默认关闭

**发现路径**：`legado_src` 源码树
```
app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt
app/src/main/java/io/legado/app/lib/cronet/CronetHelper.kt      ← 引擎构建
app/src/main/java/io/legado/app/help/http/Cronet.kt             ← 入口
app/src/main/res/xml/pref_config_other.xml:108                  ← 开关
app/src/main/assets/cronet.json                                 ← 版本清单
app/cronetlib/cronet_api.jar
```

**开关位置**：`设置 → 其他设置 → Cronet`（`key="Cronet"`，`defaultValue="false"`，`summary="use Cronet access network"`）

**引擎配置**（`CronetHelper.kt`）：
```kotlin
val cronetEngine by lazy {
    ExperimentalCronetEngine.Builder(appCtx).apply {
        setStoragePath(appCtx.externalCache.absolutePath)
        enableHttpCache(HTTP_CACHE_DISK, 50 * 1024 * 1024L)
        enableQuic(true)          // ★ HTTP/3
        enableHttp2(true)
        enablePublicKeyPinningBypassForLocalTrustAnchors(true)
        enableBrotli(true)
        setExperimentalOptions(options)
    }.build()
}
```

**动态库**：`libcronet.153.0.8010.27.so`，从
`https://storage.googleapis.com/chromium-cronet/android/153.0.8010.27/Release/cronet/libs/<abi>/libcronet.153.0.8010.27.so`
下载，MD5 校验后才 `System.load()`。

**★ 实测 `storage.googleapis.com` 国内可达！**
```
34.3.0.27     TCP 50ms   TLS 48ms
34.153.2.27   TCP 48ms
实测下载: statusCode=200, contentType=application/octet-stream, 2,059,850 字节 / 676ms
MD5 与 cronet.json 完全匹配 ✓
```

**错误格式鉴别法**：
| 格式 | 走的栈 |
|---|---|
| `failed to connect to ...`（小写 f） | OkHttp/Conscrypt |
| **`Failed to connect to ...`（大写 F）** | **Cronet** |
| `CronetUnavailableException` | Cronet 拦截器接管但失败 |

## 十八 ★★★ 上游缺陷：Cronet 缺 DNS 映射层

### 缺陷 1：`HostResolverRules` 被注释
`CronetHelper.kt`：
```kotlin
val options by lazy {
    val options = JSONObject()
    //设置域名映射规则
    //MAP hostname ip,MAP hostname ip
//    val host = JSONObject()                      ← ★ 注释
//    host.put("host_resolver_rules","")           ← ★ 注释
//    options.put("HostResolverRules", host)       ← ★ 注释
    val dnsSvcb = JSONObject()
    dnsSvcb.put("enable", true)
    dnsSvcb.put("enable_insecure", true)
    dnsSvcb.put("use_alpn", true)
    options.put("UseDnsHttpsSvcb", dnsSvcb)
    options.put("AsyncDNS", JSONObject("{'enable':true}"))
    options.toString()
}
```
**这正是 Pixiv-Shaft 用来绕 DNS 污染的关键**，Legado 侧被禁用。

### 缺陷 2：`dnsIp` 与 Cronet 互斥
`AnalyzeUrl.getClient()`：
```kotlin
val cronetInterceptor = if (urlTimeoutConfigured || followRedirects != null || dnsAddresses != null) {
    Cronet.interceptor          // ← 注意：这个变量的用途是「移除」
} else null
...
buildRequestClient(..., interceptorToRemove = cronetInterceptor)
```
`buildRequestClient` 里 `interceptors().remove(interceptorToRemove)`。

→ **一旦用 `dnsIp`（或 timeout / followRedirects），Cronet 就被移除**，退回 Conscrypt(TCP) → SNI 被 RST。

### 缺陷 3：`dns{}` 只装 okHttp
`HttpHelper.kt`：
```kotlin
if (AppConfig.addressCache.isNotEmpty()) {
    builder.dns { hostname ->
        AppConfig.addressCache[hostname] ?: Dns.SYSTEM.lookup(hostname)
    }
}
```
这个 `builder` 是 `okHttpClient`；Cronet 走自己的 `AsyncDNS` + `UseDnsHttpsSvcb`，**不读它**。

## 十九 实测因果链（pixiv 案例）

```
① Cronet 引擎       ✅ cloudflare.com → 1.3MB / example.com → 559B
② Cronet 库         ✅ 已装
③ dnsIp 绕 DNS      ✅ 0.36s 直达 104.18.42.239
④ Cronet + pixiv    ❌ ERR_CONNECTION_TIMED_OUT
   原因: DNS 污染 → 解析到 208.77.47.172（35ms 被拒）→ 30s 超时
⑤ Cronet + IP直连   ❌ ERR_SSL_VERSION_OR_CIPHER_MISMATCH（SNI=IP，CF 无法路由）
⑥ dnsIp + Cronet    ❌ 互斥（见缺陷 2）
```

## 二十 上游建议补丁

```kotlin
val options by lazy {
    val options = JSONObject()
    // 启用主机映射（Cronet 内部 DNS）
    val host = JSONObject()
    host.put("host_resolver_rules", "MAP app-api.pixiv.net 104.18.42.239,MAP oauth.secure.pixiv.net 104.18.42.239")
    options.put("HostResolverRules", host)
    ...
}
```
并让 `dnsIp` 与 Cronet 兼容（例如 dnsAddresses 存在时不移除 Cronet，而是转成 host_resolver_rules）。

## 二十一 避坑清单（K17~K22）

| # | 坑 | 说明 |
|---|---|---|
| K17 | 以为 Cronet 开关开了就完事 | 它只解决 TLS 层；**DNS 污染另需映射** |
| K18 | 用 `dnsIp` 想让 Cronet 走指定 IP | 会**移除 Cronet**（源码 interceptorToRemove）|
| K19 | 以为「自定义 Hosts」对 Cronet 有效 | 它只装 okHttpClient |
| K20 | 用 IP 当 URL + Host 头（Cronet 下）| `ERR_SSL_VERSION_OR_CIPHER_MISMATCH`（SNI=IP）|
| K21 | 误判 `CronetUnavailableException` = 库没装 | 要看 `Caused by`：`ERR_CONNECTION_TIMED_OUT` = DNS 问题 |
| K22 | 以为 Google 存储被墙 | 实测可达（TCP 50ms）；下载失败要查别处 |

## 二十二 错误格式速查（快速定位走哪条栈）

| 错误文本 | 栈 | 下一步 |
|---|---|---|
| `failed to connect to X/IP` | OkHttp | — |
| **`Failed to connect to X/IP`** | **Cronet** | 查 DNS |
| `CronetUnavailableException: Cronet request failed` + `Caused by: ERR_CONNECTION_TIMED_OUT` | Cronet | **DNS 污染** |
| `ERR_SSL_VERSION_OR_CIPHER_MISMATCH` | Cronet | SNI=IP，需真域名 |
| `SSLHandshakeException ... aborted` | Conscrypt/OkHttp | SNI 被 RST |

## 二十三 ★2026-09-19 pixiv 直连 v4 实战补充（沙盒=大陆网直接实验）

**沙盒网络位置会变**：2026-09-18 之前沙盒是海外直连；2026-09-19 起沙盒 egress 变成大陆网络
（DNS 污染 face:b00c、google/yt/twitter 超时、baidu/httpbin/github/deno.land 可达）→
**SNI/端口/分片实验可直接在沙盒做**，结论与真机一致。判据：`getaddrinfo('i.pximg.net')` 返回
`face:b00c` IPv6 = 已在大陆。

### 23.1 新实验结果（2026-09 版 GFW）
| 实验 | 结果 |
|---|---|
| 尾点 SNI `app-api.pixiv.net.` → CF | **RST**（GFW 会归一化尾点；尾点只对非 CF 的东京源站有效）|
| CF 备端口 2053/2083/2087/2096/8443 + pixiv SNI | **全 RST**（GFW 对 CF 全端口做 SNI DPI，不只 443）|
| 无 SNI（省略 ClientHello 扩展）→ CF | **handshake_failure**（CF 强制 SNI，与 Host 无关）|
| TCP 分片 ClientHello（byedpi 式，6 种切法+延时）| **全 RST**（GFW 已做流重组；分段绕法失效）|
| 无 SNI + Host: i.pximg.net → 东京 210.140.139.x | **200 真实图**（图片通道最稳写法）|
| 公共图床反代 i.pixiv.re / pximg.jackli.dev / pximg.hakurei.cc | 大陆可达 175~621ms（CF 托管，SNI 干净）|
| 托管平台大陆可达性 | deno.dev ✓ pages.dev ✓ netlify.app ✓ glitch.com ✓；**workers.dev ✗ vercel.app ✗** |

### 23.2 pixiv 免梯最终方案（书源侧可交付的极限）
- **图片/封面**：`i.pximg.net` → 公共图床反代池自动测速（i.pixiv.re 等，开源 art-workers/pixiv.re），
  失败回退「尾点+dnsIp」。封面 Glide 走反代域名后不再空白。
- **API**：**无公共反代可用**（gh-proxy/allorigins/corsproxy/codetabs 全 403/404/429/墙）→
  自建 **Deno Deploy 反代**（deno.dev 大陆可达，1 分钟部署免费）：
  `GET /ping → {"ok":true}`；`GET|POST|HEAD /<完整URL>` 白名单头转发 + body + `duplex:'half'`(CF Worker 必须)。
  书源 URL 改写 = `https://<px>/` + 完整原始 URL（**路径直通格式**，不是换 host！）。
- Legado 当前版 Cronet 路径依旧不通：`customHost()` 把 URL host 改成 IP → CF 无 SNI 拒绝。

### 23.3 本 App 新踩坑（记住）
- **`java.get()` 在部分 App 返回 jsoup Response**：只有 `.statusCode()` **没有 `.code()`** →
  探测一律 `_pr()` 双兼容（`statusCode` 优先，其次 `code`，最后 `String(r)`）。
- loginUi 文本框的键 = **UI 中文名**（`Info['代理地址']`），不是变量名。
- loginUrl 是独立作用域（eval_js 窗口 `typeof pxtest===undefined` 正常）→ 自包含
  `var ua = ua || '...'` 模式（jsLib 的 ua 是裸赋值，不冲突）。
- build 脚本改 ruleContent 时它是 **dict**（要取 `['content']`），`in` 判断会静默跳过。

---

## 二十四 ★★2026-10-11 重大更新：别名域直连（图片通道终极方案）+ QUIC 全链路实证

> 来源：pixiv 书源免代理直连修复 v5（拆解 Parfait / Pix-EzViewer / PixLume / PiPixiv 四项目）
> 实验环境：沙盒=大陆出口（广东 120.235.87.210）+ 真机（家宽）双端交叉验证

### 24.1 ★★★核心突破：**别名域直连**（图片通道最优解，无需任何绕过）

**原理**：GFW 对 `i.pximg.net` 做 SNI 封锁，但同一源站还有**未被封锁的别名域**。

| 域名 | 系统DNS | SNI握手 | 图片服务 |
|---|---|---|---|
| `i.pximg.net` | ❌ 污染（69.63.x / face:b00c）| ❌ RST | — |
| `b.pximg.net` | ✅ 210.140.139.129-138 | ✅ 未封锁 | ✅ **200** |
| `d.pximg.net` | ✅ 同上 | ✅ 未封锁 | ✅ **200** |
| `imgaz.pximg.net` | ✅ 同上 | ✅ 未封锁 | ✅ **200** |
| `source.pximg.net` | ✅ 同上 | ✅ 未封锁 | ✅ **200** |

**四条硬特性**（这使它成为**最优方案**，优于公共图床）：
1. 系统 DNS **干净**（无需 `dnsIp`）
2. SNI **未被封锁**（握手 79-100ms）
3. **纯 URL 替换**即可（无需 Host 头）→ Glide / ImageProvider / WebView **全路径通用**
4. 分辨率**完全一致**（3840×2160），仅 JPEG 重编码（3.04MB vs 3.22MB，视觉无差）

**性能对比**：
```
别名域直连    79-100ms    ← 快 17-40 倍
公共图床      3200-16000ms
```

**实现（jsLib，可直接抄）**：
```js
var PX_ALIAS = ['b.pximg.net','d.pximg.net','imgaz.pximg.net','source.pximg.net'];

// 测速选线（缓存 6h）
function pxAlias(force){
  const {java, source} = this;
  let cached=_gv(source,'pxalias');
  if(!force && cached.indexOf('|')>0){
    let t=cached.split('|');
    if((Date.now()-Number(t[1]||0))<6*60*60*1000) return t[0];
  }
  for(let i=0;i<PX_ALIAS.length;i++){
    let h=PX_ALIAS[i];
    try{
      let p=_pr(java.get('https://'+h+'/c/240x240/img-master/img/2024/02/28/05/42/23/116457142_p0_master1200.jpg',
        {'User-Agent':'PixivAndroidApp/5.0.166 (Android 14; RMX3366)','Referer':'https://www.pixiv.net/'},8000));
      if(p.code==200 && p.body.length>1000){ source.put('pxalias',h+'|'+Date.now()); return h; }
    }catch(e){}
  }
  return '';
}

// URL 改写 + 压缩参数剥离
function pxDirect(url){
  const {java, source} = this;
  if(!url) return url;
  url=String(url);
  if(url.indexOf('i.pximg.net')<0) return url;
  let h=pxAlias.call(this,false);
  if(h=='') return url;
  let u=url.replace(/^https?:\/\/i\.pximg\.net/, 'https://'+h);
  u=u.replace(/(\/c\/\d+x\d+)_\d+(\/)/, '$1$2');   // ★关键
  return u;
}
```

**★压缩参数剥离（必须做）**：别名域不支持 `c/{w}x{h}_{q}` 压缩路径：
```
c/240x480_80/...  → 403
c/240x480/...     → 200（143KB，比原 41KB 更清晰）
```
**支持的路径**：`c/240x240` ✅ `c/240x480` ✅ `c/48x48` ✅ `img-original` ✅ `novel-cover-original` ✅
**不支持**：`c/540x540` ❌ `c/240x480_80` ❌（需剥离）

**必须带 Referer**：`Referer: https://www.pixiv.net/`（否则 403）

### 24.2 ★★QUIC/HTTP3 全链路实证（API 免代理的唯一通道）

**沙盒（大陆出口）用 aioquic 手工构造 HTTP/3 请求**：
```python
cfg = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
cfg.server_name = 'app-api.pixiv.net'      # ★必须真 SNI
cfg.verify_mode = False
async with connect('172.64.145.17', 443, configuration=cfg, ...) as c:
    # 发 HEADERS: :method GET, :authority app-api.pixiv.net, :path /v1/...
```

**实测结果（4/4 CF IP 全部第 1 次成功，稳定）**：
| 端点 | 结果 |
|---|---|
| `/v1/novel/recommended` | ✅ **200** 完整小说列表（真实数据）|
| `/v1/search/novel` | ✅ **200** 搜索结果 |
| `/v2/novel/series` | ✅ **200** 完整目录 |
| `/webview/v2/novel` | ✅ **200** 完整 HTML |
| `oauth /auth/token` (POST) | ✅ 400 正常业务响应 |

⇒ **传输层完全可行，唯一缺口是 DNS**。

**QUIC 的 SNI 约束（关键）**：
| SNI | 结果 |
|---|---|
| 真 SNI (`app-api.pixiv.net`) | ✅ **200 业务数据** |
| SNI=IP 字面量 | ❌ 失败 |
| 空 SNI | ❌ 失败 |
| SNI=cloudflare.com | ❌ 403 |
| SNI=b.pximg.net 等别名域 | ❌ 失败 |

### 24.3 ★真机 Cronet 实测（开启 Cronet 后仍失败的原因）

用户在「我的 → 其他设置 → Cronet」打开开关后的实测：

| 测试 | 结果 |
|---|---|
| `cloudflare-quic.com` | ✅ 665ms（QUIC 工作）|
| `www.pixivision.net` | ✅ 574ms（★pixiv 家族域名能通！）|
| `b.pximg.net` | ✅ 458ms 图片 |
| `app-api.pixiv.net` | ❌ 31s `net::ERR_CONNECTION_TIMED_OUT` |
| `pixiv.me` | ❌ 33s 超时（**DNS 干净也不行**）|
| `fanbox.cc` | ❌ 31s 超时 |

**三个卡点（书源侧改不动）**：
1. **Cronet 的 `AsyncDNS` 走明文 UDP:53** → 拿到污染 IP（IPv6 黑洞 `face:b00c`）
2. **`dnsIp` 与 Cronet 互斥**：`AnalyzeUrl.getClient()` 里设了 `dnsIp`/`timeout`/`followRedirects` 任意一个 → **移除 Cronet 拦截器** → 退回 OkHttp(TCP) → SNI 封锁 RST（实测 222ms `Connection reset by peer`）
3. **`HostResolverRules` 在源码被注释**（`CronetHelper.kt:74`）→ 无法做「域名→干净IP」映射
   - 而「自定义Hosts」走 `customHost()` 把 URL 域名**替换成 IP** → SNI=IP → CF 拒绝

**验证日志（真机 HTTP log）**：
```
#44 GET https://app-api.pixiv.net/... -> -1 2770ms | CronetUnavailableException  (Cronet+污染DNS)
#45 GET https://app-api.pixiv.net/... -> -1 129ms  | SSLHandshakeException        (dnsIp→OkHttp→RST)
```

### 24.4 ★四项目机制对照（哪些能移植）

| 项目 | 核心机制 | 移植结果 |
|---|---|---|
| **Pix-EzViewer** | `SSLSocketFactory` 替换 SNI + 空 SNI + DoH + ECH | ❌ API域：替换SNI→421；空SNI→403；ECH 需 Conscrypt 扩展（本App无 `setEchConfigList`）|
| **PixLume** | IP直连 + Host 头 + 启动探测选线 | ✅ **图片域**（已采用别名域方案）；❌ API域 |
| **PiPixiv** | 无SNI握手 + CDN别名域(`*.cdn.cloudflare.net`) + 竞速 | ✅ **别名域思路**（已采用）；❌ `pixiv.net.cdn.cloudflare.net`→RST |
| **Parfait** | ECH + DoH + 无SNI 阶梯（rustls）| ❌ 需 Rust 原生层，书源侧无法实现 |

### 24.5 ★API 域 TCP 层穷尽验证（2026-10 版 GFW）

| 尝试 | 结果 |
|---|---|
| 真 SNI (443) | RST |
| 空 SNI | 403（源站拒绝无SNI路由）|
| SNI 替换（pixiv.me/pixivision.net/fanbox.cc/www.pixivision.net）| **421 Misdirected Request** |
| 备用端口 2053/2083/2087/2096/8443 | RST |
| CDN 别名域 `pixiv.net.cdn.cloudflare.net` | RST |
| 尾点 / 大小写 / punycode / 加空格 / `\t` | RST |
| 明文 HTTP (80) | 403 |
| TCP 分片（1字节 / SNI中间切 / 对半）| SSLEOFError |
| IPv6 (CF `2606:4700::`) | RST |
| 源站直连 (210.140.139.155-158) | RST |
| **CF 按 SNI 路由** | SNI=pixivision.net + Host=app-api → **403**（CF 拒绝跨域路由）|

⇒ **TCP 层 100% 无解**，唯一通道是 QUIC。

### 24.6 ★沙盒网络位置判据（新增）

```bash
# 判据：DNS 返回 face:b00c = 在大陆
python3 -c "import socket; print(socket.getaddrinfo('i.pximg.net',443))"
# 或看 egress IP
curl https://www.cloudflare.com/cdn-cgi/trace | grep loc=   # loc=CN = 大陆
```

### 24.7 ★★方法论：别名域探测法（可复用到任何 CDN 站）

当主域被 SNI 封锁时，按此顺序找别名域：
1. **DNS 反查同 IP 段的所有域名**（`b.` `d.` `s.` `imgaz.` `source.` 等常见前缀）
2. 对每个候选：`DoH 解析`（判 DNS 是否干净）→ `TLS 握手`（判 SNI 是否被封）→ `GET 真实资源`（判是否服务）
3. 优先选**纯 URL 替换即可**的（无需 Host 头），因为这样 Glide/ImageProvider/WebView 全路径通用

**判定脚本模板**（Python，3 秒出结果）：
```python
for host in candidates:
    ips = doh(host)                          # DNS 干净?
    try:
        tls_handshake(ips[0], host)          # SNI 未封锁?
        status = get(host, real_path)        # 服务资源?
        print(host, '✅' if status==200 else '❌')
    except: print(host, '❌ RST')
```

### 24.8 ★★交付后发现的配置丢失问题（v5.5/v5.6 修复）

**现象**：每次通过深链导入新版书源后，`pxproxy` 变量被清空 → API 全部失败。

**根因**：`loginUi` 的文本框（`name: "代理地址"`）没有 `default` 回填，
导入时 `getLoginInfoMap()` 收割 loginUi 的 default 值（空）→ 覆盖旧值。

**修复（双层自愈）**：
```js
// ① loginUrl 顶部（打开登录面板时执行）
try{
  var _Info = source.getLoginInfoMap();
  var _ui = String(_Info['代理地址']||'');
  var _v = String(source.get('pxproxy')||'');
  if((_ui==''||_ui=='null'||_ui=='undefined') && _v && _v!='null' && _v!='undefined'){
    _Info['代理地址']=_v; source.putLoginInfo(JSON.stringify(_Info));
  }
  if(_ui && _ui!='null' && _ui!='undefined' && (_v==''||_v=='null'||_v=='undefined')){
    source.put('pxproxy',_ui);
  }
}catch(e){}

// ② gethd() 开头（每次生成 header 时执行，更及时）
try{
  let _cur=String(source.get('pxproxy')||'');
  if(_cur==''||_cur=='null'||_cur=='undefined'){
    let _li=source.getLoginInfoMap();
    let _pv=String(_li['代理地址']||'');
    if(_pv && _pv!='null' && _pv!='undefined' && _pv.indexOf('.')>0){ source.put('pxproxy',_pv); }
  }
}catch(e){}
```

**通用教训**：
- 书源导入会重置 `source.get/put` 变量（除非有回填机制）
- **loginUi 静态文本框必须配 default 回填，或在 loginUrl/gethd 里做自愈**
- 关键配置建议存两份：`source.put` 变量 + `loginInfo`（互为备份）

**验证方法**：
```js
// 清空变量模拟导入后状态
source.put('pxproxy','');
// 触发自愈（调用 gethd 或打开登录面板）
gethd();
// 检查是否恢复
String(source.get('pxproxy'))   // 应恢复为原值
```
