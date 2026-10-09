# 方法-字节跳动 X-Argus 签名纯 JS 复现与红果短剧 API 书源

> 2026-10-10 红果短剧 API 版书源实战提炼
> 适用：字节系 App API（红果短剧/番茄小说/抖音系），以及一切"客户端签名"型 API

---

## 0 核心信条

**客户端能算的，书源都能算。**

字节系 App 的 `X-Argus`/`X-Gorgon`/`X-Ladon` 三件套看起来吓人（社区普遍认为需要 unidbg 模拟 so 库），
但拆开看只是 **SIMON-128 分组加密 + SM3 哈希 + AES-CBC + 一套自定义字节流布局**，
全部可在 Legado 的 Rhino 引擎内用纯 JS 复现，**无需外部签名服务、无需 unidbg、无需 JNI**。

> 反例警示：桌面版红果（hongguo-desktop-releases）依赖 `unidbg-sign.jar`（`com.hongguo.sign.FqTrace serve 0`），
> 需要 JRE + so 库常驻 —— 这个架构**书源侧不可行**。但纯 JS 实现可行。

---

## 1 关键技术事实（App 级）

### 1.1 BouncyCastle SM3 在 Legado 里可用 ★★★

SM3 是国密哈希，标准 Java 的 `MessageDigest.getInstance("SM3")` 会抛 `NoSuchAlgorithmException`。
但 Legado 打包了 BouncyCastle，可以直接实例化：

```js
var SM3 = Packages.org.bouncycastle.jcajce.provider.digest.SM3;
var d = new SM3.Digest();
d.update(javaByteArray, 0, len);
var result = d.digest();   // 32 字节
```

**实测验证**：`SM3("abc")` = `66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0` ✅

**踩坑**：`Packages.org.bouncycastle.jcajce.provider.digest.SM3` 是个 **class**（`typeof === 'function'`），
必须 `new SM3.Digest()` 才能拿到实例。`new SM3()` 会失败。

### 1.2 MD5 用 `MessageDigest`，不要用 `java.md5Encode`

`java.md5Encode` 在 jsLib 作用域**不存在**（绑的是 BookSource 对象），
且只接受单参 String（传两参会报"找不到方法"）。

统一用：
```js
var d = Packages.java.security.MessageDigest.getInstance('MD5');
d.update(byteArray);
var r = d.digest();
```

### 1.3 byte[] 互转的唯一可靠姿势 ★★★

Rhino 里 `Packages.java.lang.reflect.Array.newInstance(Byte.TYPE, n)` **不可用**
（报 `newInstance 不是函数，它是 object`）。`java.strToBytes` 返回的对象也不能直接当 byte[] 用。

**唯一可靠**：借道 `String` + `ISO-8859-1` 编码

```js
var CS = Packages.java.nio.charset.Charset.forName('ISO-8859-1');

// Uint8Array -> java byte[]
function jb(u8){
  var s='';
  for(var i=0;i<u8.length;i++) s += String.fromCharCode(u8[i] & 0xff);
  return new Packages.java.lang.String(s).getBytes(CS);
}

// java byte[] -> Uint8Array
function j2u(jarr){
  var o = new Uint8Array(jarr.length);
  for(var i=0;i<jarr.length;i++) o[i] = jarr[i] & 0xff;
  return o;
}
```

ISO-8859-1 是单字节映射，`0x00-0xFF` 无损往返，是 byte[] 通道的完美载体。

### 1.4 jsLib 作用域里 `java.ajax` 是 object 不是 function ★★★

这是**反复踩中的老坑**（memory 31/49/63 均有记录）。规则上下文里 `java.ajax` 正常，
但 **jsLib 顶层函数里 `java.ajax`/`java.post` 全部不可用**（报"ajax 不是函数，它是 object"）。

**解法：参数注入** —— 所有需要联网的 jsLib 函数把 `java` 作为**第一个参数**显式传入：

```js
// jsLib
function HG_API(JV, path, bodyObj, extra){   // ← JV = java 注入
  var java = JV;
  ...
  var r = java.ajax(url + ',' + JSON.stringify(opts));
  return String(r);
}

// 规则里调用
HG_API(java, '/novel/player/...', {...})
```

同理 `source` 也要显式传参（`HG_check(java, source)`）。

### 1.5 列表规则必须返回 JS 数组（LT 版）

`AnalyzeRule.getElements` 对 `Mode.Js` 返回值**只接受 List/Array/NativeArray**，
返回 String 会直接得到空列表（memory 49）。

```js
// ✘ 错误：整体 JSON.stringify
return JSON.stringify(out);          // → 列表大小 0

// ✔ 正确：返回数组，每个元素是 JSON 字符串
var out = [];
out.push(JSON.stringify({name:..., url:...}));
return out;                          // → 列表正常，字段规则用 $.name 直取
```

字段规则用 `$.name` / `$.url`（JSONPath 纯键名），**LT/E 双版本通用**。

---

## 2 红果短剧 API 全貌

### 2.1 域名与基础参数

```
核心域名：https://api5-normal-sinfonlineb.fqnovel.com
备用域名：api5-normal-sinfonlinea / sinfonlinec / lf / lq / hl .fqnovel.com

业务参数（短剧）：aid = 8662
app_name = novelread
UA = com.phoenix.read/72932 (Linux; U; Android 12; zh_CN; V2284A; Build/V417IR;tt-ok/3.12.13.20)
```

### 2.2 接口清单（实测）

| 用途 | 方法 | 路径 | 关键参数 |
|---|---|---|---|
| **分集详情（全集）** | POST | `/novel/player/multi_video_detail/v1/` | `series_id` + `biz_param` |
| **播放地址** | POST | `/novel/player/multi_video_model/preload/v1` | `vid` + `mixed_video_id_map` + **`video_platform:1024`** |
| 搜索（API 版） | GET | `/reading/bookapi/search/tab/v` | `query` + `tab_name:feed` + `search_source:1` |
| 搜索（网页版） | GET | `https://hongguoduanju.com/search/{kw}` | 解析内嵌 `"searchList":[...]` |
| 发现（榜单） | GET | `https://hongguoduanju.com/rank/hot-drama` | HTML 解析 `a[href^=/detail?series_id=]` |

### 2.3 ★ 播放接口的两个致命参数

```js
// 错误示范（返回 code=100001 "video platform invalid, param:0"）
var BP = { detail_page_version:0, device_level:3, ... };  // 缺 video_platform

// 正确（实测返回 19KB 完整 video_model）
var BP = {
  detail_page_version: 0,
  device_level: 3,
  disable_digg_stat: false,
  need_all_video_definition: true,
  need_mp4_align: false,
  use_os_player: false,
  use_server_dns: false,
  video_platform: 1024          // ★ 必须 1024
};
var body = {
  biz_param: BP,
  dr_scene: 'preload',
  mixed_video_id_map: { '1004': [vid] }   // ★ 1004 是短剧的 platform key
};
```

**注意**：`video_platform` 必须放在 `biz_param` **内部**（放顶层无效）。
错误信息 `param:0` 是"没读到该字段"的表现，不是"值错误"。

### 2.4 分集详情响应结构

```
data.{series_id}.video_data
  ├─ series_title      剧名
  ├─ series_intro      简介
  ├─ series_cover      封面（带签名的 heic 图，expires 约 30 天）
  ├─ episode_cnt       总集数
  ├─ duration          总时长（秒）
  ├─ video_platform    3
  ├─ pay_info          {pay_type:0}  ← 0 = 免费
  └─ video_list[]      ★ 全集列表
       ├─ vid           视频 ID（雪花 ID）
       ├─ vid_index     集数（1 起）
       ├─ title         该集标题
       ├─ duration      时长（秒）
       └─ cover / episode_cover
```

### 2.5 播放地址响应结构

```
data.{vid}
  ├─ expire_time        过期时间（unix 秒）
  ├─ video_height       1280
  └─ video_model        ★ 是 JSON 字符串，需要二次 JSON.parse
       ├─ video_list[]  5 档清晰度
       │    ├─ main_url      主直链（明文 MP4）
       │    ├─ backup_url    备用直链
       │    └─ video_meta    {definition:"1080p", vwidth, vheight, bitrate, codec_type}
       ├─ url_expire     直链过期时间（约 3 小时）
       └─ big_thumbs     进度条缩略图（heif 格式）
```

**实测**：5 档 = 360p / 480p / 540p / 720p / 1080p，全部**明文 MP4、无 DRM、无防盗链**。
Range 请求验证：`bytes=0-1023` 返回 1024 字节真实数据 ✅

### 2.6 网页版 vs API 版的能力对比

| 能力 | 网页版 | API 版（本书源） |
|---|---|---|
| 搜索 | ✅ | ✅（走网页版） |
| 发现/榜单 | ✅ | ✅（走网页版 HTML） |
| 详情 | ✅ | ✅ |
| **全集目录** | ❌ 仅前 3 集 | ✅ **全部集数** |
| **播放** | ❌ 第 4 集起 404 | ✅ **全集可播** |
| 清晰度 | 单一 | 5 档可选 |

**结论**：网页版只能"看个开头"，API 版才是完整方案。这也是用户最初质问"为什么不去开源项目查节点"的答案。

---

## 3 X-Argus 签名算法全解

### 3.1 三个签名头

| 头 | 长度 | 算法 |
|---|---|---|
| `X-Argus` | ~240 字符 base64 | Protobuf 序列化 + SIMON-128-CBC + AES-CBC 外壳 |
| `X-Gorgon` | 52 字符 hex | 自定义流密码（魔改 RC4 + 位反转） |
| `X-Ladon` | 48 字符 base64 | 自定义 Feistel 网络（0x22 轮） |
| `X-Khronos` | 10 字符 | 就是 unix 时间戳 |

### 3.2 固定常量

```js
var SIGN_KEY  = hexToBytes('ac1adaae95a7af94a5114ab3b3a97dd80050aa0a39314c40528caec95256c28c');
var ARGUS_HEADER = hexToBytes('3ccc');
var ARGUS_PREFIX = hexToBytes('a6e783ee7001100918');
var ARGUS_SUFFIX = hexToBytes('567b');
var ARGUS_XOR_WORD = hexToBytes('d04ffdff');
var LICENSE_ID   = 1611921764;
var METASEC_APP_ID = 3019;
var SDK_VERSION  = 135135744;
var COUNTER_VALUE = 1388734;
var SIMON_Z = word64(0x046d678b, 0x3dc94c3a);
```

### 3.3 SIMON-128 实现要点

SIMON 是 NSA 设计的轻量分组密码（Feistel 结构，64 位半块）。

```js
// 密钥扩展：4 个初始 key word → 72 轮密钥
function srk(key){
  var w=[]; for(var i=0;i<4;i++) w.push(readWord64LE(key, i*8));
  for(var x=4; x<72; x++){
    var m = xor(ror(w[x-1],3), w[x-3]);
    m = xor(m, ror(m,1));
    w.push(xor(not64(w[x-4]), m, zbit((x-4)%62), word64(3,0)));
  }
  return w;
}

// 加密：32 轮 Feistel
function sEnc(b, keys){
  var l=readWord64LE(b,0), r=readWord64LE(b,8);
  for(var i=0;i<keys.length;i++){
    var oldR = r;
    var nl = and64(rol(r,1), rol(r,8));
    r = xor(l, nl, rol(r,2), keys[i]);
    l = oldR;
  }
  ...
}
```

**关键**：SIMON 的轮密钥是 72 个（不是 32 个），因为要支持 128/192/256 位密钥。

### 3.4 Protobuf 手工编码

Argus 载荷是 protobuf，字段固定，手工 varint 编码即可：

```js
function pbVarint(field, value){
  return concat(encodeVarint(field*8), encodeVarint(value));      // wire type 0
}
function pbBytes(field, bytes){
  return concat(encodeVarint(field*8+2), encodeVarint(bytes.length), bytes);  // wire type 2
}
```

字段表（实测有效）：
```
1:  0x20200929*2  (版本标识)
2:  2
3:  randomValue (4 字节随机数)
4:  METASEC_APP_ID (3019)
6:  LICENSE_ID (1611921764)
7:  "6.8.1.32"
8:  "v04.07.01-ml-android"
9:  SDK_VERSION (135135744)
10: 8 字节零
12: timestamp*2
13: SM3(body)[0:6]
14: SM3(queryString)[0:6]
15: nested{1:signCount, 2:COUNTER, 3:COUNTER, 4:COUNTER}
20: "none"
21: 738
```

### 3.5 外层 AES-CBC 封装

```js
function argus(q, stub, ts, op){
  var pb = pkcs7Pad(protobuf(...));                    // PKCS7 补齐
  var sk = sm3(concat(SIGN_KEY, ARGUS_HEADER, ARGUS_SUFFIX, SIGN_KEY));  // 派生密钥
  var keys = srk(sk);
  // SIMON 加密（16 字节分组）
  var enc = [];
  for(var off=0; off<pb.length; off+=16) enc.push(sEnc(pb.slice(off,off+16), keys));
  // 异或混淆：从第 8 字节起，与 i%8 位置异或
  var encoded = concat(XOR_WORD, XOR_WORD, concat(...enc));
  for(var i=8; i<encoded.length; i++) encoded[i] ^= encoded[i%8];
  // 包壳：前缀 + 反转 + 后缀
  var container = concat(ARGUS_PREFIX, reverse(encoded), ARGUS_SUFFIX);
  // AES-CBC 外壳（key/iv 从 SIGN_KEY 派生）
  var key = hexToBytes(md5Hex(SIGN_KEY.slice(0,16)));
  var iv  = hexToBytes(md5Hex(SIGN_KEY.slice(16)));
  return base64(concat(ARGUS_HEADER, aesEncrypt(container, key, iv)));
}
```

### 3.6 X-Gorgon 实现要点

```
种子构造（20 字节）：
  md5(queryString)[0:4]  +  stubPrefix[0:4]  +  md5(cookie)[0:4]  +  [0,1,7,4]  +  timestamp[4字节]

流密码加密：
  1. 魔改 RC4：key = [0x4a, param&0xff, 0x16, headerByte3, 0x47, 0x6c, param>>8, headerByte2]
  2. 位反转（0xAA/0xCC/0xF0 掩码三次）
  3. 与下一字节 + 长度掩码异或

输出：0x84 0x04 headerByte2 headerByte3 paramLo paramHi + 加密后的 20 字节（hex）
```

### 3.7 X-Ladon 实现要点

```
轮密钥：md5(randomBytes(4) + aid) → 展开成 288 字节 → 36 个 64 位 key
加密：36 轮 Feistel（与 SIMON 类似但轮函数不同）
明文："{timestamp}-{LICENSE_ID}-{METASEC_APP_ID}" PKCS7 补齐
输出：base64(randomBytes(4) + 密文)
```

---

## 4 书源结构设计

### 4.1 jsLib 分层

```
sign.js    ← 密码学原语 + HG_sign(url, opts) 主入口
hgapi.js   ← HG_API(JV, path, body, extra) 统一请求封装
rules.js   ← HG_search / HG_detail / HG_chapters / HG_play / HG_explore / HG_check
```

### 4.2 URL 设计（关键技巧）

书籍 URL 用 **API 域名 + 查询参数** 形式，让规则能从 baseUrl 反解参数：

```
详情：https://api5-normal-sinfonlineb.fqnovel.com/detail?series_id=7690186465237535768
章节：https://api5-normal-sinfonlineb.fqnovel.com/play?vid=7690262796616879129&series_id=...&idx=1
发现：https://api5-normal-sinfonlineb.fqnovel.com/explore?path=rank/hot-drama&page=1
```

这样 `HG_SID(baseUrl)` / `HG_VID(baseUrl)` / `HG_ep(baseUrl)` 就能反解参数。
**注意**：这些 URL 本身不会被请求（详情/目录/正文规则都是 `@js:` 直接调 API），
只是**参数容器** —— 这是"POST + 加密"类站点的通用模式。

### 4.3 搜索关键词反解

`bookList` 上下文**没有 `key` 变量**（源码证实 BookList 从不 setLocal），
必须从 `baseUrl` 反解：

```js
function HG_kw(u){
  var s=String(u||'');
  var i=s.indexOf('/search/');
  if(i<0) return '';
  var rest=s.substring(i+8);
  var q=rest.indexOf('?'); if(q>=0) rest=rest.substring(0,q);
  var sl=rest.lastIndexOf('/'); if(sl>=0) rest=rest.substring(0,sl);
  try{ return decodeURIComponent(rest); }catch(e){ return rest; }
}
```

配合 `searchUrl` 用 `@js:` 生成：`'https://hongguoduanju.com/search/'+encodeURIComponent(key)+'?hg=1'`
（`?hg=1` 是防止 Legado 把搜索页当详情页解析的哨兵）。

### 4.4 括号配平提取内嵌 JSON

网页版数据藏在 `_ROUTER_DATA` 的 `"searchList":[...]` 里，
**不能用贪婪正则**（会吃尾）也不能用非贪婪（内层 `}` 会截断）：

```js
function HG_jsonArray(text, marker){
  var i = String(text).indexOf(marker);
  if(i<0) return null;
  var j = i + marker.length;
  while(j<text.length && /\s/.test(text[j])) j++;
  var open = text[j], close = open==='['?']':'}';
  var depth=0, quoted=false, esc=false, end=j;
  for(; end<text.length; end++){
    var ch = text[end];
    if(quoted){ if(esc) esc=false; else if(ch==='\\') esc=true; else if(ch==='"') quoted=false; continue; }
    if(ch==='"') quoted=true;
    else if(ch===open) depth++;
    else if(ch===close && --depth===0) break;
  }
  try{ return JSON.parse(text.substring(j, end+1)); }catch(e){ return null; }
}
```

必须处理**字符串状态**（引号内的括号不计数）与**转义**。

---

## 5 验证方法论

### 5.1 分层验证（本次有效）

| 层 | 手段 | 结果 |
|---|---|---|
| 密码学原语 | App 内 `SM3("abc")` 对比标准值 | ✅ 逐字节一致 |
| 签名生成 | 检查三头长度（240/52/48） | ✅ |
| **签名有效性** | 真实调 API 看 `code` | ✅ `code:0` |
| 业务接口 | detail 返回 76 集 / 58KB | ✅ |
| 播放地址 | 解析出 5 档 main_url | ✅ |
| 直链可播 | Range 请求 1024 字节 | ✅ |
| 全链路 | `debug_source` 搜索→详情→目录→正文 | ✅ |
| 官方校验 | `check_source` | ✅ 1/1 |
| 字段一致性 | 逐字段 md5 | ✅ 8/8 |

### 5.2 关键诊断技巧

**签名失败的表现**：`code:101000 service error` / `debug_info: "pack ret empty"`
→ 说明请求被网关丢弃（签名校验不通过）

**参数缺失的表现**：`code:100001 invalid param` + `debug_info: "video platform invalid, param:0"`
→ 说明签名**通过了**，只是业务参数不对（`param:0` 表示读到的值是 0/缺失）

**这个区分极其重要**：`100001` 出现时不要再去查签名，直接查参数。

### 5.3 MCP 长参数不稳定问题

MCP 的 `eval_js` 传超长 JS（>10KB）时会报"参数 js 不能为空"。
**解法**：
- 短脚本直接 `eval_js`
- 长脚本走 `dpaste 上传 + 深链导入 + debug_source`
- 或把 jsLib 写入书源后，用 `eval_js` 调 jsLib 里的函数（此时 `eval_js` 只需几行）

---

## 6 避坑清单

| # | 坑 | 解法 |
|---|---|---|
| K1 | `java.md5Encode` 在 jsLib 不存在 | 用 `MessageDigest.getInstance('MD5')` |
| K2 | `java.md5Encode` 只接受单参 | 不要传 charset |
| K3 | `Array.newInstance` 不可用 | 用 `String` + `ISO-8859-1` 转 byte[] |
| K4 | `Packages...SM3` 要 `new SM3.Digest()` | 不是 `new SM3()` |
| K5 | jsLib 里 `java.ajax` 是 object | **参数注入** `HG_API(java, ...)` |
| K6 | 列表规则返回 String 得到空列表 | 返回 **JS 数组**，元素是 JSON 字符串 |
| K7 | `key` 变量在 bookList 上下文不存在 | 从 `baseUrl` 反解 |
| K8 | 播放接口缺 `video_platform` | `biz_param.video_platform = 1024` |
| K9 | `mixed_video_id_map` 格式 | `{'1004': [vid]}`，key 是字符串 |
| K10 | `video_model` 是 JSON 字符串 | 二次 `JSON.parse` |
| K11 | 网页版数据藏在 `_ROUTER_DATA` | 括号配平提取，勿用正则 |
| K12 | 搜索页被当详情页解析 | searchUrl 加 `?hg=1` 哨兵 |
| K13 | 网页版只有前 3 集 | 用 API 的 `multi_video_detail` |
| K14 | 封面是 heic 格式 | 用 `series_cover`，Glide 能渲染 |
| K15 | 直链有时效（约 3 小时） | 每次实时解析，**不要缓存** |
| K16 | MCP 传长 JS 失败 | 走 dpaste + 深链 |
| K17 | 深链导入不落库 | `lastUpdateTime` 设为未来时间 |
| K18 | 上传与唤起并行会用到旧地址 | **必须串行**，用返回值里的 URL |

---

## 7 案例档案

| 项目 | 站点 | 签名方案 | 书源可用性 |
|---|---|---|---|
| **红果短剧** | api5-normal-sinfonlineb.fqnovel.com | X-Argus/Gorgon/Ladon | ✅ 本源 |
| 番茄小说 | 同族域名 | 同族签名（aid=1967） | 可复用本方案 |
| 抖音 | 同族域名 | 同族签名 | 可复用 |
| 红果桌面版 | — | unidbg + so 库 | ❌ 架构不可移植 |

---

## 8 交付物清单

```
/workspace/hongguo/api/
  ├─ sign.js            密码学原语 + HG_sign
  ├─ hgapi.js           HG_API 请求封装
  ├─ rules.js           业务规则函数
  ├─ jslib_all.js       合并版（开发用）
  ├─ jslib_final.js     压缩版（书源用，18877 字节）
  └─ booksource_v2.json 成品书源（22497 字节）
/workspace/hongguo/doc/
  └─ 方法-字节跳动X-Argus签名纯JS复现与红果短剧API书源.md（本文档）
```

---

## 9 通用结论

1. **"需要 unidbg" 是社区惯性认知，不是技术事实** —— 先找纯 JS 实现（GitHub 搜索 `X-Argus` + 语言过滤），找不到再考虑原生方案。
2. **签名失败 vs 参数错误要严格区分** —— 错误码不同，排查方向完全不同。`pack ret empty` 查签名，`invalid param` 查参数。
3. **官方 App API 的返回值先打印全部顶层 key** —— 本次 `video_platform` 藏在 `video_data` 里、`video_model` 是嵌套 JSON 字符串，靠猜必错。
4. **开源项目的 Issue / PR / 后端代码是接口金矿** —— 本次 `video_platform:1024` 与 `mixed_video_id_map` 就是从 `hongguo-downloader` 的源码里直接拿到的。
5. **网页版兜底思路**：API 挂了也能从 HTML 拿数据（搜索/发现走网页版），保证书源不会整体失效。
6. **"参数容器 URL"模式**：POST + 加密类站点，用假 URL 携带参数（不发请求），规则内 `@js:` 直调 API。天然规避 Legado 的 GET 语义。
