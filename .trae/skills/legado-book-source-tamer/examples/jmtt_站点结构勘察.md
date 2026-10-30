# jmtt1.net（禁漫天堂 18mh.net）站点结构勘察（2026-10-31）

## 发布页 jmtt1.net
- 静态发布页，线路 JS 动态生成 `<随机单词>.yyc2mhawcc` 泛子域线路（306 词表）
- ping 探活：`/favicon.ico`（站点首页 + /comic /mv /novel 四个分类入口路径）
- 分类导航 data-path：/（首页）/ /comic /mv /novel
- 备用线路页 `/index/backup`（主站内），暴露全部线路域名

## 主站（以 abandon.yyc2mhau.cc 为例，泛子域通配解析）
- **导航**：/ /comic /drama /novel /mv /comic/rank /comic/newest /index/backup
- **搜索**：`/{type}/all?key_word={kw}&page=N`（type=comic/novel/mv）— LD-JSON SearchAction 自曝
  - 漫画搜索："浪花里的双乳狂欢"→1 条命中；假词 → 0 条 ✓
  - 小说搜索：真词 12 条；视频真词 20 条；假词 0 条 ✓
- **列表卡片**：`li.jm-card`；封面 `a.jm-card__cover img[data-src|src]`；标题 `h3.jm-card__title a`；分类 `div.jm-card__cat a`（两个 a：大分类|标签）；状态 badge `span.jm-card__badge--status`（连载中/已完结）
- **详情页**：`/{type}/detail/{id}`
  - LD-JSON `ComicStory`：name/author(genre)/image/keywords/description
  - 章节面板 `div.jm-dt-panel[data-jm-dt-panel="chap"]` 内 `a.jm-dt-ch`（comic: `第N话 标题`，novel: `第N章 标题`，含 data-chapter-no）
  - 漫画：`/comic/chapter/{id}/{seq}`；小说：`novel_chapter/{id}/{n}.html`（下划线！）
  - meta: og:title/og:description/og:image（封面）→ 但小说封面 og:image 可能缺
  - 评分/喜欢/观看数在 jm-dt-stars/jm-dt-score
  - 作者锚点：`/comic/all/author/{name}` 链接
- **阅读页**：
  - 漫画 `section.jm-rd-pages img[data-src]`（loading.svg 占位 data-src 真图）
  - 小说 `.article.jm-rd-text p` 段落直出
  - 下一章链接出现 2 处（底部导航 + 推荐区）→ nextContentUrl 候选
  - 小说 data-unlock-score="300000" data-unlocked="[]"（存在付费解锁字段！待验证是否影响正文完整性）
  - data-logged="0" 游客可读性待真机确认
- **视频详情**：`/mv/detail/{id}` → embed 页 `/mv/embed?id={id}` → document.write `/videos/detail_embed.js?img=...&u=...&t=1800s窗口`
  - detail_embed.js 再 document.write `<video><source src="/media/3.m3u8?url={encodeURI(m3u8真链)}&token={md5}&exp=2F3D0|26via_bm=0&via=j三层签名参数
  - 真链=图床 m3u8 带 auth_key（时效签名）
三层签名链：详情页 → embed(1800s窗口 t) → media proxy(接 auth_key m3u8) → 图床分片
- **图床**：`xi.dz漫画域名可用图床域名列表：xi.dzuxta.cn（主图床）
- auth_key={expire}-0-0-{md5}（时效签名，expire=1793396395 ≈ 2026-10-31+）签名有效期长（约数日）
auth_key 过期图片 403；书源不做图片签名续签（按图床返回 403 时用户重进章节即可）
- **线路域名池**（/index/backup 页 + 泛子域词表 306 词）：
  abandon.yyc2mhau.cc（已验证可用）+ /index/default 备用线路 24 个域名
  泛子域词表 306 个词 → 306 候选线路（全部同后端，任一可用即可用全部）
  jmtt1.net（发布页）+ 18mh.net（主域，App 网络下 DNS 污染）
  18mh.01buliangrukou.com, 18mh.01anyeruko.com（01buliang 系列）
  ac59.gjiiuhafg.cc, 8qxwm.cu3li.cc, 8hymt.npb6frvj.cc, 16d7x.tad6kbrr.cc, 0f8.clacdzqy.cc, w9xfv.yyc2mhau.cc
  xryon.d4qx9eb9cn.cc, a7k9x.bvueg3-t1t1.icu, th8nn.oijdnd.com
  fqtu048.com:5027, t1t1.com, 29y.top, hw2.top, mtdjgw.com, mossavdhtop003.icu
- **搜索频率**：站点无明示限频，谨慎 1500ms 间隔 concurrentRate=1500
- **登录**：登录表单在首页（username/password）→ 无需登录可读正文（小说正文直出测试通过）
游客模式完全可用（data-logged=0 时小说正文直出验证通过）⇒ 无需登录即可完整使用书源
- **广告图片域名**：icv5wlc.cn / cloudfront.net / dzq66.m8cu3.top / otrzotu.cn / fqtu048.com:5027
- **18acgs.cc = APP 下载站（无关）**

## 视频播放链路（细节）
- 详情页 → embed 页：`/mv/embed?id={id}`（Referer 无硬性要求，25s 才响应——慢）
embed 页是 document.write 拼接：
`/videos/detail_embed.js?img={封面URL（auth_key签名）}&u={RSA/MD5签名}&t={unix/1800}`（u 参数名疑似 "u"）
- detail_embed.js 内容 = 又一层 document.write：
`<video><source src="/media/3.m3u8?...">` 与 `<noscript>` 夙
- `/media/3.m3 60s 諮询超时——**书源侧不依赖它**（用户手机网络可能不同，保留 startBrowser 方案）
- **书源视频模式方案**：正文 = `<img data-src="...">
` 不行——ExoPlayer 不支持 HLS+三层签名链，需要 startBrowser 打开 embed 页
- **视频正文方案 A（startBrowser）**：bookUrl=详情页URL；正文=「▶ 在内置浏览器播放」提示行 + startBrowser 到 embed 页
- **视频正文方案 B（data:base64 沉浸播放页）**：正文输出 data:text/html;base64 页（video 标签+三签名 m3u8直链）+ java.startBrowser(embedUrl)
方案 B 需要书源侧复算 embed→media 代理签名（u 参数可能是服务端 session 绦定
u 签名可能绑定 IP/session，沙盒可用但用户手机未必可用——**A 方案（startBrowser 到 embed 页）最稳**，embed 页自带 hls.js 播放器+签名自动刷新，签名过期自动重访详情页→embed→新签名（浏览器自然链路）签名自愈
方案 A 的实现：详情页 intro=<usehtml> + <button @onclick:java.startBrowser('{embed}')>，但 embed URL 需要从详情页实时解析（防签名过期）
- 视频 bookUrlPattern 不设（书架归属判断用 bookSourceType=4 时按 bookUrl 均可

## 模式变量机制（X夜社范式）
- source.put("jmMode", "漫画"/"小说"/三模式
source.put("jmMode", "漫画") → exploreUrl/searchUrl/ruleToc.chapterList/ruleContent 按 mode 分支
- book.type 位掩码：漫画=64(image)、小说=8(text)、视频=4(video)
book.type 在 ruleToc.chapterList 里动态设置（removeAllBookType 会冲掉 init 设置）
X夜社范式：chapterList 的 @js 里 book.setType(N)（E版 set
E 版 book.setType(N) 存在（E 版 Book.kt 有 setType setter）——记忆实锤（E 版 API 存在性清单）
- 搜索/发现/详情/目录/正文五处 @js 均读 jmMode 分支
五处 @js 均读 jmMode 分支
- 登录面板按钮：三模式按钮 + 一键线路获取 + 逐线路测速 + 各线路切换按钮

## 泛子域词表（306 词，发布页 <script> 内 words='...' 揔取）
发布页 words='...' 揺取 → java.ajax(发布页)+regex 揺取  一键获取线路按钮
一键获取线路：java.ajax("https://jmtt words list → sample 6 条线路 + /index/backup 页域名池
一键获取线路 = 抓发布页词表 → 随机取样 N=6 → 并发测速 → 最快者写 jmHost
jmHost 存 source.put("jmHost", url)  → 所有规则 {{jmHost}} 悉引用
所有规则用 {{}} 栽{{}}模板引用 jmHost：
- searchUrl/exploreUrl 用 {{source.get('jmHost')}}（AnalyzeUrl 模板层 source.get 可用？）
AnalyzeUrl {{}} 樊板层可用的绑定 = source（BaseSource）⇒ {{source.get('jmHost')}} 可用
- 列表/详情/目录/正文 @js 端读 source.get('jmHost') 双通道归一化
- 未设置 jmHost 时默认 abandon.yyc2mhavcc → 默认 host = "https://abandon.yyc2mhau.cc" (`DEFAULT_HOST` 常量)
DEFAULT_HOST 帡量 = "https://ab typos fixed: yyc2mhau.cc 拼写统