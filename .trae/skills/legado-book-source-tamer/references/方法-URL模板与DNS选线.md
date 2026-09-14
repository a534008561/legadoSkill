# 方法：URL 模板 `{{}}` 求值语义与 DNS 选线
## ——动态域名/hosts/参数注入的唯一可靠通道，以及它吞字符串的那些坑

> 沉淀日期：2026-09-14　｜　来源：hanime1 v2.2~v3.9（`dnsIp` + hosts 池）、mdcmai.xyz（域名切换）、zhaoshu.la、novelServices、m.lzjxx.net、77shuku
> 关联：[方法-发布页线路轮换与登录界面测速选线](方法-发布页线路轮换与登录界面测速选线.md)、[方法-legado各版本行为差异对照](方法-legado各版本行为差异对照.md)

---

## 目录

1. [`{{}}` 的两段求值时机（最重要的一条）](#一-的两段求值时机最重要的一条)
2. [模板七坑总表](#二模板七坑总表)
3. [URL 选项对象：可选项全清单](#三url-选项对象可选项全清单)
4. [★多 JSON 对象 → NPE（一句话根因）](#四多-json-对象--npe一句话根因)
5. [`dnsIp` / `resolveIp`：只劫持本域的多 IP failover](#五-dnsip--resolveip只劫持本域的多-ip-failover)
6. [hosts 池 + 测速选线 + 变量自愈的完整闭环](#六hosts-池--测速选线--变量自愈的完整闭环)
7. [探针法：一步看到模板最终产出的 URL](#七探针法一步看到模板最终产出的-url)
8. [变量读取的双通道（规则侧 vs BookSource 侧）](#八变量读取的双通道规则侧-vs-booksource-侧)
9. [避坑清单](#九避坑清单)

---

## 一、`{{}}` 的两段求值时机（最重要的一条）

理解这个，所有模板坑都能自己推出来。

```
书源里存的字符串（含 {{expr}}）
   │
   ├─ 时机A：save/导入时不做任何求值（原样存进 DB）
   │
   └─ 时机B：AnalyzeUrl 构造时求值  ← ★每次请求都重新求值！
         │  {{java.xxx()}} / {{key}} / {{page}} / {{book.bookUrl}}
         ▼
      得到最终 URL 字符串
         │
         └─ 若尾部还有 ",{...}" → GSONStrict 解析成 URL 选项
```

**推论**：

1. **任何"存下来的 URL"都能动态自愈**——`bookUrl`、`chapterUrl`、`exploreUrl`、`tocUrl`、`searchUrl` 全都吃模板。所以域名轮换站可以把 `bookUrl` 写成相对/变量拼接形态，书架里的老书签下次打开自动跟随新线路（hlwf6/zhaoshu 实测）。
2. **`{{}}` 里没有 `this`，作用域是 AnalyzeUrl 的 bindings**：`java`/`source`/`key`/`page`/`book`/`chapter`/`baseUrl`/`result`/`cookie`/`cache`/`title`/`src`/`nextChapterUrl`（各位置可用性不同）。
3. **求值发生在 GSON 解析 URL 选项之前** → 模板产出的内容里**不能出现裸双引号**，否则选项 JSON 断裂（第六节案例）。

### hanime1 的自愈式模板（生产写法）

```json
"chapterUrl": "{{H1BUE(vid,'Q'+q)}}"
```
其中 `H1BUE` 内部产出：

```
https://hanime1.me/watch/v{vid}...{"dnsIp":"{{H1IPX(source)}}","retry":3}
```

→ 每次点章节都重新读"当前选中的 hosts/清晰度"变量，**用户在线换线路不用重进书、不用刷新目录**。

---

## 二、模板七坑总表

| # | 坑 | 症状 | 根因/对策 |
|---|---|---|---|
| 1 | **域名段为空 → 整段被吞** | `{{a}}{{b}}` 只剩前半，或整条空 | 一条 URL 只用**一个** `{{}}` 产出完整字符串；空值分支在 JS 内兜底 |
| 2 | **单模板产出被小写化** | `{{'A'+x}}` 变 `a...` | `AnalyzeUrl` 模板层有 `toLowerCase` 行为（mdcmai 实测）→ 大小写敏感的 path/token **不要经模板**，改在 `@js:` 里整体拼 |
| 3 | **`{{}}` 里 `$` 不是 JSON item** | `$.id` 报 "`$` 未定义" | 模板里只有 bindings；要在 `ruleSearch.bookUrl` 用 `$.id` 必须写成 `@js:result=(typeof result==='string')?JSON.parse(result):result` |
| 4 | **`searchUrl` 用整条 `@js:`** | 静默失败："获取成功"日志消失，URL 被解析成 `https://api/...` | `searchUrl` 用 `{{}}` 模板或 `<js>…</js>`，产完整绝对 URL |
| 5 | **模板里出现裸双引号** | URL 选项解析失败 → **静默退化成 GET** | 见第四节；引号一律 `String.fromCharCode(34)` 在运行期生成 |
| 6 | **多个 JSON 对象** | `NPE: getClass() on null` | `url,{a},{b}` 非法，必须合并成单个 `url,{"a":1,"b":2}` |
| 7 | **`{{}}` 内写真实换行** | 规则解析断裂 | 规则字符串里**绝不能有真实换行**；要换行用 `String.fromCharCode(10)` 占位再 split/join |

补充两条常被混进来的：

- `tag.meta[property=...]@content` **恒空**（`tag.` 前缀走 `getElementsByTag(整串)`），与模板无关，但要记得 og 标签写 `meta[property=...]@content`；
- `^(https?:[^/]+)` 取 origin **恒 null**（`https:` 后紧跟 `//`），改 `url.split('/')` 取 `ps[0..2]`。

---

## 三、URL 选项对象：可选项全清单

形态：`URL,{"key":value,...}`（逗号 + 单个 JSON 对象）。

| 键 | 类型 | 作用 | 注意 |
|---|---|---|---|
| `method` | `"POST"` | 请求方法 | 需配 `body` |
| `body` | string / 对象 | POST 体 | 对象形式 `{"keyword":"{{key}}","page":"{{page}}"}`（Legado 自动 JSON 化并设 contentType） |
| `charset` | `"gbk"` | 编码 | GBK 站服务端常**不 urldecode POST body**，`s={{key}}` 原文 + charset 才对 |
| `headers` | 对象 | 单次请求头覆盖 | 与书源 `header` 合并，单次优先 |
| `retry` | `3` | ★失败自动重试次数 | `AnalyzeUrl.getRetry` **原生支持**（xuken 靠它扛间歇 RST）。**POST 会撞 `oneShot`**（RequestBody 不可 rewind）→ 只对 GET 有效 |
| `timeout` | `8000` | 超时 ms | 测速必配（线路轮换篇） |
| `dnsIp` / `resolveIp` | `"ip1,ip2"` | ★本地劫持本域解析 | 见第五节；老版本无此项 |
| `proxy` | `"http://127.0.0.1:7890"` | 代理 | **与 `dnsIp` 互斥** |
| `urlOption` 组合 | — | — | 全部只能一个对象 |

---

## 四、★多 JSON 对象 → NPE（一句话根因）

```
❌ https://api.example.com/x,{"method":"POST"},{"body":"a=1"}
   → GSONStrict 对整段 ",{...},{...}" 解析失败 → urlOption = null
   → 后续 option.getClass() → NullPointerException（报错信息完全不提 JSON）
✅ https://api.example.com/x,{"method":"POST","body":"a=1"}
```

**同类**：`body` 内部要嵌 JSON（如 TTS 的 `{"text":"...","voice":"..."}`）时，Legado 先做 `{{}}` 替换、再 GSON 解析整串 → **正文里只要一个英文双引号就全断**。

标准解法（HttpTTS 那次的核心结论，通用）：**运行期用 `JSON.stringify` 生成引号**：

```javascript
<js>
var Q = String.fromCharCode(34);            // 源文本零双引号
var o = {method:'POST',
         body:JSON.stringify({text:String(speakText), voice:vc}),
         headers:{'Content-Type':'application/json'}};
'https://host/legado/tts,' + Q + '' ...     // 或直接：'{' + Q + 'method' + Q + ':...' 
</js>
```

以及拼接顺序陷阱：`{` 必须在引号**之前**——`'{' + Q + 'retry' + Q + ':3}'`（ggd8 实测）。

---

## 五、`dnsIp` / `resolveIp`：只劫持本域的多 IP failover

源码依据：`AnalyzeUrlNetworkOptions.kt`（LT 版）。

| 语义 | 说明 |
|---|---|
| 作用范围 | `buildScopedDns` **只劫持 URL 本域名**的解析，其他域走系统 DNS |
| 多 IP | 逗号分隔，OkHttp 自动 **failover**（一个连不上换下一个） |
| 请求栈 | 用 `dnsIp` 会**去 Cronet 走 OkHttp**，保留 SNI 与证书校验 |
| 互斥 | 与 `proxy` **互斥**，同时给会出问题 |
| 空串 | 空串 = 正常解析（可当"关闭选线"的开关值） |
| 位置 | 是 **URL 选项**，写在 `header` 里**无效**（探针实锤） |

### 典型用法：被 DNS 污染 + SNI 重置的站

hanime1：主域被 GFW DNS 污染返 RST，`vdownload.hembed.com` 被 SNI 封锁。

```json
"bookUrlPattern": "https?://hanime1[.]me/watch/v[0-9]+",
"searchUrl": "https://hanime1.me/search?q={{key}}{{H1SFX(source)}}"
```

```javascript
// H1SFX 产出：,{"dnsIp":"{{H1IPX(source)}}","retry":3}
// H1IPX(source) 读 source 变量 h1ip：'104.25.254.167,172.64.229.154,...'（按实测延迟排序）
```

配套的两条：

1. **CDN 域名被 SNI 封锁 → 换 CDN 侧原生主机名**，而不是硬扛 DNS：
   `vdownload.hembed.com` → CNAME 链查到 `1497203185.rsc.cdn77.org`（CDN77 客户原生主机），签名只绑路径 ⇒ 直接可用。**通用方法论：SNI 封锁 → 查 CNAME → 用 CDN 主机名。**
2. `debug_source` 的 key **必须自带 `{"dnsIp":…}`**，否则走 Cronet 用被污染 DNS → 31 秒 `ERR_CONNECTION_TIMED_OUT`（浪费一整轮调试）。

---

## 六、hosts 池 + 测速选线 + 变量自愈的完整闭环

```
① IP/线路池来源
   站点自带接口 / 发布页 / 公开 CF IP 池 / 记忆里的历史可用池
② 判活（别只看状态码）
   HEAD https://host/ 拿到【任意响应码】(含 400/403) = TCP+TLS 通
   异常/空 = 被墙                        ← 无需 token 即可判连通性
   ★ 但方法可能被拒：cdn77 GET 200 / HEAD 恒 403 ⇒ HEAD 403 ≠ 被墙，需 GET 复核
③ 测速
   java.head(url, headerJson, {"timeout":8000}) + Date.now() 计时
   ★ 单位坑：jsLib/桥里 java.ajax(url, 25) 的 callTimeout 是【毫秒】，
     传 25 = 63ms 假超时"InterruptedIOException timeout"，必须传 25000
④ 排序落库
   source.put('h1ip', 'ip1,ip2,...')   ← 逗号串，第一个即首选
⑤ 消费
   URL 选项 {"dnsIp":"{{H1IPX(source)}}"} 每次请求二次求值 → 换线路即时生效
⑥ 手动自救
   登录 UI 按钮：只看不改(测速) / 改默认 / 恢复自动 / 显示当前状态
```

**变量存 `BaseSource.put/get`（`CacheManager` 键 `v_{sourceKey}_{key}`）**：进程内存级，App 重启即失效 → 首章会重探（3~5s），这是可接受代价；要持久就存进 `variable` 字段（但见第八节的双通道）。

---

## 七、探针法：一步看到模板最终产出的 URL

怀疑"模板被吞/大小写被改/选项没生效"时，**不要用眼睛猜**，2 分钟出结果：

```
① 造一个微书源：bookSourceUrl = http://probe.invalid
   （.invalid 是保留 TLD，一定解析失败）
② 把要验的 URL 原样填进 searchUrl
③ App 内跑一次搜索
④ MCP get_http_logs → 看那条请求的【最终请求 URL】
```

DNS 报错本身没有信息量，**error 里回显的 URL 就是模板求值 + 选项剥离之后的真实产物**。一次定位：

- mdcmai 的 `{{}}` 域名段被吞 → 就是靠这个看到 `https://api/...`；
- `@js:` 让 URL 退化相对路径 → 同样一步看穿。

成本：一个废域名 + 一次搜索。**这是排查 URL 模板问题的首选工具。**

---

## 八、变量读取的双通道（规则侧 vs BookSource 侧）

| 上下文 | `source` 是谁 | 可用 API |
|---|---|---|
| 规则 `@js:` / `<js>` | `JsExtensions` | `getVariable(k)` / `setVariable(k,v)` ✅ |
| `jsLib` | **`source` 未定义**（LT） | 不能用 |
| `loginUrl` / `loginUi.action` | `BaseSource` 系 | `source.get(k)` / `source.put(k,v)` ✅（持久化到 `variable` 字段，`@JsonIgnore` 不入 DB 的另说） |
| `eval_js`（绑定书源） | `BaseSource` | **没有** `getVariable/setVariable/putVariable`；只有 `put/get` |

→ **任何要读"登录 UI 写的变量"的规则，必须双通道**：

```javascript
function rd(k, dft) {
  var v = null;
  try { v = source.getVariable(k); } catch (e) {
    try { v = source.get(k); } catch (e2) { v = null; }
  }
  if (v === null || v === undefined) { v = dft; }
  v = String(v);
  if (v === 'null' || v === 'undefined' || v === '') { v = dft; }
  return v;
}
```

**为什么最后那三行 `String()` 归一化是必需的**（mdcmai 血泪，全 App 级）：
Rhino 里 **Java `null` 是 truthy**（`JsNull` 包装对象）。`source.get('未设置的键')` → `null` → `if (dv)` 为 **true**、`dv || 'default'` **不走兜底**、字符串拼接变空串。
必须 `String(dv)` 之后再判 `'null'/'undefined'/''` 三态。

---

## 九、避坑清单

| # | 坑 | 对策 |
|---|---|---|
| 1 | 一条 URL 拆成多个 `{{}}` | 只用一个，JS 内产出完整字符串 |
| 2 | 大小写敏感内容走模板 | 改 `@js:` 整体拼 |
| 3 | 模板里裸双引号 | `fromCharCode(34)` 运行期生成 |
| 4 | `url,{a},{b}` 双 JSON | 合并单对象（否则 NPE） |
| 5 | `searchUrl` 整条 `@js:` | 用 `{{}}` / `<js>` |
| 6 | POST + `retry` | 去掉 retry 或改 GET（`oneShot`） |
| 7 | `dnsIp` 写进 `header` | 它是 URL 选项 |
| 8 | `dnsIp` + `proxy` 同用 | 二选一 |
| 9 | 只看 HEAD 状态码判连通 | 任意码=通，但 403 可能是"方法被拒"，GET 复核 |
| 10 | `java.ajax(url, 25)` | 单位是毫秒，传 25000 |
| 11 | 信 `dv \|\| 默认值` | Rhino JsNull truthy，`String()` 归一化 |
| 12 | 规则字符串含真实换行 | `fromCharCode(10)` 占位 |
| 13 | `debug_source` 不带 `{"dnsIp"}` | 31s 超时假象 |
| 14 | 变量在 UI 写、规则读，只走一个 API | 双通道 `rd()` |
| 15 | App 重启后 `put/get` 变量丢失 | 首章重探可接受；要长期态就写回 `variable` |

---

## 附：模板/选项最小自检脚本

```javascript
// 在 eval_js 里直接问"这条规则最终会变成什么 URL"
function preview(tpl) {
  // 模拟：AnalyzeUrl 先 {{}} 替换，再剥 ",{json}"
  var m = tpl.match(/,\{[\s\S]*\}$/);
  var opt = m ? m[0].substring(1) : null;
  var ok = true, parsed = null;
  if (opt) { try { parsed = JSON.parse(opt); } catch (e) { ok = false; } }
  return JSON.stringify({url: m ? tpl.substring(0, m.index) : tpl,
                         optionOk: ok, option: parsed});
}
java.log(preview('https://x/y,{"dnsIp":"1.2.3.4","retry":3}'));
// → optionOk:false 就说明引号/逗号被模板阶段污染了
```
