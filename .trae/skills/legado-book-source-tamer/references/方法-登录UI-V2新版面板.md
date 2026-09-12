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
 return JSON.stringify(rows);
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
   - `source.evalLoginUiV2('{}',null,null)` → JSON.parse 校验 rows
   - `source.evalLoginActionV2(act,'{}','{...}',null,null)` → 逐动作真实网络实测（status/login/check/pick/apply/pxt/exit/reset/help/close）
   - 持久化断言：动作后 `source.get(key)` 回读
4. debug_source 全链路回归（搜索/详情/目录/正文）。
5. check_source 官方校验。
