# 方法-聚合源增量新增线路与发现页 URL 自治模板分发

> 蓝本：rrssk 聚合 v8（44 域名）→ v9.2（45 域名，新增 `www.mopbook.com`，恢复 `www.shuhaoxs.com`）
> 日期：2601107　适配：官版 `LegadoTeam/legado`(master) + `Luoyacheng/legado-E`(main)
> 成品：`/workspace/rrssk_v9/rrssk_v9_2.json`（69674B，md5 `a33637f15ffd1c33eb9376ccbd97a5cb`）

---

## 0. 本次任务与结论速览

用户要求「给 rrssk 聚合书源增加网址路线 `https://www.shuhaoxs.com`、`https://www.mopbook.com/`，
需要发现规则 / 书源 URL 正则 / UA，登录界面写发布页输入框 + 一键获取网址路线 + 测试延时 + 各网站点击切换 +
延时 ms 写回各网址按钮 + 各阶段 Toast，检查登录状态按钮；注意搜索间隔不要频繁；双版本兼容」。

**关键前提甄别（动手前必须做）**：`shuhaoxs.com` 其实 **已在 v8 的 44 域名内**（kelexs 模板），
只是历史记录 `260825g` 标记它「502 站点故障」；今日实测已恢复（首页 43092B / 分类页 `list dList` 完整）。
所以真正需要新增的只有 `mopbook.com`。**增量任务先 diff 现有 hosts/模板/正则，别把「已存在」当「新增」重复写**，
否则映射重复、`hosts` 数组多一项、登录面板多一个同名按钮。

两站合约（当日实锤）：

| 项 | shuhaoxs.com | mopbook.com |
|---|---|---|
| 首页 | 43092B，搜索中转 `https://www.rrssk.com/000P.html` | 36802B，中转 `.../00PB.html` |
| 书 ID | 小写字母数字 `t0ftt0f` | base32 风格 `B469` / `54F14` |
| 详情页 | `/book/ID.html`（og 全字段） | 同左（og 全字段 + `var articleid`） |
| 章节 URL | `/book/ID-章.html`，章内分页 `/book/ID-章-页.html` | 同左 |
| 密钥 JS | `/templates/js/<随机>.js`，`AESCrypt('..');` + `parse('..');` | `/templates/js/SCT*.js`，`class AESCrypt` 新格式（`new AESCrypt('..')`），**v8 init 的正则天然兼容** |
| 目录分页 | `[data-aid="ID"] option` → 2 页 | 同左 → 31 页（3084 章） |
| 目录 POST | `/index.php?action=loadChapterPage` AES-CBC `data=` | 同左，实测 code=0 返回 62/289/3084 章 |
| 正文 | `.content@html` + `text.下一页@href` | 同左 + PUA 图标字体、站点广告行（v8 通用分支已覆盖） |
| 发现页 | `//div[@class="list dList"]/ul/li`（kelexs 模板，**v8 已有**） | 分类页真列表 `.conLC .rankList ul li`（28 本/页）；排行/首页 `div.picList li`（51 本） |
| 登录/验证码/发布页 | 全无，游客可读 | 全无，游客可读 |
| WAF | 移动 UA 放行 | GoEdge：桌面 Chrome UA 307 验证码页，移动 UA/含 Legado 的 Android UA 放行 |

---

## 1. ★★ 新坑 A：聚合源发现页模板按「全局 server」分发 → 跨站浏览串模板

### 症状（反向验证组实锤）
`v8` 的 `ruleExplore` 九个字段全部长这样：

```js
"@js:\nlet nameRL = rules[GET('server')].name;\njava.getString(nameRL);"
```

即模板键来自**全局变量 `server`**（发现页下拉 / 登录面板选站写入）。

- 正常组：`setSite('https://www.mopbook.com')` → `::https://www.mopbook.com/rank.html` → **51 本** ✅
- 故障组：`setSite('https://www.shuhaoxs.com')` → 仍访问 `::https://www.mopbook.com/rank.html` → **0 本** ❌

根因：`EX_HOST` 缺席时，`rules[GET('server')]` 拿到的是 **shuhaoxs 的 kelexs 模板**
（`bookList='//div[@class="list dList"]/ul/li'`），而 mopbook 的 rank.html 根本没有 `list dList`
→ 列表 0 条。切回 mopbook 立刻 51 本，排除「站点/网络/正则」因素。

这与 `方法-聚合源状态漂移修复与选站面板-rrssk.md` 里的「书架书正文为空」是**同一类病的新变体**：
- 旧病：正文/目录分支误用全局 `server` → 用 `SRV(book.bookUrl/baseUrl)` 修
- 新病：**发现页模板分发**误用全局 `server` → 用 `EX_HOST(baseUrl)` 修

### 修法（URL 自治，与 SRV 同思路）
`jsLib` 新增：

```js
function EX_HOST(bu) {
  var u = String(bu || '');
  var m = u.match(/^(https?:\/\/[^\/]+)/i);
  var host = m ? m[1] : '';
  var sv = '';
  try { sv = GET.call(this, 'server'); } catch (e) { sv = ''; }
  function norm(x) { return String(x || '').replace(/\/$/, '').toLowerCase(); }
  if (host) {
    var nh = norm(host);
    if (rules[host]) return host;                       // 精确匹配优先
    for (var k in rules) {                              // 大小写 / 尾斜杠容错
      if (rules.hasOwnProperty(k) && norm(k) === nh) return k;
    }
  }
  return sv || (hosts && hosts.length ? hosts[0] : 'https://www.kelexs.com');
}
```

`ruleExplore` 九字段把 `GET('server')` 全换成 `EX_HOST(baseUrl)`（**其余逻辑零改动**）。
注意 `EX_HOST` 里回退分支用 `GET.call(this,'server')`，因为 jsLib 函数在不同 JS 环境里 `this` 绑定不同。

### 验证闭环（必须含反向组）
1. 污染态：`server=shuhaoxs` 时访问 `::mopbook/rank.html` → **51 本**（v9.0 是 0 本）
2. 详情页 `server自动对齐: https://www.shuhaoxs.com -> www.mopbook.com`（v8 的 og:url 对齐照常工作）
3. 目录 3084 章 / 31 页 → 正文 2 页合并完整
4. `server=mopbook` 时访问 `::shuhaoxs/list-4-1/` → 20 本 → 140 章 → 正文完整

> **通用判据**：凡「多域名聚合 + 按域名分发规则」的书源，规则的域名键必须来自
> **被解析内容自身的 URL**（`baseUrl` / `book.bookUrl` / 章节 URL），不能用任何全局可变状态。
> 全局状态只允许用于「UI 展示 / 发现页 URL 生成」，不允许用于「内容解析分支」。

---

## 2. ★★ 新坑 B：增量新增线路时，「模板值写成 @js: 规则」可零改动复用现有解析链

### 背景
v8 的 `ruleExplore` 字段是**双层规则**：外层 `@js:` 从 `rules[域名]` 取一个「规则字符串」，
再交给 `java.getString(规则字符串)` / `java.getStringList(规则字符串)` 二次解析。
既有 14 个模板的值都是 CSS/XPath 选择器（如 `'a.1@text'`）。

### 新增 mopbook 的困难
猫扑分类页真列表在 `.rankList`、排行页在 `div.picList`，且**分类页 `div.picList` 是每页同样的
6 本固定推荐位**（跨页 diff 实锤），必须双模板分流 + 内容级自然终止。纯 CSS/XPath 选择器表达不了。

### 解法：模板值本身写成 `@js:` 规则
把 v3 独立猫扑书源成品的 `ruleExplore` 字段规则（全是 `@js:` IIFE 正则）**原样塞进 `TEMPLATES.mopbook`**：

```js
mopbook: {
  bookList: "@js:(function(){ ... 返回 java.util.ArrayList ... })()",
  name:     "@js:(function(){var t=String(result);var m=t.match(...);return m?m[1]:''})()",
  author:   "@js:...", intro: "@js:...", coverUrl: "@js:...", ...
}
```

`ruleExplore` 的 `java.getStringList(rules[sv].bookList)` 会把 `@js:` 前缀识别为 `Mode.Js`
→ 执行 IIFE → 得到列表。**`ruleExplore` 一个字都不用改**，新增线路只动 `jsLib` 的
`HOST_TEMPLATE_MAP` + `TEMPLATES` 两处，对既有 44 域名零风险。

> 这个技巧的前提：外层字段规则必须是「`java.getString*(取到的规则)`」形态，
> 而不是直接把模板值当结果用。写新聚合源时可主动设计成这种双层结构，后续加站成本最低。

### E 版（legado-E）兼容定式（源码实锤）
E 版 `AnalyzeRule.getElements` 末尾只有 `result?.let { return it as List<Any> }`，
**没有 LT 版的 `is NativeArray -> ArrayList` 分支** ⇒ Rhino 原生数组会 ClassCastException → 目录/发现空列表。

所以 `bookList` 的 IIFE **必须**：

```js
var o = [];                                  // 中间用纯 JS 数组 out.push()
... 逐项 push ...
var L = new Packages.java.util.ArrayList();  // 最终返回 Java List
for (var k = 0; k < o.length; k++) L.add(o[k]);
return L;
```

字段规则统一 `@js:` + `String(result)` 正则（E 版 `getString` 对 String 走 `Mode.Js`，
对 `NativeObject` 才是「键值直取」，故不能返回 JS 对象）。
实测官版 + E 版源码核对：`getString`/`getElements` 分支均可通。

### 发现页翻页终止：站点自身信号，禁止写死页数
用户明确要求「页码上限不用管，你限制页码，后面网站增加书了怎么办？」。

```js
var prev = String(cache.get('rrssk_mb_last'));       // 上页首条内容指纹
var first = o[0].replace(/\s+/g,'').slice(0,200);
var hasNext = /class=.next.\s+href=.\/list-\d+-\d+\//.test(h);  // 站点自身 next 链接
if (prev && prev === first && !hasNext) return new Packages.java.util.ArrayList(); // 自然终止
cache.put('rrssk_mb_last', first);
```

- 实测 `list-4-20`（末页）→ 28 本照常显示
- 实测 `list-4-21`（超界页，站点返回 200 + 末页副本）→ 打印「内容与上页重复且无下一页，自然终止」→ 0 条
- 站点以后加书 → 末页重新出现 `next` 且首书变化 → 翻页自动继续

★ `@js:` 规则文本里**禁止出现 `class="xxx"` 裸双引号**（JSON→App 传输后 Rhino 报
「在参数列表的后面缺少 )」），判据一律用 `indexOf('rankList')` / `class=.next.` 点号通配。

---

## 3. ★ 新坑 C：官版 `LegadoTeam/legado` 与 E 版登录面板源码差异核对

本次用户指定的官版仓库是 **`LegadoTeam/legado`（分支 master）**，不是以往笔记里的 gedoor/legado。
用 GitHub Contents API 下载源码逐个核对（github.com 443 被墙，api.github.com 可达）：

| 能力 | 官版 `LegadoTeam/legado`(master) | E 版 `Luoyacheng/legado-E`(main) | 结论 |
|---|---|---|---|
| `loginUi` V1 动态 `<js>...</js>` | `BaseSource.getLoginUiJs()` 走 `JS_PATTERN.matches()`（`<js>` 或 `@js:`） | `onFragmentCreated` 里 `startsWith("<js>")` + `lastIndexOf("<")` 截取 | **两版都支持** |
| `viewName` 动态文本 | `rowUiBuilder` 里 Type.button：3..19 且首尾单引号=字面量，否则 `evalUiJs(viewName)` 异步求值 | 同款三分支 | **两版都支持** |
| `RowUi.key/hint/value/options` | 有 | **无**（Gson 静默忽略） | 输入框一律用 **`name` 作存取键** |
| 登录按钮 action 绑定 | `evalJS("$loginJS\n$action")` + `put("java", sourceLoginJsExtensions)` + `put("result", getLoginData(rowUis))` | 同款 | action 里 `source` 仍绑定（BaseSource.evalJS），`java` 被覆盖成 SourceLoginJsExtensions |
| `java.reLoginView()` / `refreshExplore()` | 有（`@JvmOverloads`） | 有 | 面板重建可用 |
| `function login(){}` | 右上角 ✓ 必需（否则 `Function login not implements!!!`） | 同 | 必需 |

★ `evalUiJs` 环境（loginUi 的 `<js>` / viewName）**不 put `java`**，所以 `loginUi` 里
读线路池/测速结果一律用 `cache.get/put` 与 `source.getVariable/putVariable`，
不要用 `java.ajax`。而 **action 环境**才有 `java`（被覆盖成 SourceLoginJsExtensions）。

### 运行时数据存 cache，避开 variable 的 `server` 耦合
v8 的 `server` 存在 `source.getVariable()` 的 JSON 里。登录面板的线路池、测速 ms、发布页 URL
若也塞进同一个 variable JSON，容易与 `setSite`/`began()` 互相覆盖。
本次全部改用 `cache`：

```
rrssk_speed_hosts  线路池 JSON 数组
rrssk_ms_<label>   每条线路测得延时（'865ms' / '超时'）
rrssk_best         最快线路文本
rrssk_pub          发布页输入框内容
rrssk_mb_last      发现页上页首条指纹（自然终止用）
rrssk_search_ts    上次搜索时间戳（节流用，存 source.get 键空间）
```

### 登录面板配方（本次 53 行，各按钮各阶段 Toast）
```
[text  发布页网址]  (name 作键，viewName 为单引号字面量提示)
[📥一键获取网址路线] [⚡测试全部延时]
[🔍检查登录状态]     [📍查看当前]      [⚙恢复默认]
[🔄重建发现按钮]     [🌐状态]          (viewName JS 表达式动态读 server+最快线路)
[各网站 × 45]        setSite('https://...') + viewName 动态读 rrssk_ms_<label>
```

各阶段 Toast：`⏳正在切换… → ✅已切换`/`❌失败`；
`📥正在读取发布页输入框… → 📥正在抓取发布页并解析… → 📥解析完成新增 N 条 → ✅线路池 a→b`；
`⚡开始测速 → ⚡共 N 条并发测速中 → ⚡测速进度 x/N → ✅完成 ok/N 最快 X → ℹ️延时已写入按钮 → 正在刷新面板`；
`🔍正在检查登录状态 → ✅游客可读/⚠️人机验证/❌无响应`；
`🔄正在重建发现按钮 → ✅已重建`；`⚙正在恢复默认 → ✅已恢复`。

★ `checkLogin()` 对「游客可读」站也给出明确结论（首页字节数 + 是否含 WAF 验证码），
满足用户「如须登录需写检查登录状态按钮」——**不登录也要有状态反馈**，别只做空按钮。

### 测速通道（复用既有定式 + 断路器）
`java.ajaxAll(urls, true)` 双参 `skipRateLimit` 两版通吃；分批 10 条；
判活三判据 `code 200-399 + body.length>10000 + 排除 WAF/异常堆栈串`；
`r.raw().code()` / `r.callTime()` / `r.body()`（**raw 也是方法**，属性访问拿 undefined）。

★ 本次实测 45 线路全跑 = **30.8s**（个别死站 TLS reset 让整批卡 15s）。
加断路器 `RR_STOP_AT=12`（攒够 12 条活线即停）→ **3.4s**，且批次异常时把该批各按钮
写 `'超时'` 不留空白。分批进度 Toast 让用户知道没卡死。

---

## 4. 搜索节流与 UA（用户明确要求）

- **UA 生死线**：GoEdge WAF 对桌面 Chrome UA 返回 307 `/WAF/VERIFY/CAPTCHA`（`Verify Yourself` +
  `GOEDGE_WAF_CAPTCHA_ID`），移动 UA / 含 Legado 的 Android UA 放行。v8 的 `header` 已是 `@js:`
  JSON（Android 15 Chrome 142 wv + `x-requested-with: cn.mujiankeji.mbrowser`），**原样保留**，
  实测 mopbook 36802B 真实首页、无 WAF。
- **搜索间隔**：只在 `searchUrl` 的 `@js:` 开头做会话级 2600ms 节流
  （`source.get('rrssk_search_ts')` + `Packages.java.lang.Thread.sleep(wait)` 纯 JS 兜底）。
  **不设全局 `concurrentRate`** —— 它是整源级限速，会把 31 页分页目录拖成 31×2s≈60s 触发
  debug 假超时（书海阁 v 实测教训）。也不主动探测搜索频率，降低被风控概率。
- 今日 `signJs` 版本 `v=17-20261107`（DJB2 倒序 + env=40），v8 的「花括号配平取整段函数 +
  eval + 注入环境检测常量」逻辑实测仍算出非零签名 `4afa535b`，真实搜索 POST 302→find 20 条全绿。
  ★ 跨日类站点仍必须换日前后各验证一次（本次当日多次全链路，跨日待用户实测）。

---

## 5. 书源 URL 正则（用户明确要求）

```
^https?://(?:www\.)?(?:<45 域名>)\.com/book/[A-Za-z0-9]+(?:-\d+(?:-\d+)?)?\.html(?:[?#].*)?$
```

★ 本次新增 `(?:-\d+(?:-\d+)?)?`：覆盖章节页 `/book/ID-章.html` 与章内分页
`/book/ID-章-页.html`。旧正则只匹配详情页 `/book/ID.html`，虽然章节 URL 由目录直出不受
`bookUrlPattern` 限制，但用户明确要求正则规则，且带后缀的深链（换源/书架修复）应能匹配。
实测 45 站详情页/章节页/章内分页全 MATCH，`/list-4-1/` 与外域 `evil.com` 全 NO。

---

## 6. 交付与验证闭环

1. **66KB 大源走 LAN**：`POST http://192.168.10.7:1122/saveBookSource`
   （头 `x-legado-token`，单对象 JSON，`Content-Type: application/json`）→ `isSuccess:true`。
   MCP `save_source` 内联上限约 19KB，绝不能传大源（会随机截断损坏）。
2. **回读逐字段比对**：`get_source` / LAN `/getBookSource?url=` → 26 字段 0 差异
   （仅 `respondTime` 被 `check_source` 改写，属正常）。
3. **App 内 Rhino 编译校验**：`new Function(字段JS)` 编译 4/4 通过（本地无 node，
   直接用书源绑定的 Rhino 更贴近真实运行环境）。
4. **MCP 全链路实测**：
   - 默认 kelexs：搜索「斗破苍穹」20 条 → 252 章 → 正文 2 页
   - mopbook：`++book/B469.html` → 62 章（密钥兜底重建成功）→ 正文
   - mopbook：`::list-4-1/` → 28 本 → 289 章/3 页 → 正文
   - mopbook：`::rank.html` → 51 本 → **3084 章/31 页** → 正文
   - mopbook：`::list-4-20/` 28 本；`::list-4-21/` 自然终止 0 条
   - shuhaoxs：`::list-4-1/` → 20 本 → 140 章 → 正文
   - 搜索（mopbook 中转 00PB）→ 20 条 → 252 章 → 正文
   - 反向验证：server=shuhaoxs 时访问 mopbook 发现页仍 51 本（v9.1 修复生效）
   - `check_source` 通过 1/1
5. **登录面板**：53 行、状态栏 `🌐 当前 mopbook.com · 最快 shuxiangdzs 787ms`、
   `mopbook 865ms` / `shuhaoxs 844ms` 按钮文案、检查登录状态返回「游客可读」、
   一键获取（空发布页）保留 45 条内置线路、测速断路器 3.4s。

---

## 7. 可复用清单（下次给聚合源加线路照抄）

- [ ] **先 diff 现有 hosts/模板/正则**，确认哪些站「已存在只是故障」，避免重复新增
- [ ] 新站抓 4 页：首页（中转/UA/WAF）、分类页（真列表容器 + 跨页 diff）、详情（og/密钥JS/data-aid）、章节（正文/下一页）
- [ ] `bookUrlPattern` 加域名 + 覆盖 `-章` / `-章-页` 形态；排除分类页与外域
- [ ] `jsLib`：`HOST_TEMPLATE_MAP` 加一行；`TEMPLATES` 加模板
  （**模板值可写 `@js:` 规则**，外层双层解析链零改动）
- [ ] 列表 `@js:` 一律返回 `java.util.ArrayList`（E 版），字段一律 `@js:` + `String(result)`
- [ ] 翻页终止用站点自身 `next` + 内容指纹，**禁止写死页数**
- [ ] `ruleExplore` 域名键改 `EX_HOST(baseUrl)`（URL 自治），别用全局 `server`
- [ ] 搜索节流做在 `searchUrl` 内，**不设全局 `concurrentRate`**
- [ ] 登录面板运行时数据存 `cache`；输入框用 `name`；`viewName` 用 JS 表达式；
      `function login(){}` 必需；各阶段 Toast；检查登录状态按钮对游客站也给出结论
- [ ] 测速 `ajaxAll(urls,true)` 分批 10 + 断路器 12 + 批次异常写「超时」
- [ ] 大源 LAN 落库 → 回读逐字段 → Rhino 编译 → `debug_source` 全链路（含**反向验证组**）→ `check_source`
- [ ] 提醒用户在官版 + legado-E 真机实测（跨日签名需换日前后各一次）
