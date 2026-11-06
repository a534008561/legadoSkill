# 方法：GoEdge WAF 的 UA 白名单、rrssk 搜索凭证链与"正文被清空"的三组对照实验

> 沉淀日期：2026-11-06 ｜ 来源：www.mopbook.com（猫扑小说）书源制作
> 关联：[方法-多层密钥AES与轮换签名逆向](方法-多层密钥AES与轮换签名逆向.md)、[WAF挑战过盾指南](WAF挑战过盾指南.md)、[方法-假表单搜索接口与列表内联文本提取](方法-假表单搜索接口与列表内联文本提取.md)、[方法-静默失败定位与探针法](方法-静默失败定位与探针法.md)
> 成品：`examples/猫扑小说_www.mopbook.com.json`

---

## 〇、本次站点画像（先记住它长什么样）

| 项 | 结论 |
|---|---|
| 站点 | `https://www.mopbook.com`（UTF-8，静态 HTML，杰奇/自研模板） |
| 盾 | **GoEdge WAF 图片验证码**（`307 → /WAF/VERIFY/CAPTCHA?info=...`，页面 `Verify Yourself`，隐藏域 `GOEDGE_WAF_CAPTCHA_ID`） |
| 搜索 | **首页是假表单**：`<form>` 无 action/name，点搜索直接跳第三方 `https://www.rrssk.com/00PB.html` |
| 搜索中转 | `www.rrssk.com/00PB.html` 是本站的官方搜索页（标题"猫扑小说 - 小说搜索"），v10 每日轮换 JS 签名 |
| 目录 | 详情页首 100 章在 `.chapter_list`；第 2..N 页 `POST /index.php?action=loadChapterPage`，`data=AES-256-CBC({"id","page"})` |
| 正文 | `<div class="content">`，章节内分页 `/book/ID-章-页.html`，含 rrssk 家族 PUA 图标字体反爬 |
| 登录 | 无。`/login.html` `/register.html` `/member.php` `/user.php` 全 404，页面无登录字样 → 游客可读，按"不影响使用可不写"不配登录 UI |
| 发布页/备用线路 | 无。全站外链只有 rrssk（搜索）、zhaoshu.la（求书）、ciyuankong.com（论坛）→ 不写发布页输入框/线路按钮/测速 Toast |
| bookUrlPattern | `https?://(?:www\.)?mopbook\.com/book/[A-Za-z0-9]+\.html.*`（覆盖详情/章节/章节内分页三种 URL） |

---

## 一、★新发现 1：GoEdge WAF 的 UA 白名单方向可能与直觉相反

### 现象
同一时刻、同一出口 IP，只对 UA 做单变量对照（**非搜索页面，不触发搜索风控**）：

| UA | 首页结果 |
|---|---|
| `Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/120.0.0.0 Safari/537.36`（桌面 Chrome） | **HTTP 307 → WAF 验证码页** |
| `Mozilla/5.0 (Linux; Android 13; Pixel 7) ... Chrome/120.0.0.0 Mobile Safari/537.36` | **HTTP 200，43KB 真实首页** |
| `Mozilla/5.0 (Linux; Android 10; K) ... Chrome/131.0.0.0 Mobile Safari/537.36` | 200 真实首页 |
| `Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Legado/3.0` | 200 真实首页 |
| `Googlebot/2.1` | 200 真实首页 |

### 结论
**该站 WAF 拦的是"桌面浏览器 UA"，放行的是"移动 UA / 爬虫 UA"**——与常见的"只放行完整桌面 Chrome UA"（如 m.bookmaopu.com 的 CF 白名单）**正好相反**。

### 通用方法论（比记住这个站更重要）
1. **UA 对照必须包含反向验证组**：至少 桌面Chrome / 移动Chrome / 含 Legado 的 Android UA / 爬虫 UA 四组；只测两组容易得出"站点全挂"或"必须人工过验证码"的错误结论。
2. **盾类型靠响应体指纹定性，不靠状态码**：`GOEDGE_WAF_CAPTCHA_ID` + `Verify Yourself` = GoEdge 图片验证码；不要一看到 307 就去写 `java.startBrowser()` 过盾流程。
3. **若移动 UA 直接放行，就不需要验证码 UI / WebView 过盾 / Cookie 人工回写**——把 UA 写进书源 `header` 即可，这是成本最低的解。
4. 书源 `header` 必须**显式带 UA**：MCP `eval_js` 的 `java.ajax(url)` 不带自定义 UA 时会拿到 WAF 页（本次实测 `len=2521` 的 `Verify Yourself`），而 `java.get(url, {'User-Agent': UA})` 拿到真实页。调试时若 eval_js 与 debug_source 结果不一致，**先怀疑 UA 没透传**。
5. 该 WAF 是**域名级**的：`www.rrssk.com` 同样吃这套（带 UA 的 `java.get` 拿到 3830B 搜索页，不带 UA 的 `java.ajax` 拿到 2539B 验证页）。**搜索中转站与内容站要分别带 UA**。

---

## 二、★新发现 2：rrssk v10 搜索是"三段凭证链"，漏一步就报「搜索凭证失效」

### 完整链路（实测全通）

```
① GET  https://www.rrssk.com/00PB.html         [带移动 UA]
   ← Set-Cookie: PHPSESSID=xxx
   ← HTML: <input name="_t" value="{32位hex}">       一次性令牌
   ← HTML: <script src="/?action=signJs&v=17-20261106">   ← 必须从页面动态抠，v=日期每天变

② GET  https://www.rrssk.com/?action=signJs&v=...  [带移动 UA]
   ← Set-Cookie: __snc=<hex>_<ts>_1_<hash>; HttpOnly; SameSite=Lax   ★★ 关键
   ← 当日签名算法 JS（变量名每日随机，算法结构稳定）

③ POST https://www.rrssk.com/?action=search      [带移动 UA + PHPSESSID + __snc]
   body: _t={token}&_ts={unix秒}&_s={8位hex签名}&keyword={RFC3986编码关键词}
   → HTTP 302 Location: /?action=find&v=16&q={AES密文}&page=1
   → Legado 自动跟随 302 → 结果页 HTML（20 张 .book-card / 页，共 3 页）
```

### ★★ 隐藏坑：`__snc` 是"搜索凭证"的组成部分

只做 ①③、跳过 ②（或 ② 请求没带 UA / 没进同一 CookieJar）时，**签名算得完全正确**，服务端却返回：

```
搜索凭证失效，请刷新页面重试      (403, 14 字节)
```

对照组（**env 常量单变量实验**）：

| env 常量 | 响应 |
|---|---|
| 45 | `搜索凭证失效` ← 签名**通过**，卡在凭证 |
| 0 / 41~44 / 46~48 | `签名校验失败` ← 签名算错 |

**判据**：返回「签名校验失败」= 算法/常量错；返回「搜索凭证失效」= 算法对但**凭证链缺件**（通常是没请求 signJs 拿 `__snc`）。这两句错误信息是免费的分段探针，别当成同一个错误。

### 为什么要从页面抠 signJs URL
`/?action=signJs` 不带 `v=` 参数直接 **404**（本次实测）。而 `v=17-20261106` 每天变。正确做法：

```javascript
var sm = home.match(/<script src="(\/?\?action=signJs[^"]*)"/);
var sjUrl = sm ? (sm[1].charAt(0)==='/' ? base+sm[1] : base+'/'+sm[1]) : base+'/?action=signJs';
```

**不要硬编码日期**。

### 每日轮换签名的"数值常量提取法"（本次新做法，与已有花括号配平法互补）

已有文档推荐「花括号配平 + eval 整段函数」。本次实测 signJs 的**变量名每天全随机**（第 1 次是 `t2/o6/q/f2/a8`，第 2 次变成 `y3/a8/u4/p7/i5`），但**算法骨架与数值常量稳定**：

```
FNV 变体：f2=2166136261；每字符 f2=(f2^cc)*12883 + d1*33339 + t[d1%len]
异或 ts；5488 轮 f2=((f2^(f2>>>13))*49)；f2^=f2>>>16
最后 v = parseInt(hex,16) ^ (env*7+3)，env 由 _df45c7!==N 提取（实测恒 45）
```

因此可以更稳地**只抽数值、固定骨架**，避免 eval 站点代码（也规避浏览器环境检测 `_df45c7!==45` / `_7bc07c!==1` 在 Rhino 里必然为 false 的问题）：

```javascript
function num(re, dflt) { var m = sj.match(re); return m ? Number(m[1]) : dflt; }
var mul   = num(/\w+\s*=\s*(\d+)\s*,\s*\w+\s*=\s*\d+\s*,\s*\w+\s*=\s*5488/, 12883);
var add   = num(/\w+\s*=\s*\d+\s*,\s*\w+\s*=\s*(\d+)\s*,\s*\w+\s*=\s*5488/, 33339);
var loops = num(/<\s*(5488)\s*;/, 5488);
var env   = num(/_df45c7\s*!==\s*(\d+)/, 45);
// 结构指纹守卫：脚本改版时自动回退实测常量
if (!/\*49/.test(sj) || !/>>>13/.test(sj)) { mul=12883; add=33339; loops=5488; env=45; }
```

> 与花括号配平法的取舍：**算法结构会变** → 用配平 eval；**只换变量名/常量微调** → 用数值提取 + 固定骨架 + 结构指纹守卫。★★**本次跨日实测推翻了"数值提取法够用"的乐观判断**：见下方 §二·补。

### ★★ 补：跨日 0 点后「搜索为空」= 算法整套换掉（用户实测报障 → 修复）

**现象**：v1 书源在 11-06 当天全部调试通过（搜索/发现/目录/正文全绿），用户次日实际搜索返回空。
开 `set_http_log_recording(true)` 复现 + `get_http_log` 看响应体，实锤：

```
GET  /?action=signJs&v=17-20261107  ← 版本跨日变了
POST /?action=search -> 403 「签名校验失败」
debug_source 无 302、列表大小 0（403 错误页被当结果页解析，最阴险的静默失败）
```

**根因**：站点**每天把签名算法整套换掉**，不只是换变量名：

| | 11-06 | 11-07 |
|---|---|---|
| 结构 | FNV 正序 | **DJB2 倒序** |
| 初值 | 2166136261 | 0 |
| 每字符 | `(f2^cc)*12883 + d1*33339 + t[i]` | `(p7*33)^(cc+t[i]) + 28671` |
| 异或 | `ts` | `62886 ^ ts` |
| 轮数/乘子 | 5488 轮 `*49` + `>>>13` + `>>>16` | 1861 轮 `*48647` + `>>>7` + `>>>13` |
| env 常量 | 45 | 40 |
| 环境检测变量名 | `_df45c7` / `_7bc07c` | `_cd2160` / `_ab1615` |

v1 的「结构指纹守卫」只看 `/\*49/` 与 `/>>>13/`，新算法仍含 `>>>13` 且 `*48647` 不含 `*49`… 实际回退到昨日常量 → 403。
**结论：任何写死骨架/常量的方案，跨日必挂。**

**最终生产方案（已实测跨两日全绿）= 花括号配平 + eval 当日函数体**：

```javascript
// 1) signJs URL 必须从 00PB.html 动态抠（v=日期每天变，不带 v= 直接 404）
// 2) 花括号配平从「function _xxx(s,t,ts){」起取整段函数（函数名每天随机）
function braceSlice(src, from) {
  var i = src.indexOf('{', from), d = 0;
  for (var j = i; j < src.length; j++) {
    if (src.charAt(j) === '{') d++;
    else if (src.charAt(j) === '}') { d--; if (d === 0) return src.substring(from, j + 1); }
  }
  return '';
}
var fs = sj.search(/function\s+_[0-9a-fA-F]+\(s\s*,\s*t\s*,\s*ts\)\s*\{/);
var body = braceSlice(sj, fs);
var fn = (body.match(/function\s+(\w+)\(/) || [])[1];
// 3) ★浏览器环境检测常量必须补：Rhino 里 document/window/isTrusted 不存在，
//    站点函数直接 return 会恒得 "00000000"。从脚本里把变量名和值抠出来注入。
var em = sj.match(/typeof\s+(\w+)\s*!==\s*"number"\s*\|\|\s*\w+\s*!==\s*(\d+)/);
var envName = em ? em[1] : 'mbEnv', envVal = em ? Number(em[2]) : 45;
var trustName = (sj.match(/if\((\w+)\s*!==\s*1\)/) || [])[1] || 'mbTrust';
var pre = 'var '+envName+'='+envVal+';var '+trustName+'=1;\n'+body+'\n';
var sig = String(eval(pre + fn + '(enc(kw), token, ts)'));
```

**验证闭环**：不能只"算出签名"，必须**真实 POST 一次看响应**（本次 eval 算出 `f475f833` → 真实 POST 返回 38132B / 20 卡片 / `斗破苍穹 - 搜索结果`）。
**排查纪律**：用户报「搜索为空」→ 先 `set_http_log_recording(true)` + `get_http_logs` 看状态码/响应体，别猜规则；`403「签名校验失败」` 与 `403「搜索凭证失效」` 是两条完全不同的排查路线。

> 带来的通用教训：**"每日轮换"类站点，必须在换日前后各做一次端到端验证**；只在同一天里跑多组关键词，验证强度等于零。本次恰好跨 0 点，用户实测才暴露。

### 结果页字段
- 列表：`@css:div.book-card`（20/页，`result-pagination` 有 `page=2/3`）
- 详情 URL：`onclick="window.open('?action=go&t={base64}&s=...&e=...')"` → **`t` 参数 base64 解码直达 `https://www.mopbook.com/book/XXX.html`**，不必再请求 `?action=go`
  ```javascript
  var m = String(result).match(/action=go&(?:amp;)?t=([A-Za-z0-9%]+)&/);
  return String(java.base64Decode(decodeURIComponent(m[1])));
  ```
- 作者/分类在 `<span class="book-card__meta-item">作者：xxx</span>` 内联文本里，用 `@js:` 正则取；`class.book-tag@text` 会同时抓到分类和"已完结/连载中"（可接受）。

### 搜索节流（用户明确要求"不要主动探测搜索频率"）
书源 `searchUrl` 的 `@js` 里做**会话级 2.5s 门槛**（`source.put('mbSearchTs')` + 补睡），不去探测站点限频阈值、不发额外探测请求。`concurrentRate` 设 `1/1000` 只作兜底；**不设过大间隔**，否则长篇目录 31 页串行 AJAX 会被整源限速拖到超时（书海阁 v1 教训）。

---

## 三、★新发现 3：`replaceRegex` 写成"无替换文本"会把正文整段清空

### 现象
`ruleContent.content` 的 `@js:` 已实测能返回 2000+ 字正文，但 debug 输出只剩 `　　n`，或 `ContentEmptyException: 内容为空`。

### 五组探针对照（定位法）
| 探针 | content 规则 | replaceRegex | 输出 |
|---|---|---|---|
| 3 | 单行 `@js:` 返回常量 | `''` | `PROBE_OK_9378` ✅ |
| 4 | **多行** `@js:` 返回常量 | `''` | `MULTI_OK_9378` ✅（证明多行 @js 无罪） |
| 5 | 单行 `@js:` 返回常量 | `##\s*猫扑小说\s*##\n##\s*请收藏.*?\s*##` | `　　` + 空内容异常 ❌ |
| 正式 | 多行完整清洗 | 同上 | `　　n` ❌ |
| 修复 | 多行完整清洗 | `''` | 完整正文 ✅ |

### 根因
`##正则##替换` 里**替换文本不能省**。我原本想"删掉匹配行"，写成了两段连写的 `##...##\n##...##`，被解析成"整段作为替换/非法规则"，把 `@js` 的结果吃光。`ruleContent.replaceRegex` 作用于**正文最终文本**，不是只作用于 HTML 清理阶段。

### 铁律
1. 正文清洗**全部放进 `content` 的 `@js`**（`split('\n').filter(...)` 逐行过滤），`replaceRegex` 保持空串最安全。
2. 确需 `replaceRegex` 时，每条必须是完整的 `##正则##替换内容`，删除类写 `##正则##`（三段式且替换为空），不要连写两条不带替换文本的 `##`。
3. 排查「正文输出只剩几个空白字符」时，**先清空 replaceRegex 做对照**，别急着改 `@js`（本次差点误判成 `setContent` 污染 / `result` 类型问题）。
4. 同类"静默清空"还有 `init` 规则：`ruleBookInfo.init` 里写 `@js` 调 `source.put(...)` 且不返回值 → `AnalyzeRule.setContent` 抛 `AssertionError: 内容不可空`。**init 要么返回非空串，要么留空**；书籍 ID 这类中间量在目录规则里从 `baseUrl` 重新提取即可。

---

## 三·补、★新发现 4：发现页「只显示一页」= 固定推荐位 + 站点假分页（用户实测报障）

### 现象与定位
用户报「发现列表只显示一页」。抓取 `list-4-1/2/3/20` 与 `rank-1/2/3` 做**跨页内容对照**：

| 页面 | 原规则 `@css:div.picList li` | 实际 |
|---|---|---|
| 分类页 1/2/3/20 | 都是同样 6 本（「读书十年无人闻…」开头） | `div.picList` 是**固定推荐位**，每页不变 |
| 分类页 `.conLC .rankList ul li` | 每页 28 本且**逐页不同** | 这才是随页码变化的真列表 |
| `rank-1/2/3.html` | 文件字节数完全相同，diff 只有 `<title>` 里的页码 | **站点假分页**，无 rankList |

⇒ 根因不是「没有翻页」，是**抓错了容器**：抓到每页都一样的推荐位，App 看起来永远只有一页。

### 修法（双模板分流）
`ruleExplore.bookList` 用 `@js` 按页面是否含 `rankList` 分流：
- 分类页 → 从 `.conLC .rankList` 的 `<li>` 正则切出 28 条（字段全在 li 内联：书名/作者/分类/最新章/日期，但**无封面无简介**，详情页会补齐）；
- 排行页 / 首页 → 仍走 `java.getElements('@css:div.picList li')`（51 本，带封面与简介）；
- 字段规则全部改 `@js` 正则，兼容两种 li 模板。
- `exploreUrl` 里排行榜改回单页 `rank.html`（既然各页内容相同，不配 `{{page}}` 假分页）。

### ★★ 翻页终止：不写死页数，用站点自身信号
我一度想按 `class="last" href="/list-N-20/"` 写死 20 页上限，**用户明确纠正**：「限制页码，后面网站增加书了怎么办？」。改为纯内容级判据：

实证（分类 4）：

| 页 | `class="next"` | rankList 首书 |
|---|---|---|
| 19 | 有（`href="/list-4-20/"`） | 修仙大道，从古稀老头开始 |
| 20（末页） | **无** | 财迷大师兄居然是绝美女剑仙 |
| 21 / 22 / 25（超界） | 无 | 与第 20 页**完全相同**（38253B 全同） |

即站点超界后返回 200 + 末页副本，若不拦截会无限翻出重复书。生产规则：

```javascript
// 与上页首条比对：内容重复 且 页面自身已无「下一页」→ 返回空 Java List 终止
var first = o[0].replace(/\s+/g,'').slice(0,200);
var prev = String(source.get('mbExploreLast')||'');
var hasNext = /class=.next.\s+href=.\/list-\d+-\d+\//.test(h);
if (prev && prev === first && !hasNext) return new Packages.java.util.ArrayList();
source.put('mbExploreLast', first);
return o;
```

- **无硬编码页数**：站点以后加书 → 末页重新出现 `next`、首书变化 → 翻页自动继续；
- 末页本身**照常显示 28 本**（第一次出现不判重），只在「下一页也返回同样内容」时终止；
- 实测：页 20 → 28 本全链路到正文全绿；页 21 → 日志「内容与上页重复且无下一页，自然终止」、列表 0 条 ✅。

> 通用教训：①「发现只有一页」先做**跨页内容 diff**，别急着改 `{{page}}`；②页面里「看起来像列表」的容器可能只是固定推荐位，真列表常在同页另一个 class；③分页终止优先用**站点自身的 next 链接 + 内容指纹**，硬编码页数会随站点数据增长失效。

### ★ 规则文本里的裸双引号坑
`@js` 里写 `h.indexOf('class="rankList"')` 时，JSON→App 传输后双引号变成裸引号，Rhino 报 `在参数列表的后面缺少 ")"`（源码上下文显示 `h.indexOf("class="rankList")<0`）。**正解**：判据只用无引号特征 `h.indexOf('rankList')`，或用 `class=.next.` 这类点号通配写法，规则文本里**不出现 `class="`**。多行脚本用 Python 三引号 raw 字符串生成，避免转义层数失控。

## 四、其它本次实踩的坑（复用价值高）

1. **`@js` 里 JS 数组与 Java List 混用**：中间结果用 `out.push(...)`，只有**最终返回**才 `new Packages.java.util.ArrayList()` + `list.add(...)`。本次把 `function push(list,...)` 里写成 `list.add` → `TypeError: 找不到函数 add`。**参数命名别叫 `list`**（叫 `arr`），避免和最终 Java List 混淆。
2. **E 版兼容定式再次验证**：`chapterList` 返回 `java.util.ArrayList`、每项 `JSON.stringify({chapterUrl,chapterName})`、字段规则 `$.chapterUrl` / `$.chapterName` —— LT 与 E 版都通（LT 版 debug 全绿，E 版源码级要求见《legado双版本差异》）。
3. **目录一次抓全 vs nextTocUrl**：本站目录分页是加密 AJAX，**不能靠 nextTocUrl 翻 HTML**（下一页按钮是 `javascript:;`）。在 `chapterList` 的 `@js` 里循环 2..N 页发 POST 最稳；31 页/3084 章实测 31s 完成，顺序严格递增。页数从 `<option value="N">` 取最大值，加 `>60` 上限防异常页死循环。
4. **AES 请求体加密**：`java.base64Encode(byte[])` 在 Rhino 里会得到 `[B@a65ea76`（对象地址串），必须**手写 JS base64** 或 `java.base64EncodeToString`。本次用纯 JS `b64(bytes)` 循环，Python↔App 逐字节一致。
5. **发现页列表选择器要看真实 DOM 层级**：页面是 `<div class="picList picList_3"><ul><li>`，`ul` **本身没有 class** → 写 `ul.picList li` 得 0 条，改 `@css:div.picList li` 得 6 条（分类页首屏）/ 51 条（排行页）。
6. **正文两套模板统一清洗**：老书 `<br />` 分段、新书 `<p>` 分段，站点还会在末尾插 `收藏mopbook.com，轻松访问猫扑小说，畅读《...》等万千好书。`。统一转纯文本后逐行 `filter` 掉含 `mopbook|猫扑小说|收藏.*访问|本站|www\.|\.com` 的行，两套模板都干净。
7. **`nextContentUrl` 双锚**：只认 `<a href="/book/ID-章-页.html">下一页</a>`；末页链接变成「下一章」且 URL 为 `/book/ID-章.html`（少一段），正则天然排除，不会串章。这类站**必须**写 `nextContentUrl`（本次每章 2~3 页）。
8. **PUA 图标字体**：直接复用技能库 `examples/rrssk聚合_44域名.json` 里 `ruleContent.content` 的 257 字 `CHARS` 表（`rep[43]='AV'`，码点 `0xE001..0xE101`），同家族通用，不必重新逆字体。**从文件读，别把 257 个敏感字符内联进工具参数**（会导致 JSON 转义失败）。

---

## 五、交付与验收记录（261106）

- 成品：`/workspace/mopbook/mopbook.json`（18.5KB，md5 `d9c57c1fe4592c53c0f80339b15c3b5e`，v3：发现页改真列表 + 内容级自然终止）
- 落库：LAN `POST /saveBookSource`（`x-legado-token` 头）→ `getBookSource` 回读**逐字段一致**（仅 `respondTime` 被校验器改写为实测 41668ms）
- MCP `debug_source` 全链路：
  - 搜索「斗破苍穹」20 条 → 详情 → 252 章/3 页 → 正文 2 页 ✅
  - 搜索「遮天」20 条 → 详情 → 107 章/2 页 → 正文 3 页 ✅
  - 发现 `list-4-2` 28 本 → 详情 → 67 章 → 正文 2 页 ✅（v3）
  - 发现 `rank.html` 51 本 → 详情 → 3084 章/31 页 → 正文 2 页 ✅（v3）
  - 正文 `--URL` 单测（2 页/3 页）✅
- `check_source`：**通过 1/1**（v3 发现页修复后复跑）
- ★**发现页回归（用户报「只显示一页」→ 修复）**：分类 `list-4-2/3/20` 各 28 本且逐页不同、`list-4-21` 自然终止 0 条、排行 `rank.html` 51 本；全链路到正文全绿。
- ★**跨日回归（11-07 00:20 用户实测报「搜索为空」→ 修复）**：`set_http_log_recording` + `get_http_log` 实锤 403「签名校验失败」+ signJs 版本 `v=17-20261107`；改花括号配平 eval 后真实 POST 返回 38132B/20 卡片，`debug_source`「斗破苍穹」「凡人修仙传」两词全链路全绿。
- 调试探针源 `?probe=1..5` 已用 `delete_sources` 全部清理，App 内只剩 1 条正式源。
- 最终必须提醒用户在 Legado APP（官版 + E 版）里实测搜索/发现/目录/正文/翻页。
