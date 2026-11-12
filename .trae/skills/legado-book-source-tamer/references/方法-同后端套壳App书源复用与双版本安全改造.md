# 方法-同后端套壳 App 书源复用与双版本安全改造

> 蓝本：全民小说 5.0.8（`com.qmxsppa.novelreader`）全量参考顶点小说 App / 猫眼看书书源 v5.4（`app.maoyankanshu.novel`），2026-11-13 交付。

## 1. 适用场景与结论

当两个 APP 名称/包名/版本号/渠道不同，但 ProxyPin 抓包显示业务请求落在同一组域名、同一批路径、同一套密文协议时，**不要从零逆向第二遍**：全量复用已验证的纯接口书源规则，只做「身份对齐 + 安全改造 + 交付回归」。本次实锤：

- 全民小说业务头：`package=com.qmxsppa.novelreader`、`version=5.0.5`、`channel=new2025`、UA=`SAMSUNG-GT-I9158_TD/1.0 ..._com.qmxsppa.novelreader`、`xf-appid=11000001`、`pt=1`；
- 真实业务域与顶点小说/猫眼看书完全相同：`s / d / book / catalog / chapter / conf / res / c-res .yutinglu.com`；
- `conf.yutinglu.com/v4/android/{package}/normal.html` 对两个包名都返回同一类主协议加密配置；
- `bqm.125ks.cn/jc/{app,tj,v,abc}.php` 是全民小说 APK 里 `com.share.sdk` / `com.tencent.as.javask` 的广告/开关控制页，**不是小说 API**。抓到它时不要据此拼搜索/目录规则。

对照实验（非搜索接口）：给 `book.yutinglu.com/book_city/v7/index/1/0/1.html` 分别发旧包名头与全民小说头，均 HTTP 200 + `code:1` + 加密 `content`，且响应带游客 `uid` Cookie。结论：**业务接口不需要登录、不需要复制 `sign/time/stamp`，只需固定正确身份头与 UA**。

## 2. 「全量参考」的最小改动清单

1. `bookSourceUrl` 换成官方书城域（本例 `https://book.yutinglu.com`），不要沿用旧发布页/广告域；
2. `header` 换目标 APP 的真实 UA + `package/version/channel/xf-appid/pt/fc-session-id`；
3. `bookUrlPattern` 必须精确到**书籍详情 URL**：`^https?://d\.yutinglu\.com/book/details/v4/(?:\d+/)?\d+\.html(?:[?#].*)?$`。不要写覆盖整域的宽正则，否则搜索 URL 可能被误判为详情页；
4. 搜索/详情/目录/正文/发现页算法、主协议解密 `D()`、正文短密文 `MK()`、线路列表 `OBJS()/BOOKS()` 全部保留；
5. 发现页 `{{page}}` 继续跟随站点自身，不写死页码上限；
6. `concurrentRate` 给保守节流（本例 `1/2000`），**不主动探测搜索频率**：只做一次 `debug_source` 关键词全链路，其余用 `::发现URL`、真实详情 URL 回归；测速/检查登录状态按钮也只走书城/配置/连通性端点，绝不请求搜索端点；
7. `bookSourceComment` 明确：无需登录、游客 uid、发布页是广告控制页、测速不碰搜索。

## 3. LT / legado-E 双版本安全改造

旧猫眼 v5.4 在 LT 正常，但 `bookList/chapterList` 返回 Rhino 原生数组，E 版 `AnalyzeRule.getElements` 没有 `NativeArray -> ArrayList` 分支，容易在目录处 ClassCastException/空目录。通用修法：

```js
// jsLib 中加纯函数，不裸碰 java/book/source
function QM_LIST(a){
 var list = new Packages.java.util.ArrayList();
 if(!a) return list;
 try { if(a.size && typeof a.size==='function') a = a.toArray(); } catch(e) {}
 for(var i=0;i<a.length;i++)
   list.add(typeof a[i]==='string'?a[i]:JSON.stringify(a[i]));
 return list;
}
```

- `ruleSearch.bookList`、`ruleExplore.bookList`、`ruleToc.chapterList` 的所有 `return [] / return out / return L / return a.map(...)` 统一改成 `return QM_LIST(...)`；
- 列表每项必须 `JSON.stringify({...})` 字符串，字段规则改成 `$.name` / `$.url` / `$.bookUrl`；E 版 `getString` 对 NativeObject 没有 `Mode.Js`，纯 `$.key` 走 JsonPath 最稳；
- `jsLib` 函数名与 `loginUrl` 函数名必须取交集为空（避免登录面板 `$loginJS + action` 拼接后同名函数覆盖规则函数）；本例规则侧 `D/F/MK/...`，面板侧 `QM_*`；
- `loginUrl` 必须包含 `function login(){return 'ok';}`；面板函数统一 `QM_xxx(java)` 单参，内部对 `source/infoMap/result` 全部 try/catch 兜底。

## 4. 无需登录时也要写「检查登录状态」按钮

用户要求「需要登录写检查登录状态」；本次虽实锤游客态免登录，仍保留 `✅ 检查登录状态` 按钮，语义改为**游客态/接口连通性检查**：一次 `book_city` 请求，判 `code:1/content` + 耗时，Toast 分「⏳ 正在检查」→「✅/⚠️ 检查完成」。这样既不误导用户去登录，也不碰搜索接口。

登录面板（V1 静态数组 + `viewName` JS 表达式）包含：

- `🔗 发布页地址` 输入框，默认 `https://bqm.125ks.cn/jc/v.php`；`QM_pub()` 多通道读 `getLoginInfoMap / source / result / infoMap / java.get`；
- `① 一键从发布页获取网址路线`：抓发布页里的 http(s) 主机 + 合并 ProxyPin 实锤的 6 个官方业务域，写入 `qm_line1..6`；
- `② 测试延时（全部网站）`：逐站 8 秒超时，只请求书城/配置/连通性端点，测得 `ms` 写入 `qm_sp1..6`，最快加 `⚡`；
- 6 个 `🌐 网址N` 按钮，各自点击切换 `qm_line` 并 Toast；按钮 `viewName` 显示域名 + 延时；
- 每个阶段都有 `QM_T()` 的 Toast（longToast → toast → copyText 三重保险）；`QM_re()` 尝试 `reLoginView()` / `reUiView(true)`。

★ 静态门禁要**剥离注释后再扫描**：注释里出现搜索端点字样会误判「测速碰搜索接口」；代码里绝不能出现该端点。

## 5. 交付闭环与实测记录

- 大文件 46KB 走 LAN `POST /saveBookSource` 单对象：LT `1122` 带 `x-legado-token`，E 版 `1125` 无令牌；`getBookSource` 回读字段闭环。掉线后 LAN IP 从 `192.168.10.7` 变为 `192.168.10.2`，两个端口都要重新探活；E 版 1125 若 App 后台 Web 服务未启动会 `Connection refused`，脚本需重试/提示用户打开 E 版 Web 服务。
- LT MCP：`check_source 1/1`；一次搜索「斗破苍穹」= 100 本 → 详情 3 线路 → 目录 1658 章 → 正文「斗之力，三段！」全绿；`::https://book.yutinglu.com/book_city/v7/index/1/0/1.html` 发现页 = 66 本 → 详情 16 线路 → 目录 5368 章 → 正文全绿。
- `eval_js` 登录面板门禁：13 行 / 9 按钮 / 所有 action 函数存在 / 所有 viewName 可求值 / `login` 函数存在 / Toast 调用 14 处 / 剥离注释后无搜索端点。
- E 版无 MCP，验证路线=`saveBookSource`→`saveBook(bookUrl+origin)`→`refreshToc?url`→`getChapterList?url`→`getBookContent?url&index=0`；`getBookContent` 必须带 `index`，且用未缓存章节验证新规则。

## 6. 本次新沉淀的通用坑

1. **「两个 APP 很像」要先分业务域与广告域**：APK `assets/info.json` 指向广告控制页，但 ProxyPin 后续 `book/catalog/chapter.yutinglu.com` 才是书源；只看首个启动请求会走错方向。
2. **套壳/马甲 APP 的书源复用不是改个名字**：身份头与 UA 决定配置/游客态，必须按抓包逐字段替换；但签名/加密/路径若同一后端可全量复用。
3. **测速按钮也会制造风控**：用户要求「不要主动探测搜索访问频率」时，不仅 `debug_source` 要少，登录面板测速也不能批量打搜索端点；用书城/配置端点做连通性延时即可。
4. **注释会成为静态门禁假阳性**：「绝不请求 lists.api」写在注释里，整串扫描会误报；门禁必须先去注释。
5. **掉线/IP 变化后双端口不是同步恢复**：1122 正常不代表 1125 正常；E 版 Web 服务独立，回读/重存/整源集成要按端口分别判活。
