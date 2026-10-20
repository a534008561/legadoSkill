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
- [定时任务Task/方法-米游社签到定时任务拆解.md](../../../../定时任务Task/方法-米游社签到定时任务拆解.md) — 定时任务三作用域架构+loginUi按钮action调试+java.show缺失兜底
- [references/方法-发布页线路轮换与登录界面测速选线.md](references/方法-发布页线路轮换与登录界面测速选线.md) — 域名轮换站通用方案：发布页抓取/线路解析过滤/timeout测速选优/TTL缓存/入口注入五层流水线+登录UI测速按钮组+参数注入法绕jsLib作用域+bookUrl相对化自愈
- [references/方法-简介useweb内嵌页面与浏览器调起.md](references/方法-简介useweb内嵌页面与浏览器调起.md) — useweb真WebView机制+WebJsExtensions注入API清单(注解差异)+startBrowser/openUrl/iframe三通道浏览器调起+跨版本(LegadoTeam/legado-E)兼容铁律
- [references/方法-番茄漫画书源与混合类型自动判型.md](references/方法-番茄漫画书源与混合类型自动判型.md) — fqapp逆向漫画链路(CM通道materials/skeleton)+"图片加密"假象破解(type:hex验魔数先于写解密)+混合类型自动判型(comic_book_type)+Rhino中文必须UTF-8字面量+大源交付与同站点多源共存(##后缀)
- [references/方法-登录UI-V2新版面板.md](references/方法-登录UI-V2新版面板.md) — **登录UI V2新版面板(loginUi={"version":2})**：下拉select/开关toggle/倒计时按钮/状态消息板/错误红字定位——V1经典面板做不到的交互；loginUi(state)+loginAction(action,state,form)骨架+RowUi V2硬约束(key/action必填校验)+Kotlin默认参数JS须传全+state内存往返+10条踩坑+node语义仿真法(hanime1首个生产案例)；**§7 控制台实战增补(hanime1 v3.4~v3.9)**：分支哨兵词冲突/多值不能当select value(分组)/延迟后缀与解析解耦/toggle能力开关三件套(写变量+立即生效+关=可回退旧实现)/账号密码三源兜底且用户清空优先/危险动作countdown+robots.txt轻量探测/消息板分隔符换行
- [references/方法-legadoE登录面板V1动态与发现页点选化.md](references/方法-legadoE登录面板V1动态与发现页点选化.md) — ★**legado-E 适配 + select→点选化总纲(禁漫天堂v15e蓝本)**：E版SourceLoginDialog能力表(@js:/<js>动态loginUi/toggle点按循环/select/Spinner/label不渲染/✓menu_ok先putLoginInfo再login/onDismiss自动存/文本行action=600ms TextWatcher/reLoginView重建)；E版发现页ExploreKind能力表(toggle读infoMap[title]+aCache持久缓存)；★**action作用域铁律：登录面板action能看到loginUrl函数(拼接eval)，发现页action只能看到jsLib(shareScope)**；改造四板斧(V2→@js:jmeRows()/toggle chars+result读选中值/状态按钮补reLoginView/发现页action下沉jsLib参数注入)；E隐形炸弹同步修复(loginCheckJs body属性方法双通道/top-level禁const-let/列表JSON字符串协议/bookSourceUrl##片段隔离缓存)；node vm沙盒仿真法；K1~K10
- [references/方法-HttpTTS朗读引擎与音色切换面板.md](references/方法-HttpTTS朗读引擎与音色切换面板.md) — **在线朗读引擎(HttpTTS)通用方法论**：实体全字段+请求链路源码拆解+给朗读引擎加按钮的唯一官方通道(编辑→⋮→登录→SourceLoginDialog)+RowUi六种type与动态viewName+★JSON body必须JSON.stringify(否则正文引号毁URL选项→静默无声)+音色变量持久化(source.put/get)+语速映射源码级推导(显示值=speakSpeed/10)+loginCheckJs把没声音变报错+零双引号工程法+13条踩坑
- [references/方法-视频书源播放本地解密完全指南.md](references/方法-视频书源播放本地解密完全指南.md) — ★★★**视频书源"能播放"完整条件链（CENC 解密 + 本地 file:// 播放）**（番茄短剧·漫剧 fqnovel.com 蓝本，4 次报障 / 7 个版本迭代才通，check 1/1 + Team/E 双版实测可播）：核心认知=**视频书源做不出来，九成不是找不到接口，而是"最后一公里"没打通**——接口/签名/解密都跑通、debug 也显示 file:///xxx.mp4，但播放器就是加载一下就停；★★★**10 条播放条件链**（缺任何一条都播不了）：①**file:// 路径必须动态探测当前 App 真实缓存目录**（★最隐蔽：硬编码 `com.legado.app.release` 在自己手机上完全正常，换 legado-E(`io.legado.app`) 就挂；解法=`java.readFile('/')` 触发 FileNotFoundException，从消息正则提取 `.../cache` 前缀）②**CENC 要清"一组"box 不是 1 个**（encv→hev1 / enca→mp4a / sinf·tenc·**senc·saiz·saio**→free；★Team 播放器宽容会忽略 senc，**E 版见到 senc 就拒播**；诊断信号"Team 能播/E 版不能"=直接排除解密错误，锁定播放器严格度差异）③**encv 必须改 hev1 不是 hvc1**（参数集内嵌样本=hev1 语义；写 hvc1 会让 MediaCodec 拒绝整条视频轨→**只有声音没画面**，ffmpeg 宽容会掩盖必须真机验证）④文件完整写入且能读回（★`readFile` 用相对路径，播放用绝对路径；磁盘满会 ENOSPC 静默失败）⑤必须有 retry（CDN 间歇 Connection reset，★域名不能互换只能同域重试）⑥默认画质选最小可用档（hex 通道内存峰值≈文件×4；360p=28MB✅/1080p=92MB❌）⑦codec 避开 bytevc2（ByteDance 私有编码安卓解不了；★**同站不同 aid 编码策略完全不同**——aid=8662 低档全 bytevc2、aid=1967 全档 bytevc1 可播且 URL 是 base64 明文）⑧**jsLib 作用域≠规则作用域**（放 jsLib 的函数内 java 不可用，eval_js 测正常但真实规则返回空→**必须内联到规则顶部**）⑨字节回写必须 `System.arraycopy`（`bytes[i]=dec[i]&255` 报"无法将255转换为java.lang.Byte"）⑩文件名唯一+缓存复用（固定文件名导致多剧互相覆盖）；★**排查 Checklist 10 步**（第 1 条最重要=debug 输出的实际字符串往往就是答案，本次 `file:///xxx.mp4` 缺目录前缀一眼就该看出，却绕了三轮）；★**构建闸门 5 道**（含"零硬编码路径"：全文搜 com.legado 只允许出现在兜底默认值；手改长 JSON 里的 JS 是高危操作，加 retry 时多插一个 `+` 就语法错）；★**跨版本兼容三件事**（第三方库 R8 裁剪 / 播放器宽容度 / 包名不同）+ **E 版模拟验证法**（字符串替换屏蔽 hutool+bouncycastle 后 eval 跑全链路，不用等真机）；★性能速查（hex 转 bytes 用 BigInteger 330ms vs 纯 JS 10439ms/512KB，**提速 164 倍**）；★四条铁律 + 完整可用的 ruleContent 模板；案例 examples/番茄短剧漫剧_www.fqnovel.com.{json,md}
- [references/方法-视频书源完全指南.md](references/方法-视频书源完全指南.md) — **一切"正文=播放地址"的站点(影视/动漫/短剧/MV/图集混合)总纲**：bookSourceType=4→BookType.video→VideoPlayerActivity 全链路源码拆解；★★三条铁律(正文可携带URL选项给播放器塞Referer/Cookie / `dnsIp`救不了播放器拉流只能换主机名 / m3u8给地址、MPD可内联文本)；`subContent`=B站XML弹幕通道；卷=线路章=剧集的官方多线路模型；当前集一致性四索引两陷阱(新书durChapterIndex=0、playlist新→旧)；播放页快照→`useweb`+`callBackJs`自造切集跟随；三诊断键(h1now/h1ev/h1diag)；DNS污���·SNI封锁·CF挑战三重鉴别+CDN原生主机替换法；`_token`匿名也发的登录判据陷阱；跨镜像域Cookie同步；登录UI控制台38行骨架；四种形态开箱模板；**51条避坑+22项验收**；5个视频站对照档案(hanime1/mdcmai/huangguo/hlwf6/novelServices)
- [references/方法-小说漫画视频三合一书源详解.md](references/方法-小说漫画视频三合一书源详解.md) — ★**一个书源同时承载 小说/漫画/视频 三种内容形态**（禁漫天堂Pro v1~v14 蓝本,check 1/1）：适用场景三问（站点真多形态/公共代码多/一次登录覆盖）；**四招总纲**（模式变量+字段整体分发+统一列表解析器+按URL类型分支）；发现页jmode下拉(infoMap.save+refreshExplore清两级缓存)与搜索前缀分发(#小说 !视频 零UI成本)；★统一解析器jmParseList输出JSON字符串数组纯键JSONPath双版本通用、bookUrlPattern绝不匹配搜索url、新类型入口四处同接(parser白名单/init分支/目录/pattern)；★**作者字段宁缺毋滥+特征行定位**(main_tag=2链接或行文本"作者:"开头，无则空绝不回退书名——周更/收藏夹页无作者行的著名翻车)；★**单击作者本源搜索=官方kind芯片原生机能**(kind头部插作者→lbKind点击回调SearchActivity(source,kind)，useweb面板内无此通道)；★book.type必须在chapterList里动态设(刷目录removeAllBookType冲掉init设置,位掩码4/8/32/64)；收藏体系闭环(登录/解冻/选夹/loginUi+useweb面板三态收藏+faved缓存优先根治重开误判+**重复收藏报错=已收藏铁律**(HTML alert清洗后关键词判定顺势修UI)+attr||attr短路失效需jmAttr显式判空)；**发现页标签数据化方法论**(结果页200+卡片统计search_query链接频次=真实热门标签,25→58剔除女性向/敏感词)；14条避坑K1~K14+6步验证(node仿真/App真Rhino回放/check_source/debug多入口/真机验收清单/dpaste深链)+8项移植改动清单；与X夜社六形态/聚合换源/线路轮换三类对照
- [references/方法-单源多模式切换书源制作.md](references/方法-单源多模式切换书源制作.md) — ★**一个书源同时承载 小说/漫画/写真/视频/动漫/有声 六种内容形态**（X夜社范式）：模式变量(`source.setVariable/getVariable`，`loginUrl` 顶层具名函数 `set_laiyuan()` + `loginUi` 六按钮）→`exploreUrl`/`searchUrl`/`ruleToc.chapterList`/`ruleContent` 四处 JS 按模式分支；★**`book.type` 必须在 `ruleToc.chapterList` 里动态设置**（`WebBook.getChapterListAwait` 刷目录时会 `removeAllBookType()` 冲掉详情页 type；位掩码 video=4/text=8/audio=32/image=64）；★**视频/音频用 `data:text/html;base64,` 内联播放页 + `java.startBrowser` 交给内置浏览器**（绕开 ExoPlayer 防盗链与 m3u8 环境依赖，`muted`+`playsinline`）；★图片形态必须自拼 `<img src="…">` **双引号**否则官方 `imgPattern` 匹配不到；`player_aaaa={...}` JSON 提直链+海报；顶层 `bookSourceUrl` 非 URL 的取舍；**16条避坑 K1~K16 + 12步制作清单 + 移植改动表**；与"换源/换域名"三类切换对照
- [references/方法-聚合源状态漂移修复与选站面板-rrssk.md](references/方法-聚合源状态漂移修复与选站面板-rrssk.md) — ★**多域名聚合源"全局状态漂移病"总纲**（rrssk聚合44域名蓝本，check_source 1/1×3）：症状三张脸（书架书正文为空=server停boluomao走data-obf分支取空/搜索中转失败/校验器洗变量炸`/list-`相对URL）与写者清单（select/init对齐/setSite/began/校验器）→**根治=URL自治五层**：`SRV(book.bookUrl/baseUrl)`推导域名（同域优先全局scheme）、chapterList输出绝对URL+`chapterUrl=$.chapterurl`、`dataEncrypt`显式缓存键+scheme兜底、**别名书按页面data-aid实际值自纠**（hggjfg→hgg）、toc取值链`book.url→tocUrl(http)→baseUrl(http)`、`{{NBK(book)}}`空书名保护；**选站三件套**：登录面板（`loginUi=<js>`运行时从hosts生成47行网格/action跑在`lifecycleScope.launch(IO)`可过refreshExplore主线程检查/`BaseSource.evalJS`单参Rhino调不到/login()仅非空文本行才调）+ 发现下拉（**SET移进select action**——evalButtonClick带infoMap绑定、kinds求值不回写防过期live InfoMap覆盖、default跟随server）+ 下拉下方**状态栏**（Type.button viewName动态读GET真值，3~19单引号字面量规则）；**check_source三坑**（无UI infoMap洗变量/哨兵只认空串与{}→改`!GET(key)`/kinds两级缓存）；**模板引擎与htmlunit四铁律**（`{{}}`无括号=属性路径恒空带括号=JS求值/Kotlin空Java串truthy须`String(x).length>0`/java.lang.String无.length/evalJS默认参数Rhino单参调不到）；**K1~K18避坑 + Node行生成仿真/真机kinds求值/污染态对照/check_source×3/全字段md5/dpaste深链交付法**；架构篇=[聚合源多域名架构设计](references/聚合源多域名架构设计.md)，案例=[rrssk聚合_44域名](examples/rrssk聚合_44域名多站聚合.md)

- [references/方法-网易云类weapi加密站的明文接口降级方案.md](references/方法-网易云类weapi加密站的明文接口降级方案.md) — ★**加密接口返回200空体不是算法错,是站点策略**(源站22ms秒拒,沙盒与真机同结果):固定secKey做JS出Python解双向验证证明加密正确后整体降级到/api/明文GET;★★★三条App级硬知识:`getElements`只接受List/Array/NativeArray(**@js列表规则return JSON字符串→列表大小0,必须return JS数组**;与E版字符串数组需求互斥);**Rhino的java.lang.String没有.length属性**(NaN<256使补零循环永不执行,所有Java返回字符串必须String()包裹);`createSymmetricCrypto(AES/CBC/PKCS5Padding,k,iv).encryptBase64()`与CryptoJS PKCS7**逐字节一致**;网易云/api/接口全清单(搜索/详情/歌单/播放直链无Referer/歌词/榜单/分类);音频书源四机制(bookSourceType=1自动audio/subContent=歌词通道/tocHtml复用省请求/禁replaceRegex);Cookie粘贴登录(putLoginHeader自动写CookieStore);12条避坑
- [references/方法-音乐书源制作指南.md](references/方法-音乐书源制作指南.md) — ★**音乐类书源(bookSourceType=1)通用制作总纲**(网易云听书源蓝本,check 1/1):**内容模型设计**(歌单=书N章/单曲=书1章/榜单=书/歌手=书的映射决策表+封面歌手头像兜底+歌词当简介+时长当字数);★★**音频类型官方机制源码级**(BookSource.getBookType=audio(32)/BookList自动设类型/刷目录removeAllBookType冲掉type/subContent→putLyric歌词LRC同步/isAudio跳过HTML净化/**replaceRegex逐行trim会切断播放URL必须留空**/tocUrl留空tocHtml复用省一次请求);★直链获取(音质参数320k→128k降级兜底/播放器不带Cookie需java.getCookie手拼/30分钟过期重进自愈/无版权VIP用throw中文提示不返回空正文);★歌单全曲目补齐(trackIds全量+每批≤50批量补名,225曲≈10s);接口设计套路七清单(搜索type区分单曲歌单/offset分页/c与cat参数encodeURI);发现页ExploreKind组织(分组标题行+榜单/推荐/分类/新歌);登录Cookie粘贴优先四件套;加密降级原则链向weapi姊妹文档;**完整开箱模板**(顶层/bookList/chapterList/content+subContent双通道/发现页多模板自适应);**20条避坑K1~K20**;验证方法论(音频特有:正文必须纯URL且indexOf('http')===0,歌词同步只能真机看);移植到QQ/酷狗/酷我/bilibili/喜马拉雅的改动清单(只需改7条接口URL+字段路径,通用骨架不用动)
- [references/方法-音频书源CENC解密与音色切换.md](references/方法-音频书源CENC解密与音色切换.md) — ★**番茄听书音频书源实战**(check 1/1):**CENC 解密全链路**(spade 无需解密判据/密钥派生 `v8=len-(r0^r1^r2)+47`+`work[i]=(-21-popcount(i)+(prev^old))&255`/逐样本 AES-CTR `iv16=senc[i*8:i*8+8]+8×0x00`/解密成功判据=首样本头 `FF F1 0A 5A` AAC-HE ADTS/fourcc `enca→mp4a`);**★★★三个 JS 环境绑定差异**(loginUi 的 `<js>` 无 source/java/infoMap → 生成函数必须无参;按钮 action 只有 java(SourceLoginJsExtensions) 无 source → 函数签名统一 `jv`;`jv.put/get` 与 `source.put/get` 同一键空间);**loginUrl 必须非空**;**infoMap 不注入的诊断法**(action 里 dump `eval('typeof X')` 清单 → 实测 `infoMapType=undefined`);**音色逐按钮 UI 模板**(`<js>FQ_atoneRows()</js>` 运行时生成 + 三重提示 toast/longToast/reLoginView);**四个 Rhino 硬约束**(arraycopy 回写/循环外 Cipher.getInstance/主动 gc/fourcc 限 moov 范围);**java.downloadFile 文件名必须唯一**;音频三件套(bookSourceType=1/chapterList 里 setType(32)/content 返回 file://);搜索相关度排序 FQ_asearch2
### 难点方法论专题（13 篇 · 2026-09-14 批量沉淀）

> 从 20+ 个生产书源的历史记录中提炼的**跨站可复用**难点，按"T0 高频再现 / T1 单站高价值 / T2 工程方法论"分层。每篇含：现象谱系 → 源码级依据 → 解法阶梯 → 开箱模板 → 避坑清单 → 案例档案表。

**T0 — 已在 3 个以上源反复再现**

- [references/方法-AnalyzeByJSoup状态污染与绕开总表.md](references/方法-AnalyzeByJSoup状态污染与绕开总表.md) — ★**最高频难点(8+源)**：同实例连调CSS索引规则→字段取空/串位/行分隔符被吞三张脸；`AnalyzeRule.kt:151`实例缓存源码实锤；"书籍总数:1"完整链路；新旧实例对照法复现；四级解法阶梯(@js直取/XPath免疫/结构规避/微型测试源)；result Element vs String 类型矩阵；10条避坑+一分钟口诀
- [references/方法-Cookie标记型限频破解.md](references/方法-Cookie标记型限频破解.md) — ★**6站同款机制**(ppxsw/book630/xuken/ggd66/35sw/lianaiya)：服务端只查Cookie键存在不校验值→永久绕过；三类限频(A/B/C/D四实验)鉴别决策树；`cookie.setCookie`整体替换语义巨坑；本App Cookie API可用性清单；IP级惩罚窗口与离线验证法；loginCheckJs倒计时透传；POST+retry的oneShot坑
- [references/方法-legado各版本行为差异对照.md](references/方法-legado各版本行为差异对照.md) — **跨版本分发必读**：LT/官方/legado-E(Lyc)三版22项差异总表；★头号差异=列表规则返回值协议(E版无Mode.Js分支→必须JSON字符串数组+纯键名)；Kotlin属性vs方法`gv()`；三作用域能力矩阵；Book.type位掩码4/8/32/64与刷目录冲掉type；-100 Cookie配对错乱三层真相；API存在性判定方法论(含ppxsw误判复盘)
- [references/方法-URL模板与DNS选线.md](references/方法-URL模板与DNS选线.md) — `{{}}`**每次请求二次求值**⇒动态域名自愈；模板七坑(空段整段吞/单模板小写化/`$`未定义/searchUrl@js静默降级/裸引号毁JSON/双JSON→NPE/真实换行)；URL选项全清单(dnsIp/retry/timeout)；`buildScopedDns`只劫持本域+去Cronet+与proxy互斥；hosts池测速选线闭环；探针法看最终URL；变量双通道+Rhino JsNull truthy

**T1 — 单站点但难度封顶**

- [references/方法-字体反爬三代方案演进.md](references/方法-字体反爬三代方案演进.md) — A图标PUA/B会话置换/C加密三型判别；★离线字形位图匹配建表全算法(包围盒裁剪+高斯模糊+L2归一化+矩阵乘+双参考字体融合+margin置信度筛)；固定guard Cookie锁定会话；**生产级运行时加载代码**(外置托管+哨兵校验+未知字原样保留+书籍级变量缓存)；getVariable语义澄清；97%精度的分层兜底
- [references/方法-多层密钥AES与轮换签名逆向.md](references/方法-多层密钥AES与轮换签名逆向.md) — 密文分型表；密钥定位四法(JS枚举/文件名随机→`?_=`回源/响应头旁路/信封自解)；动态种子信封(wendulou)；★**IV构造铁律**：`md5Encode`返回hex非raw digest、**首块乱其余好=IV错/全乱=key错**；晋江DES+头派生；★**花括号配平法**兼容每日轮换签名；随机对象名base64；破坏性单变量实验找真校验项(省90%工作量)
- [references/方法-图片不显示排查总表-加密之外的三条路.md](references/方法-图片不显示排查总表-加密之外的三条路.md) — 四象限归因；★**verify签名不绑主机**⇒自由换CDN主机(矩阵对照法)；SNI封锁→查CNAME换CDN原生主机名；★`blockNetworkImage`源码真相⇒`data:`内置封面完整方案(五护栏+候选链+状态回显)；根路径判活法与HEAD被拒陷阱；`imgPattern`硬性双引号约束；`java.webView`真机渲染探针；沙盒会完全误诊
- [references/方法-WAF与CF间歇故障及站点判活.md](references/方法-WAF与CF间歇故障及站点判活.md) — ★**判"站点失效"前的七维复测矩阵**+ggd8误判复盘；WAF家族分型表(自研挑战/GoEdge/CF挑战/CF抖动/1034/裸UA/限频/需登录)；**UA三种作用**(放行·模板分发·完整UA反被RST)；GoEdge POST强制人机；间歇TLS RST四件套(retry+异常文本校验+梯度等待+冷连接)；自伤型故障与离线验证纪律
- [references/方法-GFW-SNI封锁鉴别与绕过边界.md](references/方法-GFW-SNI封锁鉴别与绕过边界.md) — ★**「TCP 通 ≠ 能连」**：TCP几十ms通但TLS瞬间RST=**SNI域名黑名单**（区别于DNS污染的超时）；**30秒定性实验**（同一IP只换SNI，`cloudflare.com`做对照）；已被证伪的**9种SNI绕过写法**；★★**「无SNI」技术**（`createSocket(up, IP字面量, 443, true)`→JSSE按RFC 6066省略SNI）；★★★**Legado 自带 Cronet(QUIC) 且默认关闭**（设置→其他设置→Cronet；`enableQuic(true)`；libcronet 从 storage.googleapis.com 下载，**实测国内可达**）；**三条上游缺陷**（`HostResolverRules`被注释 / `dnsIp`与Cronet互斥 / `dns{}`只装okHttp）；**错误格式鉴别法**（`failed`小写=OkHttp，`Failed`大写=Cronet，`ERR_CONNECTION_TIMED_OUT`=DNS污染，`ERR_SSL_VERSION_OR_CIPHER_MISMATCH`=SNI是IP）；**完整vhost映射表**；**Glide天花板**；手机侧DoH可信度表；**22条避坑**；案例档案（IllustFerry/Pixiv-Shaft/pixez/ppxsw）
- [references/方法-付费墙与假登录墙甄别.md](references/方法-付费墙与假登录墙甄别.md) — ★**"请登录后继续阅读"多半是假登录墙**(63sg/35sw实测登录后仍锁)；五步甄别流程；登录态判据优先级(仅登录态渲染元素>入口链接>文案哨兵)；三级付费粒度处置；**SEO假正文陷阱**与四条防御；用户提示文案设计四原则；章级兜底不让整目录崩；9站对照档案表(同为"请登录"63sg假墙/ppxsw真墙)

**T2 — 工程方法论（最救命）**

- [references/方法-书源交付质量闭环.md](references/方法-书源交付质量闭环.md) — ★**"保存成功"≠"保存对了"**；六步流水线；`save_source`三语义(整体替换误传清库事故/同URL REPLACE/重置respondTime)；构建脚本四类自身bug(正则跨块吞锚/漏`+Q+`/`%`渗JS/heredoc吃引号)；零双引号零反斜杠纪律；**N字段md5回读闭环**(150字符分段二分+charCode逐字)；UTF-16vs码点/`getBytes('UTF-8')`不存在；dpaste+深链大源通道；30项交付checklist
- [references/方法-静默失败定位与探针法.md](references/方法-静默失败定位与探针法.md) — **"不要推理，要打印"**；13类静默失效总表；★IIFE漏return一个源三连犯(三字段三种症状)；四种探针(微书源+废域名看HTTP日志/eval_js真机离线复现/最小对照源/破坏性矩阵)；Rhino-jsoup语法坑合集；反射与内部类探测($后缀/getClass返回null)；症状→探针定位流程；三句口诀
- [references/方法-目录顺序与章节去重铁律.md](references/方法-目录顺序与章节去重铁律.md) — 两条源码级铁律(URL去重+不替你排序)；链式保序vs并发错序；★**"并发抓全页"能否用的判定**(详情页是否内联章节)；六类脏数据(倒序区/隐藏副本/幽灵页/镜像陷阱页/死章/占位项)；黄金特征class；aID≠章节序；虚拟章节fragment造法与污染清洗；`tocUrl`位置约束；串章三防护+`&nbsp;`碎片正则；顺序0违规验收法；12站档案表
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
- [examples/光遇聚合_www.gyks.cf.md](examples/光遇聚合_www.gyks.cf.md) — 客户端协议代理+云端 HTML→JSON 转译的三段式聚合源
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
- [references/方法-LAN-Web服务保存书源与全端点手册.md](references/方法-LAN-Web服务保存书源与全端点手册.md) — ★**LAN Web 服务全端点手册（书源交付/联调最强通道，wenku8 LAN 直存蓝本）**：认证头=**`x-legado-token`**（不是 token:/Authorization/查询参数；报"Web 书源访问令牌未配置或不正确"先查头名）+ POST 必须 **Content-Type: application/json**（form-urlencoded 时 postData 读不到→"数据不能为空"）+ **saveBookSources 吃数组 / saveBookSource 吃对象** + 响应恒 HTTP 200 成败只看 body.isSuccess；**不止保存书源**——写端点（saveBookSource(s)/deleteBookSources/saveRssSource(s)/saveReplaceRule/deleteReplaceRule/**testReplaceRule 离线测净化**(键 text+isRegex 显式 true)/saveBook/saveBookProgress/addLocalBook/saveJsSource(text/plain+≤1MiB)/**startBookSourceCheck 批量校验(必须先 save 否则 checkContent 快照不一致)**）+ 读端点（getBookSource(s) 回读**无 MCP 200000 截断**做 md5 字节级闭环 / **getHttpLogs+getHttpLog 取证不占 MCP 会话** / getBookshelf/getChapterList/refreshToc/getBookContent/cover/image/getRssSource(s)/getReplaceRules / getJsSourceApiTokenRequired=排障第一步）+ WebSocket（bookSourceDebug/rssSourceDebug/searchBook）；★**标准交付闭环**=saveBookSources 直存(>19KB 无压力、json.dumps 组包零失真、无 dpaste 限频/深链确认弹窗)→getBookSource 回读 md5 闭环(排除 respondTime/lastUpdateTime)→差异以 LAN 回读为准反推传输层；★通道决策树：有 LAN 优先 LAN(交付+验证)，无 LAN 才 dpaste/uguu+深链；含 K1~K12 避坑+用户环境速记
- [references/方法-App官方API书源与设备号风控-次元姬.md](references/方法-App官方API书源与设备号风控-次元姬.md) — ★**正版App的JSON后端做书源总纲（次元姬 api.hwnovel.com 蓝本,check 1/1×N,五轮发现页排布迭代定稿）**：★★**设备号风控**（服务端设备库：已知号200/任意新16hex→`400网络繁忙`/有序号403/缺头500；同IP好号新号对照排除限频；无离线激活接口→共享已验证设备号+登录面板「设备号」可自定义source.put('cydn')+header@js动态生成+loginCheckJs拦截）；**四件套加密门禁**（DES-ECB PKCS5 key=ZUreQN0E加密参数+requestId=UUID无杠+sign=MD5(base64拼串).大写+★timestamp必须JSON数字(字符串→500)；GET/POST同构+必带4客户端头）+★**签名无时间窗无重放→bookUrl直接嵌永久签名URL书架长生**；**crates.io拆包逆向降级路径**（GitHub被墙时GET crates.io download源码包+版本考古0.20.x已移除模块/0.19.2最高版）；★**VIP未购code=101不是错误**（~200字预览密文可解密+payAction复用chapter.url里param密文拿bookId/chapterId下单）；★★★**发现页排布终极铁律（源码实锤item_find_book.xml showDivider+margin/ExploreAdapter）**：固定layout_flexBasisPercent列数全面失效(0.5+0.5→竖排一列/0.33×3→两列)——唯一稳解=条目style={'layout_flexGrow':1}自动流式+分区标题行basis1整行url空；emoji撑大最小宽→条目纯文字；check_source首检=书架GET/签到POST第二；发现页签到提示放loginCheckJs(url/body Kotlin属性双通道+return r原样)；统一解析器pl()吃四容器+kind前3标签+wc()字数格式化；ruleBookInfo.tocUrl唯一合法位+目录bookId只在顶层bookChapter；K1~K12交付Q/A(手抄save必坏→回读md5/Python“\\n”双反斜杠坑/replace去前缀注意引号边界/node --check每轮必跑)
- [references/方法-Discuz论坛型TXT下载站书源制作.md](references/方法-Discuz论坛型TXT下载站书源制作.md) — ★**Discuz!/PHPWind 论坛型资源下载站总纲**（bookSourceType=3，蓝本墨香书阁 noveltxt.vip，check 1/1）：站点识别6特征（`_2132_` cookie前缀/`mobile=2`/**`thread-{tid}-1-1.html`**/`forum.php?mod=attachment&aid=`）；★★**三大命门**：①UA 决定模板（桌面 UA 会 302 到 `mobile=no` → header 必须钉死手机 UA）②**用户组权限要查表**（`home.php?mod=spacecp&ac=usergroup`，本站游客能搜、登录组被禁用搜索）③附件扣费=**服务端 302 到 attachcredit**（非 purchase 表单，直接给原始链接即可）；★★**双态架构**：清 cookie **+ 访问 index 重建 session 两步缺一不可**（只清→提示页，只重建→仍登录态），此后 Legado **含翻页的常规请求**才走对通道；★登录两坑（手机版接口触发验证码→改 PC 版；`loginhash` 服务端不校验可传任意值）；★`downloadUrls` 必须 `join('\n')`（JS 数组不是 Java List 会被判空）；★`searchUrl` 必须返回**纯 URL**（带 `,{json}` 会被当成 URL 一部分）；★列表解析用 `split('<li class="list">')` 而非非贪婪正则（嵌套 `<li>` 会提前截断丢简介/分类）；**K1~K15 避坑 + jsLib 骨架 + 4 类站点对照档案**
