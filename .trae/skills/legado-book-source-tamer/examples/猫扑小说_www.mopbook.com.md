# 案例：猫扑小说 www.mopbook.com 书源（261106）

成品：[猫扑小说_www.mopbook.com.json](猫扑小说_www.mopbook.com.json)（15.9KB，md5 `d9c57c1fe4592c53c0f80339b15c3b5e`（v3 发现页修复））
经验：[方法-GoEdge盾UA白名单与搜索凭证链](../references/方法-GoEdge盾UA白名单与搜索凭证链.md)

## 站点契约

| 项 | 值 |
|---|---|
| 内容站 | `https://www.mopbook.com`，UTF-8，静态 HTML |
| WAF | GoEdge 图片验证码（`GOEDGE_WAF_CAPTCHA_ID`），**桌面 Chrome UA 拦截、Android 移动 UA 放行** → `header` 钉死移动 UA |
| 搜索 | 首页假表单 → 外包 `https://www.rrssk.com/00PB.html`（官方搜索页），v10 每日轮换签名 |
| 搜索凭证链 | `GET 00PB`（`_t` + `PHPSESSID`）→ `GET /?action=signJs&v=日期`（**`__snc` HttpOnly Cookie** + 当日算法）→ `POST /?action=search` → 302 跟随到 `/?action=find` |
| 结果页 | `div.book-card` 20 条/页；`onclick` 的 `t=` 参数 base64 解码直达 mopbook 详情页 |
| 详情 | `og:novel:*` / `og:title` / `og:image` 全字段；`var articleid = "XXX"` 取书 ID |
| 目录 | 首 100 章在 `.chapter_list`；第 2..N 页 `POST /index.php?action=loadChapterPage`，`data=AES-256-CBC({"id","page"})`，key=`Hi3yccTfyPoxfoexMyZ2ohk0xFgjj1mN`，iv=`2685853201487428` |
| 正文 | `<div class="content">`；章节内分页 `/book/ID-章-页.html`；`nextContentUrl` 只认「下一页」；含 rrssk 家族 PUA 图标字体（复用 257 字 `CHARS` 表） |
| 发现 | 23 项：`rank-{{page}}.html` + `list-N-{{page}}/` 分类 + 首页 |
| 登录/发布页 | **无**（登录端点全 404，无备用线路）→ 不写登录 UI、不写线路按钮组 |
| bookUrlPattern | `https?://(?:www\.)?mopbook\.com/book/[A-Za-z0-9]+\.html.*` |

## 规则要点

```javascript
// searchUrl（@js 内完成凭证链 + 2.5s 节流，只返回最终 POST URL+选项）
GET 00PB → 抠 _t 与 signJs URL → GET signJs（下发 __snc）
→ ★花括号配平 eval 当日签名函数（跨日自适应，勿写死常量）→ return 'https://www.rrssk.com/?action=search, {"method":"POST",...}'

// chapterList（@js，双版本兼容）
首 100 章从 .chapter_list 正则取 → 循环 2..N 页 AES POST →
返回 new Packages.java.util.ArrayList()，逐项 JSON.stringify({chapterUrl,chapterName})

// content（@js）
PUA 图标还原 → CHARS 映射 → 纯正则取 .content → 转纯文本 → 逐行滤广告

// nextContentUrl（@js）
/<a href="(\/book\/[A-Za-z0-9]+-\d+-\d+\.html)"[^>]*>下一页/ → 末页「下一章」天然排除
```

## 验收（MCP debug_source 全链路）

| 场景 | 结果 |
|---|---|
| 搜索「斗破苍穹」 | 20 条 → 详情 → 252 章/3 页 → 正文 2 页 ✅ |
| 搜索「遮天」 | 20 条 → 详情 → 107 章/2 页 → 正文 3 页 ✅ |
| 发现 `list-4-2` | **28 本**（v3，逐页不同）→ 详情 → 正文 2 页 ✅ |
| 发现 `rank.html` | 51 本 → 详情 → 3084 章/31 页 → 正文 2 页 ✅ |
| 分类 `list-4-21`（超界） | 内容与上页重复且无 next → 0 条自然终止，不写死页数 ✅ |
| `check_source` | **通过 1/1**（v2 复跑） |
| 跨日回归 11-07 | 用户报搜索为空 → 403「签名校验失败」→ 改配平 eval 后两词全绿 |
| LAN 落库回读 | 逐字段一致（仅 `respondTime` 被校验器改写为 41668ms） |

## 三大新坑（详见经验文档）

1. GoEdge WAF 的 UA 白名单**方向相反**：桌面 UA 弹验证码、移动 UA 放行；四组对照（含反向验证组）定性。
2. 只拿 `_t` + 算对签名仍报「搜索凭证失效」→ **必须先 GET signJs 拿 `__snc`**；「签名校验失败」与「搜索凭证失效」是两句不同的分段探针。
3. `replaceRegex` 写成无替换文本的 `##...##` 会**把正文整段清空**（输出只剩 `　　n`）；正文清洗全放 `content` 的 `@js`、`replaceRegex` 留空。

另：`ruleBookInfo.init` 里 `@js` 不返回值会触发 `AssertionError: 内容不可空`；`out.push` 与 Java `list.add` 不能混用；`java.base64Encode(byte[])` 在 Rhino 得到对象地址串，必须手写 JS base64。

> 最终仍需在 Legado APP（LegadoTeam 官版 + Luoyacheng/legado-E）里实测搜索/发现/目录/正文/章节内翻页。
