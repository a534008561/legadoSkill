# 案例：🌙 书旗小说(APP接口)

- 成品：[书旗小说_APP接口.json](书旗小说_APP接口.json)（37KB 单对象，2026-11-04 稳定版）
- 方法文档：[方法-书旗App加密协议与UA白名单403伪装](../references/方法-书旗App加密协议与UA白名单403伪装.md)
- 参考开源项目：https://github.com/ch6vip/fqapp （`rust/src/upstream/shuqi`）
- 核心：2048 字节 keystream XOR + 纯 JS MD5 签名复现官方 App 加密口；目录/正文双链路；19 榜单 + 书库分类发现页；`searchUrl` 整条 `@js:` 动态签名
- 关键坑：UA 白名单 `okhttp/3.12.13` + headers 键名必须大写 `User-Agent` + 403/429 伪装成正常 HTML + `String(java.xxx())` 的 replace 重载歧义 + `tags` 字段是字符串 + `checkKeyWord`/`chapterList` 两必配
- 已知站点限制：完整长书名（如《大明：朕，崇祯，只想摆烂》）服务端 500 `finalPage`，**官方 App 同样搜不到**，请改搜作者或书名短片段；书源不做截短重试以免触发风控
- 验证：`check_source` 1/1 通过；`debug_source` 搜索「凡人修仙传」「斗破苍穹」+ 发现页 `rank=boyClick`/`rank=girlhot`/`fc=29` 全链路到正文；游客态无需登录
