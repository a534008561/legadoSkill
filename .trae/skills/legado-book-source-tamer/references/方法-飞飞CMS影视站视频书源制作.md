# 方法：飞飞CMS(FeifeiCMS) 影视站视频书源制作

> 2026-10-18 花都动漫（hd.huadudm.com）实战提炼  
> 适用：所有 `stui_` / `ffcms_` 前缀的 FeifeiCMS 影视站（大量成人/短剧站同模板）

---

## 0 一句话

飞飞CMS 是**高度模板化**的影视 CMS：认准 `stui-vodlist` / `detail-item` / `player_data` 三个锚点，一套规则可以横扫几十个同模板站点。

---

## 1 识别站点（30 秒判定）

打开首页，看这几处任一命中即是 FeifeiCMS：

| 特征 | 值 |
|---|---|
| JS 全局变量 | `<script>var feifeicms={"path":"","mid":"1",...}</script>` |
| 搜索框 class | `ffcms_wd` |
| 登录按钮 class | `ffcms_user login-box` |
| 列表 class | `ul.stui-vodlist` / `div.stui-vodlist__box` |
| 播放页 | `<script src="/static/js/player.js">` + `var player_data=` |

---

## 2 URL 结构总表

```
搜索    /vodsearch/{关键词}----------{页码}---.html
分类    /vodshow/{分类}--------{页码}---.html
筛选    /vodshow/{分类}-{地区}-{语言}-{年份}-{字母}-{状态}-{金币}-{页码}-{排序}.html
详情    /voddetail/{id}.html
播放    /vodplay/{id}-{线路}-{集数}.html
```

### 2.1 分页占位（最容易搞错的地方）

`/vodshow/15-----------.html` 里 `15` 后面有 **11 个连字符 = 12 段**：

```
index:  0    1     2      3     4      5     6     7     8
段名:  type area  lang  year letter state money page order
```

- **第 7 段是页码**（0-based 计数时是 index 7）
- **第 8 段是排序**：`time`（按时间）/ `hits`（按人气）/ `up`（按点赞）

实测对照：
```
/vodshow/15-----------.html      → 第1页
/vodshow/15--------1---.html     → 第1页（显式）
/vodshow/15--------2---.html     → 第2页
/vodshow/15--hits---------.html  → 人气榜第1页
/vodshow/15--hits------2---.html → 人气榜第2页   ← 注意是 6 个连字符不是 8 个
```

> ⚠️ **别凭感觉数连字符**。正确做法：在列表页 HTML 里 `grep 'pagination'`，直接抄站点自己生成的 href。

### 2.2 搜索分页只有 10 个连字符

```
/vodsearch/{kw}-------------.html     → 第1页（13 个 -）
/vodsearch/{kw}----------2---.html    → 第2页
```
**与 vodshow 的段数不同**（vodsearch 少一个 money 段）。抄站点分页链接最稳。

### 2.3 分类 0 是空壳

`/vodshow/0-----------.html` 返回 1072 B 占位页（HTTP 200，无列表）。
**分类必须从 1 开始枚举**，且要实际验证每个 ID 有数据。

---

## 3 页面结构锚点

### 3.1 列表条目

```html
<ul class="stui-vodlist clearfix">
  <li class="col-md-5 col-sm-4 col-xs-2">
    <div class="stui-vodlist__box">
      <a class="stui-vodlist__thumb picture w-thumb img-shadow"
         href="/voddetail/28106.html" title="射雕外传6卷桃花绿福">
        <img class="lazyload img-shadow"
             src="/hdys/img/load.gif"
             data-original="https://a.7976.top/upload/vod/....jpg">
        <span class="pic-tag pic-tag-b">01:27:22</span>   <!-- 时长 -->
        <span class="pic-tag pic-tag-t">3D动漫</span>      <!-- 分类 -->
        <span class="pic-tag pic-tag-l">👍 44</span>       <!-- 点赞 -->
        <span class="pic-tag pic-tag-r">205</span>         <!-- 浏览 -->
      </a>
      <div class="stui-vodlist__detail">
        <h4 class="title text-overflow">
          <a href="/voddetail/28106.html" title="射雕外传6卷桃花绿福">射雕外传6卷桃花绿福</a>
        </h4>
        <span class="text text-overflow text-muted">📆 2026-09-28</span>
        <span class="pull-right">👀 26.5k</span>
      </div>
    </div>
  </li>
</ul>
```

**关键点**：
- 封面是**懒加载**：`src` 是 `load.gif` 占位，真图在 `data-original`
- `title` 属性比 `text()` 干净（`text()` 可能含子标签）
- 分类 / 时长在 `span.pic-tag-t` / `span.pic-tag-b`，**不在** `detail` 区

### 3.2 详情页字段（非 og: meta！）

```html
<div class="stui-vodlist__detail detail-flex">
  <div class="detail-item">
    <strong class="label-width">名称：</strong>
    <span class="detail-content">绿帽向纲手</span>
  </div>
  <div class="detail-item"><strong class="label-width">标题：</strong><span class="detail-content">【火影忍者】绿帽向纲手 中字</span></div>
  <div class="detail-item"><strong class="label-width">类别：</strong><span class="detail-content"><a>大屁股</a> <a>巨乳</a> ...</span></div>
  <div class="detail-item"><strong class="label-width">分类：</strong><span class="detail-content"><a>3D动漫</a></span></div>
  <div class="detail-item"><strong class="label-width">日期：</strong><span class="detail-content">2025-11-02</span></div>
  <div class="detail-item"><strong class="label-width">时长：</strong><span class="detail-content">11分钟</span></div>
</div>
```

**必须按标签名取值，不能按索引**——不同书之间字段数量会变（有的没有"类别"、有的没有"时长"）。

```js
function lab(key){
  var items=doc.select('div.detail-item');
  for(var i=0;i<items.size();i++){
    var it=items.get(i);
    var k=String(it.select('strong.label-width').text()).replace(/[：:\s]/g,'');
    if(k===key) return String(it.select('span.detail-content').text()).trim();
  }
  return '';
}
```

### 3.3 正文：`player_data` 三层结构

```html
<script type="text/javascript">
var player_data={
  "flag":"play","encrypt":2,"trysee":0,"points":0,
  "link":"\/vodplay\/20076-1-1.html",
  "link_next":"","link_pre":"",
  "url":"JTY4JTc0JTc0JTcwJTcz...",
  "url_next":"","from":"hdys","server":"","note":"",
  "sid":1,"nid":1
}
</script>
```

**解密（`encrypt=2`）**：
```
base64Decode(url)  →  "%68%74%74%70%73..."  →  decodeURIComponent × N  →  https://.../index.m3u8
```

**解密（`encrypt=1`）**：
```
unescape(url)  →  https://.../index.m3u8
```

**注意**：
- 站点自带 `base64decode()` 是自定义实现（`player.js` 里），标准 base64 结果一致
- 多层 url-encode 的层数**不固定**（不同 CDN 不同），必须**循环到稳定**：
  ```js
  for(var i=0;i<5;i++){
    var nx=decodeURIComponent(u);
    if(nx===u) break;
    u=nx;
  }
  ```
- 用 `if(u.indexOf('http')!==0) throw` 做**最终校验**，防止解出半截垃圾当直链

### 3.4 播放页也含详情信息

`/vodplay/{id}-{线路}-{集数}.html` 里有：
```html
<p class="stui-player__detail detail">
  <strong>分类：</strong><a href="/vodshow/15-----------.html">3D动漫</a>
  <strong>日期：</strong><font>2026-10-18</font>
  <strong>观看：</strong><span>1.6k 次</span>
</p>
<strong>名称：</strong><a href="/voddetail/30008.html">仙子的修行4下</a>
```
**但目录仍应从详情页取**（播放页只有当前线路的 playlist，详情页有全部）。

---

## 4 规则模板（可直接复制）

```jsonc
{
  "bookSourceType": 4,
  "bookUrlPattern": "https?://hd[.]huadudm[.]com/voddetail/[0-9]+[.]html",
  "searchUrl": "{base}/vodsearch/{{java.encodeURI(key)}}----------{{page}}---.html",

  "ruleSearch": {
    "bookList": "@js:(function(){ /* 见 §5.1 通用列表解析器 */ })()",
    "name": "$.n", "bookUrl": "$.u", "coverUrl": "$.c", "intro": "$.m",
    "author": "", "kind": "", "lastChapter": "", "wordCount": "",
    "checkKeyWord": "中字"
  },

  "ruleBookInfo": {
    "init": "@js:(function(){ /* 见 §5.2 详情解析器 */ })()",
    "name": "$.n", "author": "$.a", "kind": "$.k", "intro": "$.i",
    "coverUrl": "$.c", "lastChapter": "$.l", "wordCount": "$.w", "tocUrl": "$.t"
  },

  "ruleToc": {
    "chapterList": "@js:(function(){ /* 见 §5.3 目录解析器 */ })()",
    "chapterName": "$.n", "chapterUrl": "$.u",
    "nextTocUrl": "", "isVolume": "", "preUpdateJs": ""
  },

  "ruleContent": {
    "content": "@js:(function(){ /* 见 §5.4 正文解密 */ })()"
  }
}
```

---

## 5 可复用代码

### 5.1 通用列表解析器（搜索 / 发现共用）

```js
@js:(function(){
  var doc=null;
  try{
    doc=(typeof result!=='undefined'&&result&&typeof result.select==='function')
        ? result : Packages.org.jsoup.Jsoup.parse(String(result));
  }catch(e){ return []; }
  var uls=doc.select('ul.stui-vodlist');
  if(!uls||uls.size()===0) return [];
  // ★ 取 li 数量最多的那个 ul（详情页会混入"猜你喜欢"）
  var best=null,bestN=-1;
  for(var i=0;i<uls.size();i++){
    var n=uls.get(i).select('li').size();
    if(n>bestN){ bestN=n; best=uls.get(i); }
  }
  if(!best||bestN<=0) return [];
  var out=[],lis=best.select('li');
  for(var j=0;j<lis.size();j++){
    var li=lis.get(j);
    var a=li.select('h4.title a').first();
    if(a===null) continue;
    var href=String(a.attr('href'));
    if(href.indexOf('/voddetail/')<0) continue;
    var name=String(a.attr('title')).trim();
    if(!name) name=String(a.text()).trim();
    if(!name) continue;
    var cover='';
    var img=li.select('img').first();
    if(img!==null){
      cover=String(img.attr('data-original')).trim();
      if(!cover) cover=String(img.attr('src')).trim();
      if(cover.indexOf('load.gif')>=0) cover='';
    }
    var cat='',dur='';
    var st=li.select('span.pic-tag-t').first();
    if(st!==null) cat=String(st.text()).trim();
    var sb=li.select('span.pic-tag-b').first();
    if(sb!==null) dur=String(sb.text()).trim();
    var meta='';
    var sp=li.select('span.text').first();
    if(sp!==null) meta=String(sp.text()).trim();
    var bits=[];
    if(cat) bits.push(cat);
    if(dur) bits.push(dur);
    if(meta) bits.push(meta);
    out.push({n:name,u:href,c:cover,m:bits.join(' · '),k:cat});
  }
  return out;
})()
```

### 5.2 详情解析器

```js
@js:(function(){
  var html=String(result);
  var doc=Packages.org.jsoup.Jsoup.parse(html);
  function lab(key){
    var items=doc.select('div.detail-item');
    for(var i=0;i<items.size();i++){
      var it=items.get(i);
      var k=String(it.select('strong.label-width').text()).replace(/[：:\s]/g,'');
      if(k===key) return String(it.select('span.detail-content').text()).trim();
    }
    return '';
  }
  var name=lab('名称');
  if(!name){                                   // 兜底：从 <title> 里取《书名》
    var t=String(doc.title()), m=t.match(/《([^》]+)》/);
    if(m) name=m[1];
  }
  var title=lab('标题'), cat=lab('分类'), tags=lab('类别');
  var date=lab('日期'), dur=lab('时长');
  var intro='';
  var md=doc.select('meta[name=description]').first();
  if(md!==null){
    intro=String(md.attr('content')).trim();
    intro=intro.replace(/^[\s\S]*?详情介绍[：:]/,'')          // 去掉"本站为您提供X的详情介绍："
               .replace(/[，,]?好看的[\s\S]*?推荐。?$/,'');   // 去掉"，好看的X资源推荐。"
  }
  // 简介去重（title / intro 常与 name 重复）
  var seen={};
  function uniq(x){
    var t=String(x||'').trim();
    if(!t) return '';
    var k=t.replace(/[\s【】《》\[\]()（）_]/g,'');
    if(k.length<2||seen[k]) return '';
    seen[k]=1; return t;
  }
  var bits=[];
  var t1=uniq(title); if(t1) bits.push(t1);
  var t2=uniq(intro); if(t2) bits.push(t2);
  if(cat) bits.push('分类：'+cat);
  if(tags) bits.push('标签：'+tags.replace(/\s+/g,' / '));
  if(dur) bits.push('时长：'+dur);
  if(date) bits.push('更新：'+date);
  var cover='';
  var im=doc.select('div.stui-vodlist__box img').first();
  if(im!==null){
    cover=String(im.attr('data-original')).trim();
    if(!cover) cover=String(im.attr('src')).trim();
    if(cover.indexOf('load.gif')>=0) cover='';
  }
  // kind 去重（分类与类别常重复）
  var kp=[],ks={};
  function kadd(x){ var t=String(x||'').trim(); if(!t||ks[t])return; ks[t]=1; kp.push(t); }
  kadd(cat);
  if(tags){ var arr=tags.split(/\s+/); for(var k=0;k<arr.length;k++) kadd(arr[k]); }
  return JSON.stringify({
    n:name, a:'', k:kp.join(','), i:bits.join('\n'),
    c:cover, l:'', w:dur||'', t:''       // t:'' → tocUrl 留空，复用详情页 HTML
  });
})()
```

### 5.3 目录解析器（零额外请求）

```js
@js:(function(){
  var html=String(result);
  var doc=Packages.org.jsoup.Jsoup.parse(html);
  var bid='';
  try{ bid=String(book.bookUrl); }catch(e){}
  var m=bid.match(/[/]voddetail[/]([0-9]+)/);
  if(!m){ try{ m=String(baseUrl).match(/[/]voddetail[/]([0-9]+)/); }catch(e2){} }
  if(!m) throw new Error('无法识别书籍ID，请刷新详情页后重试');
  var id=m[1];
  var out=[],seen={};
  // ★ 必须按 id 过滤：详情页的"猜你喜欢"也含 /vodplay/ 链接
  var as=doc.select('a[href*=vodplay]');
  for(var i=0;i<as.size();i++){
    var h=String(as.get(i).attr('href'));
    var mm=h.match(/[/]vodplay[/]([0-9]+)-([0-9]+)-([0-9]+)[.]html/);
    if(!mm) continue;
    if(mm[1]!==id) continue;
    var key=mm[2]+'-'+mm[3];
    if(seen[key]) continue;
    seen[key]=1;
    out.push({n:'第'+mm[3]+'集',u:'/vodplay/'+mm[1]+'-'+mm[2]+'-'+mm[3]+'.html'});
  }
  if(out.length===0) out.push({n:'正片',u:'/vodplay/'+id+'-1-1.html'});
  return out;
})()
```

### 5.4 正文解密

```js
@js:(function(){
  var html=String(result);
  var m=html.match(/var\s+player_data\s*=\s*([\s\S]*?)<\/script>/);
  if(!m) throw new Error('未找到播放数据：页面结构可能已变更，请刷新目录后重试');
  var raw=m[1].replace(/;\s*$/,'').trim();
  var d=null;
  try{ d=JSON.parse(raw); }catch(e){
    var m2=raw.match(/\{[\s\S]*"nid"\s*:\s*[0-9]+\}/);
    if(m2){ try{ d=JSON.parse(m2[0]); }catch(e2){} }
  }
  if(!d) throw new Error('播放数据解析失败');
  var enc=String(d.encrypt||'');
  var u=String(d.url||'');
  if(!u) throw new Error('该资源暂无播放地址（可能已下架或需要会员）');
  if(enc==='1'){
    try{ u=unescape(u); }catch(e3){}
  }else if(enc==='2'){
    try{ u=java.base64Decode(u); }catch(e4){}
    for(var i=0;i<5;i++){                 // 多层 url-decode，循环到稳定
      var nx=u;
      try{ nx=decodeURIComponent(u); }catch(e5){ nx=u; }
      if(nx===u) break;
      u=nx;
    }
  }
  if(u.indexOf('http')!==0) throw new Error('播放地址解密失败（加密方式可能已变更）');
  return u;
})()
```

---

## 6 避坑清单

- **K1** 分类 0 是空壳（1072 B 占位页），从 1 开始。
- **K2** `vodshow` 与 `vodsearch` 的连字符段数**不同**，抄站点分页 href。
- **K3** 详情字段按**标签名**取值，不能按索引（字段数量会变）。
- **K4** 封面必须取 `data-original`，`src` 是 `load.gif` 占位。
- **K5** 列表页有多个 `ul.stui-vodlist`（详情页更多），取 **li 最多**的那个。
- **K6** 目录必须按 **bookUrl 里的 id** 过滤，否则"猜你喜欢"会被当成章节。
- **K7** `player_data` 的 `encrypt` 有 1/2 两种，都要处理。
- **K8** 多层 `decodeURIComponent` 必须循环到稳定，不能写死层数。
- **K9** 解出的 URL 必须 `indexOf('http')===0` 校验，否则会把垃圾当直链。
- **K10** `tocUrl` 返回空串 → Legado 复用详情页 HTML，**零额外请求**（`BookInfo.kt:157`）。
- **K11** 裸 IIFE 规则**必须加 `@js:` 前缀**，否则被当 CSS 选择器抛 `SelectorParseException`。
- **K12** `bookUrlPattern` 不能匹配搜索/分类/播放页，否则搜索会被当详情页解析。
- **K13** `kind` 走 `getStringList`，只用**纯 text 值**，别做复杂拼接。
- **K14** 站点"搜索请间隔10秒"可能只是**占位提示**，实测不拦（别急着写限频绕过）。
- **K15** 视频 CDN 的 404 多是**短时频控**，不是 header 问题（见配套文档）。

---

## 7 移植到其他 FeifeiCMS 站

改 4 个常量即可：

```python
BASE = 'https://新站域名'
PAT  = 'https?://新站域名/voddetail/[0-9]+[.]html'   # 用 [.] 避免反斜杠
NAME = '▶ 新站名'
GROUP= '视频'
```
规则本体**不用动**（模板一致）。  
**例外**：部分站改了 class 前缀（`stui_` → `ffcms_` 或自定义），需同步替换选择器。

---

## 8 验收清单

| 项 | 标准 |
|---|---|
| 搜索 | 关键词有结果，`书籍总数 > 0`，封面/书名/详情链接非空 |
| 详情 | 书名、分类、简介、封面 全非空 |
| 目录 | 章数 ≥ 1，章节名非空，链接可点 |
| 正文 | 返回 `https://.../index.m3u8` 或 `.mp4` 直链 |
| 发现 | 每个入口都有列表；第 2 页与第 1 页内容不同 |
| 书源URL正则 | 匹配详情页、**不匹配**搜索/分类/播放页 |
| check_source | 通过 |
| 实播 | WebView `<video>` 能 `readyState=4` 且 `duration>0` |
