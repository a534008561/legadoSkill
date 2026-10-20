# 八叉书库（8xsk.cc）· 线路自愈反代源与书源自助运维面板

- 书源文件：[八叉书库_ip-ddns反代源.json](八叉书库_ip-ddns反代源.json)（99550 B / v7.1，`check_source` 通过）
- 配套方法论：
  - [方法-线路自愈与登录面板运维套件](../references/方法-线路自愈与登录面板运维套件.md)
  - [方法-书源自助运维面板与站点特色功能拆解](../references/方法-书源自助运维面板与站点特色功能拆解.md)
- 规模：99550 B / jsLib 15253 字符 / 登录面板 35 按钮 / 19 个 jsLib 功能函数
- 背景：站点 `8xsk.cc` 原为参考，真实成品是反代形态源「🌈八叉书库」（bookSourceUrl 保留 `https://八叉书库.luoyacheng.ip-ddns.com` 作身份，线路由登录面板「网址」变量驱动）；同一作者另有直连版「八叉书库(8xsk)」@8xsk.cc。

## 要点

- ★★★**多域名线路自愈**（5 备用域名）：登录界面点线路按钮 → `source.putLoginInfo({'网址':u})` → `getsurl()` 单点读取。铁律：**除 `getsurl()` 内部，任何规则不许直接读 `source.get('网址')`**——破例处上线后必漏改，表现为「部分功能能用、部分不能」。探活三判据（长度下限 + 反例关键词 + 正例关键词）**不能只看 HTTP 200**：劫持页/年龄闸门/维护页全是 200；只对 `BX_DEAD` 状态探活，测速排序取 `ok[0]`。
- ★★★**发布页取址用纯 HTTP**（v5 教训）：`webfb()` 最初用 `webView:true` 抓发布页 8xsk.org，被网络环境阻断超时 60s；改纯 HTTP `java.connect` 后 406ms 拿到全部 7 个站点。**内置浏览器/WebView 与书源 OkHttp 是两套网络栈**（WebView 连 about:blank 都超时），不能拿 WebView 失败断言站点不可达。
- ★★★**书架双向同步**（网站→Legado）：深链批量 `legado://import/addToBookshelf?src=...`，**必须 `sleep(700)` 否则 7 本只进 2~3 本**；必须带 `,{"origin":"{bookSourceUrl}"}` 防被别的源抢；**书架 id 是 `aid` 不是 `bid`**；手机 c_row 模板字段映射（书名 h4@a、aid=h4@a@href 的 aid 参数、封面 .row_cover img、书架记录 id=h4 input@value、readbookcase.php?bid=&aid=&cid= 转详情 = `getsurl()+'/book/'+aid+'.html'`）。
- ★★★**SVG 验证码当输入框**：`java.getVerificationCode('data:image/svg+xml;base64,'+svg)` 的语义是「显示一张图让用户输入」，不关心图是不是真验证码 ⇒ 在 SVG 里画操作说明、用户输命令，**零新增 UI 复用现成弹窗**，可移植到任何需要文本输入的书源。
- ★★**exploreUrl 入口 {{}} 模板的三元+逗号陷阱**（v7.1 书架失效根因）：`ck ? bookcaseURL : toast(),'dataURI'` 是**逗号表达式**，求值恒为最后的 data URI，bookcase.php 被静默丢弃。有副作用的兜底必须括号包裹 `(toast(),'dataURI')`——逗号运算符优先级低于三元。
- ★★**年龄闸门 Cookie**：必须固定带 `age18_ok=1`（POST 表单不下发，只能内置）；`cookie.setCookie` 是**整体替换语义**，合并浏览器 Cookie 时若整串回写会把 age18_ok 冲掉，页面又变「年龄确认」页（webck() 修复：只合并不替换）。
- ★★**登录态判定不能凭 Cookie 键存在**：未登录时 CookieJar 里也有 jieqiUserId/jieqiUserName，缺的只是凭证键（jieqiUserToken/jieqiUserPassword）；正确判据=访问 userdetail.php 是否被 302 到 login.php（页面含 frmlogin）。
- ★★**putLoginHeader 必须传 JSON `{"Cookie":...}`**：传纯 Cookie 串时 `getHeaderMap(true)` 静默丢弃 Cookie 键 → 请求不带凭证 → 「登录成功但 VIP 章读不了」。配套 `ckget(so)` 兼容函数统一读登录头。
- ★★**VIP 章节三态**：目录里 VIP 章 URL 是 `/modules/obook/reader.php?cid=&aid=`（非 /read/）；/read/ 访问 VIP 章 302 回目录页 → 正文规则自动改走 obook 入口；未订阅显示预览摘要+订阅指引，自动购买走 `buychapter.php`（需 jieqi_token）。
- ★★**「阅读预下载」与「批量下载」必须分流**（v7）：下载时 `book.durChapterIndex` 是阅读位置不动、`chapter.index` 是目标章 → 阅读限速锁/随机延迟对下载全是纯浪费（实测单章 40~61s）甚至空正文（`default: ii=0`）；`dn==1`（下载模式）时全部跳过，实测单章 0.9~1.5s。下载根因之一还有 `cache.getFromMemory` 返回 Java 包装对象参与字符串拼接导致死循环，`Number()` 归一 + 8s 上限 + 5s 锁修复。
- ★**购买成功分支也要走解密**（v6）：购买后返回的正文页**同样是加密的**，`result=pt.body()` 直接赋值让阅读器拿密文显示空，刷新二次访问才走解密路径——用户观感「自动购买不顺畅需刷新才出正文」。修复=解密封装 `decContent()`（首次访问/购买成功/未重定向三路共用）。
- ★**黑名单落地机制**：`name` 规则返回 `''` → `BookList.getSearchItem` 的 `name.isBlank() → return null` 就是 Legado 的过滤口（黑名单关键词靠这个生效）。
- ★**SVG 现场生成封面**：7 字切行 + `tspan` 逐字竖排，`data:image/svg+xml;base64,` 直接当 coverUrl，无图书永不 404。
- ★**版本更新检查**：gitee commits 当版本号源，版本号写在 `exploreUrl` 一处维护，按钮文案随状态变「更新/导入」。
- ★**重置必须保留用户资产**：只重置开关与登录态，账号/密码/网址/颜色保留。

## 验证

- `check_source` 通过；登录面板 35 按钮逐个实测（25 按钮轮 + 10 按钮 v7.1）
- 全链路 debug：搜索 → 详情 → 目录（VIP 三态标记）→ 正文（atob 解密 + 广告清洗）→ 发现页 46 入口
- VIP 端到端真机：订阅表单 → 自动购买 → 解密 7467 字正文
- 下载模式真机：`dn=1, inn=10/50` 单章 0.9~1.5s 全文完整
- 书架修复真机：`debug_source ::bookcase.php` 发现 7 本 → 详情 → 目录 106 章 → 正文完整
- App 回读七项特征（ckget/webfbFix/下载锁/dtm/hex 防御/decContent/buyFix）全过；jsLib 长度 15253 与本地一致

## 踩坑速查

1. `java.connect` 返回 jsoup Response（有 body()/url()/code()）；`java.get` 返回 StrResponse（有 body()/url()，没有 code()）——调用前先分清
2. `r.headers().values('Set-Cookie')` 在 Rhino 抛 ClassCastException，取 Cookie 用 `cookie.getCookie(url)`
3. loginUi 不是严格 JSON（键名无引号）不能 JSON.parse，须 eval；按钮 action 环境里 `this.book` 为 undefined
4. 多行 JSON 里换行会截断字符串字面量（node --check 通过但真实解析失败）→ searchUrl/exploreUrl 单行 + String.fromCharCode 拼引号
5. 验证码地址藏在 `input#checkcode` 的 onfocus 属性里（登录页 img src 为空）
6. patch 脚本改 lines[i] 后必须 `chr(10).join(lines)` 回写再 dump（只改 list 不 join = 改动不落盘）
7. App 端 `source.getJsLib()` 返回 Java String（`.length` 是方法引用），须 `String()` 包裹或只比特征子串
8. patch 锚点替换必须先 print 上下文再动手，replace 正则绝不能宽到命中自己刚写入的行
