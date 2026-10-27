# 方法-DNS污染间歇性线路自愈与Web服务字节级直传（黄果短剧 v9.6/v9.6.1）

> 案例：E版搜索失败 `SocketTimeoutException: whu.h2na6qa39.cc/2001::6ca0:a268 after 15000ms`。
> 关联：方法-单集视频目录污染与相关推荐池识别.md（同日 v9.5）、方法-黄果短剧发布页寻线与换源登录面板实战.md。

## 1. 间歇性 DNS 污染的识别

特征：**测速时活、用着死**。同一根域下部分子域部分时段可连，部分返回假地址。

实锤手段（沙盒 DNS getaddrinfo）：
- `whu.h2na6qa39.cc` → A=`108.160.170.41`（Dropbox 段，GFW 经典污染假 IP）+ AAAA=`2001::`（Teredo 段假 IPv6，用户日志正是连它超时）；
- 同根域所有子域全部超时；另一台设备（E版）却曾探活成功 → **逐查询随机投毒**；
- 健康根域 `arj2ftl0.cc`/`40ygo615.cc` 均为 CloudFront 真实地址。

## 2. 线路自愈 FIX（内联进 searchUrl {{}} / ruleExplore.bookUrl / ruleToc / ruleContent）

```
读 hg_line → 判 bad(坏根域) → TTL 180s 内直接返回缓存
→ 探活 cur/favicon.ico（{"timeout":8000} URL option 快速失败）
→ 活:刷新 hg_line_chk 返回
→ 死:平铺候选数组逐个探活,取首个活的写回 hg_line 并 longToast
→ 坏根域线路跳过探活直接迁移（置于 TTL 判断之前,每次请求都纠正）
```

要点：
- **坏根域必须从候选池剔除**（FIX 的 cands 数组 + loginUrl 的 hgRoots + hgCand 发布页根域过滤三处），否则"测速选线"会再次选中它；
- 探活用 `favicon.ico`（15KB 轻量、200 即活、DNS 污染直接异常判死），URL option `{"timeout":8000}` 防长时间挂起；
- TTL 180s 缓存保证列表页 21 张卡只有第一张付网络开销；
- ruleToc/ruleContent 用 `baseUrl.replace(/^https?:\/\/[^\/]+/, FIX)` 重写 host——**已收藏的坏线书也能救活**（bookUrl 里存的旧域名不影响加载）。

## 3. ★★★ {{}} 模板的 }} 截断陷阱（本次 check_source 抓到）

searchUrl 的 `{{...}}` 模板**按字符扫描第一个 `}}` 结束**。JS 代码里嵌套 for 循环收尾产生 `}}}}`（4 连）→ 模板在 `catch(e2){` 处被截断 → EvaluatorException「函数体后面缺少 }」→ 整个 searchUrl 失效。

修法（任选/并用）：
- 嵌套双循环改**平铺候选数组**（`var cands=['https://thu.arj2ftl0.cc',...]` 单层循环）；
- 无法避免的相邻花括号之间**插入空格**（`catch(e2){} }`，JS 语法合法、模板扫描不命中）；
- 保存后必须 check_source 官方校验——它抓这种截断比人工审查可靠。

⚠️ `<js>` 形式的 exploreUrl 无此问题，但 E 版对 `<js>` exploreUrl 兼容性未验证，多入口发现页建议保持静态字符串+走健康默认线。

## 4. ★★ 双 App Web 服务调试/投递通道（本次实战 API 面）

E 版 Web 服务（用户指名 1125）真实可用端点（未知路径回显 `web/xxx` 是 fallback，需甄别）：
| 端点 | 方法 | 说明 |
|---|---|---|
| `/getBookshelf` | GET | 全量书架 JSON（6653 本 16MB） |
| `/getBookSource?url=` | GET | **免令牌**回读书源 |
| `/saveBookSource` | POST JSON 原文 | 保存书源，`isSuccess:true` |
| `/saveBook` | POST JSON Book对象 | 书入库（getChapterList 前置条件） |
| `/refreshToc?url=` | GET | **强制重解析目录**（验证新规则的唯一真实途径） |
| `/getChapterList?url=` | GET | 读目录（先查缓存！0.0s 返回的是旧数据） |
| `/getBookContent?url=&index=0` | GET | 读正文，**必须带 index** |
| `/deleteBook` | POST JSON | 清理测试书 |
| `/searchBook*`、`/checkSource` | GET | **未实现**（fallback），不能用于验证 |

LT 版 Web 服务（1122）：`x-legado-token` 头鉴权，同款端点，保存/回读用法相同。

**服务会间歇离线**（App 后台被回收），重试间隔 15-20s 即可等到复活；单线程，长任务排队。

## 5. ★★ 字节级直传是唯一可靠的大 JSON 保存通道

本次第三轮 MCP `save_source` 手打 27KB JSON 再次产生多处转录损坏（style JSON 破损、`signojt`、`if(!https://...)`、参数截断等）并覆盖了 App 内好版本。

**标准流程**（本次实测双端成功）：
1. 工作区 Python 构建 JSON → 文件落盘；
2. LAN Web 服务 `POST /saveBookSource` 传**文件原始字节**（零转录）；
3. `GET /getBookSource` 回读 → **全字段逐个 json.dumps 比对** → PASS 才算落库；
4. MCP save_source 仅作最后手段，且必须紧跟 get_source 回读逐字段校验。

## 6. E 版目录缓存陷阱

`/getChapterList` 0.0s 返回的章节 host 还是旧坏线（`xjtu.h2na6qa39.cc`）——这是**数据库缓存的上次结果**，不是重新解析。必须先 `/refreshToc`（实测 3.3s 完成重解析，章节 host 变为健康线 `ruc.arj2ftl0.cc`）再读，否则会误判 FIX 未生效。

## 7. v9.6.1 全量验证矩阵（实测全绿）

LT（MCP）：check_source 1/1；发现7入口全通（短剧21卡5集/漫剧21卡3集/换脸21卡1集/魔改21卡1集/排行榜20卡33集/精品专题28卡21集/全部专题9专题24章）；搜索2关键词全通（单集/多集目录均正确）。
E（Web服务）：书源 v9.6.1 全字段一致；refreshToc 重解析成功走健康线；getBookContent m3u8 正确（hash 与 LT 一致）。
沙盒：分页 page1/2/3 唯一 ID 零重叠。
