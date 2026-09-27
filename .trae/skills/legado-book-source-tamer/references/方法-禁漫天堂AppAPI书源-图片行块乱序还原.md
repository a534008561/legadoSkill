# 方法-禁漫天堂 App API 书源与图片行块乱序还原（jasmine 机制）

> 蓝本：🔞禁漫天堂API 书源（bookSourceUrl=`https://www.cdngwc.cc##禁漫API`，2026-09-27 重置，check_source 1/1）。
> 参考开源：ComicSparks/jasmine（模块 jasmine.js + Rust `rearrange_image_rows`）、hect0x7/JMComic-Crawler-Python（JmCryptoTool/JmImageTool/JmApiClient）。
> 成品与构建脚本：/workspace/jmapi/（build.py + jmapi_final.json + README.md）。

## 1. 为什么走 App API：网页通道被"白盾"双杀
禁漫网页系（18comic.vip 系 发布页 jmcomicui.net）260926 对移动家宽全量返回 978B JS 挑战页（idss/*.js），正文图床 cdn-msp*.comic18j-hbd.space 虽然豁免但页面链已断（详情/搜索页被盾+ISP 404）。而 App API 用的是**另一套 CDN 域名体系**（cdngwc/cdnhjk 系），完全不受白盾影响——jasmine 的"全部走 API"思路是当前唯一稳路。

## 2. API 明文协议（全部真机实测）
### 2.1 域名（两线）
- API：`www.cdngwc.cc`(线1) `www.cdnhjk.net`(2) `www.cdngwc.net`(3) `www.cdngwc.club`(4) 备用 `www.cdnutc.me`(5,DNS污染)。jasmine 旧默认 `www.cdnplaystation6.vip` **已无 DNS 记录（域名已死）**——参考旧项目必须把"域名"当活数据。
- 图床：`cdn-msp.jmapiproxy1.cc` / `cdn-msp.jmapiproxy2.cc` / `cdn-msp2.jmapiproxy2.cc` / `cdn-msp.jmapinodeudzn.net`。
- **域名自动获取**：BytePlus `https://rup4a04-c02.tos-cn-hongkong.bytepluses.com/newsvr-2025.txt`（c01 新加坡被 RST、c03 北京备）→ 去首非 ASCII → AES-256-ECB 解密，`key=md5(''+'diosfjckwpqpdfjkvnqQjsik')`（API_DOMAIN_SERVER_SECRET，md5 hex 字符串=32 字节），明文 `{"Server":[域名...],"jm3_Server":[[域名,线路名]...]}`。Ts 传空串（`md5(''+secret)`）。

### 2.2 请求头（缺一 401）
```
token       = md5hex(ts + '185Hcomic3PAPP7R')     // APP_TOKEN_SECRET（另有 18comicAPPContent 为 /chapter_view_template 专用）
tokenparam  = '{ts},2.1.7'                        // APP_VERSION
user-agent  = Mozilla/5.0 (Linux; Android 13; {9位hex设备号} Build/...; wv) AppleWebKit/...
X-Requested-With: com.JMComic3.app
```
**ts 无时间窗校验**：3 天前固定 ts 实测 200 且可解（服务端只看 token 做 MD5 存在性不绑时间）。书源策略=变量半固定 ts + 401 自愈换新。初始化 Cookie：GET /setting（OkHttp enabledCookieJar=true 自动持久化）。

### 2.3 响应解密
`{"code":200,"data":"<base64 AES-256-ECB 密文>"}`；`key=md5hex(ts+'185Hcomic3PAPP7R')`（32 字节 hex 字符串 UTF-8）；`AES/ECB/PKCS5Padding`。Legado 侧：`java.aesBase64DecodeToString(data, key, 'AES/ECB/PKCS5Padding', '')` 一次到位。**解密 ts 必须与请求 cc 头 tokenparam 的 ts 一致**——最稳的架构是"规则 JS 自建请求"（见 §4）。

### 2.4 接口与字段
| 用途 | 路径 | 关键字段 |
|---|---|---|
| 搜索 | `/search?search_query=&main_tag=0&page=&o=mr&t=a` | `{total, content:[{id,name,author,image,category{title},...}], redirect_aid(直搜车号)}` |
| 详情 | `/album?id=` | `{id, name, author[], tags[], description, series[{id,name}], series_id, total_views, likes, comment_total, is_favorite, liked, addtime}` |
| 章节 | `/chapter?id=` | `{id, images:['00001.webp',...], tags(空格串), name}` |
| 分类流 | `/categories/filter?page=&order=&c={slug}&o={mr\|mv\|mp\|tf\|mv_t\|mv_w\|mv_m}` | 同搜索 SearchPage |
| 收藏夹 | `/favorite?page=&folder_id=0&o=mr` | `{list:[...], folder_list, total, count}` |
| 登录 | POST `/login` body `username=&password=` | 解密后 `{uid,username,coin,s,...}`；错误凭据 HTTP 401 |
| 收藏切换 | POST `/favorite` body `aid=` | toggle 逻辑 |
| 分类 | `/categories` | `{categories:[{id,name,slug,sub_categories}]}` |

单话本：album 的 `series=[]` 且 chapter id == album id（`is_single_album`）。多话本 series 数组直接就是全量目录（无分页）。

### 2.5 图片与封面
- 图：`https://{图床}/media/photos/{photo_id}/{img_name}?v={ts}`（2023-07 起不带 v 参数返回空数据；v 值本章固定即可）。
- 封面：`https://{图床}/media/albums/{aid}_3x4.jpg?v=1`。**无 UA 请求被拒（9B/空页）**→ 封面走 Glide 无书源 header，必须带 URL 选项：`...,{"headers":"{\"user-agent\":\"...\"}"}`（本版 okHttpStreamFetcher 的 AnalyzeUrl.getGlideUrl 支持；正文 img 因 MangaVH 设了 sourceOriginOption 会自动带书源 header，无需选项）。

## 3. 图片行块乱序还原（imageDecode）
算法（jasmine Rust 与 jmcomic-python 完全一致）：
```
aid = photo_id(章节id); fn = 图片文件名(无扩展, 如 00001)
if aid < 220980: rows=0(原图)
elif aid < 268850: rows=10
else:
  x = 10 if aid < 421926 else 8
  rows = (ord(md5hex(str(aid)+str(fn))[-1]) % x) * 2 + 2      # 取末字符 ASCII 码
rows<=1 → 不处理；gif → 不处理（Bitmap 会丢帧）
还原 = 把图片按高均分 rows 块（首块含 remainder），整块**倒序**：src_start_y=height-move*(i+1)-over → dst y 递增
```
Legado 落地：`ruleContent.imageDecode`（绑定 result=byte[]、src=URL、java/source；`BaseSource.evalJS` 自动带 jsLib 的 SharedJsScope → jsLib 函数可直接用）。用 Android 原生：`BitmapFactory.decodeByteArray` → `Canvas.drawBitmap(srcRect→dstRect)` 逐块拷贝（循环 ≤20 次，光栅化在 C++）→ `compress(PNG,100)` → `toByteArray()`。实测 1280x1790 webp 197KB：解码+重排+PNG 压缩共 ~1.7s，2.7MB。图片 URL 没有 `,{headers}` 选项时 decode 前 imgPattern 会吞属性——这里无碍见 §2.5。

**校验纪律**：md5 末字符取的是 **ASCII 码**（'9'=57 不是 9）；受 JS 环境 `%` 语义一致；rows 跨 Python/QuickJS/Rhino 三方复算必须一致（本轮 441923/00001 → rows=6 三端相同）。

## 4. Legado 书源架构四板斧
1. **规则内自建请求**：搜索/详情/目录/正文的 @js 规则统一走 jsLib `jmget(java,source,path)`（自生成 ts→带 token 头→解密→JSON.parse，401 换 ts 重试）。**根因**：解密的 ts 必须与请求 ts 绑定，依赖"header 生成 token 的 ts"会出现跨并发实例不一致导致 `SyntaxError: Unexpected token`（本轮 debug 实测踩中）——header 只负责让 Legado 主请求 200（check_source 友好），解析全走自建。
2. **列表协议**：bookList/chapterList 返回**JSON 字符串数组**（逐条 `String(JSON.stringify({...}))`），字段规则 `$.name` 纯键名 JSONPath（E/LT 双版通用）。
3. **kind 芯片**：`ruleBookInfo.kind` 用逗号分隔标签（点击=本源搜索该标签，官方原生能力）。
4. **线路按钮面板**：登录界面每线路一个按钮，点击=切换变量 + 测延迟 + longToast 结果。API 测速用 `GET /setting`（自建函数），图床测速用拉真实封面判 body>800B；测速函数与被测通道必须同构（self-contained）。

## 5. 踩坑清单（K1~K10）
- K1 参考旧项目的 API 域名必先实测存活（jasmine 默认主机已死，用 newsvr 解密获取现行域名池）。
- K2 无 token → 401；`java.post` 对 401 抛 HttpStatusException（catch 后转 toast）。
- K3 header 的 `<js>` 求值环境没有 jsLib（BaseSource.getHeaderMap 独立 evalJS），自依赖常量须内联。
- K4 jsLib 顶层函数**不能闭包读全局 source**（显式传参 jmget(java,source,...)）。
- K5 `bookSourceUrl` 域名与图床跨域：登录头同源保护（isLoginHeaderSite），跨域图床靠封面 URL 选项 headers。
- K6 `searchUrl` 静态主域名即可——解析不走它；发现页 URL 的 `{{page}}` 会被替换。
- K7 imageDecode 顶层不可 `return`（非函数体），用 IIFE 包裹。
- K8 Java 字符串返回必须 `String()` 包裹后再 `.length/.charCodeAt`（java.lang.String 无 .length 属性）。
- K9 `exploreUrl` URL 不能匹配 bookUrlPattern（否则发现条目被当详情解析）。
- K10 ts 是全局变量时并发会错位——本架构 ts 在 jmget 内每次自控，天然免疫（header 半固定 ts 仅用于主请求保 200）。

## 6. 验证方法论
- 真机探针（eval_js/空白源）：域名 DNS 探测 → /setting 带 4 头 → AES 解密比对明文 → album/chapter/search 全接口。
- 行重排算法：Python 端算 rows → App 端 jmnum 复算 → 三方一致才上线。
- imageDecode 模拟：jsoup 取 bytes → eval(规则IIFE) → 校验 PNG 魔数(137,80,78,71) + 耗时。
- `debug_source` 关键字/`::URL` 覆盖搜索与发现模板、单话与多话本。
- `check_source` 官方校验必须 1/1；checkKeyWord 选结果非空的词（MANA）。
## 7. 跨版本（legado-team / legado-E）兼容要点（260927 实测）
- ★**E 版(Luoyacheng/legado-E) `java.get/post/head` 第三参是 `Map<String,String>`**（LT 版是 JSON String），返回 jsoup `Connection.Response`；带自定义头的 GET 两版共同通道 = **`java.connect(url, headerJson)` → StrResponse**；POST 用双派发（先 String 版、catch 后 HashMap 版）。
- E 版 `source.put/get(key)` 存在（`CacheManager.put("v_{key}_{k}")` 返回 String）；header 支持 `<js>`；imageDecode/coverDecodeJs 原文 evalJS（禁 @js: 前缀两版同）；DecompressInterceptor 两版同构（书源 header 禁手写 Accept-Encoding 两版同）。
- E 版 useweb 桥 `WebJsExtensions.post(url, body, header:String)` 与 LT 同签名，收藏类按钮可双用。
- 症状对照：E 版「测速失败 6ms」= 找不到方法（签名不匹配），不是网络问题。
