# 案例：rrssk聚合（44 域名多站聚合 + 状态漂移修复 + 选站三件套）

> bookSourceName：`rrssk聚合` ｜ bookSourceUrl：`rrssk聚合` ｜ bookSourceType=0
> 成品：`examples/rrssk聚合_44域名.json`（52532B，md5 `47b3976311e9286667f78f41b238f3a0`，v8）
> 方法论：[方法-聚合源状态漂移修复与选站面板-rrssk](../references/方法-聚合源状态漂移修复与选站面板-rrssk.md) ｜ 架构篇：[聚合源多域名架构设计](../references/聚合源多域名架构设计.md)

## 一、这源是什么

一份 JSON 管 **44 个域名、14 套发现页模板、两套正文体系**（rrssk家族 + 菠萝猫 data-obf）：

- **jsLib**：`TEMPLATES`（模板）+ `HOST_TEMPLATE_MAP`（域名→模板，生成 `hosts`）+ `GET/SET/SRV/NBK/began/toSearch/checkKey/goedgeVerify/rebuildTocKey/dataEncrypt/textEncrypt`
- **发现页** `<js>` 动态生成：域名 select → 🌐 当前网址状态栏 → 搜索关键词/🔍搜索 → 分类按钮（菠萝猫分支 / rrssk家族 `list-N` 分支完全隔离）
- **搜索**：家族首页跳转 → `_t` + 花括号配平提取签名函数 → POST `rrssk.com/?action=search`
- **详情** og:novel 元标签 + init 提取 bookId/AES 密钥（随机名 `/templates/js/*.js`）
- **目录**：`loadChapterPage` POST（AES 加密）+ `/chapter/{id}.html` 的 `data-aid` 分页 + CDN 403/GoEdge 人机自愈
- **正文**：图标字体反爬（PUA 码点映射还原）+ 分页拼接

## 二、260923 三件事（v6/v7/v8）

### 1) 新增 16 域名（探测实证全为 fanqxsw 模板）

renrenshucheng / qubixsw / kankesz / luoquizww / wubensw / yuedba / ucxswz / ttkanshuba /
qshuxsw / luochen5 / bsbxs / laiyiben / cymxsw / shuhaixsw / jijxs / lwjh
（已有 fanqxsw / lwenxsw / ishuku / xiakezww 跳过）
探测：`probe2.py` 前台 ThreadPoolExecutor 并行，逐站验证家族跳转 `rrssk.com/00XX.html`、og:novel、随机名 AESCrypt、`/list-1-1/` fanqxsw 结构。

### 2) 【核心修复】书架书过段时间正文为空

- **根因真机实锤**：变量停在 `{"server":"https://www.boluomao.com","bookId":"2017969"}` → 旧正文规则见 server 含 `boluomao` 走 data-obf 分支 → 家族书 `.data-obf` 取空 → **内容为空**；用户"发现页打开对应网站再刷新"= 手动拨回 server
- **五层 URL 自治**：`SRV(url)` 推导域名 / 章节绝对 URL + `chapterUrl=$.chapterurl` / `dataEncrypt` 显式缓存键 / **别名书 data-aid 实际值自纠**（`hggjfg`→`hgg`，实测日志 `data-aid实际值修正`）/ toc 取值链 `book.url→tocUrl(http)→baseUrl(http)`
- **附带修**：replaceRegex 空书名保护 `{{NBK(book)}}`（htmlunit Java 空串 truthy 复盘）、初始化哨兵 `!GET('server')`、校验器 infoMap 洗变量

### 3) 选站三件套（v7 登录面板 + v8 状态栏）

- **登录界面**（⋮→登录）：`loginUi=<js>` 运行时从 hosts 生成 **47 行**（📍查看当前[viewName 动态] / ⚙恢复默认 / 🔄重建发现 + 44 站 0.2 宽网格）；`setSite` = 写变量 + 同步 `infoMap_rrssk聚合` 库 + `source.refreshExplore()` 清两级缓存（action 在 IO 线程可过主线程检查）
- **发现页**：select→server 的 SET **移进 action**（`SET('server', infoMap['域名']); java.refreshExplore()`，evalButtonClick 带 infoMap 绑定）；kinds 求值期不回写 + 求值时 `infoMap['域名']=GET('server')` 同步下拉显示；`default=GET('server')||hosts[0]`
- **状态栏**：下拉正下方 `🌐 当前网址: <server真值>`，点击 toast 完整网址；**读真值不依赖下拉显示**

## 三、验证记录（全绿）

| 项 | 结果 |
|---|---|
| SRV 单测四态（漂移/同域/无全局/无URL，真机） | 4/4 |
| 污染态 `--` 正文 / `++` 目录对照 | 非空 / 推导正确 |
| 别名书 `++hggjfg` | `data-aid实际值修正: hgg` → 127 章 |
| renren 677 章、lwjh 发现链 161 章、搜索 20 条 | 通过 |
| loginUi 生成（真 hosts=44 → 47 行）、setSite 四要素、select action、fixExplore | 通过 |
| 状态栏 viewName/action、infoMap 同步（过期值→当前值） | 通过 |
| `check_source` | **1/1 ×3**（v6/v7/v8） |
| 全字段 md5 本地↔App | 每版一致 |

## 四、交付记录

- 工作目录：`/workspace/rrssk_add26/`（`rrssk_patched.json` + `build.py` + `README_260923.md` + `probe2.py` + `templates_map.json` + `probe_result.json`）
- dpaste：v6 `3CZ5PVANK` / v7 `82UASB49M` / **v8 `HXL2U96MA`**
- 通道：dpaste + `legado://import/bookSource?src=` 深链 + 用户确认（48KB 超 save_source 内联上限）
- 遗留：存量书目录若曾被污染，**刷新一次目录**即按新逻辑重建自愈；`www.boluomao.com` 死主机（用 `boluomao1.com`）

## 五、一句话经验

> 全局变量只配驱动 UI，不配驱动内容链路；选站入口做三个也要共享一个真值源（URL 与 server 真值），状态栏永远读真值不读控件显示。
