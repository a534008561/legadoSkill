# 案例：hanime1.me 视频书源 → legado-E 兼容版（v3.14E）

> 日期：2026-09-21　｜　站点：`hanime1.me`（CF 托管，成人向视频聚合）
> 成品：`hanime1_E兼容版_www.hanime1.me.json`（91KB）　｜　原源：`🌸 hanime1`（v3.14，保持不变）
> 方法论文档：[方法-legadoE兼容改造实战](../references/方法-legadoE兼容改造实战.md)

---

## 一、用户报障与两次更正

1. 报障：**「🌸 hanime1」在 legado-E 上登录界面打不开**（空白）。
2. 用户更正①：**"legado-E 也支持详情页简介 useweb 的，用回原版 useweb 简介"** → 已改回（未降级）。
3. 用户新增②：**"在登录界面增加选择域名的按钮"** → 已加 4 个一键选域名按钮 + 当前配置回显。

## 二、根因（E 版源码实锤）

```kotlin
// legado-E: ui/login/SourceLoginDialog.kt —— 只认「数组」
val loginUiStr = source.loginUi ?: return
rowUis = loginUi(loginUiStr)          // → GSON.fromJsonArray<RowUi>(json)
// ★ 没有 isLoginUiV2()；LT 版的 {"version":2} 在这里解析失败 → 面板空白
```

原源 `loginUi = {"version":2}`（LT 版 V2 面板格式）→ E 版 `fromJsonArray` 解析对象失败 → **面板无 UI**。

## 三、★ 最大的坑：拉源码用错分支

最初用 **`master`** 分支拉 `Luoyacheng/legado-E` 源码 → 拿到的是**旧版**，得出 8 项**错误结论**：

| 我误判（基于 master） | 实际（main 分支） | 证据 |
|---|---|---|
| E 版不支持 useweb/usehtml | **支持** | `BookInfoActivity`: `if (intro?.startsWith("<useweb>")) { WebViewPool.acquire(this) }` |
| E 版无 onButtonClick | **有** | `BookInfoViewModel.onButtonClick`: `SourceLoginJsExtensions(activity, source)` |
| E 版 BookSourceType 无 video | **有 video=4** | `BookSourceType.kt` / `BookType.kt` |
| E 版 UrlOption 无 dnsIp | **有 dnsIp** | `AnalyzeUrl`: `dnsIp → customIp[urlNoQuery]` |
| E 版无 openVideoPlayer | **有** | `JsExtensions:302` |
| E 版 get/head/post 仅 2 参 | **3 参**（带 timeout） | `JsExtensions:483/487` |
| E 版 RowUi 仅 4 字段、无 select/toggle | **7 字段，有 select/toggle** | `RowUi.kt`（含 chars/default/viewName） |
| E 版无 `<js>` 动态 loginUi | **有** | `onFragmentCreated`: `evalUiJs(codeStr)` |

**关键差异**：`SourceLoginDialog.kt` master=7.7KB vs **main=34KB**。
**发现手段**：GitHub code search 搜 `"useweb>"` 命中 `BookInfoActivity.kt`，但本地拉的文件里没有
→ 立刻回头查 `GET /repos/Luoyacheng/legado-E` → **`default_branch = main`**（不是 master）。

## 四、真正必须改的只有 2 件事（+ 4 项防御性兼容）

| # | 原写法 | E 版行为 | 兼容写法 |
|---|---|---|---|
| **1** | `loginUi={"version":2}` | **面板空白** | **数组 43 行**（含一键选域名按钮） |
| **2** | `author:'@js:String(result.artist\|\|'')'`、`bookUrl:'@js:H1BU(...)'`、`coverUrl/kind` 用 `@js:` | NativeObject 走**键名直取** → undefined → 条目被丢 | 条目内预生成 `{title,artist,v,u,cover,kind}` + 字段**纯键名** |
| 3 | 按钮 action `return '...'` | 返回值被 `runCatching` 吞 | action 内 `java.longToast()` |
| 4 | `login()` 读 `result` | E 版 ✓ 按钮**不注入 result** | `getLoginInfoMap()` 兜底 |
| 5 | `cookie.removeCookie(u,k)` | E 版无两参重载 | `rmck()`（get→删键→setCookie） |
| 6 | `Jv.get(s,null,20000)` | E master 仅 2 参 | `try{3参}catch{2参}` |

**E 版支持、无需改**：`useweb/usehtml` 简介面板、`video=4`、`dnsIp`、`openVideoPlayer`、
`exploreUrl`/`header` 的 `<js>`、`loginCheckJs`、`ruleBookInfo.init`、`checkKeyWord`、URL 的 `{{}}` 二次求值。
**E 版两版都无**：`callBackJs` / `eventListener`（→ 正文切P跟随失效，字段保留无害）。

## 五、改动摘要

- `bookSourceUrl`：`https://hanime1.me` → `https://hanime1.me##E兼容版`（**新源，不覆盖**）
- `loginUi`：V2 → **数组 43 行**（37 功能行 + 6 行域名选择组）
  - 🌐 **选择域名**：`① hanime1.com` / `② hanime1.me` / `③ hanimeone.me` / `④ javchu.com`（点击即切换并写变量+回填输入框）
  - `🔍 查看当前域名/配置`：回显域名/hosts/代理/清晰度/CDN/封面/简介面板状态
- `loginUrl`：删 V2 骨架；追加 `H1V1(act,Jv,Sv,m)` 分发（含 `dom0~dom3`/`curcfg` 分支）+ `login()` 双通道 + `rmck` + `h1uiSave`
- `jsLib.H1CARDS(src,html)`：条目 → `{title,artist,v,u,cover,kind}`（`u` 含 dnsIp、`cover` 已 CDN 修复、`kind` 已拼接）
- `ruleSearch/ruleExplore`：6 字段 × 2 组 → 纯键名
- **`ruleBookInfo.intro` 保持原版 `@js:H1INTRO(...)`（useweb 实时面板，未降级）** ← 用户要求
- **逐字节不变**：`exploreUrl`/`header`/`loginCheckJs`/`searchUrl`/`bookUrlPattern`/`ruleToc`/`ruleContent`/`variableComment`

## 六、验证

| 项 | 结果 |
|---|---|
| 静态 `node --check`（19 个 JS 块） | 全过 |
| 面板契约（43 行 / type 白名单 / 31+4 按钮 action 全可编译 / 全部分发分支存在） | 全过 |
| 导入回读逐字段 md5 | **28/29 一致**（差异仅 `customOrder` 自动排序号） |
| `check_source` | **通过 1/1** |
| 搜索「催眠」 | 59 条，书名/作者/分类/封面/详情链接全对 |
| 详情 407947 | 书名/作者/12标签/日期/集数 + **intro 返回 `<useweb>` 面板** ✓ |
| 目录 + 正文 | 2 章；`vdownload.hembed.com/407947-1080p.mp4?secure=...` |
| 发现页「最新上傳」 | 59 条 → 详情 → 目录 3P → `rsc.cdn77.org/408330-720p.mp4` |
| **域名按钮实测**（eval_js 精确模拟点击） | ①→h1dom=hanime1.com；②→hanime1.me；③→hanimeone.me；④→javchu.com；回填值同步 ✓ |
| **查看当前配置** | 正确回显 域名/hosts/代理/720P/CDN开/封面内置/实时面板 ✓ |
| 原版回归对比（同词） | 搜索/详情/目录/正文字段**完全一致** |

## 七、环境事实（国内可用性）

- 手机侧 DNS：`hanime1.com/.me/hanimeone.me` **全被污染**（解析到 Facebook/Dropbox IP）→ 裸请求 15s 超时；
  **带 `dnsIp` 返回 224KB 正常** ✓
- E 版（main）**支持 dnsIp** → 用【🚀 测速选线】即可直连 ✓
  （E 版旧分支无 dnsIp → 那时需代理；本源同时支持【代理地址】+【🛜 代理:开/关】，两版通吃）
- `javchu.com` 域名未被污染，但 **TLS 被 RST**（SSLHandshakeException）→ 保留为可选域名（部分网络可能可用）

## 八、可复用点

1. **★拉源码先确认默认分支**（本次最大教训，见方法文档 §0）
2. **`##后缀` 建"同站第二源"** —— 安全、变量隔离、不覆盖原源
3. **数组面板 + `H1V1(act,Jv,Sv,m)` 薄分发** —— 面板形态与业务逻辑解耦
4. **按钮代替下拉做"选择域名"** + **「查看当前配置」按钮做状态回显**（V1 按钮名是静态文本）
5. **`h1uiSave()` 写 `putLoginInfo`** → 输入框自动回填（面板无 value 字段的唯一出路）
6. **列表内预生成计算字段** → 字段规则纯键名 → 两版通用（改动面最小）
7. **验证三层法**：静态契约 → LT 版真实实测 → E 版源码级契约核对 + 等价模拟
