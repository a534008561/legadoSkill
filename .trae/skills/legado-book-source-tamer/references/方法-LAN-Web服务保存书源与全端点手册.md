# 方法 - LAN Web 服务：保存书源与全端点手册（书源交付/联调最强通道）

> 依据：LegadoTeam 官方源码 `app/src/main/java/io/legado/app/web/HttpServer.kt` 全量核对（2026-10-20），并在用户真机（legadoT，局域网）实测验证。
> **定位纠正**：这个 Web 服务**远不止"保存书源"**——它是沙盒/PC 脚本与真机 App 之间的完整联调 API：保存/删除/回读书源、订阅源、替换净化规则，批量校验书源，拉 HTTP 日志取证，读书架/目录/正文，测替换净化规则。书源制作的全流程（交付 → 闭环验证 → 取证 → 离线测试）都能走这一个 HTTP 通道。

---

## 0. 一句话总结

App「Web 服务」开启后，局域网内脚本直连真机：**保存书源（LAN 直存，秒落库，无需上传中转/深链/确认弹窗）→ GET 回读做 md5 字节级闭环 → 批量校验 → HTTP 日志取证 → 离线测净化规则**。

## 1. 通道选择决策树（书源交付用哪个通道）

| 场景 | 首选通道 | 说明 |
|---|---|---|
| 书源 >19KB（MCP save_source 内联上限） | **LAN 直存** | 无 dpaste 限频/封IP/429 误诊、无深链确认弹窗依赖 |
| 用户没点深链确认弹窗（HTTP 200 已下载但未落库） | **LAN 直存** | 秒落库 + 立刻 GET 回读闭环 |
| 书源 <19KB 且 MCP 可用 | MCP `save_source` | 快；但手抄 15KB+ 必坏，大源禁手抄 |
| 无局域网（手机不在同一网段） | dpaste/uguu + 深链 | 深链需用户点确认弹窗才算落库 |
| **回读验证 / 取证 / 测净化** | **LAN GET/POST 只读端点** | MCP get_source 超 200000 字符截断；LAN 无截断 |

**结论：有 LAN 通道时，交付与验证都优先走 LAN。**

## 2. 开启与配置（App 侧）

- 入口：**我的 → Web 服务**，开启后显示 `http://<手机IP>:<port>`；默认端口 **1122**（`AppConfig.webPort`，PreferKey.webPort 默认 1122）。
- **令牌**：我的 → 其他设置 → **「Web 与 MCP 访问令牌」**（key=`jsSourceApiToken`；值 trim 后存私有 prefs `js_source_api_credentials/token`；空值=清除）。
- **「访问令牌保护」开关**（key=`jsSourceApiTokenRequired`，**默认开**）：开启时下表「受保护」端点必须带令牌。文案原文："开启时 Web 书源与 MCP 接口必须提供令牌；仅在可信网络中关闭"。

## 3. 认证：x-legado-token（★本轮踩坑实锤）

- **请求头名称 = `x-legado-token: <令牌>`**（源码 `BookSourceController.kt:23`，常量 `JS_SOURCE_TOKEN_HEADER`）。
- 头名大小写不敏感（源码 `header(name)` 用 `equals(ignoreCase=true)` 遍历匹配）。
- 比对是常量时间比较（`MessageDigest.isEqual`），**令牌值必须逐字符一致**（不能只发前缀）。
- **失败根因复盘（我第一版翻车）**：发的是 `token: a7894563` 头 → 返回 `Web 书源访问令牌未配置或不正确`。`token:` 头、`?token=` 查询参数、`Authorization` 头**全部无效**。报这个错先查头名是不是 `x-legado-token`。
- **不需要令牌的端点**：普通 GET 读写（`/getBookSource`、`/getBookSources`、`/getBookshelf`、`/getChapterList`、`/getBookContent`、`/getRssSources`、`/getReplaceRules`、`/getJsSourceApiTokenRequired`、`/cover`、`/image`）；需要令牌的见 §4 表格。

## 4. 全端点清单（源码逐行核对）

响应统一结构（`ReturnData`）：`{"isSuccess": bool, "errorMsg": string, "data": ...}`，HTTP 状态码恒 200（错误也在 body 里），**判断成败永远看 `isSuccess`**。列表 >3000 条走 chunked 传输。

### 4.1 POST 写操作（body=`postData`）

| 端点 | 功能 | 认证 | body 格式（实测） |
|---|---|---|---|
| `/saveBookSource` | 保存**单个**书源 | ★受保护 | 书源 JSON **对象**（bookSourceName/bookSourceUrl 必填） |
| `/saveBookSources` | 保存**批量**书源 | ★受保护 | 书源 JSON **数组** `[{...}]`（name/url 空白的条目被静默跳过） |
| `/deleteBookSources` | 删除书源 | ★受保护 | 书源 JSON 数组（按 bookSourceUrl 删） |
| `/startBookSourceCheck` | 启动批量校验 | ★受保护 | `{"sources":[{书源对象(至少含bookSourceUrl+checkContent一致)}], "keyword":"校验关键词"}` |
| `/stopBookSourceCheck` | 停止校验 | ★受保护 | `{"sessionToken":"<start返回的token>"}` |
| `/saveRssSource` | 保存单个订阅源 | ★受保护 | 订阅源 JSON 对象 |
| `/saveRssSources` | 保存批量订阅源 | ★受保护 | 订阅源 JSON 数组 |
| `/deleteRssSources` | 删除订阅源 | ★受保护 | 订阅源 JSON 数组 |
| `/saveReplaceRule` | 保存替换净化规则 | ★受保护 | ReplaceRule JSON 对象 |
| `/deleteReplaceRule` | 删除替换规则 | ★受保护 | ReplaceRule JSON 对象 |
| `/testReplaceRule` | **离线测净化规则**（不改数据） | ★受保护 | `{"rule":{ReplaceRule对象}, "text":"待处理文本"}` → data=处理后文本 |
| `/saveBook` | 保存书籍信息 | 免 | Book JSON |
| `/deleteBook` | 删除书籍 | 免 | Book JSON |
| `/saveBookProgress` | 保存阅读进度 | 免 | BookProgress JSON |
| `/addLocalBook` | 上传本地书籍 | 免 | multipart：`fileName` 参数 + `fileData` 文件 |
| `/saveReadConfig` | 保存 web 阅读配置 | 免 | 配置 JSON（存 CacheManager webReadConfig） |
| `/saveJsSource` | 保存 JS 源 | 特殊 | 见 §8（另设 Content-Type/长度约束） |
| `/openLegacyReview` `/runLegacyReview` | 书评（web 端遗留） | ★受保护 | — |

**★body 格式两大坑（本轮实测）**：
1. `Content-Type` **必须 `application/json`**：发 `application/x-www-form-urlencoded` 时 NanoHTTPD 把 body 当表单解析，`files["postData"]` 取不到 → 端点收到 null → 报"数据不能为空"（实测 `/testReplaceRule` 两种 CT 对照实锤）。
2. **数组 vs 对象不能搞错**：`/saveBookSources` 吃数组（`GSON.fromJsonArray`），发单对象会"转换源失败"；`/saveBookSource` 吃单对象。
3. `/testReplaceRule` 的 rule 里 **`isRegex` 必须显式 true**（false 走普通字符串替换）且 text 键名是 `text` 不是 `content`。

### 4.2 GET 读操作（query 参数）

| 端点 | 功能 | 认证 | 参数 → 返回 |
|---|---|---|---|
| `/getBookSource` | 回读**单个**书源 | 免 | `?url=<bookSourceUrl>` → data=完整书源 JSON（**含全部字段，无截断**） |
| `/getBookSources` | 回读**全部**书源 | 免 | → data=书源数组 |
| `/getBookSourcesForManagement` | 书源+校验状态快照 | ★受保护 | `?urls=["url1","url2"]`(可选) → `{sources, states}` |
| `/getBookSourceCheckStates` | 校验会话状态 | ★受保护 | → `{running, sessionToken?, states}` |
| `/getJsSourceApiTokenRequired` | 查令牌保护开关 | 免 | → data=true/false（**排障第一步**） |
| `/getHttpLogs` | HTTP 日志摘要 | ★受保护 | `?limit=N`（≤MAX_RECORDS）→ 最近 N 条脱敏日志 |
| `/getHttpLog` | HTTP 日志详情 | ★受保护 | `?id=<日志id>` → 单条详情（请求/响应正文各 8KiB 上限） |
| `/getBookshelf` | 书架全部书籍 | 免 | → data=Book 数组（按书架排序） |
| `/getChapterList` | 目录 | 免 | `?url=<bookUrl>` → 无缓存时自动触发 refreshToc |
| `/refreshToc` | 强制刷新目录 | 免 | `?url=<bookUrl>` → 重跑 ruleToc |
| `/getBookContent` | 正文 | 免 | `?url=<bookUrl>&index=<章序号>` → data=正文文本 |
| `/getReviewSummary` `/getReviewDetail` `/getReviewReplies` | 书评 | 免 | — |
| `/cover` | 封面缩略图 | 免 | `?path=<封面路径>` → PNG（84x112） |
| `/image` | 正文插图 | 免 | `?url=<bookUrl>&path=<图链>&width=N` → PNG |
| `/getReadConfig` | web 阅读配置 | 免 | → 配置 JSON |
| `/getRssSource` | 回读单个订阅源 | 免 | `?url=` → 完整订阅源 JSON |
| `/getRssSources` | 回读全部订阅源 | 免 | → 订阅源数组 |
| `/getReplaceRules` | 全部替换规则 | 免 | → data=规则 JSON 字符串 |
| 其余路径 | web 静态资源 | 免 | — |

### 4.3 WebSocket 路由（持续通讯）

| 路由 | 用途 |
|---|---|
| `/bookSourceDebug` | 书源逐步调试（等价 MCP debug_source 的底层） |
| `/rssSourceDebug` | 订阅源调试 |
| `/searchBook` | 聚合搜索 |

WebSocket 认证走 `sec-websocket-protocol` 双协议头（`legado, legado.token.<令牌>`），命令行场景一般用不到；调试用 MCP `debug_source` 即可。

## 5. 标准交付闭环（书源制作推荐流程）

```python
import json, urllib.request, urllib.parse, hashlib

BASE = 'http://192.168.10.4:1122'
TOK  = 'a7894563'   # App「Web 与 MCP 访问令牌」
HDR  = {'Content-Type': 'application/json', 'x-legado-token': TOK}

# ① 保存（LAN 直存，>19KB 无压力）
src = json.load(open('wenku8.json', encoding='utf-8'))
body = json.dumps([src], ensure_ascii=False).encode('utf-8')   # ★数组
req = urllib.request.Request(BASE + '/saveBookSources', data=body,
                             method='POST', headers=HDR)
r = json.loads(urllib.request.urlopen(req, timeout=15).read())
assert r['isSuccess'], r['errorMsg']

# ② 回读闭环（md5 字节级比对，等价 eval_js 回读但更快更全）
u = BASE + '/getBookSource?url=' + urllib.parse.quote(src['bookSourceUrl'], safe='')
back = json.loads(urllib.request.urlopen(u, timeout=10).read())
assert back['isSuccess']
got = back['data']
for k in ('jsLib', 'exploreUrl', 'ruleContent'):
    a = hashlib.md5(str(src.get(k) or '').encode()).hexdigest()
    b = hashlib.md5(str(got.get(k) or '').encode()).hexdigest()
    assert a == b, f'{k} 不一致: {a} vs {b}'
print('落库验证 PASS')
```

要点：
- **回读闭环比 eval_js 回读更强**：一次拿全字段、无 200000 字符截断、不占 MCP 会话（MCP 与 shell 并行易 "Session not found"）。
- `respondTime`/`lastUpdateTime` 保存后会被 App 刷新，比对时排除这两个字段。
- **修复字段级差异**：LAN 返回的是 App 实际存储版本——本地 md5 对不上时，**以 LAN 回读为准**反推传输层吞了什么（对比 MCP save_source 手抄丢字段，LAN 直存用 `json.dumps` 组包零失真）。

## 6. 书源制作各阶段怎么用这套端点

| 阶段 | 用法 |
|---|---|
| 交付 | `/saveBookSources` 直存（§5） |
| 验证 | `/getBookSource` md5 闭环；大源绕开 MCP get_source 截断 |
| 批量体检 | `/startBookSourceCheck`（keyword 可设）→ 轮询 `/getBookSourceCheckStates` → `/getBookSourcesForManagement` 取结果 |
| 取证 | `/getHttpLogs`/`/getHttpLog`：App 内所有书源请求的脱敏日志（URL/状态码/耗时/异常），**不占 MCP 会话**，可与 eval_js 并行排查 |
| 离线测净化 | `/testReplaceRule`：把拟写入 replaceRegex 的规则对样例文本先试跑（isRegex 记得 true） |
| 换净/灰度 | 新旧版书源并存时 `/deleteBookSources` + `/saveBookSources` 原子替换 |
| 阅读验证 | `/getChapterList`/`/getBookContent` 直接验证目录与正文产出（书架里的书） |

## 7. 排障速查

| 现象 | 原因 → 解法 |
|---|---|
| `Web 书源访问令牌未配置或不正确` | 头名不是 `x-legado-token`（查 §3）；或令牌值不一致；或 App 端「访问令牌保护」开着但没配令牌（先 `/getJsSourceApiTokenRequired` 探） |
| `数据不能为空`（明明发了 body） | Content-Type 不是 `application/json`（form-urlencoded 时 postData 读不到） |
| `转换源失败` | 对象/数组用错（saveBookSources 要数组）；或 JSON 被手抄破坏（用 json.dumps 组包） |
| GET 回读 404/连接拒绝 | Web 服务没开 / 手机 IP 变了 / 端口非 1122 / 不在同一网段 |
| `/startBookSourceCheck` 报 `书源尚未保存或设备版本已变更` | 提交的 sources 必须与 App 内已存版本 `checkContent` 一致——**先 save 再 check**，或先 getBookSources 拿最新版原样提交 |

## 8. /saveJsSource 简述

JS 单文件源专用端点，约束最严：Content-Type 必须 `text/plain`、必须有 Content-Length（0~1MiB）、认证同 §3、30s 超时。普通书源用 `/saveBookSource(s)` 即可，别混用。

## 9. 与其他交付通道对照（历史经验归位）

| 通道 | 限制 | 何时用 |
|---|---|---|
| **LAN Web 服务** | 需同网段 + Web 服务开启 + 令牌 | **默认首选**：直存/回读/校验/日志/测净化 |
| MCP save_source | 内联 ~19KB 上限；手抄必坏；串行 | 小源快速保存 |
| dpaste + 深链 | 限频 1req/s、封 IP、深链需用户点确认、429 会误诊为"XML语法错误" | 无 LAN 时 |
| uguu.se + 深链 | 同上（dpaste 封 IP 时的替代） | 无 LAN 且 dpaste 不可用 |

## 10. 避坑清单 K1~K12

- K1 认证头是 `x-legado-token`，不是 `token`/`Authorization`/查询参数。
- K2 POST 的 Content-Type 必须 `application/json`，form-urlencoded 会让 postData 读不到（报"数据不能为空"）。
- K3 `/saveBookSources` 吃数组、`/saveBookSource` 吃对象，搞反报"转换源失败"。
- K4 所有响应 HTTP 200，**成败只看 body 的 `isSuccess`**。
- K5 回读比对排除 `respondTime`/`lastUpdateTime`（App 自动刷新）。
- K6 LAN 回读是 App 实际存储版本，**字段对不上以它为准**反推传输层问题。
- K7 `/testReplaceRule`：键是 `text` 不是 `content`；rule.isRegex 显式 true 才走正则。
- K8 校验前必须先 save（checkContent 快照一致性校验），否则报"书源尚未保存或设备版本已变更"。
- K9 受保护路由清单里**没有** `/getBookSource(s)`——回读验证不需要令牌，但带上也无妨（统一 HDR 最省心）。
- K10 `/getHttpLogs` 与 MCP 的 `get_http_logs` 是同一个内存日志池（≤50 条），LAN 版可带 `limit` 且不占 MCP 会话。
- K11 令牌保护开关默认开；局域网可信时用户可关（开关 summary 原文），但**建议保持开**，脚本统一带头即可。
- K12 webPort 可改（默认 1122），IP 会随网络变——脚本把 BASE/TOK 提成常量，换网络只改一处。

## 11. 用户环境速记（2026-10-20）

- BASE=`http://192.168.10.4:1122`，令牌=`a7894563`（用户提供的 LAN web 服务通道，下次优先用）。
- 已实测通过：`/saveBookSources`（wenku8 15.6KB）、`/getBookSource` 回读 md5 闭环、`/getJsSourceApiTokenRequired`、`/testReplaceRule`、`/getHttpLogs`。

---

*本文为书源交付通用经验，蓝本=轻小说文库 wenku8 书源 LAN 直存交付（2026-10-20）。源码依据：HttpServer.kt（路由/认证/保护清单）、BookSourceController.kt（令牌常量与校验）、BookSourceCheckController.kt（校验会话）、ReplaceRuleController.kt（testRule）、AppConfig.kt（webPort/令牌存储）。*
