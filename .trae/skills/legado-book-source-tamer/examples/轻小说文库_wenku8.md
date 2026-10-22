# 轻小说文库 wenku8 书源案例

## 概览

- 站点：https://www.wenku8.net（备用 wenku8.cc / wenku8.com，jieqiCMS 体系）
- 数据源：web 页面（`/modules/article/`），**非 App 加密 API**
- 成品：`/workspace/wenku8/build/wenku8.json`（15.6KB），check_source 1/1，全链路 debug 通过
- 免登录：详情 / 目录 / 正文
- 需登录：搜索 / 榜单 / 文库分类 / 标签 / 书架（匿名访问返回"用户登录"整页，caption=用户登录 且 无 373 卡片）

## 接口清单（全部 GET）

| 功能 | URL | 认证 |
|---|---|---|
| 搜索 | `/modules/article/search.php?searchtype=articlename&searchkey={GBK编码}&page={page}&charset=gbk` | 登录 |
| 榜单 | `/modules/article/toplist.php?sort={s}&page={page}&charset=gbk`（sort: allvisit/monthvisit/weekvisit/dayvisit/allvote/monthvote/weekvote/dayvote/goodnum/size/postdate/lastupdate/anime） | 登录 |
| 文库分类 | `/modules/article/articlelist.php?class={1-14}&page={page}&charset=gbk`（1电击...13其他文库 14游戏剧本；另有 `fullflag=1` 完结、`initial=A` 首字母） | 登录 |
| 标签 | `/modules/article/tags.php?t={GBK编码标签}&v={ALL/1/2/3}&page={page}&charset=gbk`（v: ALL按更新/1按热门/2已完结/3动画化） | 登录 |
| 详情 | `/modules/article/articleinfo.php?id={aid}` 或 `/book/{aid}.htm` | 匿名✅（侧栏自带登录框，勿误判为拦截页） |
| 目录 | `/modules/article/reader.php?aid={aid}`（td.vcss=卷 td.ccss=章节） | 匿名✅ |
| 正文 | `/modules/article/reader.php?aid={aid}&cid={cid}` | 匿名✅ |
| 封面/插图 | `http://img.wenku8.com/image/{aid首位}/{aid}/{aid}s.jpg`；插图 `pic.777743.xyz`（兜底 `pic.wenku8.com`） | 匿名✅ |
| 登录 | POST `/login.php?do=submit` body=`username=&password=&usecookie=315360000&action=login&submit=%20%B5%C7%20%C2%BC%20`（GBK），成功 Set-Cookie `jieqiUserInfo`/`jieqiVisitInfo` | — |

## 关键技术点

1. **GBK 编码链**：关键词用 `java.encodeURI(key,"GBK")`；URL 选项 `{"charset":"GBK"}` 同时负责请求参数编码与响应解码（AnalyzeUrl 源码实锤，两处共用同一 charset）。
2. **登录统一走 `java.connect(url+',{...,"method":"POST","charset":"GBK","body":"..."}')`**：走 OkHttp+CookieJar 自动收会话 Cookie；`java.post` 走 jsoup **不带 CookieJar**（只置 cookieJarHeader），登录后取不到 jieqiUserInfo。
3. **正文净化**：`<ul id="contentdp">` 水印在正文开头（不能 split[0] 截取，必须 join('') 移除）；录入组信息（台版/图源/扫图/录入/修图，短行）逐行过滤；`&#12539;` → `·`。
4. **插图章**：`div.divimage > a > img`，输出 `<img src=...>` 每行一张（img 标签必须双引号）。
5. **列表卡片**：`div[style="width:373px;height:136px;float:left;margin:5px 0px 5px 5px;"]` 统一五模板（搜索/榜单/分类/标签/完结），正则提取 aid/title/cover/作者/分类/更新/字数/状态/Tags/简介；"已动画化" hottext 在状态位需修正为"连载中"。
6. **详情页版权下架书**（如 aid=1305）：正文返回"因版权问题"，详情 intro 追加提示；目录/正文规则需容错。
7. **checkKeyWord 选"隔壁"**：8 条结果全部可读；勿用会命中版权书的词。
8. **exploreUrl 必须静态 JSON 数组**：`<js>` 动态生成在 check_source 裸环境报"发现规则为空"（rrssk 经验重现）；分组标题行 `{"title":"...","url":""}` 不可点。

## 调试插曲（本轮真实踩坑）

- **沙盒与 App 的认证矩阵不同**：沙盒 python 先后两次对同一 URL 得出不同结论（第一次匿名成功是因为碰了登录会话残留？实为先后顺序误会），最终以 App 内 debug_source + eval_js 登录为准：搜索/榜单/分类/标签确实需登录，详情/目录/正文匿名可用。
- **手抄大 JSON 必坏**：两次 MalformedJsonException（ Unterminated string/object），切 uguu.se 上传+深链导入后一次成功，回读字节级一致。
- **App 登录验证方法**：`eval_js` 绑定书源 → 复现 login() 逻辑 → `cookie.getCookie('https://www.wenku8.net')` 含 `jieqiUserInfo` 且 body 无 frmlogin 即成功；随后 debug_source 搜索立即恢复。
- **check_source 的"发现规则为空"**：`<js>` exploreUrl 在校验器环境无 jsLib/变量上下文 → 静态 JSON 数组修复。

## 用户实测步骤

1. 书源管理 → 网络/本地导入成品 JSON。
2. 菜单 → 登录 → 填账号密码 → 点【1.登录账号】（Toast"登录成功"），点【2.检查登录状态】核对。
3. 未登录可用：详情/目录/正文（从发现页外链或搜索前先登录）。
4. 登录后：搜索、发现页全部入口（榜单/分类/标签/完结）。
