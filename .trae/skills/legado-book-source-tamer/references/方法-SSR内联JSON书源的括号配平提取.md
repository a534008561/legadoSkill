# 方法：SSR 内联 JSON 书源的括号配平提取（Modern.js / Next.js 类站点）

> 蓝本：`红果短剧（网页版）`（`https://hongguoduanju.com`，LegadoTeam 版，`bookSourceType=4` 视频）
> 成品：`/workspace/hongguo/hongguo_v11_one.json`（14435B，md5 `db93de8ef1240d1f3c7ae20ff098dcd0`）
> dpaste：`https://dpaste.com/7WBRPUK47.txt`
> 写作日期：2026-10-10
> 交叉引用：
> - 视频源骨架 / 播放链路 → `方法-视频书源完全指南.md`
> - `@js:` 规则返回值协议 → `方法-书源规则易错点.md`
> - 交付质量闭环（md5 回读 / dpaste）→ `方法-书源交付质量闭环.md`
> - 跨版本差异 → `方法-legado各版本行为差异对照.md`

---

## 目录

- 一、适用场景识别（什么时候该用本文）
- 二、★核心：括号配平截取器（不能贪婪、不能正则）
- 三、★三大传输/解析陷阱
- 四、字段提取：从 JSON 到 Legado 规则的映射
- 五、★`key` 变量在 bookList 上下文不存在（重大坑）
- 六、★`@js:` 顶层禁止 `return`（必须 IIFE）
- 七、红果短剧站点档案（可照抄的形态）
- 八、多形态站点（短剧 + 漫画）的类型切换
- 九、避坑清单 K1~K16
- 十、验证方法论（App 内 eval_js 四步法）
- 十一、通用结论

---

# 一、适用场景识别

## 1.1 什么样的站点需要这套方法

页面 HTML 里**不含结构化 DOM**，数据全部塞在**内联 `<script>` 里的一个巨型 JSON 对象**中。典型特征：

| 特征 | 红果实例 |
|---|---|
| HTML 里搜不到数据字段名 | `grep 'series_name' page.html` 无结果（因为数据在 JSON 里，但字段名会被 SSR 序列化） |
| 存在 `window.__INITIAL_STATE__` / `_ROUTER_DATA` / `__NEXT_DATA__` / `_SSR_DATA` | `_ROUTER_DATA = {...}` |
| 页面是 SSR 输出（view-source 有内容，但 jsoup 选择器取不到业务字段） | Modern.js（字节系 `rspack` 打包） |
| 数据 JSON 后紧跟一段 JS 代码（不能整体 `JSON.parse`） | `_ROUTER_DATA = {...}; function runWindowFn(){...}` |

## 1.2 与其他三类站点的区别

| 站点类型 | 取数方式 | 参考文档 |
|---|---|---|
| 传统 HTML 站 | jsoup CSS 选择器 | `references/css选择器规则.md` |
| 纯 JSON API 站 | `@js:JSON.parse(java.ajax(url))` | `方法-全加密API书源逆向与客户端可信重放.md` |
| **SSR 内联 JSON 站（本文）** | **括号配平截取 + JSON.parse + 字段映射** | 本文 |
| SPA + 加密接口站 | 逆向加密算法 | `方法-多层密钥AES与轮换签名逆向.md` |

---

# 二、★核心：括号配平截取器

## 2.1 为什么不能贪婪匹配

**错误写法 1（贪婪正则）**：
```js
var m = h.match(/_ROUTER_DATA = (\{[\s\S]*\});/);
```
→ `[\s\S]*` 会一直吃到页面末尾，`JSON.parse` 必失败。

**错误写法 2（非贪婪正则）**：
```js
var m = h.match(/_ROUTER_DATA = (\{[\s\S]*?\});/);
```
→ 遇到第一个 `};` 就停，但 JSON 内部有嵌套对象（`"req":{"a":1}`），会在内层 `}` 处截断。

**错误写法 3（lastIndexOf 取尾）**：
```js
var s = h.indexOf('{', start);
var e = h.lastIndexOf('}');
JSON.parse(h.substring(s, e+1));
```
→ 页面尾部还有 `window._SSR_DATA = {...}` 等其它 JSON，会把它们一并吃进来。

## 2.2 正确做法：字符级括号配平（含字符串状态机）

```js
function HG_RAW(h){
  if(!h)return '';
  var i=h.indexOf('_ROUTER_DATA = ');
  if(i<0)return '';
  i=h.indexOf('{',i);
  if(i<0)return '';
  var d=0,s=false,e=false,q='',c='';
  for(var k=i;k<h.length;k++){
    c=h.charAt(k);
    if(s){                                  // 在字符串内
      if(e){e=false;}                       // 转义字符，跳过下一个
      else if(c===HG_BS){e=true;}           // 反斜杠
      else if(c===q){s=false;}              // 字符串闭合
    }else{
      if(c===HG_Q||c===HG_SQ){s=true;q=c;}  // 进入字符串（记引号类型）
      else if(c==='{'){d++;}
      else if(c==='}'){d--;if(d===0)return h.substring(i,k+1);}  // 归零即完整
    }
  }
  return '';
}
```

**四个必须处理的细节**：

1. **字符串状态**：JSON 值里可能出现 `{` / `}`（如 `"intro":"他用{}占位"`），不排除会提前截断。
2. **转义字符**：`\"` 不能当作字符串结束（`"intro":"他说\"你好\""`）。
3. **单引号也要认**：部分站点把 JSON 混在单引号字符串里（红果的 `data-fn-args` 用了 HTML 实体化的 `&quot;`，但为兼容其它站仍应认）。
4. **`HG_BS` / `HG_Q` / `HG_SQ` 必须用 `String.fromCharCode` 生成**，不能裸写 `'\\'` / `'"'`——见第三章。

## 2.3 提取后的解析

```js
function HG_PICK(o,f){
  if(!o||!o.loaderData)return null;
  for(var k in o.loaderData){
    var v=o.loaderData[k];
    if(v&&typeof v==='object'&&v[f]!==undefined)return v;
  }
  return null;
}
```

**为什么用「按字段名遍历」而不是写死 key**：Modern.js 的 `loaderData` 键名随路由变化：

| 页面 | loaderData 键名 |
|---|---|
| `/` | `layout` / `page` |
| `/detail?series_id=X` | `detail_layout` / `detail_page` |
| `/player/S/V` | `player_layout` / `player_(series_id)/(vid)/page` |
| `/player/S` | `player_layout` / `player_(series_id)/page` |
| `/rank/hot-drama` | `rank_layout` / `rank_hot-drama/page` |
| `/category/real-drama` | `category_layout` / `category_$` |
| `/search/关键词` | `search_layout` / `search_(keyword)/page` |
| `/comic/X` | `comic_layout` / `comic_(id)/layout` / `comic_(id)/page` |

写死 key 会导致「换个页面就取不到」。**按特征字段名找**（如 `seriesDetail`、`video_player_info`、`searchList`、`recommendList`、`content`）才是稳的。

---

# 三、★三大传输/解析陷阱

## 3.1 MCP / JSON 传输层会破坏反斜杠与双引号

**症状**：本地 `node --check` 通过，导入 App 后规则报 `SyntaxError`。

**根因**：规则文本经过 JSON → MCP 参数 → GSON → 数据库多层转义，`"` 和 `\` 极易被吃掉一层。

**对策（零双引号零反斜杠纪律）**：

```js
var HG_Q  = String.fromCharCode(34);   // "
var HG_SQ = String.fromCharCode(39);   // '
var HG_BS = String.fromCharCode(92);   // \
var HG_LF = String.fromCharCode(10);   // 换行
```

**所有字符串拼接用 `HG_Q`，正则用字符类替代反斜杠**：

| 想写 | 改成 |
|---|---|
| `"\n"` | `HG_LF` |
| `/[0-9]+/` | 手写 `charAt` 数字循环（或 `[0-9]` 无需反斜杠） |
| `/\./` | `[.]` |
| `/\\/` | `HG_BS` |
| `"text"` | `HG_Q+'text'+HG_Q` |

**验证法**：`python3 -c "print(open('lib.js').read().count('\"'), open('lib.js').read().count(chr(92)))"` → 两者都应为 0。

## 3.2 转义后的 HTML 实体陷阱

红果的 `data-fn-args` 属性用了 `&quot;` 转义。如果规则里需要处理这类字符串：

```js
// 危险：实体字面量会被传输层解码
s.replace(/&lt;/g, '<')

// 安全：
s.split(String.fromCharCode(38)+'lt;').join('<')
```

**本项目实测**：不需要处理实体，因为 `_ROUTER_DATA` 里的 JSON 是原生未转义的。

## 3.3 `jsoup` 的 `script` 元素取不到 JSON（重要反例）

**尝试过的错误方案**：
```js
var doc = Packages.org.jsoup.Jsoup.parse(h);
var sc = doc.select('script');           // 13 个 script
var t = String(sc.get(10).html());       // ← 返回空字符串！
var d = String(sc.get(10).data());       // ← 返回 23KB，但 JSON.parse 报 "Expected end of stream at char 22458"
```

**原因**：jsoup 的 `html()` 对 `<script>` 返回空（script 内容是 CDATA），`data()` 虽然返回内容，但**外层包了 `_ROUTER_DATA = ` 前缀 + 尾部有其它 JS**，直接 `JSON.parse` 会失败。

**结论**：**不要用 jsoup 取 script 内容**，直接用 `indexOf` + 括号配平在原始 HTML 字符串上操作。

---

# 四、字段提取：从 JSON 到 Legado 规则的映射

## 4.1 列表规则：返回 JSON 字符串数组（E/LT 双版本通用）

```js
function HG_ITEM(sid,name,cover,kind,intro,last,url){
  var o={};
  o.name=String(name||'');
  o.url=(url&&String(url).indexOf('http')===0)?String(url):HG_DETAIL(sid);
  o.cover=String(cover||'');
  o.kind=String(kind||'');
  o.intro=String(intro||'');
  o.last=String(last||'');
  return String(JSON.stringify(o));    // ← 关键：转成 JSON 字符串
}
```

**为什么必须 `JSON.stringify`**：

| 返回值形态 | LT 版 | legado-E 版 |
|---|---|---|
| JS 数组 + 原生对象 | ✅ 能取 | ❌ 字段全空（E 版对 NativeObject 无 Mode.Js 分支） |
| **JS 数组 + JSON 字符串** | ✅ 能取 | ✅ 能取（走 Mode.Json → jsonpath） |

字段规则写 `$.name` / `$.url`，两版都走 JSONPath 直取。

## 4.2 详情规则：`init` 产出 JSON，其余字段用 `$.key`

```js
// ruleBookInfo.init
@js:(function(){
  var bu=String(baseUrl);
  var sid=HG_SID(bu);
  if(!sid)return '{}';
  var h='';
  try{ h=String(java.ajax(HG_BASE+'/detail?series_id='+sid)); }catch(e){ return '{}'; }
  var s=HG_INFO(h,sid);
  if(!s)return '{}';
  var o=JSON.parse(s);
  o.tocUrl=bu;                        // ★ 指向自身 → Legado 复用 HTML，零额外请求
  return String(JSON.stringify(o));
})()
```

字段规则：
```json
{
  "name": "$.name",
  "author": "$.author",
  "coverUrl": "$.cover",
  "intro": "$.intro",
  "kind": "$.kind",
  "lastChapter": "$.last",
  "tocUrl": "$.tocUrl"
}
```

**★ `tocUrl = bookUrl` 的收益（源码级）**：
`BookInfo.kt:157-161`：
```kotlin
book.tocUrl = analyzeRule.getString(infoRule.tocUrl, isUrl = true)
if (book.tocUrl.isEmpty()) book.tocUrl = baseUrl
if (book.tocUrl == baseUrl) { book.tocHtml = body }   // ← 复用详情页 HTML
```
`WebBook.kt:312`：
```kotlin
if (book.bookUrl == book.tocUrl && !book.tocHtml.isNullOrEmpty()) {
    BookChapterList.analyzeChapterList(..., body = book.tocHtml, ...)   // ← 不重发请求
}
```
→ 详情页与目录页同源时，**目录阶段零网络请求**（实测：详情 0.6s + 目录 0.5s 纯解析）。

## 4.3 目录规则：`chapterList` 返回数组

```js
@js:(function(){
  var bu=String(baseUrl);
  var sid=HG_SID(bu);
  if(!sid)return [];
  var isC=HG_ISCOMIC(bu);
  try{ if(isC)book.setType(64); else book.setType(4); }catch(e){}   // ★ 多形态站点必须
  var h='';
  try{ h=String(java.ajax(HG_BASE+'/detail?series_id='+sid)); }catch(e){ return []; }
  return HG_TOC(h,sid,bu);
})()
```

```js
function HG_TOC(h,sid,burl){
  var d=HG_DECODE(h,'seriesDetail');
  if(!d)return [];
  var sd=d.seriesDetail;
  var vids=sd.vid_list||[];
  var acc=sd.accessible_episode_cnt;
  if(!acc||acc<1)acc=0;
  var isC=HG_ISCOMIC(burl);
  var out=[];
  for(var i=0;i<vids.length;i++){
    var nm=(isC?'第'+(i+1)+'话':'第'+(i+1)+'集');
    if(i>=acc)nm=nm+' ⛔';        // ★ 标记不可播集数
    var u=isC?(HG_BASE+'/comic/'+sid+'?vid='+String(vids[i])):HG_PLAY(sid,String(vids[i]));
    out.push(String(JSON.stringify({name:nm,url:u})));
  }
  return out;
}
```

## 4.4 正文规则：短剧 mp4 / 漫画图片串

```js
@js:(function(){
  var bu=String(baseUrl);
  var h='';
  try{ h=String(java.ajax(bu)); }catch(e){ return '⚠ 无法访问页面，请稍后重试'; }
  if(HG_ISCOMIC(bu)){
    var imgs=HG_MANGA(h);
    if(imgs&&imgs.length>0)return HG_MHTML(imgs);
    return '⚠ 本话在网页版无法阅读。红果网页版仅开放试看，请在官方 App 观看全集。';
  }
  if(HG_IS404(h)){
    return '⚠ 本集在网页版无法播放。红果网页版每部剧仅开放前 3 集试看，请在官方 App 观看全集，或选择前 3 集。';
  }
  var u=HG_URL(h);
  if(!u)return '⚠ 未解析到播放地址，请稍后重试或换源。';
  return u;
})()
```

**404 检测**（关键：站点对不可播集返回 200 + 404 页面）：
```js
function HG_IS404(h){
  if(!h)return true;
  if(h.length<50000&&h.indexOf('not-found')>=0)return true;
  return false;
}
```
- 可播集：`len ≈ 100KB+`
- 不可播集：`len ≈ 37.9KB` + 含 `not-found` 类名
- **双重判据**（长度 + 关键词）比单一判据稳。

---

# 五、★`key` 变量在 bookList 上下文不存在（重大坑）

## 5.1 现象

搜索规则里写 `java.ajax(HG_BASE+'/search/'+java.encodeURI(String(key)))` →

```
ReferenceError: "page" 未定义
ReferenceError: "key" 未定义
```

## 5.2 源码依据

`AnalyzeRule.kt:896-914` 的 `evalJS()` bindings 全表：
```
java / cookie / cache / source / book / result / baseUrl / chapter / chapters /
title / src / nextChapterUrl / rssArticle / fromBookInfo
(+ paraIndex / paraData / page 三个 localBindings 可选)
```

`localBindings["page"]` 只在 `ReviewRuleParser.kt:132-134` 被 `setLocal` 注入（段评场景）。
**`BookList.kt` 全程不调用 `setLocal`** → 搜索/发现的 bookList 上下文里 **`key` 和 `page` 都不存在**。

## 5.3 解决方案：用 searchUrl 携带关键词，从 baseUrl 反解

**searchUrl**（模板里的 `key` 是 AnalyzeUrl 的 binding，存在）：
```
https://hongguoduanju.com/search/{{java.encodeURI(key)}}?hgk={{java.encodeURI(key)}}
```

**bookList 里反解**：
```js
var k='';
try{
  var bu=String(baseUrl);
  var i=bu.indexOf('hgk=');
  if(i>=0){ k=bu.substring(i+4); var q=k.indexOf('&'); if(q>=0)k=k.substring(0,q); k=decodeURIComponent(k); }
  if(!k){   // 兜底：从路径段取
    var j=bu.indexOf('/search/');
    if(j>=0){ k=bu.substring(j+8); var q2=k.indexOf('?'); if(q2>=0)k=k.substring(0,q2); k=decodeURIComponent(k); }
  }
}catch(e0){}
if(!k)return out;
```

**要点**：
- `decodeURIComponent` 用 **JS 原生**（Rhino 支持），`java.decodeURI` **不存在**（`java.encodeURI` 存在但语义是 `URLEncoder.encode`，会把空格变 `+`，且**不能反解**）。
- 参数名用自造的 `hgk=`（不污染站点参数），避免与站点自有参数冲突。
- 加兜底路径（万一 URL 模板被外部改动）。

## 5.4 分页处理

红果搜索接口**忽略 page 参数**（实测 `?page=2` 返回与第 1 页相同内容）。因此：

```js
// searchUrl 不带 {{page}}（避免被 AnalyzeUrl 处理成逗号分隔的分页语法）
"searchUrl": "https://hongguoduanju.com/search/{{java.encodeURI(key)}}?hgk={{java.encodeURI(key)}}"
```

`SearchModel.kt` 的 `searchPage++` 机制仍会触发第 2 次调用，但规则里返回空数组即可（Legado 会停止）。

---

# 六、★`@js:` 顶层禁止 `return`（必须 IIFE）

## 6.1 现象

```
com.script.ScriptException: 返回的值无效
Caused by: EvaluatorException: 返回的值无效
```

## 6.2 源码依据

`AnalyzeRule.kt:938-941`：
```kotlin
private fun compileScriptCache(jsStr: String): CompiledScript {
    return scriptCache.getOrPutLimit(jsStr, 16) {
        RhinoScriptEngine.compile(jsStr)     // ← 编译成"脚本"而非"函数"
    }
}
```
Rhino 的 `Context.compileString` 对顶层 `return` 报 `EvaluatorException: 返回的值无效`。

## 6.3 两种正确写法

| 写法 | 适用 | 示例 |
|---|---|---|
| **IIFE（推荐）** | 需要提前 return、逻辑复杂 | `@js:(function(){ if(x)return []; return y; })()` |
| 最后表达式 | 单行简单场景 | `@js:var a=[1,2]; a;` |

**IIFE 陷阱**：内部必须有显式 `return`，否则返回 `undefined`：
```js
(function(){ var x=[1,2]; x.length; })()   // → undefined ❌
(function(){ var x=[1,2]; return x.length; })()   // → 2 ✅
```

## 6.4 检查法（构建闸门）

```python
def check_iife(name, s):
    if not isinstance(s,str) or not s.startswith('@js:'): return
    body = s[4:].strip()
    if not body.startswith('(function()'):
        print('!! NOT IIFE:', name)
```

---

# 七、红果短剧站点档案

## 7.1 站点性质

| 项 | 值 |
|---|---|
| 域名 | `hongguoduanju.com`（`www` 也可，`m.` 无 DNS） |
| 运营方 | 抖音集团 / 北京笔墨留香科技 |
| 编码 | UTF-8 |
| 框架 | Modern.js（字节 `rspack` 打包）+ React SSR |
| WAF | **无**（实测 10+ 次请求无拦截） |
| 搜索频控 | **未探测到**（已按用户要求不做主动频率探测，`concurrentRate=2/1000`） |
| 登录 | **无账号体系**（`/login` `/user` `/mine` 全部 404） |
| UA 敏感性 | 不敏感（手机/桌面/无 UA 都能取到数据，模板有差异但核心 JSON 一致） |

## 7.2 URL 路由表

| 功能 | URL | 备注 |
|---|---|---|
| 首页 | `/` | `homeSections` 4 个区块 |
| 详情 | `/detail?series_id={id}` | 主力入口 |
| 播放（第1集） | `/player/{sid}` | 裸路径 |
| 播放（第N集） | `/player/{sid}/{vid}` | **仅前 3 集返回 200，第 4 集起 404** |
| 漫画 | `/comic/{bid}` | 独立链路 |
| 搜索 | `/search/{urlencode(kw)}` | **仅返回 10 条，忽略 page 参数** |
| 搜索联想 | `/incent_resource/suggestion?app_id=8662&web_id=x&count=20&query={kw}` | **返回 20 条，无需签名** |
| 榜单 | `/rank/hot-drama?page=N` | 20 条/页，**N>5 返回空** |
| 分类 | `/category/{real-drama\|comic-drama\|ai-drama\|comic}?page=N` | 24 条/页，real-drama 共 34 页 |

## 7.3 关键数据字段（`_ROUTER_DATA` → `loaderData`）

**详情页（`detail_page.seriesDetail`）**：
```
episode_cnt              总集数
accessible_episode_cnt   网页版可播集数（恒为 3）
pay_type                 付费类型
series_id / series_name / series_cover / series_intro
tags[]                   标签数组
celebrities[]            演员 [{nickname, avatar, sub_title, celebrity_id}]
vid_list[]               全部集的 vid（与集数等长）
```

**播放页（`player_(series_id)/(vid)/page`）**：
```
video_player_info.main_url    ★ mp4 直链（带时效签名 l=时间戳）
video_player_info.poster_url  海报
seriesDetail                  同上（全集数据）
```

**搜索页（`search_(keyword)/page`）**：
```
searchList[]   10 条，每条 {doc_type, name, keyword(=series_id), video_data{...}}
totalCount     总数（如 104）
```

**联想接口**：
```
{"suggest_list":[{"display_words":["名"],"keyword":"{series_id}","name":"名","video_data":{...}}]}
```
★ 注意：`keyword` 字段直接就是 `series_id`（19 位数字）。

## 7.4 ★网页版硬限制：每部剧仅前 3 集

**实测证据**（3 部剧 × 5 集）：
```
掌心窥爱  ep1 ✅  ep2 ✅  ep3 ✅  ep4 ❌404  ep5 ❌404
总裁是我前女友  ep1 ✅  ep2 ✅  ep3 ✅  ep4 ❌404  ep5 ❌404
首辅娇娘  ep1 ✅  ep2 ✅  ep3 ✅  ep4 ❌404  ep5 ❌404
```
- 404 页面特征：`len=37901` + `class="not-found-hVKMyd"` + `<title>` 无内容
- `accessible_episode_cnt` 字段恒为 `3`（12 部剧抽样全部为 3）
- 老剧（2024 年上线）与新剧同样限制

**尝试过的绕过方案（全部失败，记录备查）**：

| 方案 | 结果 |
|---|---|
| `?isInside=true` / `?isCrawler=true` / `?app_id=8662` / `?from=app` / `?web_id=X` | 全部 404 |
| Googlebot / Bingbot / Baiduspider UA | 全部 404 |
| 完整浏览器头（Accept / Accept-Language / Referer / Sec-Fetch-*） | 全部 404 |
| Cookie `ttwid`（从首页获取） | 404 |
| 建立会话后访问（先 GET 首页/详情页再访问 ep4） | 404 |
| `?vid={vid}` 查询参数形式 | 200 但**返回第 1 集**（参数被忽略） |
| `www.` 域名 | 404 |
| 带时间戳防缓存 `?_t=` | 404 |

**结论**：这是**服务端策略**，不是客户端标识问题。书源侧只能如实标注。

**书源处理**：
- 目录里给不可播集加 `⛔` 标记
- 正文返回明确中文提示（引导用户去官方 App）

## 7.5 播放直链特性

| 项 | 值 |
|---|---|
| 域名 | `v{N}-hgweb.qznovelvod.com`（N 随机，实测 v3/v11/v26） |
| 协议 | **mp4（非 HLS）** |
| 防盗链 | **无**（裸链 200，不需要 Referer / Cookie / UA） |
| Range 支持 | ✅ 206 |
| 时效 | 带 `l={yyyyMMddHHmmss}{hex}` 签名，实测**约 15 分钟后 403** |
| 应对 | **每次点开时实时解析**（不做缓存、不预取） |

**验证记录**：
```
旧 URL（约 1 小时前生成）→ 403
新 URL（实时解析）→ 200 / video/mp4 / 8449791 bytes
Range 请求 → 206 / ftyp 魔数正确
```

---

# 八、多形态站点（短剧 + 漫画）的类型切换

## 8.1 问题

站点同一书源内既有短剧（`/player/`，mp4）又有漫画（`/comic/`，图片串）。但 `bookSourceType` 只能取一个值。

## 8.2 源码依据

`WebBook.kt:306-307`（刷目录时）：
```kotlin
book.removeAllBookType()               // ← 清空所有类型位
book.addType(bookSource.getBookType()) // ← 只加书源类型（video=4）
```
→ 详情页 init 里设的 `book.setType(64)` 会被冲掉。

## 8.3 解决方案：在 chapterList 里按 URL 形态重新设类型

```js
@js:(function(){
  var bu=String(baseUrl);
  var sid=HG_SID(bu);
  if(!sid)return [];
  var isC=HG_ISCOMIC(bu);
  try{ if(isC)book.setType(64); else book.setType(4); }catch(e){}
  ...
})()
```

`BookType` 位掩码（`constant/BookType.kt`）：
```
video = 4
text  = 8
audio = 32
image = 64
```

**注意**：`try/catch` 必须包住（调试模式下 `book` 可能为 null）。

## 8.4 漫画链路（红果特有）

```
/comic/{book_id}                    → can_read_episode_cnt / content(JSON字符串) / next_vid
/comic/{book_id}?vid={vid}          → 同上（vid 参数实测被忽略，始终返回第 1 话）
content 解析 → chapter_info_list[{item_id, pic_list[{pic_url, low_pic_url, width, height}]}]
```

**红果漫画的额外限制**：`can_read_episode_cnt = 1`（仅第 1 话可读），且 `?vid=` 参数不生效。属于站点侧限制。

---

# 九、避坑清单 K1~K16

| # | 坑 | 后果 | 解法 |
|---|---|---|---|
| K1 | 贪婪正则取 JSON | 解析失败 | 括号配平状态机 |
| K2 | 非贪婪正则取 JSON | 内层 `}` 处截断 | 同上 |
| K3 | `lastIndexOf('}')` 取尾 | 吃到后续 JSON | 同上 |
| K4 | 用 jsoup `script.html()` 取内容 | 返回空 | 用 `indexOf` 在原始 HTML 上操作 |
| K5 | 规则里裸写 `"` / `\` | 传输层吃掉，SyntaxError | `String.fromCharCode(34/92)` |
| K6 | `@js:` 顶层 `return` | `返回的值无效` | IIFE 包裹 |
| K7 | IIFE 内漏 `return` | 返回 undefined，字段空 | 显式 `return` |
| K8 | bookList 里用 `key` / `page` | ReferenceError | 从 baseUrl 反解 |
| K9 | `java.decodeURI` | 函数不存在 | 用 JS 原生 `decodeURIComponent` |
| K10 | 列表返回原生对象（非 JSON 字符串） | E 版字段全空 | `String(JSON.stringify(o))` |
| K11 | `tocUrl` 不指向自身 | 目录阶段重复请求 | `tocUrl = bookUrl` |
| K12 | 多形态站点不在 chapterList 设 type | 漫画用视频播放器打开 | `book.setType()` |
| K13 | 404 页面当成功解析 | 空 URL 或错误提示 | `len<50000 && indexOf('not-found')` |
| K14 | 缓存播放直链 | 15 分钟后 403 | 每次实时解析 |
| K15 | 搜索分页不判空 | 无限重复 | 第 2 页起返回空数组 |
| K16 | `key` 参数名与站点冲突 | 站点行为异常 | 用自造参数名（如 `hgk=`） |

---

# 十、验证方法论（App 内 eval_js 四步法）

## 10.1 为什么必须 App 内验证

沙盒 Python 能验证「数据能不能取到」，但**不能验证**：
- Rhino 的 JS 语义差异（如 `===` 对 Java String 失败）
- Legado 规则引擎的返回值协议
- 传输层对规则文本的破坏

## 10.2 四步法

**第 1 步：原始数据可达性**
```js
var h=String(java.ajax('https://hongguoduanju.com/detail?series_id=X'));
java.log('len='+h.length+' hasRouter='+(h.indexOf('_ROUTER_DATA')>=0));
```

**第 2 步：解析函数验证（jsLib 已加载时可直接调）**
```js
var d=HG_DECODE(h,'seriesDetail');
java.log('name='+d.seriesDetail.series_name+' cnt='+d.seriesDetail.episode_cnt);
```

**第 3 步：完整规则模拟**
```js
var code="(function(){ ...规则原文... })()";
var r=eval(code);
java.log('result len='+r.length+' first='+String(r[0]).substring(0,100));
```

**第 4 步：落库后 md5 逐字段核对**
```js
function M(x){ return String(java.md5Encode(String(x))); }
java.log('jsLib md5='+M(source.getJsLib()));
```

**★ md5 比较陷阱**：`java.md5Encode` 返回 Java String，Rhino 里 `===` 比较会失败：
```js
if(M(a) === 'abc...') { }          // ❌ 恒 false
if(String(M(a)) === 'abc...') { }  // ✅ 必须 String() 包裹
```

## 10.3 字段级回读核对（本项目实测）

```
jsLib     = 48b4d9e21ff03eedb20c83f416eed197   ✅
loginUrl  = 9555f46218aa9db58732c516fdf7293b   ✅
loginUi   = 7defce822deb2dee61d52ab87dd242d8   ✅
searchUrl = f887af5250fbea7ebd544ea4c8ddec64   ✅
exploreUrl= b02ed8119ea03abca6012b8641aa178f   ✅
header    = 07acf1cf52b201e3b2ca944bd1abed16   ✅
init      = 9d6cc3ff2c9c4d2a28f051ffeb855020   ✅
content   = efba2797e9b328a1c4374e3a4e932ee3   ✅
toc       = dc453c3f7639c746b16d58450a6bf8e1   ✅
search    = 524113bfb7eb58d8d968d9df660f5482   ✅
explore   = 2260d8c105e7080dd0d9eb079bb3bebb   ✅
（15/15 与本地基线一致）
```

---

# 十一、通用结论

1. **SSR 内联 JSON 是 2025+ 的主流形态**（Modern.js / Next.js / Nuxt 都用），掌握括号配平提取器等于掌握了这一整类站点。
2. **不要相信任何"从 HTML 取结构化数据"的直觉**：先 `grep` 页面源码确认数据在 DOM 还是 script 里。
3. **零双引号零反斜杠纪律**能规避 90% 的「本地通过、App 报错」问题。
4. **`@js:` 一律用 IIFE**，比「记得不加 return」可靠得多。
5. **列表返回值用 JSON 字符串数组**是 E/LT 双版本最大公约数。
6. **`tocUrl = bookUrl`** 是零成本性能优化（目录阶段免请求）。
7. **遇到站点硬限制时，如实标注 + 中文提示**优于伪造数据（用户能理解限制，不能理解错误）。
8. **`key`/`page` 在 bookList 上下文不存在**是 Legado 的固有设计，用 `searchUrl` 携带参数是标准解法。
