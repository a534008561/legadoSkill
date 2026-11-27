---
name: 方法-百度搜书聚合源体检与ba索引崩溃及大源占位符事故
desc: 通用聚合搜索源(玄奇Pro V50百度搜书)全链路体检方法、debug_source四类URL前缀语义、ba[2]正则null崩溃修复、大书源save_source占位符落库事故与LAN整文件恢复铁律
---

# 百度搜书(玄奇 Pro V50 通用聚合源)全量体检 + ba[2] 崩溃修复 + 大源落库事故

## 〇、适用对象
`bookSourceUrl` 是中文标识(非 URL)、走 `www.baidu.com/s?wd={{...}}` 搜索、规则是"通吃任意小说站"的嗅探式超长 JS(单条 ruleContent.replaceRegex 数千字符)。这类源没有固定目标站，体检必须"规则正确性"与"搜索命中质量"分离验证。

## 一、debug_source key 四类前缀语义(★先搞清再用，否则全程误判)
| key 形态 | 实际调试入口 | 备注 |
|---|---|---|
| 裸 `https://...` | **详情页**(详情→目录→正文完整链路) | ★验证真实行为只用这种 |
| `++URL` | **目录页**(只跑 ruleToc) | 跳过详情阶段 book.putVariable 预设的 嗅/除/查/ba 变量 |
| `--URL` | **正文页**(只跑 ruleContent) | |
| `::URL` | **发现页**(ruleExplore) | 本源 ruleExplore={}，走它会超时/空 |
| 关键词 | 搜索(→取第一条结果走详情→目录→正文) | |

★关键坑：`++URL` 因跳过详情预设变量，兜底分支行为与正常流程不同。ax81 用 `++URL` 直调目录页只抓到 2 条"APP下载"广告，**这是调试模式固有局限不是规则 bug**；用裸 URL 走正常链路则正确出 14 条真实章节 + 正文跨 2 页合并。判定规则对错一律用裸 URL。

## 二、体检发现的两类问题(必须分离)
### A. 搜索命中质量(生态问题，非规则 bug)
- 热门词「斗破苍穹」9 条结果全是百度系：`dushu.baidu.com/pc/detail`(SPA 无目录) / 百度百科 / 百度视频 / 腾讯游戏 / 起点正版页 / 电视剧介绍 / lewan 游戏。**无一条真实小说站** → 详情/目录必空。
- 「斗破苍穹 全本 小说」三页全是阅文系 `readnovel.com/bookquery/...`、`hongxiu.com`(SPA)，第 3 页才出现 1 条 `quanben5.com`。
- 关键词加"笔趣阁 在线阅读"或用源自带 `书名$站点`(→`site:` 限定) 才能命中真实站：630wang.cc(已弃用 IPv6 假解析)、ax81.com、uu-xs.net、quanben5.com、jurewx.com。
- 连续搜索触发百度风控 302 → `bioc-static.cdn.bcebos.com/pages/ds_svcp.html?...&biocOrigin=seccaptcha-gs.baidu.com`；此时 debug 通道全灭，但 eval_js 通道的 java.ajax 仍能取正常页(出口/会话不同)。
- ★结论：不要试图用规则修复"搜不到真实站"，这是百度搜索生态。规则本身用真实站验证全绿即可。

### B. 规则真 bug：`ba[2]` 正则 null 崩溃
复现：`++URL` 直接调试任意目录页 →
```
EcmaError: TypeError: 无法读取 null 的属性 "2" (<script>#48)
> 48: if(xi=(id=ba[2]).match(/\?[^=]+=([^&]+)/)||...)
```
根因(ruleToc.chapterList 嗅探兜底分支)：
```js
ba=(ba=String(java.get("ba"))).match(/(\?(?:[^=]+=)+)(.+)$/)||ba.match(/(?:[^/_-][/_-]([^/._-]+))?[/_-]([^/._-]+)(?:\/|\/index[^/]*|\.[^/.]+)?$/);
if(xi=(id=ba[2]).match(...)) ...
```
`java.get("ba")` 由详情页 ruleBookInfo.tocUrl 末尾 `java.put("ba",r)` 设置。当 `++URL` 跳过详情、或详情页识别失败没 put ba 时，两次 `.match()` 全返回 `null` → `null[2]` 抛 TypeError → 整条目录崩。

**最小修复(加两级兜底，不改其他任何逻辑)**：
```js
ba=(ba=String(java.get("ba")||baseUrl)).match(/(\?(?:[^=]+=)+)(.+)$/)||ba.match(/(?:[^/_-][/_-]([^/._-]+))?[/_-]([^/._-]+)(?:\/|\/index[^/]*|\.[^/.]+)?$/)||['','',''];
```
- `||baseUrl`：ba 为空时退回用当前 URL 提 ID。
- `||['','','']`：两级 match 都失败给空数组，保证 `ba[2]` 不崩；后续 `id.match()` 对空串安全返回 null，走 `$("[title]")` 兜底。
- 回归：`++URL` quanben5 从崩溃 → 1646 章全量解析 + 正文完整；正常流程 quanben5/ax81 仍全绿。

### C. 静态门禁建议项
lint 报缺 `bookUrlPattern`/`concurrentRate`。本源 bookUrlPattern 难写通用正则(任意小说站)，**不加**以免误伤。补 `concurrentRate=3/1000` 防御性限速(1秒3次)，契合用户"搜索别太频繁"偏好；注意全局限速会拖慢多页目录(见 /topics/legado-ratelimiter-and-speedtest.md)，但本源目录多为单页全量影响小。

## 三、★★大书源落库占位符事故(最惨痛教训)
### 事故经过
源 33KB(紧凑 JSON 33841 字符)，直接用 MCP `save_source` 传全量太长。我图省事用 `PLACEHOLDER_NAME_RULE` 等占位符代替 6 个超长 @js 规则后保存——**工具返回"已保存"且占位符真的落库了，原源当场报废**。

### 铁律
1. **save_source 绝不写占位符，哪怕临时过渡也不行**——它不校验规则可执行性，占位符原样落库并覆盖原源。
2. 大源(>25KB)一律走 LAN web 服务整文件落库(本环境 `http://192.168.10.2:1122/saveBookSource`，令牌头 `x-legado-token: a7894563`)：
   ```bash
   curl -s -X POST http://192.168.10.2:1122/saveBookSource \
     -H "x-legado-token: a7894563" -H "Content-Type: application/json" \
     --data-binary @source_fixed_compact.json
   ```
   端点辨析：`/saveBookSource` 成功(isSuccess:true)；`/saveSource` 返回路径串不是端点；`/saveBookSources`(复数) 报"转换源失败"。
3. HTTP 200 ≠ 落库。保存后必须 `get_source` 回读并做三重核对：
   - `PLACEHOLDER` 残留检查(整包 JSON grep)
   - 逐字段 got==want 比对(忽略 lastUpdateTime/respondTime 等应用改写字段)
   - 关键规则回归 `debug_source`(裸 URL 跑一遍完整链路)

## 四、体检 SOP(通用聚合源)
1. `get_source` 导出 → 本地 `source_original.json` 留底。
2. `source_lint.py` 静态门禁。
3. 搜索：eval_js 抓 `baidu.com/s?wd=...` 列 h3 a + 跟随 302 看落地域名构成 → 判断是生态问题还是规则问题。
4. 详情/目录/正文：用**裸 URL** 对 1~2 个真实站(本例 quanben5 单页全量 + ax81 章内分页)跑完整链路。
5. 只对确证 bug 做最小修复，回归验证。
6. 大源 LAN 落库 → 回读三重核对 → 再次 debug 回归。

## 五、沉淀
- 记忆：`/areas/baidusoushu-book-source.md`
- 同类聚合源搜索生态参考：`方法-搜索引擎书源反爬验证弹窗人工过盾.md`
