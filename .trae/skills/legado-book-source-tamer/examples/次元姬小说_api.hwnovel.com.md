# 💰 次元姬小说 https://api.hwnovel.com 书源

状态：✅ 完成，check_source 通过 1/1，debug_source 全链路实测通过（搜索→详情→目录→正文→发现）。
兼容：LegadoTeam 官方版（实测）+ Luoyacheng/legado-E（按 E 版列表协议编写 try/catch 兼容）。

## 一、站点档案

- 站点：次元姬小说（浙江火文科技），正版二次元小说站，官方 API。
- API 基址：`https://api.hwnovel.com/api/ciyuanji/client`
- Web 版：`https://api.hwnovel.com/app-fiction/`（Next.js，仅活动/签到，无阅读接口）
- 图床：`img.ciyuanji.com`（明文，直连）
- 无需登录可搜索/阅读（游客态）；登录=手机号+短信验证码；VIP 章节需登录+购买（书币）。
- 无 UA 校验不可（要 4 个客户端头）；**设备号 deviceno 有服务端设备库风控**（见下）。

## 二、接口协议（全部实测）

```
参数体(密文前)：JSON 对象（任意业务参数）+ timestamp(数字毫秒, 必须数字!)
param    = DES-ECB / PKCS5Padding / key="ZUreQN0E" 加密整个参数 JSON 的 base64
requestId= UUID 去横线
sign     = MD5( base64( "param=<param>&requestId=<rid>&timestamp=<ts>&key=NpkTYvp...nTo18" ) ).大写
GET 形态：?timestamp=..&requestId=..&sign=..&param=<urlencoded>
POST 形态：body {"param":..,"requestId":..,"sign":..,"timestamp":..}
```

- 必带请求头（缺一即 400/500）：`version: 3.4.8`、`platform: 1`、`channel: 100`、`deviceno: <16位hex>`（+ UA）。
- **签名无时间窗校验、无重放防护**：过期 30 天的签名 URL 依然 200 → bookUrl/tocUrl/chapterUrl 可直接嵌"永久签名 URL"，书架长期有效。

## 三、接口清单（实测字段路径）

| 功能 | 接口 | 关键 JSONPath |
|---|---|---|
| 搜索 | GET /book/searchBookList {keyword,pageNo,pageSize,rankType:'0'} | `$.data.esBookList[*]` |
| 详情 | GET /book/getBookDetail {bookId} | `$.data.book` |
| 目录 | GET /chapter/getChapterListByBookId {sortType:'1',pageNo:'1',pageSize:'9999',bookId} | `$.data.bookChapter.chapterList[*]`（顶层 bookId 不在每章里!） |
| 正文 | GET /chapter/getChapterContent {bookId,chapterId} | `$.data.chapter.content`(DES密文base64) `imgList[{imgUrl,paragraphIndex}]` |
| 榜单 | GET /book/getBookListByParams {pageNo,pageSize,rankType:1人气/2订阅/3更新/4上架/6新书,bookType:'1'男/'4'女,firstClassify,secondClassify} | `$.data.bookList[*]` |
| 标签书单 | GET /book/getBookListByTagId {tagId,rankType,pageNo,pageSize,bookType} | `$.data.list[*]` |
| 分类树 | GET /classify/getBookClassifyListByParams {classifyId:'0',pageNo,pageSize,bookType} | `$.data.classifyList[*]`（childList 子分类） |
| 标签 | GET /tag/getAppTagList {pageNo,pageSize,bookType} | `$.data.list[*]` |
| 登录态 | GET /user/getUserInfo | code==200 且 data.cmUser.nickName 非空 |
| 书架 | GET /bookrack/getUserBookRackList {pageNo:1,pageSize:9999,rankType:'1'} | `$.data.bookRackList[*]` |
| 发验证码 | POST /login/getPhoneCode {phone,smsType:'1'} | code |
| 登录 | POST /login/phone {phone,phoneCode} | `$.data.userInfo.token` |
| 签到 | POST /sign/sign {} | code=200/410(今日已签到) |
| 购买章节 | POST /order/consume {viewType:'2',consumeType:'1',bookId,productId(chapterId),buyCount:'1'} | code |

- 游离说明：正文 code=200 免费/已购；code=101 = VIP 未购买（content 仍是预览 ~200 字，可解密）；目录每章 isFee/isBuy 可做 VIP/已购标志。
- 搜索列表字段富集（bookName/authorName/imgUrl/notes/tagName/endState/isFee/wordCount/latestChapterName/latestUpdateTime/bookType），无需再查详情。

## 四、本次书源要点

1. **jsLib `_cy`**：kd/kq(签名query)/gu(拼URL)/po(POST body)/de(DES解密)/pl(统一列表解析器,通吃 esBookList/bookList/list/bookRackList)。函数全部显式传参（不带隐式依赖，规避 jsLib 作用域闭包坑）。
2. **列表=E 版协议**：`@js` 返回值保持 JS 数组、条目为 `String(JSON.stringify({...}))`、字段规则纯 `$.键`（kind/wordCount/lastChapter/bookUrl 等全部在 JS 里预组装，规避 AnalyzeByJSoup 污染与复杂模板）。★所有 @js 规则必须带前缀（@js:/<js>），漏前缀会被当 CSS 解析报 SelectorParseException。
3. **规则全 JS**：searchUrl=<js>(变量 key/page 直接可用)；ruleBookInfo.init 解析详情并预生成签名 tocUrl（放 ruleBookInfo.tocUrl——TocRule 无此字段会被反序列化丢弃）；toc 用顶层 bookId（chapter 对象无 bookId 字段）；正文 @js DES 解密+插图插入(img 双引号)+code 101 追加付费引导；payAction 解密自己 chapter.url 的 param 拿 bookId/chapterId 再下单。
4. **登录**：V1 面板（手机号/验证码/发码/登录/检查登录状态/退出/设备号/应用设备号），login() 空验证码自动转发送；token 走 `source.putLoginHeader({"token":..})`。
5. **VIP 未购提示**：正文尾部固定文案引导「购买本章」，购买成功 Toast「重新进入本章即可阅读全文」（目录 isBuy 需刷新后才变）。
6. **loginCheckJs**：拦截 JSON 短响应中的 非法请求/必须参数为空/网络繁忙 → 抛中文错误；原样 return result。

## 五、搜索间隔 / 风控

- 未观测到明确的搜索间隔限制（连续搜索十余次无拒绝），仍设 `concurrentRate=1/1500` 保守限速。
- **根因确认的「网络繁忙」= 设备号风控**（见第六节）。同日多请求通过 loginCheckJs 直接中文提示。

## 六、★★本站独家难点：设备号风控

- 现象：同 IP 同时段，老设备号 e348231e3f7dbe58 搜索 200，任何新 16hex（随机值/本机 androidId/有序串）都返回 `{"code":"400","msg":"网络繁忙"}` 或 403；缺 deviceno → 500。改变 version/channel/weskit 等附加头无效。
- 判定方法：同一时刻双设备号对照实验（排除限频因素）；全新随机号仍被拒 → 服务端维护设备库/激活白名单。
- 对策：① 书源 header 用 `@js` 动态生成，默认固定已验证可用的设备号；② 登录面板提供「设备号」输入框把用户自备号写入 `source.put('cydn',..)`，header 运行时读取覆盖（16 位才生效）；③ loginCheckJs 把「网络繁忙」翻成中文提示，书源注释与 README 说明自救路径。

## 七、验证记录（2026-09-25，LegadoTeam 版真机）

- eval_js 逐接口探测：search/detail/toc/content(免费+VIP101)/classify男+女/tag/taglist/rank/rack/userinfo 全 200。
- debug_source key=妹妹：20 结果全字段 → 详情 → 目录 29 → 正文解密完整。
- debug_source ::发现页：rank3 30 条 → 第二本书详情 → 目录 510 章全（大目录 OK）→ 正文。
- 登录面板三函数 cySend/cyCheck/cyDn 在 App 真机执行通过（toast 正常）。
- check_source 官方校验 1/1 通过。
- 待用户真机确认：legado-E 版实测、短信登录、签到、购买 VIP。

## 八、发现页排布（终稿：自动流式布局）

★★源码实锤：Legado 发现页 FlexboxLayout 带 `showDivider="middle"` 间隔线+条目 3dp margin/12dp padding，**固定 layout_flexBasisPercent 列数必然溢出 wrap**（0.5+0.5→竖排一列、0.33×3→两列）。唯一稳解：
- 入口条目 style=`{'layout_flexGrow':1}`（无 basis）→ 按内容宽度自动流式排布，一行放得下几个就几个；
- 分区标题行 style=`{'layout_flexBasisPercent':1}` + url 空（不可点整行）；
- 条目标题纯文字（emoji 撑大最小内容宽会 wrap 成一列），emoji 只放分区标题行（🏆📂🏷👤）。

页面顺序：
1. 👤 个人 · 中心 → 我的书架(GET第一·check_source 首检安全) / 每日签到(POST第二·结果经 loginCheckJs toast ✅成功/☑️已签到)
2. 🏆 男生 · 排行（4 个）
3. 📂 男生 · 分类（大类+子类，无前缀符号）
4. 🏷 精选 · 标签（前 30 热门）
5. 🏆 女生 · 排行
6. 📂 女生 · 分类
- kind 芯片限前 3 标签+状态+付费；字数 wc() 格式化为「x.x万字」；分类树/标签 30 分钟缓存(source.put('cy_cls'))。

## 九、文件

- ciyuanji.json / ciyuanji_one.json — 成品书源（App 内已存同源版本）
- build.py — 构建器（node --check 全 JS 块 + 内联自检）
- 旧版参考：yckceo 源仓库 2023 版（DES 密钥与签名串一致，端点一致）