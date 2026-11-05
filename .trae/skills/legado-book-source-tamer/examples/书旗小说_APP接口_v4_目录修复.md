# 案例：🌙 书旗小说(APP接口) v4 — H5 目录按书缺失修复

- 成品：[书旗小说_APP接口_v4_目录修复.json](书旗小说_APP接口_v4_目录修复.json)（39KB 单对象，2026-11-05）
- 上一版：[书旗小说_APP接口.json](书旗小说_APP接口.json)（v3 多线路兼容，保留不覆盖）
- 方法文档：[方法-书旗H5目录按书缺失与openapi章节列表降级](../references/方法-书旗H5目录按书缺失与openapi章节列表降级.md)
- 报障：高位禁锢 / 两个爸爸一萌娃 / 总裁他非让我拖家带口住豪宅 / 广青刀三本，搜索+详情正常但目录空（TocEmptyException）
- 根因：这批书 H5 `/chapter?bid=` 返回 55 字节 `location.replace` 重定向、封面页空壳、旧 `chapterinfo` 降级 `data:null` 且章节 ID 不连续
- 修复：`SQ_toc` 双通道——H5 主通道原位保留；失效时降级 `content.shuqireader.com/openapi/book/chapterlist`（bscpubKey+MD5 签名，卷数组展平取真 chapterId），chapterUrl 复用既有免签 CDN 正文链路；删除伪递推降级
- 卷名规则（用户明确要求）：站点本身分卷(≥2卷且有卷名)才在**每卷第一章**标一次【卷名】，单卷/无卷名不加，章名已含卷名不重复；其余章标题原样
- 验证：check_source 1/1；3 本报障书 debug 全链路到正文（205/216/269 章）；广青刀 3 本 + 历史同症状书目录/末章正文全绿；《凡人修仙传》2451 章 H5 主通道零回归且仅 4 个卷首章带卷名
- 交付：LAN `POST /saveBookSource` 落库，get_source 回读 28/28 字段零差异
