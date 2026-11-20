# 方法：init 模式 IIFE 必须 return、fetchm3u8 签名头条件注入、跨区站名前缀正则（LissAV v1.0·261120）

> 案例来源：LissAV 视频书源（x99dh 发布页线路池，asian 日本区 + domestic 国产区共 23 条同构线路，streamit 主题，bookSourceType=0）。
> 适用范围：一切用 `ruleBookInfo.init` 模式的视频源 / 站点 API 返回带可选签名头的 HLS 源 / 同一线路池下不同区站名前缀会变的站。

## 1. ★★★ init 模式两个致命写法（本次最大坑，debug 报「内容不可空」）

### 1.1 症状

`debug_source` 搜索全绿（12 条），但详情页一执行 init 就炸：

```
≡执行详情页初始化规则
java.lang.AssertionError: 内容不可空（Content cannot be null）
  at io.legado.app.model.analyzeRule.AnalyzeRule.setContent(...)
```

HTTP 日志显示详情页 200 且 145KB HTML 正常返回 —— **不是网络问题，是 init 规则返回了 null/undefined**。

### 1.2 根因一：IIFE 体内漏 `return`（真正病根）

错误写法：

```javascript
// ruleBookInfo.init
"@js:(function(){var h=String(result);var o={};
   o.title=...;
   JSON.stringify(o)      // ← 只求值不 return！
 })()"
```

`@js:` 的求值语义是 `eval(表达式)`，IIFE 的结果**只能是函数 `return` 出来的值**。
`JSON.stringify(o)` 单独一行只是表达式语句，函数仍返回 `undefined` → `AnalyzeRule.setContent(null)` → AssertionError。

**正解**：`return JSON.stringify(o)`（IIFE 内必须显式 return）。

### 1.3 根因二：init 结果的字段引用是 `$.field`，不是 `{{$.field}}`

错误写法：

```json
"ruleBookInfo": {
  "init": "@js:...(return JSON.stringify({title:...,cover:...}))()",
  "name": "{{$.title}}",
  "coverUrl": "{{$.cover}}"
}
```

`{{}}` 是 **URL 模板**语法（AnalyzeUrl.initUrl 里 replaceKeyPageJs 阶段求值），在**详情页字段规则**（AnalyzeRule.getString）里不会被展开 → 字段拿到空串。

**正解**：字段直接写 JSONPath：`"name": "$.title"`、`"coverUrl": "$.cover"`、`"kind": "$.kind"`、`"intro": "$.desc"`。
（本地对照：所有成功成品 qingcheng/猫眼/STV/追书神器/番茄的 init 字段全是 `$.xxx`，无一例外。）

### 1.4 离线验证配方（不用 App 也能先排掉脚本 bug）

用 qjs 的 `eval` 直接求值 `@js:` 表达式（不是 `new Function`，后者包一层后 IIFE 恒 undefined）：

```javascript
// test_init.js
var j = JSON.parse(std.loadFile('book.json'));
var result = std.loadFile('detail.html');      // 绑定 Legado 的 result 变量
var r = eval(j.ruleBookInfo.init.substring(4)); // 去 @js: 后 eval
var o = JSON.parse(r);                          // 必须能 parse 出对象
console.log(o.title, o.uid, o.cover);
```

同时把每条 `@js:` 规则剥 `@js:` 前缀后过一遍 `new Function` 编译（语法门禁），两层结合可拦住绝大多数脚本级错误。
**注意**：`new Function(initSrc)` 因外层没 return 会恒返回 undefined，只能用来查语法，不能用来查 init 返回值。

## 2. ★★ 同一线路池跨区：站名前缀会变，init 正则不能用写死的站名

本站发布页 x99dh 给 LissAV 与 LissAV国产区分配**同一批 23 个域名**，只靠路径区分区：

- `LissAV(日本区)` → `/asian/zh-CN/...`
- `LissAV国产区` → `/domestic/zh-CN/...`

但不同域名的页面 `<title>` 前缀不同：

- `lissav.sbs/asian/...` → `<title>LissAV | FC2-PPV-xxxx ...</title>`
- `huangguo02.net/domestic/...` → `<title>黄果短剧 | 网路聊21岁...</title>`

错误写法（写死站名前缀，国产区书名全空）：

```javascript
o.title=(h.match(/<title>LissAV \| ([^<]*)<\/title>/)||['',''])[1];
```

**正解**：用通用 `|` 分隔符正则，不依赖站名：

```javascript
o.title=(h.match(/<title>[^|]*\| ([^<]*)<\/title>/)||['',''])[1];
```

经验：**同源不同线路/不同区可能挂不同品牌名**（镜像站、白牌站常见），任何从 `<title>` 抠字段的规则都应剥离开头品牌，按分隔符/结构取值。

## 3. ★★ fetchm3u8 站点：urlSign 有时有时无，Accept 头必须条件注入

本站 streamit 播放器的 `fetchm3u8` 模式：API `/{zone}/zh-CN/api/video/stream?video_uid=` 返回 `playlist[0]`。

- 日本区线路：`{"url":".../720p/video.m3u8","urlType":"m3u8","playMode":"fetchm3u8","urlSign":"32位hex"}` → 播放器每个请求带 `Accept: */*;sign={urlSign}`
- 国产区线路：`{"url":"https://rou07.net/api/hls/xxx","urlType":"m3u8","native":true}` → **没有 urlSign 字段**，根本不需要签名头

错误写法（无 sign 时输出空 sign，可能反被 CDN 拒）：

```javascript
return u+',{"headers":{"User-Agent":"'+UA+'","Accept":"*/*;sign='+sg+'"}}';  // sg 为空 → sign=
```

**正解**：有 sign 才注入 Accept，没有就只带 UA：

```javascript
var sg=(s.match(/"urlSign":"([^"]+)"/)||['',''])[1];
if(sg) return u+',{"headers":{"User-Agent":"'+UA+'","Accept":"*/*;sign='+sg+'"}}';
return u+',{"headers":{"User-Agent":"'+UA+'"}}';
```

另注意：ruleContent 是 `@js:` 返回值，`{{}}` 在此会被当模板再 eval，URL 选项必须用**单花括号** `,{"headers":...}`，写 `,{{"headers":...}}` 会破坏解析。

## 4. ★ 相关套路：发布页线路池测速改写当前变量，调试时注意状态污染

本站面板 `LS_fetchPub()` 从 x99dh.github.io 的 `encodedData`（base64→decodeURIComponent→JSON）解析 LissAV 23 条线路，剥 `/asian|domestic/zh-CN` 路径只留线路根。
`LS_pickFastest()` 用 `java.ajaxAll(urls,true)` 并发打 `/status.html`（2 字节 `ok`），callTime 严格预检（防异常堆栈串冒充成功），最快线路写 `sourceVariable`。

调试时我用 `eval_js` 临时把区切到 domestic、线路切到 `huangguo02.net` 验证国产区，**测完必须显式还原**（`LS_writeZone('asian')` / `LS_writeLine('https://lissav.sbs')`），否则后续 debug 会跟着变量走不同的线路，结论混乱。
`lissav.sbs` 对国产区搜索曾 60s 超时，`huangguo02.net` 189ms 正常 —— 同一线路池不同域名的**分区可达性不同**，遇到分区超时先测速换线，不要急着改规则。

## 5. 交付实测结论（LT + E 双端）

- `check_source` 1/1 通过；`debug_source` 搜索/发现/详情/目录/正文五链路全绿，正文输出 m3u8 直链 + sign 头
- 双端 LAN 保存（LT 1122 带 token / E 1125 免 token）回读各 27 字段一致，ruleContent/exploreUrl 关键规则完整
- 门禁：jsLib/loginUrl 过 qjs `new Function`；3 条 `@js:` 规则过 qjs 编译；jsLib 裸绑定/函数名冲突/必备函数检查全绿
- 站点游客可看无登录；搜索未主动探频

## 6. ★★★ 261120 追加：国产区无法播放 = CDN 强制 Referer（同站不同视频 CDN 策略不同）

用户反馈「书源类型换成视频、国产区视频无法播放」。排查链：

| 实验 | 结果 | 结论 |
|---|---|---|
| HTTP 日志看点播 | m3u8 清单 200，但**无分片请求** | 播放器拿到清单后没继续，怀疑分片问题 |
| 抓 API 返回 | 有的视频 `urlType:"m3u8"`→`rou07.net/api/hls/xxx`（直连 200）；有的 `urlType:"QualityUrls"`→`s550.vcjudch73.com/.../720p/video.m3u8` | 同站不同视频 CDN 域名不同 |
| s550 裸请求 | **403 len=0** | 病根 |
| s550 带 `Referer: https://{huangguo02.net}/` | **200 len=913 #EXTM3U** | 该 CDN 强制校验 Referer |

**根因**：`s550.vcjudch73.com` 系列 CDN 强制校验 Referer，ruleContent 原先只带 UA，导致清单请求 403→播放失败。而 `rou07.net` 系列不校验 Referer 但有间歇 502。

**正解（ruleContent 一行拼接 headers）**：

```javascript
var hdr=',{"headers":{"User-Agent":"'+UA+'","Referer":"'+root+'/"'
  +(sg?',"Accept":"*/*;sign='+sg+'"':'')   // 日本区有 urlSign 才加
  +',"retry":2}}';                          // 应对 CDN 间歇 502
return u+hdr;
```

- `root` = `baseUrl.match(/^https?:\/\/[^/]+/)[0]`（当前线路根）
- Referer 始终带（对不校验的 CDN 无害）
- `retry:2` 应对 rou07/rou168 的间歇 502（实测同一 URL 连续请求 502/200 交替）
- ★该 m3u8 分片是 `.png` 后缀 + `Content-Type: image/png`，但实测内容是 MPEG-TS（`G@ FFmpeg` 魔数），ExoPlayer HLS 按 byte 解析能正常播，Content-Type 不是根因（曾误判）

**书源类型**：视频源必须 `bookSourceType=4`（用户明确要求）。type=0 文本源点正文不进视频播放器。type=4 的 ruleContent 返回值就是播放地址（`纯URL` 或 `纯URL+合法URL选项JSON`），不能有多余文字/换行。

**验证**：带完整选项的 URL 用 `java.ajax` 复现拿到 913B `#EXTM3U`（决定性证据）；debug 五链路全绿；check_source 1/1；双端 LAN 落库回读一致。

## 7. ★★★ 261120 再追加：同一站点不同视频 CDN 对 Referer 要求**相反** → 必须运行时探测，不能一刀切

用户追加反馈「国产区还是无法播放，加载一下就停」。HTTP 日志决定性证据：

- `#501 GET .../api/video/stream?video_uid=46036cd49ee2dd26 -> 200`（ruleContent 执行了 API）
- **之后完全没有 m3u8 / 分片请求** ⇒ 播放器没消费返回值，不是 CDN 403 那么简单

### 对照实验（本次方法论：每步都做正反两组）

| m3u8 域名 | 裸 UA | 带 `Referer: 站点根/` | 结论 |
|---|---|---|---|
| `s550.vcjudch73.com/.../720p/video.m3u8` | **403 len=0** | **200 #EXTM3U 913B** | 强制要求 Referer |
| `rou666.net/api/hls/xxx` | **200 #EXTM3U 35918B** | **502 len=0** | 带 Referer 反而挂 |

**同一个站点（huangguo02.net/domestic）、同一个 API、不同 video_uid 的 playlist 域名不同， CDN 策略完全相反。** 之前一刀切加 Referer 的"修复"修好了 s550 视频，却弄坏了 rou666/rou07 系列 —— 用户仍播不了。

### 正解：ruleContent 运行时探测两个方案，谁返回 `#EXTM3U` 用谁

```javascript
var hA=',{"headers":{"User-Agent":"'+UA+'"'+(sg?',"Accept":"*/*;sign='+sg+'"':'')+',"retry":2}}';           // 无 Referer
var hB=',{"headers":{"User-Agent":"'+UA+'","Referer":"'+root+'/"'+(sg?',"Accept":"*/*;sign='+sg+'"':'')+',"retry":2}}'; // 带 Referer
var pick=hB;
try{var r=String(java.ajax(u+hA)||'');if(r.indexOf('#EXTM3U')>=0)pick=hA;}catch(e){}
if(pick===hB){try{var r2=String(java.ajax(u+hB)||'');if(r2.indexOf('#EXTM3U')<0)pick=hA;}catch(e2){}}
return u+pick;
```

要点：
1. **用 `java.ajax(带URL选项的完整串)` 探测**（`java.connect` 不认 `,{"headers":...}` 选项，会拿整串当 URL）；`java.ajax` 在此环境返回 String，直接 `String(r||'')` 判 `#EXTM3U`，不要 `.body()`
2. 每次正文加载多 1~2 次 ~2s 探测请求，换来两类 CDN 都能播，值得
3. 探测放 ruleContent（每次播放实时执行），不要缓存进变量——CDN 域名和策略会轮换

### 验证（App 内 eval_js 实跑落库规则逻辑）

- rou666 视频：`A探测=true(len35918) → 选中 A 无Referer` ✓
- s550 视频：`A探测=false(len0) → 选中 B 带Referer` ✓
- check_source 1/1；双端 LAN 保存成功

### 通用教训

**"某个 CDN 需要 X 头"不能推广到同站所有视频**。视频聚合站常把不同视频的流挂到不同 CDN 集群，各集群防盗链策略可能相反。遇到"修好 A 视频弄坏 B 视频"，立刻做 A/B 两组对照实验，改成运行时探测，别在两种策略间反复横跳。
