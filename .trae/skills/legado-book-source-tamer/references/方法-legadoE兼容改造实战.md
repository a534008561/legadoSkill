# 方法：书源 legado-E 兼容改造实战（数组面板 / 列表协议 / 缺失API）

> **适用**：书源在 LegadoTeam（LT）上正常，用户换到 **legado-E**（Luoyacheng/legado-E，即"阅读Sigma"）后出现
> 「**登录界面打不开（空白）** / 列表大小正常但**字段全空** / 目录获取失败 / 按钮点了没反应」等问题。
>
> **蓝本**：hanime1.me 视频书源 v3.14 → v3.14E（2026-09-21）。
>
> **核心心法**：E 版 = 官方基线 + 部分增强，**它不认 LT 版独有的 V2 登录面板**。
> 真正必须改的只有两件事：**① loginUi 必须是数组** ② **列表字段必须是纯键名**；
> 其余（缺 API 兜底 / Cookie 单键删除 / get 双通道）属于**防御性兼容**，顺手做掉即可。

---

## 0. ★★ 第一条铁律：拉源码必须先确认默认分支！

本次踩的最大坑：**用 `master` 分支拉 Luoyacheng/legado-E 的源码 → 拉到的是旧版**，
导致 8 项结论完全错误（误判"E 版不支持 useweb / video / dnsIp / openVideoPlayer"），
差点把用户的 useweb 简介面板错误地降级成纯文本。

```python
# ✅ 正确姿势
r = GET https://api.github.com/repos/{owner}/{repo}
br = r['default_branch']          # ← Luoyacheng/legado-E 的默认分支是 main，不是 master！
# 再按 br 拉文件
GET https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={br}
```

**教训**：
- `raw.githubusercontent.com/.../master/README.md` **能拉成功 ≠ master 是默认分支**（旧分支也在）
- 分支间差异可能极大：本例 `SourceLoginDialog.kt` **master=7.7KB vs main=34KB**（4.5 倍）
- 交叉验证：用 **GitHub code search** 搜关键词（如 `"useweb>"`）——若命中某文件而本地拉的文件里没有，
  **说明你拉的分支/版本不对**，立刻回头查默认分支
- jsdelivr 缓存的是**默认分支**内容（`@master` 会拉到 master），但**没有 `@main` 时也需显式指定**

---

## 1. E 版真实能力（main 分支，逐条源码核对 2026-09-21）

| 能力 | E 版 main | E 版 master（旧） | 说明 / 源码位置 |
|---|---|---|---|
| **loginUi 形态** | **数组**（`GSON.fromJsonArray<RowUi>`） | 数组 | ★`{"version":2}` 两版都不认 → 面板空白（`SourceLoginDialog.onFragmentCreated`） |
| `<js>`/`@js:` 动态 loginUi | ✓ | ✗ | main 有 `evalUiJs(codeStr)` |
| RowUi 字段 | **7**：`name/type/action/chars/default/viewName/style` | 4：`name/type/action/style` | main 的 `equals` 只比 name/type/action/default |
| 面板控件类型 | text/password/button/**toggle/select** | text/password/button | 旧版对未知 type **静默跳过** |
| 按钮 action 执行 | `evalJS(loginJs+"\n"+action){ put("result", getLoginData()) }`，**runCatching 吞返回值** | 同 | → 结果必须自己 `java.longToast` |
| ✓ 按钮 | `putLoginInfo(...)` → `source.login()`；**不注入 result** | 同 | → `login()` 用 `getLoginInfoMap()` 兜底 |
| **useweb / usehtml 简介** | **✓** | ✗ | `BookInfoActivity`: `if (intro?.startsWith("<useweb>")) { WebViewPool.acquire(...) }`；`<usehtml>` 分支另有 |
| **onButtonClick** | **✓** | ✗ | `BookInfoViewModel.onButtonClick`: `SourceLoginJsExtensions(activity, source)` + `put("java"/"book"/"result")` |
| **BookType.video=4** | **✓** | ✗（仅 0/1/2/3） | `BookSourceType.video=4` 也在 |
| **UrlOption.dnsIp** | **✓** | ✗ | `AnalyzeUrl`: `dnsIp` → `customIp[urlNoQuery]` |
| `subContent`（歌词/弹幕） | ✓ | ✗ | `BookContent`: `isAudio→putLyric` / `isVideo→putDanmaku` |
| `callBackJs` / `eventListener` | **✗** | ✗ | E 版两版都无 → 正文切P跟随失效（字段保留无害） |
| **列表条目字段协议** | NativeObject → **键名直取** `result[规则文本]`；另有 `LinkedTreeMap` 分支 | 同 | ★**`@js:` / `$.x` 都取不到 → 字段必须纯键名** |
| `getElements` 返回值 | 需 JS 数组 | `it as List<Any>`（String 抛异常） | 返回 JSON 字符串在 E 版会抛异常 |
| `cookie.removeCookie(url,key)` | **✗**（只有一参） | ✗ | 单键删除要 get 全文→删键→setCookie 回写 |
| `copyText` / `refreshBookInfo` / `refreshTocUrl` / `md5Encode` | **✗** | ✗ | 调用点必须 try/catch |
| `openVideoPlayer` | **✓** | ✗ | |
| `get/head/post` | **3 参**（带 timeout） | 2 参 | 两版通用写法：`try{3参}catch{2参}` |
| `exploreUrl`/`header` 的 `<js>` | ✓（发现页结果存 ACache，key=md5(bookSourceUrl+exploreUrl)） | ✓ | 改配置后需「刷新发现页」 |
| URL 的 `{{}}` 二次求值 | ✓（绑定含 source） | ✓ | `{{H1DOM(source)}}` 可用 |
| `getSubDomain('https://x.com##标记')` | = `x.com` | 同 | **`##后缀` 做"同站第二源"安全**（getKey 不同→变量隔离） |

---

## 2. 真正必须改的两件事

### 2.1 loginUi：`{"version":2}` → **数组**

E 版**没有** `isLoginUiV2()`，直接 `GSON.fromJsonArray<RowUi>(loginUi)`。
LT 版的 V2 面板（`{"version":2}` + `loginUi(state)`/`loginAction(action,state,form)`）在 E 版**必然解析失败 → 面板空白**。

**改造**：把 V2 骨架换成数组 + 薄分发函数。

```jsonc
// loginUi（数组；E 两版都能解析；只渲染 text/password/button 最保险）
[
 {"name":"❓ 帮助 / 使用说明","type":"button","action":"H1V1('help',java,source)","style":{"layout_flexBasisPercent":1}},
 {"name":"──── 🌐 选择域名（点一下即切换） ────","type":"button","action":"java.longToast('点①~④直接换域名')"},
 {"name":"① hanime1.com (推荐)","type":"button","action":"H1V1('dom0',java,source)"},
 {"name":"② hanime1.me (主域)","type":"button","action":"H1V1('dom1',java,source)"},
 {"name":"🔍 查看当前域名/配置","type":"button","action":"H1V1('curcfg',java,source)"},
 {"name":"自定义域名","type":"text"},
 {"name":"hostsIP","type":"text"},
 {"name":"代理地址","type":"text"},
 {"name":"✅ 应用以上配置","type":"button","action":"H1V1('apply',java,source)"}
]
```

**V1 面板硬约束**（旧分支 E 也只认这些）：
1. `type` 只用 `text`/`password`/`button`（toggle/select 在新版 E 可用，但旧版静默跳过 → **按钮 = 两版通用**）
2. 分区标题用 `button` + **inline JS**（`java.longToast('...')`）—— 不要空 action，也不要用 label
3. 输入框 `name` **既是提示也是回填键**（E 版 `loginInfo?.get(rowUi.name)`）→ 名字定了就别改
4. 输入框**没有** `value` 字段 → 想回填只能 `putLoginInfo()`
5. 按钮 `action` 是一段 JS（运行于 `loginJS + "\n" + action`，java/source 已绑定、jsLib 可见）
6. **不要**靠 action 的返回值更新 UI —— 被 `runCatching` 吞掉，反馈全靠 `longToast`

### 2.2 列表字段：`@js:` → **纯键名**

E 版 `AnalyzeRule` 对 NativeObject 条目走「**键值直接访问**」：`result[规则文本]`，且只取 `ruleList.first()`。

```
原写法（LT 版可用 / E 版取到 undefined → 条目被丢 → "书籍总数:1"）：
  author   = @js:String(result.artist||'')
  bookUrl  = @js:H1BU(String(result.v))
  coverUrl = @js:H1FIX(source,String(result.cover||''))
  kind     = @js:(function(){...拼接...})()

兼容写法（两版通用）：
  # 列表 JS 里把「需要计算」的字段预生成好
  out.push({title:t, artist:art, v:v, u:H1BU(v), cover:H1FIX(src,cv), kind:kk.join(' ')});
  return out;                      # ★返回 JS 数组（不是 JSON.stringify）
  # 字段规则只剩纯键名
  name='title' author='artist' bookUrl='u' coverUrl='cover' kind='kind'
```

> **备选方案**：条目改成 `String(JSON.stringify(item))`（JSON 字符串数组）+ 字段规则 `$.name`（走 Mode.Json）。
> 两版也通用，但**改动更大**（列表函数要改），且 LT 版 `getElements` 对 String 有历史坑。
> **二选一，不要混用**（`$.x` 配 NativeObject 在 E 版必挂）。

### 2.3 顺手的防御性兼容（对旧分支 E 也有用）

```js
// ① Cookie 单键删除（E 版无 removeCookie(url,key)）
function rmck(u,k){
  var ok=false; try{ cookie.removeCookie(u,k); ok=true }catch(e){}
  if(!ok){ try{ var c=String(cookie.getCookie(u)||''), arr=c.split(';'), out=[];
    for(var i=0;i<arr.length;i++){ var s=H1N(arr[i]); if(!s){continue}
      var p=s.indexOf('='); var kk=(p>0?H1N(s.substring(0,p)):''); if(kk&&kk!==k){out.push(s)} }
    cookie.setCookie(u,out.join('; ')) }catch(e2){} }
}
// ② get 三参/两参双通道（E master 只有 2 参）
var r=null; try{ r=Jv.get(s,null,20000) }catch(e0){ try{ r=Jv.get(s,{}) }catch(e1){ return '' } }
// ③ 缺失 API 一律 try/catch（copyText / refreshBookInfo / openVideoPlayer ...）
// ④ 面板配置回填：合并写 loginInfo（不清账号密码）
function h1uiSave(Sv,extra){
  var m={};
  try{ var lm=Sv.getLoginInfoMap(); if(lm){ var it=lm.keySet().iterator();
       while(it.hasNext()){ var k=String(it.next()); var v=lm.get(k); m[k]=(v==null?'':String(v)) } } }catch(e){}
  if(extra){ for(var k2 in extra){ var v2=extra[k2]; if(v2!==undefined&&v2!==null){ m[k2]=String(v2) } } }
  try{ Sv.putLoginInfo(JSON.stringify(m)) }catch(e){}
}
```

---

## 3. "选择域名"按钮怎么做（V1 面板没有下拉）

需求场景：站点有多个镜像域（如 hanime1 的 `.com/.me/hanimeone.me/javchu.com`），
原版 V2 面板用 `select` 下拉，**E 版旧分支不渲染 select** → 改成**一排按钮**：

```python
btn("① hanime1.com (推荐)", "dom0"),
btn("② hanime1.me (主域)", "dom1"),
btn("③ hanimeone.me (备用)", "dom2"),
btn("④ javchu.com (JAV站)", "dom3"),
btn("🔍 查看当前域名/配置", "curcfg"),
```
```js
else if(act==='dom0'||act==='dom1'||act==='dom2'||act==='dom3'){
  var di=parseInt(String(act).substring(3),10); if(isNaN(di)){di=0}
  var nd=String(DOMS[di]||'hanime1.com');          // DOMS 在 loginUrl 顶层定义
  P('h1dom',nd); st.dom=nd;                         // 立即生效（无需再点"应用"）
  h1uiSave(Sv,{'自定义域名':nd});                    // 让输入框下次打开显示当前域名
  r='🌐 域名已切换: '+nd+NL+'书架/搜索/发现即时生效';
}
else if(act==='curcfg'){                            // 状态回显（V1 无法动态改按钮文字）
  r='【当前配置】'+NL+'🌐 域名: '+(g('h1dom')||'hanime1.com')+NL+'🧭 hostsIP: '+(g('h1ip')||'(自动)')+...;
}
```

**要点**：
- V1 按钮名是**静态文本**（`it.textView.text = rowUi.name`）→ **无法显示"当前选中"**，
  所以必须配一个「查看当前配置」按钮做状态回显
- 点击即写变量 + `h1uiSave` 回填输入框 → 用户下次打开面板能看到当前域名 ✓
- 若同时保留「自定义域名」输入框，注意**按钮点击会覆盖它**（设计上合理）

---

## 4. 改造五步法

1. **判定**：先问用户用哪个版本/哪个 App；在目标 App 里 `eval_js` 探针
   （`typeof source.isLoginUiV2` → function 说明是 LT；E 版没有）
2. **建独立源**：`bookSourceUrl = 原URL + '##E兼容版'`（getKey 不同 → 变量/缓存隔离，**不覆盖原源**）
3. **loginUi 数组化**：V2 骨架 → 数组 + `H1V1(act,Jv,Sv,m)` 薄分发（业务逻辑全部留在原函数里）
4. **列表字段纯键名**：计算搬进列表 JS 预生成
5. **防御性兼容**：`rmck` / `get` 双通道 / 缺失 API try / `h1uiSave` 回填

---

## 5. 验证方法论（三层）

### 第 1 层 · 静态契约（秒级，Python）
- `node --check` 每个 JS 块（jsLib/loginUrl/exploreUrl/header/loginCheckJs/所有 `@js:` 规则）
- loginUi：行数 / type 白名单 / 按钮均有 action / 输入框均有 name / **每个 action 都有分发分支**
- 列表字段：断言**无** `@js:` 与 `$.` 前缀
- 缺失 API 调用点：扫 `\.(copyText|refreshBookInfo|...)(` 前 160 字符内是否有 `try{`
- `get/post/head` 参数个数扫描
- **原版 vs 兼容版逐字段 diff**：确认"应保留项"逐字节不变

### 第 2 层 · 真实 App 实测（MCP）
- 导入后 **逐字段回读 md5 比对**（差异通常只有 `customOrder` = App 自动排序号）
- `check_source` 官方校验
- `debug_source` 全链路：搜索 / 详情 / 目录 / 正文 / 发现（`::URL`）
- **面板契约**：`source.isLoginUiV2()` 应为 false；`getLoginUiJs()` 为 null → 两版都走数组渲染
- **按钮点击精确模拟**（不点 UI）：
  ```js
  var lu=String(source.getLoginJs()), ui=JSON.parse(String(source.loginUi));
  var act=String(ui[IDX].action);
  String(eval(lu+"\n"+"var result={'自定义域名':'x'};"+"\n"+act));   // 返回=面板提示文案
  ```
- **纯键名取值等价验证**：`new AnalyzeRule()` + `setContent(条目)` + `getString('title')`
  （注意 `new AnalyzeRule()` **不注入 jsLib**，列表规则本身要另测）

### 第 3 层 · 源码级契约（E 版无法直测时）
MCP 连的往往是 LT 版 → E 版行为只能**拉源码核对**（**记得先看默认分支！**），
并用"等价模拟"证伪/证实（如：同一条目同时取 `title` 与 `@js:String(result.artist)`，后者 undefined 即证差异真实存在）。

---

## 6. 避坑清单

| # | 坑 | 症状 | 解法 |
|---|---|---|---|
| **K0** | **拉源码用错分支（master vs main）** | 结论全错（如误判不支持 useweb） | **先 `GET /repos/{o}/{r}` 看 `default_branch`**；用 code search 交叉验证 |
| K1 | `loginUi={"version":2}` | E 版面板**空白**（无报错） | 改数组 |
| K2 | 用了 label/select/toggle | 旧版 E 里那些行**静默消失** | 只用 text/password/button |
| K3 | 按钮 action 只 `return 'msg'` | 点了没反应（runCatching 吞） | 自己 `java.longToast()` |
| K4 | `login()` 只读 `result` | ✓ 按钮无反应（E 不注入 result） | `getLoginInfoMap()` 兜底 |
| K5 | 列表字段 `@js:` / `$.x` | 列表大小正常但**字段全空** → "书籍总数:1" | 纯键名 + 列表内预生成 |
| K6 | 列表规则 `return JSON.stringify(arr)` | E 版 `as List<Any>` 抛异常 | `return` JS 数组 |
| K7 | 字段规则用管道 `a\|\|b@x` | NativeObject 分支只取 first | 单段纯键名 |
| K8 | `cookie.removeCookie(u,k)` | 退出登录清不掉 | `rmck()` |
| K9 | `Jv.get(u,null,20000)` | E master "找不到方法 get" | 3参/2参双通道 |
| K10 | `java.copyText/refreshBookInfo` | 抛异常 | `try/catch` + 降级提示 |
| K11 | V1 按钮名想显示"当前值" | 静态文本改不了 | 加「查看当前配置」按钮回显 |
| K12 | 面板输入框没有 `value` | 打开是空的 | `h1uiSave()` 写 `putLoginInfo` |
| K13 | `removeLoginInfo()` 清不掉回填 | 面板仍显示旧值 | 用 `putLoginInfo('{}')` |
| K14 | jsLib 无参函数靠闭包读 `source` | 静默失败 | **显式传参** |
| K15 | jsLib/loginUrl 顶层 `const/let` | "重新声明了常量" | 只用 `var/function` |
| K16 | 在 `eval_js` 里 `eval(loginUrl)` 后调函数 | "xxx 未定义" | **同段脚本内 eval + 调用** |
| K17 | 直接改原源 | LT 版功能被降级 | **新建 `##兼容版`** |
| K18 | 改 `exploreUrl` 后不生效 | ACache 缓存 | 「刷新发现页」（key 含 bookSourceUrl） |
| K19 | 期待 `callBackJs` | E 版两版都无 → 切P跟随失效 | 保留字段（LT 生效），文档说明 |
| K20 | 改完不重新导入 | 测的还是旧版 | 更新 `lastUpdateTime` + 重新 dpaste 深链导入 |

---

## 7. 案例档案

| 书源 | E 版版本 | 主要改造 | 结果 |
|---|---|---|---|
| **hanime1.me v3.14E** | main（支持 useweb/video/dnsIp） | loginUi 数组化 43 行（含一键选域名按钮 + 当前配置回显）；列表字段 12 处纯键名；`H1CARDS` 预生成 `u/cover/kind`；`rmck`；`get` 双通道；**简介保持原版 useweb 未降级** | check_source 1/1；搜索59/详情(useweb面板)/目录/正文/发现全通；导入回读 28/29 字节级；域名按钮 4 个 + 配置回显实测通过 |
| iwara（历史） | master（旧） | V1 面板 24 行 + `IWRV1(act,Jv,Sv,m)` | 面板可用 |

---

## 8. 一句话口诀

> **先确认默认分支再拉源码；面板降到数组（text/password/button + longToast 自报结果 + 按钮代替下拉）；字段只留纯键名（计算搬进列表 JS）；缺的 API 全兜底；另起 `##兼容版` 不覆盖原源。**
