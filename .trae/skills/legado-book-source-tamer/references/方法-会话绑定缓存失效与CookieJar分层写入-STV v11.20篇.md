# 方法：会话绑定缓存的失效与 CookieJar 分层写入 — STV v11.20 篇

> 2026-11-13 · 蓝本：STV[api_1]（sangtacviet.vip）v11.19 → **v11.20**
> 本文是《方法-抓包驱动的官方App行为对齐-STV篇》§15（v11.19 登录态双通道）的**续篇**，独立成篇，不改动主文档。
> 验证：App 内 eval_js 对照实验 + get_http_logs 请求链证据 + debug_source 全链路 + check_source 1/1。

## 0. 一句话总结

**「点同步没用、必须杀进程重开才好」几乎总是内存态缓存的信号**：缓存复用判据只盯了一个不会随登录态变化的字段，
而重开进程恰好清空了那一层内存会话数据，被动触发了重算。修法不是让用户重启，而是让缓存判据覆盖
**所有会改变服务端校验结果的输入维度**，并在写登录态时同步推进一个显式代际。

---

## 1. 报障现象

用户原话：「修复（STV[api_1]）书源，点同步登录态到正文后也不行，需要把阅读清理后台后重新打开后才能正常显示正文」。

v11.19 已经修过一次「官方 App 没登录前正文打不开」（loginHeader 与 CookieJar 不通），
并加了「同步登录态到正文」按钮。但按钮点了仍无效，只有杀进程才恢复 —— 说明 v11.19 只修了
**Cookie 写入通道**，没修**已经缓存下来的旧密钥**。

---

## 2. 根因链（四层，每层都有实测证据）

### 2.1 正文密钥是 30 分钟持久化缓存，判据只看 readcontextid

```
function getKey(host, bid, force) {
  var ck = 'stv10_<域>_<host>_<bid>';          // source.put/get 书源变量，跨进程存活
  var raw = source.get(ck);                    // "<ts>|<rc>|<key>"
  if (30min 内 && live rc === 缓存 rc) return 缓存 key;   // ← 唯一判据
  ... grantcontext 铸新密钥 ...
}
```

`rctx()` 从 `cookie.getCookie(DOM())` 取 `readcontextid`。

### 2.2 readcontextid 在「内存会话层」，登录态变了它不变

`grantcontext` 响应的 `Set-Cookie: readcontextid=...` 由 OkHttp CookieJar 落在**会话层**（未持久化）。
实锤方法：用 `cookie.setCookie(域, '__probe=BBB')` 把持久层整体替换后，
`getCookie(域)` 仍返回 `readcontextid=...` —— 证明它来自会话层，与持久层是两回事。

而 `access / PHPSESSID / useri2` 属于持久层。同步按钮改的是持久层，**rc 完全没动**。

### 2.3 于是：登录态换了，密钥没换 → key 与 access 不配对

站点正文密钥是按**会话**铸造的。新 access + 旧会话的 key → `code 12/13 / Không thể xác thực kết nối / 10002`。

### 2.4 杀进程为什么「刚好能修」

杀进程 → 内存会话层 CookieJar 清空 → `rctx()` 返回空 → `live rc === 缓存 rc` 不成立 →
强制走 `grant()` 重铸 → 新会话的 key 与新 access 配对 → 正文恢复。

> ★通用判据：**「必须重启/清后台才好」= 根因在内存态，而不是持久配置**。
> 不要去调 header、不要去换域名，先找哪份缓存是进程内的、哪份判据漏了维度。

### 2.5 反向验证（决定性日志对照）

| 场景 | 证据 |
|---|---|
| 修复前：同步后第二次 debug | 日志 #24~#31 **完全没有 `grantcontext` 请求**，直接用缓存 key 读正文 |
| 修复前：首次 debug | 日志 #21 有 `grantcontext`，#19 预取 URL 返 `code 10002` |
| 修复后：实跑 `stvsync()` | #43 心跳 → **#51 `grantcontext` 重铸** → #52 `code:0` 中文正文 |
| 修复后：再读一章 | 新缓存键带指纹 `g1_af9bdd235a77f`，旧键 `g_...`/无指纹键永不再被寻址 |

**修复机制类问题必须拿到这种「修复前无重算 / 修复后有重算」的请求链对照**，
只看「正文能显示了」是假绿（旧 access 与旧 key 恰好配对时也会全绿）。

---

## 3. ★新 Legado 机制实锤：`cookie.setCookie()` 是整体替换，不是合并

在 App 内 eval_js 做的探针：

```
cookie.setCookie('https://sangtacviet.app', '__stv_probe=BBB');
cookie.getCookie(...)  =>  "__stv_probe=BBB; readcontextid=db9fdf..."
```

原有的 `access / PHPSESSID / useri2 / transmode / ...` **全部消失**。
即 `setCookie(url, ck)` 会用 ck **替换该二级域的持久层全部键值**（会话层不受影响，所以 rc 还在）。

### 三条硬约束

1. **写之前必须 `getCookie` 合并**：`stvmerge(prev, newck)`，同名键由 newck 覆盖（顺序：旧在前、新在后）。
   v11.19 的登录/同步/退出都是裸 `setCookie(ldom(), ck)`，会顺手冲掉已有登录态 —— 这也是隐性故障源。
2. **不要把会话层 `readcontextid` 固化进持久层**：合并时显式 `if (k === 'readcontextid') continue;`。
   一旦持久化，重启也清不掉它，「杀进程自愈」的路径反而被自己堵死。
3. **探针本身会改环境**：这次排查的 setCookie 探针把 `.app` 域正式 Cookie 冲掉了，
   完事必须按排查前抓到的原值**重存正式 Cookie**（沿用 §15 的老纪律：排查完重存正式版）。

补充：`cookie.removeCookie(url, key)` 清不掉这个探针（结果 `clean:false`），
最后是用「合并完整正式 Cookie 再 setCookie 一次」恢复的。

---

## 4. ★新 Legado 机制实锤：`source.get()` 空键返回 Java 空串对象，Rhino 里 truthy

```
String(source.get('stvauthgen') || '0')   // 键不存在时得到 ''，不是 '0'
```

实测 `typeof source.get('stvauthgen') === 'object'`，Java 空串对象在 Rhino 判断里是 truthy，
`|| '0'` 的 fallback **不触发**。结果代际指纹拼成 `g_...` 而不是 `g0_...`（功能不坏，但显示/诊断全乱）。

**铁律：书源变量读值一律显式判长度**

```
var gv = ''; try { gv = String(source.get(k) || ''); } catch(e){}
var g = (gv.length > 0) ? parseInt(gv, 10) : 0;
if (isNaN(g) || g < 0) g = 0;
```

同理 `source.put(k, '')` 不能当作「删除」，旧值可能仍可读 —— 需要让缓存失效时，
**换缓存键**（把代际拼进键名），不要依赖删除/置空。

---

## 5. v11.20 修复四件套

### ① 显式代际 `stvauthgen`
`stvsave()` 统一入口里 `stvgen()` 每次 +1。触发点全覆盖：
账号登录 / Cookie 登录 / 同步按钮 / 退出登录 / 切线路（`stvset`）。

### ② 缓存键与复用校验绑定登录态指纹 `AUTHFP()`

```
function AUTHFP() {
  var jar = cookie.getCookie(DOM()), lh = JSON.parse(source.getLoginHeader()).Cookie;
  var acc = ckpick(lh,'access') || ckpick(jar,'access');   // loginHeader 优先
  var g   = <stvauthgen，显式判空>;
  return 'g' + g + '_a' + acc.substring(0,12);
}
var ck = 'stv10_' + DOM + '_' + AUTHFP() + '_' + host + '_' + bid;
// 缓存值改为 "<ts>|<rc>|<fp>|<key>"，复用时 rc 与 fp 双判据
```

★**故意排除 `PHPSESSID`**：`grantcontext` 会刷新它，纳入指纹会导致「每章都判定会话变了 → 每章重铸 85 万字符混淆 JS」。
选指纹字段的标准是「**登录态变化时必变，其它任何时候都不变**」。
`access` 只取前 12 位够区分且避免把完整凭证写进键名。

### ③ 正文首次失败自动强制重铸（不点按钮也自愈）

覆盖「官方 App 后台刷新登录态」「用户压根没去点同步按钮」等场景：

```
if (KEYRECAST===0 && !forceRecastDone) {
  KEYRECAST=1; forceRecastDone=1;
  var kf = getKey(host, bid, true);       // force=true 跳过缓存
  if (kf.k) { key=kf; r = readOne(..., String(nowMs()), true); }
}
```

放在既有 10002 重试循环内、`ERRCN` 判定之前，用 `_r=<ts>` 破 ARR 10 秒错误缓存。
全局只一次，不会和 Q02 限流预算叠加放大。

### ④ `stvsave()` 统一合并写
`putLoginHeader` + 两域（当前线路 / sangtacviet.com）`stvmerge(prev, finalCk)`，
drop `readcontextid`，再 bump 代际。心跳 `sajax=online` 用合并后的完整 Cookie。

---

## 6. 通用纪律（可迁移到任何「会话敏感」书源）

1. **缓存复用判据必须覆盖所有影响服务端校验的输入**。只盯一个「看起来会变」的字段（rc）是典型盲区；
   登录态、线路域名、语种 Cookie、设备指纹，任何一项变化都要能让缓存失效。
2. **「重启才好」优先怀疑内存态缓存 / 会话层 Cookie**，不要先去改请求头或换域名。
3. **用代际计数器做失效，比删除缓存可靠**：`source.put` 没有可靠 delete，换键名最稳，旧键自然变孤儿。
4. **写 Cookie 前先读后合并**；分清持久层与会话层，别把会话态持久化。
5. **读 `source.get` 显式判长度**，别信 `|| 默认值`。
6. **修复前后都抓请求链做反向验证**，确认「该发生的重算真的发生了」，而不是恰好撞对。
7. **实验会改环境**：探针、清 Cookie、切线路都是变量，收尾必须恢复默认线路/正式 Cookie/自动换源开关。

---

## 7. 仍需注意的边界

- `access` 若被站点后台轮换，指纹会自动让旧密钥失效（这正是想要的），随后由 ③ 自动重铸。
- 换源定位、目录解析、`<usehtml>` 排版等 v11.x 既有逻辑**一行未动**，本次只改登录态写入与密钥缓存层。
- 漫画来源 `cocomanga` 走官方独立通道 `comicprovider.js`，书源侧仍不支持（与 v11.19 一致），
  用「斗破苍穹」搜索会命中漫画源，正文报错属已知限制，不是回归。测试请用小说来源（如 `trxs/11598`）。
- 最终必须在 Legado APP 真机实测：登录面板点一次「同步登录态到正文」→ 不杀后台 → 退出本章重进 → 正文应直接显示。
