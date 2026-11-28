---
title: 方法-视频站m3u8迁入播放API的识别与改造
date: 2026-11-28
source: 黄果短剧🔞 v12（2026-11-27 站点改版）
tags: [视频书源, m3u8, 播放接口, playback, crypto-image, 410, java.post, HashMap, E版缩进]
---

# 视频站改版：m3u8 从页面搬进播放接口

## 1. 改版识别（四个探针，10 秒定性）

对任意视频站详情页跑一遍：

```js
var h=String(java.ajax(url+',{"timeout":9000,"retry":0}'));
out.push('[.m3u8] '+(h.split('.m3u8').length-1));        // 0 ⇒ 页面已无直链
out.push('[<source] '+(h.split('<source').length-1));    // 有标签但 src 可能为空
out.push(h.match(/<source[^>]*>/g).join(' | '));
out.push(h.indexOf('videoInitialData'));                 // SSR payload
```

黄果短剧 2026-11-27 改版后的指纹：

- `<source type="application/vnd.apple.mpegurl"/>` —— **标签还在，`src` 没了**（旧规则 `<source src="([^"]+)"` 会静默拿到空串，正文变 ContentEmptyException，而不是报选择器错）
- 页面里 `.m3u8` 出现次数 **0**
- `<script id="videoInitialData" type="application/json">` 里 `"videoSrc":""`、`"epPlaySrcs":{}`、`"cdnM3u8Enabled":true`、`"cdnAuthKey":"x-cdn-auth"`
- 脚本清单出现 `static/web/js/pages/cyber-video.js`、`services/playback.js`、`modules/play-sig-guard.js`、`ssp-mount.js`

> 判据总结：**页面无 m3u8 + SSR payload 里 src 为空 + 有 playback/sig-guard 脚本 = 取址已迁到 API**。
> 此时翻 `services/playback.js` 就能拿到完整取址协议。

## 2. 取址协议（playback.js 逆向结果）

```
试址顺序：先读方法开关 → GET 或 POST

A. 方法开关（5 分钟一个桶）
   GET  /m3m/off/{floor(now/300000)}.json
   → {"status":1,"data":{"bucket":…,"method":"POST"}}      // 当前为 POST

B. GET 通道（method=GET 时才可用）
   GET  /m3m/play/{videoId}/{floor(now/1800000)}.json?kind=video[&ep=N]
   → {"status":1,"data":{…}}；method=POST 时返回 {"status":0,"msg":"播放参数无效"}

C. POST 通道（当前生效）
   POST /api/videos/{id}/playback                    // 第 1 集
   POST /api/videos/{id}/episodes/{n}/playback       // 第 n 集
   Content-Type: application/json
   body: {}
   → {"data":{"manifest_method":"GET","cdn":{…},"streams":{"main":"https://…/xxx.m3u8?auth_key=…","preview":"…"},"ep":1}}
```

实测结论（黄果短剧）：

- **POST 不需要任何登录 token**（前端代码写 `useToken:true`，但游客态照样 200）
- **m3u8 不需要 `x-cdn-auth` 头**：`cdn.m3u8Enabled=true` 只表示浏览器侧 hls.js 会给 `.m3u8` 补头，服务端对 `auth_key` 签名已经放行（裸 `java.ajax` 拿到 3.6KB 标准 m3u8）
- `otherEnabled=false` ⇒ ts/key 不加头（m3u8 内部 `#EXT-X-KEY:AES-128` 播放器原生支持）
- `auth_key=<expire>-150.0.web.<uid>-0-<md5>` 有效期 **10800 秒（3 小时）**，客户端无法自造，每次取址重新拿

## 3. 正文规则改造（双端可用的写法）

```js
@js:
(function(){
var u=String(baseUrl||'');
var hm=u.match(/^(https?:\/\/[^\/]+)/); var host=hm?hm[1]:'';
var im=u.match(/\/video\/(\d+)/);      var id=im?im[1]:'';
if(!host||!id)return '';
var em=u.match(/\/ep-(\d+)/);          var ep=em?em[1]:'1';
var ck='hgc_'+id+'_'+ep;               // 25 分钟缓存（< auth_key 3h）
var now=Date.now();
try{var cv=String(source.get(ck)||'');var ct=parseInt(String(source.get(ck+'_t')||'0'));
    if(cv&&cv.indexOf('http')===0&&ct>0&&now-ct<1500000)return cv;}catch(e){}
function getPlay(h2){
  var api=h2+'/api/videos/'+id+(ep!=='1'?'/episodes/'+ep:'')+'/playback';
  var hd=new Packages.java.util.HashMap();     // ★ 见 §4
  hd.put('Content-Type','application/json'); hd.put('Accept','application/json');
  hd.put('Referer',u); hd.put('User-Agent','…');
  var r=null; try{r=java.post(api,'{}',hd)}catch(e){return ''}
  var bd=''; try{bd=String(r.body())}catch(e){return ''}
  var j=null; try{j=JSON.parse(bd)}catch(e){}
  if(j&&j.data&&j.data.streams){var s=String(j.data.streams.main||''); if(s.indexOf('http')===0)return s;}
  return '';
}
var src=getPlay(host);
if(!src){var alt=['https://thu.xxx.cc','https://pku.xxx.cc'];for(var i=0;i<alt.length&&!src;i++){if(alt[i]!==host)src=getPlay(alt[i]);}}
if(src){try{source.put(ck,src);source.put(ck+'_t',String(now))}catch(e){}return src;}
return '';
})()
```

目录侧不变（站点仍输出 `data-track-total-episode` 与 `/video/{id}/ep-{n}/` 选集链接），
章节 URL 里的 `ep-N` 就是 API 的 `{n}`；第 1 集页面 = 详情页本身，走 `/playback`（不带 episodes）。

## 4. 双端坑：java.post 的 headers 签名不同

| 版本 | 签名 | 传 JSON 字符串 | 传 HashMap |
|---|---|---|---|
| LT（gedoor/重构版） | `post(urlStr, body, headers: Any?)` | ✅ `parseJsRequestHeaders` 支持 String/Map | ✅ |
| E（Luoyacheng） | `post(urlStr, body, headers: Map<String,String>)` | ❌ 类型不匹配 | ✅ |

⇒ **规则里一律用 `new Packages.java.util.HashMap()` + `put()`**，LT/E 通吃。
同理 `java.get`。
另：`java.post(...)` 返回值是 jsoup `Connection.Response`，取 body 用 `.body()`；它没有 `code()`（那会报「找不到函数 code」，状态码是 `statusCode()`）。

## 5. 图床轮换 + 图片解密（crypto-image 插件）

改版同时换了图床：`pic.drleao.cn → pic.qnlycc.cn`，**但解密协议没变**：

- 指纹：`Content-Type: binary/octet-stream`、文件头是中文「黄果」（`4F E8 97 A4`）、长度是 16 的倍数、页面引 `plugins/crypto-image*.js`
- 密钥位置：`/static/web/js/plugins/crypto-image-protocol.js` → `window.CryptoImageProtocol = Object.freeze({"decryptEnabled":true,"decryptKey":"f5d965df75336270","decryptIV":"97b60394abc2fbe1"})`（硬编码，跨域轮换不变）
- 算法：`AES/CBC/NoPadding`，16 字节密钥 ⇒ AES-128

**新坑：解密后要按类型截尾**

```
密文 3088928B（16 倍数，服务端把原图填充到对齐）
解密后 magic=137,80,78,71 (PNG)，IEND 在 3074404，尾部 14530B 垃圾
```

v5~v11 只做了 JPEG `FF D9` 扫描，本次封面是 PNG ⇒ 必须补 IEND：

```js
var d0=(dec[0]+256)%256,d1=(dec[1]+256)%256;
if(d0===137&&d1===80){        // PNG：IEND 00 00 00 00 49 45 4E 44 AE 42 60 82
  for(var i=dec.length-8;i>Math.max(0,dec.length-131072);i--){
    if((dec[i]+256)%256===73&&(dec[i+1]+256)%256===69&&(dec[i+2]+256)%256===78&&(dec[i+3]+256)%256===68
      &&(dec[i+4]+256)%256===174&&(dec[i+5]+256)%256===66&&(dec[i+6]+256)%256===96&&(dec[i+7]+256)%256===130){end=i+8;break}
  }
}else if(d0===255&&d1===216){ // JPEG：FF D9
  for(var j=dec.length-2;j>Math.max(0,dec.length-131072);j--){ if((dec[j]+256)%256===255&&(dec[j+1]+256)%256===217){end=j+2;break;} }
}
```

- 只扫尾部 128KB，3MB 图也不会卡
- 读 InputStream 的 buffer 用 `new Packages.java.lang.String(8192个'0').getBytes()`（`Array.newInstance` 反射会报「不是函数，它是 object」）

## 6. 分类下线的判据：410 而不是 404

黄果短剧把 `AI换脸 /ai-huanlian/`、`AI魔改 /ai-mogai/` 下线，返回 **HTTP 410**，页面 75KB（不是 404 的 88KB 空壳）：

```
/ai-huanlian/ code=410 len=75548
/ai-mogai/    code=410 len=75548
```

⇒ 定期给发现页每个入口跑一次批量探活（`java.ajaxAll`），**把 410 的入口从 exploreUrl 里摘掉**，别等用户报「发现规则失败」。
新增入口同理：`/original/`（原创）、`/newest/`（最新，65 页）、`/recommend/`（推荐，3 页）是本次改版新增的频道页，卡片结构与老分类一致。

## 7. E 版正文会被加全角空格缩进

E 版 `help/book/ContentProcessor.kt`：

```kotlin
mContent.split("\n").forEach { str ->
    val paragraph = str.trim { it.code <= 0x20 || it == '　' }
    if (paragraph.isNotEmpty()) { … contents.add("${ReadBookConfig.paragraphIndent}$paragraph") }
}
```

⇒ 视频源正文（裸 m3u8 URL）经 `getBookContent` 返回时会变成 `　　https://…`（两个 U+3000）。
LT 同构。播放器侧一般会 trim，但**视频源正文必须保证只有 URL 本身、无前后缀**；若播放异常先看 content 首字符是不是 U+3000。

## 8. 验收顺序（本次实测路径）

1. 探针：`/m3m/off/` 拿 method、POST playback 拿 streams.main（先证明接口通）
2. LT `debug_source` 全链路（搜索→详情→目录→正文）
3. 单集视频（total=1）与多集视频都跑一遍
4. `ep-2/ep-3` 用 `eval(String(source.getRuleContent().getContent()))` 单独验（不同集必须是不同 m3u8 路径）
5. 缓存：同一章第二次正文应在 20ms 内返回同一 URL
6. E 版：LAN 1125 `/saveBook` 临时加书 → `/refreshToc` → `/getBookContent?index=N` → `/deleteBook` 清场（E 版无 MCP，这是唯一能验目录/正文的通道）
7. `check_source` 1/1
