# 方法：书源 legado-E 兼容改造（V2面板降级 / 列表协议 / 缺失API）

> **适用**：书源在 LegadoTeam（LT/官方改版）上正常，用户换到 **legado-E**（Luoyacheng/legado-E，即"阅读Sigma"）后
> 出现「登录界面空白 / 列表字段全空 / 目录获取失败 / 按钮点了没反应 / 简介显示源码 / 视频播不了」等问题。
>
> **蓝本**：hanime1.me 视频书源 v3.14 → v3.14E（2026-09-21）。E 版仓库：`Luoyacheng/legado-E`（默认分支 `master`）。
>
> **核心心法**：E 版是**旧版基线**（rhino-1.7.14 原生 + 旧 BookSourceType/BookType 枚举 + 精简 RowUi），
> LT 版是**功能增强版**。**兼容版必须按 E 版的"能力下限"写**，再确认 LT 版同样吃这套写法 ——
> 也就是：**V1 面板 + 纯键名字段 + JS 数组 = 两版最大公约数**。

---

## 0. 三句话结论

1. **登录界面**：`loginUi` 绝不能是 `{"version":2}`。E 版 `SourceLoginDialog` 只有
   `GSON.fromJsonArray<RowUi>(loginUi)` 一条路，`RowUi` 只有 4 个字段，只渲染 `text/password/button`。
2. **列表字段**：E 版 `AnalyzeRule` 遇到 **NativeObject 条目**走「**键名直取**」`result[规则文本]`，
   `@js:` / `$.x` 一律取不到 → **字段规则写纯键名**（`title` / `artist` / `u`），列表规则**返回 JS 数组**。
3. **缺失 API 要兜底**：E 版没有 `copyText` / `openVideoPlayer` / `refreshBookInfo` / `md5Encode` /
   `cookie.removeCookie(url,key)` / 3 参 `get()` / `dnsIp` → 全部要 `try/catch` 或双通道。

---

## 1. E 版源码级契约（逐条实测，2026-09-21）

拉源码（本环境 raw.githubusercontent 慢，用 jsdelivr）：
```
https://cdn.jsdelivr.net/gh/Luoyacheng/legado-E@master/<path>
# 列文件： https://data.jsdelivr.com/v1/packages/gh/Luoyacheng/legado-E@master?structure=flat
```

| 关键文件 | 事实 | 兼容写法 |
|---|---|---|
| `ui/login/SourceLoginDialog.kt` | `val loginUi = source.loginUi()`（**无 isLoginUiV2 判断**）→ 逐行 `when(rowUi.type)` 只有 text/password/button；`RowUi(name,type,action,style)` **4 字段**；text 的键 = `name`，值 `loginInfo?.get(rowUi.name)` | **loginUi 写 V1 数组**；输入框 `name` 既是提示也是回填键；用 `style:{layout_flexBasisPercent:1}` 撑满 |
| 同上 · 按钮 | `evalJS("$loginJS\n$buttonFunctionJS"){ put("result", getLoginData(loginUi)) }`，**整段被 `runCatching` 包住 → 返回值被丢弃** | action 里自己 `java.longToast(...)`；返回 r 仅为兼容 LT |
| 同上 · ✓ 按钮 | `menu_ok → putLoginInfo(GSON.toJson(loginData)) → source.login()`；`login()` 只注入 java/source/baseUrl/cookie/cache，**不注入 result** | `function login(){ 先读 result（可能无）→ 再用 source.getLoginInfoMap() 兜底 }` |
| `model/analyzeRule/AnalyzeRule.kt` | `getString/getStringList`：`if (result is NativeObject) { result = result[sourceRule.rule] }` —— **规则文本当键名**，且只处理 `ruleList.first()`（不支持管道） | 列表字段用**单段纯键名**；`@js:`/`$.x` 会取到 undefined |
| 同上 · `getElements` | `result?.let { return it as List<Any> }` —— **返回 String 会抛异常**（LT 版是返回空列表） | 列表规则 `return` **JS 数组**（NativeArray 在两版都实现 List） |
| `model/webBook/BookChapterList.kt` | `bookChapter.title = analyzeRule.getString(nameRule)` / `.url = getString(urlRule)` | 目录字段同样写**纯键名** |
| `model/webBook/BookContent.kt`（197 行） | **无 `callBackJs`、无 `eventListener`、无 `isVideo/isAudio`**；有 `replaceRegex`（逐行 trim+缩进）、`nextContentUrl`、`formatKeepImg` | 正文跟随/事件类增强在 E 版无效（字段保留，LT 版仍生效）；**音频/视频源注意 replaceRegex 会切断 URL** |
| `ui/book/info/BookInfoActivity.kt` | `tvIntro.text = book.getDisplayIntro()` —— **无 useweb/usehtml** | `ruleBookInfo.intro` 降级为**纯文本**（E 版会 `HtmlFormatter.format` 净化 useweb 源码） |
| `constant/BookSourceType.kt` | 只有 `default=0 / audio=1 / image=2 / file=3` —— **无 video=4** | 视频源 `bookSourceType=4` 在 E 版落到 `else → BookType.text`（正文=文本）；**无法修**，如实告知 |
| `constant/BookType.kt` | 只有 text=8 / updateError / audio=32 / image=64 / webFile / local / archive / notShelf —— **无 video=4** | 同上 |
| `model/analyzeRule/AnalyzeUrl.kt` · `UrlOption` | 字段：method/charset/headers/body/origin/retry/type/webView/webJs/js/serverID/webViewDelayTime —— **无 `dnsIp`、无 `timeout`** | `dnsIp` 在 E 版被静默忽略；**DNS 污染站点在 E 版必须走代理** |
| 同上 · 代理 | `header` 里出现 `proxy` 键 → 提取为代理客户端；`getProxyClient` 正则 `(http|socks4|socks5)://host:port(@user@pass)?` | E 版**唯一**的绕过墙/污染通道：`header` 的 `<js>` 里带 `proxy` |
| `help/http/CookieStore.kt` | `setCookie/replaceCookie/getCookie/removeCookie(url)` —— **无 `removeCookie(url,key)`** | `rmck(u,k)`：先试两参，`catch` 后 get 全文→删键→`setCookie` 回写 |
| `help/JsExtensions.kt` | **无 `copyText` / `openVideoPlayer` / `refreshBookInfo` / `refreshTocUrl` / `searchBook` / `md5Encode` / `setCookie`(java)**；`get/head/post` 只有 **2 参**（LT 版 3 参带 timeout） | 全部调用点 `try/catch`；`Jv.get(u,null,20000)` 改 `try{3参}catch{2参}` |
| `help/source/BookSourceExtensions.kt` | `exploreKinds()` 支持 `<js>`/`@js:` ✓（**结果存 ACache**，key=`md5(bookSourceUrl+exploreUrl)`） | 发现页 `<js>` 可用；改配置后需「刷新发现页」清缓存 |
| `data/entities/BaseSource.kt` | `getHeaderMap` 支持 `<js>`/`@js:` ✓；`evalJS` 绑定 java/source/baseUrl(=getKey())/cookie/cache ✓；`getLoginInfoMap/putLoginInfo` ✓；`get/put(k,v)`=CacheManager ✓；`getVariable/setVariable` ✓（无参） | 以上能力**可放心用** |
| `model/SharedJsScope.kt` | jsLib 作为 prototype 注入 loginUrl/规则 scope → **jsLib 函数在 action 里可调** | 工具函数放 jsLib，loginUrl 只做薄分发层 |

### 1.1 `{{}}` 模板在 E 版 ✓
`AnalyzeUrl.replaceKeyPageJs()`：`analyze.innerRule("{{","}}"){ evalJS(it) }`，绑定含 `source` ✓
→ `{{H1DOM(source)}}` / `{{H1OPT(source)}}` 这类模板在两版都可用（**bookUrl/chapterUrl/exploreUrl 里都能用**）。

### 1.2 `##后缀` 不影响 Cookie 域 ✓
`getSubDomain(url)` = `URL(getBaseUrl(url)).host` → 经过 PublicSuffixDatabase。
`https://hanime1.me##E兼容版` → `getBaseUrl` 截到 `https://hanime1.me` → 域 = `hanime1.me` ✓
（`##` 被当 fragment 处理）→ **用它做"同站第二书源"是安全的**，且 `getKey()` 不同 → CacheManager 变量自动隔离。

---

## 2. 改造五步法

### 步骤 1 · 判定"是否需要兼容版"
- 只有登录界面坏 → 改 `loginUi` + `loginUrl` 尾部
- 列表字段全空/条目被丢 → 改列表协议
- 以上都有 → 全套改造（本蓝本）

**关键**：先问用户"E 版还是 LT 版"，两版行为差异大，**不要盲目按 LT 版写**。

### 步骤 2 · 建独立书源（不覆盖原源）
```
bookSourceUrl  = 原URL + '##E兼容版'
bookSourceName = 原名 + ' (E兼容版)'
```
`getKey()` 不同 → 变量/登录信息/发现缓存全部隔离 ✓ 两源可并存 ✓

### 步骤 3 · loginUi 降级为 V1（见 §3 模板）

### 步骤 4 · loginUrl 尾部追加 V1 层
- **保留**原有工具函数与功能函数（`pickLine/h1check/h1login/...`）—— 它们不依赖面板形态
- **删掉** V2 骨架（`function loginUi(...)` / `function loginAction(...)`）
- **追加**：`H1V1(act,Jv,Sv,m)` 统一分发 + `login()` + `isLogin()` + `checkLogin()` + 兼容工具（`rmck`/`h1uiSave`）

```js
/* V1 统一分发：每个按钮 action = H1V1('act',java,source) */
function H1V1(act,Jv,Sv,m){
  Jv=Jv||java; Sv=Sv||source;
  if(!m){ try{m=result}catch(e0){m=null} }        // LT: result=getLoginData;  E: 同
  function mv(k){                                  // 表单取值：双通道 + H1N 归一化
    var v=''; try{ if(m&&m.get){v=m.get(k)} else if(m){v=m[k]} }catch(e1){v=''};
    return H1N(v);                                 // ★JsNull 是 truthy，必须归一化
  }
  var r='';
  try{
    if(act==='apply'){ ... } else if(act==='pick'){ pickLine(st); r=st.msg||'完成' }
    ...
  }catch(e){ r='❌ 操作出错: '+(e&&e.message?e.message:String(e)) }
  try{ if(Jv&&Jv.longToast){ Jv.longToast(String(r)) } }catch(e9){}   // ★E版吞返回值 → 必须自己提示
  return r;                                        // 兼容 LT 版
}
/* ✓ 按钮：E 版不注入 result，用 getLoginInfoMap 兜底 */
function login(){
  var m=null; try{m=result}catch(e){}
  var em='',pw='';
  function rd(k){ var v=''; try{ if(m&&m.get){v=m.get(k)}else if(m){v=m[k]} }catch(e){}; return H1N(v) }
  if(m){ em=rd('账号'); pw=rd('密码') }
  if(em===''||pw===''){ try{ var lm=source.getLoginInfoMap(); if(lm&&lm.get){ em=H1N(lm.get('账号')); pw=H1N(lm.get('密码')) } }catch(e2){} }
  if(em===''||pw===''){ return '请在面板填写账号密码后点【🔐 登录】' }
  return H1V1('login',java,source,{账号:em,密码:pw});
}
```

### 步骤 5 · 列表协议改纯键名 + 预计算字段
**问题**：原规则常用 `@js:String(result.artist||'')`、`@js:H1BU(String(result.v))` —— E 版取不到。
**解法**：把"需要计算"的字段**移到列表 JS 里预生成**，字段规则只剩纯键名：

```js
// 列表规则（两版通用）
function H1CARDS(src,html){
  ... var out=[]; ... out.push({title:t, artist:art, v:v,
        u:H1BU(v),            // ← URL 生成搬到条目里（含 dnsIp 选项）
        cover:H1FIX(src,cv),  // ← CDN 修复搬到条目里
        kind:kk.join(' ') }); // ← 拼接搬到条目里
  return out;                 // ★返回 JS 数组（不是 JSON 字符串！）
}
```
```
ruleSearch.bookList = @js:H1CARDS(source,String(result))
ruleSearch.name     = title      ← 纯键名
ruleSearch.author   = artist
ruleSearch.bookUrl  = u
ruleSearch.coverUrl = cover
ruleSearch.kind     = kind
ruleSearch.intro    = title
ruleToc.chapterName = n          ← 原本就是纯键名则不动
ruleToc.chapterUrl  = u
```

> **为什么不改成"JSON 字符串数组 + `$.键`"？** 也可以（LT/E 都走 Mode.Json），
> 但**纯键名 + JS 数组**改动更小（列表函数不用动），且 E 版源码里 NativeObject 分支明确支持键名直取。
> 两种方案二选一即可，**别混用**（`$.x` 配 NativeObject 在 E 版必挂）。

---

## 3. V1 面板模板（可直接复制）

```python
W = {"layout_flexBasisPercent": 1}
def btn(name, act):   return {"name": name, "type": "button", "action": "H1V1('%s',java,source)" % act, "style": W}
def txt(name, typ="text"): return {"name": name, "type": typ, "style": W}
rows = [
    btn("❓ 帮助 / 使用说明", "help"),
    btn("──── 🌐 网络线路（填好后点应用） ────",
        inline="java.longToast('填好文本框后点【✅ 应用以上配置】生效')"),   # 分区标题：inline JS 更稳
    txt("自定义域名"), txt("hostsIP"), txt("代理地址"),
    btn("✅ 应用以上配置", "apply"),
    ...
]
d['loginUi'] = json.dumps(rows, ensure_ascii=False)
```

**V1 面板硬约束**：
1. `type` 只能是 `text`/`password`/`button`（label/select/toggle **不渲染**，静默跳过）
2. 分区标题用 `button` + **inline JS**（`java.longToast(...)`）—— 别用空 action（无反馈）也别用 label
3. 输入框 `name` = 键名 = 回填键（E 版 `loginInfo?.get(rowUi.name)`）→ **name 要稳定**，改了就丢回填
4. 输入框**没有** `value` 字段 → 想要回填必须 `putLoginInfo()` 写入
5. 按钮 `action` 是**一段 JS 代码**，运行在 `loginJS + "\n" + action` 环境（java/source 已绑定，jsLib 可见）
6. **不要**在 action 里 `return` 期待 UI 更新 —— 返回值被吞，一切反馈靠 `longToast`

**回填（输入框显示当前配置）的通用做法**：
```js
function h1uiSave(Sv,extra){                       // 合并写 loginInfo（不清账号密码）
  var m={};
  try{ var lm=Sv.getLoginInfoMap(); if(lm){ var it=lm.keySet().iterator();
       while(it.hasNext()){ var k=String(it.next()); var v=lm.get(k); m[k]=(v==null?'':String(v)) } } }catch(e){}
  if(extra){ for(var k2 in extra){ var v2=extra[k2]; if(v2!==undefined&&v2!==null){ m[k2]=String(v2) } } }
  try{ Sv.putLoginInfo(JSON.stringify(m)) }catch(e){}
}
```
> **坑**：`removeLoginInfo()` 在部分 App 版本上"读了还在"（缓存），要清空回填用 **`putLoginInfo('{}')`** 最干净。

---

## 4. 验证方法论（三层，缺一不可）

### 第 1 层 · 静态契约（Python，秒级）
- `node --check` 每一个 JS 块（jsLib/loginUrl/exploreUrl/header/loginCheckJs/所有 `@js:` 规则）
- loginUi：行数 / type 白名单 / 按钮均有 action / 输入框均有 name / **按钮 action 全部有分发分支**
- 列表字段：断言**无** `@js:` 与 `$.` 前缀
- 缺失 API 调用点：正则扫 `\.(copyText|openVideoPlayer|refreshBookInfo|...)\(`，检查前 160 字符内是否有 `try{`
- `get/post/head` 参数个数扫描（E 版 2 参）
- **原版 vs 兼容版逐字段 diff**：确认"保留项"逐字节不变（本次 8 项全一致）

### 第 2 层 · 真实 App 实测（MCP）
- 导入后 **逐字段回读 md5 比对**（`get_source` → 本地 vs 远端；本次 28/29 一致，差异仅 `customOrder`）
- `check_source` 官方校验
- `debug_source` 全链路：搜索 / 详情 / 目录 / 正文 / 发现（`::URL` 前缀）
- **V1 面板契约**：`source.isLoginUiV2()` 应为 `false`；`source.getLoginUiJs()` 应为 `null`
  → 证明 LT 版也走 V1 渲染（两版一致）
- **按钮点击精确模拟**（不用点 UI）：
  ```js
  var lu=String(source.getLoginJs());
  var ui=JSON.parse(String(source.loginUi));
  var act=String(ui[5].action);                       // 目标按钮
  var code = lu + "\n" + "var result={'自定义域名':'x','hostsIP':'1.2.3.4'};" + "\n" + act;
  String(eval(code));                                 // 返回 = 面板提示文案
  ```
- **纯键名取值等价验证**：`new AnalyzeRule()` + `setContent(条目)` + `getString('title')`
  （注意：`new AnalyzeRule()` **不会注入 jsLib**，所以列表规则本身要另测）

### 第 3 层 · 源码级契约核对（E 版无法直连时）
MCP 连接的 App 往往是 LT 版 → **E 版行为无法直测**，必须拉 E 版源码逐条核对（§1 表），
并用"等价模拟"证明（如：对同一条目同时取 `title` 与 `@js:String(result.artist)`，
后者返回 `undefined` 即证明 E 版路径的差异真实存在）。

---

## 5. 避坑清单

| # | 坑 | 症状 | 解法 |
|---|---|---|---|
| K1 | `loginUi={"version":2}` | E 版面板**完全空白**（不报错，只是没 UI） | 改 V1 数组 |
| K2 | V1 用了 label/select/toggle | 那些行**静默消失** | 只用 text/password/button |
| K3 | 按钮 action 只 `return 'msg'` | 点了没任何反应 | 自己 `java.longToast()` |
| K4 | `login()` 只读 `result` | ✓ 按钮报错/无反应（E 版不注入 result） | `getLoginInfoMap()` 兜底 |
| K5 | 列表字段 `@js:` / `$.x` | 列表大小正常但**字段全空**（条目被丢 → "书籍总数:1"） | 纯键名 + 列表内预生成字段 |
| K6 | 列表规则 `return JSON.stringify(arr)` | E 版 `it as List<Any>` 抛异常；LT 版列表为空 | `return` JS 数组 |
| K7 | 规则里管道 `a\|\|b@x` | NativeObject 分支只取 `ruleList.first()` | 字段规则保持单段 |
| K8 | `cookie.removeCookie(u,k)` | 退出登录清不掉（异常被 catch 吞） | `rmck()` 双通道 |
| K9 | `Jv.get(u,null,20000)` | E 版"找不到方法 get" | `try{3参}catch{2参}` |
| K10 | `java.copyText/openVideoPlayer/refreshBookInfo` | 抛异常 | `try/catch`（并降级提示） |
| K11 | 依赖 `dnsIp` 绕污染 | E 版静默忽略 → 请求超时 | 明确告知"E 版需代理"；`header` 带 `proxy` |
| K12 | `ruleBookInfo.intro` 用 useweb | E 版简介显示一堆 CSS/JS 源码 | 降级纯文本 |
| K13 | 期待 `callBackJs`/`eventListener` | E 版无效 | 保留字段（LT 生效），文档说明 |
| K14 | 期待 `bookSourceType=4` 播视频 | E 版当文本 | 无法修，如实说明 |
| K15 | jsLib 里无参函数靠闭包读 `source` | 静默失败（返回空） | **显式传参**（`f(so,jv)`） |
| K16 | jsLib/loginUrl 顶层 `const/let` | E 版"重新声明了常量" | 只用 `var/function` |
| K17 | `removeLoginInfo()` 清不掉回填 | 面板仍显示旧值 | 用 `putLoginInfo('{}')` |
| K18 | 在 `eval_js` 里 `eval(loginUrl)` 后调函数 | "xxx 未定义" | **同段脚本内 eval + 调用**（函数声明不外泄） |
| K19 | 改 `exploreUrl` 后不生效 | E 版 ACache 缓存 | 「刷新发现页」；缓存 key 含 bookSourceUrl |
| K20 | 直接改原源做兼容 | 用户 LT 版功能被降级 | **新建 `##E兼容版` 独立源** |

---

## 6. 案例档案

| 书源 | 站点特征 | 主要改造 | 结果 |
|---|---|---|---|
| **hanime1.me v3.14E** | CF 托管 + DNS 污染 + V2 面板 + useweb 简介 + 视频源 | V1 面板 37 行；`H1CARDS` 预生成 `u/cover/kind`；12 处字段改纯键名；`intro` 降级纯文本；`rmck`；`get` 双通道 | check_source 1/1；搜索59/详情/目录/正文/发现全通；LT 回归一致 28/29 字段字节级；V1 面板 31 按钮全可编译 |
| iwara（历史） | REST API + 关系态 | V1 面板 24 行 + `IWRV1(act,Jv,Sv,m)` 薄分发（逻辑全在 jsLib） | 面板可用 |

---

## 7. 一句话口诀

> **面板降到 V1（text/password/button + longToast 自报结果），字段只留纯键名（计算搬进列表 JS），列表 return JS 数组，缺的 API 全兜底，另起 `##兼容版` 不覆盖原源。**
