---
name: legado-book-source-tamer
description: 用于创建、修复、调试、讲解 Legado 阅读书源。涉及书源规则、站点分析、搜索/详情/目录/正文规则时必须使用。
---

# Legado 书源开发技能

## 技能定位

本技能用于处理所有 Legado 阅读书源相关任务，包括：

- 创建新书源
- 修复已有书源
- 分析站点结构与接口
- 解释书源规则语法

一旦任务涉及以下内容，必须使用本技能：

- 搜索规则
- 详情规则
- 目录规则
- 正文规则
- 发现规则
- API 分析
- 反爬处理

最终目标是输出以下结果之一：

- 可导入 Legado 的书源 JSON
- 修复后的书源 JSON
- 明确的问题分析和待验证项

## 适用范围

适用于以下任务：

- 为小说、漫画、听书、订阅网站创建书源
- 修复搜索失败、正文乱码、目录缺失、章节打不开等问题
- 分析 HTML、JSON API、Ajax、加密参数、验证码、Cloudflare
- 讲解 CSS 选择器、JSONPath、XPath、JavaScript 在书源中的写法
- 使用Python脚本验证书源规则的正确性

常见触发词包括：

- 书源
- Legado
- 阅读 APP
- 搜索规则
- 目录规则
- 正文规则
- 发现规则
- 修复书源
- 调试书源
- 验证书源
- Python验证

## 非适用范围

以下情况不必进入完整书源工作流：

- 单纯小说推荐
- Legado 下载地址
- Legado 安装教程
- 与书源制作无关的普通技术问题

如果只是简单问答，可以直接回答；但一旦涉及书源规则或站点分析，必须切换到本技能。

## 工作模式

### 模式 1：知识问答

适用于：

- 解释规则语法
- 对比不同写法
- 给出示例

要求：

- 解释清楚概念和用法
- 可引用参考文档
- 不创建书源 JSON

### 模式 2：书源修复

适用于：

- 用户提供现成书源 JSON
- 用户描述已有书源的故障现象

要求：

- 先识别问题点
- 再输出修复建议
- 必要时输出修复后的完整 JSON

### 模式 3：新建书源

适用于：

- 用户给出站点 URL，希望从零创建书源

要求：

- 分析站点结构
- 判断请求方式和页面类型
- 生成对应规则
- 输出完整 JSON 或明确的部分可用结果

## 标准主流程

### 第一步：任务分类

先判断任务属于哪一类：

- 知识问答 / 书源修复 / 新建书源
- 只做搜索 / 搜索+详情 / 完整源
- HTML 页面 / JSON API / Ajax 动态加载
- 优先 PC 站 / 优先移动站

### 第二步：信息收集

收集或确认以下信息：

- 站点 URL
- 搜索页或搜索接口
- 详情页 URL
- 目录页 URL
- 正文页 URL
- 请求方式：GET 或 POST
- 页面编码：UTF-8 / GBK / 其他
- 是否存在登录、验证码、Cloudflare、加密参数

如果信息不足，不要直接臆造规则，先补齐关键输入。

### 第三步：规则分析

根据真实页面结构或用户提供内容，分析以下字段：

- `searchUrl`
- `ruleSearch`
- `ruleBookInfo`
- `ruleToc`
- `ruleContent`
- `exploreUrl`
- `ruleExplore`

如果只做搜索源，只需要分析与搜索相关的必需字段。

### 第四步：规则产出

将分析结果整理成完整 JSON。

至少保证：

- 基本字段完整
- 规则结构合法
- 命名清晰
- 风险说明明确

### 第五步：结果校验

输出前必须检查：

- JSON 结构是否正确
- 必填字段是否齐全
- 规则写法是否兼容 Legado
- 是否存在明显的站点依赖风险
- 是否需要用户在 Legado 中进一步实测

### 第六步：Python验证

在输出前，可以使用Python工具进行验证：

1. **规则语法验证**
   - 使用 `scripts/rule_validator.py` 验证选择器和源规则的正确性
   - 检查规则在真实HTML中的匹配效果

2. **网站结构分析**
   - 使用 `scripts/smart_web_analyzer.py` 分析目标网站
   - 确认搜索表单、列表结构、分页信息

3. **提取测试**
   - 使用 `scripts/multi_mode_extractor.py` 测试提取规则
   - 评估提取结果的置信度



**重要提示**：
- Python验证只是模拟，不能替代Legado APP实测
- 验证通过不代表在Legado中一定能正常工作
- 最终必须在Legado APP中进行完整测试

## 输入契约

### 最少输入

用户至少应提供以下信息之一：

1. 目标站点 URL
2. 任务类型：新建或修复
3. 目标范围：只搜索 / 搜索+详情 / 完整源

### 推荐输入

若用户能补充以下内容，成功率会更高：

- 搜索关键词样例
- 搜索结果页 URL
- 书籍详情页 URL
- 目录页 URL
- 正文页 URL
- 现成书源 JSON
- 报错信息或现象描述
- 是否优先手机站或 PC 站

### 信息不足时的处理原则

如果缺少核心输入：

- 先索要最小补充信息
- 不凭经验臆造完整规则
- 不把猜测写成确定规则

## 输出契约

输出必须尽量包含以下内容：

1. 完整书源 JSON 或修复后的 JSON
2. 保存路径，例如 `temp/站点名/站点名.json`
3. 本次已完成功能说明
4. 本次未完成或未验证项
5. 风险和限制说明
6. 建议用户在 Legado 中实测的步骤

如果当前只能交付部分结果，也必须明确说明：

- 哪些部分可用
- 哪些部分未确认
- 后续还需要什么信息

## 强约束

以下规则必须遵守：

1. 不允许编造站点规则，必须基于真实页面结构或用户提供内容分析。
2. 模拟调试不等于真实行为，Legado 官方源码优先于模拟结果。
3. 只要发现有分页按钮或下一页逻辑，就必须考虑 `nextContentUrl`。
4. 禁止使用 `prevContentUrl`。
5. 禁止使用 `:contains()` 作为 Legado 规则写法。
6. 禁止使用 `:first-child`、`:last-child` 这类不兼容写法，应改用索引方式。
7. 不要把可选增强能力当作默认必走流程。
8. 复杂 JavaScript 必须附用途说明。
9. 最终结果必须提醒用户在 Legado APP 中实测。

## 可选增强能力

以下能力属于可选增强，不是默认主流程：

- 批量抓取多个页面
- 使用调试器进一步验证
- 对特殊反爬站点做专项处理
- 上传书源并生成直链
- 使用Python脚本验证书源规则

使用原则：

- 仅当环境支持时使用
- 仅当任务复杂且确有必要时使用
- 不要因为存在增强能力，就强行改变主流程

## Python验证工具

本技能提供了一套Python脚本工具，用于验证书源规则的正确性。

详细的工具说明、使用方法、验证原则和最佳实践，请参考：
- [Python验证工具完整文档](references/python-validation-tools.md)

### 工具模块概览

1. **规则验证器** (`scripts/rule_validator.py`) - 验证CSS选择器、XPath、正则表达式
2. **智能网站分析器** (`scripts/smart_web_analyzer.py`) - 自动分析网站结构
3. **多模式提取引擎** (`scripts/multi_mode_extractor.py`) - 支持多种提取方式
4. **智能请求工具** (`scripts/smart_request.py`) - 智能HTTP请求和编码检测
5. **知识库工具** (`scripts/knowledge_tools.py`) - 搜索参考文档
6. **文件整理工具** (`scripts/file_organizer.py`) - 自动整理生成的文件
7. **调试器CLI** (`debugger/debugger_cli.py`) - 命令行调试工具
8. **Legado源码检查器** (`debugger/legado_checker.py`) - 参考官方源码

### 快速开始

```bash
# 使用调试器CLI测试书源
python debugger/debugger_cli.py test book_source.json --keyword "斗破苍穹"

# 测试单个功能
python debugger/debugger_cli.py search book_source.json --keyword "斗破苍穹"
python debugger/debugger_cli.py info book_source.json --url "https://example.com/book/1"
```

```python
# Python脚本验证
from scripts.rule_validator import validate_rule
from scripts.multi_mode_extractor import extract_content

# 验证规则
result = validate_rule(html, 'css', '.book-list .book-item')

# 测试提取
result = extract_content(html, '.book-title')
```

### 验证原则

1. **模拟不等于真实**：Python验证只是模拟，最终必须在Legado APP中实测
2. **优先参考官方源码**：使用`debugger/legado_checker.py`参考Legado Kotlin源码
3. **逐步验证**：先验证搜索，再验证详情，最后验证正文
4. **记录问题**：将验证中发现的问题记录到输出中

更多详细内容请查看[Python验证工具完整文档](references/python-validation-tools.md)。

## 失败与降级策略

### 可降级交付的情况

- 搜索规则可确认，但详情规则未确认：允许只交付搜索源
- 搜索、详情、目录可确认，但正文规则不稳定：允许交付部分可用源，并标注风险
- 发现规则无法稳定确认：允许暂不提供 `exploreUrl`

### 必须中止完整交付的情况

- 站点需要登录且当前无法验证
- 存在验证码或 Cloudflare，但当前条件不足以完成验证
- 页面结构未获取到，核心规则只能靠猜测

这时应改为输出：

- 已分析出的结论
- 当前阻塞点
- 需要用户补充的最小信息

### 信息不足时的默认策略

如果用户只给出模糊需求，例如“做个书源”：

- 先补齐站点 URL 和目标范围
- 不直接生成完整书源

## 参考文档导航

### 入门

- [QUICKSTART.md](QUICKSTART.md)
- [FAQ.md](FAQ.md)

### 主流程
- [references/workflow-guide.md](references/workflow-guide.md)
- [references/skill-tips-guide.md](references/skill-tips-guide.md)
- [references/书源规则易错点.md](references/书源规则易错点.md)

### Python验证工具
- [Python验证工具完整文档](references/python-validation-tools.md) - Python验证工具详细说明
- [scripts/rule_validator.py](scripts/rule_validator.py) - 规则验证器
- [scripts/smart_web_analyzer.py](scripts/smart_web_analyzer.py) - 智能网站分析器
- [scripts/multi_mode_extractor.py](scripts/multi_mode_extractor.py) - 多模式提取引擎
- [scripts/smart_request.py](scripts/smart_request.py) - 智能请求工具
- [scripts/knowledge_tools.py](scripts/knowledge_tools.py) - 知识库工具
- [scripts/file_organizer.py](scripts/file_organizer.py) - 文件整理工具
- [debugger/debugger_cli.py](debugger/debugger_cli.py) - 调试器CLI
- [debugger/legado_checker.py](debugger/legado_checker.py) - Legado源码检查器

### 规则语法
- [references/css-selector-reference.md](references/css-selector-reference.md)
- [references/css选择器规则.md](references/css选择器规则.md)
- [references/regex-guide.md](references/regex-guide.md)
- [references/json-structure.md](references/json-structure.md)
- [references/javascript-guide.md](references/javascript-guide.md)
- [references/书源规则易错点.md](references/书源规则易错点.md)

### 特殊场景

- [references/api-discovery-guide.md](references/api-discovery-guide.md)
- [references/post-request-guide.md](references/post-request-guide.md)
- [references/encoding-guide.md](references/encoding-guide.md)
- [references/动态加载.md](references/动态加载.md)
- [references/captcha-detection-guide.md](references/captcha-detection-guide.md)
- [references/WAF挑战过盾指南.md](references/WAF挑战过盾指南.md) - WAF挑战(503+token Cookie)过盾实战
- [references/webview-limitations.md](references/webview-limitations.md)
- [references/方法-登录检查JS.md](references/方法-登录检查JS.md)
- [references/方法-JS扩展类.md](references/方法-JS扩展类.md)
- [references/方法-加密解密.md](references/方法-加密解密.md)
- [references/方法-笔趣阁家族多域名同库站书源制作.md](references/方法-笔趣阁家族多域名同库站书源制作.md) — 261030 shoujixs.net 实战：笔趣阁家族多域名同库站识别（GBK PC站不可混用）+ss_search_delay Cookie 120s限频破解（清Cookie立即恢复/concurrentRate 1,120000）+三模板统一规则（og meta/锚点切割h2~p/正文三容器+reader_js.php Ajax兜底）+无发布页面板模板（预置线路+ajaxAll测速+自定义网址）+发现页三板块；通用坑：ruleSearch.lastChapter字段名（latestChapter被GSON静默丢弃）、@js: URL选项JSON必须嵌入返回串、App jsoup展开非法嵌套p>p（Python预演与App实测DOM不同）、java.post三参签名、debug_source key=章节URL只走详情目录、check_source限频误报、长JSON走LAN投递
- [references/方法-米游社签到定时任务拆解.md](references/方法-米游社签到定时任务拆解.md) — 定时任务三作用域架构+loginUi按钮action调试+java.show缺失兜底；成品 JSON 见 [examples/米游社每日签到_定时任务_v9g.json](examples/米游社每日签到_定时任务_v9g.json)
- [references/方法-发布页线路轮换与登录界面测速选线.md](references/方法-发布页线路轮换与登录界面测速选线.md) — 域名轮换站通用方案：发布页抓取/线路解析过滤/timeout测速选优/TTL缓存/入口注入五层流水线+登录UI测速按钮组+参数注入法绕jsLib作用域+bookUrl相对化自愈
- [references/方法-简介useweb内嵌页面与浏览器调起.md](references/方法-简介useweb内嵌页面与浏览器调起.md) — useweb真WebView机制+WebJsExtensions注入API清单(注解差异)+startBrowser/openUrl/iframe三通道浏览器调起+跨版本(LegadoTeam/legado-E)兼容铁律
- [references/方法-番茄漫画书源与混合类型自动判型.md](references/方法-番茄漫画书源与混合类型自动判型.md) — fqapp逆向漫画链路(CM通道materials/skeleton)+"图片加密"假象破解(type:hex验魔数先于写解密)+混合类型自动判型(comic_book_type)+Rhino中文必须UTF-8字面量+大源交付与同站点多源共存(##后缀)
- [references/方法-登录UI-V2新版面板.md](references/方法-登录UI-V2新版面板.md) — **登录UI V2新版面板(loginUi={"version":2})**：下拉select/开关toggle/倒计时按钮/状态消息板/错误红字定位——V1经典面板做不到的交互；loginUi(state)+loginAction(action,state,form)骨架+RowUi V2硬约束(key/action必填校验)+Kotlin默认参数JS须传全+state内存往返+10条踩坑+node语义仿真法(hanime1首个生产案例)；**§7 控制台实战增补(hanime1 v3.4~v3.9)**：分支哨兵词冲突/多值不能当select value(分组)/延迟后缀与解析解耦/toggle能力开关三件套(写变量+立即生效+关=可回退旧实现)/账号密码三源兜底且用户清空优先/危险动作countdown+robots.txt轻量探测/消息板分隔符换行
- [references/方法-登录UI-V2动态渲染与useweb新特性总览.md](references/方法-登录UI-V2动态渲染与useweb新特性总览.md) — ★**源码级新特性总览(与V2面板篇互补，本篇讲渲染链路与请求控制)**：①`<usehtml>`/`<md>`/`<useweb>` 三种简介前缀的完整渲染链(BookInfo.kt:125 判定 → Activity 分派)：`<md>` 走 Markwon(**支持表格**)、`<useweb>` 走真WebView(注入java/source/cache随机名映射、**activity=null 故 startBrowser 静默失效**)、三者**都以 `<` 结尾**且 substring 偏移 9/4/8 不同；②正文 `<usehtml>` 是**成对闭合**且受「适应特殊样式」控制(默认开)、处理顺序=占位符→替换净化→还原；③发现页 ExploreKind 五型(url/text/button/toggle/**select下拉**) 全字段与行为(select 的 chars 空显示占位、**初始化自动写 default 进 infoMap**、首选中被 isInitializing 跳过、切换才触发action；text 有600ms防抖)；④**infoMap 是持久化 Map**(`infoMap_${sourceUrl}`，onPause 批量 saveNow)，URL 里 `{{infoMap['标题']}}` / `{{infoMap.分类}}` / `||兜底` 均实测可用；⑤`exploreUrl` 支持 `@js:`/`<js>` **动态返回分类JSON数组**(可读infoMap、有aCache缓存、refreshExplore才清)；⑥FlexChildStyle 六字段布局；⑦**UrlOption 15字段全表**(method只认POST/HEAD否则静默降级GET、js=改URL、bodyJs=改body、webView+webJs=后台WebView执行JS、dnsIp/serverID/timeout/followRedirects/webViewDelayTime)；⑧速查排错表
- [references/方法-发现页交互与事件系统批量正文等高级特性.md](references/方法-发现页交互与事件系统批量正文等高级特性.md) — ★**发现页UI行为 + 事件系统 + 批量正文补遗**（源码逐行核对）：①**发现页搜索框是"筛书源"不是"搜书"**（SQL匹配 bookSourceGroup/bookSourceName，需 enabledExplore+hasExploreUrl）；②`group:` 前缀精确分组过滤 vs 无前缀 like 模糊；③收起/展开是**手风琴模式**（exIndex单值，同时只展开一个）；④改 exploreUrl 必须点菜单「刷新」清 sourceKinds+aCache 两级缓存；⑤**`java.reUiView(true)` 让控件action能刷新整个分类列表**（清缓存+重求值exploreUrl+重绘）；⑥发现列表**分类Tab栏默认关闭**（AppConfig.showExploreCategories=false，只能右上菜单开）且**只收 type=url 的项**（select/toggle/text/button不进Tab）；⑦页码直达1~999；⑧**双向分页**（到顶继续上滑加载N-1页并前插）；⑨一键把已加载书籍加书架；⑩**eventListener+callBackJs 事件系统19个钩子**（clickAuthor/clickBookName/clickCustomButton/clickShareBook/clickClearCache/clickCopyBookUrl/addBookShelf/saveRead/startRead/endRead/startShelfRefresh等，返回truthy**拦截**原动作、falsy放行）+customButton；⑪**contentBatch 批量正文**（maxBatchSize必须>1才启用、硬上限50、只能JS、result=章节数组、每章必须java.cacheContent回存、**按index认章不按url**、重复URL须传章节对象、自动套replaceRegex、未回存自动回落单章）；⑫其余新字段：coverDecodeJs(封面解密,入参InputStream返回ByteArray)/imageStyle(FULL最大宽)/payAction(VIP购买)/exploreScreen(JS源)/variableComment(变量说明)/ruleReview(段评)/preUpdateJs+formatJs(目录更新前后钩子)
- [references/方法-发现页本源搜索框与可伸缩分组列表.md](references/方法-发现页本源搜索框与可伸缩分组列表.md) — ★**91Hub 范式：发现页自带搜索框（只搜本源）+ 点击伸缩分组列表**（39shuwu 已落地实测）：①**本源搜索的唯一正确写法 = `java.searchBook(key, source)` 双参重载**（源码 RssJsExtensions.kt:80），内部 SearchScope(source)=`书源名::bookSourceUrl` 锁定单源；单参 `java.searchBook(k)` 会变全局搜索；源码注释明说"单源搜索不缓存、每次必须显式指定"；②**伸缩折叠三件套**=`source.getVariable()`读 → `c[key]=c[key]?0:1`翻转 → `source.setVariable()`写回 → **`java.refreshExplore()`重绘**（缺最后一步就是"点了没反应"）；③求值端用 `(cfg[key]===undefined)?defOpen:(cfg[key]!==0)` 决定是否 push 子项，标题带 ▼/▶；④**布局配比**：搜索框 flexBasisPercent 0.6 + 按钮 0.31 才能并排（合计≈0.91），折叠条 1.0 独占整行，分类项 0.25 四列；⑤**实测数据**：{}→11项/{"top":1}→21项/{"cat":0}→5项；折叠条 1→0→1 翻转正确；搜索按钮空值toast、有值 searchBook(k,source) 且 source 有值；⑥★**新发现字段名坑：`source.sourceUrl` 不存在（undefined），正确是 `source.bookSourceUrl` 或 `source.key`**（91Hub 原文用 sourceUrl 实际走兜底硬编码）；⑦与"App全局搜索框（筛书源名/分组名）"是两套东西可共存；⑧7条避坑



- [references/方法-legadoE登录面板V1动态与发现页点选化.md](references/方法-legadoE登录面板V1动态与发现页点选化.md) — ★**legado-E 适配 + select→点选化总纲(禁漫天堂v15e蓝本)**：E版SourceLoginDialog能力表(@js:/<js>动态loginUi/toggle点按循环/select/Spinner/label不渲染/✓menu_ok先putLoginInfo再login/onDismiss自动存/文本行action=600ms TextWatcher/reLoginView重建)；E版发现页ExploreKind能力表(toggle读infoMap[title]+aCache持久缓存)；★**action作用域铁律：登录面板action能看到loginUrl函数(拼接eval)，发现页action只能看到jsLib(shareScope)**；改造四板斧(V2→@js:jmeRows()/toggle chars+result读选中值/状态按钮补reLoginView/发现页action下沉jsLib参数注入)；E隐形炸弹同步修复(loginCheckJs body属性方法双通道/top-level禁const-let/列表JSON字符串协议/bookSourceUrl##片段隔离缓存)；node vm沙盒仿真法；K1~K10
- [references/方法-HttpTTS朗读引擎与音色切换面板.md](references/方法-HttpTTS朗读引擎与音色切换面板.md) — **在线朗读引擎(HttpTTS)通用方法论**：实体全字段+请求链路源码拆解+给朗读引擎加按钮的唯一官方通道(编辑→⋮→登录→SourceLoginDialog)+RowUi六种type与动态viewName+★JSON body必须JSON.stringify(否则正文引号毁URL选项→静默无声)+音色变量持久化(source.put/get)+语速映射源码级推导(显示值=speakSpeed/10)+loginCheckJs把没声音变报错+零双引号工程法+13条踩坑
- [references/方法-视频书源播放本地解密完全指南.md](references/方法-视频书源播放本地解密完全指南.md) — ★★★**视频书源"能播放"完整条件链（CENC 解密 + 本地 file:// 播放）**（番茄短剧·漫剧 fqnovel.com 蓝本，4 次报障 / 7 个版本迭代才通，check 1/1 + Team/E 双版实测可播）：核心认知=**视频书源做不出来，九成不是找不到接口，而是"最后一公里"没打通**——接口/签名/解密都跑通、debug 也显示 file:///xxx.mp4，但播放器就是加载一下就停；★★★**10 条播放条件链**（缺任何一条都播不了）：①**file:// 路径必须动态探测当前 App 真实缓存目录**（★最隐蔽：硬编码 `com.legado.app.release` 在自己手机上完全正常，换 legado-E(`io.legado.app`) 就挂；解法=`java.readFile('/')` 触发 FileNotFoundException，从消息正则提取 `.../cache` 前缀）②**CENC 要清"一组"box 不是 1 个**（encv→hev1 / enca→mp4a / sinf·tenc·**senc·saiz·saio**→free；★Team 播放器宽容会忽略 senc，**E 版见到 senc 就拒播**；诊断信号"Team 能播/E 版不能"=直接排除解密错误，锁定播放器严格度差异）③**encv 必须改 hev1 不是 hvc1**（参数集内嵌样本=hev1 语义；写 hvc1 会让 MediaCodec 拒绝整条视频轨→**只有声音没画面**，ffmpeg 宽容会掩盖必须真机验证）④文件完整写入且能读回（★`readFile` 用相对路径，播放用绝对路径；磁盘满会 ENOSPC 静默失败）⑤必须有 retry（CDN 间歇 Connection reset，★域名不能互换只能同域重试）⑥默认画质选最小可用档（hex 通道内存峰值≈文件×4；360p=28MB✅/1080p=92MB❌）⑦codec 避开 bytevc2（ByteDance 私有编码安卓解不了；★**同站不同 aid 编码策略完全不同**——aid=8662 低档全 bytevc2、aid=1967 全档 bytevc1 可播且 URL 是 base64 明文）⑧**jsLib 作用域≠规则作用域**（放 jsLib 的函数内 java 不可用，eval_js 测正常但真实规则返回空→**必须内联到规则顶部**）⑨字节回写必须 `System.arraycopy`（`bytes[i]=dec[i]&255` 报"无法将255转换为java.lang.Byte"）⑩文件名唯一+缓存复用（固定文件名导致多剧互相覆盖）；★**排查 Checklist 10 步**（第 1 条最重要=debug 输出的实际字符串往往就是答案，本次 `file:///xxx.mp4` 缺目录前缀一眼就该看出，却绕了三轮）；★**构建闸门 5 道**（含"零硬编码路径"：全文搜 com.legado 只允许出现在兜底默认值；手改长 JSON 里的 JS 是高危操作，加 retry 时多插一个 `+` 就语法错）；★**跨版本兼容三件事**（第三方库 R8 裁剪 / 播放器宽容度 / 包名不同）+ **E 版模拟验证法**（字符串替换屏蔽 hutool+bouncycastle 后 eval 跑全链路，不用等真机）；★性能速查（hex 转 bytes 用 BigInteger 330ms vs 纯 JS 10439ms/512KB，**提速 164 倍**）；★四条铁律 + 完整可用的 ruleContent 模板；案例 examples/番茄短剧漫剧_www.fqnovel.com.{json,md}
- [references/方法-视频书源完全指南.md](references/方法-视频书源完全指南.md) — **一切"正文=播放地址"的站点(影视/动漫/短剧/MV/图集混合)总纲**：bookSourceType=4→BookType.video→VideoPlayerActivity 全链路源码拆解；★★三条铁律(正文可携带URL选项给播放器塞Referer/Cookie / `dnsIp`救不了播放器拉流只能换主机名 / m3u8给地址、MPD可内联文本)；`subContent`=B站XML弹幕通道；卷=线路章=剧集的官方多线路模型；当前集一致性四索引两陷阱(新书durChapterIndex=0、playlist新→旧)；播放页快照→`useweb`+`callBackJs`自造切集跟随；三诊断键(h1now/h1ev/h1diag)；DNS污���·SNI封锁·CF挑战三重鉴别+CDN原生主机替换法；`_token`匿名也发的登录判据陷阱；跨镜像域Cookie同步；登录UI控制台38行骨架；四种形态开箱模板；**51条避坑+22项验收**；5个视频站对照档案(hanime1/mdcmai/huangguo/hlwf6/novelServices)
- [references/方法-订阅源视频播放修复与CDN-Referer指纹.md](references/方法-订阅源视频播放修复与CDN-Referer指纹.md) — ★**RSS订阅源(type=0正文=HTML+<video>)「无法播放」修复总纲（avjoy.top蓝本）**：★★★CDN Referer指纹校验（无/异域Referer→返回10秒提示片假m3u8(#EXTM3U+tip.ts,143B)；主站origin→真MP4；判据=Content-Type+首32字节ftyp vs #EXTM3U；正文模板输出referrer never是主凶）；★★正文永久缓存×签名链接时效（rssArticle.description永久入库+refresh()见缓存即跳过⇒二次打开必用过期链接⇒**页内自愈三件套**：过期预检(URL内10位时间戳>90min)/假视频检测(loadedmetadata时长<30s)/error兜底+双击手动刷新，通道=CORS fetch重取详情页，前提CDN ACAO:*）；URL选项retry抗偶发超时（,{"retry":2}跟在{{}}模板后不破坏paramPattern切分）；图床404判站方故障法（站内页面自己引用也404=站方故障别改源）；RSS播放链路源码速查（loadWithBaseUrl=true时WebView子资源自动带baseUrl Referer/ruleNextPage=PAGE机制/id=video兼容injectJs手势）；node new Function模拟Rhino绑定+12项特征断言+端到端五步模拟验证法；可复用8步排查清单
- [references/方法-小说漫画视频三合一书源详解.md](references/方法-小说漫画视频三合一书源详解.md) — ★**一个书源同时承载 小说/漫画/视频 三种内容形态**（禁漫天堂Pro v1~v14 蓝本,check 1/1）：适用场景三问（站点真多形态/公共代码多/一次登录覆盖）；**四招总纲**（模式变量+字段整体分发+统一列表解析器+按URL类型分支）；发现页jmode下拉(infoMap.save+refreshExplore清两级缓存)与搜索前缀分发(#小说 !视频 零UI成本)；★统一解析器jmParseList输出JSON字符串数组纯键JSONPath双版本通用、bookUrlPattern绝不匹配搜索url、新类型入口四处同接(parser白名单/init分支/目录/pattern)；★**作者字段宁缺毋滥+特征行定位**(main_tag=2链接或行文本"作者:"开头，无则空绝不回退书名——周更/收藏夹页无作者行的著名翻车)；★**单击作者本源搜索=官方kind芯片原生机能**(kind头部插作者→lbKind点击回调SearchActivity(source,kind)，useweb面板内无此通道)；★book.type必须在chapterList里动态设(刷目录removeAllBookType冲掉init设置,位掩码4/8/32/64)；收藏体系闭环(登录/解冻/选夹/loginUi+useweb面板三态收藏+faved缓存优先根治重开误判+**重复收藏报错=已收藏铁律**(HTML alert清洗后关键词判定顺势修UI)+attr||attr短路失效需jmAttr显式判空)；**发现页标签数据化方法论**(结果页200+卡片统计search_query链接频次=真实热门标签,25→58剔除女性向/敏感词)；14条避坑K1~K14+6步验证(node仿真/App真Rhino回放/check_source/debug多入口/真机验收清单/dpaste深链)+8项移植改动清单；与X夜社六形态/聚合换源/线路轮换三类对照
- [references/方法-单源多模式切换书源制作.md](references/方法-单源多模式切换书源制作.md) — ★**一个书源同时承载 小说/漫画/写真/视频/动漫/有声 六种内容形态**（X夜社范式）：模式变量(`source.setVariable/getVariable`，`loginUrl` 顶层具名函数 `set_laiyuan()` + `loginUi` 六按钮）→`exploreUrl`/`searchUrl`/`ruleToc.chapterList`/`ruleContent` 四处 JS 按模式分支；★**`book.type` 必须在 `ruleToc.chapterList` 里动态设置**（`WebBook.getChapterListAwait` 刷目录时会 `removeAllBookType()` 冲掉详情页 type；位掩码 video=4/text=8/audio=32/image=64）；★**视频/音频用 `data:text/html;base64,` 内联播放页 + `java.startBrowser` 交给内置浏览器**（绕开 ExoPlayer 防盗链与 m3u8 环境依赖，`muted`+`playsinline`）；★图片形态必须自拼 `<img src="…">` **双引号**否则官方 `imgPattern` 匹配不到；`player_aaaa={...}` JSON 提直链+海报；顶层 `bookSourceUrl` 非 URL 的取舍；**16条避坑 K1~K16 + 12步制作清单 + 移植改动表**；与"换源/换域名"三类切换对照
- [references/方法-聚合源状态漂移修复与选站面板-rrssk.md](references/方法-聚合源状态漂移修复与选站面板-rrssk.md) — ★**多域名聚合源"全局状态漂移病"总纲**（rrssk聚合44域名蓝本，check_source 1/1×3）：症状三张脸（书架书正文为空=server停boluomao走data-obf分支取空/搜索中转失败/校验器洗变量炸`/list-`相对URL）与写者清单（select/init对齐/setSite/began/校验器）→**根治=URL自治五层**：`SRV(book.bookUrl/baseUrl)`推导域名（同域优先全局scheme）、chapterList输出绝对URL+`chapterUrl=$.chapterurl`、`dataEncrypt`显式缓存键+scheme兜底、**别名书按页面data-aid实际值自纠**（hggjfg→hgg）、toc取值链`book.url→tocUrl(http)→baseUrl(http)`、`{{NBK(book)}}`空书名保护；**选站三件套**：登录面板（`loginUi=<js>`运行时从hosts生成47行网格/action跑在`lifecycleScope.launch(IO)`可过refreshExplore主线程检查/`BaseSource.evalJS`单参Rhino调不到/login()仅非空文本行才调）+ 发现下拉（**SET移进select action**——evalButtonClick带infoMap绑定、kinds求值不回写防过期live InfoMap覆盖、default跟随server）+ 下拉下方**状态栏**（Type.button viewName动态读GET真值，3~19单引号字面量规则）；**check_source三坑**（无UI infoMap洗变量/哨兵只认空串与{}→改`!GET(key)`/kinds两级缓存）；**模板引擎与htmlunit四铁律**（`{{}}`无括号=属性路径恒空带括号=JS求值/Kotlin空Java串truthy须`String(x).length>0`/java.lang.String无.length/evalJS默认参数Rhino单参调不到）；**K1~K18避坑 + Node行生成仿真/真机kinds求值/污染态对照/check_source×3/全字段md5/dpaste深链交付法**；架构篇=[聚合源多域名架构设计](references/聚合源多域名架构设计.md)，案例=[rrssk聚合_44域名](examples/rrssk聚合_44域名多站聚合.md)
- [references/方法-Legado三个JS环境变量差异与返回值类型铁律.md](references/方法-Legado三个JS环境变量差异与返回值类型铁律.md) — ★★★**源码级实测的四个通用机制坑（liz04.com 荔枝短剧视频书源蓝本，与站点无关）**：①**loginCheckJs 返回值必须是传入的 result（StrResponse）**——源码 WebBook.kt/Rss.kt 全线 `analyzeUrl.evalJS(checkJs, it) as StrResponse` 硬强转，写 `return true/false/''` 会抛 `ClassCastException: java.lang.Boolean cannot be cast to io.legado.app.help.http.StrResponse`；**报错指纹=搜索/check_source 失败但 HTTP 日志 200 且响应体完整**（极易误判成网络/站点问题，网上大量教程就是这么写错的）；②**bookList/chapterList 的 @js: 环境没有 key/page 变量**（只有 result/src/baseUrl，key/page 只属于 AnalyzeUrl）→ 写 String(key||'') 抛 ReferenceError key 未定义；铁律=**列表规则只能从 result 解析已抓到的内容，不要在 bookList 里再调 java.ajax**（省一次请求配额）；③**exploreUrl 的 @js: 必须 return JSON.stringify(rows)**——BookSourceExtensions.exploreKinds() 用 isJsonArray() 判断，返回 JS 对象数组 toString 得 [object Object] → 回落「标题::地址」文本解析 → kinds 空 → **报「发现规则为空」**（与「发现失效」是两种分组）；附带源码确认 initUrl() 顺序 = analyzeJs→replaceKeyPageJs→analyzeUrl，故 @js: 里可安全用 {{page}}（发现页跟随线路切换的根基）；④**视频源(bookSourceType=4)优先用 ruleBookInfo.init 一次取回 + 字段填单字母 key**，不要让各字段各自 @js: 请求、tocUrl 也别带 ,{headers} 选项（本次 ClassCastException 的第二来源）；⑤调试辅助：source.get(k) 在 Rhino 返回包装对象（typeof 为 object）必须先 String() 再判 length/indexOf；eval_js 环境 r instanceof java.lang.String 抛 TypeError、r.getClass().getName() 也可能 null 失败，改用 String(r).length + JSON.parse(r) 判类型；附**排查 Checklist 5 步**（先看报错类型再怀疑网络）；三类 JS 环境变量速查表；案例 areas/liz04-book-source.md；**★261028 增补：封面不显示 = header 的 Accept 被 Glide 复用到图片请求（源码 AnalyzeUrl.getGlideUrl() 用 source.getHeaderMap()，图床按 Accept 分流：带 text/html 返回 ~2KB HTML 页→IOException/加载失败，带 image/avif,image/webp,image/apng,image/*,*/*;q=0.8 才返回 ~95KB 正常图片，**图床型站点 header.Accept 必须图片优先**且实测不影响 HTML/JSON/m3u8）；**★视频不播放 = ruleContent.content 返回值被污染**（视频源 content 返回值就是播放地址，必须是纯 URL 或带选项 JSON，写 `return '📺 '+ttl+'\n\n'+cu` 带标题换行→播放器无法播，**只 return 纯 URL**；判据=debug 用 --URL 看正文页那行是否干净 URL）；防盗链判活表（m3u8/key/ts 全无防盗链时 ExoPlayer 自动解 AES-128 无需本地解密）

- [references/方法-网易云类weapi加密站的明文接口降级方案.md](references/方法-网易云类weapi加密站的明文接口降级方案.md) — ★**加密接口返回200空体不是算法错,是站点策略**(源站22ms秒拒,沙盒与真机同结果):固定secKey做JS出Python解双向验证证明加密正确后整体降级到/api/明文GET;★★★三条App级硬知识:`getElements`只接受List/Array/NativeArray(**@js列表规则return JSON字符串→列表大小0,必须return JS数组**;与E版字符串数组需求互斥);**Rhino的java.lang.String没有.length属性**(NaN<256使补零循环永不执行,所有Java返回字符串必须String()包裹);`createSymmetricCrypto(AES/CBC/PKCS5Padding,k,iv).encryptBase64()`与CryptoJS PKCS7**逐字节一致**;网易云/api/接口全清单(搜索/详情/歌单/播放直链无Referer/歌词/榜单/分类);音频书源四机制(bookSourceType=1自动audio/subContent=歌词通道/tocHtml复用省请求/禁replaceRegex);Cookie粘贴登录(putLoginHeader自动写CookieStore);12条避坑
- [references/方法-音乐书源制作指南.md](references/方法-音乐书源制作指南.md) — ★**音乐类书源(bookSourceType=1)通用制作总纲**(网易云听书源蓝本,check 1/1):**内容模型设计**(歌单=书N章/单曲=书1章/榜单=书/歌手=书的映射决策表+封面歌手头像兜底+歌词当简介+时长当字数);★★**音频类型官方机制源码级**(BookSource.getBookType=audio(32)/BookList自动设类型/刷目录removeAllBookType冲掉type/subContent→putLyric歌词LRC同步/isAudio跳过HTML净化/**replaceRegex逐行trim会切断播放URL必须留空**/tocUrl留空tocHtml复用省一次请求);★直链获取(音质参数320k→128k降级兜底/播放器不带Cookie需java.getCookie手拼/30分钟过期重进自愈/无版权VIP用throw中文提示不返回空正文);★歌单全曲目补齐(trackIds全量+每批≤50批量补名,225曲≈10s);接口设计套路七清单(搜索type区分单曲歌单/offset分页/c与cat参数encodeURI);发现页ExploreKind组织(分组标题行+榜单/推荐/分类/新歌);登录Cookie粘贴优先四件套;加密降级原则链向weapi姊妹文档;**完整开箱模板**(顶层/bookList/chapterList/content+subContent双通道/发现页多模板自适应);**20条避坑K1~K20**;验证方法论(音频特有:正文必须纯URL且indexOf('http')===0,歌词同步只能真机看);移植到QQ/酷狗/酷我/bilibili/喜马拉雅的改动清单(只需改7条接口URL+字段路径,通用骨架不用动)
- [references/方法-音频书源CENC解密与音色切换.md](references/方法-音频书源CENC解密与音色切换.md) — ★**番茄听书音频书源实战**(check 1/1):**CENC 解密全链路**(spade 无需解密判据/密钥派生 `v8=len-(r0^r1^r2)+47`+`work[i]=(-21-popcount(i)+(prev^old))&255`/逐样本 AES-CTR `iv16=senc[i*8:i*8+8]+8×0x00`/解密成功判据=首样本头 `FF F1 0A 5A` AAC-HE ADTS/fourcc `enca→mp4a`);**★★★三个 JS 环境绑定差异**(loginUi 的 `<js>` 无 source/java/infoMap → 生成函数必须无参;按钮 action 只有 java(SourceLoginJsExtensions) 无 source → 函数签名统一 `jv`;`jv.put/get` 与 `source.put/get` 同一键空间);**loginUrl 必须非空**;**infoMap 不注入的诊断法**(action 里 dump `eval('typeof X')` 清单 → 实测 `infoMapType=undefined`);**音色逐按钮 UI 模板**(`<js>FQ_atoneRows()</js>` 运行时生成 + 三重提示 toast/longToast/reLoginView);**四个 Rhino 硬约束**(arraycopy 回写/循环外 Cipher.getInstance/主动 gc/fourcc 限 moov 范围);**java.downloadFile 文件名必须唯一**;音频三件套(bookSourceType=1/chapterList 里 setType(32)/content 返回 file://);搜索相关度排序 FQ_asearch2
- [references/方法-飞飞CMS影视站视频书源制作.md](references/方法-飞飞CMS影视站视频书源制作.md) — ★**飞飞CMS(FeifeiCMS) 影视站视频书源模板**（花都动漫 hd.huadudm.com 蓝本，check 1/1）：30秒识别四特征（`var feifeicms=`/`ffcms_wd`/`ul.stui-vodlist`/`player_data`）+ URL 结构总表（**vodshow 12 段与 vodsearch 10 段连字符数量不同，必须抄站点分页 href**；分类 0 是 1072B 空壳）+ 详情字段是 `div.detail-item` 键值对（**按标签名取值不能按索引**，字段数会变）+ 封面取 `data-original`（src 是 load.gif）+ **列表页有多个 `ul.stui-vodlist`，取 li 最多的那个**（详情页混入"猜你喜欢"）+ 目录按 bookUrl 的 id 过滤（否则猜你喜欢被当章节）+ **正文 `player_data` 解密**（encrypt=1→unescape / encrypt=2→base64+多层 decodeURIComponent **必须循环到稳定**，末尾 `indexOf("http")===0` 校验）+ tocUrl 留空复用详情页零额外请求 + 15条避坑 K1~K15 + 移植四常量 + 8项验收
- [references/方法-CDN短时频控与假UA敏感误判.md](references/方法-CDN短时频控与假UA敏感误判.md) — ★★★**「带某 header 就 404、去掉就 200」几乎不是 UA 敏感，而是短时频控**（花都动漫 CDN 实战翻案）：**基线穿插法**（A/B/A/B 交替，而不是"跑完 A 组再跑 B 组"——若基线在第 5 次也挂就是频控）+ 三种假象（404→"URL拼错" / 超时→"DNS污染" / 换UA首次404→"UA敏感"）共同点是**同一 (URL,header) 不同时刻不同结果**=时间维度问题 + **判定流程五步** + 频控窗口实测（CDN 10~60秒，主站搜索框写"间隔10秒"实为装饰不拦）+ **不要为躲频控阉割 header**（用 `concurrentRate` 节流才是正解）+ 错误文案要给"等 1~2 分钟"的出路 + K1~K10（含"不要连打10次统计成功率——那是在制造频控"、"java.ajax 与 java.get 不同栈可区分网络层与 jsoup 层"）+ 可复用对照实验模板；**§10 同族陷阱「畸形 URL 也返回 200」**（发现页把 `{{page}}` 拼在 `.html` 后面生成 `...html1`，站点返回 200+正常页面 → debug 全绿、check_source 1/1 通过，**但翻页永远停在第1页**；唯一抓法=**看 HTTP 日志的实际请求 URL**；解法=**从站点真实分页 href 反推段位**（按 `-` 切段找"哪一段随页码变化"）+ 验证三件套（URL 逐字符比对 / 第2页内容≠第1页 / page=1 与省略形式同页）+ K11~K15）
- [references/方法-发现页只显示一页的排查与加固.md](references/方法-发现页只显示一页的排查与加固.md) — ★★★**发现页「只显示一页」的定位与加固**（花都动漫 v1.5→v1.6 实战）：**先证明站点第2页有数据 → 再证明 App 请求过第2页 → 最后才怀疑规则**；源码级机制 `ExploreShowActivity.upData()` 里 `adapter.getActualItemCount() == books.size` 就 `noMore()`（books 是 linkedSetOf，去重键 bookUrl）⇒ **任一页没新增书就永久停止翻页**（请求失败/空壳页/解析0条都中招）；三类根因与对策（①`page` 为 null/空/0 → URL 变字面量 `null` → 站点返 7157B 空壳 → **页码归一化** `Number(page)`+`>0`；②单页抖动 → URL 追加 `{"timeout":20000,"retry":2}`；③空页被当"真到底" → 读 `span.stats-text` 的 `第X/Y页`，`cur>=tot` 才算真到底，否则**抛错弹重试**绝不写 noMore）；**翻页自检**（把实际页码写进书源变量 + 面板按钮读出，一步区分"App 没请求"与"规则解析失败"）；★零引号纪律延伸到**会被嵌套的代码片段**（`String.fromCharCode(104,103,112,103)` 拼 `hgpg`，因为表达式要嵌进单引号 JS 字符串）；K1~K7 避坑 + 5 步验证清单
- [references/方法-服务端忽略页码参数与||分支空格陷阱.md](references/方法-服务端忽略页码参数与||分支空格陷阱.md) — ★★★**「200+20条 ≠ 第2页」假分页**（m.xhwx8.com 实战）：`?page=2/3/592` 全返回第1页同一集合，**判据必须逐页比对 bookUrl 集合而非条数**；排除法实测清单（各种参数名/随机数绕缓存/Referer/`_2.html`/PC站/空关键词搜索 全失败）⇒ 站点功能缺失，**不要写 nextPage 规则**（重复数据触发 App 去重后 noMore），改写进 comment + 找替代入口（热门榜467/排行榜84/首页66/7分类各20）；sitemap 1282 分片只有 URL 没书名不能做列表；★★★**`||` 分支空格陷阱**（本次最隐蔽）：`a@text || b@text` 切分后不 trim → 尾随空格让 `@text ` 精确匹配失败 → 整个 `||` 返回空（现象=列表20条但书名全空、书籍总数0）；**`&&`/`||`/`%%` 两侧一律不留空格**；★★`@js:` 顶层 `return` 非法，必须 IIFE 包裹或末表达式返回（报错原文「返回的值无效」）；★目录取「第2组 ul.chapter」只有 `:nth-of-type(2)` 可用（`:eq(1)`/`:nth-child(2)`/`ul.chapter[1]` 全 0 条，Legado 的 `[N]` 索引必须在规则末尾）；★`#nr1@html` + JS 九步清洗（含 HTML 残缺 `<iclass=`、末尾「！」**必须在删空段落之后**处理、`</div>` 用 `[\s\S]*$` 而非 `\s*$`）+ 整章广告清洗为空属正确行为；8步排查 Checklist
- [references/方法-目录分页窗口陷阱与页码推算.md](references/方法-目录分页窗口陷阱与页码推算.md) — ★**目录分页「滑动窗口」陷阱与「当前第X页，共Y页」定位法**（爱看书吧 m.2tsw.com 蓝本）：分页条以当前页为中心 ±10 页，第 11 页起窗口内已不含第 1 页，「找第 1 页取下一个」只翻 11 页；正确锚点是分页条首项纯文本「当前第X页，共Y页」+ `baseUrl` 提 bookId；★含 `@js:` 顶层 `return` 在 Rhino 报「返回的值无效」的两种正确写法（末表达式返回变量 / IIFE）；⚠ 已按源码级铁律修正为「只返回下一页 1 个 URL」
- [references/方法-正文跨页断字修复与逐行广告过滤.md](references/方法-正文跨页断字修复与逐行广告过滤.md) — ★**杰奇CMS 系 GBK 老站正文分页截断的完整修复**（爱看书吧 m.2tsw.com 蓝本）：站点在分页处按字节硬截 HTML，句子被拆开 + `&nbsp;` 被切成 `&n`/`bsp;` 两半，`nextContentUrl` + `##替换` 救不了；必须 `@js` 自控抓页循环：整块删按钮/`<font>` → 按 `<br>` 切行逐行判广告 → **每页剥首尾空白与 `<br>`** → `ps.join('')` 无缝拼接（不能 `join('\n')`）→ 最后修断裂实体；**六类广告行三层判定函数** + **必做的反向验证**（第一版裸 `/无广告/` 把「无广告的阅读体验确实舒服很多」这种正文也删了）；附实测广告变体清单与代价风险

### 难点方法论专题（13 篇 · 2026-09-14 批量沉淀）

> 从 20+ 个生产书源的历史记录中提炼的**跨站可复用**难点，按"T0 高频再现 / T1 单站高价值 / T2 工程方法论"分层。每篇含：现象谱系 → 源码级依据 → 解法阶梯 → 开箱模板 → 避坑清单 → 案例档案表。

**T0 — 已在 3 个以上源反复再现**

- [references/方法-AnalyzeByJSoup状态污染与绕开总表.md](references/方法-AnalyzeByJSoup状态污染与绕开总表.md) — ★**最高频难点(8+源)**：同实例连调CSS索引规则→字段取空/串位/行分隔符被吞三张脸；`AnalyzeRule.kt:151`实例缓存源码实锤；"书籍总数:1"完整链路；新旧实例对照法复现；四级解法阶梯(@js直取/XPath免疫/结构规避/微型测试源)；result Element vs String 类型矩阵；10条避坑+一分钟口诀
- [references/方法-Cookie标记型限频破解.md](references/方法-Cookie标记型限频破解.md) — ★**6站同款机制**(ppxsw/book630/xuken/ggd66/35sw/lianaiya)：服务端只查Cookie键存在不校验值→永久绕过；三类限频(A/B/C/D四实验)鉴别决策树；`cookie.setCookie`整体替换语义巨坑；本App Cookie API可用性清单；IP级惩罚窗口与离线验证法；loginCheckJs倒计时透传；POST+retry的oneShot坑
- [references/方法-正文跨页重复输出与整页去重.md](references/方法-正文跨页重复输出与整页去重.md) — ★★★**分页站正文的第二种病：站点把整章重复输出 N 份**（m.juzhishuwu.net 蓝本，《完美世界》序章 85 行 = 同一章 5 份）：与「跨页断字」同族但更阴险 —— 每份正文都通顺、无特征词，**任何广告关键词黑名单都命中不了**，过滤后仍是 4 倍长度；★★**判据 A（页内重复）**：`#content` 里 `提供的《` 或 `(第\d+/\d+页)` 标记出现 ≥2 次 → 切行时遇第 2 个标记就 `break`（`arr.length>0` 条件必须有，第 1 份的标记在首行要跳过不能 break；标记要覆盖 **HTML 实体形式** `&lt; "https:"&gt;提供的《`，因为 `Element.html()` 会转义 `<`）；★★**判据 B（跨页重复）**：`_2.html` 开头正好是第 1 页尾部 → 整页与已收内容**连续 3 段一致**则跳过（只回溯最近 60 段防 O(n²)；只比 1 段会误杀「”好。“」这类高频短句；`Math.min(3,page.length)` 兜住尾页）；★**为什么过滤广告行救不了**：85 行过滤后仍 74 行，重复段落原样保留；★**广告行 `< "https:" >` 里没有 `//`**，`/https?:\/\//` 完全漏掉，必须写 `/https?:\s*"/`；★`作者有话要说…` 不是广告（实测 5 章都有，删了会丢作者话）；★验收数据 6 本书（完美世界 85→16 行 / 南瓜马车 146 行 / 唐人的餐桌 74 行 / 万神 139 行 / 港片 61 行 / 万古神帝 72 行）**残留噪声行全部为 0**；含适用站点特征 5 条 + 排查顺序 5 步
- [references/方法-搜索限频伪装的间歇性错误页.md](references/方法-搜索限频伪装的间歇性错误页.md) — ★★★**杰奇CMS 搜索限频不返 429，而是 HTTP 200 + 974 字节「出现错误！」页**（m.juzhishuwu.net 蓝本，App 内 MCP + Python 双通道对照实验）：错误文案「对不起，两次搜索的间隔时间不得少于 30 秒」，导致三个误判方向（规则写错 / 关键词没这本书 / cookie 卡了）；★★**三条判据缺一不可**：`'出现错误' in html` + `len(html)<2000` + `id="nr"` 计数为 0（正常「0 结果」页也 `nr==0`，但长度 ~4700 且标题是 `<关键词>-搜索-桔纸书屋`）；★★★**六组对照实验**：A 同 session 连发 → 第 2 次起报错；B 每次新 session → **仍报错**（排除 cookie）；C 伪造 `jieqiVisitTime=jieqiArticlesearchTime%3D1` → **仍报错**（排除时间戳）；D 换 UA → **仍报错**（排除 UA）；E 静默 45s 单发 → 成功；F 静默 45s 后**连发 5 次全部成功** ⇒ **不是「每次都要隔 30 秒」，而是「窗口内配额约 1~2 次」**；★★**bodyJs 自动重试实测无效**：`bodyJs` 里能拿到 `java.ajax`/`baseUrl`/`Packages.java.lang.Thread.sleep`，但窗口是 30 秒级，重试 2~3 次 × 3 秒全失败，且会卡住搜索线程（Legado 搜索有 30 秒 `withTimeout`）⇒ **正确做法是写进 comment，不做重试**；★已实测失败的绕过手段 7 种（清 cookie / 伪造时间戳 3 种写法 / 换 UA / `&_r=` 绕缓存 / `searchtype=all`）；★同站**搜索假分页**：`page=2/3` 返回与第 1 页完全相同的 30 条（页内 `<strong>1</strong>` 也不变）→ `bookList` 里 `page>1` 直接 `return []` 短路，否则无限翻页；含 6 步排查 Checklist
- [references/方法-搜索签名失败伪装成空结果.md](references/方法-搜索签名失败伪装成空结果.md) — ★**`code:0` + 空数组 ≠ 没搜到**（m.dzrjk.com 蓝本）：签名/参数校验失败时服务端**不报错而是返回 `{"code":0,"data":{"search":[]}}`**，伪装成“无结果”，极易误判接口失效（本次卡 2 小时）。★★**三组对照缺一不可**：正向组（webView 让站点自己 JS 发请求）/ 反向组（故意改错签名，若与真签名返回相同则说明该参数没被校验）/ 修复组（按假设改必须出现结果）。★★★**必读发请求前的预处理函数**：本案 `search_before()` 里 `if(document.cookie!="") bgt=bgt.slice(0,len-1)`，浏览器必带 cookie 故真实请求的 bgt 永远截断——**抓到的页面内联变量 ≠ 实际发出的值**。含常见改写清单（截断/反转/拼时间戳/二次编码/条件分支/大小写）、正则字面量一次性建 map 的正确写法、`concurrentRate` 单位是毫秒（`1/2` 形同不限流）、空结果假书与 `bookUrlPattern`、`replaceRegex` 三条铁律
- [references/方法-假表单搜索接口与列表内联文本提取.md](references/方法-假表单搜索接口与列表内联文本提取.md) — ★**纯静态模板站的四个隐蔽坑（m.tkshuw.com 蓝本，check/debug 全绿）**：①★**假表单**——同站首页/分类/详情/搜索页四种 `<form>` 声明三种形态，实际只有 `GET ?nf=` 有效（`POST s=` 直接 404；**`GET ?s=` 返回 200+100 条默认推荐列表但和关键词无关=最危险**）→ 必须用"确定存在的书名能搜到 + 确定不存在的词 0 条"双向验证；②★**列表内联裸文本**——`div.s_list` 里无任何子标签，书名在 `<a>`、作者是 `/` 后裸文本、分类是行首 `[xx]`（仅分类页有）且分隔符空格不固定 → 用 `@js:` + `result.text()` + `lastIndexOf('/')`（书名可能含 `/`，不能 indexOf）；③★★**`@js:` 里 `result` 是 Element 不是字符串**（源码级：AnalyzeRule.getString 由上游规则返回类型决定，`String(element)` 得对象地址 → match 静默返回 null，日志有 `┌获取分类`/`└` 但值为空=静默失败指纹）→ 先判 `result.text` 是不是函数；④★★★**`nextContentUrl` 取不到必须 `return null` 不能 `return ''`**（源码级修正《目录顺序与章节去重铁律》既有结论：`getStringList` 里 `result==null→return null` 干净短路；而 `''` 会进 `isUrl` 分支被 `getAbsoluteURL(redirectUrl,"")` **拼成当前页 URL**，多发一次请求且 `本章总页数` 日志消失）→ 通用规则：**所有"取不到就不拼"的 URL 类规则（nextContentUrl/nextTocUrl）优先 return null**。另含封面 id 拼凑法、`wrap-box` 容器差异导致 search/explore 必须分开写 bookList、站点自身截断（`_2.html` 与主页 md5 相同）与死章节的甄别、MCP 全链路验证记录
- [references/方法-legado各版本行为差异对照.md](references/方法-legado各版本行为差异对照.md) — **跨版本分发必读**：LT/官方/legado-E(Lyc)三版22项差异总表；★头号差异=列表规则返回值协议(E版无Mode.Js分支→必须JSON字符串数组+纯键名)；★新增「故障指纹」(列表大小有数但书籍总数为0=整条被丢弃+BookList.getSearchItem判据是书名非空→封面简介一并丢)+真机Rhino三条对照法+勿改字段规则迁就；E版java.get/head/post的headers是Map不接受null→两版通用java.connect；Kotlin属性vs方法`gv()`；三作用域能力矩阵；Book.type位掩码4/8/32/64与刷目录冲掉type；-100 Cookie配对错乱三层真相；API存在性判定方法论(含ppxsw误判复盘)
- [references/方法-URL模板与DNS选线.md](references/方法-URL模板与DNS选线.md) — `{{}}`**每次请求二次求值**⇒动态域名自愈；模板七坑(空段整段吞/单模板小写化/`$`未定义/searchUrl@js静默降级/裸引号毁JSON/双JSON→NPE/真实换行)；URL选项全清单(dnsIp/retry/timeout)；`buildScopedDns`只劫持本域+去Cronet+与proxy互斥；hosts池测速选线闭环；探针法看最终URL；变量双通道+Rhino JsNull truthy

**T1 — 单站点但难度封顶**
- [references/方法-站点自建土盾与CF盾双域名切换体系-西瓜书屋.md](references/方法-站点自建土盾与CF盾双域名切换体系-西瓜书屋.md) — ★**「主站CF+备用域站点自建土盾」双域名切换体系**（西瓜书屋 xiguashuwu2 蓝本）：土盾vs CF盾甄别表（安全验证无_cf_chl_opt=站点自制算术题设恒定Cookie nginx_waf_passed=1，直接带Cookie免验证；CF managed challenge 必须真浏览器）；**登录面板切换网址按钮**（xgHosts白名单+setVariable存当前域+setCookie种土盾+viewName动态显示当前站，action统一FQ_xxx(jv,sv)显式传参）；**全站跟随关键=规则全部相对路径**（isUrl按当前书源URL拼绝对地址，切站书架旧书自动跟随无需迁移）；★★**CF loginCheckJs 正确姿势=弹带关键词的baseUrl**（旧写法 removeCookie 删掉刚过的盾+弹空搜索页丢关键词→LT版每次都弹验证且拿不到词的根因；正确=u=baseUrl含关键词，过盾refetch自动重放搜索，**绝不 removeCookie**）；★正文三形态适配器（静态#C0NTENT/UpWz乱序 slots[v-(i+1)%code] 实证/AES newcon——md5前16=**iv**后16=**key**与直觉相反，meta client=md5[8:24]自校验，java.createSymmetricCrypto('AES/CBC/PKCS5Padding',key,iv)）；simishuwu空格间隔广告变体正则；★App Web API 全链路实测通道（MCP断连替代：POST /saveBookSource单对象/GET refreshToc/getBookContent?url=&index=，x-legado-token鉴权；探针法=content里throw Error(中间变量)从errorMsg回传全部中间值；正文按bookUrl+index落盘缓存→改规则要用没读过的index验证）；案例 examples/西瓜书屋_xiguashuwu2_多域名切换.md
- [references/方法-CF盾双版本行为差异与书源运行时自适应.md](references/方法-CF盾双版本行为差异与书源运行时自适应.md) — ★★★**「同一CF站两版行为相反」的分版本运行时自适应**（西瓜书屋实锤，此前从未沉淀）：行为矩阵（LT=指纹放行型弹窗直进页面无验证→webView:true；E=webView恒60s超时但人工过盾cf_clearance持久→OkHttp+loginCheckJs）；**searchUrl @js: 版本探针** `typeof source.getLoginUiJs==='function'`（LT独有方法）分通道路由开箱模板；★webView通道5条机制认知（BackstageWebView直载不经OkHttp/无JS默认900ms须显式webViewDelayTime/请求不进HTTP日志/URL选项布尔解析/Cookie自动落库）；★loginCheckJs配套铁律（弹带关键词baseUrl/绝不removeCookie/return result）；Rhino双铁律（content <js>必须IIFE+return、跨try/catch变量顶部var——node测试桩必须从JSON提取同源测试）；正文第四形态「明文容器干扰页」与plainLen四层判据；check_source对CF站source verification cancelled=预期行为；★261029追补源码级铁律：**loginCheckJs 的 baseUrl=bookSourceUrl(主页)非请求URL**、**过盾弹窗必须弹会被挑战的页**(弹首页→200无_cf_chl_opt→saveVerificationResult永不触发→「验证结果为空」)、**searchUrl 返回相对路径会导致切站变量完全失效**(搜索入口baseUrl恒为bookSourceUrl，必须返回绝对URL)、startBrowserAwait 必须 try/catch + 回包洁净度校验(>500且无CF标记)否则静默0结果；★★**镜像透明兜底**(`java.connect(url)`返回真StrResponse且带source header/Cookie，`checkRedirect`只记日志不换源 ⇒ 可在loginCheckJs里直接把镜像站结果当搜索结果显示，用户无感、不改域名，且bookUrl相对路径自动跟随镜像域名)；★★**土盾站禁止用webView通道**(BackstageWebView拿土盾页→0结果，土盾站只能OkHttp+恒定Cookie)；★反模式：用`source.setVariable`自动切站做过盾兜底会静默污染用户域名且持久化，禁用

- [references/方法-字体反爬三代方案演进.md](references/方法-字体反爬三代方案演进.md) — A图标PUA/B会话置换/C加密三型判别；★离线字形位图匹配建表全算法(包围盒裁剪+高斯模糊+L2归一化+矩阵乘+双参考字体融合+margin置信度筛)；固定guard Cookie锁定会话；**生产级运行时加载代码**(外置托管+哨兵校验+未知字原样保留+书籍级变量缓存)；getVariable语义澄清；97%精度的分层兜底
- [references/方法-多层密钥AES与轮换签名逆向.md](references/方法-多层密钥AES与轮换签名逆向.md) — 密文分型表；密钥定位四法(JS枚举/文件名随机→`?_=`回源/响应头旁路/信封自解)；动态种子信封(wendulou)；★**IV构造铁律**：`md5Encode`返回hex非raw digest、**首块乱其余好=IV错/全乱=key错**；晋江DES+头派生；★**花括号配平法**兼容每日轮换签名；随机对象名base64；破坏性单变量实验找真校验项(省90%工作量)
- [references/方法-图片不显示排查总表-加密之外的三条路.md](references/方法-图片不显示排查总表-加密之外的三条路.md) — 四象限归因；★**verify签名不绑主机**⇒自由换CDN主机(矩阵对照法)；SNI封锁→查CNAME换CDN原生主机名；★`blockNetworkImage`源码真相⇒`data:`内置封面完整方案(五护栏+候选链+状态回显)；根路径判活法与HEAD被拒陷阱；`imgPattern`硬性双引号约束；`java.webView`真机渲染探针；沙盒会完全误诊
- [references/方法-WAF与CF间歇故障及站点判活.md](references/方法-WAF与CF间歇故障及站点判活.md) — ★**判"站点失效"前的七维复测矩阵**+ggd8误判复盘；WAF家族分型表(自研挑战/GoEdge/CF挑战/CF抖动/1034/裸UA/限频/需登录)；**UA三种作用**(放行·模板分发·完整UA反被RST)；GoEdge POST强制人机；间歇TLS RST四件套(retry+异常文本校验+梯度等待+冷连接)；自伤型故障与离线验证纪律
- [references/方法-GFW-SNI封锁鉴别与绕过边界.md](references/方法-GFW-SNI封锁鉴别与绕过边界.md) — ★**「TCP 通 ≠ 能连」**：TCP几十ms通但TLS瞬间RST=**SNI域名黑名单**（区别于DNS污染的超时）；**30秒定性实验**（同一IP只换SNI，`cloudflare.com`做对照）；已被证伪的**9种SNI绕过写法**；★★**「无SNI」技术**（`createSocket(up, IP字面量, 443, true)`→JSSE按RFC 6066省略SNI）；★★★**Legado 自带 Cronet(QUIC) 且默认关闭**（设置→其他设置→Cronet；`enableQuic(true)`；libcronet 从 storage.googleapis.com 下载，**实测国内可达**）；**三条上游缺陷**（`HostResolverRules`被注释 / `dnsIp`与Cronet互斥 / `dns{}`只装okHttp）；**错误格式鉴别法**（`failed`小写=OkHttp，`Failed`大写=Cronet，`ERR_CONNECTION_TIMED_OUT`=DNS污染，`ERR_SSL_VERSION_OR_CIPHER_MISMATCH`=SNI是IP）；**完整vhost映射表**；**Glide天花板**；手机侧DoH可信度表；**22条避坑**；案例档案（IllustFerry/Pixiv-Shaft/pixez/ppxsw）
- [references/方法-付费墙与假登录墙甄别.md](references/方法-付费墙与假登录墙甄别.md) — ★**"请登录后继续阅读"多半是假登录墙**(63sg/35sw实测登录后仍锁)；五步甄别流程；登录态判据优先级(仅登录态渲染元素>入口链接>文案哨兵)；三级付费粒度处置；**SEO假正文陷阱**与四条防御；用户提示文案设计四原则；章级兜底不让整目录崩；9站对照档案表(同为"请登录"63sg假墙/ppxsw真墙)

**T2 — 工程方法论（最救命）**

- [references/方法-书源交付质量闭环.md](references/方法-书源交付质量闭环.md) — ★**"保存成功"≠"保存对了"**；六步流水线；`save_source`三语义(整体替换误传清库事故/同URL REPLACE/重置respondTime)；构建脚本四类自身bug(正则跨块吞锚/漏`+Q+`/`%`渗JS/heredoc吃引号)；零双引号零反斜杠纪律；**N字段md5回读闭环**(150字符分段二分+charCode逐字)；UTF-16vs码点/`getBytes('UTF-8')`不存在；dpaste+深链大源通道；30项交付checklist
- [references/方法-静默失败定位与探针法.md](references/方法-静默失败定位与探针法.md) — **"不要推理，要打印"**；13类静默失效总表；★IIFE漏return一个源三连犯(三字段三种症状)；四种探针(微书源+废域名看HTTP日志/eval_js真机离线复现/最小对照源/破坏性矩阵)；Rhino-jsoup语法坑合集；反射与内部类探测($后缀/getClass返回null)；症状→探针定位流程；三句口诀
- [references/方法-目录顺序与章节去重铁律.md](references/方法-目录顺序与章节去重铁律.md) — 两条源码级铁律(URL去重+不替你排序)；链式保序vs并发错序；★**"并发抓全页"能否用的判定**(详情页是否内联章节)；六类脏数据(倒序区/隐藏副本/幽灵页/镜像陷阱页/死章/占位项)；黄金特征class；aID≠章节序；虚拟章节fragment造法与污染清洗；`tocUrl`位置约束；串章三防护+`&nbsp;`碎片正则；★★**终止信号源码级修正(260122)**：`nextContentUrl`/`nextTocUrl` 末页一律 `return null` 而非 `''`（`getStringList` 里 `''` 会被 `getAbsoluteURL` 拼成当前页→白发一次请求+`本章总页数`日志消失；`null` 走 `result==null→return null` 零请求）；顺序0违规验收法；12站档案表
- [references/方法-详情页交互按钮选型树.md](references/方法-详情页交互按钮选型树.md) — 五通道(usehtml@onclick/useweb活视图/正文虚拟章节/订阅源/`legado://`深链)完整决策树+能力边界总表；★**"`@onclick`跑Rhino不看`@JavascriptInterface`注解"**⇒useweb调不到的startBrowser在按钮里能调；20项桥能力矩阵；实时取签名直链防过期；`substring`截断陷阱六约束；`activity=null`静默失败；三档实现模板；java.webView验证法
- [references/方法-详情页写操作按钮与关系态显示.md](references/方法-详情页写操作按钮与关系态显示.md) — ★**关注/收藏/点赞这类“改服务端状态”的按钮怎么做**：源码级实锤**本App动词白名单 `RequestMethod{GET,POST,HEAD}`，URL选项写 `method:"DELETE"` 会被静默降级成 GET**（AnalyzeUrl.kt:268）→取消类操作在书源侧不可能；三条POST覆盖绕路(`?_method`/`X-HTTP-Method-Override`/body)与原始TLS套接字手写DELETE实测**全部作废**（CF Read timed out）；★**从站点自己的 main.js bundle 里 grep API 定义表**一次拿到「路径+参数是UUID还是用户名+动词+幂等返回体+i18n官方文案」；★**关系态√四层阶梯**（L1业务响应内嵌 `user.following`/`liked` 随 loginHeader 免费下发→L2专用接口→L3本机账本10min填空窗→L4显式核对）+三态UI（未关注/√已关注/是自己/未登录整行不渲染）+显示名与onclick两套清洗；★**TTL面板三件套**（自愈补拉+冷却戳写在发请求之前+显式🔄强刷）与**哨兵空头支票检查法**（grep键名确认有写入方）；幂等POST会伪装成功（判返回行id）；按钮上限要对齐真实账号数据量（12 vs 真机14）；**新断言必须先负对照（跑旧版必须挂）再谈通过**；18条避坑+iwara v6.3→v6.5案例档案
- [references/方法-云反代破封锁-Netlify实战.md](references/方法-云反代破封锁-Netlify实战.md) — ★**被墙站点+REST API 的云反代总纲（pixiv 免梯直连蓝本，check 实测通过）**：三大认知修正（①pixiv 只按 ASN 封——CF 边缘 403/Deno 平台 SUSPENDED 但 **Netlify(AWS 出口)放行** ②书源 pxproxy 拼装是「单协议格式」`反代域/app-api...`，反代必须自动补协议否则 400 bad ③Netlify Edge Functions 默认 Edge Access 保护须设 Public）；开箱 Netlify Edge Function 代码 + netlify.toml + 部署四步（手机全程）；云平台选型对照表（CF 系出局/AWS 系首选/住宅 IP 终极保底）；DNS 投毒矩阵（腾讯 DoH 真实 IP，阿里与 UDP53 全投毒→DoT 只能填 dns.pub）；Cronet 自定义 Hosts 危害（customHost→SNI=IP→CF 拒）；故障速查 400/401/403/404/502；K1~K14 避坑 + 移植改动清单
- [references/方法-深链保存书源与dpaste通道.md](references/方法-深链保存书源与dpaste通道.md) — ★**「上传只是半程，唤起才算交付」**：`legado://import/{path}?src=` 深链全谱(path 全表/AndroidManifest exported+BROWSABLE/5 处触发方/`src` 六种形态含 `#requestWithoutUA`)；★**唤起导入三步走**(造文件→上传中转→`java.openUrl(深链)`)与**成功硬证据=HTTP 日志 `GET raw -> 200`**；★**三类资源格式差异表**(订阅源 URL 分支强制 `fromJsonArray`→**单对象必报 `Expected BEGIN_ARRAY but was BEGIN_OBJECT`，永远写数组**；书源/TTS 单对象亦可)；dpaste API 契约实测(尾斜杠/`expiry_days` 1~365/`expiration_days` 拼错→静默 7 天/`.txt` 非 `.raw`/429→伪装成「XML 语法错误」的完整机制链)；三条投递通道对照(深链/网络导入/扫码)；K1~K28 避坑；`scripts/dpaste_upload.py` 一键上传+字节校验+打印唤起代码；正/反向端到端实测留档

- [references/方法-禁漫天堂AppAPI书源-图片行块乱序还原.md](references/方法-禁漫天堂AppAPI书源-图片行块乱序还原.md) — ★**禁漫天堂 jasmine 同款 App API 直连书源（check 1/1）**：网页通道被白盾双杀后唯一稳路=App API 通道（cdngwc 系域名与网页 18comic 系无关）；token=md5(ts+'185Hcomic3PAPP7R')+AES-256-ECB(同 md5 为 key)；**ts 无时间窗校验**（3天前 ts 测通）→ 变量半固定+401自愈；域名池从 BytePlus newsvr-2025.txt AES 解密获取（jasmine 旧主域已死）；**解密 ts 必须与请求 ts 绑定 **→ 搜索/详情/目录/正文规则统一 jsLib `jmget()` 自建请求（header 只保主请求 200，踩中 SyntaxError Unexpected token 后改架构）；**图片行块乱序还原**=imageDecode 钩子 + Bitmap/Canvas 块倒序（rows=md5(aid+文件名)末 ASCII 码 %10/8*2+2，jasmine Rust 与 jmcomic-python 三方一致）；封面无 UA 被拒→URL 选项 headers；登录界面 API/图床每条线路一个按钮=切换+测延迟+toast 结果；K1~K10+6 步验证

- [references/方法-切片签名头与响应加密状态漂移.md](references/方法-切片签名头与响应加密状态漂移.md) — ★**站点悄悄加请求头校验时的定位与适配总纲**（acfan.com v15 蓝本，check 1/1）：★★**缺头静默失败**=HTTP 200 + `content-length:0`，零报错，唯一可靠定位法是**四组对照实验**（旧版号无ts/新版号无ts/旧版号有ts/新版号有ts——只跑两组会得出错误结论）；★★**切片式签名**=`s=md5(t.substring(3,8))`（防逆向的轻量手段，直接 md5 整串会失败；逆向用「暴力试所有 start×len」脚本）；★**敏感接口 5 头**（`X-Sensitive-Action/X-Request-Timestamp/X-Request-Nonce/X-Request-Body-SHA256/X-Request-Signature`），★**bodySha 必须用「键名升序的紧凑 JSON」**（`json.dumps(...,sort_keys=True,separators=(',',':'))`，与抓包逐字节 MATCH 验证）；★★**响应包裹三态化**（同一站点不同接口返回 `{code,msg,data}` / 顶层直出 / `{data:[...],domain}` 三种，写 `AC_unwrap` 统一取业务数据）；★★**encData 双兼容必写**（同一接口匿名明文/登录密文，`o.encData ? 解密 : 明文`；`Base64.decode(enc,2)` 第二参 2=NO_WRAP）；★**登录态权威探针**（`POST /api/user/base/info` → 200 有效 / 301 刷新token / 1001 token解析错误，比「页面含某元素」可靠）；★工程纪律（带连字符头键名必须加引号 `'User-Mark'`，`node --check` 唯一能提前抓；新增内容形态同步改 6 处；book.type 位掩码 text=8/audio=32；提示型虚拟条目 URL 要能被 AC_id 友好识别）；含开箱模板+验证清单+与「Cookie标记型限频」的边界对照

- [references/方法-文本文件混淆头与媒体域切换.md](references/方法-文本文件混淆头与媒体域切换.md) — ★**文本正文文件带混淆头 + 同一资源多域择优 + 内联JS页面语法校验**（acfan.com v16 蓝本，check 1/1）：★★**文本文件混淆头**=网页能读、规则读到乱码（ACFAN 每个 .txt = **101 字节混淆头 + UTF-8 正文**，头前4字节固定 `a3c1a3c1`）；解法=`bodyAsBytes()` 后**扫描第一个合法 UTF-8 中文**（E4-E9+80-BF+80-BF）自适应去头（**不要写死 101**，别站头长会变）；★★**同一资源多域**=响应里给的两个域可用性不同（`playPath` 域 403 返回 16 字节 JSON，`mp4Domain + fictionUrl` 才是真地址 2MB ID3）；判活必须看**内容特征**不能看 HTTP 200；★★**有声小说必须强制 `book.type=32`**（audio；video=4/text=8），否则调起视频播放器黑屏；**必须在 chapterList 设**（init 会被 removeAllBookType 冲掉）+ 正文规则双保险；★★**内联 HTML/JS 页面用 `String.fromCharCode(34)` 造引号必须成对**（`+'var SRC='+Q+m3u8+Q+';'`，漏一个 `+Q+` → 整段 script SyntaxError 静默失效，症状「点了播放没反应」）；`</script>` 写成 `'<'+'/script>'`；加 **CDN 递归兜底**（jsdelivr→unpkg→cdnjs→fastly）；**H5 发现页按站点分类体系重建法**（抓分类接口逐 type 枚举→完整分类树）+ fiction 过滤参数实测（`fictionType=1/2` 分离文字/有声、`classId` 有效、`tagId` 无效）；K1~K17 + 验证清单（含 §8 标签数组参数 tagIds/tagType双体系/编码前缀冲突、§9 **发现页排布优化：固定 `layout_flexBasisPercent` 列数会被 divider 挤成竖排→唯一稳解 `layout_flexGrow:1` 自动流式** + 标题长度控制 + 样式分布验证法）

- [references/方法-按作者列作品-API参数逆向.md](references/方法-按作者列作品-API参数逆向.md) — ★**「按作者/UP主/画师列作品」做成合集书**（iwara v13 蓝本，check 2/2）：核心=**书籍URL直接指向可用的作品列表接口**（bookUrl本身可请求→IWRINIT短路）；目录=每一条作品；`nextTocUrl` 链式翻页（off+len<count 返回下一页否则空数组）；★★**参数逆向关键**=`GET /videos?user=<作者UUID>&page=N&sort=date&limit=50` —— **参数名叫 user 但值必须是 UUID**（传用户名 count=0、传 `userid=` 会返回站内热门流=最阴的坑）；★★**响应归属校验 IWRRAFVFY**（authorId 是 UUID + `results[].user.id` 匹配请求 uid，否则 throw——没有这步用户会看到别人的视频）；破局方法=查 GitHub 开源实现（yt-dlp 的 IwaraUserIE）比盲试参数快一个数量级；详情字段从 init 注入的 `__au_uid/__au_un/__au_pg` 读；kind 显示总数/页数/分桶；深链 `legado://import/addToBookshelf?src=` 一键加入书架；K1~K10 避坑（results 归属校验/正则 `[/]videos[?]` 恒不匹配/非捕获组旧Rhino不可靠/未登录也要显示「📚 全部作品」/startBrowser 传 API URL 用户看不到内容→构造网页 URL）

- [references/方法-资源上限放开与静默截断排查.md](references/方法-资源上限放开与静默截断排查.md) — ★**书源内「自定义资源」上限放开与静默截断排查**（iwara v10 蓝本）：★★**三遍扫描法**（grep 所有 `substring/slice/splice/limit/max` 找硬编码上限）；**IWRMAX 统一上限三原则**（书源变量可覆盖 + 分类硬护栏 + 按单位分类：条数2000 / budget 单列 3600000）；实测 8 处硬编码上限（域名池 40→200 / 保存 40→200 / 测速 40→200 / UI 14→40 / 测试 12→60 / budget 40000ms→120000ms / probe tried 3→12 / order 5→40）；★**按实测延迟重排域名池**按钮（权重：通ms升序→不通→未测）；★无点域名补 `.iwara.tv`；非 `*.iwara.tv` 域名直接放行；**K1~K10 踩坑**（含 §10 **探测必须走与实际使用同一通道**——探测不带 dnsIp 走 Cronet 会系统性误判，比不探测更糟 / 环境错误与目标错误必须区分 / 两行对照实验锁定通道归属）

- [references/方法-晋江书源高级技术拆解.md](references/方法-晋江书源高级技术拆解.md) — ★**晋江文学城（VIP 付费站顶级案例）**：★★**双层密钥反爬** = 固定 DES/CBC（KW8Dvm2N / 1ae2c94b）+ 响应头 `accesskey/keystring` 派生；多接口拼装（搜索/详情/目录/正文/购买走 4 个域名 5 个接口）；动态密钥 + 扫码登录 + 余额预查 + 批量预取 + `data:` URL 自销毁；13 章 + 12 个可复用代码片段；配套案例 `examples/晋江文学城_www.jjwxc.net.json`

- [references/方法-登录注册验证码与限频破解.md](references/方法-登录注册验证码与限频破解.md) — ★**登录·注册·验证码·限频破解主干方法论**（ppxsw 蓝本，lyc 修改版 App）：`dl()`/`zc()` 双函数骨架 + `java.getVerificationCode` 图形验证码（★**API 存在性必须在真实调用上下文实测**——eval_js 独立环境探测 undefined 不代表 loginUrl/loginUi 上下文不可用）+ MD5 密码 + `search_time` Cookie 标记型限频（服务端只查键存在不校验值）+ base64 反爬；登录 UI 最佳实践（`loginUrl`=顶层具名函数集 / `loginUi` 按钮 action 直接调函数名 / 成功后 `java.getCookie()+source.putLoginHeader()` 持久化）；补充篇见下条

- [references/登录注册验证码与限频破解实战-ppxsw篇.md](references/登录注册验证码与限频破解实战-ppxsw篇.md) — 上条的同站全要素实录补充（UA 双模板 / 目录乱序 / `tocUrl` 位置坑 / `cookie.setCookie` 整体替换语义 / 注册接口参数与登录不同名 / 验证码 `code.jpg` 响应 Set-Cookie 绑会话 等推导全过程）

- [references/方法-Legado密码学能力全景与作用域差异.md](references/方法-Legado密码学能力全景与作用域差异.md) — ★★**「Legado 到底能算什么」的全量实测底座**（红果 X-Argus 复现过程中发现既有 `方法-加密解密.md` 只是官方 JsHelp 抄本，无算法矩阵/无作用域差异/无坑位）：★★★**三作用域差异实测对照**（同一段代码：`eval_js` 顶层 eval = `java.*` 全可用；**函数写进 jsLib = `java.*` 全部变 object 不可调用**（不止 ajax！）；写在 `@js:` 规则 = `java.*` 全可用）⇒ **jsLib 里只能用 `Packages.*` 或参数注入 `f(JV)` 传 java**；★★★**算法支持矩阵（逐项真机实测）**：摘要 `MD5/SHA-1/256/384/512/**SM3**/SHA3-256/BLAKE2B-256`（SM2 ❌ 是非对称）、HMAC `HmacMD5/SHA1/256/384/512/**HmacSM3**/SHA3-256`、对称加密 `AES(ECB/CBC/CTR/GCM/OFB/CFB/NoPadding)` + `DES(ECB/CBC)` + `DESede` + **`SM4(ECB/CBC)`** + `Blowfish/RC2/RC4/ChaCha20`；★★**byte[] 互转唯一可靠姿势**（`Array.newInstance` 不可用 ⇒ `String`+`ISO-8859-1` 往返）；★★`decryptStr` **自动识别 Hex/Base64**（`SymmetricCryptoAndroid.kt` 源码：`if(data.isHex()) HexUtil.decodeHex else Base64.decode`）；★官方 API 覆盖不到时的两条后路（`Packages.javax.crypto.Cipher` 手写 / `new Packages.org.bouncycastle...SM3.Digest()` 绕 provider）；★12 条避坑（`md5Encode` 只接受单参 / 无 `java.decodeURI` / `setIv` 只收 byte[] / AES 只收 16·24·32 字节 key / 无 `encryptToString` / SM3 必须 `new SM3.Digest()`）；★**作用域探测方法论三轮对照表**（顶层 eval 会给出**完全相反**的错误结论，必须写进 jsLib 或 `@js:` 规则实测）
- [references/方法-字节跳动X-Argus签名纯JS复现与红果短剧API书源.md](references/方法-字节跳动X-Argus签名纯JS复现与红果短剧API书源.md) — ★**客户端签名型 API 书源总纲（字节系）**（红果短剧 api5-normal-sinfonlineb.fqnovel.com 蓝本）：★★★**X-Argus/X-Gorgon/X-Ladon 三件套纯 JS 复现**——社区普遍认为需 unidbg 模拟 so 库，实则只是 **SIMON-128 分组密码 + SM3 哈希 + AES-CBC 外壳 + protobuf 手工编码**，全部可在 Rhino 内跑通，无需外部签名服务；★★**BouncyCastle SM3 在 Legado 可用**（`new Packages.org.bouncycastle.jcajce.provider.digest.SM3.Digest()`，`MessageDigest.getInstance("SM3")` 会抛 NoSuchAlgorithmException，实测 SM3("abc") 与标准值逐字节一致）；★★**byte[] 互转唯一可靠姿势**（`Packages.java.lang.reflect.Array.newInstance` 在 Rhino 不可用 ⇒ 借道 `String` + `ISO-8859-1` 编码往返，0x00-0xFF 无损）；★★**jsLib 里 `java.ajax` 是 object 不是 function**（老坑第 N 次复现）⇒ 所有联网函数把 `java`/`source` **作为参数显式传入**（`HG_API(JV, path, body, extra)`）；★★**列表规则必须返回 JS 数组**（LT 版 `getElements` 对 `Mode.Js` 只接受 List/Array，返回 String 直接得空列表）⇒ 数组元素各自 `JSON.stringify` + 字段规则用 `$.name` 纯键名（LT/E 双版本通用）；★★**签名失败与参数错误的严格区分**（`code:101000` + `debug_info:"pack ret empty"` = 签名不过；`code:100001` + `"video platform invalid, param:0"` = 签名已过、业务参数缺失）；★★**红果接口全档案**（`multi_video_detail/v1` 全集列表 / `multi_video_model/preload/v1` 播放地址必须带 `video_platform:1024` + `mixed_video_id_map` / 搜索与发现走网页版 `/search/{kw}` 与 `/rank/hot-drama` 的 `"searchList":` 内嵌 JSON）；★**参数容器 URL 模式**（假 URL 携带参数不发请求，规则内 `@js:` 直调 API，天然规避 GET 语义）；★**网页版 vs API 版能力对比表**（网页版仅前 3 集且第 4 集 404，API 版全集 + 5 档清晰度 + 明文 MP4 无 DRM）；K1~K18 避坑清单 + 分层验证法（密码学原语→签名生成→签名有效性→业务接口→直链可播→全链路→官方校验→字段 md5）
- [references/方法-正版App协议逆向与本地缓存书源-QQ阅读.md](references/方法-正版App协议逆向与本地缓存书源-QQ阅读.md) — ★**正版 App 协议逆向 + 本地缓存型书源总纲**（book.qq.com「QQ阅读(纯本地)」蓝本，jsLib 396KB / loginUrl 76KB / 规则全 @js）：★★★**官方 `{"type":"hex"}` URL 选项**（AnalyzeUrl.kt:461 源码实锤：`if (type != null) return StrResponse(url, HexUtil.encodeHexStr(getByteArrayAwait()))`）——把二进制响应以 hex 送进规则，是「加密 API 站」的地基；★三条硬约束（拼在 URL 末尾用英文逗号 / 同 URL 不能既要 hex 又要文本 / 长度恒为字节×2 可自校验）；★★**自实现完整密码学栈**（SHA256/AES-256-CBC/CTR/DES/CRC32/MD4/自定义哈希/Inflate + 自定义信封 nibLk「算法由内容哈希驱动，两条路径都要实现」）+ **原生 Java 与纯 JS 双实现互备**（`natCtx()` 用 `Cipher.getInstance` 调用即验证可用性，类存在≠provider 可用；原生 1.7ms vs JS 数十ms）；★★**响应头部指纹校验**（`peekId` 读密文头 0x80 字节数字串，与上次成功指纹比对，不一致直接拒）——防密钥池漂移时「解出垃圾当正文」；★★**试读/全文双态缓存**（`{"t":...,"p":1}` 标记，购买成功后主动丢弃）；★★**服务端拒绝包显式识别**（tar 内 `info.txt` code 负数 ⇒ 抛错，**绝不返回可疑文本**，因为缓存会把它沉淀成长期故障）；★**tar 容器解析三易错点**（size 是八进制 / 数据区 512 对齐 / 结束标志首字节 0）+ **一次拉 8 章只解密当前章**（`scids=100-107` 区间语法 + `qfSelArg` 保留 `-`/`,`）；★★**网络失败兜底到本地缓存**（loginCheckJs 里 `new StrResponse('http://localhost/', b)` 伪造响应让流程继续）——真正实现「离线可读」；★**设备指纹表 43 字段**（`mldt`/`sift` 都以 `dn` 结尾 ⇒ 服务端交叉一致性校验，不能单独改）+ **设备被限专用码**（code=3/-11059 ⇒ `bsDevNew()` 重生成指纹而非换 IP）；★**字段拼签**（`SIGN_FIELDS` 13 字段 + ttime + SIGN_SALT → SHA256 → BCrypt 二次哈希；大小写不敏感查找 + 缺字段补空串 + 20s TTL 缓存）；★**自管鉴权型书源标准姿势**（`removeLoginHeader()` 主动清除，绝不让 Legado 登录头与自管 Cookie 两套并存）；★**段落级评论气泡注入**（段号从 1 起 + 累计字符偏移回传 + `chapter.putVariable` 跨目录/正文传 uuid）；★**自动购买三护栏**（按书白名单 `bs_ab_list`/软硬冷却/全订月票章跳过）+ 区间解析护栏（`b-a>50000` 跳过防打爆内存）；★**searchUrl 关键词特判触发自检**（`fockselftest`/`shelfdiag`/`qfbench`，无 UI 依赖的诊断入口）；K1~K22 避坑清单 + 移植清单（必改/选改/保留三档）+ 分层验证法（hex 通道→容器解析→密钥池→单章解密→全链路）
- [references/方法-全加密API书源逆向与客户端可信重放.md](references/方法-全加密API书源逆向与客户端可信重放.md) — ★**L4 级全加密 API 书源逆向与客户端可信重放总纲**（zjread.cc 纸间双源蓝本，jsLib 7.9KB / 规则全 @js:）：★★★核心信条=**客户端能算的，书源都能算**（L4 站点假设「脚本环境没有密码学库」，而 Legado Rhino **有完整 `javax.crypto`**，无需破解服务端只需忠实重放）；★★★**五级加密强度阶梯**（L1只编码/L2固定密钥/L3同包动态密钥/**L4握手派生+请求签名**/L5客户端证明，判断错级别=浪费大量时间）；★★★**协议解剖七层模型**（握手/派生/信封/签名/响应/校验/会话，每层独立实测，任何一层猜错症状都是统一「401」无法反推）；★★**密钥派生「参数顺序反直觉」**（`l(e,r)` 内部调 `h(r,e)` → `PRK=HMAC(key=sid, msg=km)`，嵌套函数必须纸上展开，猜反必 `AEADBadTagException`）；★★**章节级密钥重派生**（`key_mode:"chapter"` 时响应回传 book_id/chapter_id，`ikm=hexDecode(hex(bid+NL+cid+NL+ver)+hex(nonce))` **双层 hex**，先算预期长度 132 字节对不上就是构造错）；★★**响应模式字段是设计者的善意**（`key_mode` 明确用哪套密钥，**缺 token 时降级为 session + code=4001**，写死任何一套都在降级路径上炸）；★★★**破坏性单变量实验**（11 组实测全 401 ⇒ 全字段强校验 + 时间戳容差 <300s，三种结果对应三种实现策略）；★★★**ALTCHA PoW 全自动**（challenge 参数明文 → 本地 `SHA256(hexDecode(salt+hex8(counter)))` 迭代 cost 次 ~1.2s → 裸 base64 payload 换 `captcha_token`，把「人机验证」降级成「本地算力问题」）；★★**明文 GET 当跨阶段参数载体**（`?zjb={book_id}` 这类 URL 永不被请求，通用模式适用于任何「POST+加密」站点）；★★**缓存自愈四设计**（会话缓存故意不存过期时间靠 401 自愈 / 重试必须换条件 / 校验最低标准是长度 + 4 种污染全自愈 / `##` 后缀天然隔离缓存）；★★**`java === source` 实测为 true**（同一 BookSource 对象，跨字段传值 `java.put('zjd')` 但键不含书籍 ID → 并发串数据）；★**独立加密子通道**（封面类 GET 无签名但校验会话，base64 转 URL-safe，**响应里的明文 URL 直接请求会 401**）；★**三级错误分类** + 可读中文消息 + 两个并存源优于一个开关源 + 移植改动清单 + 六步验证清单 + K1~K26

- [references/方法-抓包驱动的官方App行为对齐-STV篇.md](references/方法-抓包驱动的官方App行为对齐-STV篇.md) — ★**抓包驱动的「官方 App 行为对齐」总纲**（ProxyPin，STV 蓝本，check 1/1）：核心信条=**有官方 App 就抓包它**（官方请求头/参数/域名池/重试是服务端验证过的黄金标准）+ **官方 JS 是公开的**（Capacitor/WebView 壳直接 GET `/asset/*.js`，grep `url +=` 拿隐藏参数、grep `defaultDomains` 拿域名池、grep `verifyDomain` 拿探活接口）；★★**P0 崩溃定位**=规则残留 `if (m2)` 未定义变量 → 边界分支必炸，`debug_source` 堆栈直接给行号；★★**P0 性能**=混淆JS用 `btoa()` 而 Rhino 无（`typeof btoa==='undefined'`）→ eval 必败→每次走 WebView（319~457ms）；垫片 `Base64.encodeToString(new java.lang.String(s).getBytes('ISO-8859-1'),2)` 与浏览器 latin1 语义一致，但 **Rhino 与 V8 仍有执行差异** → 用「try 快路径→catch 回落」零回归结构；★★**0 字节静默失败**=A/B 对照唯一可靠定位（STV 目录接口无 Referer=0 字节）；★★**warp.php 域名探活**（200-299=alive，"yes"/"no" 是站点应答；状态会波动不能硬编码）；★**官方隐藏参数**（`&rescan=true` 重扫、`download=true&key=` 下载通道需登录）；★**本App陷阱**=`java.ajax(url+',{json}')` 返回 Java String 而非 StrResponse（`body/headers` 全 undefined，读不到 Set-Cookie）；★**沙盒≠真机**（数据中心IP与家宽被区别对待，关键结论必须 App 内 eval_js）；含完整检查清单与通用结论 8 条；§10「探活可用 ≠ 业务可用」陷阱（dns1 域名）；§11 v11.10 三修复（编号跳号/10002缓存窗口/分段打分池）；**§12 v11.11 分隔符型目录数据解析陷阱**（`-//-` 分记录 + `-/-` 分字段，平铺扫描遇「标题含 `/`」→ 🔑 丢 4379 个；服务端 `unvip` 计数当免费真值交叉验证；跨来源样本矩阵必须 ≥8~10 个）

- [references/方法-线路自愈与登录面板运维套件.md](references/方法-线路自愈与登录面板运维套件.md) — ★**多域名轮换站的「线路自愈」总纲**（八叉书库 8xsk.cc 蓝本，5 备用域名 / 35 按钮面板）：★★★**三层架构**（L3 loginUi 按钮 → L2 `source.putLoginInfo({'网址':u})` → L1 `getsurl()` 单点读取），**除 `getsurl()` 内部，任何规则都不许直接读 `source.get('网址')`**（破例必漏改→「部分功能能用」）；★★**探活三判据**（长度下限 + 反例关键词 + 正例关键词，**不能只看 HTTP 200**——劫持页/年龄闸门/维护页全是 200）；★★**只对 `BX_DEAD` 探活**（每次探整个池会慢 5 秒）；★★**发布页取址**用纯 HTTP `java.connect` 而非 `webView:true`（实测 webView 抓发布页被网络环境阻断超时 60s，纯 HTTP 406ms 拿到 7 个站点）+ `data:text/html;base64,` + `startBrowser` 注入「复制」按钮 + 域名特征白名单过滤广告链；★**测速排序取 `ok[0]`** 而非 `pool[0]`，结果全量展示成功+失败；★**重置必须保留用户资产**（账号/密码/网址/颜色），只重置开关与登录态；★★**诊断按钮 7 步**（线路→页面→验证码→Cookie→登录头→表单值，每步 ✅/⚠️/❌ 明确结论，同时 `java.log` + `longToast`）；K1~K12 避坑（含 `cookie.setCookie` 整体替换冲掉年龄 Cookie、`text` 的 action 是「值变化」回调而非点击、`loginUi` 的 `<js>` 里访问 `source` 会导致整个界面渲染失败）

- [references/方法-书源自助运维面板与站点特色功能拆解.md](references/方法-书源自助运维面板与站点特色功能拆解.md) — ★**「自带运维能力」的书源怎么做**（八叉书库 v7.1 蓝本，35 按钮 / 19 jsLib 函数）：核心信条=**把「用户报障」变成「用户自助」**；★★★**书架双向同步**（网站→Legado 用深链批量 `legado://import/addToBookshelf?src=...`，**必须 `sleep(700)` 否则 7 本只进 2~3 本**、必须带 `,{"origin":"{bookSourceUrl}"}` 防被别的源抢、**书架 id 是 `aid` 不是 `bid`**、三层解析兜底卡片→全页扫→正则、`seen` 去重）；★★★**SVG 验证码当输入框**（`java.getVerificationCode('data:image/svg+xml;base64,'+svg)` 的语义是「显示一张图让用户输入」，不关心图是不是真验证码 ⇒ 图里画操作说明、用户输命令，**零新增 UI 复用了现成弹窗**，可移植到任何需要文本输入的书源）；★★**黑名单落地机制**=`name` 规则里返回 `''`（`BookList.getSearchItem` 的 `name.isBlank() → return null` 就是 Legado 的过滤口）；★★**SVG 现场生成封面**（7 字切行 + `tspan` 逐字竖排，`data:image/svg+xml;base64,` 直接当 coverUrl，永不 404）；★★**版本更新检查**（gitee commits 当版本号源，版本号写在 `exploreUrl` 里一处维护，按钮文案随状态变「更新/导入」）；★**开关矩阵** `bfqfun2(x)` 一函数管所有开关（`!= 1` 才是默认开）；★**调试模式**让用户开开关后复现，`java.log` 可导出分析，比截图快 10 倍；K1~K14 避坑（含 `result=''` 必须写在 name 规则、`getVerificationCode` 取消返回值要判空、版本号字符串比较跨位数会判错）

### 黄果短剧专题方法论（9 篇 · 2026-10-27 批量沉淀）

- [references/方法-封面钩子返回值必须是Java-byte数组与三层缓存中毒.md](references/方法-封面钩子返回值必须是Java-byte数组与三层缓存中毒.md) — ★★★**封面解密钩子返回值必须是 Java `byte[]`，不是 JS 数组**（黄果短剧蓝本）：源码 `RhinoScriptEngine.kt:235` `unwrapReturnValue` **只 unwrap `Wrapper`** —— `Packages.java.util.Arrays.copyOf(...)`→`NativeJavaArray`（**是 Wrapper**）→Kotlin `as ByteArray` ✅ 成功；JS 数组字面量 `[b0,b1,...]`→`NativeArray`（**非 Wrapper**）→强转失败→`runCatching` **静默吞掉**→`onStreamReady(null)`→Glide `failUrl` 拉黑该 URL→「封面二次解密失败」；★**三层缓存叠加**（Glide 密文缓存 → 加 `&hgimgv=2` 换 cache key / Glide `failUrl` **进程级黑名单** → 改完**必须重启 App** / 正文缓存 → 正文图 URL 含选项串 ⇒ `MD5(src)` 变化 ⇒ **旧书须删书重加或清正文缓存**）；★★**封面取错对象的坑**：详情页要取 `body[data-history]` 里的 `"cover"`（**先 `replace(/&#34;/g,'"')` 解实体**），不能取 `img[data-src^=https://pic]`（那是底部推荐卡的封面）；★**多结构站点合并进单书源**：三种列表容器共存时，**多选 `bookList` 后字段级选择器不按索引对应**（`name` 返回空 / 书籍总数 0）→ 所有字段必须统一 `@js:` 自解析并按结构用各自锚点（video 用 `data-track-title` / rank 用 `.hg-rank-item__title` / topic 用 `.hg-topic-card__title`）；★**先量隔离矩阵再写规则**（`.hg-list-page` 之后三容器互不重叠）；★**容器后缀限定既是去重也是提纯**（分类页 84 条 → 21 条，原 84 是 4 个 tab 面板混在一起的假象）
- [references/方法-多结构站点合并进单书源与封面钩子返回类型.md](references/方法-多结构站点合并进单书源与封面钩子返回类型.md) — ★**「不要分成两个书源」需求的落地方案**（黄果 v9.0 实例）：三容器隔离矩阵模板 + 字段自解析范本 + `bookUrl` 按结构分流 + `ruleBookInfo`/`ruleToc` 双结构兼容（视频页有 `data-track-total-episode` → 按集数生成章节；专题页无此属性 → 把专题内视频作为章节）；★相关推荐条目残留**不是 bug**（点进去同样是专题页，行为一致）
- [references/方法-登录面板三协议辨析与E版兼容.md](references/方法-登录面板三协议辨析与E版兼容.md) — ★★★**登录面板三协议辨析 + E 版兼容**（黄果 v9.3 蓝本，用户报「登录界面，各功能失效」）：★**根因 = `loginUi` 字段格式非法**（既不是 V1 的 JSON 数组，也不是 V2 的 `{"version":2}` 对象 → `GSON.fromJsonArray<RowUi>` 解析失败 → **界面能开但所有行功能全失效**）；★★**三协议**：①**V1 静态**（`loginUi` 是 JSON 数组，**E 版唯一可用形态**）②**V1 动态**（`<js>FQ_fn()</js>`，`JS_PATTERN` 要求**整串匹配**，`handleReUiView` 会重执行 JS 重建界面）③**V2**（`{"version":2}`，新版专有；`loginUrl` 里须定义 `function loginUi(state)` 返回 `{"rows":[...]}` 与 `function loginAction(action,state,form)`；★**`state` 是 JSON.parse 后的对象，必须 `JSON.stringify(state)`**，用 `String(state)` 会得到 `"[object Object]"`）；★★★**V1 的 `viewName` 是 JS 动态文本机制（E 版兼容动态面板的关键）**：源码 `rowUiBuilder` 里 `viewName==null`→用 name；长度 3..19 且首尾单引号→直接作文本；**否则→`execute{evalUiJs(viewName)}` 异步执行后设为 hint/按钮文本** ⇒ **静态数组 + `viewName` 为 JS 表达式 = 固定行数 + 动态面板，且每次渲染自动重跑 JS、不依赖 `reLoginView`**（12 个固定线路位各写 `FQ_siteName(i)`）；★★**绑定实锤（修正旧认知）**：`handleButtonClick` → `source.evalJS("$loginJS\n$buttonFunctionJS"){put("java",sourceLoginJsExtensions)}` ⇒ **`java` 被覆盖成 `SourceLoginJsExtensions`，但 `source` 仍绑定**（`BaseSource.evalJS` 的 `bindings["source"]=this`）⇒ **action 里 `source.get/put` 可用**（旧版「action 无 source」的说法已过时）；★**`"$loginJS\n$jsStr"` 拼接 ⇒ `loginUrl` 的函数在 loginUi/action 环境全都可用**；★**`loginUrl` 必须有 `function login(){}`**，否则点登录抛「Function login not implements!!!」；★★**Rhino 里 Kotlin 属性是方法**：`StrResponse.code/callTime/body` 必须 `r.raw.code()` / `r.callTime()` / `r.body()`，直接 `String(r.code)` 得到方法引用字符串（长度 ~30，**看起来像成功但判据全错**）；★**并发测速用 `java.ajaxAll`**（61 候选 54ms；串行 88 秒）+ `java.ajaxTestAll` 是 `isTest=true` **不真正发请求**不可用；★**探针法验证**：临时把 `loginUi` 改 `<js>FQ_probeAll()</js>`（返回行须带 `key` 才会被 `getLoginInfoMap` 保留）实测各函数，**测完必须还原**
- [references/方法-黄果短剧发布页寻线与换源登录面板实战.md](references/方法-黄果短剧发布页寻线与换源登录面板实战.md) — ★**发布页寻线 + 换源登录面板实战**（黄果短剧蓝本）：发布页 `publish.js` 里 `var urls=[3个根域]` + `var subdomains=[19个高校前缀]` ⇒ 候选 61 个；★**测速判据**：HTTP 200-400 **且 body 长度 > 20000**；★**换源架构三层**（L3 loginUi 按钮 → L2 `source.putLoginInfo` → L1 单点读取）；★线路池要**测速排序取最快**而非池首；★「##」会被传输层吃掉 → 用 `String.fromCharCode(35,35)`
- [references/方法-登录面板E兼容动态线路板-V1数组与reLoginView.md](references/方法-登录面板E兼容动态线路板-V1数组与reLoginView.md) — ★**E 兼容动态线路板**（黄果 v9.2 蓝本）：V1 静态数组 + 12 个固定线路位 + `viewName` JS 动态文本；★`java.reLoginView()` 可能不存在 → 必须 try/catch 兜底 + toast 提示「重新打开本面板」（因为 `viewName` 的 JS 每次渲染都重跑）
- [references/方法-AES图片解密后的FFD9截断与假分页陷阱.md](references/方法-AES图片解密后的FFD9截断与假分页陷阱.md) — ★**AES 图片解密的两个陷阱**：①解密后数据**必须保留完整 JPEG 头尾**（FFD8/FFD9），截断到 FFD9 会导致图片显示异常；②**假分页**（页面返回 200 但内容重复/截断，须靠内容判据而非页码判断）
- [references/方法-站点自带crypto-image插件的AES图片解密.md](references/方法-站点自带crypto-image插件的AES图片解密.md) — ★**站点自带 `crypto-image` 插件时的 AES 图片解密**：优先复用站点自带的解密实现（密钥/IV 常在插件 JS 里），比自己逆解省事；★插件的密钥提取位置与调用签名要现场抓
- [references/方法-视频书源三件套-type-setType-coverDecodeJs.md](references/方法-视频书源三件套-type-setType-coverDecodeJs.md) — ★**视频书源三件套**：`bookSourceType=4` + `chapterList` 内 `book.setType(4)` + `coverDecodeJs` 封面解密钩子；★三者的配对关系与各自失效症状
- [references/方法-Flutter Dart AOT APK逆向与发布页寻线.md](references/方法-Flutter Dart AOT APK逆向与发布页寻线.md) — ★**Flutter Dart AOT APK 逆向**：AOT 快照里字符串常量可提取（`strings`/快照解析），可用于定位接口路径、发布页地址、密钥；★AOT 无源码/无动态求值，只能静态提取 + 交叉验证

- [references/方法-双版本兼容LT与E的源码级差异对照.md](references/方法-双版本兼容LT与E的源码级差异对照.md) — ★★★**LT 版(gedoor/legado) 与 E 版(Luoyacheng/legado-E) 源码级差异对照与双版本兼容改造**（黄果短剧 v9.4 蓝本，用户报「E 版目录加载失败」）：★★**头号杀手 = `AnalyzeRule.getElements` 的 NativeArray 处理**——LT 版末尾有 `is NativeArray ->` 显式分支（转成 `ArrayList`），**E 版末尾只有 `it as List<Any>` 强转** ⇒ Rhino `NativeArray` 不是 `java.util.List` ⇒ **E 版 ClassCastException ⇒ 目录加载失败**（症状指纹：搜索/详情/发现全正常，唯独目录失败，因为只有目录走 `getElements`）；✅**修法 = `chapterList` 返回 `new Packages.java.util.ArrayList()` + `list.add()`**（★**Java List 的方法是 `add` 不是 `push`**；★**为什么两版都通**：Rhino 把 Java 对象包成 `NativeJavaObject`（是 `Wrapper`）→ `RhinoCompiledScript.eval` → `unwrapReturnValue` → 还原 `java.util.ArrayList`）；★★**次号杀手 = `getString` 对 NativeObject 的处理**——LT 版有 `Mode.Js`/`Mode.Json` 分支，**E 版只有「键值直取」** ⇒ JS 对象的 `@js:`/`$.x` 全取不到；✅**双版本通吃 = 列表用 CSS 选择器（`getAnalyzeByJSoup().getElements()` 返回 `List<Any>`）+ 字段用 `@js:`**（Element/String/List 都走 `else` 分支 → `Mode.Js`）；★★**E 版 API 存在性清单**（逐个源码核对）：**有** = `coverDecodeJs`（★**在 `BookSource` 里不在 `BaseSource`**，只搜 BaseSource 会误判缺失）/`java.ajaxAll`/`StrResponse.code()|callTime()|body()`/`reLoginView`/`{{}}` 模板/`source.get`/`book.setType(4)`（Kotlin `var` 生成 setter）/视频播放（`BookType.video=4`）/V1 静态 loginUi + `viewName` 三分支；**没有** = `getElements` 的 NativeArray 分支 / `getString` 的 NativeObject Mode.Js / `getLoginUiJs()`+V2 / `RowUi.key|hint|value|options`（⇒ **输入框一律用 `name` 作存取键**）；★**E 版源码用 GitHub API 下载**（`api.github.com` 可达，`github.com` 443 被墙）：`GET /repos/Luoyacheng/legado-E/contents/<path>?ref=main` → base64 解码；★**`Packages` 在 `eval_js` MCP 工具不可用但在规则 JS 可用** ⇒ 别在沙盒下结论，用 `debug_source` 实测；★排查流程：分清哪一步失败（目录失败⇒chapterList 返回类型）→ API 下载 E 源码 → diff `AnalyzeRule.getElements/getString` + `webBook/BookList|BookChapterList|BookContent` → 逐个 API 存在性核对（★**字段可能在子类**）→ 静态审查表 → **LT 版 debug_source 回归**

### 参考资料

- [references/book-source-templates.md](references/book-source-templates.md)
- [references/html-structure-examples.md](references/html-structure-examples.md)
- [references/output-template.md](references/output-template.md)
- [references/书源规则：从入门到入土.md](references/书源规则：从入门到入土.md)
- [references/订阅源规则：从入门到再入门.md](references/订阅源规则：从入门到再入门.md)
- [references/订阅源规则帮助.md](references/订阅源规则帮助.md)
- [references/快速写源订阅源原理分析.md](references/快速写源订阅源原理分析.md)
- [references/阅读lyc版js变量和函数.md](references/阅读lyc版js变量和函数.md)

### 案例

- [examples/README.md](examples/README.md)
- [examples/天空书屋_m.tkshuw.com.json](examples/天空书屋_m.tkshuw.com.json) — 天空书屋手机站成品源（check/debug 全绿）；技术要点见 [方法-假表单搜索接口与列表内联文本提取](references/方法-假表单搜索接口与列表内联文本提取.md)
- [examples/天空书屋_m.tkshuw.com.md](examples/天空书屋_m.tkshuw.com.md) — 同上案例详解页：假表单双向验证法 / `s_list` 内联裸文本 `lastIndexOf('/')` 定式 / `@js:` 的 `result` 是 Element 静默失败 / `nextContentUrl` 必须 `return null`；含站点自身截断（`_2.html` 与主页 md5 相同）与死章节的甄别
- [examples/玄幻文学_m.xhwx8.com.json](examples/玄幻文学_m.xhwx8.com.json) — 玄幻文学手机站成品源（check 1/1 + 五链路全绿）；技术要点见 [方法-服务端忽略页码参数与||分支空格陷阱](references/方法-服务端忽略页码参数与||分支空格陷阱.md)
- [examples/玄幻文学_m.xhwx8.com.md](examples/玄幻文学_m.xhwx8.com.md) — 同上案例详解页：POST 搜索（GET 假成功 0 条）/ `og:` 全字段 + 简介前缀剥离 / `ul.chapter:nth-of-type(2)` 取第 2 组 / 数字后缀章内分页 + 「本章未完」终止判据（超末页仍返 200 同内容）/ 九步正文清洗（含 HTML 残缺 `<iclass=`、末尾「！」顺序陷阱）/ 发现页三模板合一 + **站点假分页**（`?page=N` 全返第 1 页）与替代入口
- [examples/2tsw-爱看书吧.json](examples/2tsw-爱看书吧.json) — 爱看书吧手机站成品源（check 1/1 + 搜索/详情/目录/正文/发现全链路 App 内实测）；技术要点见 [方法-目录分页窗口陷阱与页码推算](references/方法-目录分页窗口陷阱与页码推算.md) 与 [方法-正文跨页断字修复与逐行广告过滤](references/方法-正文跨页断字修复与逐行广告过滤.md)
- [examples/2tsw-爱看书吧-验证记录.md](examples/2tsw-爱看书吧-验证记录.md) — 同上案例详解页：GBK 搜索（`charset` 选项）/ 单结果 302 跳详情靠 `bookUrlPattern` 兜底 / **目录分页条是滑动窗口**（第 11 页起窗口内不含第 1 页，只翻 11 页）⇒ 用「当前第X页，共Y页」+ `baseUrl` bookId 定位，**`nextTocUrl` 只返回下一页 1 个 URL、末页 `return null`**（124 页串行 26 秒，5569 章零重复严格递增）/ **正文跨页断字 + 断 `&nbsp;` 实体**（页尾 `&n` + 下页 `bsp;`）需 `@js` 自行按页抓取无缝拼接 / 六类广告行三层判定 + **反向验证防误伤正文**（「无广告的阅读体验确实舒服很多」必须保留）/ 含遗留风险 4 条
- [examples/桔纸书屋_m.juzhishuwu.net.json](examples/桔纸书屋_m.juzhishuwu.net.json) — 桔纸书屋手机站成品源（check 1/1 + 搜索/详情/目录/正文/发现五链路全绿）；技术要点见 [方法-正文跨页重复输出与整页去重](references/方法-正文跨页重复输出与整页去重.md) 与 [方法-搜索限频伪装的间歇性错误页](references/方法-搜索限频伪装的间歇性错误页.md)
- [examples/桔纸书屋_m.juzhishuwu.net.md](examples/桔纸书屋_m.juzhishuwu.net.md) — 同上案例详解页：GBK + `charset` 选项 / 单结果 302 跳详情靠 `bookUrlPattern` 兜底 / 结果 `.com` 域 `##` 替换归一省 7 秒 / `#first + div.section-box` 取第 2 组目录（`:nth-of-type` 会各自算第 1 个）/ **分页条只显示当前页 ±10 页 ⇒ `nextTocUrl` 必须从「当前第X页，共Y页」推算，但只返回「下一页」1 个 URL、末页 `return null`**（★源码级铁律：返回 ≥2 个 URL 走并发分支必乱序；★从 `baseUrl` 提 bookId，`replace(/\/\d+\/?$/,'')` 会把 bookId 一起删掉）/ 正文三坑（跨页断句 + 跨页断实体 + 整章重复 5 份）与无缝粘合 / 发现页三模板合一（分类 5 span + 榜单 3 span，`s1` 是名次数字需过滤）/ 13 项验收记录
- [examples/光遇聚合_www.gyks.cf.md](examples/光遇聚合_www.gyks.cf.md) — 客户端协议代理+云端 HTML→JSON 转译的三段式聚合源
- [examples/轻小说文库_wenku8.md](examples/轻小说文库_wenku8.md) — **jieqiCMS 文库站（wenku8）完整案例**（check_source 1/1，全链路 MCP debug 通过）：登录态分层（详情/目录/正文匿名✅，搜索/榜单/分类/标签需登录，匿名返回"用户登录"整页）；**GBK 全链路**（searchUrl 用 `java.encodeURI(key,"GBK")` + URL 选项 `{"charset":"GBK"}` 同时管请求参数编码与响应解码）；**登录统一 `java.connect(url+,{...,"method":"POST","charset":"GBK","body":"..."})`**（走 OkHttp+CookieJar；`java.post` 走 jsoup 不带 CookieJar 登录取不到会话）；373px 卡片五模板统一正则解析；正文净化（`<ul id="contentdp">` 水印必须 join 移除不能 split[0]，录入组短行过滤，`&#12539;`→`·`）；插图章 divimage img 双引号逐行；版权下架书容错；exploreUrl 必须静态 JSON（`<js>` 动态在 check_source 裸环境报"发现规则为空"）
- [examples/轻小说文库_www.wenku8.net.json](examples/轻小说文库_www.wenku8.net.json) — 同上成品源（23 字段 / 分组"轻小说" / 已启用）
- [examples/米游社每日签到_定时任务_v9g.json](examples/米游社每日签到_定时任务_v9g.json) — 米游社每日签到定时任务成品（AutoTask 格式：`id`/`cron`/`script`/`loginUrl`/`loginUi`/`loginCheckJs`）；技术要点见 [方法-米游社签到定时任务拆解](references/方法-米游社签到定时任务拆解.md)
- [references/方法-光遇聚合书源架构拆解.md](references/方法-光遇聚合书源架构拆解.md) — 光遇聚合型书源架构详解(data:协议+云端代理+多源聚合)
- [references/方法-APP接口聚合书源拆解.md](references/方法-APP接口聚合书源拆解.md) — s.wendulou.com(小小阅读/书香之家)多App聚合API书源：双层AES信封解密+换源聚合+动态分类发现页+子域推导+鉴权破坏性实验
- [examples/小小阅读书香之家app_s.wendulou.com.md](examples/小小阅读书香之家app_s.wendulou.com.md) — 同上案例页(含成品JSON)
- [references/方法-图床AES加密图片解密.md](references/方法-图床AES加密图片解密.md) — 图床全站AES加密图片解密通用方案：魔数探测定位法+LegadoTeam双钩子(imageDecode/coverDecodeJs)+密钥混淆提取套路+缓存中毒三层机制+?v=版本参数自愈

## 执行原则总结

核心原则如下：

- 先分类，再分析
- 先收集信息，再写规则
- 先保证可用，再考虑增强
- 有风险就明确标注
- 不确定就降级，不臆造

本技能的重点不是“尽量多写内容”，而是“尽量稳定地产出可验证结果”。

- [references/方法-AEGIS-ALTCHA验证与WebView通道书源.md](references/方法-AEGIS-ALTCHA验证与WebView通道书源.md) — ★**AEGIS(ALTCHA PoW)过盾双通道：被动拦截式+主动预取式(delayed-webview)**(69shuba.tw 双源蓝本,check 1/1)：协议逆向(keyPrefix判活铁律=32hex deny-by-design)；**通道A被动拦截**=`java.webView(null,url,null)`走真Chromium栈→loginCheckJs拦验证页重取→`new StrResponse(url,src)`替换响应；**通道B主动预取**=searchUrl带`{"webView":true,"webJs":"document.documentElement.outerHTML","webViewDelayTime":5000}`或规则内`java.webView('',url,js)`/`java.webViewGetSource('',url,js,'',false,4200)`直走内核+**delay等页面内自动PoW完成再取DOM**(搜索5s/发现4.2s/正文0=哨兵反馈闭环调参,无js无delay系统兜底900ms)；★全签名核准(3/4/6参+POST走loadDataWithBaseURL+UI线程禁调+blockNetworkImage++cacheFirst慎用)+逐环节对照表+四件套整合模板(主动打底+loginCheckJs兜底+正文自愈+面板过盾按钮)+K1~K13+双版本两铁律

- [references/方法-字节系官方App接口签名门槛与降级.md](references/方法-字节系官方App接口签名门槛与降级.md) — ★★**字节系官方App接口签名门槛与降级策略（红果短剧 hongguoduanju.com 实战）**：★★★**"能否突破"决策树**（返回404→找其它入口 / 返回默认数据=服务端静默降级→**必须加参数-响应一致性校验** / 有官方App/桌面版→查接口签名方式 / 纯JS哈希→可复现 / **native so库/unidbg/frida→书源侧架构不匹配，不可行** / 全不可行→降级交付）；★★**字节系签名实测全貌**：域名`api5-normal-sinfonlineb.fqnovel.com`、红果**aid=8662**（非番茄1967）、`app_name=novelread`、路径**必须带尾斜杠**`/novel/player/multi_video_detail/v1/`、`x-ss-stub`=MD5(body).upper()**仅body校验不等于签名**、**`{"Code":110001}`是签名失败码不是参数错误**（见它别再调参）；**免签接口子集**=`/reading/bookapi/bookmall/cell/change/v`（列表/榜单类常免签，详情/播放类必签）；★★**桌面版全集之谜**=内置`unidbg-sign.jar`(`com.hongguo.sign.FqTrace serve 0`)用unidbg模拟Android so库生成X-Argus，需JRE+so库常驻，书源无法复制；★★**线索链方法论**：发布仓库的**PR/Issue是架构级信息金矿**（社区PR的`desktop_bootstrap.patch`一眼看出unidbg启动方式）+ Issue错误串（"signer回环监听"/"未能取得剧集列表HTTP 500"）+ **同族项目调研**（找专门做接口研究的项目如`N3urda/hongguoTV`的`docs/research/*.md`，直接给完整路径表）；★★**服务端静默降级识别与修复**（红果漫画忽略`vid`恒返回第1话、`next_vid`循环指向自己 → 加`HG_REQVID`/`HG_MANGA_ITEM`一致性校验，不一致明确报错而非静默重复）；★降级交付三原则（如实标注/明确提示/不伪造）+ **`#fragment`伪URL技巧**（不发请求、天然唯一、可带参）+ 三段式提示文案（问题+原因+出路+识别方法）+ K1~K12
- [references/方法-字节系App全签名复现与DH解密通道.md](references/方法-字节系App全签名复现与DH解密通道.md) — ★★**字节系App全签名纯JS复现与DH解密正文通道（番茄小说实战，LT/E双版本兼容）**：★★★**三大签名纯JS复现**（x-argus=SIMON-128+手写protobuf / x-ladon=MD5展开34轮流密码 / ttEnc=SHA512派生AES）+ **CM通道3072位MODP DH握手**（pk=random(256)%(P-1)，pub=2^pk mod P，aesKey=sharedBytes[:32]）；★★**五大坑**：jsLib作用域java.*全不可用（必须Packages.*或参数注入）/ `Packages.android.util.Base64.decode`返回全零（用java.util.Base64）/ byte[]→字符串必须`new Packages.java.lang.String(b, Charset.forName('ISO-8859-1'))`（`b[i]&255`会失真）/ `@js:`顶层禁return（IIFE包裹）/ bookUrl分隔符必须单`#`（`##`会404）；★★**legado-E兼容**：BouncyCastle类不可用（R8裁剪）→ **纯JS SM3实现**（含3个国密标准向量）+ **纯JS Base64双通道兜底** + 依赖审计清单（高风险/安全分类）；★★**发现页分类体系**：榜单/分类榜=`bookmall/cell/change/v1`带`req_rank_category_id`+`req_rank_algo`（16分类+4榜单）/ 频道tab真实ID（**不是顺序索引**）/ 首页SSR / **URL参数分发设计**（`标题::url?t=rank&cat=37&algo=101`）+ **分组标题用空URL**；★设备注册gzip字节需手工改XFL/OS对齐zlib、CM解密pubBytes/sharedBytes必须去前导零、dpaste限频时改用uguu.se

- [references/方法-SSR内联JSON书源的括号配平提取.md](references/方法-SSR内联JSON书源的括号配平提取.md) — ★**SSR内联JSON书源总纲（Modern.js/Next.js/Nuxt类站点，红果短剧 hongguoduanju.com 蓝本，check 1/1）**：★★★**括号配平状态机**是唯一可靠取数法（贪婪正则吃尾/非贪婪在内层`}`截断/lastIndexOf吃到后续JSON；必须处理字符串状态+转义+单引号三态）；★**loaderData键名随路由变化**（`detail_page`/`player_(series_id)/(vid)/page`/`search_(keyword)/page`/`category_$`/`rank_hot-drama/page`）→ 必须**按特征字段名遍历**而非写死key；★★**三大传输陷阱**（零双引号零反斜杠纪律`String.fromCharCode(34/92)`；HTML实体字面量被解码；**jsoup的`script.html()`返回空/`data()`含前缀+尾部JS不能直parse → 必须在原始HTML上indexOf+配平**）；★★**`key`/`page`在bookList上下文不存在**（源码实锤AnalyzeRule.kt:896-914 bindings全表无key，BookList.kt从不setLocal）→ **searchUrl携带自造参数`?hgk={{java.encodeURI(key)}}`+规则内从baseUrl反解**（`decodeURIComponent`用JS原生，`java.decodeURI`不存在）；★★**`@js:`顶层禁止return**（Rhino `compileString`报"返回的值无效"）→ 一律IIFE且内部显式return；★**列表返回JSON字符串数组**（E/LT双版本最大公约数）+字段规则`$.key`；★**`tocUrl=bookUrl`零请求目录**（BookInfo.kt:157-161 + WebBook.kt:312 源码级复用tocHtml）；★**多形态站点在chapterList里`book.setType()`**（WebBook.kt:306 `removeAllBookType()`会冲掉详情页设的type）；★★**网页版硬限制如实标注**（红果每部剧仅前3集可播，第4集起404；9种绕过方案全失败=服务端策略）；★**播放直链mp4免防盗链但带15分钟时效签名**→每次实时解析不缓存；K1~K16避坑+App内eval_js四步验证法+**md5比较必须String()包裹**（Rhino里`java.md5Encode`返回Java String，`===`恒false）

- [references/方法-同模板迁站与文本转换边界-twkan.md](references/方法-同模板迁站与文本转换边界-twkan.md)
 — twkan案例：迁站不保证ID互通、Java空字符串回退、仅转显示文字、目录分页与下一章分离、风控哨兵、交付停止条件。
- [references/方法-对照实验驱动的接口逆向与正文排版.md](references/方法-对照实验驱动的接口逆向与正文排版.md) — ★**对照实验驱动的接口逆向 · 会话铸语义 · 正文排版三道关口**（sangtacviet.vip 蓝本，v9.21 实测）：核心信条=**不要推理要对照**——在参数上盲试一百次，不如把官方 App 对**同一接口**的响应原文调出来逐字节比对（本次绕几十轮，答案在第一条官方抓包里）。★★**响应字段必须全量打印**：顶层是 code/data/**oridata**/unvip/unlocked/val，我只读 data（越南语）而漏了 oridata（中文），于是试遍四种 Cookie + 官方一致请求头 + 12 个参数得出「站点限制」的**完全错误**结论。★★**会话铸语义**：决定正文语种的是**铸 key 那次请求**的 Cookie（`transmode=chinese`），不是读正文时带的；抄成 `transmode=name` 之后，degloss/squeeze/分段/排版全在给这一个错误擦屁股（票据类接口通用检查表见 §3）。★★★**正文「一整段」的三道关口**：规则输出 → 净化链路 → 渲染层。净化按上游源码是把 `<p>` 转成换行、不会拍平，但**改版会加步骤**（本 App 把正文标点转半角 = 证据）；绕过净化用 `<usehtml>`，而 **TextView 不给 `<p>` 垂直间距、只有 `<br/>` 换行**，且整块必须单行（阅读端按换行切 contents 会切碎）、不要 `<p>`+`<br/>` 双叠加。jsoup **`text()` 吃换行、`wholeText()` 才保留**。★**分段策略别写死**：三种来源分别是空行型/标签型(121 个 p、119 个相邻无换行)/制表符型，终版同时跑五种切法打分选最优。★**测试与交付纪律**：harness 必须用**真实函数**装配（复制桩=测副本）、不同分支各有用例（否则假绿）、反向对照断言、闸门要做负例验证；删函数后 `grep -c` 必须为 0（残留调用语法合法、运行时才炸）；**上传与唤起必须串行且只用当次返回值 URL**（404 会被当书源解析→弹窗乱码）；确认导入查日志+回读特征，不要问用户。含 STV 完整接口档案（Referer 分接口、`c` 必须是章节 ID、`truyen/{host}/1/{bookid}/` 顺序）
- [references/方法-封面Glide链路与IP-Host头直连.md](references/方法-封面Glide链路与IP-Host头直连.md) — ★**封面修复通用范式（Glide 丢弃 dnsIp 的根因与解法）**：封面走 Glide `OkHttpStreamFetcher`→`AnalyzeUrl.getGlideUrl()`，**只保留 url+headerMap、丢弃 dnsIp**；正文走 `getByteArrayAwait()` dnsIp 完整生效 ⇒「正文能显示但封面全灰」的通用根因；解法=**http://<CF-IP><path> + {"headers":{"Host":"域名"}}**（Host 头在 OkHttp BridgeInterceptor 只在缺失时补⇒保留），既绕系统 DNS 的 IPv6 不可达又让 CDN 认出虚拟主机；★**真机判据**：沙盒直连≠真机 Glide，用 LAN `/cover` 端点或 eval_js+java.ajax；`/cover` 返回 **PNG**（不能用 JPEG 魔数），正确做法=先取必然失败 URL 作「占位图基准」比 md5；★**tobeimg 陷阱**：base64 里是真实图片 URL，须解码取 `/static/` 路径（避开 302 跳 img.picacomic.com）；payload 非 4 倍数要补 `=`；`tobs/` 前缀必须去掉；★**分形态路由**：以 base64 解码出的真实托管域为准（非 fileServer）；★**覆盖边界要诚实**：有些封面是上游数据本身失效（服务端 404/502），书源层无解，不能无限换通道试错；★**新坑**：JS 规则漏 `<js>` 包裹 ⇒ Legado 当 CSS 解析 ⇒ check_source 报「后未平衡」而 debug_source 看不出来；★**交付纪律**：沙盒≠真机 ⇒ 先建独立 bookSourceUrl 测试源跑通→check_source 通过→LAN 覆盖正式源→回读比对→删测试源；测试源登录态**不与正式源共享**（token 按 bookSourceUrl 存）；★**漫画浏览模式同坑（v85 实锤）**：Legado 有两条图片链路——普通浏览 `BookHelp.fetchImage`→`getByteArrayAwait()`（**dnsIp 生效**），漫画浏览 `MangaVH`→`BookCover.loadManga`→Glide→`OkHttpStreamFetcher`(manga=true)→`getGlideUrl()`（**dnsIp 丢弃**）⇒ 站点「普通能看图、漫画看不了图」的症状就是这么来的（真机对照：新格式 IP+Host ✅ / 旧格式域名+dnsIp ❌ / 裸域名 ❌ / 无Host ❌）；★**通用结论：只要图片可能走 Glide（封面/漫画浏览/预览），URL 就必须自带 IP+Host 头，不能依赖 dnsIp 选项**——同一个 URL 在两条链路上都能加载；★**禁止在 `<img src>` 外层再套 dnsIp**（双层选项⇒UrlOption 解析失败⇒回退裸 URL⇒又超时，v63 老坑同源再现）；★正文图 URL 含选项串 ⇒ 缓存文件名 `MD5(src)` 变化 ⇒ **旧书须删书重加或清正文缓存**
- [references/方法-App官方API书源与设备号风控-次元姬.md](references/方法-App官方API书源与设备号风控-次元姬.md) — ★**正版App的JSON后端做书源总纲（次元姬 api.hwnovel.com 蓝本,check 1/1×N,五轮发现页排布迭代定稿）**：★★**设备号风控**（服务端设备库：已知号200/任意新16hex→`400网络繁忙`/有序号403/缺头500；同IP好号新号对照排除限频；无离线激活接口→共享已验证设备号+登录面板「设备号」可自定义source.put('cydn')+header@js动态生成+loginCheckJs拦截）；**四件套加密门禁**（DES-ECB PKCS5 key=ZUreQN0E加密参数+requestId=UUID无杠+sign=MD5(base64拼串).大写+★timestamp必须JSON数字(字符串→500)；GET/POST同构+必带4客户端头）+★**签名无时间窗无重放→bookUrl直接嵌永久签名URL书架长生**；**crates.io拆包逆向降级路径**（GitHub被墙时GET crates.io download源码包+版本考古0.20.x已移除模块/0.19.2最高版）；★**VIP未购code=101不是错误**（~200字预览密文可解密+payAction复用chapter.url里param密文拿bookId/chapterId下单）；★★★**发现页排布终极铁律（源码实锤item_find_book.xml showDivider+margin/ExploreAdapter）**：固定layout_flexBasisPercent列数全面失效(0.5+0.5→竖排一列/0.33×3→两列)——唯一稳解=条目style={'layout_flexGrow':1}自动流式+分区标题行basis1整行url空；emoji撑大最小宽→条目纯文字；check_source首检=书架GET/签到POST第二；发现页签到提示放loginCheckJs(url/body Kotlin属性双通道+return r原样)；统一解析器pl()吃四容器+kind前3标签+wc()字数格式化；ruleBookInfo.tocUrl唯一合法位+目录bookId只在顶层bookChapter；K1~K12交付Q/A(手抄save必坏→回读md5/Python“\\n”双反斜杠坑/replace去前缀注意引号边界/node --check每轮必跑)
- [references/方法-图片CDN间歇阻断与Legado重试语义.md](references/方法-图片CDN间歇阻断与Legado重试语义.md) — ★**图片 CDN 间歇阻断根因定位**（哔咔 v76 蓝本）：★**Legado 的 `retry` 只重试非 2xx，不重试 IOException**（源码 OkHttpUtils.newCallResponse：await() 抛异常直接跳出重试循环）→ 写 retry 抗不了连接超时；★**`dnsIp` 逗号分隔多 IP = OkHttp 按序尝试自动跳过不通的**（AnalyzeUrlNetworkOptions.buildScopedDns），且**只约束首个 host**、与 proxy 互斥、池内不能混域名；★**按图序号轮换首选 IP 顺序**（`idx % pool.length`）可把"整章同节点批量失败"降级为"个别失败"；★**0ms IOException = Glide failUrl 黑名单秒拒**（OkHttpStreamFetcher），不是网络问题；★**隐藏 bug：nextContentUrl 取 book.tocUrl（目录页 URL）永远匹配不到 order/(\d+) → 章节内分页只出第 1 页**，正解是从章节自身 baseUrl 取 order（debug 日志 `◇本章总页数` 即信号）；★URL 选项 `"type":"jpg"` → 响应体是完整 hex（验证图片可达性的最干净手段），但 `java.base64Encode(byte[])` 在 Rhino 下不可靠、不能拼 data URI；★旧章节缓存不重跑正文规则 → 改源后须删书重加；净化规则能改写缓存正文但会二次包装带选项 URL 自伤
- [references/方法-签名过期与现签URL-@js机制.md](references/方法-签名过期与现签URL-@js机制.md) — ★**签名过期型 API 的现签机制**（哔咔 v83 蓝本）：★`@js:` 表达式里 `result` = URL **前缀**（含 path），且**每次请求都重新求值** ⇒ 天然解决签名过期；★**规则文本里禁止出现字面 `@js:`**（AnalyzeRule.splitSourceRule 的 JS_PATTERN 会误判并立即求值）→ 用 `String.fromCharCode(64,106,115,58)` 拼；★签名 IIFE 必须是**字符串字面量**（立即执行会在目录规则阶段就跑错）；★`@js:` 环境 `java`=AnalyzeUrl（无 getLoginHeader/ajax）且**无外部变量** → 全部内联 + token 用 `source.get()`；★多层转义会丢反斜杠 → `String.fromCharCode(92)`；★**`nextContentUrl` 终止值必须是 `"javascript:void(0)"` 不能是空串**（空串会被 getAbsoluteURL 解析成当前页 URL → 重复请求已消费签名 → 400）；★从 URL 取 id 用**精确正则+格式校验**（贪婪 replace 会把域名截成 `https:`）；★`kind.url` 的 `@js:` 不能调用 jsLib（java.ajax 不存在）→ 必须完全内联；★服务端「200 但 data 为空」= **path 算错**的伪装形态
- [references/方法-LAN-Web服务保存书源与全端点手册.md](references/方法-LAN-Web服务保存书源与全端点手册.md) — ★**LAN Web 服务全端点手册（书源交付/联调最强通道，wenku8 LAN 直存蓝本）**：★★**认证头=`x-legado-token`**（不是 token:/Authorization/查询参数；源码 BookSourceController.kt:23；头名大小写不敏感；报"Web 书源访问令牌未配置或不正确"先查头名）+ **POST 必须 Content-Type: application/json**（form-urlencoded 时 postData 读不到→"数据不能为空"）+ **saveBookSources 吃数组/saveBookSource 吃对象**+ **响应恒 HTTP 200 成败只看 body.isSuccess**；★**不止保存书源**——全端点三类：写（saveBookSource(s)/deleteBookSources/saveRssSource(s)/saveReplaceRule/deleteReplaceRule/**testReplaceRule 离线测净化**(键 text+isRegex 显式 true)/saveBook/deleteBook/saveBookProgress/addLocalBook/saveReadConfig/saveJsSource(text/plain+≤1MiB)/startBookSourceCheck+stop(必须先 save 否则 checkContent 快照不一致报"书源尚未保存")）读（getBookSource/getBookSources 回读**无 MCP 200000 截断**做 md5 字节级闭环/getBookSourcesForManagement/getBookSourceCheckStates/getJsSourceApiTokenRequired 排障第一步/getHttpLogs+getHttpLog **取证不占 MCP 会话**/getBookshelf/getChapterList/refreshToc/getBookContent/cover/image/getRssSource(s)/getReplaceRules/getReadConfig）WebSocket（bookSourceDebug/rssSourceDebug/searchBook，sec-websocket-protocol 双协议认证）；★**标准交付闭环**=saveBookSources 直存(>19KB 无压力、json.dumps 组包零失真、无 dpaste 限频/深链确认弹窗)→getBookSource 回读 md5 闭环(排除 respondTime/lastUpdateTime)→差异以 LAN 回读为准反推传输层；★通道决策树：有 LAN 优先 LAN(交付+验证)，无 LAN 才 dpaste/uguu+深链；用户环境 BASE=http://192.168.10.4:1122 令牌=a7894563
- [references/方法-Discuz论坛型TXT下载站书源制作.md](references/方法-Discuz论坛型TXT下载站书源制作.md) — ★**Discuz!/PHPWind 论坛型资源下载站总纲**（bookSourceType=3，蓝本墨香书阁 noveltxt.vip，check 1/1）：站点识别6特征（`_2132_` cookie前缀/`mobile=2`/**`thread-{tid}-1-1.html`**/`forum.php?mod=attachment&aid=`）；★★**三大命门**：①UA 决定模板（桌面 UA 会 302 到 `mobile=no` → header 必须钉死手机 UA）②**用户组权限要查表**（`home.php?mod=spacecp&ac=usergroup`，本站游客能搜、登录组被禁用搜索）③附件扣费=**服务端 302 到 attachcredit**（非 purchase 表单，直接给原始链接即可）；★★**双态架构**：清 cookie **+ 访问 index 重建 session 两步缺一不可**（只清→提示页，只重建→仍登录态），此后 Legado **含翻页的常规请求**才走对通道；★登录两坑（手机版接口触发验证码→改 PC 版；`loginhash` 服务端不校验可传任意值）；★`downloadUrls` 必须 `join('\n')`（JS 数组不是 Java List 会被判空）；★`searchUrl` 必须返回**纯 URL**（带 `,{json}` 会被当成 URL 一部分）；★列表解析用 `split('<li class="list">')` 而非非贪婪正则（嵌套 `<li>` 会提前截断丢简介/分类）；**K1~K15 避坑 + jsLib 骨架 + 4 类站点对照档案**
- [examples/哔咔漫画_案例说明.md](examples/哔咔漫画_案例说明.md) — **哔咔漫画自包含书源 v76 成品案例**：官方 App JSON API + HMAC-SHA256 全请求签名 + 服务端强制登录；两个真问题修复=图片部分失败（retry 无效/dnsIp 按图轮换/并发降峰）+ 章节内分页只出第1页（nextContentUrl 取 baseUrl）；附 jsLib 作用域铁律与 v76 实测档案
- [references/方法-单集视频目录污染与相关推荐池识别.md](references/方法-单集视频目录污染与相关推荐池识别.md) — ★**「每本书点进去都一样」= 目录挂了推荐池**：单集视频无集数标记⇒chapterList兜底扫到详情页底部related-grid猜你喜欢7卡(同分类推荐池7/7相同)；识别三征兆(章节名与书名无关/换书目录集合不变/章节URL指向其他ID)；修法=语义判据分支(无hg-list-page锚点⇒单集,目录=[第1集→详情页本身])；探针法bookUrl一次实锤result形态/逐卡独立/相对URL拼接；ArrayList判空用list.size()===0
- [references/方法-DNS污染间歇性线路与Web服务字节级直传.md](references/方法-DNS污染间歇性线路与Web服务字节级直传.md) — ★**间歇性DNS污染识别**(测速时活用着死,假IP 108.160.170.41/假IPv6 2001::段,逐查询随机投毒)；线路自愈FIX五步(读hg_line→坏根域强制迁移置TTL前→favicon探活timeout8000→平铺候选切换→baseUrl host重写救活已藏书)；★★**{{}}模板的}}截断陷阱**(嵌套循环收尾产生4连}}⇒模板被截断成语法错,check_source才抓得到；解法=平铺候选数组+相邻花括号插空格)；★★**双App Web服务通道**(E版1125免令牌:saveBookSource字节级直传/refreshToc强制重解析/getBookContent必须带index/searchBook是fallback未实现;LT版1122用x-legado-token)；★★**字节级直传是唯一可靠保存通道**(MCP手打27KB JSON三轮两坏)；E版目录缓存陷阱(getChapterList 0.0s返回旧数据,必须refreshToc再验证)
