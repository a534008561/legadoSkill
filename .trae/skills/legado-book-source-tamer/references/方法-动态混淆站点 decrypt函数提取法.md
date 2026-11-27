# 动态混淆站点：执行站点解密函数法

> 蓝本：www.69shu.xyz（69書吧繁体站），2026-11-27 首次完整实践
> 适用：每次请求都更换 JS 变量名 / data 属性名 / 加密算法 / base64 段数 / XOR 常量的反爬站。

## 0 核心信条

> **不要逆向算法，要借用算法。**

站点每次请求都重新生成混淆脚本：同一本书的目录页，第一次是 XOR 链，第二次是 RC4，
第三次是 rotate+XOR；变量名、属性名、key 长度、base64 分段数全部随机。
硬编码任何一套算法都只能稳定一次。**正解：把站点内联脚本里的解密函数原样提取出来，
在 Legado 规则 JS 沙盒里 eval 并调用**，让站点自己的代码解密自己的数据。

## 1 混淆页特征识别

目录页：
```html
<dl id="_随机7位" data-随机属性="base64前缀...">
  <dd><span class="_随机" data-随机属性="37828">第1章 ...</span></dd>
  ...
</dl>
<script>(function(){try{
  var A=document.getElementById("_随机7位");
  var B=(A.getAttribute("data-随机属性")||'')+["base64段1","段2"].join('');
  var F=function(P){ ... atob(P) ... return X; };
  var C=F(B).split('\n');
  ...
}})();</script>
```
正文页：
```html
<div id="chaptercontent"><div id="_随机" data-随机属性="base64..."></div></div>
<script>... var F=function(P){...return Uint8Array...};
var bytes=F(base64拼接); TextDecoder→JSON.parse→{c:[...],o:[...]};
按 o 索引从 c 取字符串拼成正文 HTML ...</script>
```

关键观察：
- `getElementById` / `getAttribute` 的名字每次变，但**出现顺序和角色固定**
- 解密函数总是 `var FUNC = function(PARAM){ ... return X; };`
- base64 总是「容器属性前缀 + 脚本内 `[...].join('')` 段」
- 目录配置明文固定 7 行；正文配置是 `{c, o}` 乱序重组

## 2 解密函数提取四件套（通用骨架）

```js
@js:
var html = String(result);
var scripts = html.match(/<script[^>]*>([\s\S]*?)<\/script>/g) || [];
var sc = '';
for (var i=0; i<scripts.length; i++) {
  var t = scripts[i].replace(/^<script[^>]*>/,'').replace(/<\/script>$/,'');
  if (t.indexOf('atob') >= 0 && t.length > 800) sc = t;   // 目录>800 正文>1500
}
// ① 容器 id 与属性名：按出现顺序取
var id = (sc.match(/getElementById\(["']([^"']+)["']\)/)||[])[1];
var attrs = [], ar = /getAttribute\(["']([^"']+)["']\)/g, m;
while ((m=ar.exec(sc))!==null) attrs.push(m[1]);
var cattr = attrs[0];                       // 容器上的 base64 前缀属性
// ② 容器属性前缀
var tag = (html.match(new RegExp('<[^>]*id="'+id+'"[^>]*>'))||[''])[0];
var b64p = (tag.match(new RegExp(cattr+'="([^"]*)"'))||[])[1] || '';
// ③ 脚本内 base64 段
var jm = sc.match(/\[([\s\S]*?)\]\.join\(['"]{2}\)/), segs=[], qr=/["']([A-Za-z0-9+\/=]{10,})["']/g;
if (jm) while ((m=qr.exec(jm[1]))!==null) segs.push(m[1]);
// ④ 解密函数定义
var fm = sc.match(/var\s+(\w+)\s*=\s*function\s*\(\s*(\w+)\s*\)\s*\{[\s\S]*?return\s+\w+;\s*\};/);
```

## 3 沙盒执行：必须提供的 stub

站点解密函数内部直接调用 `atob` / `new Uint8Array`，规则环境没有这些全局对象，必须同名提供：

```js
var atob = function(s){                       // ★ 名字必须叫 atob，不能叫 _atob
  var ba = java.base64DecodeToByteArray(String(s)), o='';
  for (var i=0;i<ba.length;i++) o += String.fromCharCode(ba[i] & 255);
  return o;
};
var Uint8Array = function(n){ return []; };    // 普通数组即可，函数内按下标赋值
var fn = null;
eval(fm[0] + ';fn=' + fm[1] + ';');            // 顶层 return 非法，用变量接
var out = fn(b64p + segs.join(''));
```

> **K1 血坑**：站点脚本调用的是 `atob(...)`。若规则里定义 `_atob`，
> eval 出来的函数会抛 `ReferenceError: atob 未定义`，而外层 `catch(e){return []}`
> 会把它吞成「列表为空 / 无正文」，极难定位。诊断时务必在 catch 里打印 err。

## 4 目录：配置明文与章节索引映射

解密返回字符串按 `\n` 切成 7 段：
```
[0] mode '1'/'0'
[1] 章节 URL 前缀  '/read/5516/'
[2] 章节 URL 后缀  '.html'
[3] 章节 ID 列表（mode=1：逗号分隔36进制，首个直接 parseInt(36)，后续累加；
                 mode=0：tab 分隔直接 ID）
[4] 当前页 URL
[5] 翻页 URL 前缀  '/index/5/5516/'
[6] 翻页 URL 后缀  '.html/'
```
章节顺序映射：`<span data-随机="37828">第1章...</span>` 的值 `^ XOR = 配置索引`。
XOR 常量从脚本里取**最后一个** `\^\s*\d+`（如 `^22999`）。
> 曾观察到 key 表达式里也有 `^数字`（如 `(33^145)`），取最后一个才命中索引 XOR。

```js
var xc = sc.match(/\^\s*\d+/g)||[];
var xor = parseInt(String(xc[xc.length-1]).replace(/[^\d]/g,''),10);
var idx = parseInt(dataVal,10) ^ xor;
out.push({name: chapName, url: L[1] + ids[idx] + L[2]});
```

翻页终止不写死页码：从页面 `共(\d+)章` 与 `章節目錄 \((\d+)-(\d+)\)` 算总页数，
当前页 p*per >= total 才返回 null。

## 5 正文：c/o 乱序重组

解密返回字节数组（Uint8Array stub 的普通数组）：
```js
var pct='';
for (i=0;i<bytes.length;i++) pct += '%' + ('0'+(bytes[i]&255).toString(16)).slice(-2);
var obj = JSON.parse(decodeURIComponent(pct));   // UTF-8 还原
var body='';
if (obj && obj.c && obj.o) for (i=0;i<obj.o.length;i++) body += (obj.c[obj.o[i]] || '');
return body;                                      // 已是 <p>...</p> HTML
```
部分变体在 atob 前会 `split('').reverse().join('')`，这段逻辑在站点函数内部，
所以「执行站点函数」方案自动兼容，无需规则关心。

## 6 坑位清单

| # | 坑 | 对策 |
|---|---|---|
| K1 | 定义 `_atob` 而站点调用 `atob` → ReferenceError 被 catch 吞掉 | 必须同名 `atob`；catch 里输出 err 诊断 |
| K2 | 站点算法在 XOR链 / RC4 / rotate+XOR 间随机切换 | 不硬编码算法，提取函数执行 |
| K3 | base64 段数 2/3/4/5 随机 | 用 `[...].join('')` 数组通用提取，不写段数 |
| K4 | 顶层 `return` 在 @js 非法 | eval 追加 `;fn=FUNCNAME;` 用变量接 |
| K5 | ESA WAF 首次 POST 403 + Set-Cookie + JS 跳 `/search` | searchUrl 先 `java.ajax(首页)` 预热；loginCheckJs 检测极短盾页并 `java.post` 重发 |
| K6 | MCP `save_source` 与 `debug_source` 同批发起时，debug 用旧规则 | **必须串行**：先保存，单独再 debug |
| K7 | 诊断规则里正则漏写起始 `/` → ScriptException「字符串文字没有限制」 | 诊断版也跑静态门禁/先在 eval_js 验证 |
| K8 | 目录空但 nextTocUrl 正常 → Legado 并发抓十几页后报 TocEmptyException | 先查 chapterList 的 @js catch 是否被吞 |

## 7 双端验证

LT(MCP) 与 E(LAN WS 1126 `/bookSourceDebug`) 均需验证：
- 搜索 → 详情 → 目录 → 正文 → 发现 全链路
- E 版 WS 握手：`Sec-WebSocket-Protocol: legado, legado.token.<base64url(token)>`
  + `x-legado-token`，首帧 `{"tag":"<bookSourceUrl>","key":"<关键词或::URL>"}`
- 经验：E 版临时换成诊断书源后正文可能显示占位文本；恢复完整书源后复测即正常，
  不要据此判定 E 版不兼容。

## 8 交付形态

- 成品：`/workspace/69shu/69shu.json`（含 build_source.py / ws_debug_e.py）
- 书源 URL 正则：`https?://www\.69shu\.xyz/(book|read|index)/`
- UA：桌面 Chrome 120；`concurrentRate: 2/1000`（保守限速，不探测搜索频率）
- 公开站，无需登录/登录 UI；无发布页

## 9 繁体站显示字段 T2s 包装（用户要求简体显示时）

> 站点返回繁体、用户希望 App 显示简体：只转**显示字段**，绝不转 URL / ID / 封面地址 / 整份 HTML。

- 字段规则用 Legado **规则链**：`"name": "h4.name a@text\n@js:String(java.t2s(String(result)))"`
  （前一段 `@text` 的结果作为 result 传给后一段 `@js:`，见 `方法-403双击验证与搜索action轮换站.md`）。
- 适用于 ruleSearch / ruleExplore / ruleBookInfo 的 name/author/intro/kind/wordCount/lastChapter，
  以及 ruleContent.title（`h1...@text||...@text\n@js:...` 可带 `||`）。
- 由 @js 自造的列表（如目录 `chapterList` 的 `out.push({name,...})`）在 push 处转：
  `String(java.t2s(String(m[3]).trim()))`。
- 正文 @js 解密 return 前转：`if(body) return String(java.t2s(body));`；
  明文兜底 `return mm ? String(java.t2s(mm[1])) : '';`。
- 注意：`java.t2s` 是平台词库，不保证歧义字（如「著/着」）人工校订级正确；原站错字会保留。
  实测 LT MCP 与 E LAN WS 双端均生效。

## 10 发现页全量子入口 + 分组标题定案（69shu.xyz 终版）

> 用户要求：发现列表要按网页「分类 / 排行 / 完本」及各自子分类全量展开，
> 三个频道名做成独占整行的标题，子标签去掉「分类·/排行·/完本·」前缀，清爽一点。

- **静态 exploreUrl JSON 数组里放 `url:null`/`""` 的分组标题项会被
  `ExploreShowViewModel.loadCategories()` 过滤**，发现页根本不显示。
  ★必须把 `exploreUrl` 改成 `@js:` 动态返回 `JSON.stringify(rows)`。
- 分组标题行：`{title:'分类', url:null, style:{layout_flexBasisPercent:1,
  layout_wrapBefore:true, layout_justifySelf:'flex_start'}}` —— 独占整行、宽度铺满、不可点。
- 子标签：`{title:'玄幻', url:'真实URL', style:{layout_flexGrow:1}}` —— 均匀铺满、不带频道前缀。
- 69shu 终版 31 项 = 3 标题 + 28 入口（分类 10 + 排行 8 + 完本 10）。
  子路由实测：`/sort/{all|xuanhuan|xianxia|dushi|lishi|youxi|kehuan|kongbu|nvsheng|qita}/{{page}}.html`、
  `/rank/{allvisit|monthvisit|weekvisit|dayvisit|allvote|goodnum|lastupdate}/{{page}}.html` + `/top`、
  `/full/{同 9 子分类}/{{page}}.html`，均为 99 张 `.book-coverlist` + `li.next` 分页信号。
- 翻页仍用站点原生 `{{page}}`，不写死页码上限；ruleExplore 各频道共用同一套 CSS 规则。
- LT MCP 与 E LAN WS 1126 双端回读 exploreUrl 以 `@js:` 开头且含 `url:null`，
  实测 rank/allvisit 与 full/xuanhuan 入口 99 本 → 详情 → 目录 → 正文全绿。
  详见技能库《方法-登录UI-V2动态渲染与useweb新特性总览.md》§3.7、
  《方法-APP接口聚合书源拆解.md》§6.2、《方法-前端PoW读门SHA256挑战书源破解.md》§五。
