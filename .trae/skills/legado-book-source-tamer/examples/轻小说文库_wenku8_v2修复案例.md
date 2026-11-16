# 轻小说文库书源 v2 修复案例（261116）

## 案例信息

- 站点：轻小说文库 `www.wenku8.net`（备用 `.cc` / `.com`，jieqiCMS，GBK）
- 书源：轻小说文库，bookSourceUrl 主键 `https://www.wenku8.net##`（保持不变，避免主键冲突）
- 故障现象：用户报"搜索没结果/报错"，随后实测发现"发现列表规则错误 ScriptException"
- 成品：`examples/轻小说文库_www.wenku8.net.json`（v2，27971B，已覆盖旧版）
- 相关经验：`references/方法-CF拦截切备用域三坑-charset403与相对URL主域补齐与体检假阴性.md`

## 一、根因（三层叠加 + 一个交付后暴露的第四层）

### 层1：主域被 Cloudflare 全站拦截

`www.wenku8.net` 连首页都返回 CF 挑战/封锁页（`Just a moment...` / `Sorry, you have been blocked`，HTTP 403）。书源所有 URL 写死 `.net`，全链路瘫痪。`.com` 同样被拦。

对照实验（`eval_js` 里 `java.connect` 批量探测）：`.cc` 首页/详情/目录/正文/榜单/标签全部 200。⇒ 切 `.cc`。

### 层2：备用域 `.cc` 对 `charset=gbk` query 参数返回 nginx 403

```
.../search.php?...&charset=gbk       -> 403 (LEN=139 nginx)
.../search.php?...&charset=GBK       -> 403
.../search.php?charset=gbk&...       -> 403
.../search.php?...&page=1            -> 200
```

只要真实 query 出现 `charset=...`（任何形态）就 403。

**解法**：charset 移到逗号 option `...,{"charset":"gbk"}`。option 不进真实 query，故不 403；且 AnalyzeUrl 的 `encodeParams` 与 `OkHttpUtils.text` 共用该 charset，GBK 编码+解码一步到位。`{{java.encodeURI(key,"GBK")}}` 随之简化为 `{{key}}`。

### 层3：searchUrl 相对路径被主域补齐

`eval_js` 的 `java.connect('https://www.wenku8.cc/...')` 正常拿 373 卡片，但 `debug_source` 一直 0 条。用 `get_http_logs` 看真实请求才真相大白：

```
GET https://www.wenku8.net/modules/article/search.php?... -> 403   ← debug 实际发这里
```

根因：searchUrl 是相对路径 `/modules/article/search.php?...`，AnalyzeUrl 用 **bookSourceUrl 主域 `.net`** 补齐 host，规则里 exploreUrl 写的 `.cc` 根本救不了 searchUrl。

**解法**：searchUrl 改绝对 URL `https://www.wenku8.cc/...`。

### 层4（交付后用户实测暴露）：`<js>` exploreUrl 里 option 双引号没转义

批量把 `&charset=gbk&page=` 替换成 `&page=...,{"charset":"gbk"}` 时，写进 **JS 双引号字符串**里的 option 双引号是裸的：

```js
E.push({title:"总排行榜",url:"https://...&page={{page}},{"charset":"gbk"}"});
//                                                  ↑ 这里提前闭合字符串
```

103 处全错 → 用户一开发现页就报：

```
ScriptException: 在属性列表的后面缺少 "}" (<script-920>#5)
```

之前自测只测了 `debug_source key="::URL"` 直连（跳过 `<js>` 编译）和搜索，都没触发 `<js>` 编译，所以漏掉了。

**解法**：JS 源码里转义成 `{\"charset\":\"gbk\"}`（恰好 1 个反斜杠）。

## 二、最终修复清单

| 字段 | 修复 |
|---|---|
| 所有 URL | `.net` → 绝对 `https://www.wenku8.cc/...` |
| searchUrl charset | `&charset=gbk` → `,{"charset":"gbk"}` option；`{{java.encodeURI(key,"GBK")}}` → `{{key}}` |
| exploreUrl `<js>` 内 option | 103 处 option 双引号在 JS 字符串内正确转义 `{\"charset\":\"gbk\"}` |
| loginUrl / loginUi / jsLib / header Referer | 全部 `.net` → `.cc` |
| concurrentRate | 新增 `1/500` 保守限速 |
| bookSourceUrl 主键 | 保留 `.net##` 不变（避免主键冲突） |

## 三、验证记录（App 内 debug，全绿）

- 搜索："隔壁" 8 条，字段齐全；精确书名命中时 302 跳详情，Legado 原生处理完美
- 详情：书名/作者/分类/简介/封面/目录链接正确
- 目录：49 章 / 517 章 / 45 章 / 9 章（多本抽样）
- 正文：约 1.2 万字完整中文，无乱码无水印无广告
- 发现页 `<js>` 全文 eval：榜单 14 项 / 文库 15 项 / 标签 49 项 / 首字母 29 项 / 完结 3 项，JSON.parse 全通过
- 发现页真实访问：总排行榜 20 本、标签"只看完结" 20 本 → 详情 → 目录 → 正文
- 登录：登录提交、检查登录状态正常
- LAN 闭环：`saveBookSources` → `getBookSource` 回读 md5 一致

## 四、check_source 假阴性说明

`check_source` 报 `ScriptException`，但真机全绿。二分实验定性：

- 保留动态 `<js>` exploreUrl → 体检失败
- 静态化 exploreUrl + 完整登录 JS → 体检通过

结论：体检裸环境不绑定 `source/java`，跑不了依赖它们的动态发现页 JS，登录 JS 本身没问题。这是"登录站 + 动态发现页"书源的固有局限，不为过体检改坏功能。

## 五、可复用铁律（提炼）

1. debug 与 eval 结果矛盾 → 第一反应查 `get_http_logs` 的真实出口 URL（相对 URL 会被主域补齐）。
2. 备用域对 query 参数 403 → 试着把参数移到 `,{...}` option，option 不进真实 query。
3. 动态 `<js>` exploreUrl 交付前必须 `eval(去壳后的全文)` + `JSON.parse`，`::URL` 直连测不到 JS 编译错误。
4. JS 双引号字符串里内嵌 option 必须转义 \\"，层数用 `ord==92` 核对，别信终端 repr 的假象。
5. 精确书名 302 跳详情由 Legado 原生处理，不要画蛇添足写 bookList 兜底。
6. 不要把站点搜索限频误判为规则失效：连查会短暂返回"出现错误"页，等几秒或单次搜索正常。
