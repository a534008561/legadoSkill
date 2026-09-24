# 禁漫天堂Pro（小说/漫画/视频三合一书源）案例

- 成品 JSON：同目录 `禁漫天堂Pro_三合一.json`（= App 内 v14，check_source 1/1）
- 方法论：`references/方法-小说漫画视频三合一书源详解.md`
- 站点：https://jmcomicui.net（发布页发布；实际线路由登录界面「🚀测速选线」动态选定，如 comic18j-hbd.space）
- 能力：漫画（含 COS片视频/单行本/同人/CG）+ 小说 + 视频；发现页下拉切换三形态；#前缀搜小说、!前缀搜视频；登录/解冻/收藏夹/收藏（useweb 面板三态+重复收藏识别+本地缓存）；CDN 切换；点作者芯片本源搜索
- 技术要点：统一 jmParseList / jmDetailInit / jmChapters / jmContent；book.type 动态设置；kind 头部=作者；jmAttr 显式判空；发布页测速选线；零双引号纪律
