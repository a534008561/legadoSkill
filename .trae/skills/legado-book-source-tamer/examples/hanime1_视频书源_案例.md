# 案例 10：🌸 hanime1（视频书源 · bookSourceType=4）

- 站点：`https://hanime1.me`（镜像 `hanime1.com` / `hanimeone.me`，Laravel SSR + Cloudflare + CDN77 媒体域）
- 成品：[`hanime1_视频书源_v39.json`](hanime1_视频书源_v39.json)（89739B，md5 `62eef4b30c39905afcd53058920494de`，App 内一致，`check_source` 通过 1/1）
- 方法文档：[`references/方法-视频书源完全指南.md`](../references/方法-视频书源完全指南.md)（本案例的完整拆解，17 章 / 50 条避坑 / 22 项验收）

## 一句话形态

> 一集一行、正文输出**带时效签名的 mp4 直链**（`video#player > source[size][src?secure=]`，约 10 分钟过期），
> 详情页是 `<useweb>` **活视图面板**（靠 `ruleContent.callBackJs` + `source` 变量实现"播放切集实时跟随"），
> 控制台（登录 UI V2，38 行）负责域名 / hosts 多 IP failover / 代理 / CDN 主机替换 / 清晰度 / 封面内置 / 登录与跨域登录态同步。

## 本案例贡献的、可跨站复用的八条

| # | 知识 | 通用性 |
|---|---|---|
| 1 | **正文会被再解析一次 `AnalyzeUrl`** ⇒ 视频正文可以携带 URL 选项，`headers` 直达播放器（`player.mapHeadData = analyzeUrl.headerMap`） | ★★ 任何防盗链视频站 |
| 2 | **`dnsIp` 救不了播放器**：播放器用全局 `okHttpClient`（只认 App 设置→「自定义 Hosts」的 `addressCache`）⇒ 媒体域名必须"换主机名"或用户自己配 | ★★ 被墙视频站 |
| 3 | **CDN SNI 封锁 → 换 CDN 原生主机名**（`vdownload.hembed.com` → `1497203185.rsc.cdn77.org`，签名只绑路径） | ★★ CDN77 / Edgecast 系 |
| 4 | **播放页简介是静态快照**（`VideoPlayerActivity` 不监听 `REFRESH_BOOK_INFO`）⇒ `<useweb>` + `callBackJs(eventListener=true)` 自造跟随通道 | ★★ 多集视频站 |
| 5 | **同步桥会冻结 WebView JS 线程** ⇒ 面板首屏零网络（目录侧栏内嵌每集封面标题 + 正文侧写 `h1info`），按钮 `setTimeout(60ms)` 包装 | ★★ 一切 useweb 面板 |
| 6 | **`ruleContent.subContent` 在视频源 = 弹幕通道**（`putDanmaku`，B 站 XML，`http` 开头会被先请求） | ★ 冷门但白送的功能 |
| 7 | **站点 playlist 新→旧排序 → 入口集必须排目录第 1 行**（否则"点这集播那集"）；`durChapterIndex` 新书默认 0 陷阱 | ★★ 多集站 |
| 8 | **`_token` 匿名也下发** ⇒ 登录判据要用 `like-user-id` / 仅登录渲染元素；多镜像域 Cookie 隔离需"同步登录态" | ★★ Laravel 站 |

## 关键成品片段（节选，便于直接抄）

```js
// ① 带清晰度与线路的章节 URL（自定义键 "q" 会被 UrlOption 忽略但保留在字符串里，正文再读回来）
function H1BUE(v,f){var C=String.fromCharCode,LB=C(123),RB=C(125,125),Q=C(34);
  var q=String(f==null?'':f).replace(/[^0-9]/g,'');
  return 'https://'+LB+'H1DOM(source)'+RB+'/watch?v='+v+','+C(123)+Q+'dnsIp'+Q+':'+Q+LB+'H1IPX(source)'+RB+Q
       +','+Q+'timeout'+Q+':25000'+(q?(','+Q+'q'+Q+':'+Q+q+Q):'')+C(125)}

// ② CDN 换主机（split/join 全替换，零正则零反斜杠）
function H1FIX(src,u){u=String(u); if(u.indexOf('vdownload.hembed.com')<0)return u;
  return u.split('vdownload.hembed.com').join(H1CDN(src))}

// ③ 切集信号（正文事件 → source 变量 h1now = 入口vid|播放vid|ts）
(function(){try{ if(event!='saveRead'&&event!='startRead'&&event!='endRead')return;
  function g2(o,k){var f=o[k]; return typeof f=='function'?String(f.call(o)||''):String(f==null?'':f)}
  var m=String(g2(chapter,'url')).match(/[?&]v=([0-9]+)/), e=String(g2(book,'bookUrl')).match(/[?&]v=([0-9]+)/);
  if(!m||!e)return; var pv=String(source.get('h1now')||'').split('|');
  if(pv.length>1&&pv[0]==e[1]&&pv[1]==m[1])return;
  source.put('h1now', e[1]+'|'+m[1]+'|'+String(Date.now())); }catch(err){}})();
```

## 版本演进（v2.0 → v3.9，需求清单化）

```
v2.0 骨架 + 登录UI V2 → v2.2 hosts实测池 → v2.3 ★CDN SNI→原生主机 → v2.4 多域回退
→ v2.5 逻辑下沉 jsLib → v2.6 每 P 一行 → v2.7 收藏/关注按钮 → v2.8 详情跟随当前 P
→ v2.9 ★发现播放页是快照 → v3.0 ★新书索引陷阱 + 7 字段统一 → v3.1 ★入口 P 排首位
→ v3.2 ★useweb + callBackJs 实时跟随 → v3.3 ★零网络快绘 + 非阻塞按钮 + 三诊断键
→ v3.4 hosts 下拉分组 → v3.5 ★登录判据 + 跨域 Cookie 同步 → v3.6 延迟后缀 + 密码回填
→ v3.7 robots.txt 全量测速 → v3.8 endRead + 缺数据不空等 → v3.9 ★标签行 + 封面 data 内置
```

## 已知限制（写在 `bookSourceComment` 里）

- 视频域名依赖 `dnsIp` 选线与 CDN 主机替换，**播放本身不走 dnsIp**（用户网络差时需 App 设置→自定义 Hosts 或系统代理）。
- 播放页简介跟随依赖 App 支持 `<useweb>` + `callBackJs`（跨版本行为见 `方法-legado各版本行为差异对照.md`）。
- 内置封面使 `book.intro` 从 ~21KB 增至 ~121KB/本（可在控制台关掉）。
- 站点无弹幕接口 ⇒ `subContent` 未启用（功能留白，方法见指南 1.4.1）。
