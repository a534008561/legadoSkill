# 方法：字节系 App 全签名复现与 CM/DH 解密正文通道（番茄小说实战）

> 适用场景：目标站是「字节系 App」（番茄小说/番茄畅听/红果短剧等），网页版有字体反爬或数据不全，
> 需要**完全用官方 App 接口**做书源（搜索/详情/目录/正文/发现），且不借助任何外部签名服务。

---

## 0. 一句话总结

**x-argus(SIMON-128) + x-ladon(自定义流密码) + ttEnc(SHA512派生AES) 三个签名算法纯 JS 复现，
CM 通道（3072-bit MODP DH + AES-256-CBC）解密正文，设备注册走 log.snssdk.com。**
全部在 Legado 的 Rhino 环境内完成，无需 unidbg/外部服务。

---

## 1. 通道选择决策表

| 通道 | 端点 | 是否需要设备 | 能否拿正文 | 结论 |
|---|---|---|---|---|
| **网页版 SSR** | `fanqienovel.com/page/{id}` | 否 | ❌ 字体反爬 | 只做 fallback |
| **搜索（免签）** | `api.fanqiesdk.com/api/novel/channel/homepage/search/search/v1/` | 否 | — | ✅ 主搜索 |
| **目录（需签）** | `api5-normal-sinfonlineb.fqnovel.com/reading/bookapi/directory/all_items/v` | ✅ | 含 book_info | ✅ 主目录+详情 |
| **batch_full（需签+设备）** | `.../reading/reader/batch_full/v` | ✅ | ⚠️ crypt_status=2 | 部分可用 |
| **CM 全文（需签+设备）** | `novelfm-hl.snssdk.com/novelfm/playerapi/full/mget/v1/` | ✅ | ✅ **明文** | ✅ **主正文** |
| **发现页（需签）** | `.../reading/bookapi/bookmall/tab/v` | ✅ | — | ✅ 主发现 |
| **首页 SSR** | `fanqienovel.com/` 的 `__INITIAL_STATE__` | 否 | — | ✅ 备用发现 |

---

## 2. 三大签名算法（纯 JS 复现要点）

### 2.1 x-argus（SIMON-128 分组密码 + protobuf 手工编码）

**Bean 结构（protobuf 字段序）**：
```
field1  = 1077940818 (varint 常量)
field2  = 2
field3  = rand (32位随机)
field4  = aid (字符串)
field5  = device_id (字符串)
field6  = "1611921764" (license_id 字符串)
field7  = version_name ★从 query 提取，不能硬编码
field8  = "v04.04.05-ov-android"
field9  = 134744640
field10 = 8字节零
field11 = 0
field12 = ts*2
field13 = SM3(stub_bytes)[:6]
field14 = SM3(query)[:6]
field15 = {1:1, 2:1, 3:1, 7:0xC792ECCC}
field16 = install_id
field20 = "none"
field21 = 738
field23 = {1:"NX551J", 2:8196, 4:0x80E0D800}
field25 = 2
```

**加密链**：
```
1. pkcs7_pad(bean, 16)
2. SIMON-128-ECB 加密（72 轮密钥，key 来自 FQ_SK hex）
3. magic8 = f2f7fcfff2f7fcff
4. un = magic8 + enc + tail9(eafb2cfe8568519154)
5. buf[0:8] = magic8; buf[i>8] ^= magic8[i%8]
6. buf = reverse(buf)
7. buf += "ao"; pkcs7_pad
8. AES-128-CBC-NoPadding(buf, AK, AIV)   ← ★ 必须 NoPadding（已手工 pad）
9. base64(f281 + ct)
```

### 2.2 x-ladon（自定义流密码）

```
data = "{ts}-{license_id}-{aid}"    ← ★ license_id=1611921764 固定，不是 aid
pkcs7_pad(data, 16)
key_schedule = MD5(rp + aid) 展开 34 轮（rp = 4字节随机）
逐 16 字节加密（每块 34 轮：r ^= keys[i] + (l + ror(r,8)); l ^= r + ror(l,61)）
base64(rp + ct)
```

**★ 参数顺序陷阱**：`FQ_ladon(ts, lic, aid, rp)` —— 早期版本写成 `FQ_ladon(ts, aid, rp)` 把 aid 当 license_id，导致签名全部失效。

### 2.3 ttEnc（设备注册 body 加密）

```
rnd = 32字节随机
hv = SHA512(SHA512(rnd) + FIXED_32B)
key = hv[0:16], iv = hv[16:32]
hd = SHA512(data) + data
AES-128-CBC-NoPadding(pkcs7(hd), key, iv)
输出 = magic6(746305100010) + rnd + ct
```

**★ 必须用 NoPadding**：手工 pad 后若再用 PKCS5Padding 会**多补一个块**（224→240 字节），服务端直接拒绝。

---

## 3. 设备注册（log.snssdk.com）

```
POST https://log.snssdk.com/service/2/device_register/?{sorted_query}
body = ttEnc(gzip(json))
headers = {content-type: application/octet-stream;tt-data=a, accept-encoding:gzip, user-agent, connection:Keep-Alive}
```

**★ gzip 字节必须与 zlib 逐字节一致**：
```js
// Java GZIPOutputStream 输出 XFL=0/OS=255，需手工改为 XFL=2/OS=3
for(i){ v=arr[i]&255; if(i===8)v=2; if(i===9)v=3; ... }
```
否则服务端返回 `{"device_id":0,"install_id":0}`（静默失败）。

**★ 参数集必须 32 项**（含 tt_data/os_api/device_type/ssmix/.../mcc_mnc），
缺任何一项都会被静默拒绝（返回 0）。

---

## 4. CM 正文通道（核心）

```
POST https://novelfm-hl.snssdk.com/novelfm/playerapi/full/mget/v1/?aid=3040&...&device_id={d}&iid={i}
body = {"book_id":"{bid}","item_ids":["{item}"],"key":"{handshake}"}
headers = 签名头 + Content-Type: application/json; charset=utf-8 + x-ss-stub=MD5(body)
```

**握手（client_handshake）**：
```
pk = random(256) % (P-1)              ← P = 3072-bit MODP (RFC 3526 group 15)
pub = 2^pk mod P
pubBytes = 无符号大端，去前导零        ← ★ 必须去前导零（否则 388 vs 384 hex）
iv = random(16)
key = base64(iv + AES-128-CBC-PKCS5(pubBytes, REQ_KEY, iv))
```

**响应解密**：
```
srv = base64_decode(resp.key)
shared = srv^pk mod P
sharedBytes = 无符号大端，去前导零，取前 32 字节  ← ★ aesKey = sharedBytes[:32]
cb = base64_decode(resp.content)
iv = cb[:16]; ct = cb[16:]
plain = AES-256-CBC-PKCS5(ct, aesKey, iv)
text = String(plain, "UTF-8")         ← ★ 必须显式 UTF-8
```

**★★ 三个致命细节**：
1. `BigInteger.toString(16)` 结果可能带前导零字节（388 vs 384 hex）→ 必须 `if(h.length>384) h=h.substring(h.length-384)`
2. `java.util.Base64.getDecoder().decode()` 正确；`Packages.android.util.Base64.decode()` 返回**全零**（坏实现）
3. `FQ_j2s(byte[])` 必须用 `new Packages.java.lang.String(b, Charset.forName('ISO-8859-1'))`，用 `b[i]&255` 会失真

---

## 5. Legado 环境陷阱（本项目踩坑全集）

| 坑 | 现象 | 解法 |
|---|---|---|
| **jsLib 里 java.* 不可用** | `java.strToBytes 不是函数，它是 object` | 全部改用 `Packages.*`，或把 java 作参数传入 |
| **`Packages.android.util.Base64.decode` 返回全零** | 解密必然失败 | 用 `Packages.java.util.Base64.getDecoder().decode()` |
| **`FQ_j2s` 用 `b[i]&255` 失真** | hex 输出差 1（0x46 vs 0x47） | 用 `new Packages.java.lang.String(b, ISO-8859-1)` |
| **`@js:` 顶层不能 return** | `返回的值无效` | 一律 IIFE 包裹 |
| **`key`/`page` 在 bookList 上下文不存在** | `ReferenceError: key 未定义` | 用 `typeof key!=='undefined'` 保护，或从 baseUrl 提取 |
| **URL 分隔符用 `##`** | 详情页 404 | 用单个 `#`（`String.fromCharCode(35)`） |
| **exploreUrl 指向 `##tabN`** | check_source 报"发现目录失效" | 用**真实可请求的 URL**（首页） |
| **check_source 需要 checkKeyWord** | "搜索目录失效" | `ruleSearch.checkKeyWord` 填一个真实能搜到的词 |
| **目录 catalog_data 为 null** | 目录列表为空 | 回退 `item_data_list`（同结构） |
| **dpaste 限频** | HTTP 400 | 改用 `uguu.se`（`POST /upload.php`, field `files[]`） |
| **MCP save_source 超 19KB** | 参数截断 | 走 uguu + 深链导入 |

---

## 6. 目录/详情双字段兼容

```js
// 详情：目录接口同时返回 book_info（零额外请求）
var raw = FQ_api(java, source, '/reading/bookapi/directory/all_items/v', 'book_id='+bid+'&'+base);
var j = JSON.parse(raw);
var bd = (j.data && j.data.book_info) || {};
// name=book_name, author=author, kind=category, intro=abstract, cover=thumb_url

// 目录：catalog_data 可能为 null → 回退 item_data_list
var cats = j.data.catalog_data || j.data.item_data_list || [];
// catalog_data: {catalog_id, catalog_title, item_id}
// item_data_list: {item_id, title, volume_name, ...}
var t = c.catalog_title || c.title || ('第'+(i+1)+'章');
var id = c.item_id || c.catalog_id;
```

---

## 7. 发现页两种方案

**方案 A（推荐，check_source 友好）**：首页 SSR
```js
var raw = FQ_web(java, 'https://fanqienovel.com/', UA);
var d = FQ_state(raw);   // 括号配平提取 window.__INITIAL_STATE__
var groups = ['weekList','editorList','updateList','newbookList',...];
// 每项：{bookName, author, category, abstract, thumbUri, bookId}
```
exploreUrl = `首页推荐::https://fanqienovel.com`

**方案 B**：bookmall/tab/v（9 个 tab：推荐/经典/知识/听书/看剧/视频/短篇/漫画/买书）
```js
var q = 'tab_type='+tt+'&offset='+off+'&client_template=0&'+base;
var d = JSON.parse(FQ_api(java, source, '/reading/bookapi/bookmall/tab/v', q));
// d.data.tab_item[].cell_data[].book_data[] → {book_id, book_name, author, ...}
```

---

## 8. 验证方法论

1. **逐字节对照**：每个中间值（bean 长度、enc hex、pub hex、shared hex、aesKey hex）都要与 Python 参考实现比对
2. **长度断言**：pub=384hex、shared=384hex、aesKey=64hex、key=300/320 base64
3. **golden 向量**：固定 ts/rand/device_id，比对完整签名输出
4. **分段验证**：先验证签名能过（接口返回 200 有数据），再验证解密
5. **check_source 是最终裁判**：它会做完整的搜索→详情→目录链路校验

---

## 9. 站点档案

- **aid**: 1967（番茄小说 App）/ 3040（CM 全文接口）/ 13（免签搜索）
- **license_id**: 1611921764
- **版本**: com.dragon.read 6.5.1.32（version_code 65132）
- **搜索**: `api.fanqiesdk.com/api/novel/channel/homepage/search/search/v1/`（免签，10条/页）
- **目录**: `api5-normal-sinfonlineb.fqnovel.com/reading/bookapi/directory/all_items/v`
- **正文**: `novelfm-hl.snssdk.com/novelfm/playerapi/full/mget/v1/`
- **发现**: `.../reading/bookapi/bookmall/tab/v` 或首页 SSR
- **注册**: `log.snssdk.com/service/2/device_register/`
- **设备池**：建议存 2-3 个设备（`source.put('fqPool','d,i,o,c|d,i,o,c')`），首个失败自动切换

---

## 10. 性能参考

| 操作 | 耗时 |
|---|---|
| 搜索（10条） | 0.4s |
| 详情（含目录请求） | 1.0s |
| 目录（1496章） | 0.8s |
| 正文（3486字） | 1.5s |
| 发现页（36本） | 0.6s |
| 设备注册 | 0.5s |

---

## 11. 关键源码出处（fqapp 开源项目 github.com/ch6vip/fqapp）

- `src/sign/argus.rs` — argus Bean 结构 + SIMON 加密
- `src/sign/ladon.rs` — ladon 流密码
- `src/sign/simon.rs` — SIMON-128 分组密码
- `src/device/crypto.rs` — ttEnc / registerkey 加解密
- `src/upstream/cm.rs` — CM 握手与解密
- `src/endpoints/full.rs` — CM 全文接口
- `src/endpoints/book.rs` — 目录/详情接口
- `src/endpoints/home.rs` — 发现页接口

---

## 12. 发现页分类体系（26012 补充）

### 12.1 三个独立的数据源

| 入口 | 接口 | 参数 | 数量 |
|---|---|---|---|
| **榜单/分类榜** | `/reading/bookapi/bookmall/cell/change/v1/` | `cell_id=7098235271900037133` + `req_rank_category_id` + `req_rank_algo` | 16/页 |
| **频道 tab** | `/reading/bookapi/bookmall/tab/v` | `tab_type`（真实ID见下表） | 16-20/页 |
| **首页 SSR** | `https://fanqienovel.com/` | 无 | 35+/次 |

### 12.2 榜单 cell 的完整结构（★ 挖出分类体系的关键）

`cell_view.rank_with_category_data` 内含三组元数据：
```json
{
  "category_list": [{"category_id":0,"category_name":"全部"}, ...16个],
  "sub_info_list": [{"info_id":0,"info_name":"全部","info_type":1}, ...16个],
  "rank_algo_list": [{"rank_algo":101,"rank_name":"推荐榜"}, ...4个]
}
```

**16 个分类**（category_id）：
```
0=全部  37=穿越  19=系统  1=都市  3=现代言情  7=玄幻  5=古代言情  36=重生
452=架空  511=东方玄幻  522=打脸  259=奇幻仙侠  262=都市脑洞  8=科幻末世
257=玄幻脑洞  1079=衍生
```

**4 个榜单**（rank_algo）：`101=推荐榜 100=完本榜 200=巅峰榜 104=口碑榜`

### 12.3 频道 tab 的真实 ID（★ 不是顺序索引！）

服务端返回的 `tab_item[].tab_type` 才是真实 ID：
```
2=推荐  11=经典  12=知识  5=听书  8=看剧  16=视频  103=短篇  9=漫画  15=买书
```
⚠️ 用 1/2/3/4... 顺序猜会拿到错误频道（听书/看剧/视频返回空）。

### 12.4 发现页 URL 参数分发设计（Legado 实现）

**关键约束**：`exploreUrl` 里的 URL 必须是**真实可请求**的（check_source 会校验），
但又要携带自定义参数 → **用 query 参数 + 统一分发**：

```
📊 排行榜::
🔥 推荐榜::https://fanqienovel.com?t=rank&cat=0&algo=101
📚 分类榜::
🌀 穿越::https://fanqienovel.com?t=rank&cat=37&algo=101
📖 频道::
✨ 推荐::https://fanqienovel.com?t=tab&tt=2
```

`ruleExplore.bookList` 单函数分发：
```js
var u=String(baseUrl||'');
if(/[?&]t=rank/.test(u))      → FQ_pickBooks(java,source,cat,algo,page)
else if(/[?&]tt=/.test(u))    → FQ_tabBooks(java,source,tt,page)
else                          → FQ_homeList(java,source)   // 首页兜底
```

**★ 分组标题**：`标题::`（URL 为空）会被 Legado 渲染为**不可点击的分组标题行**，
让发现页层次清晰（本项目 4 个分组 + 25 个入口）。

### 12.5 各频道正文形态差异

| 频道 | 正文形态 | 处理 |
|---|---|---|
| 推荐/经典/知识/短篇 | 纯文本（CM 通道） | ✅ 直接可用 |
| **漫画** | `{"materials":{"img_N":{"data":{"encrypt_web_uri":...}}}}` | 需解析 JSON + 拼图床 URL |
| **听书** | 音频（需 `audio_play` 接口 + tone_id） | 需专门适配 |
| **看剧/视频** | 视频（需 `multi_video_detail`） | 需专门适配 |
| 买书 | 需特殊参数 | 未适配 |

漫画图床拼接规律（待验证）：
```js
// web_uri = "novel-pic/{md5}" 或 "tos-cn-i-7vwuozyx5p/{hash}"
// 完整 URL 需加签名参数（encrypt_algorithm=aes-256-gcm 表示加密图，可能需额外处理）
```

---

## 13. legado-E 兼容性（26012 补充）

### 13.1 报错现象

```
com.script.ScriptException: org.mozilla.javascript.EcmaError: 
TypeError: [JavaPackage org.bouncycastle.jcajce.provider.digest.SM3.Digest] 不是函数，它是 object。
```

**根因**：legado-E 的 R8 裁剪/依赖配置不同 → BouncyCastle 类不可用（LT 版可用）。
`Packages.xxx` 访问不存在的类时返回 **JavaPackage 对象**（不是 function），调用即报错。

### 13.2 解法：把密码学算法全部改成纯 JS（零 Java 依赖）

**① 纯 JS SM3（国密标准，已验证 3 个标准向量）**

```js
function FQ_sm3(s){
  var rotl=function(x,n){n=n&31;return ((x<<n)|(x>>>(32-n)))>>>0;};
  var len=s.length,bitLen=len*8,arr=[];
  for(var i=0;i<len;i++)arr.push(s.charCodeAt(i)&255);
  arr.push(0x80);
  while(arr.length%64!==56)arr.push(0);
  var hi=Math.floor(bitLen/4294967296),lo=bitLen>>>0;
  arr.push((hi>>>24)&255,(hi>>>16)&255,(hi>>>8)&255,hi&255);
  arr.push((lo>>>24)&255,(lo>>>16)&255,(lo>>>8)&255,lo&255);
  var V=[0x7380166f,0x4914b2b9,0x172442d7,0xda8a0600,0xa96f30bc,0x163138aa,0xe38dee4d,0xb0fb0e4e];
  for(var b=0;b<arr.length;b+=64){
    var W=[];
    for(var i=0;i<16;i++)W.push(((arr[b+i*4]<<24)|(arr[b+i*4+1]<<16)|(arr[b+i*4+2]<<8)|arr[b+i*4+3])>>>0);
    for(var j=16;j<68;j++){
      var x=(W[j-16]^W[j-9]^rotl(W[j-3],15))>>>0;
      x=(x^rotl(x,15)^rotl(x,23))>>>0;
      W.push((x^rotl(W[j-13],7)^W[j-6])>>>0);
    }
    var W1=[];for(var j=0;j<64;j++)W1.push((W[j]^W[j+4])>>>0);
    var A=V[0],B=V[1],C=V[2],D=V[3],E=V[4],F=V[5],G=V[6],H=V[7];
    for(var j=0;j<64;j++){
      var Tj=(j<16)?0x79cc4519:0x7a879d8a;
      var SS1=rotl((rotl(A,12)+E+rotl(Tj,j&31))>>>0,7);
      var SS2=(SS1^rotl(A,12))>>>0;
      var FFj=(j<16)?((A^B^C)>>>0):(((A&B)|(A&C)|(B&C))>>>0);
      var GGj=(j<16)?((E^F^G)>>>0):(((E&F)|((~E)&G))>>>0);
      var TT1=(FFj+D+SS2+W1[j])>>>0;
      var TT2=(GGj+H+SS1+W[j])>>>0;
      D=C;C=rotl(B,9);B=A;A=TT1;
      H=G;G=rotl(F,19);F=E;E=(TT2^rotl(TT2,9)^rotl(TT2,17))>>>0;
    }
    V[0]=(V[0]^A)>>>0;V[1]=(V[1]^B)>>>0;V[2]=(V[2]^C)>>>0;V[3]=(V[3]^D)>>>0;
    V[4]=(V[4]^E)>>>0;V[5]=(V[5]^F)>>>0;V[6]=(V[6]^G)>>>0;V[7]=(V[7]^H)>>>0;
  }
  var out='';for(var i=0;i<8;i++)out+=('0000000'+V[i].toString(16)).slice(-8);
  return out;
}
```

**标准测试向量（必须全部通过）**：
```
sm3('abc')  = 66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0
sm3('')     = 1ab21d8355cfa17f8e61194831e81a8f22bec8c728fefb747ed035eb5082aa2b
sm3('abcd'*16) = debe9ff92275b8a138604889c18e5a4d6fdb70e5387e5765293dcba39c0c5732
```

**② 纯 JS Base64 双通道兜底**

```js
function FQ_b64eJS(str){ /* 标准 base64 编码 */ }
function FQ_b64dJS(str){ /* 标准 base64 解码 */ }

// 双通道：优先用 java.util.Base64，失败降级纯 JS
function FQ_b64d2(s){
  try{return Packages.java.util.Base64.getDecoder().decode(String(s));}
  catch(e){return FQ_s2j(FQ_b64dJS(String(s)));}
}
```

### 13.3 依赖审计清单（跨版本兼容必查）

用以下方法审计书源的全部 `Packages.*` 依赖：

```js
var deps=[];var lib=String(source.getJsLib());
var re=/Packages\.[a-zA-Z0-9_.]+/g;var m;
while((m=re.exec(lib))!==null){if(deps.indexOf(m[0])<0)deps.push(m[0]);}
JSON.stringify(deps);
```

**高风险依赖（E 版可能缺失）**：

| 依赖 | 风险 | 替代方案 |
|---|---|---|
| `Packages.org.bouncycastle.*` | ❌ E 版缺失 | 纯 JS 实现（SM3/SM4 等） |
| `Packages.android.util.Base64` | ❌ 返回全零 | `Packages.java.util.Base64` 或纯 JS |
| `Packages.java.util.Base64` | ⚠️ Java 8+ API | 纯 JS 兜底 |
| `Packages.java.nio.charset.Charset` | ⚠️ 可能缺失 | `String.getBytes("UTF-8")` 字符串参数版 |

**安全依赖（E/LT 都有）**：
`javax.crypto.Cipher` / `java.math.BigInteger` / `java.security.MessageDigest` /
`java.util.zip.GZIPOutputStream|GZIPInputStream|Deflater|CRC32` / `java.net.URL` /
`java.io.ByteArrayOutputStream|BufferedReader|InputStreamReader` / `java.util.Arrays` /
`java.util.UUID` / `javax.crypto.spec.SecretKeySpec|IvParameterSpec` / `java.security.SecureRandom`

### 13.4 验证方法

1. **算法级**：纯 JS 实现必须通过标准向量（SM3 三向量 / Base64 全字节往返）
2. **功能级**：`FQ_argus(...)` 长度 > 200（证明 SM3 在签名链中工作）
3. **端到端**：`check_source` + `debug_source` 全链路（搜索→详情→目录→正文）
4. **依赖审计**：`lib.indexOf('bouncycastle')===0 && lib.indexOf('Packages.android.util')===0`
