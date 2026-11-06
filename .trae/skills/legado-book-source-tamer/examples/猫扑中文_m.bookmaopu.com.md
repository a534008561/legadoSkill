# 猫扑中文文学（m.bookmaopu.com）成品书源案例

> 2026-11-06 制作；适用 LegadoTeam/legado 官版 + Luoyacheng/legado-E；MCP 调试 + LAN 直存闭环，check_source 通过 1/1。
> 成品源见同目录 `猫扑中文_m.bookmaopu.com.json`；技术总纲见 [references/方法-猫扑中文字符流硬切分页与双模板正文.md](../references/方法-猫扑中文字符流硬切分页与双模板正文.md)。

## 站点契约

| 项 | 值 |
|---|---|
| 主域 | `https://m.bookmaopu.com`（杰奇 CMS 换皮，UTF-8） |
| UA | 必须移动 UA（内置 Android 14 + Chrome/124）；旧安卓 4.4/桌面 Chrome UA 被 CF WAF 403 |
| 搜索 | `POST /page/search.html`，body `type=articlename&searchkey={{key}}`，单次 30 条；翻页依赖 PHPSESSID 会话态，只取第一页 |
| 详情 | `/书ID.html`：`.xx li` 第 0/1/2/3/4 行 = 分类/作者/状态/时间/最新章节 |
| 目录 | 单页全量（4879 章实测），`class.zxjz.-1@tag.li` 取倒数第 1 个 zxjz 区 |
| 章节 | `/书ID/章ID/`，章内分页 `/书ID/章ID/N.html` |
| 发现 | 9 分类 `?page=N` + 排行 `/top.html` + 完本 `/news.html` |
| 登录 | 全游客可读，未配登录 UI；无发布页/多线路 |
| 限速 | `concurrentRate: 1/500`（用户要求不主动探测搜索频率） |

## 三个核心难点

1. **正文分页是字符流硬切**：切点落在句中（「现在正」+「是使用此物的最佳时期」），连 HTML 标签都被切半（页尾孤立 `<`、页首 `/p>`）。官版 `nextContentUrl` 以换行拼接必然断句，且末页 next 指向目录页会多抓噪声 → 改用 `ruleContent.content` 的 `@js` 自抓分页、`parts.join('')` 无缝拼接，翻页判据双锚 `/bookId/chapId/` + `/N.html`。
2. **站内两套正文模板**：新书 `<p>` 段落、老书 `<br><br>` 分隔（末页带会被跨页切断的 `div align=center` 维护提示块）→ 清洗必须放在 join 之后。
3. **封面双路径分流**（用户两轮反馈纠正）：新路径 `/uploads/images/<ID>s.jpg` 是真封面（8/8 + 4/4 全 200），旧路径 `/uploads/<6位日期>/<hash>.jpg` 全 404（0/21，带完整浏览器头也 404，非防盗链），空 src 靠站点 onerror 兜底（App 不执行 onerror）→ 三处 `coverUrl` 共用 `@js`：列表环境 `result` 是 jsoup Element（从 `result.parent()` 取兄弟 `li.tjimg img`），详情环境 `result` 是整页 HTML 字符串（正则取 `.xsfm img src`），有效真封面绝对化、旧死链/空回退 `/static/images/nocover.jpg`。

★方法论教训：第一轮只抽样旧路径 21 张全 404 就断言「全站封面已死」并统一兜底图，导致「怎么全是同一副图」——**一组样本全灭 ≠ 总体全灭，必须补反向验证组（深分页/PC 推荐位/详情页）覆盖所有路径形态**。

## 验收记录

- `debug_source` 搜索「全民领主 / 斗破苍穹 / 长生修仙」→ 详情 → 目录 → 正文全链路通过；
- 发现页 `::/2.html?page=1/2/5`、`::/top.html` 全链路通过；
- `eval_js` 跑保存后的正文规则全文：新书 `<p>` 模板 3 页 3350 字、老书 `<br><br>` 模板 3 页 2577 字，均零广告/零残标签/零断句；
- 封面：`1366667` 详情 → `167033s.jpg`；`/2.html?page=5` 4 本真封面各自返回、旧路径/空 src 回退 nocover，4 张逐一 `curl -I` 全 200 image/jpeg；
- `check_source` 通过 1/1；LAN `/saveBookSource` + `/getBookSource` 字节级回读闭环。
