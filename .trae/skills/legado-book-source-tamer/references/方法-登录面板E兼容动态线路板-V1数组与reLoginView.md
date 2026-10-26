# 方法：登录面板 E 兼容动态线路板（V1 `@js:` 数组 + `reLoginView`）

> 沉淀来源：黄果短剧 v7e（2026-10-27）。需求：发布页输入框默认填好 →
> 点「一键获取网址并测速」→ 测速结果**以按钮形式列在发布页下面** →
> 点某按钮即应用该线路并 toast「已选择网站：xxx / 延迟：Nms」。
> 约束：**不用 V2 面板，必须兼容 legado-E**。

---

## 0. 为什么不能走 V2

| | V1 经典 | V2 `{"version":2}` |
| --- | --- | --- |
| LT 版 | ✅ | ✅ |
| **legado-E** | ✅ | ❌ **面板空白**（`fromJsonArray` 失败） |
| 动态按钮 | ✅ `@js:` 返回数组 | ✅ `state.rows` |
| 重建面板 | `java.reLoginView(true)`（E）/ `java.reUiView(true)` | 返回 `state` 自动重渲染 |
| label 行 | ❌ **E 不渲染 label** | ✅ |

E 版 `SourceLoginDialog` 只吃 V1 数组，且 **`label` 类型不渲染**——
所以分隔行/状态行必须用 `text` 占位。

⇒ 要跨版本就用 V1 动态数组。

---

## 1. 三段式结构

```javascript
// loginUrl 顶层（LT/E 都靠拼接 eval 看到这些函数）
function hgRows(){ ... return JSON.stringify(rows) }   // 动态面板
function hgGo(){ ... }                                  // 抓发布页 + 测速 + 写盘
function hgPick(i){ ... }                               // 应用第 i 条
```

```json
"loginUi": "@js:hgRows()"
```

- `@js:` 前缀后全部文本当代码执行，**返回值就是 rows 数组**
- E 版：`evalJS(loginUrl + "\n" + "hgRows()")`
- LT 版：同链路
- 每次打开面板重新求值 ⇒ 天然反映最新变量

---

## 2. `hgRows()` 的硬约束（E 版 `isValid` + viewName 规则）

```javascript
function hgRows(){
  var rows=[];
  rows.push({name:'st',type:'text',viewName:"'· 状态 ·'",value:tip,action:'hgNoop1',
             style:{layout_flexBasisPercent:1}});
  rows.push({name:'pub',type:'text',viewName:"'发布页地址'",
             value:hgGV('pub',HG_PUB),style:{layout_flexBasisPercent:1}});
  rows.push({name:'go',type:'button',viewName:"'一键获取网址并测速'",
             action:'hgGo',style:{layout_flexBasisPercent:1}});
  // 测速结果按钮（按延迟升序）
  var arr=JSON.parse(hgGV('hg_sites','')||'[]');
  if(arr.length){
    rows.push({name:'sep',type:'text',viewName:"'— 测速结果 · 点按应用 —'",
               value:'',action:'hgNoop2',style:{layout_flexBasisPercent:1}});
    for(var i=0;i<arr.length;i++){
      var lbl=hgShort(arr[i].host)+' '+arr[i].ms+'ms';
      rows.push({name:'s'+i,type:'button',viewName:"'"+lbl+"'",
                 action:'hgPick('+i+')',style:{layout_flexBasisPercent:0.32}});
    }
  }
  return JSON.stringify(rows)}
```

### 三条铁律

1. **`viewName` 必须是 3..19 字符且首尾单引号**（字面量），否则走异步 `evalUiJs`
   → 站点名必须截断：`function hgShort(h){h=String(h||'');var d=h.split('.');var t=d[0]||h;if(t.length>13)t=t.substring(0,13);return t}`
   - `'thu 1256ms'` = 12 ✅
   - `'thu.arj2ftl0.cc  1256ms'` = 25 ❌
2. **action 必须全面板 distinct**（含 text 行的 action）——两个 `noop` 会被判重
   ⇒ 用 `hgNoop1` / `hgNoop2`
3. **E 版不渲染 `label`** ⇒ 分隔行用 `type:'text'` + `value:''`

---

## 3. `reLoginView(true)` 是 E 专属重建通道

```javascript
function hgGo(){
  ...
  hgSV('hg_sites',JSON.stringify(rows));      // 写盘
  hgSV('hg_line',rows[0].url);                // 自动选最快
  hgT('测速完成...');
  try{java.reLoginView(true)}catch(e){}       // ★ 重建面板刷新按钮
}
function hgPick(i){
  var arr=JSON.parse(hgGV('hg_sites','')||'[]');
  if(!arr[i]){ hgT('该线路已失效，请重新点「一键获取网址并测速」'); return }
  hgSV('hg_line',arr[i].url);
  hgT('已选择网站：'+arr[i].host+hgNL()+'延迟：'+arr[i].ms+'ms');
  try{java.reLoginView(true)}catch(e){}
}
```

- **`reLoginView(deltaUp)` 重跑动态 `loginUi` 并重建面板** —— 点选后刷新按钮文字/数量就靠它
- 必须 `try/catch`：LT 版是 `java.reUiView(true)`（发现页用），登录面板的 `reLoginView` 可能不存在
- **toast 必须在 action 内自己做**：E 版按钮 action 的**返回值被忽略**，`source.evalJS(loginUrl+"\n"+action)` 不取回值

---

## 4. 变量承载：`source.put/get` 而非 state

V2 用 `state` 传面板内存；**V1 没有 state**，动态数据必须落 `source.put`：

```
pub        发布页 URL（用户可改）
hg_sites   JSON 数组 [{url,host,ms}]，最多 12 条
hg_line    当前生效线路
hg_line_ts 时间戳（TTL 3 分钟，供 searchUrl 模板读）
```

**坑**：`source.getVariable()` / `setVariable()` 与 `source.get/put` 是两套。
`get/put` 是 CacheManager 持久化（跨会话），`getVariable/setVariable` 是 BookSource.variable。
本例用 `get/put`。

---

## 5. App 内预演方法（eval_js）

```javascript
// 1. 确认 V1 形态
String(source.isLoginUiV2())    // 必须 "false"

// 2. eval loginUrl 再调 hgRows（eval_js 环境已注入 source/java）
var js=String(source.getLoginUrl());
eval(js);
JSON.parse(hgRows())            // → 数组，逐行断言

// 3. 断言清单
//    - Array.isArray(a)
//    - viewName 3..19 且首尾单引号
//    - action distinct
//    - name 非空
//    - pub 行 value = 默认发布页
//    - 有 hg_sites 时出现 N 个 site 按钮且 action=hgPick(i)
```

> ⚠️ **`source.evalJS(str, null)` 会 NPE**（`vu.l` 要非 null）；
> `evalJS(str,'')` 报「找不到方法 (string,string)」。
> eval_js 里预演请直接 `eval(source.getLoginUrl())` 后调函数。

---

## 6. 实测数据（黄果短剧 v7e）

```
发布页抓取：58 条线路（19 子域 × 3 根域 + 默认）
真实测速：87.2s，可用 12 条
最快：thu.arj2ftl0.cc 1256ms
面板行数：初始 6 行 → 测速后 11 行（4 站点按钮）
点 s2 → hg_line=https://nju.40ygo615.cc + toast「已选择网站：nju.40ygo615.cc / 延迟：1406ms」
重建后面板仍 11 行 / 4 个站点按钮
```

---

## 7. Checklist

```
[ ] loginUi = "@js:函数名()"（不是 {"version":2}）
[ ] source.isLoginUiV2() === false
[ ] 分隔/状态行用 text 不用 label（E 不渲染 label）
[ ] 所有 viewName 3..19 且首尾单引号（站点名截断）
[ ] 所有 action distinct（noop 也要唯一化）
[ ] 每个 action 内自 try/catch + java.longToast（返回值被忽略）
[ ] 写盘用 source.put/get，不用 state
[ ] 状态变化后 try{java.reLoginView(true)}catch(e){}
[ ] 动态数据 JSON 存 source.put，解析要 try/catch
[ ] node vm 沙盒断言 + App 内 eval_js 预演 + check_source
```

---

## 8. 关联

- `方法-legadoE登录面板V1动态与发现页点选化.md`：E 版能力表总纲、`reLoginView` 首次沉淀
- `方法-登录UI-V2新版面板.md`：V2 协议（LT only）
- `方法-发布页线路轮换与登录界面测速选线.md`：线路池通用方案
