# 方法-订阅源分辨率档位/视口懒加载与 Legado-E 分支辨析（261109 ExHentai v3）

> 场景：以阅读 App「现在这个版本」(🅴ExHentai 订阅源 36 字段) 为基础，
> 增加「分辨率选择按钮」「正文缩略图懒加载」「完善分类页分页」，兼容 LegadoTeam 与 legado-E。
> 本文只记**本次新出现、此前技能库未掌握**的机制与坑，全部有真机/源码实锤。

---

## 1. ★★★ E 版仓库默认分支是 `main`，不是 `master`（重大误判纠正）

- **症状**：我拉 `raw.githubusercontent.com/Luoyacheng/legado-E/master/.../RowUi.kt`，
  得到 457B 的缩减版 `RowUi`（只有 text/password/button），据此判定「E 版不支持 select/viewName/chars」，
  把分辨率选择退化成「V1 纯 button 循环切换」。
- **用户纠正**：「E版支持select，例如（🍥哔咔漫画）书源登录界面」。
- **实锤**：`GET https://api.github.com/repos/Luoyacheng/legado-E` → `default_branch=main`（pushed_at 2026-08-01）。
  `main` 分支 `RowUi.kt` = 1159B，**含 `Type.toggle` / `Type.select` / `chars` / `default` / `viewName` / `style`**；
  `main` 的 `SourceLoginDialog.kt` = 34267B，**与官方版同尺寸**，`Type.select` 分支齐全。
  `master` 是残留旧分支（拉得到但内容陈旧）。
- **实例佐证**（MCP `get_source` 读「🍥哔咔漫画」https://manhuabika.com）：
  `loginUi` 用 `<js>` 动态数组，含
  `{"name":"图片清晰度","type":"select","action":"setQuality()","chars":["低清","高清","超清","原图"],"default":def}`。
- **铁律**：**查 E 版源码一律用 `main` 分支**；`master` 会得到过时结论。
  通用化：拉 GitHub 源码前先 `GET /repos/{owner}/{repo}` 读 `default_branch`，别凭习惯猜 master/main。

## 2. ★★★ `select` 协议的 `action` 绑定与 `default` 语义（源码级）

`SourceLoginDialog.kt`（官方版与 E 版 main 一致）：

- `Type.select` 分支：`loginInfo[name] = char`（`char = loginInfo[name] ?: default ?: chars[0]`），
  `selector.setSelectionSafely(chars.indexOf(char))`；`onItemSelected` 里
  `loginInfo[name] = chars[position]` 后调 `handleButtonClick(source, action, name, false)`。
- **`default` 是纯字符串**（`chars.indexOf(default)` 直接比较），**不做 JS 求值**；
  写成 `"EH_default()"` 会被当字面量字符串，选中项落到 `chars[0]` 之外 → `indexOf=-1`。
- `handleButtonClick` → `source.evalJS("$loginJS\n$buttonFunctionJS"){ put("result", getLoginData(rowUis)) }`，
  `getLoginData` = `viewModel.loginInfo.toMutableMap().apply{ putAll(输入框值) }`
  ⇒ **action 里读 `result['控件name']` 即当前选中项**（哔咔实例读 `infoMap[...]` 亦可，两个通道都绑）。
- 已保存的选择由 `putLoginInfo(GSON.toJson(loginData))` 持久化，重开面板 `loginInfo[name]` 回显，
  与 `source.put('ehRes', k)` 是**两套存档** → 需 `EH_resCfg()` 三通道兜底
  （`source.get` 主存档 + `result/infoMap` 标签反查），否则面板显示 A 档、正文实际跑 B 档。
- `viewName` 长度 3..19 且首尾单引号 → 直接当文本；否则 `execute{evalUiJs(viewName)}` 异步求值。
  动态文字（如 `EH_resBtn()`）走后者，E 版 main 同样支持。

## 3. ★★★ 拼进 HTML `<script>` 的 JS 必须「零反斜杠」（真机 WS 抓出的真 bug）

- **症状**：v3 首版把 124 行懒加载脚本写成「Python 数组 → `json.dumps` → Rhino `join('\n')` →
  `.replace('__PEND__', JSON.stringify(...))` → 拼进 `<script>`」。
  本地 QuickJS `new Function` 编译 OK，但 **App 真机 Rhino WS 诊断 `scriptCompile=FAIL 字符串文字没有限制`**
  （Rhino 的「unclosed string literal」中文报错）。
- **根因**：`pickSrc` 正则里写了 `id=\"img\"`、`([^\"]+)`，`fetchOne` 写了 `',{\"headers\":'`，
  这些 `\"` 经过「Python 字符串 → JSON 数组元素 → Rhino 字符串常量 → HTML `<script>` 内联」
  **三层转义被吞掉一层**，最终脚本里引号配平被破坏。
  本地模拟（手工内嵌/QuickJS）因转义链不同，**抓不到这个错** —— 只有真机 WS 能抓。
- **修法（铁律）**：**拼进 `<script>` 的 JS 正文里一个反斜杠都不能有**：
  - 双引号用 `var Q=String.fromCharCode(34)` 运行时拼；正则用 `new RegExp(pat,'i')` 字符串构造，
    `pat='<img[^>]+id='+Q+'img'+Q+'[^>]+src='+Q+'([^'+Q+']+)'+Q`（零 `\"`）。
  - URL 选项 JSON 的 `{`/`}` 用 `String.fromCharCode(123)` / `(125)` 拼，不写 `,{...}` 字面里的转义引号。
  - 域名替换用 `String(u).split('exhentai.org').join('e-hentai.org')`，**不用 `\/` 正则**。
  - 数组换行用 `.join(String.fromCharCode(10))`，不写 `.join('\\n')`。
  - 构建脚本加自检：`assert all('\\' not in line for line in LAZY_LINES)`。
- **验收法**（比本地编译可靠）：临时在 `ruleContent` 末尾插诊断桩
  `var _sm=/<script>([\s\S]*?)<\/script>/.exec(h); new Function(_sm[1]); java.log('scriptCompile=OK')`
  → LAN WS 跑一次看日志 → **确认 OK 后删诊断桩重存正式版**（用户偏好：排查完必须重存正式版）。
  注意 WS `notPrintState=[10,20,30,40]` 会过滤正文 HTML，但 `java.log` 的诊断行会推出来。

## 4. ★★ E-Hentai 分辨率的真实控制链（不臆造）

- **站点真实表单** `GET /uconfig.php`（已登录）实拉：
  `xr` radio = `0`(checked,自动) / `1`(780x) / `3`(1280x) / `4`(1600x,disabled) / `5`(2400x,disabled)；
  `ts` radio = `0`(checked) / `1` / `2`；`<form id=profile_form method=post>` + `name=apply value=Apply`。
  与 TachiyomiSY `EhUConfigBuilder.kt`（`entry.ImageSize` AUTO/2400/1600/1280/980/780，`key="xr"`）交叉印证。
- **`POST /uconfig.php` body=`xr=3&ts=2&apply=Apply` → 返回含 `Settings were updated`**（真机实测），
  回读 `checked` 会变。★我做完对照后**立刻 POST `xr=0` 恢复零残留**（`final_checked=xr_0`），
  验证写操作必须可恢复，不能把用户账号设置改坏。
- **裸 Cookie 覆盖无效**：`Cookie: ...; uconfig=...; xres=1` / `xres=5` 三组对照，
  同一 `/s/` 页 body 与 `xres=1280` 图 URL **完全一致** ⇒ 服务端分辨率由账号 uconfig 决定，
  不是请求期 Cookie。**不能靠 header 注入改分辨率**，只能 POST uconfig 或客户端侧控画质。
- **`inline_set=ts_m` / `ts_l` 在 Compact(dm_l) 布局下无效果**：
  真机对照 `?inline_set=ts_m` 与 `ts_l` 的首页 `img style` 与详情页 `#gdt` 结构完全相同
  （`gt200` / `157x300` / 同一 sprite）⇒ 别把 `ts_*` 当「详情页缩略图分辨率开关」。
  真正影响客户端画质的是：①是否请求 `/s/` 单图页（出 `xres=1280` 中图）②是否用 250px sprite 缩略图。
- **定案**：分辨率档位做**客户端侧真实可控的组合**（首屏内联高清张数 0/6/15/25 +
  视口懒加载串行间隔 350~1000ms + 预取 margin 0~1800px），另给一个**用户主动点**的
  「⚙ 同步站点分辨率(xr/ts)」按钮 POST 写账号 uconfig（全阶段 Toast + 回读确认）。

## 5. ★★ 分类页分页：站点自身信号分层（不写死上限）

真机单次克制探测（不碰 `f_search`）：

| 分类 | 站点分页信号 | 规则处理 |
|---|---|---|
| 首页 `?` | `#unext href="https://exhentai.org/?next=GID"` | 原样跟随游标 |
| `?f_cats=1021` | `#unext href="...?f_cats=1021&amp;next=GID"` **自带筛选参数** | 必须原样跟随 + `&amp;`→`&`；丢参数就翻回全部分类 |
| `/watched` | `#unext href="/watched?next=GID"` | 跟随 |
| `/popular` | **无 `#unext` / 无 `table.ptb` / `?p=1/2` 与 `?p=0` 完全同页**（81 画廊一次给全） | 返回空 → 空列表自然终止，**不伪造下一页** |

- `ruleNextPage` 用 `@js:` 时 **`result` 是 HTML 字符串**（`getString` 结果），**不是 Elements**，
  只能用正则，不能用 `result.select()`（这是旧版已踩过的坑，本次复核）。
- 加固：解码 `&amp;`/`&#38;`；只放行 `exhentai.org|e-hentai.org`；
  与 `baseUrl` 相同则停（防回环）；限频/白屏页直接停（别把伪装错误页当「还有下一页」）。
- 符合用户既有偏好：**不写死页码上限**，站点以后加数据自动继续。

## 6. ★★ 风控合规（用户明确要求「不主动探测搜索访问频率」）

- 全程**没有请求 `f_search` 搜索接口**；连通性/分类/分辨率验证只打首页、`/uconfig.php`、
  `?f_cats=`、`/popular`、`/watched`、同一 `/s/` 页，且每次带 1.2~1.5s 间隔，共约 20 次必要请求。
- 源侧 `concurrentRate=1/800` 保持不变；正文 `/s/` 高清 `HD_BATCH=5` + 批间隔 `RES.gap`（档位 350~1000ms）；
  WebView 懒加载**串行** `setTimeout(pump,GAP)`，绝不整章并发。
- 「✅ 检查登录状态」按钮只单次 `java.ajax(EH_ajaxUrl('/'))` 打首页，不循环、不测频率。
- 「⚡ 测试各线路延时」每条线路各 1 次、间隔 800ms，Toast 明示「不频繁访问」。
- 站方对短时密集 `/s/` 敏感（约 24h 限频），档位 `HD_MAX` 克制在 0/6/15/25，不因「超清」拉到 60。

## 7. ★★ WebView 懒加载的双版本桥差异（源码级）

- **官方版** `ReadRssActivity`（`master`）：`initJavascriptInterface()` 注入 `WebJsExtensions` 为 `java`
  （有 `ajax/get/connect/post/toast/log`），另有 `source`/`cache`；`preloadJs` 经
  `shouldInterceptRequest` 以 `JS_INJECTION` 注入，`JS_INJECTION` 里 `const java=window.$nameJava`。
- **E 版** `RssJsExtensions` 是空壳（无 ajax），`ReadRssActivity` 也无 `WebJsExtensions` 注入。
- ⇒ **内联 `<script>` 不能假设 `java.ajax` 存在**：脚本里
  `hasJava=(typeof java!=='undefined'&&java!=null)` → 有桥才请求 `/s/` 高清；
  无桥时保留已带 `loading="lazy"` 的 250px 缩略图，由 WebView 原生懒加载承载，
  并 HUD 明示「原生懒加载(E版)」——**不是白屏、不是规则失效**。
- 官方版 `onPageFinished` 还会 `evaluateJavascript(injectJs)`；本源把懒加载放在正文 `<script>` 内，
  两版本都由 WebView 直接执行，不依赖 `injectJs`/`preloadJs`。

## 8. 交付闭环（本次实测数据）

- 成品 `/workspace/exhentai/exhentai_rss_v3.json`（95808B / 36 字段 / loginUi 30 行）。
- LAN `/saveRssSources`（body=数组）双端口落库：`1122`(LegadoTeam) + `1125`(E) 均 `isSuccess:true`；
  `getRssSources` 回读 **1122 差异 0 / 1125 仅 `enableReadRecord` 被 E 版 GSON 丢弃**（E 版本身无此字段，正常）。
- WS 验收：官方 1123 与 E 1126 均「列表大小25 / `?next=GID` 游标 / 内容页解析完成 / 异常计数 0」。
- 真机诊断桩：`V31DIAG scriptCompile=OK bs=false`（零反斜杠生效）/
  `outLen / need / hd / lazy / IO / res / hdmax / gap / margin` 全出，**确认 OK 后已删桩重存正式版**。
- 面板函数语义（App Rhino 模拟）：`EH_setRes` 把「高清·1280x」→`ehRes=2`，
  动态文字/状态函数正确，Toast 全阶段覆盖。
  ★用户后续要求「把分辨率切换按钮去掉，留下下拉框就行」⇒ 最终版**只保留 1 个 select 下拉**
  （29 行 loginUi），删除循环切换按钮与 `EH_toggleRes`/`EH_resBtn` 死代码；
  构建脚本加断言 `EH_toggleRes not in loginUrl`。
- 账号写操作可恢复：`POST xr=3` 验证后立刻 `POST xr=0` 还原，`final_checked=xr_0` 零残留。

## 9. 复用清单（下个订阅源直接照抄）

1. 查 E 版源码先读 `default_branch`（是 `main`）。
2. 下拉选择用 `select` + `chars` + 纯字符串 `default` + `action` 里读 `result[name]`。
3. 任何拼进 `<script>` 的 JS：**零反斜杠**，双引号用 `String.fromCharCode(34)`，
   正则用 `new RegExp(字符串)`，域名替换用 `split().join()`。
4. 落库前用「诊断桩 + LAN WS」验 `new Function(<script>内容)`，OK 后删桩重存。
5. 分类分页跟随站点 `#unext` 游标、解码 `&amp;`、保留筛选参数、无游标则空列表终止，不写死上限。
6. 服务端设置类写操作（POST uconfig）必须①用户主动点②全阶段 Toast③回读确认④验证后恢复原值。
7. 不碰 `f_search` 做频率探测；`/s/` 之流串行 + 间隔 + 批大小克制。
