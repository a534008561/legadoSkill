# 方法-Discuz论坛型站书源制作（TXT下载站 · bookSourceType=3）

> 蓝本：墨香书阁 `www.noveltxt.vip`（Discuz! X5）· 2026-09-17
> 适用：所有 Discuz!/PHPWind 论坛形态的**资源下载站**（TXT/漫画/资源包）
> 与「方法-登录注册验证码与限频破解」互补：那篇讲 qsskel 家族（自研 CMS），本篇讲 **Discuz 家族**

---

## 0. 一句话总结

Discuz 站的三大命门：
**① UA 决定模板** → header 必须给手机 UA；
**② 用户组权限** → 游客能搜、登录不能搜（或反之）；
**③ 附件下载 = 服务端 302 扣费** → 直接给 `forum.php?mod=attachment&aid=XX` 即可。
再叠加一个**登录/游客双态**架构（用 Cookie 快照 + session 重建），就能稳定跑通。

---

## 1. 站点识别：一眼认出 Discuz

| 特征 | 值 |
|---|---|
| Cookie 前缀 | `[随机4位字母]_2132_xxx`（如 `amBy_2132_sid`） |
| 手机版开关 | URL 带 `mobile=2`（或 `mobile=no` 强制 PC） |
| 帖子 URL | `/thread-{tid}-1-1.html` 或 `forum.php?mod=viewthread&tid=N` |
| 版块 URL | `/forum-{fid}-1.html` 或 `forum.php?mod=forumdisplay&fid=N` |
| 搜索 URL | `search.php?mod=forum&srchtxt=XX&searchsubmit=yes` |
| 登录 URL | `member.php?mod=logging&action=login&loginsubmit=yes&loginhash=XX` |
| 附件 URL | `forum.php?mod=attachment&aid=XXX` |
| 错误页 | `Discuz! General Error`（HTML 标题） |
| 提示页 | `<div class="jump_c"><div>提示文案</div></div>` |

**判别命令**（书源调试用）：
```js
var c = String(cookie.getCookie('https://站点/'));
if (c.indexOf('_2132_') >= 0) { /* 是 Discuz */ }
```

---

## 2. ★ 核心机制一：UA 决定模板（生死线）

### 现象
同一个 URL，UA 不同返回**完全不同的 HTML**：
- 手机 UA → `mobile=2` 模板（`.threadlist_tit`、`.threadlist_mes`）
- 桌面 UA → PC 模板（`.xs2`、`tbody[id^=normalthread]`）

更坑的是：**桌面 UA 会 302 到 `mobile=no`**，此时 `mobile=2` 参数被丢弃。

### 判定
```js
var isMobile = html.indexOf('discuz_diy') >= 0;   // 手机模板标志
var isPC     = html.indexOf('discuzx5') >= 0;     // PC 模板标志
```

### 解法
```json
"header": "{\"User-Agent\": \"Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36\"}"
```
> ⚠️ **不要依赖 App 默认 UA**（通常是桌面 Windows UA）。
> ⚠️ jsLib 内 `java.ajax` 传的 `User-Agent` 只是**双保险**，主开关还是 `header` 字段。

---

## 3. ★ 核心机制二：用户组权限（游客 vs 登录）

### 现象
登录后搜索报错：
> 抱歉，您所在的用户组(XX)无法进行此操作

而**游客反而能搜索**。Discuz 用户组权限里有独立的「**使用搜索**」开关。

### 查询方法
```
GET home.php?mod=spacecp&ac=usergroup&mobile=2
```
页面里有权限表：`<td>禁用搜索</td>` = 无权限，`<td><i class="fico-valid fc-v" title="data_valid"></i></td>` = 有权限。

### 三类站点
| 类型 | 搜索 | 下载 | 对策 |
|---|---|---|---|
| A. 游客可搜 + 下载要登录（**本蓝本**） | 游客态 | 登录态 | 双态切换（见 §5） |
| B. 登录可搜 + 下载要登录 | 登录态 | 登录态 | 正常单态 |
| C. 都要登录 | 登录态 | 登录态 | 正常单态 |

> **如何判断属于哪类**：先用游客 cookie 搜一次，再用登录 cookie 搜一次，对比返回。

---

## 4. ★ 核心机制三：附件下载

### 结构
```html
<ul id="attach_13884" class="quote post_attlist cl">
  <li class="p5">
    <a href="forum.php?mod=attachment&amp;aid=MTM4ODR8...%3D&amp;mobile=2" target="_blank">
      <div class="tit">
        <span class="link f_b">《书名》作者：XXX.rar</span>
        <p class="pl5 f_9">181.14 KB, 下载积分: 金币 -1 </p>
      </div>
    </a>
  </li>
</ul>
```

### 扣费机制
**不是** `purchase` 表单，而是**服务端 302 到 `attachcredit` 页面**：
```
GET forum.php?mod=attachment&aid=XXX
 → 302 → misc.php?mod=attachcredit&aid=XXX&...（服务端在此扣费）
 → 302 → 真实文件流
```
所以：**直接给 `downloadUrls` = 附件 URL 即可**，金币由服务端自动结算。

### ★ 关键坑：`downloadUrls` 返回值类型
`AnalyzeRule.getStringList()` 源码：
```kotlin
if (result is String) { result = result.split("\n") }   // ← String 会按 \n 切
...
return result as? List<String>                           // ← JS 数组不是 Java List！
```
**JS 数组（NativeArray）在 Rhino 里不是 `java.util.List`** → 会被判为空 → 报「下载链接为空」。

**正确写法**：
```js
return out.join(String.fromCharCode(10));   // ← 换行分隔字符串
```
**错误写法**：
```js
return out;   // ← JS 数组 → getStringList 拿到空
```

### ★ 关键坑：附件 URL 的 `&amp;`
HTML 里是 `&amp;`，必须解码：
```js
var u = String(m[1]).split('&amp;').join('&');
u = u.replace(/[&?]mobile=2/, '');   // 去掉多余参数
```

---

## 5. ★★ 双态架构：搜索游客态 + 下载登录态

### 问题链
1. `cookie.removeCookie(url)` 清空 cookie → 搜索**仍失败**
   → 服务端 session 里记着账号；`amBy_2132_lip`（上次 IP）把 IP 与账号关联
2. 显式给 `Cookie` 头（手动头优先）→ 搜索成功，但**翻页失败**
   → Legado 请求翻页 URL 时用的是**库 cookie**，不是手动头
3. 只清 cookie 不重建 session → 返回 4470 字节提示页
   → 服务端要求「先建立 session 再搜索」

### 最终方案（三步）
```js
// searchUrl 里
if (nLogged(cookie)) { nGuest(cookie); }   // 1) 切到干净游客态（★必须 setCookie 整体替换）
nSession(java);                            // 2) 访问 index 让服务端下发新 session
// 3) 此后库 cookie 即游客态 → Legado 的常规请求（含翻页）都能正常搜索
var r = nx(java, NT_BASE + 'search.php?mod=forum&srchtxt=' + kw + '&searchsubmit=yes&mobile=2');
```

配套函数：
```js
// ★★ 必须用 setCookie【整体替换】，不能只 removeCookie！
//   实测：本站签到插件会写 amBy_2132_zqlj_sign_<uid>=日期 这类账号绑定 cookie，
//   removeCookie 只清客户端 → 服务端仍按旧 session 认账号 → 搜索被拒
//   （现象：cookie 显示为空，但搜索仍报"您所在的用户组无法进行此操作"）
function nGuest(C) {
  try {
    C.setCookie(NT_BASE, 'amBy_2132_saltkey=' + String(Math.random()).substring(2, 12)
                        + '; amBy_2132_mobile=2');
  } catch (e) {}
}
function nSession(J) { return nx(J, NT_BASE + 'index.php?mobile=2'); }
function nLogged(C) {
  try { return String(C.getCookie(NT_BASE)).indexOf('amBy_2132_auth') >= 0; }
  catch (e) { return false; }
}
```

> **为什么"替换 + 重建"缺一不可**：
> - 只 removeCookie → 服务端 session 里仍有账号痕迹（含插件写的 `zqlj_sign_<uid>` 键）→ 仍被拒
> - 只 setCookie 不重建 session → 服务端认为会话异常，返回提示页
> - 同时 `setCookie` 是**整体替换**语义：传的串就是新全集，旧键自动消失
>
> **排查技巧**：`cookie.getCookie(url)` 打印出来看有没有**插件写入的账号绑定键**
> （如 `amBy_2132_zqlj_sign_2249=20260918`），有的话必须整体替换。

### 下载态怎么恢复？
**不需要特殊处理**。用户点「🔓 登录」时：
1. 登录成功 → 当前 session 内即建立了 auth
2. 之后 `downloadUrls` 提取的链接，Legado 用库 cookie 请求 → 正常下载
3. 但用户**下次搜索**会清掉登录态 → 所以：
   - **每次要用下载/签到前，重新点一次登录**（登录页 button 一键完成）
   - 或在 `downloadUrls` 里提示「⚠️ 未登录」（本蓝本做法）

---

## 6. ★ 登录接口的两个大坑

### 坑 1：手机版登录接口触发风控
```
POST member.php?mod=logging&action=login&loginsubmit=yes&loginhash=XX&mobile=2
→ 请输入验证码后继续登录
```
**解法**：改用 **PC 版接口**（不带 `mobile=2`）：
```
POST member.php?mod=logging&action=login&loginsubmit=yes&loginhash=XX
→ 欢迎您回来，XXX
```

### 坑 2：已登录时登录页会 302
登录状态下访问 `member.php?mod=logging&action=login` → 返回「欢迎您回来」提示页 → 拿不到 `loginhash`。

**解法 A（推荐）**：`loginhash` 值服务端**不校验**，可传任意值：
```js
var u = NT_BASE + 'member.php?mod=logging&action=login&loginsubmit=yes&loginhash=LoGin';
```
**解法 B**：先从任意页面抓 `formhash`（未登录时 PC 首页也带）。

### formhash 抓取（多形态兼容）
```js
function nfh(html) {
  var t = String(html);
  var m = t.match(/name="formhash" id="formhash" value='([0-9a-f]+)'/);
  if (m) { return m[1]; }
  m = t.match(/name="formhash" value="([0-9a-f]+)"/);
  if (m) { return m[1]; }
  m = t.match(/formhash=([0-9a-f]{8})/);
  return m ? m[1] : '';
}
```

### 登录 POST body（Discuz 标准）
```
formhash=XXX&referer=URL编码的首页&fastloginfield=username
&username=URL编码&password=URL编码&questionid=0&answer=&cookietime=2592000
```
> ⚠️ **不要手动设 `Content-Type`**（会让 AnalyzeUrl 跳过 analyzeFields → body 空）。

---

## 7. 列表解析：手机模板三种结构

### 结构 A：标准列表（搜索页 / 分类页）
```html
<li class="list">
  <div class="threadlist_top cl">  <!-- 头像/作者/时间 -->
  <a href="thread-9369-1-1.html">
    <div class="threadlist_tit cl"><em>《书名》作者：XXX【完结】</em></div>
  </a>
  <a href="thread-9369-1-1.html">
    <div class="threadlist_imgs1 cl"><ul><li><img src="forum.php?mod=image&aid=..."></li></ul></div>
  </a>
  <a href="thread-9369-1-1.html"><div class="threadlist_mes cl">简介...</div></a>
  <div class="threadlist_foot cl">
    <ul>
      <li class="mr"><a href="forum-2-1.html">#分类名</a></li>   <!-- 或 forum.php?mod=forumdisplay&fid=2&filter=typeid&typeid=1 -->
      <li><i class="dm-eye-fill"></i>45</li>
      <li><i class="dm-chat-s-fill"></i>0</li>
    </ul>
  </div>
</li>
```

### ★ 关键坑：不能用非贪婪正则切块
```js
// ❌ 错误：块内 threadlist_imgs1 里还有嵌套 <li> → 提前截断
var re = /<li class="list">([\s\S]*?)<\/li>/g;
//     → 丢失 threadlist_mes(简介) 与 threadlist_foot(分类)

// ✅ 正确：按 <li class="list"> 作分隔符 split
var parts = t.split('<li class="list">');
```

### 结构 B：置顶帖（`list_top`）
```html
<li class="list_top">
  <a href="thread-7076-1-1.html">
    <span class="micon">置顶</span>
    <em style="...">✨论坛 VIP 会员功能正式上线啦！</em>
  </a>
</li>
```
**过滤规则**：含 `<span class="micon">` 的是纯公告，应跳过；其余（书籍置顶）可保留。
```js
t = t.replace(/<li class="list_top[^"]*">([\s\S]*?)<\/li>/g, function (all, body) {
  if (body.indexOf('<span class="micon">') >= 0) { return ''; }
  return '<li class="list">' + body + '</li>';
});
```

### 结构 C：首页「最新主题」swiper
```html
<div class="swiper-slide">
  <ul><li>
    <a href="thread-9369-1-1.html">
      <span class="mybk">8 小时前</span><span class="mico"></span>
      《七零五好家庭[美食]》作者：海底玫瑰【完结】
    </a>
  </li></ul>
</div>
```
正则：
```js
var hr = /<a href="(thread-[0-9]+-1-[0-9]+\.html)"><span class="mybk">[^<]*<\/span><span class="mico"><\/span>([\s\S]*?)<\/a>/g;
```

---

## 8. ★ 搜索分页：searchid 复用

Discuz 搜索流程：
```
GET search.php?mod=forum&srchtxt=XX&searchsubmit=yes&mobile=2
 → 302 → search.php?mod=forum&searchid=141&orderby=lastpost&...
```
**后续翻页必须带同一个 `searchid`**，否则回第一页。

`searchUrl` 写法：
```js
(function(){
  if (nLogged(cookie)) { nGuest(cookie); }
  nSession(java);
  var kw = encodeURIComponent(key);
  var r = nx(java, NT_BASE + 'search.php?mod=forum&srchtxt=' + kw + '&searchsubmit=yes&mobile=2');
  var sid = String(r).match(/searchid=([0-9]+)/);
  if (!sid) {
    return NT_BASE + 'search.php?mod=forum&srchtxt=' + kw + '&searchsubmit=yes&mobile=2';
  }
  return NT_BASE + 'search.php?mod=forum&searchid=' + sid[1]
       + '&orderby=lastpost&ascdesc=desc&searchsubmit=yes&kw=' + kw
       + '&page=' + (page || 1) + '&mobile=2';
})()
```

### ★ 大坑：`searchUrl` 必须返回**纯 URL**
```js
// ❌ 返回 "url,{json}" 形式 → Legado 把 ,{json} 当成 URL 的一部分
return url + ',' + JSON.stringify({headers: {...}});
//    → 请求变成 ...mobile=2,{"headers":{...}} → 列表为空

// ✅ 正确：返回纯 URL
return url;
```

---

## 9. 详情页规则

### 字段位置（手机模板）
```html
<div class="view_tit">
  <em>[现代情感]</em>
  《七零五好家庭[美食]》作者：海底玫瑰【完结】
</div>
<!-- 面包屑 -->
<h2><a href="forum.php?mod=forumdisplay&fid=2&page=1&amp;mobile=2">浪漫言情-TXT全本下载</a></h2>
<!-- 正文/简介 -->
<div class="message">简介内容<br />...</div>
<!-- 附件 -->
<ul id="attach_13884" class="quote post_attlist cl">...</ul>
```

### 书名净化
标题可能带 `[分类]` 前缀，且 `《》` 后还有 `作者：XX【完结】`：
```js
function nname(s) {
  s = nc(s);
  s = s.replace(/^\[[^\]]{1,12}\]\s*/, '');   // 去 [分类] 前缀
  s = s.replace(/^【[^】]{1,12}】\s*/, '');
  s = s.replace(/^《/, '');
  s = s.replace(/》[\s\S]*$/, '');            // 去 作者/完结 尾巴
  return s;
}
```

### 简介（`div.message` → 到 `ul#attach_` 之间）
```js
var i = t.indexOf('<div class="message">');
var j = t.indexOf('<ul id="attach_', i);
var s = t.substring(i + 21, j);
s = s.split('<br />').join('\n');
s = s.replace(/<[^>]*>/g, '');
```

### 字数（附件大小）
```js
var m = String(result).match(/([0-9.]+\s*(?:KB|MB|GB))/);
```
> 注意：这个正则第一个命中通常是附件大小（`181.14 KB`）。
> 如果帖子正文里也有类似数值，建议限定在 `attach_` 块内匹配。

---

## 10. 通用坑清单（K1~K15）

| # | 坑 | 解法 |
|---|---|---|
| K1 | 桌面 UA → 302 到 `mobile=no` | `header` 显式给手机 UA |
| K2 | 登录用户组禁用搜索 | 双态：搜索前清 cookie + 重建 session |
| K3 | `removeCookie` 清不掉服务端 session | 清完后必须 `GET index.php` 重建 |
| K4 | 手机版登录接口触发验证码 | 改用 PC 版接口（去掉 `mobile=2`） |
| K5 | 已登录时拿不到 `loginhash` | `loginhash` 可传任意值 |
| K6 | `downloadUrls` 返回 JS 数组被判空 | `return out.join(String.fromCharCode(10))` |
| K7 | 附件 URL 的 `&amp;` 未解码 | `.split('&amp;').join('&')` |
| K8 | 列表用非贪婪正则切块 → 丢字段 | 用 `split('<li class="list">')` |
| K9 | 搜索翻页回第一页 | 复用 `searchid` |
| K10 | `searchUrl` 返回 `url,{json}` | 必须返回纯 URL |
| K11 | 公告置顶帖污染列表 | 过滤含 `<span class="micon">` 的 |
| K12 | jsLib 里 `java.ajax` 不可用 | 参数注入 `nx(java, url)` |
| K13 | 书名带 `[分类]` 前缀 | `nname()` 正则剥离 |
| K14 | 高频请求触发 `General Error` | 降低频率；`concurrentRate` 设保守值 |
| K15 | 附件下载链接带时效签名 | 每次从详情页重新提取 |
| K16 | `removeCookie` 清不干净 → 搜索仍被拒 | **`setCookie` 整体替换**（插件会写 `zqlj_sign_<uid>` 绑定键） |
| K17 | 签到判据误用「今日已签到」字符串 | 该文案在**排行榜别人区块**也有 → 改判 **按钮文案** + **`discuz_uid='0'`** |
| K18 | 游客访问签到页按钮文案仍是"点击签到" | 先判 `discuz_uid = '0'`，否则误报"签到失败" |
| K19 | ★Discuz 登出后 cookie 值为字符串 `deleted` | `nLogged` 必须排除 `deleted`（`m[1].length>4 && m[1]!=='deleted'`） |
| K20 | 登录页本身无验证码字段 | 验证码是**按 IP 频率动态触发**，属站点防护；书源无需处理，等几分钟自愈 |

---

## 10.5 ★ 签到插件（zqlj_sign）判据三态

签到页 `plugin.php?id=zqlj_sign&mobile=2` 是**插件页**，判据比想象复杂：

### 三态判据表

| 状态 | `discuz_uid` | 按钮文案 | 说明 |
|---|---|---|---|
| **未登录** | `'0'` | `点击签到` | ⚠️ 游客也能看到按钮！点了才失败 |
| **已登录未签** | 真实 uid | `点击签到` | 正常执行签到 |
| **已登录已签** | 真实 uid | `今日已签到` | 重复点击服务端返回"请勿重复操作" |

### ★ 两个致命误判

**误判 1**：`if (t.indexOf('今日已签到') >= 0) return 'done'`
→ **错**！该文案在页面**「签到记录」排行榜里其他用户**的区块也会出现（如 `用户名：rongyi ... 今日已签到`）
→ 必须看**按钮文案**：`/<a href="[^"]*sign=[0-9a-f]+[^"]*" class="btna">([^<]+)<\/a>/`

**误判 2**：游客访问时按钮文案仍是「点击签到」
→ 直接点会失败，必须**先判 `discuz_uid = '0'`**

### 正确实现

```js
function ntSign(J, C) {
  var t = nx(J, NT_BASE + 'plugin.php?id=zqlj_sign&mobile=2');
  if (!t) { return { s: 'fail', m: '页面获取失败' }; }
  if (t.indexOf('General Error') >= 0) { return { s: 'fail', m: '站点限流中' }; }
  // ① 未登录判据（零双引号写法，防 MCP 传输层破坏）
  var Q0 = String.fromCharCode(39);
  var pUid = t.indexOf('discuz_uid');
  var isGuest = false;
  if (pUid >= 0) { isGuest = t.substring(pUid, pUid + 24).indexOf(Q0 + '0' + Q0) >= 0; }
  if (isGuest) { return { s: 'need', m: '未登录，请先登录' }; }
  // ② 取 uid，定位当前用户统计区块
  var uidM = String(t).match(/discuz_uid\s*=\s*'(\d+)'/);
  var uid = uidM ? uidM[1] : '';
  var block = t;
  if (uid) {
    var i = t.indexOf('uid=' + uid);
    if (i >= 0) { block = t.substring(i, i + 800); }
  }
  var dTotal = block.match(/总天数[:：]\s*([0-9]+)/);
  var dMonth = block.match(/月天数[:：]\s*([0-9]+)/);
  var dAll   = block.match(/总奖励[:：]\s*([0-9]+)金币/);
  var dLast  = block.match(/上次奖励[:：]\s*([0-9]+)金币/);
  // ③ 看按钮文案
  var m = t.match(/<a href="([^"]*sign=[0-9a-f]+[^"]*)" class="btna">([^<]+)<\/a>/);
  if (!m) { return { s: 'fail', m: '未找到签到按钮（站点可能改版）' }; }
  var label = nc(m[2]);
  var href = String(m[1]).split('&#38;').join('&').split('&amp;').join('&');
  if (href.indexOf('http') !== 0) { href = nu(href); }
  if (label.indexOf('已签到') >= 0) {
    var s1 = '今天已经签过啦';
    if (dTotal) { s1 += '（累计 ' + dTotal[1] + ' 天'; }
    if (dMonth) { s1 += '，本月 ' + dMonth[1] + ' 天'; }
    if (dTotal || dMonth) { s1 += '）'; }
    if (dLast) { s1 += String.fromCharCode(10) + '上次奖励 ' + dLast[1] + ' 金币'; }
    if (dAll) { s1 += '，总奖励 ' + dAll[1] + ' 金币'; }
    return { s: 'done', m: s1 };
  }
  // ④ 执行签到
  var r = nx(J, href);
  var ok = String(r).indexOf('签到成功') >= 0 || String(r).indexOf('恭喜') >= 0;
  if (!ok) {
    var msg = String(r).match(/jump_c">\s*<div>([\s\S]{0,200}?)<\/div>/);
    return { s: 'fail', m: '签到失败：' + (msg ? nc(msg[1]) : nc(String(r).substring(0, 100))) };
  }
  // ⑤ 成功 → 回签到页抓最新统计
  var t2 = nx(J, NT_BASE + 'plugin.php?id=zqlj_sign&mobile=2');
  var blk2 = t2;
  if (uid) {
    var j = t2.indexOf('uid=' + uid);
    if (j >= 0) { blk2 = t2.substring(j, j + 800); }
  }
  var aTotal = blk2.match(/总天数[:：]\s*([0-9]+)/);
  var aLast  = blk2.match(/上次奖励[:：]\s*([0-9]+)金币/);
  var aAll   = blk2.match(/总奖励[:：]\s*([0-9]+)金币/);
  var out = '签到成功 🎉';
  if (aLast)  { out += String.fromCharCode(10) + '本次奖励 +' + aLast[1] + ' 金币'; }
  if (aTotal) { out += String.fromCharCode(10) + '累计 ' + aTotal[1] + ' 天'; }
  if (aAll)   { out += '，总奖励 ' + aAll[1] + ' 金币'; }
  return { s: 'ok', m: out };
}
```

### 插件页的其它可用入口
```
plugin.php?id=zqlj_sign&tb=index     签到记录（全站）
plugin.php?id=zqlj_sign&tb=my        我的记录
plugin.php?id=zqlj_sign&tb=today     今日排行
plugin.php?id=zqlj_sign&tb=month     本月排行
plugin.php?id=zqlj_sign&tb=rank      总天数排行
plugin.php?id=zqlj_sign&tb=money     总奖励排行
plugin.php?id=zqlj_sign&tb=checkall  全勤奖励
plugin.php?id=zqlj_sign&tb=rule      签到规则
```

---

## 11. 开箱模板（jsLib 骨架）

```js
var NT_UA = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36';
var NT_BASE = 'https://你的站点/';

function nu(url) { /* 相对转绝对 */ }

function nx(J, url, extra) {          // ★ 参数注入 java
  var o = { headers: { 'User-Agent': NT_UA } };
  if (extra) { for (var k in extra) { o[k] = extra[k]; } }
  var r = '';
  try { r = String(J.ajax(String(url) + ',' + JSON.stringify(o))); } catch (e) { return ''; }
  if (r.indexOf('javax.net.ssl') >= 0 || r.indexOf('java.net.UnknownHost') >= 0
      || r.indexOf('InternalError') >= 0 || r.indexOf('reset by peer') >= 0) { return ''; }
  return r;
}

function nGuest(C)   { try { C.removeCookie(NT_BASE); } catch (e) {} }
function nSession(J) { return nx(J, NT_BASE + 'index.php?mobile=2'); }
function nLogged(C)  { try { return String(C.getCookie(NT_BASE)).indexOf('_2132_auth') >= 0; } catch (e) { return false; } }
function nfh(html)   { /* formhash 多形态抓取 */ }
function nc(s)       { /* 去标签 + 实体解码 */ }
function nname(s)    { /* 书名净化 */ }
function nauthor(s)  { /* 作者提取 */ }
function nlist(html) { /* 列表解析（split 法） */ }
```

---

## 12. 验证方法论

### 沙盒 vs 真机
| 现象 | 原因 |
|---|---|
| 沙盒游客搜索成功，真机失败 | 真机 cookie 里残留登录态 → 必须走"清+重建" |
| 沙盒 `followRedirects:false` 返回空 | 302 无 body，属正常 |
| `discuz_diy` 标志 | 判断拿到的是手机模板还是 PC 模板 |

### 调试命令
```
# 搜索（游客态应返回 20 条）
debug_source(url=书源URL, key='重生')

# 发现页
debug_source(url=书源URL, key='::https://站点/index.php?mobile=2')
debug_source(url=书源URL, key='::https://站点/forum-3-1.html')

# 详情
debug_source(url=书源URL, key='https://站点/thread-9369-1-1.html')

# 官方校验
check_source(urls=[书源URL])
```

### 真机 eval_js 验证片段
```js
// 1) 确认模板
var h = nx(java, NT_BASE + 'index.php?mobile=2');
java.log('isMobile=' + (h.indexOf('discuz_diy') >= 0));

// 2) 确认游客态搜索
try { cookie.removeCookie(NT_BASE); } catch (e) {}
nSession(java);
var r = nx(java, NT_BASE + 'search.php?mod=forum&srchtxt=' + encodeURIComponent('重生') + '&searchsubmit=yes&mobile=2');
java.log('sid=' + (String(r).match(/searchid=([0-9]+)/) || ['', 'NONE'])[1]);
java.log('nlist=' + nlist(r).length);

// 3) 确认登录
var lp = nx(java, NT_BASE + 'member.php?mod=logging&action=login&mobile=no&_t=' + Date.now());
var fh = nfh(lp), lh = String(lp).match(/loginhash=([A-Za-z0-9]+)/);
java.log('fh=' + fh + ' lh=' + (lh ? lh[1] : 'NONE'));
```

---

## 13. 案例档案

| 站点 | 程序 | 搜索 | 下载 | 特有点 |
|---|---|---|---|---|
| **noveltxt.vip**（墨香书阁） | Discuz! X5 | 游客态 | 登录 + 1 金币 | UA 分流 + 登录组禁搜 + IP 级限流 |
| 63sg.com（63书阁） | PTcms | 游客 | 登录（假墙） | `search_time` cookie 限频 |
| 35sw.org（35书屋） | PTcms | 游客 | 登录（假墙） | 60 秒搜索限频 |
| ppxsw.cc（皮皮小说） | qsskel | 登录 | 免费 | `search_time` cookie 限频 |
| xuken.net（笔趣阁） | qsskel | 游客 | 免费 | TCP RST 需 retry |

---

## 14. 通用结论

1. **Discuz 站的 UA 是生死线**：先在 header 里钉死手机 UA，再谈规则。
2. **权限要先查用户组表**：`home.php?mod=spacecp&ac=usergroup` 一眼看清。
3. **双态不是"清 cookie"那么简单**：必须「清 + 重建 session」两步，才能让 Legado 的**常规请求**（含翻页）走对通道。
4. **`getStringList` 只吃 String/List**：JS 数组不是 Java List，`downloadUrls` 必须 join 成字符串。
5. **`searchUrl` 返回纯 URL**：任何额外后缀都会被当 URL 的一部分。
6. **列表解析用 split，不用非贪婪正则**：嵌套 `<li>` 会让正则提前截断。
7. **附件扣费是服务端 302**：书源只需给出 `mod=attachment&aid=` 的原始链接。
8. **jsLib 作用域受限**：联网一律参数注入 `nx(java, url)`。
