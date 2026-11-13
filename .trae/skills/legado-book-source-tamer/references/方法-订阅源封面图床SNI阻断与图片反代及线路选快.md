# 方法：订阅源「封面图不显示 + 视频加载慢」——图床 SNI 阻断 / 图片反代 / 线路选快 / 签名时效自愈

> 蓝本：91PORN 订阅源（`sourceName=91PORN`，`sourceUrl=https://418.sol148.com/index.php`），261113 报障修复。
> 适用：Legado 订阅源（RssSource）列表封面全部空白、列表/内容页打开慢、视频转圈；
> 也适用于任何「图片域被 SNI 阻断但站方 HTML 仍给该域」的图文/视频源。

---

## 0. 结论先行（三个独立根因，别混成一个）

| 报障 | 真因 | 判据 | 修法 |
|---|---|---|---|
| 封面图不显示 | 站方图床 `1729130453.rsc.cdn77.org` 被 SNI 重置，App 每个封面请求 5~8s 失败 | `java.ajax(封面URL)` 返回 5901B `SSLHandshakeException` 堆栈串（不是抛异常，是 **body 里包了堆栈**） | `ruleImage` 改 `@js:` 把该域改写成 `https://i2.wp.com/<host><path>?w=320` |
| 列表/内容页慢 | ① 44 个 5~8s 失败封面请求并发堆积；② 当前线路 `a.26702.app` 已劣化到 60s 超时；③ 主站偶发 SSLHandshakeException | 线路对照：`418.sol148.com` 两轮 378~429ms 完整 75KB，`a.26702.app` 60s/2.5s 失败 | 默认线路改快镜像 + 面板「🚀 一键切到最快线路」+ 测速完自动切换 |
| 视频加载慢/转圈 | 直链 `&e=` 是 ~2h 时效签名，过期后 **302 跳回被墙的 cdn77 域**，播放器卡 5~8s TLS 握手 | 反向验证：`e` 改成过去 1h/1d、去掉 `&f=` → 全部 `302 text/html`，`Location: https://1729130453.rsc.cdn77.org//mp43/...` | 正文内层加「签名时效预检」：`e - now < 300` 时 `java.post /vlk.php` 换新鲜直链 |

---

## 1. 诊断顺序（先分层，别一上来改规则）

### 1.1 先确认规则层没问题
从 LAN `/getRssSources` 回读当前落库对象，看 `ruleImage`。本例已是
`tag.img.0@src||tag.img.0@data-src`（261107 修过「一个条目 3 个 `<img>` 被 `getString` 拼成畸形 URL」的坑），
所以 **不是选择器问题**。WS 日志里 `└获取图片url` 也是单行合法 URL → 规则层已排除。

### 1.2 再看网络层（App 真机，别用沙盒出口）
沙盒 curl 与 App 出口 IP 不同（历史多次实锤），**不能给网络层定性**。
用 App 内 `java.ajax(url)` 单参直取封面：

```js
var r = String(java.ajax('https://1729130453.rsc.cdn77.org/thumb/1259686.jpg'));
// → 5901B "javax.net.ssl.SSLHandshakeException: SSL handshake aborted:
//   I/O error during system call, Connection reset by peer ..." 堆栈串，5.6~8.1s
```

★ **铁律：`java.ajax` / `java.connect` 失败不抛异常，而是 code=200 + 异常堆栈串当 body**
（`JsExtensionsAndroid` 用 `runCatching` 包了 body），所以必须显式排
`Exception` / `timeout` / `UnknownHost`，否则会误判成「HTTP/200 正常」。

### 1.3 反向验证（必须有）
- HTTPS 原域 → SSLHandshakeException（5.6~8.1s）
- HTTP 明文 → `SocketException: Connection reset`（2.9s）⇒ 不是证书问题，是 SNI/连接重置
- 站方自身 `/thumb/<id>.jpg` 与 418 镜像 → 404（921B）⇒ 站方没有本地代理路径
- `rsc.cdn77.org` 主域 → `UnknownHostException`
- 对照 `img.alicdn.com` → 200 真 GIF（351ms）⇒ **不是 App 整体断网，只针对该域**

---

## 2. 图片反代选型：8 组对照 + 冷缓存坑

公共图片反代逐组真机测（App `java.ajax` 单参）：

| 通道 | 结果 |
|---|---|
| `images.weserv.nl` / `wsrv.nl` | SSLHandshakeException |
| `i0.wp.com`（原图无 query） | SSLHandshakeException（有时 200） |
| `api.allorigins.win` | 520 / 14.1s |
| `api.codetabs.com` | 522 / 20s |
| `corsproxy.io` | 401 需 key |
| `external-content.duckduckgo.com` | SocketTimeoutException 15.3s |
| `ghproxy.net` | 403 |
| **`i1.wp.com` / `i2.wp.com`** | **200 真 JPEG** |

### ★★ 决定性的「?w=320」发现
不带 query 的原图版冷缓存回源时**偶发** SSLHandshakeException（3 轮里 4 次失败）；
加 `?w=320` 缩放参数后走 Jetpack 图片 CDN 缓存，**12/12 全绿**（35~1259ms，8.9~18KB，平均 597ms）：

```
https://i2.wp.com/1729130453.rsc.cdn77.org/thumb/1259697.jpg?w=320
→ 200 / ffd8ffe0...JFIF / 8940B / 29~438ms
```

列表缩略图 320px 足够；`i2.wp.com/ssl:<host>` 前缀会 400（参数无效），不要用。

### 判据纠错：Rhino String 的 charCodeAt 不是字节
`java.ajax` 把二进制按字符串返回，`r.charCodeAt(0)` 得到 `0xFFD8`（UTF-16 码元），
**不是** `0xFF`；写成 `r.charCodeAt(0)===0xff` 会把 8/8 全部误判成失败。
正确判据 = `r.length>5000 && r.indexOf('Exception')<0 && r.indexOf('error code')<0`，
或看 `r.substring(0,2)==='ÿØ'` / `c0` 是否为 `ffd8` 或 `ff`。

---

## 3. `ruleImage` 写法（只改被墙域，不写死站方图床）

```js
@js:
(function () {
  var u = '';
  // 主通道：result 是条目 Element，jsoup 直取首图（避开 like/dislike 三图拼接）
  try {
    var imgs = result.select('img');
    if (imgs.size() > 0) {
      u = String(imgs.get(0).attr('src') || '');
      if (!u) u = String(imgs.get(0).attr('data-src') || '');
    }
  } catch (e0) { u = ''; }
  // 兜底：规则索引写法（@js 环境 java.getString 可用，261107 已验证）
  if (!u) { try { u = String(java.getString('tag.img.0@src') || ''); } catch (e1) {} }
  if (!u) { try { u = String(java.getString('tag.img.0@data-src') || ''); } catch (e2) {} }
  u = u.trim();
  if (!u) return '';
  // 面板开关（默认开；读不到也默认开，保证封面一定能显示）
  var on = 1;
  try {
    var raw = '';
    try { raw = String(source.getVariable() || ''); } catch (a0) {}
    if (!raw) {
      try { raw = String(cache.get('sourceVariable_' + String(source.sourceUrl || '')) || ''); } catch (a1) {}
    }
    if (raw) {
      var o = JSON.parse(raw) || {};
      var v = String(o.picProxy === undefined ? '1' : o.picProxy);
      if (v === '0' || v === 'false') on = 0;
    }
  } catch (e3) { on = 1; }
  if (!on) return u;
  if (u.indexOf('//') === 0) u = 'https:' + u;
  if (u.indexOf('http') !== 0) return u;              // 相对路径交给 loadWithBaseUrl
  var m = u.match(/^https?:\/\/([^\/]+)(\/.*)$/);
  if (!m) return u;
  var host = m[1], path = m[2];
  if (host !== '1729130453.rsc.cdn77.org' && host.indexOf('.rsc.cdn77.org') < 0) return u;
  return 'https://i2.wp.com/' + host + path + '?w=320';
})()
```

★ **只改写命中黑名单的域，其余原样返回** ⇒ 站点以后换图床不会被写死（用户偏好：不写死上限/域）。
★ 开关用**两个按钮** `PN_setPicProxy('1')` / `PN_setPicProxy('0')`，**不要用 toggle**：
V1 toggle 在 `login()` 的 `result` 里取值语义双版不一致，且 `login()` 每次点 √ 都重建
`sourceVariable`，拿不到值会把用户已关的开关误改回开。按钮直接传字符串最稳。

---

## 4. 线路选快：LT/E 是独立 App，LAN 写不进变量

- 缓存回读 `cache.get('sourceVariable_https://418.sol148.com/index.php')`
  → `{"page":"1","pnLine":"https://a.26702.app"}`，**用户一直停在劣化线路**。
- 改 `PN_LINE_DEFAULT` 只对「从未设过线路」生效；已有 `pnLine` 的用户不会被迁移。
- LT 可以用 MCP `eval_js` 的 `cache.put(KEY, ...)` 直接写（本轮已把 LT 切到 418）。
- **E 版 LAN 1125 的 `setVariable` / `getVariable` / `evalJs` / `getHttpLogs` 全是 `web/xxx` 占位回显**，
  三种 body 试探都返回字面串 ⇒ 只能靠用户在 App 面板操作。
  真实可用的 E 版接口只有 `/getRssSources`、`/saveRssSources`（数组）、`/deleteRssSources`（完整对象数组）、
  `/getRssSource?url=`（E 版 WS 1126 = HTTP+1）。

### 面板「🚀 一键切到最快线路」实现要点
```js
function PN_fastLine() {
  var list = PN_found();                    // 不写死条数上限
  var i, best = '', bestMs = 999999, hit = 0;
  for (i = 0; i < list.length; i++) {
    try {
      var r = java.connect(list[i] + '/v.php?next=watch&page=1', PN_hdr(), 8000);
      var b = String(r.body());
      // 判活三判据：无堆栈串 + 长度>5000 + 含站点特征
      if (b.indexOf('Exception') > -1 || b.indexOf('timeout') > -1 ||
          b.length < 5000 || b.indexOf('col-xs-12') < 0) continue;
      var ms = r.callTime ? Number(r.callTime()) : 99999;   // 真毫秒
      if (isNaN(ms) || ms <= 0) ms = 99999;
      hit++;
      if (ms < bestMs) { bestMs = ms; best = list[i]; }
    } catch (e) {}
  }
  if (!best) { PN_toast('⚠ 暂无可用线路'); return PN_line(); }
  PN_writeLine(best);                       // 双写 source.put + sourceVariable
  PN_bumpRev();
  return best;
}
```
★ 同时把原 `PN_testAll()`（测速按钮）从「只把 ms 写进按钮名」改成**测速完自动 `PN_writeLine(list[best])`**，
否则用户测完速还得自己点一次，仍停在劣化线路。
★ 真机验证：5 条线路里只有 418 命中（597ms / 81KB），其余全失败 ⇒ 自动选中 418。
★ `PN_base()`（`{{}}` 内联 JS）**不能**放 `java.connect` 做自动选线：历史诊断桩实锤
`SharedJsScope` 里裸 `java`/`cache`/`source` 全抛异常，只有 `this.source.getVariable()/setVariable()` 可用。
自动选线只能放在 `loginUrl`（面板环境确定有 java）。

### 提速对照（同一份源、同一篇文章类型）
| | 列表 `≡获取成功` | 内容页完成 |
|---|---|---|
| 切线路前（a.26702.app） | 2.608s | 3.788s |
| 切线路后（418.sol148.com） | **0.513~0.602s** | **1.010~1.892s** |

---

## 5. 签名时效自愈（正文内层最小改动）

站点正文直链形态（261107 改版后）：
`var vbF0=strencode2("%3c%73%6f%75%72%63%65...")`
→ `decodeURIComponent` → `<source src='https://la.btc620.com//mp43/<id>.mp4?st=...&e=<unix>&t=...&k=...&f=...'>`

- `e` 距当前 ~7200s（2h）；`&f=` 是签名必需（去掉 → 302）。
- **反向验证**：把 `e` 改成过去 1h / 1d、或删 `&f=` → 全部 `302 text/html 145B`，
  `Location` 跳回 `1729130453.rsc.cdn77.org` —— 正是被 SNI 阻断的域，播放器卡 5~8s 才失败。
- fresh：`HEAD 200 video/mp4 16MB`（208~898ms）、`Range 206 Content-Range bytes 0-262143/16283995`（208~302ms）。

修法 = 在 v5 内层脚本的**输出判断之前**插一段（不改成 HTML 播放器页，
`<usehtml>` 页内 `java` 注入未验证，风险更高）：

```js
if (url) {
  try {
    var em = url.match(/[?&]e=(\d+)/);
    if (em) {
      var exp = parseInt(em[1], 10);
      var now = Math.floor(Date.now() / 1000);
      if (exp - now < 300 && typeof java.post === 'function') {
        // 取页面 vbG / vbGT，POST /vlk.php 换 {"u":新鲜直链}
        // origin 从 baseUrl 推（随线路走），绝不写死域
      }
    }
  } catch (eR) {}
}
```

★ **顺序铁律**：`<js>` 规则的求值结果 = 脚本**最后一条语句的值**。
如果把这段预检追加在 `if (!url...) {...} else { url; }` **之后**，`eval` 返回 `undefined` ⇒ 正文空。
必须插在输出判断**之前**，且末尾仍保留 `url;`（构建脚本要断言）。

★ 多层 Base64 修复定式（与 261108 相同）：只重编码**第 2 段**（内层脚本），
外层署名校验层、错误信息层、`sourceComment` 一律字节级原样保留；
`ruleContent` 里的 `source.sourceComment.includes(java.base64Decode('...作者：夜明空...'))`
是署名校验，改坏会恒定输出「检测到书源被恶意篡改」。

---

## 6. 交付闭环（双版）

1. `build_261113.py` 带 12 条断言：除 6 个改动字段外其余 26 项字节级不变；三层解码回读；
   `loginUi` 无 toggle；`PN_picText()` 有 `return`（动态 viewName 必须返回纯文本）。
2. LT(1122) / E(1125) 各自基于**自己当前落库对象**生成（E 版少 `enableReadRecord` 字段，
   不能拿 LT 对象直接存 E）。`/saveRssSources` 必须传**数组**，单对象报 `Expected BEGIN_ARRAY`。
3. `/getRssSources` 回读逐字段 diff = 0。
4. LT WS 1123 / E WS 1126 真实规则链回归：
   `└获取图片url` = 单行 `https://i2.wp.com/...?w=320`、
   `└获取文章链接` 跟随线路、正文输出完整 `https://la.btc620.com//mp43/....mp4?...&f=...`。
5. `get_http_logs` 看 App 图片加载链路：批量 12 个 `?w=320` 请求**全部 200**（35~1068ms，零异常）。
6. **诊断桩/中间版每轮都会覆盖落库 ⇒ 最后必须重存正式版并回读**（本轮共重存 3 次）。

---

## 7. 通用铁律（跨站可复用）

1. **HTTP 日志里大批同一域 `SSLHandshakeException` + 每张图 5~8s = SNI 阻断**，
   不是规则选择器问题，别再改 `ruleImage` 的索引写法。
2. `java.ajax` / `java.connect` 失败返回**堆栈串当 body**，判活必须排 `Exception`/`timeout`，
   且 `HTTP 200 ≠ 图片能解码`（二进制要看魔数/块对齐）。
3. 图片反代带**尺寸参数**（`?w=320`）比原图版稳得多：命中 CDN 缓存、避免冷回源被墙；
   先跑 12 张批量验证再落库，别凭 1 张成功就下结论。
4. 「视频加载慢」要分三层查：**失败封面请求堆积 / 线路劣化 / 直链签名过期 302 跳回被墙域**，
   每层都要有正向组 + 反向组（改 `e` 到过去）。
5. **默认线路改了不等于现有用户会迁移**：`sourceVariable.pnLine` 已存在时默认值不生效；
   LT 可用 `cache.put` 直接修，E 版只能靠面板按钮 ⇒ 面板必须有「一键选最快」且测速自动切换。
6. 用户偏好：**不写死页码上限、不写死域名**，翻页/线路终止跟随站点自身信号；
   封面改写只命中黑名单域，其余原样返回，站点换图床后自动可用。
7. 双版本差异必须分别验证：E 版正文 `≡获取成功` 写死打印 `sourceUrl`（LT team 已重构打印真 URL），
   **别看这行判断线路**，看 `└获取文章链接` 或 `≡获取成功:<域>/v.php` 列表行。
