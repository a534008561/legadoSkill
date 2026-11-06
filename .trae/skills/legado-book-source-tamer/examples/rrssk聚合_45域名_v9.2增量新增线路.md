# 案例：rrssk 聚合 v9.2（45 域名，新增 mopbook / 恢复 shuhaoxs）

- 成品：`rrssk_v9_2.json`（本目录同名案例 JSON，见技能库 examples）
- 书源名：`rrssk聚合`，`bookSourceUrl="rrssk聚合"`，`bookSourceType=0`
- 日期：2601107
- 适配：官版 `LegadoTeam/legado`(master) + `Luoyacheng/legado-E`(main)
- 经验文档：`references/方法-聚合源增量新增线路与发现页URL自治模板分发.md`

## 本次变更（相对 v8 44 域名）

| 项 | 内容 |
|---|---|
| 线路 | 新增 `https://www.mopbook.com`（猫扑小说）；`https://www.shuhaoxs.com`（书豪小说）v8 已在内，实测从 502 恢复 |
| 发现规则 | `TEMPLATES.mopbook`：分类页 `.rankList`（28 本/页）/排行首页 `div.picList`（51 本）双模板 + 内容级自然终止 |
| 规则分发 | `ruleExplore` 九字段 `GET('server')` → `EX_HOST(baseUrl)`（发现页 URL 自治，修跨站串模板） |
| URL 正则 | 加 `mopbook` + `(?:-\d+(?:-\d+)?)?` 覆盖章节页/章内分页 |
| UA | 沿用 v8 `@js:` 移动 UA（GoEdge 桌面 UA 弹验证码） |
| 搜索节流 | `searchUrl` 内会话级 2600ms（不主动探测频率、不设全局 concurrentRate） |
| 登录面板 | 53 行：发布页输入框 / 一键获取路线 / 测试全部延时 / 45 站点击切换 / 检查登录状态 / 查看当前 / 恢复默认 / 重建发现 / 动态状态栏；各阶段 Toast；延时 ms 写回各网址按钮 |
| 详情/目录/正文 | 零改动复用 v8 通用分支（mopbook 密钥 JS `class AESCrypt` 新格式兼容、`data-aid` option 分页、POST loadChapterPage、`.content@html`、章内分页） |

## 实测记录（MCP debug_source）

```
默认 kelexs  搜索「斗破苍穹」 → 20 条 → 252 章 → 正文 2 页
mopbook     ++/book/B469.html → 62 章（密钥重建） → 正文
mopbook     ::/list-4-1/      → 28 本 → 289 章/3 页 → 正文
mopbook     ::/rank.html      → 51 本 → 3084 章/31 页 → 正文
mopbook     ::/list-4-20/     → 28 本（末页照常）
mopbook     ::/list-4-21/     → 自然终止 0 条（不写死页数）
shuhaoxs    ::/list-4-1/      → 20 本 → 140 章 → 正文
搜索(00PB)  → 20 条 → 252 章 → 正文
反向验证    server=shuhaoxs 时访问 mopbook/rank.html → 仍 51 本（v9.1 修复生效）
check_source 通过 1/1
```

登录面板：状态栏 `🌐 当前 mopbook.com · 最快 shuxiangdzs 787ms`；
`mopbook 865ms` / `shuhaoxs 844ms`；检查登录状态 →「游客可读」；
测速断路器把 45 线路从 30.8s 降到 3.4s。

## 站点合约速查

- 两站全游客可读、无登录/注册/验证码/官方发布页（论坛 `ciyuankong.com`、求书站 `zhaoshu.la` 均非发布页）
- 搜索中转：`shuhaoxs → 000P.html`，`mopbook → 00PB.html`（rrssk.com 三段凭证链 + 每日轮换 signJs）
- 今日 signJs `v=17-20261107`（DJB2 倒序 + env=40），v8 花括号配平 eval 逻辑实测仍兼容
- 章节内分页 `/book/ID-章-页.html`，`text.下一页@href` 命中，末页「下一章」天然排除

## 交付

`POST http://192.168.10.7:1122/saveBookSource`（头 `x-legado-token`），
回读 `get_source` 26 字段 0 差异（仅 `respondTime` 被校验器改写）。

## 待用户真机确认

1. 官版 + legado-E 各打开登录面板，逐个点按钮看 Toast 与按钮文案刷新
2. 跨日（0 点前后）各搜一次，验证每日轮换签名端到端
3. 发现页翻到末页/超界页看自然终止
