# 方法：Flutter Dart AOT APK 逆向与发布页寻线

> 场景：用户给一个 App 的 APK 要求做书源，App 是 Flutter 打包（Dart AOT 编译进 `libapp.so`），
> 且后端域名经常轮换/被封。本文给出「APK 域名池提取 → 后端判活 → 发布页寻真实线路 → Web 书源」的完整链路。

---

## 1. 先判是不是 Flutter AOT

看 APK 内是否有这些特征：

```
lib/arm64-v8a/libapp.so     ← Dart 快照（业务代码全在这）
lib/arm64-v8a/libflutter.so ← Flutter 引擎
AndroidManifest: io.flutter.embedding.android.NormalTheme
```

`libapp.so` 通常 15~30 MB。`classes.dex` 里**只有** Flutter 插件壳，业务逻辑 100% 在 Dart 快照里，
所以 **Java 层反编译（jadx/dex 分析）对这个 App 基本无用**，不要浪费时间。

---

## 2. 从 libapp.so 提取域名池与 API 清单（MT MCP 零成本做法）

Dart snapshot 的字符串存在 `.rodata`，用 MT 的 `native_strings` 检索即可：

```
target = native_strings
prefix = lib/arm64-v8a/libapp.so
query  = https://          → 拿域名池
query  = /content/         → 拿业务 API 路径
query  = /api/             → 拿网关 API
```

**注意**：结果会被 MCP 工具截断（单次 200 hit），保存到 `/tool_outputs/*.txt` 后用 shell 提取：

```bash
cd /tool_outputs && for f in *.txt; do grep -o 'content/[a-z0-9-]*/[a-z0-9/-]*' "$f"; done | sort -u > paths.txt
```

⚠️ MCP 的 `mt_apk_copy_entry` 想把 `.so` 拷到本地时，若 Home 在 Android 设备上会
`FILE_ACCESS_DENIED`（沙盒 `/workspace` 与 MCP Home 不互通）。此时**不要**试图把 so 拉到沙盒用
`strings` 分析——直接用 MCP 的 `native_strings` 检索 + shell 后处理，足够。

### 判据：Dart 快照 hash 不是密钥

`.rodata` 开头有形如
```
d20a1be77c3d3c41b2a5accaee1ce549product no-code_comments dwarf_stack_traces_mode ...
```
这 32 位 hex 是 **Dart snapshot 版本标识**，不是签名密钥，不要往 HMAC 方向猜。

---

## 3. 后端判活：三组对照实验定生死

不要看到 403/502 就断定"服务下线"，按下面顺序做：

| 步骤 | 请求 | 判据 |
| --- | --- | --- |
| ① 突破 UA 封锁 | `GET /` 带完整 Chrome UA | 原站 CF 常见 `error code: 1010`（UA 被禁），换 UA 即通 |
| ② 网关是否活着 | `GET /` | 返回 `{"service":"xxx","status":"ok"}` = 网关壳活着 |
| ③ **业务路由是否存在** | `GET /api/v1/app/config`<br>`GET /api/v1/zzz_not_exist`<br>`GET /api/v1/a/b/c` | **三者返回完全相同** → 纯网关壳，无业务路由 |
| ④ 内容服务是否活着 | `GET /content/xxx` | 一律 502 → 源站整体不可达 |

**关键铁律**：如果 `/api/v1/{任意不存在路径}` 与已知路径返回同一句错误文案，
说明这是个 catch-all 网关，后面所有 `/content/*` 的 502 都**不是签名问题**，
加签名头/换 UA/换备用域都不会变。此时应果断放弃 APK 接口，转 Web 线路。

---

## 4. 发布页寻线（域名轮换站的通用解法）

轮换域名的站几乎都会挂一个**地址发布页**。找法：

1. 官网 HTML（`huangguoju.com`）里翻 `<a href>`，找 `*.pages.dev` / `*.github.io` 之类托管页
2. 落地页 HTML 里常有 `publish.js` / `publish.css`
3. 发布页 JS 里直接写死域名池：

```javascript
var subdomains = ['thu','pku','fdu', ...];        // 高校名随机子域
var urls = ['40ygo615.cc/', 'h2na6qa39.cc/', ...]; // 根域池
var foreverUrls = ['https://huangguoai.com', 'https://huangguoai.ai'];
```

4. 组合探测：`{sub}.{root}/` → 跟 301 → 落地真实线路
5. **永久地址**（`foreverUrls`）优先试，往往直接就是可用站点

> 本例：`thu.40ygo615.cc` → 301 → `4108.arj2ftl0.cc`；
> 永久地址 `huangguoai.ai` 首页直接给出真实线路 `l205.arj2ftl0.cc`。

---

## 5. 沙盒 vs App 通道：先用哪个？

**先沙盒**（Python urllib 快），但沙盒可能：
- 无 `curl`（用 `python3 -c` + urllib）
- 出口 IP 被墙/超时
- DNS 污染（`No address associated with hostname`）

**沙盒不可信时切 App 通道**（LegadoTEAM MCP `eval_js`）：

```javascript
'' + java.ajax('https://example.com/')     // 单参！双参重载不存在
```

App 通道的优势：真实手机网络、真实 UA、能带 Cookie。
劣势：慢（每跳 15s 超时），需要批量测时注意 `timeoutSec`。

⚠️ **沙盒能通不代表服务活着，沙盒不通也不代表服务死了**（本例沙盒全 502、
App 通道同样 502，才最终确认下线）。

---

## 6. Web 线路的书源化：SSR 站点优先找 `<source>`

Dart/SPA 站转 Web 后，先看详情页是否 **SSR 直出播放地址**：

```html
<video class="hg-web-play__video" data-ssr-native controls playsinline ...>
  <source src="https://cdn/xxx.m3u8?auth_key=<expire>-0-0-<md5>&v=3&time=0&via=hgdj&via_bm=dx" type="application/vnd.apple.mpegurl">
</video>
```

有 `data-ssr-native` / `<source>` 就意味着**不需要 WebView、不需要 JS 执行**，
一条正则/`indexOf` 就能抠出地址。判断方法：`curl` 拿到的 HTML 里直接搜 `<source src=`。

若没有 SSR（播放地址靠 JS 异步拉），才需要考虑 `useWebView` + `callBackJs` 或
`java.webView` 探针方案（见 hanime1 / hlwf6 案例）。

---

## 7. 防盗链时效签名的通用形态

```
?auth_key=<unix_expire>-0-0-<md5hex>
```

- `<unix_expire>`：秒级过期时间（本例约 +10 分钟）
- 中间 `0-0`：疑似 rate/limit 参数
- `<md5hex>`：服务端按 路径+过期时间+盐 生成，**客户端无法自造**

**结论**：这类签名只能"从页面里抠现成的"，不能复现算法。
书源策略 = 每次进正文重新请求详情页抠地址，不做长期缓存。

---

## 8.  Checklist

```
□ APK 是 Flutter AOT？ → lib/arm64-v8a/libapp.so 存在
□ 域名池已从 libapp.so .rodata 提取（native_strings: https://）
□ /content/* API 清单已提取（native_strings: /content/）
□ 三组对照实验确认 /api/v1/* 是 catch-all 网关壳
□ /content/* 502 与签名无关（加签名头仍 502）
□ 已从官网 HTML 找到发布页（*.pages.dev / publish.js）
□ 域名池已从 publish.js 提取，永久地址已试
□ 真实 Web 线路已确认（详情页可访问）
□ 详情页 SSR 直出 <source src>（无需 WebView）
□ m3u8 auth_key 时效签名形态已记录
□ 书源已存 App + check_source 通过 + debug_source 全链路实测
```
