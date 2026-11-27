# 69書吧(www.69shu.xyz) 书源示例 · 261127

## 成品
- 书源文件：`69书吧_www.69shu.xyz.json`（单对象 JSON，可直接导入 Legado）
- 主用版本：LegadoTeam/legado（MCP 调试保存）；兼容 Luoyacheng/legado-E（LAN WS 1126 调试、1125 保存）
- 构建脚本与调试脚本：`/workspace/69shu/build_source.py`、`ws_debug_e.py`

## 站点特征
- 繁体公开小说站，无需登录、无发布页；搜索 POST `/search`（searchkey）
- 列表统一 `.book-coverlist`；详情 og meta 全字段；目录每页 100 章
- 目录/正文各页动态混淆：每次请求随机换变量名/属性名/算法(XOR链、RC4、rotate+XOR)/base64 段数
- ESA WAF 对首次 POST 搜索返回 403 + Set-Cookie + JS 跳 `/search`（CookieJar 存后重试即 200）

## 规则要点
1. **目录/正文**：不硬编码算法，抠出站点解密函数在 `@js:` 沙盒 eval 调用（见 references《方法-动态混淆站点 decrypt函数提取法.md》）
2. **搜索**：`searchUrl` 先 `java.ajax(首页)` 预热；`loginCheckJs` 检测极短盾页用 `java.post` 重发
3. **发现**：`exploreUrl` 用 `@js:` 动态返回 31 项（3 个 `url:null` 分组标题 + 28 子入口），分组标题整行铺满
4. **T2s**：所有显示字段用规则链 `CSS@text\n@js:String(java.t2s(String(result)))`，URL/ID 不转
5. **翻页**：目录按 `共X章`+`章節目錄(A-B)` 算总页数；发现用站点 `{{page}}`，均未写死页码上限
6. **限速**：`concurrentRate: 2/1000`，未主动探测搜索频率

## 验证记录
- LT MCP：搜索 54 本 → 详情 → 目录 118 章/3 页 → 正文 → 发现 99 本全绿
- E LAN WS 1126：同链路全绿；双端回读规则逐字段一致
- 静态门禁 source_lint.py 全通过
