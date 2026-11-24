# 方法：订阅源 sortUrl 全站动态分类 + XML/HTML 双形态解析（Jable 261124 实战）

> 来源：x99dh 导航 Jable 站视频订阅源（type=2）。用户要求「分类 URL 按网站动态构建」——把单条 RSS 入口扩展为覆盖网站 12 主题分类 + 115 标签 + 3 榜单的全站导航。

## 一、订阅源 sortUrl 格式与书源 exploreUrl 的关键差异

| | 书源 exploreUrl | 订阅源 sortUrl |
|---|---|---|
| 格式 | **JSON 数组**（ExploreKind 对象，支持 type/select/style） | **文本多行** `标题::URL`，一行一个分类 |
| 动态线路 | `{{JB_base()}}` 在 URL 模板里 | 同左（`{{JB_base()}}` 是 AnalyzeUrl.replaceKeyPageJs 请求时求值，不受 sortUrl 的 @js 缓存陷阱影响） |
| 分类数量 | 132 项无压力 | 130 行无压力（本次实测） |
| 坑 | @js 动态 exploreUrl 会被 check_source 误报"发现规则为空" | sortUrl 整段 `@js:` 结果被 ACache 缓存（key=MD5(sourceUrl+sortUrl)），**线路必须放 `{{JB_base()}}` 模板而不是 @js 求值整个 sortUrl** |

本次 sortUrl 构造（130 行，跟随线路切换）：
```
💡 最近更新::{{JB_base()}}/rss/
主奴调教::{{JB_base()}}/categories/bdsm/
3P::{{JB_base()}}/tags/3p/
...（12 分类 + 115 标签）
```

## 二、★规则必须同时兼容 RSS XML 与 HTML 分类页（双形态）

RSS 入口返回 XML（`<item>`），分类/标签入口返回 HTML（`.video-img-box` 卡片）。用 `||` 依次尝试两种选择器：

```
ruleArticles = item||.video-img-box
ruleTitle    = title@text||.detail h6.title a@text
ruleLink     = link@text||.img-box a@href
ruleImage    = @js:(function(){var h=String(result);var m=h.match(/data-src="([^"]+)"/);if(m&&m[1])return m[1];m=h.match(/<img[^>]+src="([^"]+)"/);return m&&m[1]?m[1]:null})()
rulePubDate  = pubDate@text||.absolute-bottom-right .label@text
```

- XML 的 `item` 用 jsoup 小写标签选择器命中（不是 XPath `//item`——`//item` 在订阅源环境解析错位，WS 实测列表 12 条但标题/链接全空、文章链接拿到 sortUrl 本身）
- `ruleImage` 双正则：HTML 卡片取 `data-src`（`src` 是 1px 占位图），RSS description CDATA 里取 `<img src>`。返回值失败用 `null` 不用 `''`（**空串 `''` 经 JSON/`@js:` 转义链会被吞成语法错误**：WS 实测 `return m?m[1]:})()` 缺空串导致 SyntaxError）
- 分类页标题与书源同款（`.detail h6.title a@text`），已经书源 debug 24 卡验证过的选择器直接复用

## 三、★★type=2 视频订阅源 ruleDescription 必须留空（本次回归坑）

首版设 `ruleDescription='description@html||...'` → WS 日志出现 `⇒存在描述规则，不解析内容页` ⇒ **正文完全不解析**（不输出 m3u8，视频源播放必失败）。

铁律：**type=2 视频订阅源只要 ruleDescription 非空，Legado 直接用描述当正文、跳过 Rss.getContentAwait**（源码分支 "存在描述规则，不解析内容页"）。视频源必须 `ruleDescription=''`，靠 type=2 的 ruleContent 输出纯媒体 URL。

## 四、共享 sourceVariable 缓存键：书源与订阅源线路联动

Jable 书源（sourceUrl=`https://jable02.net`）和订阅源（sourceUrl=`https://jable02.net/rss/`）**共享同一 sourceVariable 缓存**（本次实测：书源面板测速后 `jbLine=jable01.com`，订阅源 `{{JB_base()}}` 立即跟着变）。这是优点（一处切线路全跟随），但交付前须 eval_js `cache.put(key, {...jbLine:默认})` 还原，否则用户看到的第一条线路不是默认。

## 五、验证链（本次全绿）

1. sortUrl 130 行写入 + LAN `/saveRssSources` 数组 POST（LT 1122/E 1125）双端 isSuccess
2. WS 1123/1126 `/rssSourceDebug` tag=sourceUrl：RSS 入口列表 12 条 + 标题/时间/封面/链接全对 + 正文输出带 Referer 的 m3u8
3. HTML 分类/标签入口用书源 debug `::URL` 与 App eval_js 双验证 24 卡 + 字段可提取
4. 双端 `/getRssSources` 回读逐字段 diff=0
5. 站方无搜索 RSS（`rss/?q=` 返回同样 12 条）⇒ 搜索留空，走配套视频书源


## 六、书源分组标题点击展开/收回 + 订阅源登录切换分类模式（Jable 261124 追加）

### 6.1 书源 exploreUrl 改 @js 动态折叠
- 分组标题 = `{title:'▼/▶ 组名', url:'', type:'button', action:'翻转 source.getVariable() 状态键 + java.refreshExplore()', style:{layout_wrapBefore:true}}`
- 子项按 `cfg[key]===undefined?默认:(cfg[key]!==0)` 决定是否 push；默认榜单/主题展开、标签/女优收起（19 项起步，全展开 194 项）
- 真机 eval_js 实测：点标签条 → `jOpenTag=1` → 标题变 ▼ → 项数 15→130；qjs 三态（全默认/全展开/全收起）编译+输出条数全对
- ★已知代价：**check_source 对 @js exploreUrl 误报「发现失效」**（校验器裸环境无 source binding），但真机 eval_js + debug 全链路正常——这是机制限制不是书源缺陷；若用户强依赖 check 绿，需退回静态 exploreUrl（放弃折叠）

### 6.2 订阅源登录面板切换「热门标签 / 按女优」
- sortUrl 改 `@js:` 脚本（LT 源码 `help/source/RssSourceExtensions.kt` 实锤支持 @js，`getSortUrlsKey=MD5(sourceUrl+sortUrl)`）
- 脚本读 `source.getVariable().jbSortMode`（tags|models）决定渲染 115 标签还是 60 女优，榜单+12 主题恒定
- ★★突破 sortUrl 的 ACache 缓存：登录 action 里写变量后 **同时 `source.setSortUrl(原文本.split(' //mode=')[0]+' //mode='+mode+'-'+Date.now())`**——sortUrl 文本变 → 缓存 key 变 → 下次 sortUrls() 重新 eval 脚本读新变量。`java.refreshExplore()` 重绘（源码 SourceLoginJsExtensions.refreshExplore 存在）
- loginUi 插入 3 行（切换标签/切换女优/当前模式动态 label），全 Toast
- 验证：两模式 qjs 模拟 130 行(115标签)/76 行(60女优) 正确；WS 1123/1126 默认模式回归列表 12 + m3u8 全绿；双端回读 diff=0
- ⚠️`//mode=...` 注释追加在 `@js:` 脚本末尾是合法 JS 注释，不影响解析；书源/订阅源共享 sourceVariable 缓存键，线路一处切换全联动
