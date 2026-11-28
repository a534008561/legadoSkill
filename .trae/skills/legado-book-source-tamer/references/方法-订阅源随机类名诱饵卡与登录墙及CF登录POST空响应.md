# 方法：订阅源「随机类名 + 诱饵卡 + 登录墙」三连改版修复（91PORN 261128 蓝本）

> 适用：小说/视频订阅源列表突然变空、条数对但内容错位、正文全空；站点给标题套随机类名、
> 往列表里混诱饵卡、对新内容加登录墙；以及「源内账号密码登录被 Cloudflare 返回空 body」的场景。
> 全部结论来自 261128 真机 WS 1123/1126 + LAN 回读 + qjs/esprima 离线验证。

---

## 一、三个独立故障，症状完全不同

| 症状 | 根因 | 判据 |
|---|---|---|
| 列表「解析成功，为空」 | 标题选择器失效 → `RssParserByRule.getItem` 里 `if (title.isBlank()) return null` 全部条目被丢 | WS 日志 `└获取标题` 后是空行，`└列表大小:N` 却 >0 |
| 列表有条目但重复/标题张冠李戴 | 站点混入**诱饵卡** | 同 viewkey 多标题、`playvthumb_N` 与 `thumb/N.jpg` 不一致 |
| 正文 100% 空 | 站点**登录墙**（3 天内新片仅会员） | 正文页有 `player_one` 但 `strencode2` 出现 0 次 |

三条必须分别定位，别用一条「站点改版」糊过去。

---

## 二、随机类名：标题迁进 `<bdi>`，外层 class 每次请求都变

261128 实测（同一小时内 4 次请求，4 个不同类名）：

```html
<!-- 列表页（新模板） -->
<div class="tb2af50"><bdi> 标题文字 </bdi></div>   <!-- p1 -->
<div class="tbfaedc"><bdi> 标题文字 </bdi></div>   <!-- p2 -->
<div class="td88a07"><bdi> 标题文字 </bdi></div>   <!-- p3 -->
<div class="t8a2906"><bdi> 标题文字 </bdi></div>   <!-- 中文页 -->
```

- 老模板（搜索结果页 / 正文页侧栏）仍是 `<span class="video-title title-truncate">标题</span>`。
- `.video-title` 在列表页出现 **0 次**，所以旧规则 `ruleTitle=.video-title@text` 恒空。

**正解（双模板兼容，零类名依赖）**

```
@js:
var t = '';
try { t = String(java.getString('.video-title@text') || '').trim(); } catch (e0) { t = ''; }
if (!t) { try { t = String(java.getString('bdi@text') || '').trim(); } catch (e1) { t = ''; } }
if (!t) { try { var b = result.select('bdi'); if (b.size() > 0) t = String(b.get(0).text() || '').trim(); } catch (e2) { t = ''; } }
t = t.replace(/&amp;#0?39;/g, "'").replace(/&#0?39;/g, "'").replace(/&amp;/g, '&').trim();
t;
```

> 该站把单引号写成 `&amp;#039;`（双层实体），jsoup `text()` 出来仍是 `&#039;`，要手动再解一次。

---

## 三、诱饵卡：结构与真卡完全一致，只有两处隐藏指纹

261128 列表页每页 41~45 张卡，`Videos 1 - 24 of 151062` 却写着 24 —— 实测**真卡恰好 24 张**，其余是诱饵：

| | 真卡 | 诱饵卡 |
|---|---|---|
| `<a href>` 的 `c=` 参数 | `cvqqa` | **`acvqqa`** |
| `id="playvthumb_N"` 与 `img src=.../thumb/M.jpg` | **N === M** | 多数 N ≠ M（打乱） |
| 标题 | 与本视频一致（正文页 h4 可核对） | 借用别的视频标题 |
| viewkey | 24 个互不重复 | 与真卡**共用 viewkey**，同一 viewkey 可重复 5 次 |

- 三页 + 搜索结果页实测：`c=cvqqa` 恒为 24 条、viewkey 唯一、标题唯一；`acvqqa` 为 14~21 条。
- 诱饵卡会**穿插在真卡中间**（第 0 张就是诱饵，导致列表首条直接消失）。
- 用 viewkey 去重**不够**：同一 viewkey 的真卡与诱饵卡标题不同，留哪张决定对错。

**正解：双判据过滤 + 兜底（就地改 jsoup `Elements`，见第五节）**

```
good = (c !== 'acvqqa');
if (good && pid && tid) good = (pid === 'playvthumb_' + tid);   // pid 取 attr('id') 全串
// 真卡不足 3 条 ⇒ 站点又换形态，退回「仅按 viewkey 去重」保证列表不空
```

---

## 四、发布时间：标签随页面语言变，必须双语

站点按 **Accept-Language** 切语言（不是 cookie）：`Accept-Language: zh-CN` 时整站中文，
`Views/Favorites/Comments` → `热度/收藏/留言`，`Added` 区变成 `4 分钟  前`。

原规则 `rulePubDate=<js>…java.getString('.well@text')…</js>` 在新模板里把整块文本糊成一行
（261128 WS 实锤：`🔁00:01:29 ⏰HD00:01:29标题…热度:186收藏:2留言:1积分:000 🔥186`）。

**正解：结构正则 + 英文标签优先 + `class="info"` 顺序盲取**

```
var dur  = (h.match(/class="duration"[^>]*>\s*([0-9:]+)/)||[])[1] || '';
var add  = (h.match(/<\/span>\s*-\s*([^<]{0,40}?)<br/i)||[])[1] || '';         // 新模板 " - 3 分钟 前"
if (!add) add = (h.match(/<span class="info">(?:Added|添加|上傳|上传)[^<]*<\/span>\s*([^<]{0,40}?)<br/i)||[])[1] || '';
// 英文标签
views = /Views:\s*<\/span>\s*([0-9][0-9,]*)/i …
// 中文/未知语言：按 class="info" 的「标签:数字」顺序取，跳过添加时间/来源
if (!views && !fav && !cm) { … /(add|from|添加|来源|上傳|上传|upload)/i.test(lbl) ⇒ continue … }
```

实测输出：英文 `🔁00:00:13 ⏰12 minutes 👁186 ⭐2 💬1`；中文 `🔁00:14:09 ⏰5 分钟 前 👁1 ⭐0 💬0`。

> `result.html()` 在 `<js>` 里可用（`result`=条目 Element，`src`=同内容）；拿不到时退回 `String(result)`。

---

## 五、E 版兼容：绝不要从规则返回 JS 原生数组

E 版 `AnalyzeRule.getElements` 是 `result as List<Any>` 硬转 —— 返回 Rhino `NativeArray` 直接 CCE；
LT `getElements` 则显式处理 `NativeArray`。两版通吃的写法：

**就地删改 `java.getElements()` 返回的 jsoup `Elements`（它本身就是 `ArrayList<Element>`）**

```
var a = java.getElements('.col-xs-12');
var meta = [], i;
for (i = 0; i < a.size(); i++) { … meta.push({good: good, vk: vk}); }
for (i = a.size() - 1; i >= 0; i--) { if (!meta[i].good) a.remove(i); }
a;                       // 仍是 Elements，双版都当 List
```

- `java.getElements` 在规则 `@js` 里的 `java` 是 **AnalyzeRule**（`bindings["java"] = this`），
  不是 SourceJsExtensions；`java.getString/java.getElements` 都来自它。
- `new Packages.java.util.ArrayList()` 在 LT 可用（`add/size/toString` 正常，`getClass()` 返回 null 别慌），
  但没必要——就地 remove 不需要任何 Java 类，E 版更安全。

---

## 六、登录墙：新内容仅会员，游客只看 3 天前

261128 正文页（3 天内新片）特征：

```html
<b>New videos are for logged-in members only. Please log in or register for free to watch.
   Guests can watch videos older than 3 days.</b>
```

- 页面仍有 `<video id="player_one">`，但**没有** `strencode2`，也没有 `<source src>`；
- 同一规则打 3 天前的视频页：`strencode2` 出现 1 次，直链正常。
- 所以「正文空」不是改版，是登录墙 —— 必须把这条判断写进正文规则的**失败分支**，
  否则用户永远看到「站点可能再次改版」的误导提示。

```
var gate = /logged-in members only|Guests can watch videos older than/i.test(html);
if (!url || !/^https?:\/\//.test(url)) {
  if (gate) { java.toast('🔒 该视频是 3 天内的新片，游客不可看；请在登录面板登录后重试'); }
  else      { java.toast('⚠ 正文直链未取到，站点可能再次改版'); }
  '';
} else { url; }        // 成功分支必须逐字节保持原样（裸 URL 才能被内置播放器接管）
```

### 6.1 登录态怎么进 CookieStore（LT/E 双版源码实锤）

| 入口 | Cookie 同步 |
|---|---|
| `WebViewActivity.onPageFinished`（`java.startBrowserAwait` 走这个） | `CookieStore.setCookie(url, CookieManager.getInstance().getCookie(url))` |
| `WebViewLoginFragment`（源无 loginUi 时的内置登录页） | `CookieStore.setCookie(source.getKey(), cookieManager.getCookie(url))` |
| `BackstageWebView`（`java.webView`） | 同样 `CookieStore.setCookie(url, cookie)` |
| `BaseSource.putLoginHeader('{"Cookie":"…"}')` | `CookieStore.replaceCookie(getKey(), cookie)` |

- `CookieStore` 按 **二级域名** 存（`NetworkUtils.getSubDomain`）：`418.sol148.com` 登录后
  `*.sol148.com` 通用；换到 `a.26702.app` 这种**另一个域名**必须重新登录 —— 面板要提示。
- `java.getCookie(url)` 读的就是这个库；`cookie.removeCookie(url)` 可清（`cookie` 绑定 = CookieStore）。
- `enabledCookieJar=true` 才会把 Cookie 带进规则请求。

### 6.2 图形验证码可以在源内直接问用户

`java.getVerificationCode(imageUrl)` 会**下载图片并弹窗**让用户输入，返回值就是输入的文本；
它与后续 `java.post` 共用同一个 CookieJar 会话，服务端 `$_SESSION` 对得上。
比在登录面板里塞一个「验证码」输入框（用户看不到图）实用得多。

---

## 七、Cloudflare 会把源内登录 POST 打成「200 + 空 body」

261128 实测（`418.sol148.com`，Cloudflare）：

| 请求 | 结果 |
|---|---|
| `POST /login.php` 空 body | 200，12556B（登录页正常） |
| `POST /login.php?凭据` | **200，0 字节**，header `content-encoding: gzip`，无 `Set-Cookie` |
| `POST /index.php` `a=1` | 200，57416B（正常） |

- 结论：带凭据的登录 POST 被 CF 挡掉（返回空 gzip 响应），源内直登**不可靠**。
- 判据：`java.post` 返回的是 **jsoup `Connection.Response`**（有 `statusCode()` / `body()` / `url()`，
  **没有** `code()`），`String(resp.body()).length < 100` 即视为被拦。
- 正解：直登失败 → **自动降级到 `java.startBrowserAwait(login.php,'登录')`**（WebView 登录 + Cookie 同步），
  并 toast 说明原因；不要只报「登录失败」让用户以为是密码错。

```
if (!html || html.length < 100) {
  toast('⚠ 账号直登被站点风控拦截（空响应）→ 自动改用内置浏览器登录');
  PN_webLogin();  return;
}
```

### 7.1 登录态检测别只看「有 cookie」

- 探测页用 `my_video.php`（游客态必定含 `id="loginForm"` / `password` / `captcha_input`）。
- 已登录页导航会出现 `logout`；游客页只有 `login.php` 链接（实测游客页 `logout` 出现 0 次）。
- 判定顺序：`logout` → 已登录；登录表单特征 → 游客；都没有 → `unknown`（**不要**默认当已登录）。
- 校验失败/被 CF 挡回时统一报「已提交但未确认，请点🔍检查登录状态复核」。

---

## 八、分页：`.page_number` 已消失，改用 `.pagingnav`

新老模板统一结构（列表页与搜索结果页相同）：

```html
<div id="paging"><div class="pagingnav">
  <span class="pagingnav">1</span><a href="?next=watch&page=2">2</a>…<a href="…page=11">11</a><a href="?next=watch&page=2">»</a>
</div></div>
```

- 当前页 = `.pagingnav span` 第一个文本；总页数 = `.pagingnav a` 文本里的最大数字（`»` parseInt 为 NaN 自动忽略）。
- 旧的 `.page_number@value` / `.pagingnav@form@a.-2@text` 取不到 ⇒ 会 toast「第NaN/NaN页」，
  必须改成上面两条，且**取不到就不提示**。
- `ruleNextPage=page` 仍然有效（`uppercase()=="PAGE"` ⇒ nextUrl=sortUrl，`{{page}}` 自增），不写死上限。

---

## 九、其它本轮结论

1. **搜索冷却**：非 VIP 搜索页 9 秒内重复会返回
   `<div class="errorbox">You are not vip member. Please wait 9 second to retry.</div>`。
   不要主动探频率；在 sourceComment/面板里写明「非VIP 9 秒冷却」即可。
2. **搜索页是老模板**：结果条目仍是 `<span class="video-title">`，链接是**相对路径**
   `view_video.php?viewkey=…&c=cvqqa`（无前导 `/`）⇒ `ruleLink` 必须自己拼绝对地址
   （`PN_base() + '/' + u.replace(/^\.?\//,'')`），不能指望 baseUrl 兜底（换线路会钉死旧域）。
3. **UA**：本源把 Quark UA 换成标准 Chrome Android 后列表/正文均正常；UA 不影响登录墙（三种 UA 都挡）。
4. **摘要卡片文案别信页面头**：`Videos 1 - 24 of 151062` 与真实卡片数不一致，真值以过滤后为准。

---

## 十、验证链（本轮实际执行顺序）

1. **离线**：esprima 全规则/面板 JS 语法 + QuickJS `eval` 跑正文内层规则（老片出完整 `&f=` 直链、
   登录墙片出空+正确 toast）+ Python 复刻筛选（4 个页面 kept=24、标题/时间字段逐条核对）。
2. **真机规则链**：LAN `/saveRssSources`（**数组**）→ `/getRssSources` 回读 diff 0 →
   WS1123（LT）/1126（E）看 `└列表大小:24`、标题、`🔁… ⏰… 👁… ⭐… 💬…`、图片、`└获取文章链接`。
3. **正文可用性**：临时把 `sortUrl` 换成「本月最热」（首条必是 3 天前的片）→ WS 看到完整
   `https://…mp4?…&f=…` → **立刻把正式 sortUrl 存回**并回读确认（临时改 sortUrl 是验证正文的可靠手法）。
4. **双版**：LT 1122/1123 与 E 1125/1126 分别落库、回读、WS；E 版无 `enableReadRecord` 字段。

> 铁律复用：诊断桩/临时改动每轮都会覆盖落库 ⇒ 收尾必须重存正式版并回读 diff 0。
