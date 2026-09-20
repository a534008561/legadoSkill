# 案例：hanime1.me 视频书源 → legado-E 兼容版（v3.14E）

> 日期：2026-09-21　｜　站点：`hanime1.me`（CF 托管，成人向视频聚合）
> 成品：`hanime1_E兼容版_www.hanime1.me.json`（80KB）　｜　原源：`🌸 hanime1`（v3.14，保持不变）
> 方法论文档：[方法-legadoE兼容改造实战](../references/方法-legadoE兼容改造实战.md)

---

## 一、用户报障

「🌸 hanime1」在 **legado-E**（Luoyacheng/legado-E，"阅读Sigma"）上**登录界面打不开**（空白）。

## 二、根因（E 版源码实锤）

```kotlin
// legado-E: ui/login/SourceLoginDialog.kt
val loginUi = source.loginUi()          // → BaseSource.loginUi()
// legado-E: data/entities/BaseSource.kt
fun loginUi(): List<RowUi>? = GSON.fromJsonArray<RowUi>(loginUi)...
// legado-E: data/entities/rule/RowUi.kt
data class RowUi(var name: String = "", var type: String = "text",
                 var action: String? = null, var style: FlexChildStyle? = null)
```

原源 `loginUi = {"version":2}` → **`fromJsonArray` 解析对象失败 → 返回 null → 面板无 UI**。
E 版**没有** `isLoginUiV2()`、**没有** `<js>` 动态 loginUi、`RowUi` 只有 4 字段、只渲染 `text/password/button`。

## 三、连带发现的 12 处 E 版不兼容

| # | 原写法 | E 版行为 | 兼容写法 |
|---|---|---|---|
| 1 | `loginUi={"version":2}` | 面板空白 | **V1 数组 37 行** |
| 2 | 按钮 action `return '...'` | 返回值被 `runCatching` 吞 → 无反馈 | action 内 `java.longToast()` |
| 3 | `login()` 读 `result` | E 版 ✓ 按钮**不注入 result** | `getLoginInfoMap()` 兜底 |
| 4 | `author:'@js:String(result.artist\|\|'')'` | NativeObject 走**键名直取** → undefined → 条目被丢 | `author:'artist'`（纯键名） |
| 5 | `bookUrl:'@js:H1BU(String(result.v))'` | 同上 | 条目内预生成 `u` 字段 → `bookUrl:'u'` |
| 6 | `coverUrl/kind` 用 `@js:` | 同上 | 条目内预生成 → 纯键名 |
| 7 | `ruleBookInfo.intro` = useweb 面板 | E 版 `tvIntro.text=...` **无 useweb** → 显示源码 | 纯文本摘要 |
| 8 | `cookie.removeCookie(u,k)` | E 版 `CookieStore` 无两参重载 | `rmck()` 双通道 |
| 9 | `Jv.get(s,null,20000)` | E 版 `get` 仅 2 参 | `try{3参}catch{2参}` |
| 10 | `java.copyText/refreshBookInfo/openVideoPlayer` | E 版**不存在** | 已有 `try/catch`（降级提示） |
| 11 | 依赖 `{"dnsIp":...}` | E 版 `UrlOption` 无 dnsIp → DNS 污染站点直连必挂 | 文档指引：E 版用**代理**（`header` 的 `proxy`） |
| 12 | `bookSourceType=4` 期待播放 | E 版 `BookSourceType` 无 video → `BookType.text` | 无法修，如实告知（正文=直链文本） |

**E 版支持、无需改**：`exploreUrl`/`header` 的 `<js>`、`loginCheckJs`、`ruleBookInfo.init`、
`checkKeyWord`、URL 的 `{{}}` 二次求值、jsLib→loginUrl 作用域共享、`getVariable/setVariable`。

## 四、改动摘要

- `bookSourceUrl`：`https://hanime1.me` → `https://hanime1.me##E兼容版`（**新源，不覆盖**；`getKey()` 不同 → 变量/缓存自动隔离）
- `loginUi`：V2 → **V1 数组 37 行**（31 按钮 + 6 输入框，`style:{layout_flexBasisPercent:1}`）
- `loginUrl`：25671B → 21326B（删 V2 骨架；追加 `H1V1(act,Jv,Sv,m)` 分发 + `login()` 双通道 + `rmck` + `h1uiSave`）
- `jsLib.H1CARDS(src,html)`：条目改 `{title,artist,v,u,cover,kind}`（`u` 含 dnsIp、`cover` 已 CDN 修复、`kind` 已拼接）
- `ruleSearch/ruleExplore`：6 字段 × 2 组 → 纯键名
- `ruleBookInfo.intro`：useweb → 纯文本摘要
- **逐字节不变**：`exploreUrl`/`header`/`loginCheckJs`/`searchUrl`/`bookUrlPattern`/`ruleToc`/`ruleContent`/`variableComment`

## 五、验证

| 项 | 结果 |
|---|---|
| 静态 `node --check`（19 个 JS 块） | 全过 |
| V1 契约（37 行 / type 白名单 / 31 action 全可编译 / 26 分支全覆盖） | 全过 |
| 导入回读逐字段 md5 | **28/29 一致**（差异仅 `customOrder` 自动排序号） |
| `check_source` | **通过 1/1** |
| 搜索「催眠」 | 59 条，字段全对 |
| 详情 407947 | 书名/作者/12标签/日期/集数/简介 ✓ |
| 目录 + 正文 | 2 章；`vdownload.hembed.com/407947-1080p.mp4?secure=...` |
| 发现页「最新上傳」 | 59 条 → 详情 → 目录 3P → `rsc.cdn77.org/408330-720p.mp4` |
| 原版回归对比（同词） | 搜索/详情/目录/正文字段**完全一致** |
| V1 面板契约 | `isLoginUiV2()=false`、`getLoginUiJs()=null` → **LT/E 都走 V1** |
| 按钮点击精确模拟（`evalJS(loginJS+"\n"+action)`+result） | 应用配置/清晰度/帮助/完成/登录(空)/保存(空)/复制(空) 全过 |
| 纯键名取值 + 旧 `@js:` 对照 | `title/artist/u/kind` 正确；`@js:String(result.artist)` → **undefined**（证实差异） |

## 六、环境事实（E 版可用性关键）

- 手机侧 DNS：`hanime1.com/.me/hanimeone.me` **全被污染**（解析到 Facebook/Dropbox IP），裸请求 15s 超时；
  带 `dnsIp` 返回 224KB 正常 → **LT 版靠 dnsIp，E 版无 dnsIp → 必须代理**
- `javchu.com` 未被污染但 **TLS 被 RST**（SSLHandshakeException）→ 不可作镜像
- E 版 `getProxyClient` 支持 `http://` `socks4://` `socks5://` ✓（面板【代理地址】+【🛜 代理:开/关】）

## 七、E 版能力边界（无法修复的部分）

| 功能 | LT | E |
|---|---|---|
| 搜索/发现/详情/目录 | ✓ | ✓（需代理） |
| 登录界面控制台 | ✓ | ✓ ← **本次修复** |
| 视频播放 | ✓ | ✗（无 `BookType.video`；正文=直链文本） |
| useweb 简介面板 | ✓ | ✗（降级纯文本） |
| 切P跟随（callBackJs） | ✓ | ✗ |
| dnsIp / 自定义 Hosts | ✓ | ✗（用代理） |

## 八、可复用点

1. **`##后缀` 建"同站第二源"** —— 安全、变量隔离、不覆盖原源
2. **V1 面板 + `H1V1(act,Jv,Sv,m)` 薄分发** —— 面板形态与业务逻辑解耦（逻辑全留原函数）
3. **`h1uiSave()` 把配置写进 `putLoginInfo`** → V1 输入框自动回填（V1 无 value 字段的唯一出路）
4. **列表内预生成计算字段** → 字段规则纯键名 → 两版通用（改动面最小）
5. **`rmck` / `get` 双通道 / 缺失 API 全 try** → 一次改造，两版通吃
6. **验证三层法**：静态契约 → LT 版真实实测 → E 版源码级契约核对 + 等价模拟
