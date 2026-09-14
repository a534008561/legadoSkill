# 方法：WAF / Cloudflare 间歇故障与"站点到底死没死"的判活纪律
## ——GoEdge、CF 抖动、TLS RST、UA 豁免，以及一次把活站误判成死站的复盘

> 沉淀日期：2026-09-14　｜　来源：ggd8.cc（CF 间歇抖动，误判复盘）、lianaiya.com（503+token）、rrssk/lwenxsw/7shuw（GoEdge）、zhaoshu.la（GoEdge UA 生死线）、xuken.net（TCP RST 累计惩罚）、hanime1（CF 挑战自伤）
> 前置阅读：**[WAF挑战过盾指南](WAF挑战过盾指南.md)**（lianaiya 型 503+`var token` 的全内联实现与自愈设计）——本篇补**判活纪律、WAF 家族分型、间歇故障工程化处理**。

---

## 目录

1. [第一原则：判定"站点失效"之前必须做的复测](#一第一原则判定站点失效之前必须做的复测)
2. [一次真实误判复盘（ggd8）](#二一次真实误判复盘ggd8)
3. [WAF/防护家族分型与对策](#三waf防护家族分型与对策)
4. [★UA 是生死线：三种作用](#四ua-是生死线三种作用)
5. [GoEdge 专项（rrssk 家族）](#五goedge-专项rrssk-家族)
6. [Cloudflare 专项](#六cloudflare-专项)
7. [间歇性 TLS RST 的工程化处理四件套](#七间歇性-tls-rst-的工程化处理四件套)
8. [自伤型故障：把自己的调试打成了封锁](#八自伤型故障把自己的调试打成了封锁)
9. [判活决策树](#九判活决策树)
10. [避坑清单](#十避坑清单)

---

## 一、第一原则：判定"站点失效"之前必须做的复测

**"打不开"有 6 种得不同的病，只有 1 种是站死了。**

复测矩阵（全做完不超过 10 分钟）：

| 维度 | 具体操作 | 排除掉的原因 |
|---|---|---|
| **多时点** | 同一 URL 隔 5~10 分钟再试 2~3 次 | **CF 节点抖动 / 间歇 RST**（ggd8 就是这种） |
| **多通道** | 沙盒 `curl`/python + App 内 `java.ajax` + 手机浏览器 + 桌面浏览器 | 沙盒出口被限制、App 的 Cronet/OkHttp 栈差异 |
| **多协议** | http 与 https 各试（xheiyan 只有 HTTP 可用，HTTPS 是 nginx 默认页） | 证书/协议配置问题 |
| **多端口** | 换端口（xuken 的 80 端口 RST，必须 HTTPS） | 端口级封锁 |
| **多 UA** | 完整 Chrome UA / 短移动 UA / 无 UA（三者结果可能完全不同） | UA 触发的防护或模板分发 |
| **多路径** | 首页 / 详情页 / 接口 各试 | 只有某条接口被限流（其余正常） |
| **看镜像** | `site:` 搜索、Bing 缓存、其他域名同 CMS 站 | 域名迁移 vs 站点关闭 |

**判据**：

- 全维度都不通 + DNS 无解析 → 真死了（迁移或删除）；
- **只有部分时点通 → 抖动，不是死**，用第七节四件套扛住；
- 沙盒不通、App 通（或反之）→ **网络侧问题**，见[图片排查篇第七节](方法-图片不显示排查总表-加密之外的三条路.md)的沙盒误诊纪律。

---

## 二、一次真实误判复盘（ggd8）

```
Day N   ：手机侧 "SSL handshake aborted"；本机 Errno 104 Connection Reset
        ：全端口、全路径不可达
        ：结论 → "ggd8.cc 已死"，于是另起炉灶做了 ggd66.com 镜像源
Day N+1 ：复测 → 域名已迁 Cloudflare（104.21.85.233 / 172.67.212.22）
        ：无 WAF 挑战、无登录、无搜索频控、UA 不影响（5/5 全过）
        ：真相 = ★CF 节点间歇抖动的误判
结果     ：两源并存互补（书库不互通），反而都是好源；但当时浪费了一整天
```

**教训固化成三条规则**：

1. **任何"站点已死"的结论必须隔时点复测 ≥2 次**（建议隔 5 分钟一次、共三次，或早晚各一次）；
2. 报"失效"前先在**书源里加一个"检查站点连接"按钮**（`checkConn`），让用户自己一键复测——黄果剧场、mdcmai、hanime1 都因此省了来回；
3. 结论要**写进 `bookSourceComment`** 并留复测日期，不要只写在对话里。

---

## 三、WAF/防护家族分型与对策

| 家族 | 识别特征 | 首屏表现 | 书源对策 |
|---|---|---|---|
| **lianaiya 型自研挑战** | `503` + 响应体含 `var token` + 需设 `waf_challenge` Cookie | 503 | 内联过盾（见 WAF 指南），token ~5 分钟过期 → 自愈重试 |
| **GoEdge** | 307/302 跳 `/WAF/VERIFY/CAPTCHA`，页里含 `goedgeVerify` | 跳图形码 | ① 移动 UA 豁免 **GET**；② **POST 强制人机** → `java.getVerificationCode(url)` 弹窗过盾；③ 回退请求也带移动 UA |
| **Cloudflare（挑战型）** | `Just a moment...`、`cf-chl`、`_cf_chl_opt` | 403/503 挑战页 | 书源基本无解；优先找**未被 CF 保护的镜像/接口**；或 `java.startBrowser` 让用户过一次 |
| **Cloudflare（抖动型）** | 间歇 `ERR_CONNECTION_RESET` / TLS aborted，无挑战页 | 时好时坏 | `retry:3` + 梯度等待 + 异常文本校验（第七节） |
| **Cloudflare（error 1034）** | 响应含 error code **1034** | 特定节点回源环路 | 换 IP/换线路（`dnsIp` 池），非规则问题 |
| **裸 UA 封锁** | 默认 `Python-urllib` / 无 UA → 403 或 1010 | 403 | `header` 必配真实浏览器 UA（API 站尤其：nicomanga 的 ihlv1 图床无 UA 403） |
| **限频型** | 正常页 + "搜索间隔 N 秒"文案 | 200 但内容不对 | 见 [Cookie 标记型限频破解](方法-Cookie标记型限频破解.md) |
| **需登录型** | 302 到 login.html | 302 | 登录 + `putLoginHeader`；见登录验证码篇 |

**分型三步**：拿响应码 → 看 Location/页面关键串 → 换 UA 再拿一次。三分钟内能定完。

---

## 四、★UA 是生死线：三种作用

UA 在很多站不只是"伪装"，它有**三种完全不同的副作用**，必须逐一确认：

### 作用 1：决定放行还是拦截

- zhaoshu.la：桌面 UA → GoEdge `302 /WAF/VERIFY/CAPTCHA`；手机 UA（Android14 Pixel8 Chrome126）→ **GET + POST 全豁免**。`header` 必须写手机 UA。
- lianaiya、rrssk 家族回退请求同理，**三处内联回退请求都要带移动 UA**（漏一处就吃 307）。

### 作用 2：决定返回哪套模板（规则会全线失效）

- ppxsw：分类页/目录页按 UA 返回**移动/PC 两套 HTML** → 规则必须按移动版写；
- xuken：PC UA = `style2_pc`、手机 UA = `style2_m` → `header` 固定手机 UA；
- wn10：PC/移动 UA 模板大小差 ~50% → 规则按 PC 模板写，`reader` 页不敏感。

### 作用 3：某些站"完整 UA 反而被 RST"（★反直觉）

- m.lzjxx.net（17mb 手机模板家族）：**完整 Chrome UA**（`AppleWebKit/537.36 + Chrome/xxx + Mobile Safari/537.36`）会被 **RST 断连**（`ERR_EMPTY_RESPONSE`/`ERR_CONNECTION_RESET`），沙盒 python 带该 UA 同样被 RST；而短 UA `Mozilla/5.0 (Linux; Android 14; Mobile)` 和桌面 UA **放行**。
- **诊断法**：`get_http_logs` 对比成功/失败请求的 UA，一眼定位。

> 所以配 UA 的正确顺序不是"抄个最新的"，而是：**枚举 4 种（完整移动 / 短移动 / 桌面 / 无 UA）各测一次，选既放行又是你要的模板的那个，写进 `header` 并在源备注里记下原因。**

---

## 五、GoEdge 专项（rrssk 家族）

已实测的完整处置：

```javascript
// 1) GET 类：移动 UA 即豁免，最省事（header 配好就不管了）
// 2) POST 类（如 action=loadChapterPage）：★强制人机验证
//    → 弹窗取码过盾（官方版有该 API）
var code = java.getVerificationCode('https://site/WAF/VERIFY/CAPTCHA?' + Date.now());
// 3) 目录内联回退请求也要带移动 UA（三处全加）
// 4) @css: 前缀不能用在 || 组合段内（GoEdge 修复过程中顺带发现的规则限制）
```

**过盾后的 Cookie 要能持久**：`enabledCookieJar=true` 时 `java.ajax` 的 POST 会自动把会话 Cookie 写进 `CookieStore`（wn10 实测）。若 `enabledCookieJar=false`，过盾结果不落地，下一次请求又吃 307。

**⚠️ 米游社的教训在这里同样适用**：改 `enabledCookieJar` 会连带改变 `AnalyzeUrl.setCookie()` 的 merge 行为，别为了绕过一个验证把 Cookie 策略整体关掉（会删掉配对必需键）。要精准，用 `removeCookie(url, key)`（⚠️ LT 版两参签名不存在，见版本差异篇）。

---

## 六、Cloudflare 专项

### 6.1 挑战触发条件是"频率"，不是"UA"

hanime1 实锤：**多页连打（8~10 请求/分钟）即触发 `Just a moment` 挑战**，一旦触发需要**长冷却**。

→ 调试该站必须：**极低频、单页重试、离线 jsoup 分析优先**。触发挑战后继续打 = 越陷越深。

同类：xuken `debug_source` 页间连抓 9 页触发封锁 → 页间 ≥1.5s。

### 6.2 IP 池

参考项目（Han1meViewer）内置 CF IP 池：`172.64.229.154 / 162.159.0.1 / 108.162.192.1 / 172.64.33.1 / 104.19.0.1`。
**手机侧实测只有部分时通** → 需要"宽池 + 测速选线 UI"，不能硬编码单 IP。hanime1 实测 `hanime1.com` 最快 `104.25.254.167`，上面三个已失效。

用法：`{"dnsIp":"ip1,ip2,ip3"}`（只劫持本域，OkHttp 自动 failover）+ `{{}}` 二次求值 → 换线路即时生效。见[URL模板篇第五节](方法-URL模板与DNS选线.md)。

### 6.3 error code 1034

响应里出现 `1034` = CF 节点回源环路/配置异常，**不是你的规则问题**，也不是"站点死了"。处置：换 IP / 换线路；等自愈。

---

## 七、间歇性 TLS RST 的工程化处理四件套

适用：CF 抖动（ggd8）、TCP RST（xuken）、CDN 冷连接（rrssk）。

### 件 1：`retry:3`（官方原生）

```javascript
"bookUrl": "https://site/book/1.html,{\"retry\":3}"
// JS 内拼 URL 选项时零双引号纪律：
var OPT = String.fromCharCode(44,123,34,114,101,116,114,121,34,58,3,125);  // ,{"retry":3}
url + OPT;
```

`AnalyzeUrl.getRetry` 原生支持 → 失败自动重试。**这是"扛住抖动"最便宜的手段，全链路每个 URL 都该加。**
⚠️ POST 加 retry 会撞 `oneShot`（RequestBody 不可 rewind）→ 只对 GET 有效。

### 件 2：异常文本校验（★不能只看有没有抛）

```javascript
var h = String(java.ajax(url) || '');
if (/javax\.net\.ssl|Exception|reset by peer|Unable to resolve host|timeout/i.test(h)) {
  // java.ajax 异常时【有时抛、有时返回 3748 字节的堆栈字符串】
  // → 不校验就会把堆栈当 HTML 去解析，得到"0 结果"这种诡异现象
  throw new Error('网络异常：' + h.substring(0, 120));
}
```

### 件 3：梯度等待 + 自愈请求

```
首次失败 → 等 5s 重试 → 再失败 → 等 30s
        → 降级路径（如 CDN 域名 → 源站 /chapter/{id}.html 直读，按 URL 数字去重升序保底）
CDN 人人书云对 loadChapterPage 限频 403 → GET 首页"自愈"后再试
★ 本 App 无 java.sleep！延迟用 Packages.java.lang.Thread.sleep(ms)
```

### 件 4：TLS 冷连接重试

冷连接（首次/久未访问）更容易被 RST。做法：正式请求前先打一次**首页 GET**（无解析需求，只为热连接/种 Cookie），再打接口。rrssk 实测有效。

---

## 八、自伤型故障：把自己的调试打成了封锁

**症状**：一开始是好的，越排查越坏，最后连正确规则都验不出来。

三个真实案例：

| 站 | 自伤方式 | 恢复 |
|---|---|---|
| 35sw | debug 循环连搜 → IP 级长惩罚（**失败尝试也刷新冷却**） | 10 分钟完全静默可解封；期间改**离线法** |
| xuken | 撞 RST 惩罚累计 | 最长 1.5h+，删 Cookie 也无效，只能静默 |
| hanime1 | 8~10 req/min → CF 挑战 | 需长冷却 |

**纪律**：

1. **优先离线验证**：`eval_js` 里嵌真实 HTML + `new AnalyzeRule().setContent()` → `getElements`/`getString` 模拟 `BookList` 全流程，**零配额消耗**（63sg 的解析问题、35sw 的搜索列表都是这么定位的）；
2. **一次 debug 只验一件事**，不要顺手连打多页；
3. **意识到自己也是变量**：清域、改 Cookie、开关 `enabledCookieJar` 都可能改变环境状态，让后续判断失真（米游社清域案）；
4. 排查完必须**把诊断桩撤掉**（`save_auto_task` 被覆盖类事故）。

---

## 九、判活决策树

```
请求失败
├─ DNS 解析失败 / ERR_NAME_NOT_RESOLVED
│    ├─ 换镜像域名（Bing site: 或同 CMS 站）→ 有 → 迁移 bookSourceUrl（保排序/分组：删旧存新）
│    └─ 全无 → 真死了
├─ ERR_CONNECTION_RESET / handshake aborted
│    ├─ 隔 5 分钟复测 3 次：全失败 → 试换 CDN 原生主机名 / dnsIp 池
│    └─ 时好时坏 → ★CF 抖动，上"四件套"（retry+异常校验+梯度等待+冷连接）
├─ ERR_CONNECTION_TIMED_OUT（31s）
│    └─ debug 时常见：DNS 被污染且没带 {"dnsIp":…} → 补 URL 选项
├─ 403 / 307
│    ├─ 有 /WAF/VERIFY/CAPTCHA → GoEdge → 移动 UA 或 getVerificationCode
│    ├─ 有 Just a moment → CF 挑战 → 冷却 + 降频，别硬打
│    └─ 裸 → UA 问题，四 UA 枚举测
├─ 503 + var token → lianaiya 型自研挑战 → 内联过盾（WAF 指南）
├─ 302 → login.html → 需登录，不是站点故障
└─ 200 但内容不对
     ├─ "搜索间隔 N 秒" → Cookie 标记型限频篇
     ├─ "请刷新页面"/占位 → 接口参数缺（aaawz：必须 ?format=g2）
     └─ 汉字读不通 → 字体置换篇
```

---

## 十、避坑清单

| # | 坑 | 对策 |
|---|---|---|
| 1 | 一次打不开就判"站死了" | 多时点/多通道/多协议/多 UA 复测矩阵 |
| 2 | 间歇 RST 当代码 bug 改规则 | `retry:3` + 异常文本校验，先扛住 |
| 3 | 以为 `java.ajax` 一定会抛异常 | 有时返回堆栈文本，必须 `indexOf('Exception')` |
| 4 | 移动 UA 站只在 searchUrl 配了 UA | 内联回退请求（目录/正文）**每一处**都要带 |
| 5 | 抄一个最新 Chrome UA 就完事 | 有的站完整 UA 反被 RST（17mb 系）→ 四 UA 枚举 |
| 6 | UA 只管放行，不管模板分发 | 同一站 PC/移动两套 HTML，规则会全线失效 |
| 7 | GoEdge 站指望 POST 也豁免 | POST 常强制人机 → `getVerificationCode` |
| 8 | CF 站用 debug 连打 9 页 | 触发挑战 + 长冷却；页间 ≥1.5s |
| 9 | 硬编码单个 CF IP | 池化 + 测速选线 UI；池会过期，留更新通道 |
| 10 | 限流后持续重试 | 失败尝试刷新冷却 → 越重试越久，改为静默 + 离线验证 |
| 11 | 为绕验证关掉 CookieJar | merge 语义变化会删掉配对必需键 → 全量发送 |
| 12 | 用 `java.sleep` 做退避 | 本 App 无此 API → `Thread.sleep(ms)` |
| 13 | 排查后不撤诊断桩 | 排查完重存正式版 |
| 14 | HTTPS 不通就判死 | 有的站只有 HTTP（xheiyan），或 HTTPS 是 nginx 默认页 |
| 15 | 沙盒不通 = 站死 | 沙盒连不上 ≠ 站点失效；必须 App 内 `java.ajax` 实测 |

---

## 附：源备注里该写的"连通性档案"

在 `bookSourceComment` 留一段，下次谁接手（包括三个月后的你）都能秒判：

```
【连通性档案 2026-09-14】
主域 https://site.cc/  已迁 Cloudflare（104.21.x.x / 172.67.x.x）
表现：间歇 TLS RST，无 WAF 挑战、无登录、无搜索频控
UA：  不影响（PC/移动/无 UA 同一份响应式 HTML）
处置： 全链路 retry:3 + 异常文本校验
镜像： other.com 同程序但书库 ID 不互通 → 只做连通性探测，不做域名切换（切换会让书架全失效）
判活： 至少 3 个时点复测；沙盒不通不代表站死
```

> 最后一条尤其重要：**镜像站"能打开"不等于"能换"**。同程序不同库的站（ggd66 vs huilingtian、qmzw5 vs 123wxwz），换域名 = 全书架失效。迁移前必须验证**书籍 ID 是否互通**。
