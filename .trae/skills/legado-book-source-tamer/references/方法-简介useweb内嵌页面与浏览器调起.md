# 简介 useweb 内嵌页面与浏览器调起（startBrowser / openUrl / iframe）完全指南

> **样本**：黑料网 v3.1 (`hlwf6.com`)、黄果剧场 (`huangguo.video`)、找书啦 (`zhaoshu.la`)
> **整理时间**：2026-09-11
> **验证版本**：LegadoTeam 官方版 + legado-E (Luoyacheng/legado-E) 双版源码级验证
> **难度等级**：★★★★（简介区可编程 UI + 三通道浏览器调起 + 跨版本兼容）

书源 `ruleBookInfo.intro` 返回 `<useweb>` 包裹的 HTML，详情页简介区会变成一个**真 WebView**——可以在里面放按钮、样式、脚本，甚至内嵌整站网页。这是 Legado 官方特性（非 hack），但有一堆源码级陷阱。本文是三个书源实战 + 两版 App 源码 diff 后的完整沉淀。

---

## 一、useweb 机制原理（源码级）

### 1.1 数据链路：从 intro 规则到 WebView

```
ruleBookInfo.intro 返回字符串
  ↓ BookInfo.analyzeBookInfo (BookInfo.kt:122)
intro.trimStart() 以 <usehtml> / <md> / <useweb> 开头?
  ├─ 是 → book.intro = introTrimS 原样保存（★跳过 HtmlFormatter.format 净化）
  └─ 否 → HtmlFormatter.format(intro)（所有 < > 会被转义，按钮全废）
  ↓ BookInfoActivity.showBookIntro (BookInfoActivity.kt:542)
intro?.startsWith("<useweb>") == true
  → html = intro.substring(8, intro.lastIndexOf("<"))   ★注意：取的是【整串最后一个】"<"
  → WebViewPool.acquire() 取池化 WebView
    · webView.javaScriptEnabled = true
    · webView.domStorageEnabled = true
    · setDarkeningAllowed(夜间模式)
  → webView.loadDataWithBaseURL(bookUrl, html, "text/html", "utf-8", bookUrl)
  → 塞进 binding.tvIntroContainer (FrameLayout)
```

**同类标记**：`<usehtml></usehtml>`（TextView 渲染，支持 `@onclick:`）、`<md></md>`（Markdown）。只有 `<useweb>` 是真 WebView。

### 1.2 shouldOverrideUrlLoading 的生死线（CustomWebViewClient）

内嵌 WebView 里点击链接的分流规则：

| scheme | 行为 |
|---|---|
| `http` / `https` | **return false → 原地导航**——内嵌 WebView 直接跳走，你的按钮页永久丢失！ |
| `legado://` / `yuedu://` | startActivity\<OnLineImportActivity\>（打开另一本书的深链） |
| 其他（tel: mailto: 等） | 弹确认框后 openUrl |

**推论**：useweb 页面内**绝不放 http(s) 直链**。要展示网址就写纯文本（用户可长按复制），要跳转就用 `java.openUrl()` 调起（见下文）。

---

## 二、页面里能调用什么？——WebJsExtensions 注入 API 完全清单

showBookIntro 时 App 注入三个 Java 对象到页面（`addJavascriptInterface`，对象名每次随机——但全局变量 `java` 由注入脚本 `getInjectionString` 统一暴露）：

```js
// 注入脚本实际做的事（源码 WebJsExtensions.getInjectionString）
const java = window.随机名1; delete window.随机名1;   // → WebJsExtensions 实例
const source = window.随机名2; delete window.随机名2;  // → BaseSource 实例
const cache = window.随机名3; delete window.随机名3;  // → WebCacheManager
```

**只有带 `@JavascriptInterface` 注解的 public 方法才能被页面 JS 调用**（Android WebView 安全限制）。两版实测清单：

### ✅ 页面可直调（两版一致）

| 方法 | 签名 | 用途 |
|---|---|---|
| `java.openVideoPlayer(url, title)` | (String, String) | 内置全屏播放器（GSY/ExoPlayer，m3u8+AES-128 直播） |
| `java.openVideoPlayer(url, title, isFloat)` | (String, String, Boolean) | 悬浮窗播放（旧版无 3 参方法需 try/catch 降级） |
| `java.openUrl(url)` | (String) | **走 OpenUrlConfirmActivity = 外部浏览器确认页**（legado:// 深链除外） |
| `java.toast(msg)` / `java.longToast(msg)` | (String) | 提示（WebJsExtensions 子类带注解） |
| `java.ajax(url)` | (String) → String | 网络请求（带书源 header/CookieJar） |
| `java.connect(urlStr, header)` | 同上 | OkHttp 请求 |
| `java.get / java.post / java.head` | (url, body?, header, timeout?) | HTTP 全家桶 |
| `java.log(msg)` | → String | 日志 |
| `java.getString(rule, content, isUrl)` | | 在页面里跑 Legado 规则引擎！ |
| `cache.getFromMemory(key)` | | 内存缓存 |
| `source.get/put(key, value)` | | 书源变量读写 |

### ❌ 页面调不到（重要！）

| 方法 | 原因 | 替代方案 |
|---|---|---|
| `java.startBrowser(url, title)` | **两版 JsExtensions 均无 @JavascriptInterface 注解** | ① iframe 内嵌（第五章）② 造虚拟章节在规则上下文调（见 4.1） |
| `java.request("run", [jsCode], id)` 分发器 | useweb 场景 activity=null → 静默失败（找书啦/huangguo 双证） | `java.ajax` + `java.getString` 组合拳 |
| `java.startBrowserAwait` | 同 startBrowser | 同上 |

**辨别技巧**：页面里 `typeof java.startBrowser` 是 `'function'`（JS 可见）但**调用直接无效/静默**——注解缺失不报错，只是不注册到 JS 桥。用 try/catch 包住 + alert 验证返回不可靠，最可靠的是翻源码看注解。

---

## 三、三条硬约束（血泪教训）

### 约束 1：首尾格式

```
intro 必须严格以 '<useweb>' 开头（前面只能空白）
intro 必须严格以 '</useweb>' 结尾
```

因为截取是 `substring(8, lastIndexOf("<"))`——**整串最后一个 `<` 必须是 `</useweb>` 的 `<`**。若用户文本里还有裸 `<`，截取会在错误位置截断，页面残废。

### 约束 2：正文用户文本全部转义

所有动态内容（书名/简介/URL）拼进 HTML 前必须转义 `<` `>` `&` `"`，防止截断/破结构：

```js
function H(s){s=String(s||'');s=s.split('&').join('&amp;');s=s.split('<').join('&lt;');
  s=s.split('>').join('&gt;');s=s.split(NL).join('<br>');return s}      // HTML 显示转义
function JS(s){s=String(s||'');s=s.split(BS).join(BS+BS);s=s.split(Q).join(BS+Q);
  s=s.split('<').join(BS+'u003c');s=s.split(NL).join(' ');return s}    // JS 字符串转义
// Q=String.fromCharCode(34), BS=String.fromCharCode(92) —— 零反斜杠写法防 MCP 转义
```

### 约束 3：列表页 intro 必须纯文本

`ruleSearch.intro` / `ruleExplore.intro` **绝不能**返回 useweb/HTML——列表是纯文本展示，会把标签全部露出来。只有 `ruleBookInfo.intro` 才能玩 useweb。

### 附加约束（踩过就懂）

- **img src 必须双引号**：官方 `AppPattern.imgPattern = <img[^>]*src="([^"]*...)"` 硬性要求，无引号写法匹配不到→图不显示。JS 里用 `String.fromCharCode(34)` 生成双引号。
- **HTML 无引号属性值禁空格**：`style=width:100%` 合法，`style=padding:9px 26px` 非法（提前结束属性值）→ 改 `padding:10px`。
- **规则字符串内不能有真实换行**（书源 JSON 多层转义必坏）——用 `String.fromCharCode(10)` 占位。
- **`</script>` 要拆写**：`'</scr'+'ipt>'`，否则部分解析器提前终止。

---

## 四、三种浏览器调起方式对比（核心决策表）

| 方式 | 调用位置 | 内置/外部 | 两版兼容 | 适用场景 |
|---|---|---|---|---|
| `java.startBrowser(url, title)` | **规则上下文**（@js: 规则 / ruleToc / ruleContent） | **内置** WebViewActivity | ✅ 两版都可用 | 造一个「🌐 章节」，点开=正文规则 JS 调起 |
| `java.startBrowser(...)` | useweb 页面 JS | — | ❌ 无注解调不到 | 不可用（用 iframe 替代） |
| `java.openUrl(url)` | 任意 | **外部**（OpenUrlConfirmActivity 确认页） | ✅ | 兜底、用户明确要"去浏览器看" |
| **iframe 内嵌** | useweb 页面 HTML | **内置且无缝**（不离开详情页） | ✅ WebView 原生 | 站点无 X-Frame-Options 时的最优解 |

### 4.1 规则上下文调 startBrowser 的标准姿势（黑料网验证）

目录造虚拟章节（fragment 保证 URL 唯一不进 HTTP）：

```js
// ruleToc.chapterList —— 返回 JSON 字符串数组（跨版本铁律！）
var out=[String(JSON.stringify({name:'📖 图文阅读',url:b}))];
if(有视频){
  out.push(String(JSON.stringify({name:'🎬 视频播放',url:b+'#video'})));
  out.push(String(JSON.stringify({name:'🌐 视频播放(内置浏览器)',url:b+'#browser'})))}
return out
// 字段规则：chapterName = $.name，chapterUrl = $.url（纯键名，勿用 @js:，见第七章）
```

```js
// ruleContent.content —— 🌐 章节的正文规则里调起
if(u.indexOf('#browser')>-1){
  var od2='';var ok=false;
  try{java.startBrowser(pg,tt);ok=true;od2='✅ 已调起内置浏览器，退出可回到本页'}
  catch(e5){od2='⚠️ startBrowser调起失败: '+e5}
  if(!ok){try{java.openUrl(pg);od2='✅ 已请求打开浏览器'}catch(e6){}}  // 外部兜底
  return '🌐 内置浏览器播放'+NL+'▶ 播放页: '+pg+NL+NL+od2
}
```

**注意**：startBrowser 调起后**立即返回**（不等待浏览），正文返回提示文字即可。章节 URL 的 `#browser` fragment 不进 HTTP 请求且天然唯一（BookChapter 只按 URL 去重）。

### 4.2 openUrl 的真相（两版行为一致）

```
openUrl(url):
  url 以 legado:// 或 yuedu:// 开头 → OnLineImportActivity（深链，直达书籍详情页！）
  否则 → OpenUrlConfirmActivity（外部浏览器确认页，标题显示书源名）
```

**误用警示**：想在简介里"打开内置浏览器"用 `java.openUrl(网页)` 是**错的**——它弹的是外部浏览器确认框。深链 `legado://import/addToBookshelf?src=...` 才是 openUrl 的正道用法（跳转 App 内另一本书）。

---

## 五、iframe 内嵌完整网页 = 真·内置浏览器（黑料网 v3.1 方案）

### 5.1 原理

useweb 本身就是 WebView → WebView 里跑 `<iframe src="https://站点/">` = **把整个目标站嵌在简介区里**。用户不离开详情页，滚动/评论/看视频全能操作，比 WebViewActivity（startBrowser）更无缝。

### 5.2 前提验证：目标站必须无 iframe 防护

```bash
# 检查响应头（沙盒或 java.head）
curl -I https://目标站/页面
# 必须同时满足：
# ① 无 X-Frame-Options 头（或值非 DENY/SAMEORIGIN）
# ② 无 Content-Security-Policy: frame-ancestors 限制
```

黑料网 3 条线路实测全部无防护 → iframe 直嵌成功。若站点有防护 → iframe 显示空白 → 必须走 startBrowser 章节（4.1）。

### 5.3 完整按钮+折叠 iframe 模板（黑料网 v3.1 生产版）

```js
// 简介 HTML 生成部分（@js: 规则内）
h+='<div class="vb vb2" onclick=IF(this)>🌐 内嵌浏览器播放</div>';
h+='<div id=fwWrap style=display:none>'
  +'<div class=hd>🌐 内嵌播放页 <span style=color:#1e88e5;font-size:13px onclick=CFW()>(点击收起)</span></div>'
  +'<iframe id=fw class=fw src=about:blank></iframe></div>';
// CSS: .fw{border:1px solid #ddd;border-radius:10px;margin:10px 0;width:100%;height:70%;min-height:300px;background:#fff}

// 页面脚本部分
function IF(el){                    // 展开并加载
  var w=document.getElementById('fwWrap');var f=document.getElementById('fw');
  if(!w||!f){IHELP();return}        // 容器缺失→降级
  w.style.display='block';f.src=PAGE;window.scrollTo(0,f.offsetTop-60)}
function CFW(){document.getElementById('fwWrap').style.display='none'}  // 收起
function IHELP(){                    // 三级降级链
  try{if(typeof java!=='undefined'&&java.startBrowser){java.startBrowser(PAGE,TT);return}}catch(e){}  // ①（多数版本静默失败）
  try{if(typeof java!=='undefined'&&java.openUrl){java.openUrl(PAGE);return}}catch(e2){}             // ② 外部浏览器确认页
  alert('此版本不支持内嵌浏览器')}    // ③
```

### 5.4 按钮点击时动态重抓（解决时效签名）

视频直链类地址通常有时效（黑料 m3u8 签名约 1 小时）。按钮点击时 `fetch` 重抓详情页解析最新地址，失败回退烘焙进页面的旧直链：

```js
function PV(el,n,f){                 // n=第几个视频，f=是否悬浮
  var L=el.getAttribute('data-l');   // 备份按钮文案
  el.textContent='⏳ 获取中...';
  var fin=function(u){el.textContent=L;                 // 恢复文案
    if(u){try{java.openVideoPlayer(u,TT,f)}catch(e2){alert('调起失败:'+e2)}}
    else{alert('未获取到视频地址，请稍后重试')}};
  var fail=function(){fin(FB[n]||'')};                  // 回退旧直链
  try{fetch(PAGE).then(function(r){return r.text()}).then(function(t){
    var u='';try{var doc=new DOMParser().parseFromString(t,'text/html');
      var ds=doc.querySelectorAll('div.dplayer');
      if(ds.length>n){var c=JSON.parse(ds[n].getAttribute('config'));u=(c.video&&c.video.url)||''}}
    catch(e){}fin(u||FB[n]||'')}).catch(fail)}catch(e){fail()}}
```

---

## 六、完整可复用模板（黑料网 v3.1 intro 规则全文）

**规则形态**：`ruleBookInfo.intro = "@js:" + 下述 IIFE`（配套 jsLib 里 `J(s)=Jsoup.parse`、`NL()` 等）

```js
(function(){
var Q=String.fromCharCode(34);      // 双引号（零内嵌双引号，防 JSON 转义地狱）
var BS=String.fromCharCode(92);     // 反斜杠
var NL=String.fromCharCode(10);    // 换行
var d=J(result);                    // 详情页 Document
var m=d.select('meta[property=og:description]');
var tx=m.size()>0?String(m.first().attr('content')):'';   // 纯文本简介
var dps=d.select('div.dplayer');var n=dps.size();
if(n===0){return tx}                // ★非视频文章直接返回纯文本（不该 useweb）
var FB=[];                          // 烘焙视频直链数组
for(var i=0;i<n;i++){var fu='';try{var c=JSON.parse(String(dps.get(i).attr('config')));
  fu=String((c.video&&c.video.url)||'')}catch(e){}FB.push(fu)}
var tt='';try{tt=String(d.select('h1.detail-title').first().text())}catch(e2){}
var PAGE='';try{PAGE=String(baseUrl||'')}catch(e3){}
PAGE=PAGE.split(String.fromCharCode(35))[0];               // ★剥离 fragment 防污染
function H(s){...见约束2...}   function JS(s){...见约束2...}
var fb='';for(var j=0;j<FB.length;j++){if(j>0)fb+=',';fb+=Q+JS(FB[j])+Q}
// —— HTML 组装（样式+简介+播放按钮+悬浮+内嵌iframe）——
var h='<style>.vb{...}.vb2{background:#1e88e5}...fw{...}</style>';
h+='<div class=hd>📋 简介</div><div class=it>'+H(tx)+'</div>';
h+='<div class=hd>🎬 视频播放(共'+n+'个)</div>';
for(var k=0;k<n;k++){h+='<div class=vb data-l='+Q+'▶ 立即播放 '+(k+1)+Q+' onclick=PB(this,'+k+')>▶ 立即播放 '+(k+1)+'</div>'}
h+='<div class="vb vb3" onclick=PF(this)>🪟 悬浮播放</div>';
h+='<div class="vb vb2" onclick=IF(this)>🌐 内嵌浏览器播放</div>';
h+='<div id=fwWrap style=display:none>...<iframe id=fw class=fw src=about:blank></iframe></div>';
// —— 页面脚本（PV/PB/PF/IF/CFW/IHELP 见第四五章）——
h+='<script>';
h+='var PAGE='+Q+JS(PAGE)+Q+';var TT='+Q+JS(tt)+Q+';var FB=['+fb+'];';
h+="function PV(el,n,f){...}function PB(el,n){PV(el,n,false)}function PF(el){PV(el,0,true)}";
h+="function IF(el){...}function CFW(){...}function IHELP(){...}";
h+='</scr'+'ipt>';
return '<useweb>'+h+'</useweb>'
})()
```

**配套要点**：
- jsLib 的 `J()` 在 useweb 规则上下文可直接用（jsLib 自动求值进共享作用域）
- `baseUrl` fragment 剥离：黑料网案例中 debug 带 `#browser` 请求会污染详情页 baseUrl → 目录章节 URL 也被污染 → **chapterList/intro 里统一 `split('#')[0]` 清洗**
- 图文封面/图片：`<img src="绝对URL">` 精简格式（imgPattern 硬要求双引号 src）

---

## 七、跨版本差异对照（LegadoTeam vs legado-E）

源码 diff 实锤（2026-09-10，LT master vs E main）：

| 项 | LegadoTeam | legado-E | 影响 |
|---|---|---|---|
| useweb 渲染 | ✅ 同款 | ✅ 同款 | 无差异 |
| 注入 java（WebJsExtensions） | openVideoPlayer✓ openUrl✓ toast✓ ajax✓ | 同左 | 无差异 |
| `openUrl` 行为 | 外部确认页 | 外部确认页 | **两版都不是内置浏览器！** |
| `startBrowser` 页面调用 | ✗ 无注解 | ✗ 无注解 | 都要 iframe 或章节方案 |
| `startBrowser` 规则调用 | ✅ | ✅ | 章节方案两版通吃 |
| `getString` 对 @js:列表条目 | ✅ 有 Mode.Js→evalJS 分支 | ❌ **只有键值直取** | ★E版 bookList/chapterList 必须返回 JSON 字符串+纯键名规则 |
| loginUi `<js>` 解析 | ✅ | ✅ | 无差异 |
| jsLib 变量 source.get/put | ✅ 持久化 | ✅ 持久化 | 无差异 |
| exploreKinds 缓存 | 内存 map | aCache 持久(md5 key) | E 版改 exploreUrl 后需刷新发现 |
| Rhino | htmlunit corejs | 原版 1.7.14 | NativeArray 都实现 List，互转兼容 |

**★跨版本列表铁律（本次最大教训）**：`bookList`/`chapterList` 用 `@js:` 返回**JSON 字符串数组**（`arr.push(String(JSON.stringify({name,url}))`），字段规则用**纯键名字符串**（`$.name`/`$.url`）。字符串条目两版都走 Mode.Json→jsonpath，行为完全一致。E 版对 JS 对象条目（NativeObject）会把 `@js:xxx` 当键名直取 → 全空 → 条目全被过滤/章节全被丢。

---

## 八、避坑清单（按踩坑频率排序）

1. **useweb 页面里放 http 链接 = 按钮页丢失**（shouldOverrideUrlLoading 返回 false 原地导航）。深链 legado:// 可用，http 网址写纯文本。
2. **`java.openUrl` 不是内置浏览器**——是外部浏览器确认页（OpenUrlConfirmActivity）。内置要 startBrowser（仅规则上下文）或 iframe。
3. **E 版 @js: 列表条目全空**——见第七章铁律，返回 JSON 字符串+纯键名。
4. **intro 尾部裸 `<` 截断页面**——lastIndexOf("<") 陷阱，用户文本必须转义 &lt;。
5. **`</script>` 直接写会提前终止**——拆成 `'</scr'+'ipt>'`。
6. **规则内真实换行**——书源 JSON 传输层转义地狱，统一 fromCharCode 占位。
7. **MCP save_source 传高密度转义必坏**——全书源 JS 零反斜杠零内嵌双引号（fromCharCode 生成），单行压缩。
8. **img 无引号 src 不显示**——AppPattern.imgPattern 硬要求双引号。
9. **非视频文章别包 useweb**——判空 `return tx` 返回纯文本，否则空按钮页很尴尬。
10. **页面脚本避免反引号模板字符串**——真机 WebView 支持，但 QuickJS 沙盒/部分工具链不支持，统一单引号最稳。
11. **baseUrl 带 fragment 污染**——章节 URL `#browser` 会渗进详情页 baseUrl，chapterList/intro 统一 split('#')[0] 清洗。
12. **startBrowser 无需等待**——调起即返回，正文规则返回说明文字即可。

## 九、验证方法论

1. **离线端到端**：jsoup mock（只实现用到的选择器）+ IIFE 完整跑 → 校验生成的 HTML（useweb 首尾/iframe/按钮数）→ 提取 `<script>` 块 `node --check`（见 `/workspace/hlwf6/test_intro.js` 模板）。
2. **MCP debug_source**：`<详情页绝对URL>` 走详情→目录→正文全链路，简介输出在"获取简介"日志里可直接肉眼核对按钮 HTML。
3. **useweb 渲染验证**：手机上 `getLoginInfoMap` 式白盒不可用；直接看详情页简介区是否有样式/按钮即成功（渲染失败会显示原始标签或空白）。
4. **iframe 可行性预检**：HEAD 请求看 X-Frame-Options/CSP——沙盒 python urllib 或规则里 `java.head(url, '{}')`。
5. **E 版行为模拟**：拉 GitHub 两版源码 diff 定位分支差异 + class 文件解析确认接口实现 + 离线模拟 getString 走行。
