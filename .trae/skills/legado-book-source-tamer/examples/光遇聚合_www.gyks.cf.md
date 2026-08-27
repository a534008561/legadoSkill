# 光遇聚合（🔅光遇聚合）案例索引

## 1. 基本信息

- **书源名**：`🔅光遇聚合(26.8.16)`
- **书源 URL**：`光遇聚合`
- **书源类型**：0（纯声明式 + jsLib 协议壳）
- **分组**：`聚合,番茄,七猫,书旗,塔读,QQ阅读,轻小说`
- **作者**：`光遇看书`（gyks.cf）
- **网站**：<https://legado.gyks.cf>
- **分析时间**：2026-08-28
- **分析方式**：`mcp__legado3__eval_js` 绑定 bookSourceUrl 调 `source.<字段>.substring()` 分段抽取

## 2. 关键尺寸

| 字段 | 字符数 | 备注 |
|---|---|---|
| jsLib | 146621 | 全部协议/UI helper 都在这 |
| exploreUrl | 10532 | 动态发现页 |
| searchUrl | 604 | 最小可执行 data: 协议 |
| ruleToc.chapterList | 5897 | 章节列表（含同步书架） |
| ruleContent.content | 6744 | 正文（含视频/段评/图片后处理） |
| loginUrl | 7361 | 顶层具名函数集（login/register/logout/user/checkStatus…） |
| loginUi | 6505 | JSON 数组式 UI（19 个按钮 + 2 个输入） |
| ruleBookInfo.init | 1830 | 详情页初始化（gydetail 协议解析） |
| ruleBookInfo.intro | 3606 | 富文本书籍信息（含讨论按钮注入） |
| ruleToc.chapterUrl | 894 | 章节 URL（含 gycontent 协议 + js 懒加载） |
| ruleSearch.bookList | 285 | 搜索结果（$.data 数组） |

## 3. 核心机制（详见 [方法-光遇聚合书源架构拆解.md](../references/方法-光遇聚合书源架构拆解.md)）

1. **data: URL 协议** — 全部 search/info/toc/content 都用 `data:;base64,XXX,{"type":"gyX"}` 协议壳
2. **统一 request() + hosts 切线** — 失败/超时自动递归切下一个 host
3. **JSON 变量系统** — `getVariable/setVariable` 序列化整个 source 状态
4. **跨字段 state 传递** — `java.put('book_id', ...)` / `java.get('book_id')`
5. **loginUrl = 顶层具名函数集 + loginUi = JSON 数组 UI** — lyc/改版双兼容
6. **checkEnv()** — 4 端适配（轻阅读/改版/苹果/安卓）
7. **createFilter/createButton/createText/createSvg** — 发现页 UI 工厂
8. **syncBookShelf** — 同步阅读进度到云端"用户书架"
9. **段评气泡** — createSvg 生成 data: URL + 协议 + showCmt 弹窗
10. **视频/听书/漫画分支** — ruleContent.content 末尾类型分发

## 4. 适用场景

✅ **适合光遇聚合模式**：
- 想做主流付费站（番茄/七猫/书旗/塔读/QQ阅读/起点）聚合
- 客户端能稳定，反爬/限频/登录态统一丢给云端
- 频繁加新平台/调上游
- 想给用户提供"书架同步""段评""音色切换"等增值

❌ **不适合光遇聚合模式**：
- 单一公开免费站（直接写更省事）
- 一次性抓取脚本（不值得搭云端）
- 临时小工具（5KB 以内能搞定的事）

## 5. 参考产出

- 完整架构详解：[references/方法-光遇聚合书源架构拆解.md](../references/方法-光遇聚合书源架构拆解.md)（30KB）
- 含最小可执行骨架（210 行左右 JSON）
- 含 hosts 切线、token 检查、UI 工厂、同步书架、段评气泡完整代码
- 含 4 端适配（轻阅读/改版/苹果/安卓）
- 含 10 个常见坑 + 验证清单

## 6. 抽取经验时遇到的元坑

| 坑 | 解决 |
|---|---|
| MCP `get_source` 单次输出上限 200020 字符，源 213KB 被截断 | 用 `eval_js` 绑定 url 后逐字段 `source.<字段>.substring()` 分段读 |
| `source.getSource(url)` 方法签名不匹配 | 直接用 `eval_js` 的 `url` 参数绑定，不用 `getSource` |
| `.jsLib.length()` 是方法不是属性 | 用 `.length()` 而不是 `.length` |
| `substring(0, 300)` 报 StringIndexOutOfBoundsException | 字符串比索引短时，substring 越界需先 `length()` |
| 200K 源文件无法用 Python json.loads（字符串内真实换行） | 走 `eval_js` 让 QuickJS 引擎处理 + source.field 子串返回 |

## 7. 经验总结（迁移到其他书源）

- 任何 50KB+ 的书源都优先用 `eval_js` 字段抽取
- 字段抽取顺序：先 `length()` 探尺寸 → 再 `substring(0, N)` 按 8KB 窗口分段
- JSONPath 写 `$.xxx` 时，云端响应必须 `{"code":0,"data":{...}}` 才走通
- `data:;base64,` 协议配对 `java.base64Encode` 编码 + `java.hexDecodeToString` 解码（hex 不是 base64！）

## 8. 工作流模板

未来需要做"云端代理型"书源时，直接调：

```bash
# 1. 用 eval_js 抽取目标书源所有字段
mcp__legado3__eval_js(js='<for each key> JSON.stringify({jsLib_len: source.jsLib.length(), exploreUrl_len: source.exploreUrl.length(), ...})</js>', url='目标书源URL')

# 2. 读 references/方法-光遇聚合书源架构拆解.md
# 3. 套用 §4 阶段 0~3 的搭建流程
```
