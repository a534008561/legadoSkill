# 方法-App官方API书源与设备号风控（次元姬 api.hwnovel.com 全案）

> 适用场景：正版 App 的 JSON 后端做书源（次元姬/火文/热读等杭州热读系站点共用同一后端）。
> 蓝本：次元姬小说书源（2026-09-25 定稿，check_source 1/1 ×N，搜索/详情/目录/正文/发现(五轮排布迭代)全链路实测，兼容 LegadoTeam 官方版 + Luoyacheng/legado-E）。
> 本文档六章覆盖本单全部新难点，直接可复用于同类 **「设备号白名单 + 四件套加密签名 + 发现页排布」** 站点。

## 1. 站点与 API 真相

- 官网 `hwnovel.com` = 浙江火文科技，旗下「次元姬小说」「火文小说」等多 App 共用后端 `api.hwnovel.com`。
- 真正的 API 前缀：`https://api.hwnovel.com/api/ciyuanji/client`（2023 年旧书源同一族端点仍存活）。
- Web 版 `/app-fiction/` 是 Next.js 空壳（只有活动/签到页面），**没有阅读接口**，但它把 API baseURL、DES 密钥、MD5 密钥、默认公共参数 {deviceno…} 全部写在 `_next/static/chunks/*.js` 里——**想找密钥与已知设备号，直接挖 bundle**。

## 2. ★请求门禁：四件套加密签名（GET / POST 同构）

```
内层: 业务参数 JSON（对象内自动附 timestamp —— ★必须是数字）
param     = base64( DES-ECB / PKCS5Padding / key='ZUreQN0E'.encrypt(JSON字串) )
requestId = UUID 去横线
sign      = MD5( base64("param=<p>&requestId=<r>&timestamp=<t>&key=<88字符MD5KEY>") ).大写
外层 GET : ?timestamp=&requestId=&sign=&param=<urlencode(param)>
外层 POST: body {"param","requestId","sign","timestamp"}
```

- MD5KEY = `NpkTYvpvhJjEog8Y051gQDHmReY54z5t3F0zSd9QEFuxWGqfC8g8Y4GPuabq0KPdxArlji4dSnnHCARHnkqYBLu7iIw55ibTo18`
- **必带 4 个客户端头**：`version:3.4.8` `platform:1` `channel:100` `deviceno:<16hex>`（缺任一 → `500 服务器异常`；无签名 → `400 必须参数为空`）。UA 无硬校验但显式设置手机 UA。
- ★**签名无时间窗、无重放防护**：过期 30 天的签名 URL 照样 200 → **bookUrl/tocUrl/chapterUrl 直接嵌「永久签名 URL」**，书架/书签长期有效，不需要每次重签。
- JS 实现（书源 jsLib）：`new cn.hutool.crypto.symmetric.DES('ECB','PKCS5Padding',8字节key)`；`java.digestHex(java.base64Encode(str),'md5').toUpperCase()`。

## 3. ★★★全新难点：设备号风控（deviceno 服务端设备库）

| 实验（同 IP 同时段对照） | 结果 |
|---|---|
| `e348231e3f7dbe58`（站点 JS bundle 里挖出的已知号） | ✅ 200 一切正常 |
| 任意新 16hex（多个全新随机值 / 本机 androidId） | `{"code":"400","msg":"网络繁忙"}` |
| 有序号 `0123456789abcdef` | nginx 403（WAF 层） |
| 12 位短号码 | 「网络繁忙」 |
| **缺 deviceno 头** | `500 服务器异常` |
| 补 weskit/sign/oid/appVersion/statusBarHeight 等附加头 | 无效 |

判定方法论：★同 IP 同时段「好号 200 / 新号 400」对照，证明是**设备号维度**风控而非 IP 限频；改 channel/version 无效；`/login/anonymousLogin` 等激活接口尝试全部 404 → **没有离线激活通道**。

书源对策三件套：
1. `header` 写成 `@js:` 动态生成，默认内置「已验证可用」的共享设备号；
2. 登录面板加「设备号」文本框 +「应用设备号」按钮：`source.put('cydn',16hex)` → header 运行时代入（16 位才生效）→ 共享号被封时用户可自救；
3. `loginCheckJs` 检测短 JSON 里的「网络繁忙」`throw new Error('次元姬接口提示: …')`，书源注释写清自救路径。

## 4. ★逆向降级路径：GitHub 被墙时拆 crates.io 包

本机 GitHub 全 404/连接超时。找到活跃开源客户端 `novel-api`（Rust crate）后：
- 元数据：`GET https://crates.io/api/v1/crates/novel-api`（newest_version/repository）。
- **下载源码包**：`GET https://crates.io/api/v1/crates/novel-api/{ver}/download` → gzip.decompress → tarfile（crate 打包源码，无需 GitHub）。
- **版本考古**：0.20.x 已移除 ciyuanji 模块（大概率因风控升级被删），向下试 **0.19.2** = 含完整 ciyuanji 的最高版：`src/ciyuanji/{mod.rs,utils.rs,structure.rs}` = 全部端点 + 密钥 + 签名实现 + 响应结构体 + 每个参数注释（rankType 语义、bookType 1男4女、isFee/isBuy、chapterPreviewLen、图片 paragraphIndex…）。
- ★拿到实现后仍必须真机逐端点实测：Rust 结构体 serde 跳过未声明字段，实际响应字段更多。

## 5. ★VIP 章节 code=101 不是错误

- `getChapterContent` 返回 `code=200`（免费/已购）或 **`code=101 + msg '未开启自动购买开关'`**——但 data.chapter.content 仍下发密文，解密后是 **~200 字预览**（= 详情里的 `chapterPreviewLen:200`）。
- 正文规则：200/101 两个码都走解密；仅 code==101 时尾部追加购买引导文案；其他 code 才 throw。
- **payAction 参数复用技巧**：`chapter.url` 本身就是带签名 getChapterContent URL → regex 取 `param=` 段 → DES 解密 → 得 `{bookId,chapterId,timestamp}`（无需任何存储变量）→ POST `/order/consume {viewType:'2',consumeType:'1',bookId,productId:chapterId,buyCount:'1'}`。响应 `200`=成功 / `msg 含'暂无可购买章节'`=已购过 / 其他=toast 原样 msg。
- 目录的 `isFee/isBuy`（每章都有）→ ruleToc 的 isVip/isPay；正文响应没有 isBuy，别找。

## 6. ★★★发现页排布终极铁律（五轮用户反馈定稿，源码级实锤）

**病根**：Legado 发现页 FlexboxLayout（`item_find_book.xml`）使用 `app:showDivider="middle"`（条目间插间隔线）+ 条目 `item_fillet_text.xml` 自带 `3dp margin + 12dp×2 padding`。**任何固定 `layout_flexBasisPercent` 列数方案都会因「百分比之和 + divider + margin」溢出容器宽度而被 wrap**：
- `0.25` 四列：4 字标题只显示前 2 个字（卡片太窄必截断）；
- `0.5+0.5=1.0`：加 divider 后溢出 → **竖排一列**（惨案：无论 emoji 还是纯文字都一列）；
- `0.33×3=0.99` / `0.31×3=0.93`：都只有两列。

**唯一稳解 = 自动流式布局**：
```
所有入口条目 style = {'layout_flexGrow': 1}     // 无 basis
分区标题行   style = {'layout_flexBasisPercent': 1}  // 整行独占, url:''
```
flexbox 按内容宽自动 wrap，一行能放几个就放几个，宽度自动拉伸——**用户口头诉求"自动排布"即此案**。

配套规则：
1. **分区标题行（url:''）必须在它的条目之前**：用独立分区函数（ranksec/catsec）先 push 标题再循环 push 条目；第一版把「男/女标题」一次性插在中段的"标题后置 bug"是排布混乱主因。
2. ★**emoji 会撑大卡片最小内容宽**（"🔥人气最高" 在 0.5 下仍被 wrap 成一行一个）→ **入口卡片的 title 一律纯文字**，emoji 只允许出现在分区标题行（整行 W）与列表 kind 芯片里。
3. ★**check_source 校验器取 exploreKinds() 第一个非空 url 按书单解析** → 首位必须是「安全幂等 GET 且响应可解析出书单」；**POST 写操作（签到）永远放第二位**（个人中心组置顶时=书架 GET 第一/签到 POST 第二，游客书架实测也有书）。分区标题行 url='' 会被跳过，无碍。
4. ★**发现页签到的成功提示放 loginCheckJs**：入口点击后响应按书单解析必然空列表（"无反应"的根因）→ 在 loginCheckJs 里 `String(u).indexOf('/sign/sign')>-1` 时 JSON.parse 响应，`code==200→longToast('✅ 签到成功')` / `410→'☑️ 今日已签到'` / 其他→原样 msg。★StrResponse 的 url 与 body 一样是 Kotlin 属性=方法引用，必须 `var u=r.url; if(typeof u==='function'){u=u.call(r)}` 双通道调用，最后 **return r 原样**。
5. 分区标题用 emoji 图标（🏆📂🏷👤）美观；分类树/标签列表 30 分钟缓存 `source.put('cy_cls')`（有数据才写缓存）；子分类标题直接 classifyName 不加前缀符号。

## 7. 列表与详情规则要点（E 版兼容铁律重演）

- 列表 @js 返回 **JS 数组，条目 `String(JSON.stringify({...}))`**，字段规则纯 `$.键`（LT/E 双版通吃）；所有派生字段（kind/wordCount/lastChapter/bookUrl 等）在 JS 里预组装，绕开 AnalyzeByJSoup 状态污染与复杂模板。
- ★@js 规则必须带 `@js:` / `<js>` 前缀（漏前缀 → jsoup `SelectorParseException`）；jsLib 顶层 `var _cy=(function(){...})()` 在 searchUrl/规则/loginUrl 内均可见（共享作用域）。
- searchUrl=`<js>` 上下文有 key/page 变量（typeof 兜底）。
- `ruleBookInfo.tocUrl` 是 tocUrl 唯一合法位置（TocRule 无此字段会被反序列化丢弃）。
- ★目录响应 `chapterList[].chapterId` 有、**bookId 只在顶层 bookChapter** → 正文 URL 必须取顶层 bookId（第一版误用每章 bookId=undefined）。
- 统一列表解析器 pl() 一个函数吃四种容器：`data.esBookList||data.bookList||data.list||data.bookRackList`（搜索/榜/标签书单/书架通吃）。
- ★统一 wc() 把字数格式化为"x.x万字/亿字"短文本；kind 只取前 3 个标签防芯片溢出。
- bookUrlPattern `https?://api[.]hwnovel[.]com/api/ciyuanji/client/(book/getBookDetail|chapter/getChapterContent).*`——绝不能匹配 searchBookList（BookList 会把匹配项按详情页解析）。

## 8. 登录（手机号+验证码）与按钮

- 接口：`POST /login/getPhoneCode {phone,smsType:'1'}` → `POST /login/phone {phone,phoneCode}` → `data.userInfo.token`；token 用 `source.putLoginHeader(JSON.stringify({token:…}))` 持久化（同域请求自动携带）。
- 登录态检查：`GET /user/getUserInfo`，`code==200 && data.cmUser.nickName 非空`。
- loginUi = V1 数组 8 行（手机号/验证码/📤发码/🔑登录/🔍检查登录状态/🚪退出/设备号/⚙应用设备号）——E 版只吃 V1 数组+text/password/button；loginUrl 顶层具名函数、action 直调函数名；`function login()` 空验证码自动转「发送验证码」；所有按钮函数内自 try/catch + longToast。
- 游客态可搜索/免费阅读；发现页支持签到(200/410)。

## 9. 交付 Q/A 清单（本次踩坑）

- MCP `save_source` 手抄 17KB 大 JSON **必错**（本次出现过 cySend 手误 `_cy.getPo?`）→ 保存后必须 get_source/eval_js 回读逐字段 md5 闭环；差异用「Python 生成单行 JSON → read_file → 原样粘贴」修正。
- build.py 拼 JS：**Python `"\\n"`（双反斜杠）= 字面 `\n` 两字符、`"\n"`（单反斜杠）= 真换行**——header 曾被写成字面反斜杠 n 破坏 @js 语法，产物 base64 判别（`Cg==`=真换行 / `XG4`=字面）立即暴露。
- App 侧比字段只比 UTF-8 md5（emoji 占 2 个 UTF-16 单元，Java length 偏小）；实体 getter（getRuleSearch 等）返回 Kotlin 对象比 toString 无意义。
- ★字符串 replace 去前缀时注意引号边界：把 `title:'· '+x` 想改成 `title:x` 时误删字符串开头引号 → `title:'+x` 语法错——node --check 每轮必跑。
- 站点 API 宽松：实测无搜索间隔、concurrentRate `1/1500` 保守即可。
- debug_source 前缀：关键词=搜索、`::URL`=发现页、绝对 URL=详情（自动连带目录/正文）。
- **本地源码树 `/workspace/legado_src`（LegadoTeam 全仓）是排布/协议疑问的第一查证点**——本轮 flexBasisPercent 失效根因正是从 ExploreAdapter.kt + item_find_book.xml 实锤。

## 10. 遗留（待用户真机确认）

- legado-E 版发现页渲染与登录面板；短信登录；VIP 购买；共享设备号长期稳定性（被封按第 3 章三件套自救）。