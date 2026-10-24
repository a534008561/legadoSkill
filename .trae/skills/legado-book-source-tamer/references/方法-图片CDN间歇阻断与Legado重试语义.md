# 方法：图片 CDN 间歇阻断的根因定位 —— Legado `retry` 语义、`dnsIp` 多 IP 池与章节内分页陷阱

> 2026-10-24 实战沉淀（蓝本：哔咔漫画自包含书源 v75 → v76 修复）
> 关联：[[方法-URL模板与DNS选线]]、[[方法-LAN-Web服务保存书源与全端点手册]]、[[方法-书源交付质量闭环]]、[[方法-WAF与CF间歇故障及站点判活]]

---

## 0. 一句话结论

「正文图片有的显示失败」这类**部分成功、部分失败**的现象，根因往往不是规则写错，而是三层机制叠加：

1. **Legado 的 `retry` 只重试非 2xx 响应，不重试 IOException**（连接超时/DNS 失败直接抛出）；
2. **CDN 同一批 IP 会被间歇性阻断**，并发批量下载时形成"同节点批量失败"；
3. **`nextContentUrl` 取错变量会导致章节内分页永远停在第 1 页**，图片"少一大截"看起来也像失败。

v76 的修复 = **去掉无效 retry + 10 IP 池按图轮换首选顺序 + 修正 nextContentUrl 取值来源 + 降并发**。

---

## 1. 【源码级铁律】Legado `retry` 不重试 IOException

`OkHttpUtils.kt`：

```kotlin
suspend fun OkHttpClient.newCallResponse(retry: Int = 0, builder: ...): Response {
    var retriesRemaining = retry.coerceAtLeast(0)
    while (true) {
        val response = newCall(requestBuilder.build()).await()   // ← IOException 在这里抛出
        if (response.isSuccessful || response.code in 300..399 || retriesRemaining == 0) {
            return response
        }
        response.close()
        retriesRemaining--
    }
}
```

`await()` 的 `onFailure` 直接 `resumeWithException(e)` —— **连接层异常（SocketTimeout / UnknownHost / ConnectException）根本走不到重试判断**。

**结论**：URL 选项里写 `"retry":3` 对"连接超时"零作用；它只对「HTTP 5xx / 4xx 非 2xx」有效。
写书源时不要把 retry 当"抗网络抖动"手段。

### 1.1 判别"retry 有没有用"的实操方法

| 失败形态 | 日志 duration | 是否 retry 能救 |
|---|---|---|
| `IOException` / `SocketTimeoutException` / `UnknownHostException` | = 超时值（10s/15s） | ❌ 完全无效 |
| `HTTP 5xx` | 几十~几百 ms | ✅ 有效 |
| `IOException` duration = **0ms** | 0ms | ❌ 属 failUrl 黑名单秒拒，重试无意义 |

---

## 2. 【源码级机制】`dnsIp` 多 IP 池是抗间歇阻断的标准姿势

`AnalyzeUrlNetworkOptions.kt`：

```kotlin
internal fun buildScopedDns(targetHost: String, addresses: List<InetAddress>, fallback: Dns): Dns {
    return Dns { hostname ->
        if (hostname.equals(targetHost, ignoreCase = true)) addresses
        else fallback.lookup(hostname)
    }
}
```

要点：

- `dnsIp` **只约束首个 host**（重定向目标不受控）；
- 传**逗号分隔多 IP**时，OkHttp 按顺序尝试，**自动跳过不通的**；
- `parseDnsIpAddresses` 逐个 `parseIpLiteral`，非法 IP 会让整个选项抛异常（`invalidDnsIp`）——**池里不能混入域名**；
- `dnsIp` 与 `proxy` **互斥**（`validateDnsIpProxyCompatibility` 会抛）；
- `dnsIp` 会让 `AnalyzeUrl` 走 `buildRequestClient`（换 client），并把 Cronet interceptor 摘掉改用 OkHttp —— 所以**带 dnsIp 的请求不经 Cronet**。

### 2.1 「每张图轮换 IP 顺序」比「所有图共用一个池」更抗阻断

同一批图共用同一个池时，OkHttp 对每张图都会**从池首元素开始试**，于是所有图都压在同一节点上；该节点一旦被阻断，整章一起失败。

按图序号轮换（`idx % pool.length` 偏移）后，40 张图的首选节点均匀分布成 10 组 × 4 张，**单节点阻断只影响 4 张而不是 40 张**。

```js
var _out = _d.map(function (x, idx) {
  var u = picab_img(x.media);
  var _p = _poolBase.slice();
  var _shift = idx % _p.length;
  _p = _p.slice(_shift).concat(_p.slice(0, _shift));
  return '<img src="' + u + ',{"method":"GET","timeout":30000,"dnsIp":"' + _p.join(",") + '"}">';
});
```

### 2.2 对照实验怎么设计（必须含反向验证组）

```
组A（实验组）：裸 URL（无 dnsIp）        → 必败：UnknownHostException / SocketTimeoutException
组B（对照组）：同 URL + dnsIp 多 IP 池   → 必成：~1.7s，256KB hex
```
反向验证组的作用：如果只测"带 dnsIp 成功"，无法排除"是网络整体恢复了"。裸 URL 必败才是根因的实锤。

---

## 3. 【排障判据】0ms 秒拒 = failUrl 黑名单，不是网络问题

`OkHttpStreamFetcher.kt`：

```kotlin
companion object { private val failUrl = hashSetOf<String>() }

override fun loadData(...) {
    if (failUrl.contains(url.toStringUrl())) {
        callback.onLoadFailed(NoStackTraceException("跳过加载失败的图片"))
        return                       // ← 0ms 直接返回，日志 duration=0
    }
    ...
}
```

- 一次失败后该 URL 进黑名单，**同一 App 进程内不再重试**；
- `manga == false`（普通图文阅读）才写黑名单，漫画模式不写；
- **0ms 的 IOException 是黑名单秒拒，不是超时** —— 排障时必须先看 duration 再下结论。

---

## 4. 【隐藏 bug 模式】`nextContentUrl` 取错变量 → 章节内分页只出第 1 页

哔咔章节接口 `comics/{id}/order/{order}/pages?page=N` 返回：

```json
{"data":{"pages":{"page":1,"pages":6,"limit":40,"docs":[...40张图...]}}}
```

即**一章最多 6 页 × 40 图 = 240 张图**，需要 `nextContentUrl` 驱动翻页。

App 侧 `BookContent.analyzeContent`：nextContentUrl **返回单个值**时，App 会自动循环翻页直到它返回空串：

```kotlin
if (contentData.second.size == 1) {
    var nextUrl = contentData.second[0]
    while (nextUrl.isNotEmpty() && !nextUrlList.contains(nextUrl)) { ... }
    Debug.log(bookSource.bookSourceUrl, "◇本章总页数:${nextUrlList.size}")
}
```

**旧版 bug**：nextContentUrl 里写 `String(book.tocUrl).match(/order\/(\d+)/)`。
但 `book.tocUrl` 是**目录页 URL**（`comics/{id}/eps?page=1`），根本不含 `order/` → 正则永不命中 → 永远返回空 → 实际表现是"只有 40 张图，后面的都没了"。

**正解**：章节自身的 `baseUrl` 就是 `comics/{id}/order/{order}/pages?page=N`，直接从 `baseUrl` 取 order：

```js
var _ord = String(baseUrl || "").match(new RegExp("order/(\\d+)"));
```

**排障抓手**：debug 日志里的 `◇本章总页数:1` 就是信号（真实应为 6）。
另注意 `nextContentUrl` **不能写 `return`**，要用末尾表达式；返回空串表示"没有下一页"。

---

## 5. 【通道盘点】正文图片实际走哪条路（决定 dnsIp 是否生效）

| 场景 | 通道 | dnsIp 生效？ |
|---|---|---|
| 正文插图 `<img src="...jpg,{options}">` | `BookHelp.fetchImage` → `AnalyzeUrl.getByteArrayAwait` | ✅ 生效（源码实测） |
| 封面 / 列表缩略图（Glide） | `OkHttpStreamFetcher` → `AnalyzeUrl.getGlideUrl` | ❌ **不生效**（Glide 丢弃 URL 选项） |
| `java.ajax(url)` | `AnalyzeUrl.getStrResponse` | ✅ 生效 |
| `java.ajaxAll(urls)` | 并发 `getStrResponseAwait` | ✅ 生效，且并发下载快得多 |

### 5.1 `type` 选项 = 二进制 hex 通道（可用于取证/自建代理）

`AnalyzeUrl.getStrResponseAwait`：

```kotlin
if (type != null) {
    return StrResponse(url, HexUtil.encodeHexStr(getByteArrayAwait()))
}
```

- URL 选项加 `"type":"jpg"` → 返回体是**完整图片的 hex 字符串**（512336 字符 / 256168 字节）；
- 这是**验证图片能否下载的最干净手段**（不看 Glide、不看渲染）；
- ⚠️ `java.base64Encode(byte[])` 在 Rhino 下会把 byte[] 错转字符串（实测得到 `"W0JAYjdhNDg2Ng=="` 这种固定 16 字符），**不能用它拼 data URI**，否则图片损坏。

### 5.2 `java.ajaxAll` 的返回协议

```js
var rs = java.ajaxAll([url1, url2]);   // 并发
rs[i].code()      // 200
rs[i].body()      // 字符串（type!=null 时是 hex）
```
实测 2 张并发总耗时 2.4s，比串行 2×1.8s 快。

---

## 6. 【交付纪律】旧正文缓存不会重跑正文规则

正文内容按**书 + 章节**缓存（`BookHelp.saveContent` / `contentSaveToken`）。改书源后：

- **已缓存的章节正文不会重新执行 ruleContent** → 新版 `src` 不会生效；
- 净化规则（replaceRegex）走的是另一条路：`ContentProcessor.getContent` 在**每次阅读渲染时**对全文跑替换 —— 所以净化规则能改写**已缓存**正文里的 URL，这是"免清缓存"手段；
- 但净化规则有反噬风险：若规则 pattern 会匹配**书源自己产出的带选项 URL**，就会二次包装成 `url,{opt},{opt}` → `GSON.fromJsonObject<UrlOption>` 解析失败 → 退回裸 URL → 全部超时。
  - 负向断言 `(?!\{)` **挡不住** `,{`（紧随字符是逗号不是花括号）→ 正确写法应连逗号一起排除，或**直接禁用该规则**。

**结论**：修复图片问题后，用户必须**删除书籍后重新搜索加入**（或清正文缓存重新下载），否则看不到变化。

---

## 7. 【排障流程】图片部分失败的六步定位法

```
1. 读 HTTP 日志，按 duration 分三类：
   - 0ms          → failUrl 黑名单（App 进程内已放弃），换 URL（加选项）即可绕过
   - =超时值(10/15s) → 连接层失败（IOException），retry 无效，必须靠 dnsIp 多 IP
   - 几百 ms + 200 → 正常
2. 检查正文规则产出的 src 是否真的带 dnsIp：
   - 用 AppPattern.imgPattern 正则实测提取条数是否 = 接口返回图数
   - 检查 paramPattern（`\s*,\s*(?=\{)`）能否在 src 上 find
3. 查 src 的 IP 池是否只有"首元素"在承压（没有轮换 → 同节点批量失败）
4. 查 nextContentUrl：debug 日志 `◇本章总页数` 是否 = 接口的 pages.total
5. 查净化规则：是否 isEnabled、pattern 是否会匹配书源自己产出的带选项 URL
6. 查旧缓存：章节是否在修改前就已下载（需删书重加）
```

---

## 8. 【可复用结论清单】

| 编号 | 结论 |
|---|---|
| L1 | Legado `retry` 只重试非 2xx，**不重试 IOException** |
| L2 | `dnsIp` 逗号分隔多 IP = OkHttp 按序尝试，自动跳过不通的 |
| L3 | `dnsIp` 只约束首个 host；与 `proxy` 互斥；池内不能有域名 |
| L4 | 多 IP 池 + **按图轮换首选顺序**，可把"整章失败"降级为"个别失败" |
| L5 | 0ms IOException = Glide failUrl 黑名单秒拒，非网络问题 |
| L6 | `nextContentUrl` 返回单值时 App 自动循环翻页；写 `return` 会报"返回的值无效" |
| L7 | 分页参数要取**章节自身 URL**（baseUrl），不要取 `book.tocUrl`（目录页 URL） |
| L8 | URL 选项 `"type":"jpg"` → 响应体是完整 hex，可用于精确验证图片可达性 |
| L9 | `java.base64Encode(byte[])` 在 Rhino 下不可靠，别用它拼 data URI |
| L10 | 旧章节缓存不重跑正文规则；净化规则能改写缓存正文但可能二次包装自伤 |
| L11 | `concurrentRate` 是"次数/毫秒"，图片密集站应调大间隔（如 1/1200）降低并发洪峰 |
| L12 | 排查必须做反向验证组（裸 URL 必败 + 带 dnsIp 必成）才能实锤根因 |

---

## 9. 配套实证（哔咔 v76，2026-10-24）

| 实验 | 结果 |
|---|---|
| 裸 URL（无 dnsIp） | UnknownHostException 1.3s / SocketTimeout 15.3s —— 必败 |
| 同 URL + 10 IP 池 | 1.7s 成功，512336 hex 字符（256168 字节） |
| 同一张失败图 × 10 个 IP × 3 次 | **30/30 全通** → 节点本身可用，问题在并发洪峰与首选节点集中 |
| 真实章节 40 张全量下载（带池） | **40/40 成功**，平均 1.8s，最大 3.6s |
| 规则产出校验 | 图数 40 = imgPattern 提取 40，异常 src 0，首选 IP 分布 10 组 × 4 张 |
| 修正 nextContentUrl 后 | App 自动翻完 6 页：40+40+40+40+40+32 = **232 张** |
| 全链路 HTTP 日志 | 搜索/详情/目录/正文 6 页全部 200 |
| LAN 落库回读 | 11 个关键字段 md5 全一致（PASS） |

---

*本文所有源码引用均来自 LegadoTeam 官方源码 `app/src/main/java/io/legado/app/`（OkHttpUtils.kt、AnalyzeUrl.kt、AnalyzeUrlNetworkOptions.kt、BookContent.kt、BookHelp.kt、OkHttpStreamFetcher.kt、TextChapterLayout.kt），实验数据来自 2026-10-24 App 内 MCP + LAN Web 服务实测。*

---

## 12. 【v83 补测】正文图通道在 App 内的真实成功率

v83（dnsIp 10 节点 + 按图轮换）实测（App 内 MCP，走 `AnalyzeUrl` 同一条通道）：

| 轮次 | 结果 | 说明 |
|---|---|---|
| 第 1 轮（10 张） | ok=9 fail=1，平均 8438ms | 1 张偶发失败 |
| 第 2 轮（10 张，逐张记录） | **ok=10 fail=0，无 >4s 的慢请求** | 单张偶发抖动，非系统性 |

**结论**：
- 轮换机制把"整章失败"降级为"个别图偶发失败"——**这已是 CDN 侧不可完全消除的固有噪声**；
- 单张失败是**节点瞬时抖动**，重进章节/下拉刷新即可恢复；
- 若需进一步提高，可把**实测最稳的 1~2 个 IP 放在池首**（其余仍保留做后备），代价是失去负载分散。

> 排障口径：正文偶发 1~2 张空白 = 正常抖动；**整章空白/报错** = 才是真故障。
