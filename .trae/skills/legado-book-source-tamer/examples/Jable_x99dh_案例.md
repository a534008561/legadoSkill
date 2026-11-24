# Jable 视频书源（x99dh 导航 18 线路）案例 261124

## 成品
- 文件：`examples/Jable_x99dh_video.json`（bookSourceType=4，30KB v2.0）
- 主键：`https://jable02.net`；分组：视频,R18
- 双端落库：LT MCP + LT LAN(1122) + E LAN(1125)，check_source 1/1，debug 五链路全绿

## 站点结论
- `x99dh.github.io` `encodedData` JSON（32站）→ `name==='Jable'` 18条线路；url 带 `/enter` 后缀需剥除
- 游客可看无登录；列表 `.video-img-box`、搜索 `/search/{key}/{page}/`、分页 `{page}/`
- m3u8 来源：详情内联 `var hlsUrl` → 同域 `/pumpres/` → 302 随机CDN → AES-128 HLS

## 关键坑（详见 references/方法-订阅源视频播放修复与CDN-Referer指纹.md §八）
1. **tip.ts 假片**：裸 m3u8 → 143B `tip.ts` 占位；带 `Referer` 同源根 → 54KB 真片。正文用 URL 选项 `,{"headers":{...,"Referer":"..."}}` 注入播放器（源码 player.mapHeadData=analyzeUrl.headerMap）
2. **目录污染**：详情页 23 张相关推荐卡，目录必须 @js 返回 java.util.ArrayList 只放 1 条本片
3. **测速 ajaxAll 并发 18 条报 SSLHandshakeException** → 串行 connect 兜底成功（8秒/18条）
4. 详情 `og:description` 常缺，简介兜底 `<h5 class="desc h6-md">` + h6 时间/观看数；分类用 `meta keywords`（不用全页 tags 会塞 120+ 标签）

## 面板
V1 静态 loginUi（E兼容）：发布页输入框 + 🧭一键取线路 + ⏱测速(ms写各按钮) + 12线路按钮翻页 + 🔍检查；全 Toast + viewName 动态文本。

## v2.0 发现页按网站制作（261124 追加）
- 从网站 `/categories/` 抓 12 个主题分类（含中文名+影片数）、`/tags/` 抓 115 个标签、`/latest-updates/` `/hot/` `/new-release/` 3 榜单
- `exploreUrl` 静态 JSON 数组 133 项 = 3 分组标题行（`url:''` + `style:{layout_flexBasisPercent:1,layout_wrapBefore:true,layout_justifySelf:'flex_start'}` 独占整行）+ 130 可点击入口（`{{JB_base()}}/{categories|tags|...}/{{page}}/`）
- ★分组标题行不进"分类Tab栏"（源码只收 type==url 且 url 非空），正好做视觉分区；全部项 `style:{}` 交给 Legado Flexbox 自动折行（不要手算字数/basis，emoji 会翻车）
- ★选择静态数组而非 @js 动态/select：check_source 对 @js exploreUrl 有"发现规则为空"误报风险；130 项静态全展开虽长但零兼容性风险，LT/E 双版一致
- 验证：App eval_js `exploreKinds`=133 项；debug 分类页 `/categories/chinese-subtitle/` 与标签页 `/tags/3p/` 均 24 卡全链路绿；check_source 1/1

## 按女优列表（261124 追加）
- 网站 `/models/{page}/` 按作品量排序，每页 20 女优；取前 3 页共 60 个热门女优（三上悠亜72部/枫カレン67部/河北彩花53部…）
- 书源 exploreUrl 追加分组「👩 按女优（热门60）」60 项 → 总 194 项（4 分组 + 190 入口）
- 订阅源 sortUrl 追加 60 行 `女优名(数量)::{{JB_base()}}/models/{slug}/` → 总 190 行
- ★`/models/{slug}/` VideoPlay 跟随 301 到 `/s1/models/...` 后正常返回 24 视频卡；书源 debug 全链路绿；女优列表页本身（`/models/`）是女优卡不是视频卡，**不能**直接做视频入口（会解析出 0 个视频）

## 分组折叠 + 登录切换分类模式（261124 追加）
- 书源 exploreUrl 改 @js 动态：4 分组标题点击 ▼/▶ 展开收回（榜单/主题默认开、标签/女优默认关），默认 19 项不刷屏；check_source 对 @js exploreUrl 误报"发现失效"是校验器裸环境限制，真机 eval_js/debug 全绿
- 订阅源登录界面新增「🏷️切换热门标签(115)」「👩切换按女优(60)」「当前模式」3 按钮；sortUrl @js 读 jbSortMode；切模式时改 sortUrl 末尾 `//mode=...` 注释使 ACache key 变化破缓存；WS 1123/1126 全绿
