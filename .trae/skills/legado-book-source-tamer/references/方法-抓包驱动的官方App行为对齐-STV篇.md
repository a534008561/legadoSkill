# 方法：抓包驱动的「官方 App 行为对齐」— STV 篇

> 2026-10-07 · 蓝本：STV[api_1]（sangtacviet.vip）v11.6.1 → v11.7
> 数据源：ProxyPin 实时抓包（1000 条缓冲，含官方 App 完整会话）
> 验证：App 内 eval_js 真机对照实验 + debug_source 全链路 + check_source 1/1

## 0. 一句话总结

**当站点有官方 App 时，抓包它比读它的网页 JS 更快更准**——官方 App 的请求头、参数、域名池、重试策略都是「经过服务端验证可用」的黄金标准；
把书源的行为对齐到官方，能一次性修掉性能与稳定性问题。

---

## 1. 抓包工具链（ProxyPin MCP）

| 工具 | 用途 | 关键点 |
|---|---|---|
| `get_proxy_status` | 确认录制中 | `recording:true, sslInterception:true` |
| `list_flows(host=,keyword=,limit=)` | 按主机/关键词过滤 | 大缓冲用 `keyword` 精确定位 |
| `get_flow_detail(id)` | 完整请求/响应头 | 看 `Cookie`/`Referer`/自定义头 |
| `get_flow_body(id,side,limit,offset)` | 响应体分页 | 大响应必须 offset 翻页 |
| `search_flows(keyword)` | 全文搜请求/响应体 | 找特定参数出现处 |

★ **实战技巧**：
- 先用 `list_flows(host="目标域", limit=100)` 拉全量，看**接口清单**
- 官方 App 的接口调用顺序本身就是「正确流程」的证据
- **同一接口的不同调用要对比**（如 grantcontext 带 `mac_tt` 而 bookinfo 不带）

---

## 2. 从抓包到源码：官方 App 的 JS 是公开的

STV 的官方 App 是 **Capacitor（WebView 壳）+ 服务端 JS**，所以它的 JS 可以直接下载：

```bash
# 1) 抓包看到页面加载的 script 标签
GET /app.v2.php  → 内含 ui.scriptmanager.load("/asset/app.v2.js?...")

# 2) 直接下载
GET /asset/app.v2.js            # 261KB 主逻辑
GET /asset/app.v2.read.js       # 145KB 阅读器（含正文请求）
GET /stv.host.js                # 9KB 域名映射表
GET /asset/app.v2.config.js     # 配置默认值
```

**`app.v2.read.js` 里直接给出了正文请求的完整构造**：
```js
headers = {
  Cookie: document.cookie + "; mac_tt=true;",
  "User-Agent": navigator.userAgent,
  "x-stv-transport": "app",
  "x-requested-with": "com.sangtacviet.mobilereader",
}
url = `/?sajax=readchapter&h=${h}&bookid=${i}&c=${c}&key=${this.chapterkey}`
if(rl){ url += "&rescan=true"; }        // ← 重读时加
```

**`app.v2.js` 里给出了域名管理**：
```js
defaultDomains: ["https://sangtacviet.com", "https://dns1.stv-appdomain-00000001.org", "https://sangtacviet.app"],
verifyDomain: GET {domain}/warp.php  → status 200-299 = alive
bestDomain(): 按 ping 选最快 alive
```

★ **教训**：书源池里塞了 13 个域名（其中 5 个长期 DNS 失败），而官方只用 3 个 + 一个探活接口。
**不要凭感觉堆域名，去看官方的域名管理逻辑**。

---

## 3. 真机对照实验（沙盒 ≠ 真机）

沙盒（数据中心 IP）与手机（家宽 IP）在 STV 上被**区别对待**（限流策略不同），
所以关键结论必须用 **App 内 eval_js** 验证。

### 3.1 对照实验模板

```js
// 在 App 内 eval_js 里跑
var UA='...';
function req(url, hd){
  try {
    var r = java.ajax(url + ',' + JSON.stringify({headers: hd, timeout: 20000}));
    return String(r);
  } catch(e) { return 'ERR ' + String(e).substring(0,60); }
}
// A/B 对照：只改一个变量
out.push('A 无Referer: ' + req(tocUrl, {..., 无Referer}).length);
out.push('B 带Referer: ' + req(tocUrl, {..., Referer:RF}).length);
```

### 3.2 STV 实测结果

| 实验 | 结果 | 结论 |
|---|---|---|
| 目录接口 `web+Referer` | 23842 字节 ✓ | — |
| 目录接口 `app+Referer` | 23842 字节 ✓ | transport 不影响 |
| 目录接口 `无Referer` | **0 字节** ✗ | **Referer 是硬要求** |
| `warp.php` sangtacviet.com | `yes` 175ms | — |
| `warp.php` sangtacviet.vip | `no`（采样1）/ `yes`（采样2） | **状态波动，不能硬编码** |
| `warp.php` stv302.com | DNS fail | 移除 |
| grantcontext 跨域（.com/.app/.pro） | 全部 200 | 域名可互换 |

★ **0 字节静默失败**是这类站点最常见的坑：**不报错、不返回、规则看起来正常**。
定位方法就是 A/B 对照（只改一个变量）。

---

## 4. 官方 App 的三个「隐藏参数」

抓包 + 源码交叉确认的官方参数，书源往往漏掉：

| 参数 | 位置 | 作用 | 实测 |
|---|---|---|---|
| `mac_tt=true` | Cookie | 官方所有正文/grant 请求都带 | 对齐（当前不影响，但是官方行为） |
| `rescan=true` | URL query | 重读章节时让服务端重扫 | 官方 `if(rl) url += "&rescan=true"` |
| `download=true&key=stvmobilereader` | URL query | 官方下载通道 | 未登录返回 `{"code":2,...}`，登录后可用 |

★ **发现方法**：把官方 JS 里所有 `url +=` 都 grep 一遍：
```bash
grep -o 'url += "[^"]*"' app.v2.read.js
```

---

## 5. P0 级 BUG 的发现（这次的最大收获）

### 5.1 `m2` 未定义 → 正文规则崩溃

**症状**：`debug_source --URL` 直接抛
```
ReferenceError: "m2" 未定义 (<script-1070>#797)
```

**定位**：`debug_source` 的堆栈直接给了行号 `#797`，对照书源规则第 797 行：
```js
if (IDX < 1) {
  if (IDX < 1) IDX = ordFrom(TIT);
  if (m2) IDX = num(m2[1]);     // ← m2 从未定义（残留代码）
}
```

**触发条件**：`IDX < 1`（章节 URL 无 `i=` 参数）
- 书架存量书（老版章节 URL）
- `debug_source --URL`
- 手动打开详情页

**为什么长期没被发现**：正常阅读流程的章节 URL **都带 `i=`**（目录规则生成的），
所以只有「书架老书 / 调试」才会踩到 —— 而这恰恰是用户报障最常见的场景。

★ **教训**：规则里的「边界分支」必须单独测试（用老格式 URL、空参数、异常值）。
`debug_source --URL` 是个好工具，但要用**真实章节 URL 的多种形态**。

### 5.2 `btoa` 未定义 → eval 必然失败，每次走慢速 WebView

**症状**：铸密钥时，`eval(混淆JS)` 抛 `ReferenceError: btoa 未定义`
→ 落到 `java.webView(...)` 兜底（319~457ms + WebView 创建开销）

**根因**：混淆 JS 用了浏览器 `btoa()`，Rhino 环境没有（实测 `typeof btoa === 'undefined'`）

**修复尝试**：给 STVSKEL 加 btoa/atob 垫片
```js
window.btoa = function(s){
  return String(Packages.android.util.Base64.encodeToString(
    new Packages.java.lang.String(String(s)).getBytes('ISO-8859-1'), 2));
};
```
垫片本身**完全正确**（实测 `btoa('hi')='aGk='`、`btoa('héllo')='aOlsbG8='`、256 字节往返 OK，
与浏览器 latin1 语义一致），但 **Rhino 里混淆 JS 仍有执行差异**：
- Node（V8）：同一份 grant JS 能出 key（187~192 字符）
- Rhino：无报错但 key 未产出

**务实结论**：
- 垫片作为「快速路径尝试」，**失败时自动回落 WebView**（已验证 319ms 正常）
- **零回归风险**：WebView 路径本来就工作，垫片只是可能省掉它
- ★ **通用原则**：优化不能引入回归。当「快速路径」的收益不确定时，
  用「try 快路径 → catch 回落原路径」的结构，而不是替换。

---

## 6. `java.ajax` 的返回值陷阱（本 App 特有）

**实测**：`java.ajax(url + ',{json选项}')` 返回的是 **Java String 对象**（不是 StrResponse）：
```
props: getClass, toCharArray, length, substring, indexOf, ... （全是 String 方法）
body: undefined
headers: undefined
```

**后果**：
- 书源的 `bodyof(r)` 走 `String(r)` 分支 ✓（书源已兼容）
- **读不到响应头** → `Set-Cookie` 里的 `readcontextid` 拿不到
- 只能从 CookieJar 读（`cookie.getCookie()`）—— 但**实测 CookieJar 不随 grantcontext 更新**！

**实测记录**：
```
BEFORE jar: readcontextid=f2e59f5c...
glen=259943
AFTER jar:  readcontextid=f2e59f5c...   ← 未变！
```

★ 这与官方行为不同（官方每次 grantcontext 都拿新 readcontextid）。
可能是 10002 限流的一个诱因，但**本次未改动**（因为 key 与 rcid 成对，
服务端可能按 key 校验而不是 rcid）。**记录待观察**。

---

## 7. 交付清单（本次）

| 项 | 值 |
|---|---|
| 成品 | `/workspace/stv_opt/stv_v117.json`（128048 字节） |
| 直链 | https://n.uguu.se/nOmfRuMH.json |
| 构建脚本 | `build_v117.py`（10 项锚点替换，每项都有断言） |
| 语法校验 | 9 个 JS 字段 node --check 全过 |
| 落库验证 | 深链导入 + 特征回读（STVB64 ✓ / mac_tt ✓ / rescan ✓ / m2 已删 ✓） |
| 全链路 | 搜索 17 条 → 详情（13 来源）→ 目录 1419 章 → 正文 ✓ |
| check_source | **通过 1/1** |

---

## 8. 可复用的检查清单

**抓包阶段**：
- [ ] `list_flows(host=)` 拉全量，列接口清单
- [ ] 逐接口对比请求头（Cookie/Referer/自定义头）
- [ ] 找官方 JS（`/asset/*.js`、`/stv.*.js`），grep `url +=`、`headers =`、`defaultDomains`
- [ ] 记录官方域名池 + 探活接口

**对照实验阶段**：
- [ ] 用 App 内 `eval_js`（沙盒 ≠ 真机）
- [ ] A/B 对照只改一个变量
- [ ] 特别注意 **0 字节静默失败**（无报错 = 最危险）

**修复阶段**：
- [ ] 边界分支单独测试（老格式 URL、空参数）
- [ ] 优化用「try 快路径 → catch 回落」结构，不替换原路径
- [ ] 每项改动配断言（锚点命中次数）

**验证阶段**：
- [ ] 9 个 JS 字段 node --check
- [ ] 深链导入 + 特征回读（不能只看「已保存」）
- [ ] debug_source 四模式（搜索/详情/目录/正文）
- [ ] check_source

---

## 9. 通用结论（跨站适用）

1. **有官方 App 就抓包它** —— 官方请求头/参数是服务端验证过的黄金标准
2. **官方 JS 是公开的** —— Capacitor/WebView 壳的 App，JS 直接 GET 就有
3. **域名管理去看官方的** —— 不要凭感觉堆，官方可能有探活接口（`/warp.php`）
4. **0 字节 = 静默失败** —— A/B 对照是唯一可靠定位法
5. **沙盒 ≠ 真机** —— 关键结论必须 App 内验证
6. **优化不能引入回归** —— try 快路径 → catch 回落原路径
7. **边界分支必须单独测** —— 正常流程走的路径覆盖不到它们
8. **`debug_source` 堆栈给行号** —— 直接对照规则源码定位


---

## 10. 【v11.8 追加】官方域名的「探活可用 ≠ 业务可用」陷阱

### 10.1 事故经过

v11.7 从官方 `app.v2.js` 的 `defaultDomains` 里学到 `dns1.stv-appdomain-00000001.org`，
把它加进了书源域名池。**结果：这本书的正文全部读不出来**（官方 App 正常）。

**用户报障**：《我还没张嘴，女神就开始服务了》阅读打不开正文。

**真机复现**：
```
debug_source --https://sangtacviet.vip/?sajax=readchapter&h=fanqie&bookid=7628272929679084606&c=...
→ [STV 本章读不出来] 原因：Không thể xác thực kết nối.（无法验证连接）
```

### 10.2 对照实验（决定性）

同一本书、同一章、同一套请求头，**只改域名**：

| 实验 | 铸密钥域 | 读正文域 | 结果 |
|---|---|---|---|
| 1 | dns1.stv-appdomain-00000001.org | dns1 | ❌ `{"code":"1","err":"Không thể xác thực kết nối."}`（48 字节） |
| 2 | sangtacviet.com | .com | ✅ `{"code":"0", ...完整中文正文}`（3281 字节） |

**逐域复测**（每域间隔 5s 避限流）：

| 域名 | warp.php 探活 | readchapter | 结论 |
|---|---|---|---|
| sangtacviet.com | yes | ✅ 3281 字节 | 可用 |
| sangtacviet.app | yes | ✅ 3281 字节 | 可用 |
| sangtacviet.pro | yes | ✅ 3281 字节 | 可用 |
| sangtacviet.xyz | yes | ✅ 3281 字节 | 可用 |
| **dns1.stv-appdomain-00000001.org** | **yes** | ❌ **48 字节「无法验证连接」** | **仅官方 App 可用** |

★ **`dns1` 是官方 App 专用中转域**（服务端按某种客户端标记放行），
`warp.php` 探活回 `yes`，但 `readchapter` **一律拒绝**。

### 10.3 连带故障：死源误标

dns1 的 readchapter 失败被规则当成「来源死亡」→ 写入 `stvd_` 死源标记
→ 之后每章都先跳过/惩罚这个来源，**故障被放大**。

### 10.4 修复（v11.8）

1. **域名池移除 dns1**
2. **正文规则的 `DOM()` 里过滤 dns1**：即使 `stvdom` 变量被残留值污染，也会自动回退到 `sangtacviet.com`
   ```js
   if (d.indexOf('dns1.') >= 0) d = DOM0;   // DOM0 = 'https://sangtacviet.com'
   ```
3. **「无法验证连接」不计入死源**（域名级拒绝 ≠ 来源级死亡）
   ```js
   if (deff && why.indexOf('VIP') < 0 && why.indexOf('无法验证') < 0) deadMark(cd.h, cd.b);
   ```
4. **错误翻译表新增**：`Không thể xác thực kết nối` → 「线路被拒（该域名只服务官方 App，请换回 sangtacviet.com）」
5. **线路切换探活提示**：选中 dns1 时直接警示

### 10.5 通用教训（★★★）

1. **「探活可用」≠「业务接口可用」**
   - 探活接口（`/warp.php`）只证明「TCP+TLS+HTTP 通」
   - 业务接口（`readchapter`）可能有额外的客户端校验（签名/标记/域名白名单）
   - **引入新域名前，必须用真实业务接口逐个验证**，不能只看探活

2. **官方用的域名 ≠ 书源能用的域名**
   - 官方 App 可能有书源无法模拟的客户端标识
   - 官方域名池里可能有「专用中转域」（如 dns1 这类随机域名）
   - 看到 `dns1.xxx-00000001.org` 这种形态要警惕：它往往是 CDN/中转专用

3. **域名级拒绝不要标成来源死亡**
   - `Không thể xác thực kết nối.` / `无法验证连接` 这类是**域名级**拒绝
   - 标记死源会污染缓存，导致故障放大且难以自愈
   - **错误分类要精确**：域名问题 / 来源问题 / 章节问题 / 限流问题

4. **修复要带「变量污染防护」**
   - 用户设备上的 `source.get('stvdom')` 可能残留坏值
   - 光改域名池不够，规则层要能**自动纠偏**（如 `if (d.indexOf('dns1.')>=0) d=DOM0;`）

### 10.6 验证记录（v11.8）

| 项 | 结果 |
|---|---|
| 用户报障书正文 | ✅ 完整中文正文 |
| 目录 | ✅ 311 章 |
| 回归（诡秘之主） | ✅ 搜索 17 条 → 详情 13 来源 → 目录 1419 章 → 正文 |
| check_source | ✅ 通过 1/1 |
| 9 个 JS 字段 node --check | ✅ 全过 |

---

## 11. 【v11.10 追加】三个「用户报障」的抓包定位与修复

本轮报障三条（同一本书《我能复制天赋》shu05 来源）：
1. 54 章往后章节名与内容对不上（对照官方 App 越南语原目录可看出错位）
2. 有的来源第一次打开必定失败，刷新一下才有正文
3. 54 章正文格式丢失（整章糊成几坨）

### 11.1 章节名错位：站点编号「跳号 + 无编号条目」吃掉了序号

**站点原始数据（shu05/49013，54 章附近）**：

| 位置 | 站点原始数据 |
|---|---|
| 53 | `Thứ 53 chương Buông xuống Tôn gia 【 Canh [4] 】` |
| 54 | `Thứ 54 chương Tông sư xuất hiện!【 Canh [5] 】` |
| 55 | `Lên khung cảm nghĩ`（上架感言，**无编号**） |
| 56 | `Thứ 55 chương Tông sư vẫn lạc` |
| 57 | `Tấn thăng đại võ giả`（**无编号**） |
| 58 | `Thứ 57 chương Rốt cuộc tìm được` |

旧逻辑：`if (kk > 0 && kk > prevK && usedN[kk] == null)` —— 要求站点号「必须递增且未被用过」才算数；
遇到无编号条目就走 else 分支「顺手分配一个序号」。结果：55 章起每一章的显示号都比站点号大 1。

**为什么这是设计错误**：站点号是官方 App 的显示基准，跳号/重复是站点自身数据（实测 shu05 全书 1124 章里
有 9 处重复号、11 处逆序、2 处无编号）。书源要做的是「与官方一致」，不是「自行修正」。

**修复**：
```js
if (kk > 0) {
  nm = '第 ' + String(kk) + ' 章';   // 站点号一律原样采用
  prevK = kk; usedN[kk] = 1;
} else {
  nm = '· ' + nm;                     // 无编号条目加标记，永不吃章节号
}
```

**验证（真机跑规则，54 章附近输出）**：
```
52 | 第 54 章
53 | · Lên khung cảm nghĩ
54 | 第 55 章
55 | · Tấn thăng đại võ giả
56 | 第 57 章
57 | 第 58 章
```
与站点目录逐条对齐。

**通用教训**：站点给的编号不要「修正」。任何「跳过重复/要求递增」的清洗逻辑，在数据有跳号时
都会产生系统性偏移，且偏移会累积到全书末尾。

### 11.2 第一次打开失败：无效请求统一回 10002 + 10 秒缓存窗口

**抓包证据链（ProxyPin，516 条流）**：

1. 站点对**任何无效请求**统一回 `{"code":"10002","err":"Khởi động lại ứng dụng..."}`：
   - 无 key 请求 → 10002
   - 错 key 请求 → 10002
   - 错章节号请求 → 10002
   - 三种情况响应都是 63 字节
2. Legado 打开章节时会**先按章节 URL 原样请求一次**（不带 key）→ 服务端回 10002
3. 该响应带 `Cache-Control: public` + `Expires` 约 10 秒，落在 ARR（Azure Request Router）缓存层
4. 规则紧接着带 key 请求时，可能拿到的还是刚才那份 10002（同 URL 10 秒窗口内）
5. 旧版只在 10002 时重试；遇到 **0 字节 / 非 JSON 直接放弃** → 表现为「第一次失败，刷新就好」

抓包中还能看到同一章节 URL 连续两次 `status 0`（socket 断开）后第三次成功的记录 ——
这类瞬时失败同样不会触发旧版的重试。

**修复**：
```js
// 重试条件放宽
if (w0.indexOf('触发站点限流') !== 0 && w0.indexOf('响应 0 字节') !== 0 && w0.indexOf('响应非 JSON') !== 0) break;
// 重试时带时间戳破缓存参数（已有）
var u = base + '?...&key=' + kk + (String(bust).length > 0 ? ('&_r=' + String(bust)) : '') + ...;
```
外加 `getallhost` 来源列表 6 小时缓存（键含书名+作者，目录与正文共用），少发一次请求就少一次撞限流。

**验证（真机）**：
- 冷启动（清空全部缓存）：第一次打开即成功（3898ms 含铸密钥）
- 冷启动 + 外层污染：第一次打开成功（1505ms）
- 连续 5 章：全部一次成功（1.2~1.5s/章）
- **限流状态下**：底层 readOne 直接返回 10002，但完整规则通过「重铸密钥 + 退避」自愈成功（1517ms）

**通用教训**：
- 「错误响应带短 Expires」时，重试必须换 URL（加时间戳参数），否则重试拿回同一份错误
- 重试条件不要只认「特定错误码」——网络层的 0 字节/非 JSON 同样需要重试
- 站点把「无效请求」统一报成一个码时，该码既可能是限流也可能是参数错，重试 + 重铸是通用解法

### 11.3 格式丢失：分段打分器把「站点结构」和「猜测候选」放在同一个池子里竞争

**站点正文的两种排版**：
- `<p>` 块（番茄系，如 fanqie 的 `<p idx="N">`）
- `<br />` 分隔（shu05 系，实测 54 章有 100 个 `<br>`）

**旧逻辑的致命点**：把 `<br>` 切法丢进「按字数打分」的猜测池，与「每 300 字合并」等候选比分数：

| 候选 | 段数 | 旧分数 | 说明 |
|---|---|---|---|
| segBR（正确） | 100 | **1** | 33 段是「然而。」「噗噗！！」这类短句，每段扣 3 分 |
| segByLen300（猜测） | 7 | **7** | 段数少、无短段 → 胜出 |

结果：整章变成 7 坨，段落全丢。

**修复**：
```js
// 站点给了结构就直接采用，不参与打分
var LB = segBR(html);
if (LB.length >= 3) return LB;
// 短句惩罚 3 → 1（对话体小说本就多短句）
return n - tiny - (avg > 600 ? 2 : 0);
```

**验证（真机 debug）**：54 章输出为 100 段逐句 `<br/>` 分隔，不再是 7 坨。

**通用教训**：
- 「站点已给结构」与「需要猜测」是两个层级，不能放进同一个评分池
- 长度惩罚项在设计上会系统性偏袒「段数少」的候选，对对话体小说是灾难
- 只有当站点完全没给结构（纯文本）时才应该启动猜测

### 11.4 补充：错误翻译要覆盖「新出现的错误文本」

真机验证时又发现两句越南语原文直接漏给读者：
- `Có lỗi xảy ra, truyện không tồn tại trong hệ thống.`（aikanshu 目录 code=2 的来源读章节时回这句）
- `Khởi động lại ứng dụng để tự cập nhật.`（10002，经非 readOne 路径冒出时会漏译）

**教训**：ERRCN 这类翻译函数要定期用真实错误文本回测；每加一个来源/接口都可能带出新错误文本。

### 11.5 本轮验证清单

- [x] node --check 9/9（含两个修改的大字段）
- [x] 离线仿真：编号对照站点目录逐条对齐；段落 8 段（截断样本）
- [x] 字段级 diff：仅 `ruleToc.chapterList` / `ruleContent.content` / `bookSourceComment` / `lastUpdateTime` 变更
- [x] 真机 debug：目录 1124 章 / 正文格式完整 / 发现页 48 本
- [x] 冷启动 + 污染 + 限流三场景：全部自愈成功
- [x] 自动换源：死源（aikanshu）→ 自动切到 duanqingsi 读到正文
- [x] check_source 通过 1/1

## 12. 【v11.11 追加】分隔符型目录数据的解析陷阱 —— faloo 来源 🔑/🔒 标记丢失

### 12.1 报障

> 《神豪从高考后开始》的 faloo 来源，阅读里部分目录（unvip 标识 🔑 或 vip 锁 🔒）缺失。
> —— 澄清：**不是章节缺失，是标记缺失**（外加标题被截断）

### 12.2 站点数据格式（抓包实证）

```
记录分隔 = -//-      字段分隔 = -/-
每条记录 = [序号, 章节ID, 标题, 状态?]
状态 = unvip(已解锁🔑) / vip(未解锁🔒) / 缺省(免费)
```

响应顶层还有 `unvip: 5460` 这个**服务端计数**（免费的真值，见 12.5）。

### 12.3 根因：平铺扫描遇到「标题含分隔符」就散架

书源的 `pseg()` 是 v9.x 时代遗留的**平铺扫描**实现：

```js
// ✘ 旧版：把整份数据按 '/' 切开，靠「前后邻槽是不是数字」猜字段
var seg = String(sv).split('/');
// ... 扫出「名字槽」，再看前后数字槽猜 ID、看后 3 槽猜状态
```

**只有当标题不含 `/` 时才碰巧正确。** faloo/770959 实测 5551 章里 **4384 章标题含 `/`**：

```
h073 vòng bằng hữu quan tuyên?2/30
h826/827 tân thủ âm dương sư![1+2/10]
h834/835 nhân mạch vòng  mở rộng![9+10/10]
```

被 `/` 切碎后（插桩实测 `gi=371` 处）：
```
[92] c=75 k=0 gi=371 q1="75" q2="1" next3=["30","unvip",""] n="h073 vòng bằng hữu quan tuyên?2"
                                        ↑ 状态槽跑到 "/30" 之后，后 3 槽检测不到 unvip
```

| 影响 | 量化 |
|---|---|
| 🔑 标记丢失 | 应 5460 → 实际只显示 **1081**（丢 4379） |
| 标题截断 | 4384 个（`...?2/30` → `...?2`） |
| 中间碎片 | 9939 条（真实 5551），靠 URL 去重压回 5551 |
| 连带：`n=` 参数 | 写成 9939（错值，影响正文换源定位） |

**为什么其他来源没暴露**：trxs / jjwxc / shu05 / fanqie / qimao / ptwxz / 69shu /
uukanshu / xklxsw 的标题都不含 `/` —— 平铺扫描**侥幸通过**。
**单样本验证永远发现不了这类 bug。**

### 12.4 修复

```js
// ✔ 新版：先按记录分隔符切，再按字段分隔符切
function pseg(sv) {
  var raw = String(sv == null ? '' : sv);
  var recs = raw.split('-//-');
  var rr = [];
  if (recs.length > 1) {
    for (var i = 0; i < recs.length; i++) {
      var f = recs[i].split('-/-');
      if (f.length < 3) continue;
      var st = 0;
      if (f.length > 3) {              // 末字段是状态词时提取
        var lt = cleanName(f[f.length - 1]);
        if (lt == 'unvip') { st = 1; f = f.slice(0, f.length - 1); }
        else if (lt == 'vip') { st = 2; f = f.slice(0, f.length - 1); }
      }
      if (f.length < 3) continue;
      var a0 = cleanName(f[0]), a1 = cleanName(f[1]);
      var nm = String(f[2]);           // 标题若含 -/- 会变成额外字段 → 回粘
      for (var q = 3; q < f.length; q++) nm += '-/-' + String(f[q]);
      nm = cleanName(nm);
      // ... 双数字槽取长者为章节 ID（雪花 ID 长），短者为站点序号
    }
    if (rr.length > 0) return rr;
  }
  return psegFlat(raw);                // 回退：数据里没有 -//- 时走旧扫描
}
```

**三个设计要点**：
1. 用站点**真正的分隔符**，不要猜
2. **标题回粘**（防御性：即使标题含字段分隔符也能还原）
3. **保留回退路径**（数据格式变更时不至于全崩）

**三处同步替换**：`ruleToc.chapterList` / `ruleContent.content` / `ruleBookInfo.init`
（三处函数体逐字节相同 → 构建脚本内置一致性闸门）

### 12.5 验证方法论（可复用）

**① 服务端自带计数 = 免费真值**
```
服务端 unvip: 5460  ←→  修复后 🔑 数量: 5460  ✅ 精确一致
```
不需要人工数，交叉验证一步到位。

**② 跨来源样本矩阵（必须）**
```
faloo    标题含 / → 暴露 bug（🔑 1081→5460）
ptwxz    标题含 / → 暴露旧版自身缺陷（1 章被拆成 2 条 → 正确合并）
其余 8 个  标题不含 / → 逐字节一致（零回归）
```
单样本 = 赌博；至少抓 8~10 个不同来源的同类接口响应。

**③ 真实规则 × 真实数据 离线仿真**
从 App 内提取**真实规则代码**（不是重写），用抓包原始数据跑：
```bash
node harness.js   # 真实 ruleToc.chapterList × faloo_chapterlist_raw.json
```
输出必须与官方 App 显示一致。

**④ 真机 Rhino 复跑**
node 通过 ≠ Rhino 通过。`eval_js` 里跑同一份代码：
```json
{"total":5551, "key":5460, "srv_unvip":5460}
```

### 12.6 本轮验证清单

- [x] 真机 Rhino：新解析器 × 线上真实数据 → `key=5460` 与 `srv_unvip=5460` 一致
- [x] 10 样本矩阵回归：9 个逐字节一致 + ptwxz 修正 1 条
- [x] 49 项检查（结构/JS语法/传输纪律/非BMP/字段对照）
- [x] 52 字段 md5 回读与本地字节级一致
- [x] debug 实测：目录 5551 条、`n=5551`（修复前 9939）、正文正常
- [x] 深链导入成功（HTTP 日志 `GET <raw> -> 200`）

### 12.7 通用结论（跨站）

1. **「恰好通过」的解析器最危险**：平铺扫描在 9/10 样本上工作，
   第 10 个（标题含分隔符）暴露 —— 验证覆盖度决定 bug 暴露速度。
2. **写解析器前先问：数据格式有没有正式的分隔符？有就用它，别猜。**
3. **自由文本字段（标题/作者/简介）是分隔符的天然污染源**；
   解析代码里凡出现「靠邻槽类型推断字段」的写法，就应怀疑它会在边界样本上失败。
4. **服务端计数/校验字段是免费真值**，修复后用它交叉验证，比人工抽查可靠得多。
5. 同类风险点：搜索建议接口、章节名、多作者/标签列表、分页信息拼接串。

## 13. 【v11.12 追加】目录回归「站点原始数据」—— 章节名「二次加工」的陷阱

### 13.1 报障

> 《镇国战神》(69shu/10044050，作者剑子仙迹) **第 3 章显示成第 100 章**

### 13.2 根因：标题里的正文数字被当成章节号

**站点原始数据**：
```
Thứ 1 chương Chiến thần trở về           （第1章 战神归来）
Thứ 2 chương Gia tộc tội nhân            （第2章 家族罪人）
Thứ 3 chương 100 ức  ngồi ở kia một bàn   ← 标题里含「chương 100」
```

**旧逻辑的加工链**：越南文标题 → `vnNum()` 提取章节号 → 重写为「第 N 章」

```js
// ✘ 旧：正则优先匹配「Chương + 数字」
var RE_VN1 = new RegExp('Chương' + '[ \t]+' + '([0-9]{1,5})', 'i');
// 对 "Thứ 3 chương 100 ức..." → 匹配到 "chương 100" → 抓出 100
```

标题正文里的 `chương N`（"100 亿"）被当成章节号 → **第 3 章显示成第 100 章**。

**同类误判全书 30 处**：
| 实际 | 误显 | 标题 |
|---|---|---|
| 第3章 | 第100章 | Thứ 3 chương **100 ức** ngồi ở kia một bàn |
| 第36章 | 第6章 | Thứ 36 chương **6** Phòng ăn |
| 第38章 | 第2章 | Thứ 38 chương **2** lần giá cả |
| 第169章 | 第3章 | Thứ 169 chương **3** ức |
| 第701章 | 第3000章 | Thứ 701 chương **3000** ức mua một cái mạng |
| 第1198章 | 第1章 | Thứ 1198 chương **1%** khả năng |
| 第2323章 | 第1章 | Thứ 2323 chương **1⁄3** thế lực ra khỏi |

（凡标题里出现「chương N / N ức / N 个 / N 年 / N%」这类正文数字，全部错位）

### 13.3 修复：删掉整段「重编号」，回归站点原始目录

用户要求原话：
> 用回 STV APP 中各来源的自己的原始目录，只需要确保阅读中能读出目录，
> 不需要对它的目录进行加工，还有有会员标记的在前面加上标记

**新逻辑**（`ruleToc.chapterList`）：
```js
var LA = T1.A, LB = T1.B;
var direct = (LB.length == LA.length && LB.length > 0);
var out = [], seenC = {};
for (var i = 0; i < LA.length; i++) {
  var vn0 = decEnt(LA[i].n);
  var nm = vn0;                                    // 默认：站点越南文原文
  if (direct) {
    var cn0 = decEnt(LB[i].n);
    if (cn0.length > 0) nm = cn0;                  // 有中文（oridata）→ 用中文
  }
  if (seenC[cp] != null) continue;                 // 去重
  if (LA[i].k == 2) nm = '🔒 ' + nm;               // 会员未解锁
  else if (LA[i].k == 1) nm = '🔑 ' + nm;          // 会员已解锁
  // ... 输出
}
```

**删除**：`vnNum()` / `RE_VN1~3` / `prevK` / `usedN`（不再提取编号、不再重写标题）
**保留**：`oridata` 中文优先 / 🔑🔒 标记 / `pseg()` 结构化解析 / URL 的 `i=` 序号参数（正文换源定位用）

### 13.4 验证（真实规则 × 真实抓包数据）

| 来源 | 章节数 | 中文 | 第 3 章显示 |
|---|---|---|---|
| **69shu/10044050** | 4034 | 无 | `Thứ 3 chương 100 ức  ngồi ở kia một bàn` ✅ |
| **fanqie/6901975…** | 4034 | **有** | `第3章 一百亿的坐在那一桌` ✅ |
| xbiquge/4136 | 4034 | 无 | `Thứ 3 chương 100 ức…` ✅ |
| shu05/93838 | 4034 | 无 | `Thứ 3 chương 100 ức…` ✅ |

**回归**（10 样本）：faloo/770959 保持 5551 章 + 🔑5460；jjwxc 保持 🔑198 + 🔒2；其余 8 个逐字节一致。

### 13.5 通用教训（★★★）

1. **站点给的数据不要「二次加工」**：一旦把 A 格式改写成 B 格式，任何格式歧义都会变成显示错误。
   「chương N」既是编号前缀也可能出现在正文里 —— **只有不做加工才能零风险**。
2. **正则可加锚点降低误判，但根治是「不加工」**：标题是自由文本，
   任何「从中提取数字」的写法都会在某个边界样本上失败（30 处误判就是证据）。
3. **中文优先是数据层面的**（`oridata` 字段与 `data` 一一对齐），不是机器翻译 ——
   有就用、没有就用原文。
4. 用户诉求「只需能读出目录、不加工、保留会员标记」= **最小加工原则**：
   **只做「数据搬运 + 状态标记」，不做「内容改写」**。

### 13.6 本轮验证清单

- [x] node --check 9/9
- [x] 离线仿真：4 个来源 × 真实数据，第 3 章全部正确
- [x] 回归：10 样本矩阵，faloo/jjwxc 标记数保持，其余逐字节一致
- [x] 字段级 diff：仅 `ruleToc.chapterList` / `bookSourceComment` / `lastUpdateTime`
- [x] 52 字段 md5 回读与本地字节级一致
- [x] debug 实测：目录 4034 章 / 正文中文正常 / `n=4034`
- [x] check_source 通过 1/1

## 14. 【v11.13 / v11.14 追加】74 样本全来源测试：目录通用性加固

### 14.1 背景

v11.12 让目录回归「站点原始数据」后，做了一轮**全来源通用性测试**：
7 本书 × 最多 20 个来源 = 抓取 **74 个目录样本**（覆盖 40+ 个来源站）。

### 14.2 发现一：部分来源的「最新章节置顶块」导致目录截断

**结构**（ranwenla / paoshu8 / uuxs 等来源）：
```
pos 0..N    : 最新 N 章复制一份放在开头（倒序，标记 Phần mới = 最新）
pos N+1..end: 完整正序列表（1 → 末章）
```

**问题**：旧去重逻辑「保留首次出现」会保留置顶块、把正序列表里的同一批章节删掉 →
目录开头是最新章倒序，**正文列表在中间就断了**（ranwenla 实测：读到 336 章就停，
337~351 永远读不到）。

**修复**：去重改为「**保留最后一次出现**」（= 完整列表里的那一份），顺序恢复正常。

| 样本 | 旧策略逆序点 | 新策略逆序点 |
|---|---|---|
| ranwenla/155870 | 18 | **4** |
| 其他 73 个样本 | — | 无变化 |

**验证**：74 样本全量对比 → **改善 1 个、变差 0 个**（纯改进）。

### 14.3 发现二：chapMap 与目录输出序号不一致

**背景**：v11.13 给目录加了去重，但正文规则的 `chapMap`（换源定位用）仍用未去重的数组建索引。
实测 ranwenla：目录输出 **904** 章，`chapMap.ids` 有 **918** 条 → 序号错位 14 位。

**影响**：换源时若走「按序号兜底定位」路径（标题匹配失败时），可能定位到错章。

**修复**：`chapMap` 应用同一套「保留末次」去重，使 `ids` 与目录输出序号一一对应。

**验证**：74 个样本逐个对比 `chapMap.ids` 与目录输出的章节 ID 序列 → **74/74 完全对齐**。

### 14.4 全量测试结果（74 样本 / 107424 章节）

| 检查项 | 结果 |
|---|---|
| 服务端 `unvip` 计数交叉验证 | **7/7 PASS**（🔑 数量精确一致） |
| 章节 URL 唯一性 | **107424/107424 唯一**（Legado 不会误合并） |
| chapMap 对齐 | **74/74 完全对齐** |
| 顺序 | 18 完全单调 + 47 轻微逆序(≤20) + 9 明显逆序 |
| 9 个明显逆序的根因 | **均为站点原始数据**（置顶块 / 源站章节号重复） |

**9 个明显逆序样本的站点数据特征**：
| 样本 | 现象 |
|---|---|
| paoshu8/1011、xbiquge/6169、uukanshu/44 | 置顶块（最新 3~15 章复制到开头） |
| ptwxz/1272、yushubo/36220 | 源站章节号跳号（"第335章"后跟"第236章"） |
| shucw/13785 | 源站 212 个重复章节号 |
| uukanshu/74534 | 源站 249 个重复章节号 |
| uukanshu/10079 | 整体倒序（`normPair` 已正确翻转） |
| 69shu/31477 | 源站章节号重复 |

**覆盖来源**（40+）：qidian / 69shu / 69shuorg / uukanshu / uuxs / ddxs / ptwxz /
bxwxorg / biquge / biqugexs / biqugeinfo / hetushu / yushubo / shubaow / shu05 /
shucw / qimao / xbiquge / xklxsw / xinshuhaige / 230book / biqubu / ranwenla /
paoshu8 / zwduxs / faloo / trxs / jjwxc 等

### 14.5 通用教训（★★★）

1. **「保留首次」vs「保留末次」的去重语义**：站点把内容复制到开头时，
   保留首次会把「展示用的副本」当成正文，导致主体被截断。
   **判据 = 哪一份能让顺序单调**（保留末次）。
2. **跨函数的一致性**：目录输出与换源索引必须用**同一套去重策略**，
   否则序号会错位。这类 bug 不会报错，只在换源时静默给错章。
3. **「顺序错乱」要分两类**：① 我们的去重策略问题（可修）；② 站点源站数据本身
   混乱（章节号重复/跳号，不可修且不该修 —— 用户要求「不加工」）。
   **判断方法**：看原始数据的章节号是否本身就重复。
4. **全来源测试的价值**：74 样本才暴露出置顶块问题（单样本完全看不到）。
   **测试覆盖度决定 bug 暴露速度。**

### 14.6 本轮验证清单

- [x] node --check 9/9
- [x] 74 样本 × chapMap 对齐：74/74
- [x] 74 样本 × URL 唯一性：107424/107424
- [x] 服务端 unvip 交叉验证：7/7
- [x] 字段级 diff：仅 `ruleToc.chapterList` / `ruleContent.content`
- [x] 52 字段 md5 回读字节级一致
- [x] debug 实测：qidian 1419 章中文目录 / 正文正常
- [x] check_source 通过 1/1
