# 网易云类 weapi 加密站的明文接口降级方案

> 2026-09-17 网易云音乐听书源实战提炼。核心结论：**weapi 加密链路已能被完美实现，但站点会在源站层 22ms 秒拒返回 200 空体**；正确对策不是继续调加密，而是**整体降级到 /api/ 明文 GET 接口**。同时记录本次挖出的 3 个 App 级硬知识（getElements 返回值协议 / Rhino java-String .length 坑 / createSymmetricCrypto 与 CryptoJS 的一致性）。

## 0. 一句话总结

站点把加密接口（weapi）的 POST 在源站层静默丢弃（200 + content-length:0），但同域的**明文 /api/ GET 接口全部可用**且数据更全；书源应放弃 weapi，全部走 /api/，登录改用 Cookie 粘贴（putLoginHeader 自动写 CookieStore）。

## 1. 适用场景识别

- 目标站有成熟的加密接口（网易云 weapi / 携程 / 12306 类），且加密算法已被公开逆向
- POST 加密接口返回 **200 但 body 为空**（不是 401/403/验证码）
- 同站存在 `/api/xxx` 明文 GET 镜像接口
- 站点核心内容（搜索/列表/详情/播放地址）匿名可访问

**不适用**：站点只有加密接口、或明文接口返回的是阉割数据（如只给标题不给播放地址）。

## 2. 网易云 2026 接口现状（实测）

### 2.1 weapi 的死法：200 空体

```
POST https://music.163.com/weapi/song/enhance/player/url/v1
→ 200, content-length: 0, server-timing: origin;dur=22, x-via: MusicServer
```

特征：
- **源站 22ms 就返回空**（`origin;dur=22`，不是 CDN 拦截，是源站策略）
- 沙盒（数据中心 IP）与**真机（家宽 IPv6）都返回空** → 不是 IP 信誉
- UA / Referer / Origin / csrf_token 全补齐仍空
- 加密链路经**双向验证 100% 正确**（见 §3）→ 不是实现 bug

结论：站点对非浏览器环境的 weapi POST 做了指纹级识别，无法在书源侧绕过。

### 2.2 /api/ 明文接口全清单（匿名可用，实测 2026-09）

| 用途 | 方法 URL | 备注 |
|---|---|---|
| 搜索单曲 | GET `/api/search/get?s=词&type=1&limit=30&offset=N` | type=1000 歌单/10 专辑 |
| 歌曲详情 | GET `/api/v3/song/detail?c=[{"id":N}]` | **c 参数必须 URL 编码**；ar[]有歌手名；al.picUrl 封面 |
| 歌单详情 | GET `/api/v6/playlist/detail?id=N&n=1000` | **tracks 只给 10 首，trackIds 给全量** |
| 批量歌曲信息 | GET `/api/v3/song/detail?c=[{"id":1},{"id":2}]` | 每批 ≤50，用于补全歌单曲目名 |
| 播放地址 | GET `/api/song/enhance/player/url?ids=[N]&br=320000` | **直链无 Referer 校验**，m4a/mp3 明文 |
| 歌词 | GET `/api/song/lyric?id=N&lv=1&kv=-1&tv=-1` | lrc.lyric 带时间戳 |
| 官方榜单 | GET `/api/toplist` | list[] |
| 歌单广场 | GET `/api/playlist/list?cat=华语&limit=30&offset=N` | cat 需 encodeURI；分页 |
| 推荐歌单 | GET `/api/personalized/playlist?limit=30` | 匿名也给 |
| 每日推荐 | GET `/api/v3/discovery/recommend/songs` | data.dailySongs[] |
| 新歌速递 | GET `/api/discovery/new/songs?areaId=0&limit=30` | limit 被忽略（返回 100） |
| 登录态检查 | GET `/api/nuser/account/get` | code 200 + profile 非空 = 已登录 |

关键坑：
- **搜索结果的 song 对象没有 album.picUrl**（为 null），封面只能用 `artists[0].img1v1Url`（歌手头像）
- 歌单 v6 的 `tracks` 只有前 10 首，**完整曲目要靠 trackIds 数组再批量取**
- 播放地址 br=320000 对 VIP 歌也返回标准音质文件（不会因 br 高而失败）；url 为空且 code=404 = 无版权
- 音频直链**不校验 Referer**，播放器裸拉即可

## 3. ★weapi 加密的正确实现（留着备用，万一站点恢复）

虽然当前被拒，但实现已验证 100% 正确（Python 与真机 JS 输出完全一致），站点策略松动时可直接用：

- AES：`java.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv).encryptBase64(明文)` — **与 CryptoJS AES-CBC-PKCS7 输出逐字节一致**（实测 `hello` → 两端同为 `+J9Q3vLzLGFuqlWFQh3T3A==`）
- 双层：`params = aes(aes(json, 固定ekey), 随机secKey)`
- RSA：`new Packages.java.math.BigInteger(hex,16).modPow(e,n).toString(16)`，结果**补前导零到 256 位**
- 常量：ekey=`0CoJUm6Qyw8W8jud` / iv=`0102030405060708` / e=`010001` / n=1024 位 modulus
- POST body：`params=<urlencoded>&encSecKey=<256hex>&csrf_token=`

## 4. ★★★App 级硬知识一：getElements 的返回值协议（LT 版）

**AnalyzeRule.kt:478-507 源码实锤**：`getElements()` 对 @js 规则的返回值只接受 `List<*>` / `Array<*>` / `NativeArray`，**String 返回值直接 `return ArrayList()`（空列表）**。

```kotlin
when (val value = result) {
    is List<*> -> ...
    is Array<*> -> ...
    is NativeArray -> ...
}
return ArrayList()   // ← String 落到这里，列表大小 0
```

### 后果

`ruleSearch.bookList` / `ruleToc.chapterList` / `ruleExplore.bookList` 的 @js 规则：
- ❌ `return JSON.stringify(out)` → **debug 日志"列表大小:0"，书籍总数 0**
- ✅ `return out`（JS 数组）→ 列表正常，item 是 NativeObject，字段规则 `$.name` / `$.author` 可取

### 与 E 版（legado-E/Lyc）的冲突

E 版 `getString` 对 NativeObject **没有 Mode.Js 分支**，需要列表返回 **JSON 字符串数组**。两者不可兼得：
- 只做 LT 版（官方 LegadoTeam）→ 返回 JS 数组 + 纯键名 JSONPath 字段
- 需双版本 → 字段规则用 `@js:` 分支按版本返回（成本高），或只做 E 版协议牺牲 LT

**验证方法**（eval_js，我的标准方法论）：
```js
var ar = new Packages.io.legado.app.model.analyzeRule.AnalyzeRule();
ar.setContent(真实响应); ar.setBaseUrl('...');
var r = ar.getElements('你的规则');
// typeof r === 'object' && r.length === 期望条数
```

## 5. ★★★App 级硬知识二：Rhino 的 java.lang.String 没有 .length 属性

`b.modPow(e,n).toString(16)` 返回 **java.lang.String**（不是 JS string）。在 Rhino 里：

```js
var enc = b.modPow(e, n).toString(16);   // java String
enc.length        // undefined（String 只有 length() 方法，无字段）
enc.length < 256  // NaN < 256 = false → while 补零循环一次都不执行！
```

**实测症状**：encSecKey 长度 188 而非 256，加密被服务端拒绝。

**正确写法**（所有 Java 方法返回的字符串都要先转）：
```js
var enc = String(b.modPow(e, n).toString(16));   // 或 '' + enc
while (enc.length < 256) enc = '0' + enc;
```

同一坑的其它形态：jsoup `.text()` / `.html()` / `.attr()` 返回的也是 java String，正则 `.replace(正则, 串)` 会报"选择不明确"。**统一用 String() 包裹**。

## 6. ★App 级硬知识三：init 规则统一多形态详情

`BookInfo.kt:75`：`infoRule.init` 的返回值会 `setContent(...)` **替换掉整个内容**，后续 name/author/intro 等字段从新内容解析。

用途：一个书源同时支持「单曲详情 JSON」和「歌单详情 JSON」两种结构，init 里判断结构并输出**统一的扁平 JSON**，字段规则全用 `$.xxx` 纯 JSONPath。

```js
// init @js
if (j.playlist) return JSON.stringify(plOut(j.playlist));   // 歌单
if (j.songs && j.songs.length) return JSON.stringify(songOut(j.songs[0]));  // 单曲
// 字段: name=$.name author=$.author intro=$.intro ...
```

注意：init 用的是 `getElement`（单数），返回 **String 是正确的**（与 bookList 的 getElements 协议相反，别搞混）。

## 7. 音频书源的四个官方机制（源码级）

1. `bookSourceType=1` → `BookSource.getBookType()` 返回 `BookType.audio(32)`，搜索/发现时**自动设 book.type**（BookList.kt:173/212）
2. `WebBook.kt:306` 刷目录时 `removeAllBookType() + addType(getBookType())` 会重设，无需在规则里 setType
3. `BookContent.kt:152`：`book.isAudio -> bookChapter.putLyric(subContent)` → **`ruleContent.subContent` = 歌词通道**，AudioPlay 播放时同步显示 LRC
4. 音频正文 `content` 就是播放 URL 纯文本；`BookContent.kt:243` 对 isAudio **跳过 HTML 净化**；`replaceRegex` 仍会执行且逐行 trim → **音频源不要写 replaceRegex**（会切断 URL）

### tocHtml 复用（省请求）
`BookInfo.kt:158-160`：tocUrl 为空时 `book.tocUrl = baseUrl`，且 `tocHtml = body`；
`WebBook.kt:312`：目录阶段若 `bookUrl == tocUrl && tocHtml 非空` → **直接复用，不再发请求**。
→ 详情和目录指向同一 API 时，设 `tocUrl` 为空，自动只请求一次。

## 8. 登录：Cookie 粘贴是唯一稳路

- `BaseSource.kt:235 putLoginHeader(json)` 内部自动 `CookieStore.replaceCookie(key, cookie)` → **写入后 enabledCookieJar=true 的所有请求自动携带**
- 登录 UI 提供：Cookie 粘贴框（推荐）/ 手机号+密码（weapi，当前会被站点拦截，空响应时 toast 明确引导改用 Cookie）/ 检查登录状态按钮（`/api/nuser/account/get` 的 profile 判定）
- `source.removeLoginHeader()` 退出

## 9. 开箱模板

### 9.1 列表规则（搜索/发现/目录通用）

```js
@js:(function(){
  var j = JSON.parse(String(result));
  var arr = j.result.songs || [];      // 按实际容器改
  var out = [];
  for (var i = 0; i < arr.length; i++) {
    var s = arr[i];
    out.push({
      name: s.name,
      author: (s.ar||s.artists||[]).map(function(a){return a.name;}).join('/'),
      cover: (s.al && s.al.picUrl) || '',
      intro: '',
      bookUrl: 'https://music.163.com/api/v3/song/detail?c=' + java.encodeURI(JSON.stringify([{id: s.id}]))
    });
  }
  return out;        // ★ 必须 return JS 数组，不能 JSON.stringify
})()
```
字段规则（纯键名）：`name=$.name` `author=$.author` `coverUrl=$.cover` `bookUrl=$.bookUrl`

### 9.2 歌单全曲目补全（trackIds → 批量取名）

```js
var ids = (pl.trackIds||[]).map(function(t){return t.id;});
var known = {};
(pl.tracks||[]).forEach(function(t){known[t.id] = t.name + ' - 歌手';});
var unknown = ids.filter(function(i){return !known[i];});
for (var i = 0; i < unknown.length; i += 50) {
  var cs = unknown.slice(i, i+50).map(function(x){return {id: x};});
  var rr = String(java.ajax('.../api/v3/song/detail?c=' + java.encodeURI(JSON.stringify(cs))));
  JSON.parse(rr).songs.forEach(function(s){known[s.id] = s.name;});
}
// 225 曲歌单 = 5 次批量请求 ≈ 10s，一次性
```

### 9.3 正文（播放地址）

```js
@js:(function(){
  var d = JSON.parse(String(result)).data[0];
  if (!d.url) throw new Error('无版权或VIP专享, 可尝试登录');
  return d.url;        // 纯 URL，ExoPlayer 直接拉流
})()
```

## 10. 避坑清单

| # | 坑 | 对策 |
|---|---|---|
| K1 | @js 列表规则 return JSON 字符串 → 列表大小 0 | return JS 数组（本App getElements 只认 List/Array/NativeArray） |
| K2 | Java 方法返回字符串的 `.length` 是 undefined → 补零/截断循环失效 | String() 包裹 |
| K3 | weapi POST 200 空体（源站 22ms 秒拒） | 降级 /api/ 明文接口 |
| K4 | 音频源写 replaceRegex 切断播放 URL | 音频源禁用 replaceRegex |
| K5 | 搜索结果 album.picUrl 为 null | 用 artists[0].img1v1Url |
| K6 | 歌单 tracks 只有 10 首 | trackIds 全量 + 批量 v3 song detail |
| K7 | c 参数含 `[{` 特殊字符 | java.encodeURI(JSON.stringify([...])) |
| K8 | 中文 cat 参数未编码 | exploreUrl 的 <js> 里 java.encodeURI |
| K9 | 音频直链有效期约 30 分钟 | 每次播放重新走 content 规则取新链（别缓存） |
| K10 | loginUrl 作用域无 cookie 对象 | 用 source.putLoginHeader（自动写 CookieStore） |
| K11 | 登录 weapi 空响应时 toast 显示空 | 显式 `if (!r) toast('weapi返回空, 改用Cookie')` |
| K12 | bookUrlPattern 误匹配搜索 URL → 结果按详情页解析 | 只匹配 detail 路径，不含 search/toplist/list |

## 11. 验证方法论

1. **加密链路**：固定 secKey，真机 JS 输出 params/encSecKey，Python 反解（AES 两层 + RSA modPow 比对）证明端到端正确
2. **接口可用性**：沙盒 urllib 与真机 `java.ajax` 各测一遍（沙盒 5.5s/请求 vs 真机 0.2s，差异本身是信息）
3. **列表协议**：eval_js 里 `new AnalyzeRule().setContent(真实响应).getElements('规则')` 看 `r.length`
4. **全链路**：debug_source 四前缀（关键词=搜索 / 绝对URL=详情 / ++URL=目录 / --URL=正文 / ::URL=发现）
5. **官方校验**：check_source 通过 1/1

## 12. 案例档案

| 站点 | 现象 | 解法 | 状态 |
|---|---|---|---|
| music.163.com | weapi 200 空体 | 全降 /api/，Cookie 登录 | ✅ check 1/1，debug 全链路（搜索30/歌单225章/单曲1章/直链+歌词/发现63+30+30） |

## 13. 通用结论

1. **"加密接口返回空"先怀疑站点策略，别怀疑算法**——用固定密钥做双向验证（JS 出 Python 解）是最快定位手段
2. **明文 /api/ 镜像往往数据和加密接口一样全**（甚至更全，如 trackIds），优先找明文镜像
3. **App 行为以实测为准**：getElements 的 String 丢弃行为与旧记忆冲突时，以 eval_js 实测为准
4. Rhino 里所有 Java 返回字符串一律 String() 包裹再操作
