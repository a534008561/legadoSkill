# 案例：2048ai2（Sigma 视频）· data URI 内联 HLS 让内置播放器直接播

> 日期：2026-11-28 ｜ 站点：`https://2048ai2.com/` ｜ 类型：`bookSourceType=4` 视频源
> 结论：Legado-team / Legado-E 双端正常，内置 ExoPlayer 直接播放，不依赖 WebView / hls.js / 本地解密。

## 一、问题

站点取流接口是：

```text
https://mdaiapi.2346dv1m.work/api/v1/m3u8/proxy?path=jpd/.../xxx.m3u8
```

`.m3u8` 只在 query 里，`Uri.path` 是 `/api/v1/m3u8/proxy`。  
Legado 的 `ExoPlayerHelper.createMediaItem()` 只 `setUri()`、不 `setMimeType()`，Media3 只看 URI path 后缀：

- path 以 `.m3u8` 结尾 → `HlsMediaSource`；
- 否则 → `ProgressiveMediaSource`。

所以直接把 proxy URL 交给内置播放器，必然不播。

## 二、Sigma 的解法

`ruleContent` 不返回 URL，而是把已经取到的 m3u8 文本 base64 成：

```text
data:/stream.m3u8?;base64,I0VYVE0zVQo...
```

URI 解剖：

```text
data:/stream.m3u8?;base64,...
└scheme┘ └──path──┘ └query┘
```

- path = `/stream.m3u8` → `getLastPathSegment() = stream.m3u8`；
- Media3 走 `HlsMediaSource`；
- `DataSchemeDataSource` 解码 base64；
- m3u8 里的 KEY/TS 都是绝对 `https://`，直接由原生网络栈加载。

## 三、核心规则

### ruleContent

```js
@js:(function(){
  var u=String(baseUrl||'').trim();
  if(!/^https?:\/\//i.test(u) || /\.(m3u8|mp4)$/i.test(u.split(/[?#]/)[0])) return u;
  var body=String(result||'').replace(/^\uFEFF/,'');
  if(!/^#EXTM3U(?:[\r\n]|$)/.test(body) || body.length>262144) return u;
  var lines=body.split(/\r?\n/), media=false;
  for(var i=0;i<lines.length;i++){
    var line=lines[i].trim(); if(!line) continue;
    if(line.charAt(0)!=='#'){
      if(!/^https:\/\//i.test(line)) return u;
      media=true;
    }else{
      var m=line.match(/(?:^|[:,])\s*(?:URI|SERVER-URI)\s*=\s*"?([^",]+)"?/i);
      if(m && !/^https:\/\//i.test(m[1])) return u;
    }
  }
  if(!media) return u;
  var b64=String(java.base64Encode(body)||'').replace(/\s+/g,'');
  if(!/^[A-Za-z0-9+/]+={0,2}$/.test(b64)) return u;
  return 'data:/stream.m3u8?;base64,'+b64;
})()
```

### ruleToc 归一化

目的：让 Legado 取正文时拿到纯 m3u8 文本，而不是 JSON/HTML。

```js
function toM3u8TextUrl(v){
  var u=String(v||'').trim(); if(!u) return '';
  if(/^\/\//.test(u)) u='https:'+u;
  var raw=u.replace(/^https?:\/\/[^/?#]+/i,'');
  var m=raw.match(/[?&]path=([^&#]+)/);
  var path=m?decodeURIComponent(m[1]):raw.split(/[?#]/)[0];
  path=path.replace(/^\/+/,'');
  if(/\.mp4$/i.test(path)) return u;
  if(!/\.m3u8$/i.test(path)) return '';
  if(/^https?:\/\//i.test(u) && !m) return u;
  return 'https://gwbe.jw5cqzrc.work/api/resource-pool/m3u8/decode/by/path?path='+encodeURIComponent(path);
}
```

## 四、关键约束

1. `data:/stream.m3u8?;base64,...` 的 `.m3u8` 必须在 **path**；写成 `data:application/vnd.apple.mpegurl;base64,...` 仍会被当 Progressive。
2. KEY / TS 必须是绝对 `https://`；data URI 没有 base URI，相对地址解析不了。
3. m3u8 体积控制在 256KB 内；过大回退原 URL。
4. 只包 m3u8 文本；`.mp4` 直链直接 return。

## 五、对照结果

| 方案 | 结果 |
|---|---|
| type=4，ruleContent 直接 return `/m3u8/proxy?path=...` | 不播（path=/proxy → Progressive） |
| type=0 + WebView hls.js + `startBrowser(url,title,html)` | 能播，但走 WebView，依赖 CORS/Origin |
| type=4，ruleContent 返回 `data:/stream.m3u8?;base64,...` | **内置播放器正常，LT/E 双端实测通过** |

## 六、适用边界

- 适用：标准 HLS（TS + AES-128），KEY/TS 绝对可达。
- 不适用：H265 / bytevc2 / DRM-CENC / 需要前端解密的流 / master playlist 相对变体未改写。
- 若 `auth_key` 极短效，注意正文缓存会让 data URI 里的旧签名失效，需要刷新正文。

## 七、关联文档

- [方法-视频源内置播放器HLS判定与dataURI内联绕过.md](../references/方法-视频源内置播放器HLS判定与dataURI内联绕过.md)
- [方法-proxy类接口path必须相对路径与SPA逆向API域.md](../references/方法-proxy类接口path必须相对路径与SPA逆向API域.md)
