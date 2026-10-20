# 方法-legadoE 登录面板 V1 动态化与发现页点选化（select→toggle）

> 260926 禁漫天堂 v15e 实战沉淀。适用：把 V2 面板书源适配 legado-E；把登录面板/发现页下拉框改成按钮点选。

## 0 一句话
E 版登录对话框 V2 直接解析失败（空面板）；E 版完全支持 **@js:/<js> 动态 V1 数组** 与 **toggle 点选行**（登录面板与发现页都支持，含 select）；点选化的关键是 action 作用域：**登录面板 action 能看到 loginUrl 函数（拼接 eval），发现页 action 只能看到 jsLib（shareScope）**。

## 1 E 版 SourceLoginDialog 能力表（Luoyacheng/legado-E main，2026-09-25）
- loginUi 三种形态：字面 JSON 数组 / `@js:`（取前缀后全部文本）/ `<js>`（substring(4, lastIndexOf('<'))，代码里不能出现 `<`）
- 类型白名单渲染：text / password / select(Spinner+onItemSelected 自动跑 action) / button(短按+长按 isLongClick) / toggle(点按自动循环 chars：先把选中值写 loginInfo[name]，再跑 action，action 内 result 可读选中值)；**label 不渲染**
- viewName 规则（select/text/password/button/toggle 通用）：3..19 且首尾单引号=字面量；否则异步 evalUiJs（bindings=result=loginInfoMap、book、chapter、默认 java/source/baseUrl/cookie/cache），UI 层不阻塞
- 按钮 action：`source.evalJS(loginUrl+"\n"+action){put("java",SourceLoginJsExtensions),put("result",getLoginData)}`，**返回值被忽略** → 结果必须自己 java.toast/longToast
- ✓(menu_ok)：getLoginData(只有 text/password 行) → 空则 removeLoginInfo+dismiss；非空则 putLoginInfo(JSON) 再 eval `if(typeof login=='function')login.apply(this)`（bindings 含 java/result/book）；onDismiss 未点✓但有改动→自动 putLoginInfo
- login() 需要写在 loginUrl 顶层；读凭据双通道（getLoginInfoMap→result→存变量 fallback）
- SourceLoginJsExtensions 额外可用：reLoginView(deltaUp)（重跑动态 loginUi 并重建面板！点选后刷新按钮文字就靠它）、refreshExplore、copyText、showBrowser
- 文本行带 action → TextWatcher 600ms 防抖自动执行（可与 autosave 配合）

## 2 E 版发现页（ExploreKind / ExploreAdapter）能力表
- exploreUrl 支持 @js:<js>（BookSourceExtensions.exploreKinds：evalJS 时 put("infoMap", exploreInfoMap)）；结果 aCache 持久缓存（键=md5(bookSourceUrl+exploreUrl)——**改书源 URL 即换新缓存，不串旧缓存**）
- ExploreKind 类型：url/text/button/toggle/select；toggle=点按循环 chars（直接读写 infoMap[title]，点击后执行 action）
- viewName 同登录面板字面量/异步规则；bindings=infoMap+默认
- action 执行：`source.evalJS(action){put("java",SourceLoginJsExtensions),put("infoMap",infoMap)}` —— **作用域只有 jsLib(shareScope)+绑定；loginUrl 函数不可见**（有 `eval(String(source.loginUrl))` 的只有 exploreUrl 求值本身）

## 3 改造四板斧
1. loginUi：`{"version":2}` → `@js:jmeRows()`；jmeRows 放 loginUrl（被拼接 eval 时可见）；返回 JSON.stringify(rows)。jmeRows 内可直接调 loginUrl 其它函数（jmLines/jmFoldersRaw/GV/SV…）
2. select→toggle：chars=短可读值、default=当前变量、viewName 给 3..19 单引号字面量后缀（如 `"'·点按切换'"`），组件自动「选中值+后缀」显示、点按循环；action 里用 `result.get?result.get(name):result[name]` 双通道读选中值 → 写变量 → toast；读不到时按当前变量自循环兜底
3. 状态性按钮（模式/分流/每周/收藏夹选定）点击后补 `try{java.reLoginView(true)}catch(e){}` 重建面板刷新文字（E 专属但 LT 侧 try/catch 无害）
4. 发现页 action 必须下沉 jsLib 且**参数注入**：`jmExplAct(java,source,infoMap)`——jsLib 无参闭包读全局 source 会静默失效（Rhino SharedJsScope 老坑）

## 4 必须同步修复的 E 隐形炸弹
- loginCheckJs：`result.body` 在 E 是属性、在 LT(htmlunit) 是方法——全部改 `(typeof r.body=='function')?r.body():r.body`，并以 IIFE `(function(){...return r;})()` 原样返回 StrResponse
- jsLib 与 loginUrl/loginUi 共享作用域：顶层禁止 const/let（拼接重复声明 → "变量被重新声明"）
- 列表协议：JS 数组 + 逐条 String(JSON.stringify(o)) + 字段 `$.key`（E 对 NativeObject 条目把 `$.key` 当完整键名 → undefined → 掉条目）
- 版本无关：bookSourceUrl 加 `##E兼容` 片段 → 与主源并存不覆盖；改 URL 天然隔离 exploreUrl aCache、CacheManager 变量键

## 5 验证方法论（本案例全套）
1. node vm 沙盒（`vm.createContext`+`runInContext`，函数声明附着沙盒）直跑**产出的真实** loginUrl/jsLib/loginCheckJs/exploreUrl 文本，stub 掉 java.ajax/source 存取层 → 结构断言（类型白名单/action 可达/viewName 3..19/收藏夹按钮/默认回填）+ 行为断言（toggle 写变量/模式路由/login 双通道/loginCheckJs 5 场景含 body 双向）
2. App 真 Rhino 小探针（真实 jme 块+stub）跨引擎验证
3. dpaste 字节级校验 + 深链 + get_http_logs `GET raw -> 200` + 导入后 get_source 逐字段 md5 回读
4. 现场校准：debug 搜索列表=0 时，先对照组（旧源同关键词）确认不是我改动的因果；再抓响应看真实页面（当晚全线路 978B /idss/ 挑战=站方对家宽 IP 风控，海外 IP 669KB 正常）→ loginCheckJs 加 `/idss/` 判据把风控显性化

## 6 坑清单
K1 E V2 面板字段 → fromJsonArray 失败面板空白 / K2 body 属性方法双引擎 / K3 发现页 action 作用域只有 jsLib / K4 toggle action 靠 result 读选中值（键=name=infoMap key，emoji 键名可用）/ K5 返回 JSON 数组要零 `<`（若走 <js> 会被 lastIndexOf 截断；@js: 无此限制）/ K6 E toggle 显示=选中值+viewName（viewName 要与 name 分工：name 做键，viewName 做后缀文案）/ K7 点选后 value 与 chars 失配时 indexOf=-1 循环从头（可用）/ K8 java.ajax 异常有时返回异常串（抓取后必须判 key 特征而非长度）/ K9 MCP/js 手写禁用反斜杠正则（`<\/span>` 传输层变非法标志）——正则用 jsoup select 替代 / K10 风控页必须在 loginCheckJs 显性 throw，否则「获取成功但列表0」的静默假象