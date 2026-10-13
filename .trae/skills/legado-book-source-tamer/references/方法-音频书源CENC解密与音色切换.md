# 方法：音频书源 CENC 解密与音色切换

> 案例：番茄听书 (APP) `https://fanqienovel.com` —— bookSourceType=1 音频书源
> 日期：2026-10-13 ｜ 参考：ch6vip/fqapp（Rust 版官方接口实现）、红果短剧 v5（CENC 同源算法）

## 0. 适用识别

一次命中以下特征即可套用本篇：

- 站点是 **ByteDance 系**（fqnovel / fanqiesdk / novelfm / 番茄 / 红果 / 抖音）
- 响应带 `encrypt_info: {encrypt:true, spade_a, kid, encryption_method:"cenc-aes-ctr"}`
- MP4 头有 `enca` / `sinf` / `tenc` / `saiz` / `saio` / `senc` box
- `media_type:"audio"` + `mime_type:"audio_mp4"`
- App 的 ExoPlayer 无 Widevine CDM（Legado 全系均无，`media3-exoplayer-hls` 都被注释）

## 1. 音频书源的三个类型声明（缺一不可）

```json
"bookSourceType": 1          // 音频；BookType.audio = 0b100000 = 32
"ruleToc": { "chapterList": "... book.setType(32); ..." }   // 目录规则里也要设
"ruleContent": { "content": "... return 'file://'+FQ_CACHE+path;",
                 "subContent": "... 音色名 ..." }
```

**为什么 ruleToc 里还要 setType**：`WebBook.getChapterListAwait` 会 `removeAllBookType()` 再 `addType(bookSource.getBookType())`，详情页设的 type 会被冲掉（记忆21/48 同款坑）。

**音频 content 就是播放地址**：源码 `AudioPlay.contentLoadFinish()` → `durPlayUrl = content`。返回 `file://` 本地路径即可，不需要任何 HTML。

**`subContent` = 歌词/副标题通道**：`BookContent.kt` 里 `book.isAudio → putLyric(subContent)`。本案例用来显示当前音色名。

## 2. 播放地址接口（本轮最大卡点）

番茄听书有三套音频接口，只有一套能用：

| 接口 | 结果 |
|---|---|
| `POST /reading/reader/audio/playinfo/` | HTTP 200 但 **content-length: 0**，只有音色列表 |
| `POST /novelfm/playerapi/video_model/mget/v1`（条件不齐） | `{"code":4000,"message":"bad request"}` 或 404 |
| **`POST /novelfm/playerapi/video_model/mget/v1`（条件齐）** | ✅ 可用 |

**可用配置**（缺一即 bad request）：

```
host : https://api5-sinfonlineb.novelfm.com
path : /novelfm/playerapi/video_model/mget/v1
query: aid=3040 & app_name=novelapp & version_code=58932 & version_name=5.8.9.32
       channel=0 & device_type=UGFFI55 & device_platform=android
       manifest_version_code=632 & dpi=440 & device_brand=Redmi & os_api=35 ...
       & iid={install_id} & device_id={device_id}
body : {"audio_type":0,"bgm_used":0,"book_id":...,"device_score":0,
        "item_ids":[cid],"multi_shift":false,"source":"default",
        "tone_id":N,"user_select_start_para":0,"user_select_start_para_off":0}
sign : x-argus / x-ladon / x-ss-stub=md5(body) ；UA = com.dragon.read
```

**踩坑记录**：我先后试过 88 个 aid（3040~3060、1112~1180、1967、8662…）全部 `{"code":403,"message":"invalid aid"}`；换 host 试过 8 个（`api5-sinfonline{a,b,c}.novelfm.com` / `api-sinfonline{a,b,c}.fanqiesdk.com` / `api5-normal-sinfonline{a,b}.fqnovel.com`）分别得到 404 或 invalid aid。
**真正的解法不是换 aid/host，而是把 `device_type=UGFFI55` + `version_code=58932` + `channel=0` 一起补齐**。

**`aid` 白名单只在 novelfm.com 域生效**；`api5-*.fqnovel.com` 域只认 `reading/` 路径。

## 3. main_url 是明文，不需要 spade URL 解密

| 字段 | 形态 |
|---|---|
| `video_model.video_list["0"].main_url` | **https 明文**，直接可下载 |
| `fallback_api` 响应的 `video_list.video_1.main_url` | spade 密文（需 `data.key_seed`） |

本例可以直接下载明文流，省掉一整套 SHA512+AES-CBC 的 URL 解密。
**判据**：`url.indexOf('http')===0` → 明文。

`video_model` 本身是**嵌在 JSON 里的字符串**，必须二次 `JSON.parse(rows[0].video_model)`。

## 4. CENC 内容密钥派生（spade_a → 16 字节 key）

```
raw = base64Decode(spade_a)                       # 32 字节（b64 44 字符）
v8  = len(raw) - (raw[0]^raw[1]^raw[2]) + 47      # 再钳到 len-1
work = raw[1 : 1+v8]
a, b = 85, 246
for i in 0..v8-1:
    prev = (i & 1) ? a : b
    if (i & 1) a = work[i] else b = work[i]
    work[i] = (-21 - popcount(i) + (prev ^ work[i])) & 255
key = ascii(work[1:33])                            # 32 个 ASCII 字符
```

实测向量（本例第 1 章）：

```
spade_a = "o7wt9WeNL/BTthTOW4cg/Fq1FvlasRD/XbIn/2uBJNFrniOMjA=="
key     = "b33b1fd00a72cca355412646b53f6759"
```

**算法与红果短剧 v5 完全一致**（记忆107），ByteDance 系通用。

## 5. MP4 box 定位与逐样本解密

### 5.1 关键 box 实测偏移

```
ftyp@0/28          moov@28/271365
stsd@433/183   →  enca@449                      # fourcc type 字段在 453
stsc@648/76    →  5 条 [1,2822][2,2821][3,2822][7,2821][8,2781]
stsz@724/90152 →  22533 个样本，dflt=0（逐样本 size）
stco@90876/48  →  8 个 chunk，ch[0]=271409
senc@90924/180280 → 22533 个 IV，每样本 8 字节
saio@271204/20  saiz@271224/17  sgpd@271241/26  sbgp@271267/28
```

**注意 moov 有 271 KB**：只下载 `Range: 0-300000` 就能拿到全部 stbl 元数据，不必先下全文件。

**box 遍历要支持 `sz===1`（64 位 size）**：本例 moov size 是 `0x00042405`=271365（注意不能把 `0x00000424` 误读成 1060）。

**IV 逐样本递增**：`0d1dc53f2201f0bf → f0c0 → f0c1`（标准 CENC，块计数在低字节）。

### 5.2 解密循环（用 System.arraycopy 回写）

```js
for c in chunks:
    off = stco[c]
    spc = stsc 指针推进查表                       # 必须 O(n) 指针推进，O(n²) 会 48 秒
    for k in 0..spc-1:
        size = stsz[idx]
        iv16 = senc[idx*8 : idx*8+8] + 8×0x00
        cipher.init(DECRYPT, key, new IvParameterSpec(iv16))
        dec = cipher.doFinal(Arrays.copyOfRange(bytes, off, off+size))
        System.arraycopy(dec, 0, bytes, off, size)   # ★ 唯一可靠的回写方式
        off += size; idx++
```

**★ `bytes[off+i] = dec[i] & 255` 会报「无法将 255 转换为 java.lang.Byte」**（Rhino 对 byte[] 索引赋值的类型转换缺陷）。必须用 `Packages.java.lang.System.arraycopy(dec, 0, bytes, off, size)`。

### 5.3 解密成功判据

首样本头变成 `2111450014500146fff10a5a5a5a5a5a`

= AAC-HE (SBR) ADTS 帧 `FF F1 0A 5A`。

若仍是随机字节 → key 派错或 IV 拼错；若首字节 `FF F1` 但后续乱 → IV 块计数没补零。

## 6. fourcc 修复（必须限定范围）

```
enca → mp4a
sinf → free（并把 sinf 的 body 全部清零）
```

**★ 性能杀手**：对 8.6 MB 全文件逐字节扫 4 字符，实测 **46.9 秒**；
限定在 moov 范围（本例 `< 400000`）后 **0 ms**。

定位 sinf 的稳妥写法：`sinf` 的 type 字段在 `q`，则 box 头在 `q-4`，size = `u32(q-4)`：

```js
if (u32(q-4) >= 8 && u32(q-4) < 50000 && q-4+size <= len) {
    bytes[q]=0x66; bytes[q+1]=0x72; bytes[q+2]=0x65; bytes[q+3]=0x65;   // "free"
    for (j=q+4; j<q-4+size; j++) bytes[j]=0;
}
```

## 7. 解密提速：Cipher 复用（51 s → 7.8 s）

| 写法 | 22533 样本耗时 |
|---|---|
| 每样本 `Cipher.getInstance('AES/CTR/NoPadding')` | **51.8 s** |
| **只在循环外 getInstance 一次，循环内只 init** | **7.8 s** |

同时避免把 byte[] 手工转字符串再转回来（用 `Arrays.copyOfRange` + `System.arraycopy`）。

## 8. 写文件与缓存

```js
var hex  = HexUtil.encodeHexStr(bytes);
var path = java.downloadFile(hex, 'https://x/'+fname+',{"type":"m4a"}');
return 'file://' + FQ_CACHE + path;
```

**★★ 最容易踩的坑：文件名必须唯一**

`java.downloadFile` 的第二个参数 URL 决定输出文件名。早期版本固定 `https://x/fqa.m4a`，导致：

```
fqA_book1_ch1_0 -> /85c5a4e3adeba826.m4a
fqA_book2_ch1_0 -> /85c5a4e3adeba826.m4a     ← 同一路径！
fqA_book3_ch1_0 -> /85c5a4e3adeba826.m4a
```

三本书互覆盖，缓存机制完全失效。**正解**：`fname = 'fa'+tone+'_'+itemId.substring(0,18)+'.m4a`。

缓存键设计：`fqA_<bookId>_<itemId>_<tone>`（音色不同必须分文件，否则换音色不生效）。

命中判据：先 `java.readFile(path)` 验证 `length > 100000`，实测 **487 ms** 返回（首次 17 s）。

淘汰：保留最近 6 个，超出 `java.deleteFile` + 清键。

## 9. 音色体系

`POST /reading/bookapi/audio/toneinfo/?book_id=X` → `data.tts_tones[]`：

```json
{"id":97,"title":"升级版","is_multi_tone":true,"badge":"多角色","description":"自然流畅"}
{"id":74,"title":"成熟大叔音升级版","icon_url":"...","tone_gender":1}
{"id":4,"title":"成熟大叔音","description":"经典"}
{"id":1,"title":"甜美少女音"}  {"id":2,"title":"清亮青叔音"}
{"id":5,"title":"开朗青年音"}  {"id":6,"title":"温柔淑女音"}
```

- 书自身的可用音色表：`audio/detail` 的 `data.tones`（逗号串，如 `"4,1,5,2,74,6,4,97"`）
- `tone_id=0` = 默认（服务端推荐）
- 不同音色 = 不同音频文件（实测 duration 都不同：默认 523.15s / 97 号 509.41s / 74 号 461.14s）

jsLib 内置常用 24 项（含未命名的用「音色N」占位），切换按钮循环遍历。

## 10. 音色选择 UI（登录界面按钮 + Toast）

```json
"loginUi": [
 {"name":"使用说明","type":"text","view":"...","chars":1},
 {"name":"🎙 切换音色","type":"button","action":"FQ_atoneBtn(source,java)"},
 {"name":"🎵 当前音色","type":"button","action":"FQ_atoneShow(source,java)"},
 {"name":"↩️ 恢复默认音色","type":"button","action":"FQ_atoneReset(source,java)"},
 {"name":"🔍 检查连通/设备状态","type":"button","action":"FQ_acheck(source,java)"},
 {"name":"🗑 清空音频缓存","type":"button","action":"FQ_aclear(source,java)"}
]
```

三个音色函数（jsLib）：

```js
function FQ_atoneBtn(sv,jv){
  var n=FQ_atoneNext(sv);
  jv.toast('已切换音色：'+n);          // ★ jv.toast，不是 java.toast
  return n;
}
function FQ_atoneShow(sv,jv){
  var n=FQ_atoneName(sv);
  jv.toast('当前音色：'+n+'（ID '+FQ_atone(sv)+'）');
  return n;
}
function FQ_atoneReset(sv,jv){
  FQ_asetTone(sv,0);
  jv.toast('音色已重置为默认(推荐)');
  return 'default';
}
```

**要点**：
1. `type` 只能用 `text`/`button`（E 版只渲染这三种；LT 版还支持 select/toggle 但跨版本不要用）
2. **说明性内容一律用 `type:"button"` + action toast**，不要用 `label`（渲染 when 无分支，静默不显示）也不要给 text 加自定义 `view` 键（GSON 静默丢弃）
3. `source.put('fqTone', id)` 持久化；`source.get()` 未设置返回 `null`，**Rhino 的 JsNull 是 truthy**，必须 `String(...)` 归一化后再判 `'null'/'undefined'/''`
4. 音色名同时写进 `ruleContent.subContent`，阅读时显示在副标题位置

## 11. 音频源专属避坑清单

| # | 坑 | 解法 |
|---|---|---|
| K1 | `bookSourceType` 忘改或只写 `ruleToc` | 顶层 `bookSourceType=1` + `ruleToc` 里 `book.setType(32)` 双重声明 |
| K2 | 用视频播放器测音频 | 音频走 `AudioPlay`，`durPlayUrl = content`；测试应看书源返回的 file:// 是否合法 |
| K3 | `main_url` 当成密文去解密 | 先判断 `indexOf('http')===0`；只有 fallback 里那个才是密文 |
| K4 | `video_model` 当对象直接用 | 它是嵌在 JSON 里的**字符串**，要二次 `JSON.parse` |
| K5 | 接口报 bad request 就疯狂换 aid/host | 本例真正缺的是 `device_type=UGFFI55`+`version_code=58932`+`channel=0` |
| K6 | 只下 0-63 字节判 mp4 头 | 前 1KB 明文（`check_info: e:0-511-...`），**后面全是密文**；必须看 100000 字节之后 |
| K7 | 误把 CBC-IV 只毁首块的认知套到全文件 | AES-CTR 是流式，IV 错则**整条样本全乱**（对比红果视频 CBC 的经验） |
| K8 | `bytes[i]=dec[i]&255` | Rhino 报「无法转换为 java.lang.Byte」；必须 `System.arraycopy` |
| K9 | 每样本 `Cipher.getInstance` | 51.8 s；循环外 getInstance 一次 → 7.8 s |
| K10 | 全文件扫 fourcc | 46.9 s；只扫 moov 范围 → 0 ms |
| K11 | `downloadFile` 文件名固定 | 多书互覆盖、缓存失效；必须 `fa<tone>_<itemId>` |
| K12 | 缓存键不含音色 | 换音色仍返回旧音频；键必须是 `fqA_<book>_<item>_<tone>` |
| K13 | 不限文件大小 | 36 MB 时 hex 通道需 144 MB 直接 OOM；设 22 MB 上限并给换音色提示 |
| K14 | jsLib 函数里裸写 `java.ajax` | jsLib 作用域 `java` 是 JavaPackage 不是 JsExtensions；必须显式传 `jv` 参数 |
| K15 | 规则里引用 `key` / `page` | `searchUrl` 已带 `{{key}}`、`exploreUrl` 已编码分页时，规则里这两个变量**未定义**；从 `baseUrl` 反解 |
| K16 | `enca` fourcc 位置找错 | `enca` 的 type 字段在 box头+4（本例 449 是 size，453 才是 type）；别把 size 字段改成 mp4a |
| K17 | 缓存路径硬编码 | `java.downloadFile` 返回的是相对路径，拼 `file://` 前缀要用**真实包名**的 cache 目录 |
| K18 | 音频 hex 字符串不释放 | 8.6 MB 文件 hex 长 17 MB，解密完要 `bytes=null; hex=''; System.gc()` |

## 12. 验证方法论（三端一致）

1. **沙盒交叉验证**：Python/Node 实现同一算法，输出逐字节对比（本例 key 向量 `b33b1d00...`）
2. **App 内 eval_js 真实规则路径**：`source.getContentRule()` 拿规则 → 伪造 `book/baseUrl/result` → eval
3. **MCP debug_source 全链路**：搜索 → 详情 → 目录 → 正文
4. **check_source 官方校验**：`page`/`key` 未定义类错误只有校验器会暴露
5. **真机播放**：最终必须用户确认能出声（WebView 的 `<video>` 对 CENC 会报 `PIPELINE_ERROR_DECODE` 且 `encrypted=0`，这是**解密成功的反证**——容器可读但样本解不开）

## 13. 与红果视频 CENC 的异同

| 维度 | 红果短剧（视频） | 番茄听书（音频） |
|---|---|---|
| 播放地址 | spade 密文，需 `key_seed` + SHA512 + AES-CBC | `main_url` 直接明文 |
| fourcc 修复 | `encv → hev1`（**不是 hvc1**） | `enca → mp4a` |
| 编码门槛 | 需避开 `bytevc2`（bv2C） | 无（aac 全平台可解） |
| 样本 IV | 8B + 8B 大端块计数 | 同 |
| key 派生 | 同（spade_a → 32 ASCII） | 同 |
| 解密后判据 | `0000001d 40010c02`（H.265 VPS NAL） | `2111450014500146`（AAC-HE ADTS） |
| 交付形态 | 写 `.mp4` → `openVideoPlayer` | 写 `.m4a` → `AudioPlay`（durPlayUrl） |
| 速度 | 720p 6.6 MB ~9 s | 8.6 MB ~17 s |

## 14. 通用结论

1. **字节系站点优先找"明文直链"**：不要一上来就复现最复杂的分支；先用 Range 拉几百 KB 看头部字节，`ftyp` 可读 ≠ 全明文，要看到 100000 字节之后
2. **`content-length: 0` 的 200 响应用"缺必备参数"解释**，不是限流不是签名错（本例换 88 个 aid 都没用）
3. **接口调不通时，先读参考实现的完整 URL 常量**（fqapp 的 `audio.rs` 一次给出 host/path/params/body/headers），比盲试快一个数量级
4. **MP4 解密三件套可跨站复用**：spade 派生 / 逐样本 CTR / fourcc 修复；差异只在 fourcc 目标值和地址形态
5. **音频书源的交付终点是 `file://`**，不是 HTML、不是 URL 数组

## 15. ★★ 音色选择 UI 的两种落点与「infoMap 不可用」诊断（260913 实战补充）

### 15.1 两个落点对比

| 落点 | 优点 | 限制 |
|---|---|---|
| **登录界面 `loginUi`** | 可显示"当前音色"（`<js>` 每次打开重新生成）；按钮可带 ✅ 标记 | 需要 `loginUrl` 非空（否则 `hasLoginForm` 判定/JS 环境不全） |
| **发现页 `exploreUrl`** | 与书籍浏览同屏，随手可切 | 依赖 `infoMap` 传递输入框内容（**本 App 实测不可用**） |

**结论**：音色切换按钮**放登录界面最稳**（不依赖 infoMap）。发现页只保留"点一下就切换"的纯按钮（不读输入框）。

### 15.2 ★★★ `loginUi` 的 `<js>` 环境绑定（源码级）

`SourceLoginDialog.evalUiJsResult()`：
```kotlin
source.evalJS("$loginJS\n$jsStr") {
    put("result", result)     // = getLoginData(rowUis) 或 viewModel.loginInfo
    put("book", viewModel.book)
    put("chapter", viewModel.chapter)
}
```
**没有 `source`、没有 `java`、没有 `infoMap`**。

⇒ `<js>FQ_atoneRows()</js>` 里**不能访问 source**，否则 `ReferenceError: "source" 未定义` → **整个登录界面渲染失败（表现为"登录界面打不开/不显示"）**。

### 15.3 ★★★ 按钮 `action` 的环境绑定

`ExploreAdapter.evalButtonClick()` / `SourceLoginDialog` 按钮回调：
```kotlin
source.evalJS(jsStr) {
    put("java", java)       // SourceLoginJsExtensions（继承 RssJsExtensions）
    put("infoMap", infoMap) // ★ 部分分支/版本没有这一行
}
```
**没有 `source`**。

⇒ action 里写 `FQ_xxx(source,java)` 会因 `source` 未定义而**静默失败**（点击无反应）。
⇒ **正解：action 只用 `java`**，函数签名改成 `function FQ_xxx(jv)`，内部用 `jv.put/jv.get/jv.toast`。

### 15.4 ★★★ `java`（SourceLoginJsExtensions）能做什么

| 可用 | 说明 |
|---|---|
| `jv.put(k,v)` / `jv.get(k)` | **与 `source.put/get` 完全同一键空间**（实测 crossRead=true） |
| `jv.toast(s)` / `jv.longToast(s)` | UI 线程 toast |
| `jv.ajax/get/post/head` | 网络（继承 JsExtensions） |
| `jv.searchBook(kw)` | 打开系统搜索（`RssJsExtensions.searchBook(key, searchScope=null)`；**activity 为空时静默无效**） |
| `jv.reLoginView(delta)` / `jv.reUiView(delta)` | 刷新登录界面/发现界面（`SourceLoginJsExtensions` 特有，经 callback） |
| `jv.refreshExplore()` | 刷新发现页 |

**不可用**：`jv.searchBook(kw, sv)`（第二参必须是 `BookSource` 对象，规则里没有）、`jv.startBrowser` 在部分版本受限。

### 15.5 ★★ 输入框内容传递失败的确诊法（本次实证）

在 text 的 `action` 里把环境全量 dump 到书源变量：

```js
function FQ_bindKw(jv){
  var names=['infoMap','result','java','source','key','title','page','baseUrl','text','value'];
  var found=[];
  for(var n=0;n<names.length;n++){try{found.push(names[n]+'='+eval('typeof '+names[n]));}catch(e){found.push(names[n]+'=ERR');}}
  var got='';
  try{if(typeof infoMap!=='undefined'&&infoMap&&infoMap['搜索词'])got=String(infoMap['搜索词']);}catch(e0){}
  try{jv.put('fqDiag3',found.join(',')+' || got='+got);}catch(e1){}
  if(got){try{jv.put('fqSearchKw',got);}catch(e2){}}
  return '';
}
```

实测输出（决定性）：
```
fqDiag2 = "bindKw@1791868143707 | infoMapType=undefined | got="
```
⇒ **text 的 action 确实被触发（有时间戳），但 `infoMap` 是 `undefined`** —— 该 App 版本的 ExploreAdapter **不注入 infoMap**。
⇒ 任何依赖 `infoMap['键名']` 的取词方案在该版本上**必然失败**，与键名无关。

**应对**：需要用户输入的交互，改用
1. `jv.searchBook('')` 打开系统搜索页（用户在那里输入）
2. 或把可选值做成**按钮**（如音色列表），彻底不需要输入

### 15.6 音色逐按钮 UI 生产模板

```js
function FQ_atoneRows(){                       // 供 loginUi 的 <js> 调用（无参、不访问 source）
  var rows=[];
  rows.push({name:'📖 使用说明（点击查看）',type:'button',action:'FQ_ahelpSafe(java)'});
  rows.push({name:'🎵 查看当前音色',type:'button',action:'FQ_toneShowSafe(java)'});
  for(var i=0;i<FQ_TONES.length;i++){
    var t=FQ_TONES[i];
    rows.push({name:'🎙 '+t.n,type:'button',action:'FQ_toneSetSafe(java,'+t.i+')'});
  }
  rows.push({name:'↩️ 恢复默认音色',type:'button',action:'FQ_toneResetSafe(java)'});
  return JSON.stringify(rows);
}
function FQ_toneSetSafe(jv,id){                // 只用 java 绑定
  var nm=FQ_toneNameById(id);
  try{jv.put('fqTone',String(id));}catch(e1){}
  try{jv.toast('已切换音色：'+nm);}catch(e2){}
  try{jv.longToast('🎙 已切换音色：'+nm+'\n（返回本书后重新进入章节生效）');}catch(e3){}
  try{jv.reLoginView(false);}catch(e4){try{jv.reUiView(false);}catch(e5){}}
  return 'ok';
}
```

配套：`loginUrl` 必须**非空**（至少 `function login(){return 'ok';}`），否则 `SourceLoginDialog` 的 `loginJS` 为空、且部分版本判定异常。

### 15.7 验证方法论（本轮踩坑顺序）

1. `eval_js` 里 `source.getLoginUi()` 有值 ≠ 界面能打开 → 必须**真机点开菜单「登录」**
2. `eval_js` 里调 `FQ_atoneRows()` 报 `source 未定义` → 说明函数体引用了 `<js>` 环境没有的绑定
3. 按钮点击无反应 → 在 action 里 dump `typeof` 清单，确认环境到底有什么
4. **`typeof` 清单是本轮唯一能定位"infoMap 不存在"的手段** —— 不要猜键名，直接打印
