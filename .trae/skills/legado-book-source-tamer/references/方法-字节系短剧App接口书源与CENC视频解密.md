# 方法 - 字节系短剧 App 接口书源与 CENC 视频解密（番茄短剧·漫剧实战）

> 蓝本：`github.com/ch6vip/fqapp`（番茄小说/短剧/漫剧/听书/漫画 聚合客户端，Rust 核心逆向）
> 成品：`🍅番茄短剧·漫剧(APP)`（bookSourceUrl=`https://api5-normal-sinfonlineb.fqnovel.com##短剧版`）
> 2026-10-13 全程真机实测（LegadoTeam 版 + E 版兼容）

---

## 0. 一句话总结

字节系短剧（番茄/红果同后端）的正确打开方式是**两条通道分开走**：
- **发现/详情/目录** 走 `api5-normal-sinfonlineb.fqnovel.com`（aid=8662，`com.phoenix.read` UA，multi_video_detail / bookmall cell）
- **播放** 走 `api3-normal-sinfonlinea.fqnovel.com`（aid=1967，`com.dragon.read` UA，shortplay video_model）
  因为 aid=8662 通道的低档位是 **bytevc2**（ByteDance 私有编码，安卓解不了），而 aid=1967 通道**各档位都是 bytevc1（H.265，可播）且 URL 是 base64 明文**（不需要 spade 解密）。

---

## 1. 接口全貌（本轮实测）

### 1.1 发现页（漫剧/短剧/动漫）

**两段式**（来自 fqapp `api_client.dart` 的 `_seriesFlowTabs = {8, 16, 24}`）：

```
第一段：GET /reading/bookapi/bookmall/tab/v?tab_type={TT}&client_template=0&offset=0
        &last_tab_index=0&screen_width_px=1281&classic_tab_style=v3
        &bottom_tab_type=0&client_req_type=1
        → data.tab_item[] 里找 tab_type 匹配项 → cell_data[0].cell_id_str + session_id

第二段：GET /reading/bookapi/bookmall/cell/change/v1/?cell_id={CELL}
        &tab_type={TT}&client_template=2&client_req_type=2&offset={OFF}
        &unlimited_selector_change_type={2|1}    ← 首屏=2，翻页=1
        &session_id={SID}                        ← 必须回传（服务端绑设备，否则 101116）
        → data.cell_view.cell_data[] → 递归收集 video_data[]
        → data.next_offset（步长 6~12）/ data.has_more / data.session_id
```

**频道 tab_type 实测表**（★与 fqapp 文档注释有出入，以实测为准）：

| tab_type | 频道名 | 每页条数 | 说明 |
|---|---|---|---|
| 8 | 找剧 | 6 | 真人短剧精选 |
| 16 | （当前服务端未下发） | — | 文档提到但 tab/v 里不存在 |
| 24 | **动漫** | 12 | 文档注释误标为"漫剧" |
| 32 | **漫剧** | 9 | ★实测确认 |
| 38 | 真人剧 | — | 只有 tab 壳，无 cell |

★ **cell_id 会变**（数天级），必须运行时从第一段取，不能硬编码。

### 1.2 搜索（★最难的一环）

**`/reading/bookapi/search/tab/v` 已下线**（返回空体），`/reading/bookapi/search/page/v` **只返回小说**（`book_data`，无 `video_data`），传 `tab_type=11/16/24/32` 都一样。

**可用通道 = 联想词接口**：

```
GET /reading/bookapi/search/suggest/v?query={KW}&keyword={KW}&q={KW}
    → data.query_result_v2[] 里含 video_data 的条目就是短剧/漫剧
    → video_data: {vid, title, series_id, episode_cnt, cover, video_desc, score, play_cnt, vertical}
```

- 固定 **10 条**，无翻页参数（`offset`/`page`/`count` 均无效）
- 混排：小说与视频同在一个数组，需按 `video_data` 字段过滤
- 实测命中率：`万妖`→3条、`都市`→3条、`霸道总裁`→2条、`重生`→3条、`穿成傀儡皇帝`→3条

★ 通用教训：**"搜索接口不可用"时先试联想词接口**——很多 App 的搜索联想与结果共用同一个召回后端，而联想接口往往免鉴权/免风控。

### 1.3 详情 / 目录

```
POST /novel/player/multi_video_detail/v1/
body: {"biz_param":{detail_page_version:0,disable_digg_stat:false,disable_video_relate_book:false,
       need_all_video_definition:false,need_mp4_align:false,screen_width_px:"900",source:7,
       use_os_player:false,use_server_dns:false},"series_id":"{SID}"}
→ data[SID].video_data: {series_title, series_intro, series_cover, episode_cnt, video_list[]}
→ video_list[]: [{vid, vid_index, ...}]  ← 一集一条，vid_index 从 1 起
```

★ **详情与目录共用同一接口**：目录规则再调一次即可，无需分页。

### 1.4 播放（★核心突破）

```
POST https://api3-normal-sinfonlinea.fqnovel.com/novel/player/video_model/v1/
     ?iid=..&device_id=..&aid=1967&app_name=novelapp&version_code=72132
     &version_name=7.2.1.32&device_platform=android&device_brand=Xiaomi&os_version=13&cdid=..
body: {"video_id":"{VID}","content_type":1004,"biz_param":{...,"source":4,"video_platform":3}}
UA: com.dragon.read
→ data.video_model 是**字符串**（需二次 JSON.parse）
→ video_model.video_list 是 **object**（不是数组！key = video_1..video_N）
→ 每档位: {definition:"360p", codec_type:"bytevc1", size:7445409,
           main_url:"<base64 明文 URL>", spade_a:"<CENC 密钥密文>", encryption_method:"cenc-aes-ctr"}
```

**与 aid=8662 通道的对照（决定性）**：

| 项 | aid=8662（phoenix） | aid=1967（shortplay） |
|---|---|---|
| URL 形态 | spade 密文（需 SHA512 派生解密） | **base64 明文**（一层 base64 解码即得） |
| 360~720p 编码 | bytevc2（❌ 安卓解不了） | **bytevc1（✅ 可播）** |
| 1080p 编码 | bytevc1 | bytevc1 |
| key_seed | 在 fallback_api 响应里 | 直接给（但明文 URL 不需要） |
| 结论 | 只适合取高清 | **主用通道** |

★ **通用教训：同站不同 aid 的编码策略可能完全不同**。发现低档位全是 bytevc2 时，不要急着放弃，先试其它 aid/通道。

### 1.5 播放数据实测

| 档位 | 体积 | 编码 |
|---|---|---|
| 360p | 7.1MB | bytevc1 |
| 480p | 10.7MB | bytevc1 |
| 540p | 11.0MB | bytevc1 |
| 720p | 12.9MB | bytevc1 |

---

## 2. CENC-AES-CTR 解密（书源侧完整实现）

### 2.1 密钥派生（spade_a → 16 字节 AES key）

```js
function RG_cencKey(JV, spadeB64){
  var raw = RG_b64d(String(spadeB64).replace(/-/g,'+').replace(/_/g,'/'));
  var len = raw.length;
  if (len < 3) throw new Error('spade_a过短');
  var v8 = len - (RG_U8(raw,0)^RG_U8(raw,1)^RG_U8(raw,2)) + 47;
  v8 = Math.min(v8, len-1);
  if (v8 < 33) throw new Error('spade_a长度无效');
  var work = [];
  for (var i=0;i<v8;i++) work.push(RG_U8(raw,1+i));
  var a=85,b=246;
  for (var i2=0;i2<v8;i2++){
    var old=work[i2], prev=(i2&1)?a:b;
    if (i2&1) a=old; else b=old;
    var pop=0,x=i2; while(x){pop+=x&1;x>>=1;}
    work[i2]=(-21-pop+(prev^old))&255;
  }
  var hs=''; for (var i3=1;i3<33;i3++) hs+=String.fromCharCode(work[i3]);
  return hs;   // 32 个 hex 字符 = 16 字节 key
}
```

★ `prev` 交替 85(0x55)/246(0xF6)，`popcount` 逐位统计，`-21` 偏移——**少任何一项都解出垃圾**。

### 2.2 逐样本解密（AES-CTR）

```js
// 每个样本的 IV = senc box 里的 8 字节 + 8 字节零
var iv16 = 8字节IV + [0,0,0,0,0,0,0,0];
var cph = Cipher.getInstance('AES/CTR/NoPadding');
cph.init(DECRYPT_MODE, key, new IvParameterSpec(iv16));
var dec = cph.doFinal(bytes[off..off+size]);
System.arraycopy(dec, 0, bytes, off, size);   // ★回写必须用 arraycopy
```

★ **Rhino 硬约束**：`bytes[off+i] = dec[i]&255` 会报"无法将 255 转换为 java.lang.Byte"——**唯一可靠回写是 `Packages.java.lang.System.arraycopy`**。

### 2.3 MP4 box 修复（三处）

| 原 fourcc | 改为 | 原因 |
|---|---|---|
| `encv` | **`hev1`**（不是 hvc1！） | 参数集内嵌样本 = hev1 语义；写 hvc1 会让 MediaCodec 拒绝整条视频轨 → **只有声音没画面** |
| `enca` | `mp4a` | 音频轨去加密标记 |
| `sinf` | `free`（且清零后续） | 移除 DRM 描述，否则播放器仍认为加密 |
| `senc` / `saiz` / `saio` | `free`（且清零后续） | **CENC 样本加密索引**——Team 版会忽略，**E 版见到就拒绝播放** |

★ **`hev1` vs `hvc1` 是本任务最大的坑**：ffmpeg 宽容会掩盖，必须真机播放验证。

### 2.4 性能实测

- 360p（7.1MB）：下载 1.2s + 解密 2.4s + 写文件 0.9s ≈ **5s**
- 720p（12.9MB）：≈ 9s
- 解密速度约 3MB/s（Rhino JCE）

---

## 3. 书源工程要点

### 3.1 文件路径（★必须用相对路径读、绝对路径播）

```js
// downloadFile 返回相对路径（如 /5afbb59d8f78322a.mp4）
var path = String(java.downloadFile(outHex, 'https://x/key.mp4,{"type":"mp4"}'));
// 播放必须返回 file:// 绝对路径
return 'file:///storage/emulated/0/Android/data/com.legado.app.release/cache' + path;
```

- `java.readFile('/x.mp4')` ✅（相对路径，内部自动拼 cachePath）
- `java.readFile('/storage/.../cache/x.mp4')` ❌ 返回 null（getFile 会再拼一次前缀）
- `java.getFile()` 有 `isSameOrDescendantOf(externalCache.parentFile)` 守卫

★ **包名探测法**：用 `java.readFile('/')` 触发异常，从 `FileNotFoundException` 消息里读出真实缓存路径（本次拿到 `/storage/emulated/0/Android/data/com.legado.app.release/cache`）。

### 3.2 缓存复用

```js
var cacheKey = 'fv_' + vid + '_' + defName.replace('p','');
var cachedPath = String(source.get(cacheKey) || '');
if (cachedPath) {
  var cb = java.readFile(cachedPath);
  if (cb && cb.length > 100000) { /* 秒播 */ }
}
// 解密成功后
source.put(cacheKey, path);
// 维护 fv_keys 列表，超 6 个删最旧
```

★ **文件名必须含 vid + 画质**，否则多剧多集会互相覆盖。

### 3.3 内存管理（OOM 防线）

```js
hexStr = null;  bytes = null;  outHex = null;
try { Packages.java.lang.System.gc(); } catch(e) {}
```

- hex 通道内存峰值 ≈ 文件的 **4 倍**（hex 字符串 2 倍 + byte[] 2 倍）
- 360p 7MB → 峰值 ~28MB ✅；720p 13MB → ~52MB ⚠️；1080p 23MB → ~92MB ❌ 易 OOM
- **默认 360P** 是安全选择，画质在登录界面可调

---

## 4. E 版兼容（Luoyacheng/legado-E）

### 4.1 纯 JS SM3（R8 裁剪掉 bouncycastle）

E 版报 `Packages.org.bouncycastle.jcajce.provider.digest.SM3.Digest 不是函数，它是 object`。
**必须用纯 JS SM3**（与 BC 实现逐字节一致，已用 3 个标准向量验证）：

```js
function HG_sm3(u8){
  // ... SM3 压缩函数 ...
  var out = new Uint8Array(32);   // ★★ 必须返回 Uint8Array，不能返回普通 Array
  for(var i=0;i<8;i++){var v=V[i];out[i*4]=(v>>>24)&255;...}
  return out;
}
```

★★★ **本任务最隐蔽的坑**：纯 JS 版最初 `return out;`（普通 Array），导致：
- `HG_cat` 的 `instanceof Uint8Array` 判断失败 → 走 `new Uint8Array(arr)` 分支（看似无害）
- 但后续 `HG_srk`/`HG_r64` 等索引访问在某些路径下行为不同
- **现象：签名头完整生成（X-Argus 260 字符）、HTTP 200，但响应体为空**
- **定位方法：决定性对照实验**——把 `HG_sm3` 换回 BC 版，同一请求立即成功（12570 字节）
- **修复：`return new Uint8Array(32)` 逐字节写入**

★ 通用教训：**Rhino 里"看起来等价"的类型差异（Array vs Uint8Array）会造成静默失败**。移植加密算法时，返回类型必须与原实现严格一致。

### 4.2 Base64 双通道

```js
function HG_b64(u8){
  try{ var r=String(Packages.android.util.Base64.encodeToString(HG_jb(u8),2));
       if(r&&r.length>0) return r; }catch(e){}
  return HG_b64JS(u8);   // 纯 JS 兜底
}
```

★ 注意：`Packages.android.util.Base64.encodeToString(Uint8Array, 2)` 在部分版本报"找不到方法"——`HG_jb()` 转换后传 Java byte[] 才稳。


---

## 4.5 E 版深度兼容：NoClassDefFoundError 的根治（★2026-10-13 用户报障修复）

### 4.5.1 症状与根因

**用户报障**：E 版（Luoyacheng/legado-E）搜索和解析发现规则时报
```
java.lang.NoClassDefFoundError: Failed resolution of: Ljava/awt/Color;
```

**根因**：`cn.hutool.core.util.HexUtil` 是 hutool 的类，其**静态初始化块引用 `java.awt.Color`**（桌面 Java 类），Android 上不存在该包。E 版 R8 裁剪掉 hutool 后，任何对它的引用（**包括 jsLib 顶层的 `var RG_HEX = Packages.cn.hutool...`**）都会在**类加载时**抛 NoClassDefFoundError。

★ **关键认知**：这不是"方法调用失败"而是"**类加载失败**"，所以：
- 放在 jsLib **顶层的变量声明**就会触发（不是等到函数被调用）
- try-catch 能捕获（实测验证），但**顶层求值发生在任何 try 之前**

### 4.5.2 三级降级设计（性能是硬约束）

**踩坑记录**：最初用纯 JS 逐字节循环解析 hex，512KB 需 **10.4 秒** → 4MB 视频需 **80 秒**，完全不可用。

**正解：用 Java 标准库 BigInteger 做 hex 转换**（不依赖任何第三方库）：

```js
// ① hex → bytes（三级降级：hutool → BigInteger → 纯JS）
function RG_decodeHex(hex){
  var s=String(hex||'');
  // ① hutool（LT 版，最快）
  try{
    var H=Packages.cn.hutool.core.util.HexUtil;
    if(H && typeof H.decodeHex==='function'){
      var r=H.decodeHex(s);
      if(r && r.length>0) return r;
    }
  }catch(e){}
  // ② BigInteger（E 版首选，性能与 hutool 相当）
  try{
    if(s.length===0) return new Uint8Array(0);
    if(s.length%2===1) s='0'+s;              // ★奇数长度补前导零
    var bi=new Packages.java.math.BigInteger(s,16);
    var arr=bi.toByteArray();
    var n=s.length>>1;
    if(arr.length===n) return arr;
    if(arr.length===n+1) return Packages.java.util.Arrays.copyOfRange(arr,1,arr.length);  // 去符号位
    if(arr.length<n){                        // 补前导零
      var bos=new Packages.java.io.ByteArrayOutputStream();
      for(var i=0;i<n-arr.length;i++) bos.write(0);
      bos.write(arr,0,arr.length);
      return bos.toByteArray();
    }
    return Packages.java.util.Arrays.copyOfRange(arr,arr.length-n,arr.length);
  }catch(e2){}
  // ③ 纯 JS 兜底（慢，仅保底）
  return RG_hexToBytesJS(s);
}

// ② bytes → hex（三级降级）
function RG_encodeHex(b){
  try{
    var H=Packages.cn.hutool.core.util.HexUtil;
    if(H && typeof H.encodeHexStr==='function'){
      var r=String(H.encodeHexStr(b));
      if(r && r.length>0) return r;
    }
  }catch(e){}
  try{
    if(!b || b.length===0) return '';        // ★空数组
    var bi=new Packages.java.math.BigInteger(1,b);   // ★1 = 正数语义
    var h=String(bi.toString(16));
    var want=b.length*2;
    while(h.length<want) h='0'+h;            // ★补前导零
    return h;
  }catch(e2){}
  return RG_bytesToHexJS(b);
}
```

**性能实测（4MB = 8M hex 字符）**：

| 方案 | decode | encode | 可用性 |
|---|---|---|---|
| hutool（LT版） | 66ms/512KB | — | ✅ 最快 |
| **BigInteger（E版）** | **330ms** | **103ms** | ✅ **首选** |
| 纯 JS 逐字节 | 10439ms/512KB | 9079ms/512KB | ❌ 4MB 需 80 秒 |

★ **提速 164 倍**。BigInteger 是 Android 内置类，不受 R8 裁剪影响。

### 4.5.3 Base64 三级降级（同样问题）

```js
function RG_b64d(s){
  var str=String(s||'').replace(/-/g,'+').replace(/_/g,'/');
  try{ var B=Packages.android.util.Base64;      // ① LT 版
       if(B && typeof B.decode==='function'){ var r=B.decode(str,0); if(r&&r.length>0) return r; } }catch(e){}
  try{ var D=Packages.java.util.Base64.getDecoder();  // ② E 版（Java 8+ API）
       var r2=D.decode(str); if(r2&&r2.length>0) return r2; }catch(e2){}
  return RG_b64dJS(str);                         // ③ 纯 JS 兜底
}
```

### 4.5.4 顶层引用的清理原则

**必须从 jsLib 顶层移除的**（加载时求值，E 版必崩）：
```js
var RG_HEX = Packages.cn.hutool.core.util.HexUtil;   // ❌ 元凶
var RG_B64 = Packages.android.util.Base64;           // ❌ 有风险
```

**可以保留的**（Android/Java 核心类，E 版必然存在）：
```js
var HG_CS  = Packages.java.nio.charset.Charset.forName('ISO-8859-1');  // ✅
var RG_MD  = Packages.java.security.MessageDigest;                     // ✅
var RG_ARR = Packages.java.util.Arrays;                                // ✅
var RG_CIPHER = Packages.javax.crypto.Cipher;                          // ✅
var RG_SK  = Packages.javax.crypto.spec.SecretKeySpec;                 // ✅
var RG_IVP = Packages.javax.crypto.spec.IvParameterSpec;               // ✅
```

★ **判定标准**：`java.*` / `javax.*` / `android.*` 安全；`cn.*` / `org.*` / 任何第三方库都有被 R8 裁剪的风险。

### 4.5.5 E 版模拟验证法（★通用技巧）

**问题**：如何在 LT 版 App 里验证"E 版能跑"？

**方法**：读 jsLib 源码 → 用字符串替换"屏蔽"第三方类 → eval → 跑完整链路：

```js
var lib=String(source.getJsLib());
var e3sim=lib
  .replace(/Packages\.cn\.hutool\.core\.util\.HexUtil/g,'Packages.com.sim.nohutool.HexUtil')
  .replace(/Packages\.org\.bouncycastle\.jcajce\.provider\.digest\.SM3\.Digest/g,'Packages.com.sim.nobc.SM3.Digest');
eval(e3sim);
// 之后跑完整链路（签名/搜索/播放/解密）看是否全部降级成功
```

**实测结果**（模拟 E 版）：
```
① 签名: X-Argus len=216 X-Ladon len=48        ✅ SM3 走纯 JS
② 搜索: n=3 :: 万妖图录传第一季                 ✅
③ 播放数据: 360p / 4MB                         ✅
④ 下载: 3.9MB                                  ✅
⑤ hex→bytes: len=4126725 (BigInteger 路径)     ✅
⑥ 解密: samples=7718 bv2c=false                ✅
⑦ 写文件: 3.9MB 总耗时 5223ms                   ✅
⑧ moov=true hev1=true mp4a=true                ✅
```

★ **这是"跨版本兼容验证"的通用套路**——不用等用户真机反馈，在开发环境就能模拟目标版本的能力缺失。


### 4.5.7 ★★★ 二次报障与根治（2026-10-13 晚）

**用户二次报障**（同一错误，但堆栈不同）：
```
java.lang.NoClassDefFoundError: Failed resolution of: Ljava/awt/Color;
	at java.lang.reflect.Executable.getParameterTypesInternal(Native Method)
	at java.lang.reflect.Method.getParameterTypes(Method.java:186)
	at org.mozilla.javascript.JavaMembers$MethodSignature.<init>(...)
```

**堆栈的含义（关键）**：异常发生在 **Rhino 的 `JavaMembers$MethodSignature.<init>`** —— 这是 Rhino 在**首次访问某个 Java 类成员时枚举其方法签名**的路径。

★ **这推翻了我上一轮的判断**：我以为"把 hutool 包在 try-catch 里"就安全了，但 Rhino 的**成员枚举发生在 JS 异常处理之外**，try-catch **拦不住**。

**实测验证**（LT 版）：
```js
// 访问不存在的类（Rhino 惰性 JavaPackage）
var P = Packages.com.definitely.not.exist;   // typeof = object（不抛）
var m = P.HexUtil;                            // typeof = object（不抛）
typeof m.decodeHex                            // 'object'（不是 function）
```
→ 所以**正确的守卫写法**是 `typeof H.decodeHex === 'function'`，而不是依赖 try-catch。

**最终解法：彻底移除所有第三方类引用**（不是"包在 try 里"）：

| 项 | 修正前（v3） | 修正后（v4） |
|---|---|---|
| hex 编解码 | hutool → BigInteger → 纯JS（三级） | **只用 BigInteger**（零第三方） |
| HG_b64 | android.util.Base64 + `indexOf('AAAA')` 检查 | android → java.util.Base64 → 纯JS（移除误判检查） |
| 播放 URL 解码 | 直接 `Packages.android.util.Base64.decode` | 走 `RG_b64d`（三级降级） |

**修正后的依赖清单（全部为 Android/Java 核心类）**：
```
android.util.Base64 / java.io.ByteArrayOutputStream / java.lang.String / java.lang.System
java.math.BigInteger / java.nio.charset.Charset / java.security.MessageDigest
java.util.Arrays / java.util.Base64 / javax.crypto.Cipher
javax.crypto.spec.IvParameterSpec / javax.crypto.spec.SecretKeySpec
```
零 `cn.*` / 零 `org.*`。

### 4.5.8 ★ 构建闸门（防止再犯）

这次踩了两个坑，都用**自动化闸门**根治：

**坑1：手改 JSON 破坏 JS 语法**
```python
# ❌ 错误：多了一个 + 号
'hex'+String.fromCharCode(34)+','+String.fromCharCode(34)+'retry'+String.fromCharCode(34)+':2,+String.fromCharCode(34)+'headers'
#                                                                                        ^^^ 多余
# ✅ 正确
'hex'+String.fromCharCode(34)+','+String.fromCharCode(34)+'retry'+String.fromCharCode(34)+':2,'+String.fromCharCode(34)+'headers'
```
→ **闸门**：对**每个** JS 块（jsLib / loginUrl / ruleContent / ruleSearch / …）单独跑 `node --check`

**坑2：只移除顶层引用，忘了函数内的**
→ **闸门**：扫描所有 `Packages.*` 引用，非 `java./javax./android.` 前缀的直接报错

**`build_final.py` 四道闸门**：
```python
【闸门 1】jsLib 文本卫生      —— 零双引号/零反斜杠/零非BMP/零HTML实体
【闸门 2】jsLib 依赖安全      —— 零第三方类 + 顶层声明全为核心类
【闸门 3】JS 块语法          —— 每个 JS 块单独 node --check
【闸门 4】JSON 结构           —— 必需字段齐全
```

★ **通用教训**：**手改长 JSON 里的 JS 代码 = 高危操作**。任何对规则/JS 字段的修改都必须：
1. 改完立刻 `node --check`
2. 导入后回读 App 内实际存储的版本（`source.getContentRule()`）再验一次
3. 不要相信"文件看起来对"——本次就是文件对、但插入时多了个字符


### 4.5.9 ★★★ 三次报障：Team 能播 / E 版不能播（senc 残留）

**用户报障**：
> legado-team 正常播放，legado-E 无法播放，加载转一下就停

**关键线索**：同一份文件、同一个 `file://` 路径，**Team 版能播、E 版不能播** —— 说明**解密本身是对的**（Team 已证明），问题在**两个版本播放器的严格程度不同**。

**诊断过程**（对比解密前后的 box 结构）：

```
解密后（修复前）:
  ftyp=true moov=true mdat=true
  hev1=true mp4a=true           ← 视频轨/音频轨 fourcc 已修复
  sinf=false tenc=false         ← DRM 描述已清（sinf→free 生效）
  senc=true saiz=true saio=true ← ❌ CENC 样本加密信息残留！
```

**根因**：`senc`（Sample Encryption Box，35944+25832 字节）、`saiz`（Sample Auxiliary Information Sizes）、`saio`（Sample Auxiliary Information Offsets）是 CENC 的**样本加密索引**。

- **Team 版播放器宽容**：见到 senc 但轨道已是 hev1/mp4a，就直接播
- **E 版播放器严格**：见到 senc 就认为文件仍加密 → 拒绝播放 → 转一下就停

**修复**：解密完成后，把这三个 box 也改成 `free`（保留 box 大小与位置，只改 fourcc 并清零 payload）：

```js
// ★E版兼容：清除 CENC 样本加密信息（senc/saiz/saio）
var n4=0,n5=0,n6=0;
for (var si3=0; si3<stbls.length; si3++){
  var sp2=stbls[si3].p, ss2=stbls[si3].s;
  var kids2=RG_boxes(bytes, sp2+8, Math.min(sp2+ss2, BL));
  for (var i3=0;i3<kids2.length;i3++){
    var e3=kids2[i3];
    if (e3.t==='senc'||e3.t==='saiz'||e3.t==='saio'){
      if (e3.t==='senc') n4++; else if (e3.t==='saiz') n5++; else n6++;
      bytes[e3.p+4]=0x66; bytes[e3.p+5]=0x72; bytes[e3.p+6]=0x65; bytes[e3.p+7]=0x65;  // 'free'
      for (var j3=e3.p+8;j3<Math.min(e3.p+e3.s,BL);j3++) bytes[j3]=0;
    }
  }
}
return {samples:total, encv:n1, enca:n2, sinf:n3, bv2c:hasBv2C, senc:n4, saiz:n5, saio:n6};
```

**修复后结构**（干净的无 CENC 标记 MP4）：
```
senc=false saiz=false saio=false schm=false
hev1=true  mp4a=true
sinf=false tenc=false
```

★ **通用教训**：**CENC 解密要清除的 box 是"一组"，不是"一个"**。完整清单：

| box | 作用 | 处理 |
|---|---|---|
| `encv` / `enca` | 加密的视频/音频轨道入口 | 改 fourcc → `hev1` / `mp4a` |
| `sinf` | DRM 描述（含 tenc） | 改 fourcc → `free` 并清零 |
| `tenc` | 加密模板（默认 IV/KeyID） | 随 sinf 一起清除 |
| **`senc`** | **样本加密索引（IV 列表）** | **改 fourcc → `free` 并清零** |
| **`saiz`** | **辅助信息大小** | **改 fourcc → `free` 并清零** |
| **`saio`** | **辅助信息偏移** | **改 fourcc → `free` 并清零** |
| `schm` | Scheme 类型标记 | 一并清除 |

★ **"一个版本能播、另一个不能"是最有价值的诊断信号** —— 它直接排除了"文件损坏/解密错误"，把范围缩小到"播放器的严格程度差异"。此时应该去对比两个版本的播放器行为差异，而不是反复检查解密逻辑。

★ **排查手法**：把解密后的文件 dump 出来，**grep 所有加密相关 fourcc**，逐个确认是否清除。不要只查 `encv`/`sinf` —— `senc`/`saiz`/`saio` 同样会让严格播放器拒绝。


### 4.5.10 ★★★ 四次报障：E 版看不了 → 硬编码包名路径（2026-10-13 深夜）

**用户报障**：
> legado-E 版还是看不了，加载一下就停（但 legado-team 正常播放）

**排查过程（走了弯路，价值最高）**：

1. **先怀疑文件结构** → dump 出来对比，发现 `mp4a=false` → 以为是音频轨没修复
2. **再怀疑 CENC 残留** → 发现 `senc/saiz/saio=true` → 加了清除逻辑（v5）
3. **仍然失败** → 对比两版播放器源码，发现 `Exo2MediaPlayer` **完全相同**（连 GSY 版本差异都不是直接原因）
4. **★ 最终发现**：debug 输出 `file:///5afbb59d8f78322a.mp4` —— **路径里没有目录前缀**！

**根因**：`ruleContent` 里**硬编码了 Team 版的包名路径**：
```js
// ❌ 错误：硬编码
return 'file:///storage/emulated/0/Android/data/com.legado.app.release/cache' + path;
//                                                        ^^^^^^^^^^^^^^^^^^^^^^^^ Team 版包名
```

- **Team 版**（包名 `com.legado.app.release`）→ 路径正确 → 能播
- **E 版**（包名 `io.legado.app`）→ 路径指向**另一个 App 的私有目录** → 读不到 → "加载一下就停"

★ **这是最隐蔽的一类 bug**：在自己手机上完全正常（因为包名恰好匹配），换个版本/包名就挂。

**解法：动态探测缓存目录**（内联在规则顶部，不要放 jsLib）：

```js
// ★ 内联在 ruleContent 的 IIFE 开头（规则上下文）
var FVCD='';
try{ java.readFile('/'); }catch(e0){
  var mm=String(e0).match(/([/]storage[/]emulated[/]0[/]Android[/]data[/][^/]+[/]cache)/);
  if(mm) FVCD=mm[1];
  if(!FVCD){
    var m2=String(e0).match(/([/]data[/]data[/][^/]+[/]cache)/);
    if(m2) FVCD=m2[1];
  }
}
if(!FVCD) FVCD='/storage/emulated/0/Android/data/com.legado.app.release/cache';  // 兜底

// 使用
return 'file://' + FVCD + path;
```

**原理**：`java.readFile('/')` 会抛 `FileNotFoundException`，异常消息里带**完整的绝对路径**：
```
JavaException: java.io.FileNotFoundException: /storage/emulated/0/Android/data/com.legado.app.release/cache: open failed: EISDIR
```
→ 正则提取 `.../cache` 前缀 → 自动适配任何包名。

★★★ **踩坑：jsLib 作用域 vs 规则作用域的 `java` 不同**（本轮第 N 次）

最初把 `FV_cacheDir()` 放进 jsLib，规则里调 `FV_cacheDir(java)`：
- `eval_js` 里测试 **正常返回**
- **真实规则上下文里返回空串**

原因：**jsLib 求值在独立作用域**（`SharedJsScope`），函数内访问的 `java` 与规则上下文的 `java` 不是同一个对象。即使显式传参，某些版本的绑定仍有差异。

→ **最终解法：内联到规则顶部**，直接用规则自己的 `java`。实测两版都返回正确路径：
```
Team 版 → /storage/emulated/0/Android/data/com.legado.app.release/cache
E   版 → /storage/emulated/0/Android/data/io.legado.app/cache
```

### 4.5.11 零反斜杠正则写法（本轮踩坑）

正则里的 `\/` 会被构建闸门的"零反斜杠"检查拦下，改用**字符组**：
```js
// ❌ 有反斜杠
/\/storage\/emulated\/0\/Android\/data\/[^\/]+\/cache/
// ✅ 零反斜杠
/[/]storage[/]emulated[/]0[/]Android[/]data[/][^/]+[/]cache/
```
实测 Rhino 完全支持这种写法。

### 4.5.12 跨版本兼容检查清单（补充）

| 检查项 | 方法 | 通过标准 |
|---|---|---|
| **零硬编码路径** | `grep "com.legado" ruleContent` | 0 处（含 `/storage/emulated`、`/data/data`） |
| **零硬编码包名** | 全文搜 `com.legado.app` | 只允许出现在**兜底默认值**里 |
| **动态探测可用** | debug_source 看正文输出 | `file:///真实缓存路径/xxx.mp4` |
| **两版路径不同** | Team / E 分别跑 | 各自探测到自己的包名路径 |

### 4.5.6 E 版兼容检查清单

| 检查项 | 方法 | 通过标准 |
|---|---|---|
| 顶层第三方类引用 | `grep "^var .*= Packages\."` | 只剩 java/javax/android |
| hutool 残留 | `grep -c "hutool"` | 只在 try 块内（有 catch 兜底） |
| bouncycastle 残留 | `grep -c "bouncycastle"` | 0（SM3 用纯 JS） |
| hex 转换性能 | 4MB 往返计时 | < 1s |
| Base64 降级 | 屏蔽 android.util.Base64 后测试 | 走 java.util.Base64 或纯 JS |
| 端到端 | 模拟屏蔽后跑完整链路 | 全绿 |
| **JS 语法闸门** | 每个 JS 块单独 `node --check` | 全部通过 |
| **导入后回读** | `source.getContentRule()` 检查 | 无损坏字符 |


---

## 5. 三条铁律（可复用到其它 App 接口书源）

1. **发现接口返回"服务端推荐池"（随机流）时，翻页不可靠** —— 用 `next_offset` 返回的游标，不要自己 `page*N` 推算。若两次相同请求结果不同（重叠 <50%），说明是随机推荐流，只能当"更多"入口用。
2. **同站不同 aid 的编码/加密策略可能完全不同** —— 低档位全不可播时，先横向试 aid、host、channel 组合，别急着下"站点不支持"的结论。
3. **加密算法的返回类型是契约的一部分** —— Array 与 Uint8Array 在 Rhino 里看似通用，实则会在下游静默失败。移植时逐函数核对类型。

---

## 6. 验收清单

| 项 | 结果 |
|---|---|
| check_source | ✅ 通过 1/1 |
| 搜索（都市/万妖/重生） | ✅ 3条/3条/3条 |
| 发现页（漫剧/找剧/动漫） | ✅ 9/6/12 条，翻页零重叠 |
| 详情 | ✅ 140集/81集/1000集 |
| 目录 | ✅ 全量内联 |
| 正文（CENC解密+写文件） | ✅ 2.7MB MP4，moov/hev1/mp4a 齐全、encv/sinf 已清 |
| 画质切换（360/480/540/720） | ✅ 登录界面按钮，实测生效 |
| 连通检查按钮 | ✅ 输出签名耗时 + 当前画质 |
| 缓存清理按钮 | ✅ |
| E 版兼容 | ✅ 零 hutool/零 bouncycastle/零 awt（hex 用 BigInteger，4MB 487ms）|

---

## 7. 站点档案速查

```
发现-漫剧   tab_type=32（9条/页）
发现-找剧   tab_type=8（6条/页）
发现-动漫   tab_type=24（12条/页）
搜索        /reading/bookapi/search/suggest/v（固定10条，含视频）
详情/目录   POST /novel/player/multi_video_detail/v1/
播放        POST api3/novel/player/video_model/v1/（aid=1967）
签名        X-Argus(SIMON-128+protobuf) / X-Ladon / X-Gorgon / X-Khronos
UA          发现/详情: com.phoenix.read/72932；播放: com.dragon.read
风控        无搜索限频（suggest 接口连续调用正常）；游客可看全集
```
