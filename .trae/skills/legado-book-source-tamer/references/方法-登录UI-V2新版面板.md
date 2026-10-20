# 方法：登录 UI V2 新版面板（LegadoTeam 新版 `loginUi={"version":2}`）

> 来源：hanime1 v2.0 生产实战（2026-09-13，check_source 1/1 + 真机全动作实测）
> 本 App（LegadoTeam 新版）源码完整确认：`SourceLoginDialog` / `SourceLoginV2Delegate` / `LoginUiV2` / `BaseSource.evalLoginUiV2/evalLoginActionV2`

## 0. 什么时候用 V2

| 需求 | V1(经典) | V2(新版) |
|---|---|---|
| 文本框+按钮 | ✅ | ✅ |
| **下拉选择**(域名/hosts/线路/清晰度) | ❌(只能手输) | ✅ select+options |
| **开关**(代理/模式) | ❌ | ✅ toggle |
| **防连点倒计时**(测速/登录) | ❌ | ✅ button countdown |
| 状态消息板(操作结果显示在面板顶部) | ❌(只能 toast) | ✅ state.msg→label 行 |
| 错误定位到具体输入框 | ❌ | ✅ error:{key:msg} |
| 账号密码自动回填(官方加密存储) | ✅ loginInfo | ✅ putLoginInfo |

V1/V2 判定：`loginUi` 文本以 `{` 开头且 `version==2` → V2（`LoginUiV2.isV2`）。否则走 V1 经典流程。**同一书源只能二选一**。

## 1. 数据链路（源码级）

```
loginUi = '{"version":2}'            ← 触发标记
loginUrl = <全部 JS 逻辑(顶层函数集, 必须含 loginUi/loginAction)>

打开面板: SourceLoginV2Delegate.render()
  → source.evalLoginUiV2(stateJson, book, chapter)
  → JS: loginUi(JSON.parse(String(__loginState)))
  → 返回 JSON: {"rows":[RowUi...]}   (LoginUiV2.parseRender 校验)

点按钮/切开关: dispatch(action)
  → formJson = 当前所有输入行 {key:value}
  → source.evalLoginActionV2(action, stateJson, formJson, book, chapter)
  → JS: loginAction(String(__loginAction), JSON.parse(String(__loginState)), JSON.parse(String(__loginForm)))
  → 返回命令 JSON(LoginUiV2.parseActionResult):
      {"state":{...},           // 非空→重渲染面板(新state); 空→仅应用error
       "error":{"key":"消息"},   // key对应输入行红字; key不在面板→toast
       "login":{...},           // 非空→putLoginInfo 官方加密存储(账号密码)
       "close":true}            // 关闭面板
```

**state 就是面板的内存**：每次动作返回的 state 会原样传回下次渲染/动作。用它存 msg、临时选择、检测结果。

## 2. RowUi V2 字段与硬约束

```json
{"name":"显示名", "type":"text|password|label|select|toggle|button",
 "key":"form键(text/password/select/toggle必填)",
 "action":"动作名(button必填,toggle可选)",
 "options":["A","B"],           // select必填(注意: 不是chars!)
 "value":"当前值",               // select/toggle/输入行初值
 "hint":"输入框占位文字",
 "countdown":30,                 // button可选: 成功后N秒倒计时防连点
 "style":{"layout_flexBasisPercent":1}}  // 1=整行
```

`LoginUiV2.isValid()` 校验（任一不通过→整面板渲染失败显示"渲染出错"）：
- text/password：**key 必填**
- select：**key + options 必填**
- toggle：**key 必填**，value 只能是 "true"/"false"/null
- button：**action 必填**
- label：仅需 name
- 所有输入行 key 必须 distinct；所有 button/toggle 的 action 必须 distinct

## 3. 推荐骨架（生产验证版）

**★ 第一铁律：`loginUi(state)` 必须返回 `{"rows":[...]}` 对象包装，绝不能返回裸数组！**
`LoginUiV2.parseRender` 第一步就是 `obj.get("rows")`——裸数组 `[...]` 会让 `GSON.fromJsonObject` 直接失败 → parseRender 返回 null → **对话框打不开（显示"登录UI v2 渲染结果格式错误"）**。这是把 V1"loginUi 返回裸 rows 数组"的习惯带进 V2 最容易犯的错误（260913 hanime1 v2.0 真实翻车：evalLoginUiV2 单测"能返回 24 行"≠能渲染，**必须同时验证对象包装格式**）。

```js
// loginUrl 顶层函数集(压缩成单行, 全源零双引号零反斜杠: Q()=fromCharCode(34))
function loginUi(st){
 st=st||{};
 // 变量回填: state优先,书源变量兜底(source.get 需三态归一化)
 var dom=st.dom||g('h1dom')||'hanime1.com';
 var S1={layout_flexBasisPercent:1};
 var tips = st.msg ? String(st.msg).split('⏎').join(NL()) : '默认说明文字';
 var rows=[];
 rows.push({name:tips,type:'label',style:S1});                    // 顶部消息板
 rows.push({name:'🌐 域名',type:'select',key:'dom',options:['a.com (推荐)','b.com (备用)'],value:dom,style:S1});
 rows.push({name:'✅ 应用选择',type:'button',action:'apply'});
 rows.push({name:'🚀 测速',type:'button',action:'pick',countdown:30});
 rows.push({name:'代理地址',type:'text',key:'px',hint:'http://127.0.0.1:7890',value:g('h1px'),style:S1});
 rows.push({name:'🛜 使用代理',type:'toggle',key:'pon',value:g('h1px')?'true':'false',action:'pxt'});
 rows.push({name:'账号',type:'text',key:'账号',value:g('h1email')});
 rows.push({name:'密码',type:'password',key:'密码'});
 rows.push({name:'🔐 登录',type:'button',action:'login',countdown:12});
 rows.push({name:'✅ 关闭',type:'button',action:'close'});
 return JSON.stringify({rows:rows});   // ★必须是 {rows:[...]} 对象,不是裸数组!
}
function loginAction(act,st,form){
 st=st||{};form=form||{};
 var out={state:st};
 var done=function(msg){if(msg){st.msg=msg}return JSON.stringify(out)};
 if(act==='apply'){ P('h1dom',form['dom'].split(' ')[0]); return done('✅ 已应用') }
 if(act==='close'){ out.close=true; return done('') }
 if(act==='pxt'){
   if(String(form['pon'])==='true'){
     var p=H1N(form['px']);
     if(!p){ out.error={px:'开启前请先填写代理地址'}; return done('⚠️ 未填代理地址') }  // 红字定位
     P('h1px',p); return done('✅ 代理已开启')
   }
   P('h1px',''); return done('⛔ 已关闭')
 }
 if(act==='pick'){ /*测速...*/ return done('结果') }
 if(act==='login'){ /*登录...*/ return done('结果') }
 return done('');
}
```

## 4. 十条踩坑清单（实测）

1. **Kotlin 默认参数 JS 不可省略**：`source.evalLoginUiV2('{}',null,null)` / `evalLoginActionV2(act,state,form,null,null)` 必须传全参，否则"找不到方法"。
2. **规则文本禁真实换行**：多行消息用 `⏎` 占位，渲染时 `.split('⏎').join(String.fromCharCode(10))`。
3. **state 里每个键都要初始化判型**：`typeof st.ip==='string'?st.ip:g('h1ip')`（Rhino 的 Java null/JsNull 是 truthy！）。
4. **button 的 action 与 toggle 的 action 共用 distinct 校验**——动作名全面板唯一。
5. **countdown 只在无 error 时启动**；动作返回 malformed/异常时按钮立即恢复。
6. **label 行 style 用 layout_flexBasisPercent:1** 整行显示长消息。
7. **select 的 value 必须等于 options 之一**，否则落到第一项；自定义值先 unshift 进 options。
8. **putLoginInfo 存 JSON 字符串**（官方 AES+androidId 加密），V2 的 getLoginInfoMap 返回空 map（不解析），回填靠自己读变量。
9. **error 的 key 不在面板时自动降级 toast**——通用错误可直接用。
10. **singleline 压缩器四个续行陷阱**：行尾 `[`/`(` 不补 `;`；下一行 `else/catch/finally/.`/`]`/`)` 开头不补 `;`（否则 `[;`、`} ;catch`、`';].join` 三类语法错）。

11. **★md5 校验双坑（260913 实测裁决）**：①`java.md5Encode(String)` 字符串重载=标准 MD5，但 `java.md5Encode(byte[])` **字节数组重载不是标准 MD5**（"abc"→`d72fda8c...` 而非 `90015098...`）——App 端 md5 校验**必须直接传字符串**，getBytes 路线全错；②JS `String.length` 是 UTF-16 code unit 数，python `len()` 是 code point 数——BMP 外 emoji 每个差 1，**长度对比不可信，以 md5 为准**（hanime1 loginUrl 两端"差 42"实为 42 个 emoji 的幻觉，md5 证明字节级一致）。

## 5. 实战：hanime1 控制台（24 行生产布局）

label(消息板) → 🌐域名select → 🧭hosts select → ✅应用 → 🚀测速(30s) → 📊检测(15s) → 自定义hosts text → 💾存池 → 自定义域名 text → 代理地址 text → 🛜代理toggle → 分隔label → 账号/密码 → 🔐登录(12s) → 💾存账号 → 🚪退出 → 🔍状态(10s) → 分隔label → 📺清晰度select → 🛡过CF盾 → 🔄恢复默认 → ❓帮助 → ✅关闭

配套机制（与面板联动）：
- **header 用 `<js>` 动态生成**：`source.get('h1px')` 非空→注入 `proxy` 键（AnalyzeUrl 原生从 header 提取 proxy，`getProxyClient` 生效；视频播放器同样走——VideoPlay 用 `AnalyzeUrl.headerMap`）。
- **proxy×dnsIp 互斥**：`validateDnsIpProxyCompatibility` 抛异常→jsLib 提供 `H1IPX(src)`（代理开启时返回空），所有 dnsIp 选项经它生成，代理一开 hosts 自动失效。
- **域名/hosts 选择 → source.put 持久化 → URL 模板 `{{H1DOM(source)}}` 二次求值** → 书架自愈（既有机制）。

## 6. 验证方法论

1. node --check 全部 JS 块（26 项）。
2. node 语义仿真：stub java/source/cookie/Packages，全动作断言（36 项，含 loginUi rows 结构/key distinct/action distinct/各 action 的 state/msg/error/close/login 命令）。
3. **App 端 eval_js（绑定书源）**：
   - `source.isLoginUiV2()` = true
   - `source.evalLoginUiV2('{}',null,null)` → **必须验证返回的是 `{"rows":[...]}` 对象**（JSON.parse 后有 .rows 键；裸数组=必崩，对话框打不开）
   - 用 JS 复现 `LoginUiV2.parseRender` 校验：rows 非空 + 每行 isValid（text/password 要 key、select 要 key+options、toggle 要 key 且 value∈{true,false}、button 要 action）+ 输入行 key distinct + button/toggle action distinct
   - `source.evalLoginActionV2(act,'{}','{...}',null,null)` → 逐动作真实网络实测；**再测 state 回传二次渲染**（action 返回的 state 喂回 evalLoginUiV2，模拟对话框 render→action→render 循环）
   - 持久化断言：动作后 `source.get(key)` 回读
   - md5 一致性校验：`java.md5Encode(String(source.loginUrl))`（**字符串重载**，勿用 getBytes）
4. debug_source 全链路回归（搜索/详情/目录/正文）。
5. check_source 官方校验。


## 7. 实战增补（hanime1 v3.4~v3.9 控制台，2026-09-14）

> 这一段是从"38 行视频源控制台"里提炼的**面板设计通用规则**，与站点无关，任何 V2 面板都会再遇到。

### 7.1 ★分支哨兵词冲突（连踩两代）
`applyForm()` 常用选项文案里的关键词做分支判断（`indexOf('自动')`、`indexOf('自定义')`），于是：
- 新选项「🔗 多IP**自动**切换」含"自动" → 误走"清空 hosts"分支（v3.4 现场）；
- 分组标题「──── **自定义**…」含"自定义" → 用户误点分隔行会把备用池第 1 条写进 hosts（v3.6 修复：标题改「我填入的IP」）。
⇒ **规则**：① 分支哨兵用**唯一词**（且只出现在真正可点的选项里）；② 判定顺序显式排：**多值项 → 自动项 → 自定义项 → 单值项**；③ 对读到的值加格式校验（如 `/^[0-9.]+$/` 不过 → 回报"配置无变化"，绝不动线上配置）。分隔 `label` 行必须**不可能被误当成有效值**。

### 7.2 ★多值不能当 select 的 value
底层把多个备用项拼成逗号串（OkHttp 多 IP failover）时，V2 的 `value` 必须是 `options` 之一，否则那一行会显示成一整串脏值。
⇒ 正解 = **分组呈现**：`🔗 多IP自动切换(N) · 当前生效` 代表整组（作为默认选中项），组内每个值再逐条列出（点它=固定单值）。所有条目去重。

### 7.3 状态后缀与解析解耦
下拉项显示 `104.25.254.167 · 123ms` / ` · 不通` / ` · 未测`（延迟表存 `IP:ms;IP:x`，最多 24 条），**取值时 `split(' ')[0]`** ⇒ 显示层与解析层解耦，加后缀零风险。

### 7.4 toggle 当"能力开关"必须三件套
① 写变量（`source.put('h1web','off')`）；② **立即生效路径**（同一变量被规则与面板双向读，键空间相同）；③ **关=可回退的旧实现**（`H1INTRO` 的 `off` 分支走 `H1OLD()` 旧版快照，不是"关掉功能"）。
另：App 重启后 `source.put` 的键（CacheManager，进程内存级）会失效 ⇒ 面板/规则要能自动重探（"首章自动重探"设计）。

### 7.5 密码/账号回填：三源兜底 + 用户意图优先
`state内存 → source变量 → source.getLoginInfo()`（**本版本 getLoginInfo 返回可逆 AES(androidId) 解密后的原文 JSON**，键名=RowUi 的 `name`，如 `账号`/`密码`）；**用户在面板里显式清空过的（state 里已是字符串）不要被存储值覆盖**，否则"清空"永远清不掉。登录成功的两个分支（真登录 / 本来就已登录）都要自动 `putLoginInfo`，别依赖用户手点"💾保存"。

### 7.6 危险动作 = countdown + 文案劝退
测速类按钮会连发十几个请求（视频/小说站常有 CF 或 WAF）⇒ 一律 `countdown:30~90`，提示语直接写"不急就别点"。全量测速用**最轻的探测目标**（`/robots.txt` 几十~几百字节）而不是首页（几百 KB）。

### 7.7 消息板与换行
`st.msg` 用自定义分隔符（本项目用 `⏎`）再 `split(⏎).join(NL())`，**不要把真实换行写进 JS 字符串字面量**（多层转义必坏）。错误回报优先塞 `st.msg` + `error:{key:…}` 定位到输入框红字。

### 7.8 一次"跨版本行为"提醒（V2 相关）
V2 面板渲染在 LegadoTeam 与 legado-E/Lyc 上 `RowUi` 字段基本一致，但**桥能力**不同（`startBrowser` 注解差异、`NativeObject` 条目协议差异）⇒ 面板里按钮调用的函数要 `typeof` 探测 + 显式降级提示。跨版本差异详见 `方法-legado各版本行为差异对照.md`。

---

## 8. 两条"真机才暴露"的 V2 致命坑（iwara v3→v4，2026-09-15）

### 8.1 ★jsLib 里的 `java` 不是 Legado 的 java，是 **Rhino 内置 JavaPackage**

`BaseSource.evalJS()`：jsLib 在 **SharedJsScope** 求值，`loginUrl` 在带绑定的子作用域求值
（`bindings["java"]=…` 然后 `chainTo(sharedScope)`）。于是同一个标识符在两层里是不同东西：

| 作用域 | `java` 是什么 | `typeof java` | `typeof java.ajax` |
|---|---|---|---|
| loginUrl / 规则 `@js:` | Legado JsExtensions（能联网） | object | **function** ✔ |
| **jsLib 函数体内** | Rhino `JavaPackage(java)` | object | **object**（`java.util` 那个味道的包对象）✘ |

后果最阴险的一点：把 jsLib 里读到的 `java` 当参数往下传（`IWRLAT(java,Sv)`），
`Jv` 非空、`if(!Jv)` 判不出来，但 `Jv.ajax()` 抛 TypeError → 被 `try/catch` 吞成 `''` →
**6 个 IP 的"测速"在 17 毫秒内全部报"不通"**。同理 `source` 在 jsLib 里是 `null`（见 §7.5 前身）。

**三条纪律**

1. jsLib 里**禁止**用自由变量拿能力对象：`java / source / result / book / chapter / cache / cookie`
   一律由上层（loginUrl 函数、规则 `@js:`）**显式形参注入**。
   ```js
   // loginUrl（这层的 java/source 是真绑定）
   function loginUi(st){return UI(st,source);}
   function loginAction(act,st,form){return ACT(act,st,form,source,java);}  // ← 两个都要注
   ```
2. 注入后**校验能力真实存在**，别只判真假：
   ```js
   function JW(){try{var j=java;if(j&&typeof j.ajax=='function'){return j;}}catch(e){}return null;}
   function JVC(Jv){if(Jv&&typeof Jv.ajax=='function'){return Jv;}return JW();}
   ```
3. 网络动作**集中前置守卫 + 明确文案**，宁可报"内部错误：无网络能力"，也不要让它伪装成"站点不通"：
   ```js
   var NET={pick:1,testimg:1,testmh:1,login:1,status:1,refresh:1,favlist:1};
   if(NET[act]&&!Jv){return done('⚠ 内部错误：登录面板未获得网络能力（java.ajax 不可用），请反馈截图');}
   ```

### 8.2 ★带 `key` 的行一旦发了 `value`，就会**盖掉用户正在输入的内容**

```kotlin
// LoginUiV2.kt
fun resolveFieldValue(renderValue, sessionInput, stored) = renderValue ?: sessionInput ?: stored
```
Kotlin 的 `?:` **只对 null 短路**，`value:""`（空串）是"有值"⇒ 优先级最高。
`jsHelp.md` 也写明回填顺序 = **行内 value → 本次弹窗输入 → 已保存登录信息**。

典型翻车：面板里 `{key:'账号',type:'text',value:IWRG(Sv,'iwEm','')}`，而 `iwEm` 只在登录**成功**时写；
用户填好账号点【登录】→ 登录失败 → 返回 `state` 触发重渲染 → `value:''` 把刚输入的内容抹平
（用户视角＝"我一按登录，账号数字就自己消失了"）。**自定义 hosts、播放域名等所有文本框同病。**

**解法：把"本次输入"暂存进 state，按"用户输入优先（含主动清空）"出值。**

```js
// ① ACT() 顶部：每次动作 App 都会把全量 form 传进来，直接暂存
if(!st.v){st.v={};}
for(var fk in form){ if(form[fk]===undefined||form[fk]===null){continue;} st.v[fk]=STR(form[fk]); }

// ② UI() 出值：state.v 有就用（可能是''，那正是用户想要的），否则用已存值
function RFV(st,k,def){try{if(st&&st.v&&st.v[k]!==undefined&&st.v[k]!==null){return String(st.v[k]);}}catch(e){}
  return (def==null)?'':String(def);}
R.push({name:'邮箱',type:'text',key:'账号',value:RFV(st,'账号',em),hint:'…',style:S1});
```
**能不发现场就别发**：若不需要"主动清空"语义，最省事的做法是**干脆不写 `value`**，
让 App 走 `sessionValues → loginInfo` 的官方兜底（登录成功返回 `login:{账号:…,密码:…}` 命令，
App 会自己加密保存并在重开面板时按 key 回填）。

### 8.3 `select` 的 value 必须 ∈ options，否则被复位成第一项

```kotlin
val value = resolveFieldValue(row.value, sessionValues[key], stored[key])?.takeIf { it in options } ?: options.first()
```
选项标签里嵌了实测延迟（`1.2.3.4 · 971ms` → 测速后变 `1.2.3.4 · 1030ms`）会让历史标签失配 ⇒ 下拉跳回第一项。
解法：出值前做**前缀回映射**（显示层与解析层用空格切开，见 §7.3）：
```js
function SEL(st,k,opts,def){var w=RFV(st,k,''),i,hd;
  if(w!==''&&opts&&opts.length){ for(i=0;i<opts.length;i++){if(opts[i]===w)return w;}
    hd=w.split(' ')[0]; if(hd!==''){for(i=0;i<opts.length;i++){if(opts[i].indexOf(hd)===0)return opts[i];}}}
  if(def&&opts&&opts.length){ for(i=0;i<opts.length;i++){if(opts[i]===def)return def;}
    hd=String(def).split(' ')[0]; if(hd!==''){for(i=0;i<opts.length;i++){if(opts[i].indexOf(hd)===0)return opts[i];}}}
  return (opts&&opts.length)?opts[0]:'';}
```

### 8.4 ★V2 面板的"真机复验"根本不用麻烦用户点屏幕

`eval_js` 与 V2 委托走同一个 `BaseSource.evalJS`（实测 `source===java` 为 true），
所以可以在设备上直接驱动官方调用链（Kotlin 默认参数必须传全）：

```js
source.evalLoginActionV2('testimg','{}','{}',null,null);       // → {state:{msg:…}}
source.evalLoginUiV2(JSON.stringify(state),null,null);          // → {rows:[…]}
// A/B 定身法：同一条函数，一次走真实通道、一次显式传真 java
var t0=new Date().getTime();
var viaPanel=JSON.parse(source.evalLoginActionV2('testimg','{}','{}',null,null)).state.msg; // 17ms → java 是假的
var viaDirect=IWRTIMG(java,source);                                                          // 18530ms → 真结果
```
**教训**：v3 交付时"测速选线 ✅"只做了 node 仿真——仿真的 `java` 是真对象，**jsLib 作用域 bug 仿真不出来**。
带面板的书源，交付前必须补一轮 `evalLoginActionV2` 真机复验（每个 action 一次，读 `state.msg`）。

### 8.5 构建脚本自检三件套（本次抓到两类笔误）

1. **花括号/引号配平扫描**（字符串 + 正则字面量感知）：手写 JS 块最容易 `}}}` 多数一个、
   或把 `break` 留在 `for` 外面（node 只会把整条压缩长行回显，定位极慢；配平扫描直接指出下溢偏移）。
2. `node --check` 全部 JS 块（jsLib/loginUrl/每条 `@js:`、`<js>`）。
3. **双作用域仿真**：node `vm` 里用 `(function(java,Packages,source,cache,cookie,result,baseUrl){…jsLib…})(bogusJava,{},{},…)`
   求值 jsLib（模拟 SharedJsScope：java=无 ajax 的假包、source=null），再把函数名搬进
   带真 stub 的外层 context 跑 loginUrl/loginUi/loginAction —— 能离线复现 8.1 的秒失败。
