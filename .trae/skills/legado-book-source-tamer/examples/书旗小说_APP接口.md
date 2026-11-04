# 案例：🌙 书旗小说(APP接口) v3

- 成品：[书旗小说_APP接口.json](书旗小说_APP接口.json)（40KB 单对象，2026-11-04 v3 多线路兼容版）
- 方法文档：[方法-书旗App加密协议与UA白名单403伪装](../references/方法-书旗App加密协议与UA白名单403伪装.md)
- 参考开源项目：https://github.com/ch6vip/fqapp （`rust/src/upstream/shuqi`）
- 核心：2048 字节 keystream XOR + 纯 JS MD5 签名复现官方 App 加密口；目录/正文双链路；`searchUrl` 整条 `@js:` 动态签名
- **发现页 v2**：`@js:` 结构化 53 行 = 6 分组标题（独占整行）+ 47 入口（17 有效榜单 + 书库 5 维 30 入口），全部 `&page={{page}}`，`bookList` 从 baseUrl 反解页码；逐个验活 47/47 全绿
- **多线路 v3**：实测能力矩阵后分池——`sqWeb`∈{www.shuqi.com, shuqi.com}（发现/详情/目录）、`sqCdn`∈{c1, c2.shuqireader.com}（正文 8 组合），所有 URL 动态跟随，旧书架跨线自愈；登录 UI 4 按钮按 H5/CDN 分工测速回填
- 关键坑：UA 白名单 `okhttp/3.12.13` + headers 键名大写 + 403/429 伪装正常 HTML + Java String replace 重载歧义 + `tags` 是字符串 + jsLib 块注释须整块剥离 + **备用域对未知 path 返回 200 首页伪装** + `java.sleep`/`S` 跨环境差异
- 已知站点限制：完整长书名服务端 500 `finalPage`，官方 App 同样搜不到，改搜作者或短片段
- 验证：`check_source` 1/1；`debug_source` 搜索 + 裸域发现 page=2 全链路到正文；换线（裸域+c2）全链路通过；游客态免登录
