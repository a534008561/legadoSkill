# 方法：「按作者/UP主/画师列作品」做成合集书（全流程 + 参数逆向）

> **一句话**：把「作者的全部作品」变成一本 Legado 的书——书籍URL直接指向可用的作品列表接口，
> 目录 = 每一条作品，`nextTocUrl` 链式翻页到底，配合**归属校验**防止串到别人的内容。
>
> 蓝本：iwara.tv（2026-09-20，v13，check_source 2/2 通过）
> 适用：iwara / B站 / Pixiv / hanime1 / 各类视频站与图站——只要站点有「作者作品列表」。

---

## 0. 什么时候用这篇

需求形如：
- 「详情页作者名点一下，打开 TA 的全部作品」
- 「想把某个画师/UP主的所有作品当一本书追」
- 「能不能像关注一样，一键把作者所有投稿变成目录」

**核心判定**：目标站点是否存在「按作者筛选作品」的接口/页面。
不存在就退化为「打开作者网页主页」（见 §7 降级方案）。

---

## 1. ★头号陷阱：`count` 正确但 `results` 是假的

这是本项目**最值钱的一条经验**，也是最容易让人写出「能跑但内容是别人的」的源。

```
GET /videos?userid=<UUID>&page=0&limit=50
→ 200
→ count = 51        ← 与作者真实作品数完全一致！看起来一切正常
→ results 50 条，其中 0 条属于该作者（全是站内热门流）
```

**用户看到的现象**：点「全部作品」→ 打开的书里全是乱七八糟别人的视频。

### 失败形态对照表（iwara 实测）

| 尝试 | 返回 | 诊断 |
|---|---|---|
| `?userid=<UUID>` | count 真、results 假 | **反爬：参数被忽略，列表被替换** |
| `?user=<username>` | count=0 | 参数值类型错（要 UUID） |
| `/user/{id}/content/videos` | `errors.forbidden` | 路由存在但限制看他人 |
| `?userId=` / `?createdBy=` / `?author=` / `?u=` | 站内热门 | 参数名无效 |
| **`?user=<UUID>`** ✅ | count 与结果数一致，100% 命中 | **正确形态** |

### 鉴别决策树

```
请求作者作品接口
├─ 报错（403/404/forbidden）
│  └─ 路由问题或权限问题 → 换路由 / 补 token / 换方案
├─ count>0 且 results 里能匹配到该作者
│  └─ ✅ 可用 → 照常实现
├─ count>0 但 results 里 0 条匹配该作者     ★ 最危险
│  └─ 参数被忽略（反爬）→ 换参数名/值类型（§3）
└─ count=0
   └─ 参数值类型错（username vs UUID）/ 参数名错（§3）
```

> **铁律**：拿到作者作品响应后，**永远**校验 `results[].user.id === 请求的 uid`（§5）。

---

## 2. 破局第一优先：查 GitHub 开源实现

**比盲试参数快一个数量级。** 这是本项目实际奏效的路径。

### 搜索话术

```
GitHub <站点名> API client project source code user videos endpoint
GitHub <站点名> downloader extractor implementation
<站点名> api docs user content endpoint
```

### 优先查的项目类型

| 项目 | 为什么优先 | 路径 |
|---|---|---|
| **yt-dlp** | 最权威，含完整 query 参数与 headers | `yt_dlp/extractor/<site>.py` |
| **gallery-dl** | 含 API 类定义与分页逻辑 | `gallery_dl/extractor/<site>.py` |
| 站点专用下载器 | 最贴近站点实际用法 | GitHub 搜 `<site> downloader` |

### iwara 的决定性证据（yt-dlp `IwaraUserIE`）

```python
_VALID_URL = r'https?://(?:www\.)?iwara\.tv/profile/(?P<id>[^/?#&]+)'

# 列出作者视频：
#   path  = 'videos'
#   query = {
#       'page':  page,
#       'sort':  'date',
#       'user':  user_id,        # ★★★ 值是 user_id（UUID），不是 username
#       'limit': 32,
#   }
```

**我最初的误判**：参数名叫 `user`，就按字面传了 `username` → `count=0` →
误以为「接口已废弃」，白折腾了一轮。

### 修正后的实测（多作者，命中率 100%）

| 作者 | count | 返回条数 | 命中 |
|---|---|---|---|
| pastapaprika | 44 | 44 | 44/44 |
| aide | 51 | 50 | 50/50 |
| fearess | 51 | 50 | 50/50 |
| user3207206 | 22 | 22 | 22/22 |
| fiorammd | 51 | 50 | 50/50 |

分页（`limit=5` 强制分页验证）：
```
page=0 count=6  n=5 命中=5
page=1 count=11 n=5 命中=5
page=2 count=16 n=5 命中=5
```

---

## 3. 辅助手段：挖站点自己的 JS bundle

当 GitHub 没有现成实现时，直接读站点前端代码。

```js
// 1) 抓首页拿 bundle 地址
var h = String(java.ajax('https://www.iwara.tv/'));
// → <script defer src="/main.838884031a28ff0e346d.js"></script>

// 2) 抓 bundle（~1.18MB）
var s = String(java.ajax('https://www.iwara.tv/main.<hash>.js'));

// 3) grep 关键片段
s.indexOf('fetchUserContent')     // 找到 API 定义表
s.indexOf('api.iwara.tv')         // 找到 baseURL 与路径拼接方式
```

iwara 的关键发现：

```js
fetchUserContent: function(e, t, n, r) {
  return A(e, "/user/".concat(t, "/content/").concat(n), ..., {query: r})
}
//  e = token, t = userId, n = type('videos'/'images'), r = query
```

**注意**：这条路找到的 `/user/{uid}/content/videos` 最终是 `forbidden`
（只能看自己），但这仍然是必要信息——**排除法**同样有价值。

### SPA 渲染探针（辅助）

当接口都不明确时，用 `java.webView` 加载真实页面，观察它自己发什么请求：

```js
// ★ JS 必须是「表达式」(IIFE)，顶层 return 会报 Illegal return statement
var Q = String.fromCharCode(34);
var probe = '(function(){var sel=' + Q + 'a[href*=' + String.fromCharCode(39)
          + '/video/' + String.fromCharCode(39) + ']' + Q
          + ';var a=document.querySelectorAll(sel);return String(a.length);})()';
java.webView('<html><body>x</body></html>', 'https://www.iwara.tv/users/<name>', probe);
```

> 坑：`java.webView` 返回 null/空会按 `[200,400,600,800,1000]ms` 重试到约 30s 后抛
> 「js执行超时」。用 `window.__n` 自计数控制采样轮数。
> 页面脚本统一用单引号（QuickJS 场景不支持反引号模板串）。

---

## 4. 落地：作者合集 = 一本虚拟书

### 4.1 ★书籍 URL 直接就是可用的 API 地址

```
https://api.iwara.tv/videos?user=<UUID>&page=0&limit=50&sort=date&un=<用户名>
```

**为什么要这样设计**（血泪教训）：

- ❌ 若书籍 URL 用 `/user/{uuid}` 这类**非真实端点** → Legado 框架会先请求它，
  得到 404 → **在 `ruleBookInfo.init` 执行之前就失败了**
- ✅ 让 bookUrl 本身就是可用接口 → 框架请求即拿到 JSON
  → `IWRINIT` 可以**短路复用**，省一次请求

`un=<用户名>` 是自定义附加参数，纯粹为了展示友好（接口会忽略它）。

### 4.2 `IWRINIT` 短路（省一次请求 + 注入上下文）

```js
function IWRINIT(Jv,Sv,bu,res){
  IWRTKL(Jv,Sv);
  if(IWRAFIS(bu)&&res){
    var s0=IWRT(res);
    if(s0!=''&&IWRAFCO(IWRP(s0))){
      var f0=IWRAFINFO(bu);
      var e0=IWRAFVFY(IWRP(s0),f0.uid);     // ★ 校验放在这里，尽早失败
      if(e0!=''){throw new Error(e0);}
      try{
        var o0=IWRP(s0);
        o0.__au_uid=f0.uid; o0.__au_un=f0.un; o0.__au_pg=f0.pg;  // 注入上下文
        return IWRT(JSON.stringify(o0));
      }catch(e1){return s0;}
    }
  }
  // ... 原有单视频/合集逻辑
}
```

> **不要用全局变量传 `uid/un/pg`** —— 不同请求间会串数据。
> 注入到 init 返回的 JSON 里，`IWRAFL` 再从中读，天然隔离。

### 4.3 编号识别（作者类型判定）

```js
function IWRIDF(u){
  var x=IWRT(u).split(',')[0];   // ★ 先剥掉 ,{json选项} 后缀

  // ★ 正则要用 [?&] 打头，不要写 [/]videos[?][^#]*[?&]xxx=
  //   因为 [?] 已消费掉问号，后面 [^#]* 会把参数名也吃掉 → 恒不匹配
  var mv=x.match(/[?&](userid|user)=([0-9a-fA-F]{8}[-][0-9a-fA-F]{4}[-][0-9a-fA-F]{4}[-][0-9a-fA-F]{4}[-][0-9a-fA-F]{12})/);
  if(mv&&x.indexOf('/videos')>0){return {type:'au',id:mv[2]};}

  // ... 原有 /video/ /playlist/ 分支保持不变（注意回归测试！）
}
```

> ★ Rhino 旧 RegExp **不支持非捕获组 `(?:a|b)` 的可靠行为** → 用 `(a|b)` + `mv[2]`。

### 4.4 翻页：`nextTocUrl` 链式单 URL

```
ruleToc.nextTocUrl = @js:IWRAFNX(java,source,baseUrl,result)
```

```js
function IWRAFNX(Jv,Sv,bu,res){
  var o=IWRP(res);
  if(!IWRAFCO(o)){return [];}
  var fi=IWRAFINFO(bu);
  var lim=IWRAFLIM(Sv);
  var arr=(o.results&&o.results.length!=null)?o.results.length:0;
  var cnt=parseInt(o.count,10); if(cnt!=cnt){cnt=arr;}
  var off=fi.pg*lim;
  if(arr<=0){return [];}
  if((off+arr)>=cnt){return [];}         // ★ 到底了 → 空数组 → Legado 自动终止
  return [IWRAFU(fi.uid,fi.pg+1,lim,fi.un)];
}
```

**为什么只返回 1 个 URL**（源码级依据，`BookChapterList.kt`）：

- 返回 **0 个** → `Unit`，停止
- 返回 **1 个** → 走 `while` **串行链**（`nextUrlList.add` 去重）→ **目录顺序天然保证**
- 返回 **多个** → `flow{}.mapAsync(threadCount)` **并发** → **顺序不保证**

> 另注：`analyzeRule.getStringList(rule, isUrl=true)` 之后会过滤 `item != redirectUrl`
> （防自我循环），且此时 content 是**整个页面 body**（未被 `setContent(item)` 覆盖）。

### 4.5 目录条目（每页 50 条）

```js
function IWRTOCA(Jv,Sv,bu,res){
  var o=IWROK(res),C=IWRC(),out=[],i;
  var fi=IWRAFINFO(bu);
  var uid=fi.uid, pg=fi.pg;
  var lim=IWRAFLIM(Sv);

  var ve9=IWRAFVFY(o,uid);                  // ★ 每页都校验
  if(ve9!=''){throw new Error(ve9);}

  var arr=(o&&o.results)?o.results:[];
  var cnt=(o&&o.count!=null)?parseInt(o.count,10):arr.length;
  if(cnt!=cnt){cnt=arr.length;}
  var off=pg*lim;                            // ★ 全局编号，跨页连续

  for(i=0;i<arr.length;i++){
    var r=arr[i];
    if(!r||!r.id){continue;}
    if(r.private){continue;}                 // ★ 过滤私密
    var f=r.file||{};
    out.push(IWRJ({
      name: IWRPAD(off+i+1,3)+' '+IWRT(r.title||'(未命名)')
            + (f.duration?('  ['+IWRDUR(f.duration)+']'):''),
      url:  IWRU(Sv,C.api+'/video/'+r.id),
      coverUrl: IWRCOV0(Sv,r)
    }));
  }
  if(!out.length){
    if(cnt>0){throw new Error('该页取不到视频（可能都是私密或已删除），请下拉重试');}
    throw new Error('该作者暂无公开视频（可能全部私密或已注销）');
  }
  return out;
}
```

**关键点**：
- 编号用 `off+i+1` 而不是 `i+1` → **跨页连续**（001…050、051…100）
- `private` 过滤（私密作品点了也播不了）
- 空页要给**明确中文提示**，不要静默返回空

### 4.6 详情页字段

```js
function IWRAFL(Jv,Sv,o,f){
  // 从 IWRINIT 注入的上下文读（不用全局变量）
  var fi={uid:'',un:'',pg:0};
  try{
    fi.uid=IWRT(o&&o.__au_uid);
    fi.un =IWRT(o&&o.__au_un);
    fi.pg =IWRAFPGN(o&&o.__au_pg);
  }catch(e0){}

  var arr=(o&&o.results)?o.results:[];
  var cnt=(o&&o.count!=null)?parseInt(o.count,10):arr.length;

  if(f=='name')     return (fi.un?('@'+fi.un):'作者主页')+' · 全部作品（'+cnt+' 个）';
  if(f=='author'){  var au9=IWRAFAUO(o); return au9?IWRT(au9.name||au9.username):''; }
  if(f=='kind'){
    var g=0,e=0;
    for(var i=0;i<arr.length;i++){ if(arr[i]&&arr[i].rating=='general'){g++;}else{e++;} }
    var s='📚 作者合集 · 共 '+cnt+' 个视频 · 本页 '+arr.length+' 个';
    if(g||e){s=s+'（本页 一般向'+g+'/里向'+e+'）';}
    return s;
  }
  if(f=='cover'){ for(var i=0;i<arr.length;i++){ if(arr[i]&&arr[i].id){ var u=IWRCOV0(Sv,arr[i]); if(u!=''){return IWRCOVB(Jv,Sv,u);} } } return ''; }
  if(f=='last'){ return arr.length?('最新 '+IWRT(arr[arr.length-1].title).substring(0,24)):(cnt+' 个作品'); }
  if(f=='word'){ /* 累加 file.size → IWRSIZESUM */ }
  if(f=='intro'){ /* 作者信息 + 总数 + 前 20 条列表 */ }
  return '';
}
```

### 4.7 ★作者对象兜底（否则作者行整行不渲染）

```js
function IWRFAUO(o){
  if(!o||typeof o!='object'){return null;}
  if(o.user&&(o.user.name||o.user.username)){return o.user;}       // 单视频/合集
  var a=(o.results&&o.results.length)?o.results:[];
  for(var i=0;i<a.length&&i<3;i++){
    if(a[i]&&a[i].user&&(a[i].user.name||a[i].user.username)){return a[i].user;}
  }
  return null;   // ★ 作者响应的 user 在 results[].user，不在顶层！
}
```

> **症状**：详情页作者行**完全消失**（不是报错，是整行不渲染）。
> 原因：`IWRINTR` 里 `L=L.concat(IWRFAROW(...))`，`IWRFAROW` 开头 `if(!au){return L;}`
> 返回空数组 → 看起来"没这个功能"。

---

## 5. ★必须做服务端归属校验（防串作者）

因为存在「服务端忽略非法参数返回全站热门」的行为，这一步**不可省**：

```js
function IWRAFVFY(o,uid){
  var u=IWRT(uid);
  if(u==''){return '⚠ 作者ID为空，无法打开作者合集';}
  if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(u)){
    return '🔍 作者ID格式不对（应为 UUID）：'+(u.length>20?(u.substring(0,20)+'…'):u);
  }
  var a=(o.results&&o.results.length)?o.results:[];
  if(!a.length){return '';}
  var hit=0,tot=0;
  for(var i=0;i<a.length&&i<5;i++){
    if(a[i]&&a[i].user&&a[i].user.id){ tot++; if(IWRT(a[i].user.id)==u) hit++; }
  }
  if(tot>0&&hit==0){return '⚠ 站点未返回该作者的视频（可能作者ID失效或已被注销）';}
  return '';
}
```

**三层防御**：
1. **ID 格式预检**（`IWRAFUIDOK`）—— 非法 ID 连请求都不发
2. **响应归属校验**（`IWRAFVFY`）—— 上面这段，在 `IWRAFNX`/`IWRTOCA`/`IWRAFL` 各处调用
3. **明确报错文案** —— 让用户知道发生了什么，而不是看到别人的内容

**没有这三层，用户会看到别人的视频而毫不知情。**

---

## 6. 按钮与深链

### 6.1 详情页按钮

按钮走 `<usehtml>` + `@onclick`（在**完整 Rhino 规则环境**执行）：

```js
L.push('<b>👤 作者 '+lab+'</b>');
L.push(' ');
// ★ 未登录也显示（打开作者合集不需要登录！只有"关注"需要）
if(TK9==''){ L.push('<button>🔒 登录后可关注@onclick:java.toast(\'...\')</button>'); }
else       { L.push('<button>＋ 关注作者 '+lab+'@onclick:java.toast(IWRFO(...))</button>'); }
L.push(' ');
L.push('<button>📚 全部作品@onclick:java.openUrl(IWRFAUDS('+chr39()+au.id+chr39()+','+chr39()+au.un+chr39()+'))</button>');
L.push(' ');
L.push('<button>🌐 主页@onclick:java.startBrowser(IWRAFWWW('+chr39()+au.id+chr39()+','+chr39()+qu+chr39()+'),'+chr39()+qn+chr39()+')</button>');
```

> ★ 常见 bug：`IWRFAROW` 开头 `if(IWRG(Sv,'iwTk','')==''){return L;}`
> → **未登录时整行消失，连"全部作品"按钮也没了**。
> 改成把登录判据**下推到"关注"按钮内部**（用 `TK9` 变量 + 三元/if）。

### 6.2 深链（`addToBookshelf`）

```js
function IWRFAUDS(uid,un){
  return 'legado://import/addToBookshelf?src=' + encodeURIComponent(IWRAFURL(uid,un));
}
```

Legado 三级匹配书源（`AddToBookshelfDialog.kt`）：

1. URL 选项里的 `{"origin": "<bookSourceUrl>"}`
2. `getBookSourceAddBook(baseUrl)` —— 按**域名**匹配
3. 遍历所有**有 bookUrlPattern** 的源，用正则匹配

因此必须扩展 `bookUrlPattern`：

```
https?://[a-z0-9.-]*iwara[.](tv|ai)/(video|playlists|user)/[A-Za-z0-9_-]+(?=[,?]|$)
```

> `(?=[,?]|$)`：兼容「URL + ,{json选项}」形态，**又不会误匹配搜索/列表页**
> （因为 `bookUrlPattern` 命中会让 `BookList.kt:64` 把搜索结果当详情页解析）。

### 6.3 两个 URL 要分开

| 用途 | 函数 | 指向 |
|---|---|---|
| 书籍 URL / 深链 | `IWRAFURL(uid,un)` | API 地址（`?user=<UUID>...`） |
| 浏览器打开主页 | `IWRAFWWW(uid,un)` | 网页地址（`https://www.iwara.tv/users/<name>`） |

> 坑：`java.startBrowser` 传 API URL → 用户看到一堆 JSON，等于没用。

---

## 7. 降级方案（接口彻底失效时）

| 方案 | 做法 | 权衡 |
|---|---|---|
| **A. 打开网页主页** | 按钮 → `java.startBrowser(网页作者页)` | 100% 可用，但非原生目录 |
| **B. 留桩自动生效** | 保留完整逻辑；接口恢复即自动工作 | 用户可能长期看到报错 |
| **C. 混合（推荐）** | 按钮保留原生合集；失败时明确提示 + 提供「🌐 主页」 | 兼顾两者 |

**iwara 采用 C**：`📚 全部作品` + `🌐 主页` 并排。

---

## 8. 踩坑清单（K1~K14）

| # | 坑 | 说明与解法 |
|---|---|---|
| K1 | **`count` 正确但 `results` 是假的** | 最危险。必须校验 `results[].user.id`（§1/§5） |
| K2 | **参数名叫 `user` 但值是 UUID** | 别按字面传用户名（§2） |
| K3 | 正则 `[/]videos[?][^#]*[?&]xxx=` 恒不匹配 | `[?]` 已消费问号，`[^#]*` 吃掉参数名 → 用 `[?&](a\|b)=` 打头 |
| K4 | 非捕获组 `(?:a\|b)` 在旧 Rhino 不可靠 | 用 `(a\|b)` + 索引 `mv[2]` |
| K5 | 作者响应的 `user` 在 `results[].user`，不在顶层 | `IWRFAUO` 必须兜底，否则**作者行整行不渲染** |
| K6 | `if(iwTk==''){return L;}` 让新按钮也消失 | 登录判据下推到「关注」按钮内部 |
| K7 | `java.startBrowser` 传 API URL | 用户看不到内容 → 单独构造网页 URL |
| K8 | 书籍 URL 用非真实端点 | 框架先请求 bookUrl，404 会在 init 前就失败 |
| K9 | 锚点替换时 `\n` 是字面量还是真换行 | jsLib 里通常是**真实换行 `chr(10)`**；先 `js.count(anchor)` 验证 |
| K10 | 高频排查触发站点限流降级 | 冷却后再复测；别把限流当成接口失效 |
| K11 | `java.webView` 的 js 必须是**表达式**（IIFE） | 顶层 `return` 报 `Illegal return statement`；`var a=x;` 报 `missing )` |
| K12 | 全局变量传 `uid/un/pg` | 请求间串数据 → 注入进 init 返回的 JSON |
| K13 | 每页都返回多个 nextTocUrl | 会走并发 → **顺序不保证** → 只返回 1 个 |
| K14 | 空页静默返回空数组 | 给明确中文提示，别让用户面对空白目录 |

---

## 9. 验证方法论（四层，缺一不可）

### 第 1 层：语法
```bash
node --check <(cat jsLib)          # 完整 jsLib 语法
```

### 第 2 层：离线仿真（node，毫秒级迭代）
```js
const M = new Function('java','source','baseUrl','result', jsLib
  + '\nreturn {IWRAFU,IWRIDF,IWRAFIS,IWRAFINFO,IWRTOC,IWRAFNX,IWRAFL};'
)(fakeJava, fakeSource, '', null);

// ① 类型识别回归（不能破坏原有 video/playlist）
// ② URL 构造
// ③ 翻页链：造 N 页假数据，跑 while 链，断言 章节数/唯一URL数/顺序
```

翻页链断言的黄金三问：
- 总章节数 == 期望？
- 唯一 URL 数 == 总章节数？（防重复）
- 顺序正确？（`every((c,i)=>c.name.startsWith(String(i+1).padStart(3,'0')))`）

### 第 3 层：真机 eval_js（真实网络 + 真实 Rhino）
```js
// 直接调真实函数，观察真实响应
var s = IWRA(java, source, IWRAFU(UID,0,50,'name'));
var o = JSON.parse(s);
// ★ 关键断言：命中率
var hit=0; for(var i=0;i<o.results.length;i++){ if(o.results[i].user.id==UID) hit++; }
hit + '/' + o.results.length;   // 必须 100%
```

### 第 4 层：真机 debug_source 全链路
```
key = 完整的作者合集书籍 URL
→ 逐段检查：书名/作者/分类/字数/最新章节/简介/封面/目录列表大小/首章链接
```

> **导入前必做**：上传 dpaste → 用 `java.openUrl(深链)` 导入 →
> 用 `get_http_logs` 看 `GET <raw> -> 200` 作为**硬证据**（429/404 都算失败）。

---

## 10. 跨站移植表

换站点时**只需改这几处**，骨架不用动：

| 改动点 | iwara 的值 | 换成 |
|---|---|---|
| 作品接口 URL | `/videos?user=<UUID>&page=N&limit=50&sort=date` | 站点对应接口 |
| 作者 ID 形态 | UUID | 数字 / 短码 / 用户名 |
| 作者 ID 在响应中的位置 | `results[].user.id` | 按实际（可能是顶层 `creator.id`） |
| 归属校验字段 | `results[].user.id` | 按实际 |
| 作品链接构造 | `/video/<videoId>` | 按实际 |
| `count` 字段名 | `count` | 可能是 `total` / `totalCount` / `hasMore` |
| 每页上限 | 50 | 站点自己的上限 |
| 网页作者页 | `/users/<name>` | 按实际 |
| `bookUrlPattern` | `/(video\|playlists\|user)/...` | 加作者分支 |

**可保留不动**：`IWRAFNX` 翻页骨架、`IWRAFVFY` 校验骨架、`IWRFAUO` 兜底、
`IWRAFL` 字段结构、按钮与深链、注入式上下文传递。

---

## 11. 交付验收清单

- [ ] `check_source` 通过
- [ ] `debug_source`：书籍URL → 书名/作者/分类/字数/最新章节/简介/封面全对
- [ ] 目录条数 == `count`（或 count 的上限页数之和）
- [ ] 目录编号跨页连续、无重复、顺序正确
- [ ] 点进任一章 → 能解析出播放/阅读地址
- [ ] 作者行三个按钮都渲染（含**未登录**场景）
- [ ] 点「📚 全部作品」→ HTTP 日志出现 `videos?user=... -> 200`
- [ ] 非法作者 ID → 明确报错而非静默错内容
- [ ] 原有功能回归（单视频 / 播放列表 / 搜索 / 发现 全不受影响）
- [ ] dpaste 字节级校验 PASS + 深链导入硬证据 200

---

## 12. 对照档案

| 站点 | 作者作品接口 | 鉴权 | 备注 |
|---|---|---|---|
| iwara.tv | `GET /videos?user=<UUID>&page=N&sort=date&limit=50` | 匿名可用 | `?userid=` 已被反爬（**count 真、结果假**）；`/user/{id}/content/videos` 返回 forbidden |

**参考开源项目**：
- **yt-dlp** `yt_dlp/extractor/iwara.py` — `IwaraUserIE`（**决定性线索**）
- gallery-dl `gallery_dl/extractor/iwara.py` — `IwaraUserVideosExtractor`
- Moeary/IwaraTool、Izumiko/iwaradl、hare1039/iwara-dl、FoxSensei001/LoveIwara、xiatg/iwara-python-api

**相关文档**：
- `方法-详情页交互按钮选型树.md` — 按钮五通道选型
- `方法-详情页写操作按钮与关系态显示.md` — 关注/收藏这类"改服务端状态"的按钮
- `方法-目录顺序与章节去重铁律.md` — 链式保序 vs 并发错序
- `方法-深链保存书源与dpaste通道.md` — dpaste 上传 + 深链导入
- `方法-静默失败定位与探针法.md` — "不要推理，要打印"
