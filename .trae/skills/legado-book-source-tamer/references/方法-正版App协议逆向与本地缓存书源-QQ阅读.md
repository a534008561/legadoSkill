# 方法：正版 App 协议逆向 + 本地缓存型书源
## ——QQ阅读(纯本地) 拆解：当站点是「加密 API + 密钥池 + 二进制容器」时，规则该怎么写

> 沉淀日期：2026-10-08　｜　蓝本：`QQ阅读(纯本地)`（`https://book.qq.com`，jsLib 396KB / loginUrl 76KB / 全 @js 规则）
> 关联：[方法-抓包驱动的官方App行为对齐-STV篇](方法-抓包驱动的官方App行为对齐-STV篇.md)、[方法-App官方API书源与设备号风控-次元姬](方法-App官方API书源与设备号风控-次元姬.md)、[方法-多层密钥AES与轮换签名逆向](方法-多层密钥AES与轮换签名逆向.md)、[方法-视频书源完全指南](方法-视频书源完全指南.md)

---

## 目录

0. [一句话总结](#零一句话总结)
1. [适用识别：什么站值得走这条路](#一适用识别什么站值得走这条路)
2. [架构总览：四层结构](#二架构总览四层结构)
3. [★hex 传输通道：官方 `{"type":"hex"}` 选项](#三hex-传输通道官方-typehex-选项)
4. [请求侧：设备指纹表 + 字段拼签](#四请求侧设备指纹表--字段拼签)
5. [★响应侧：QQFock 密钥池 + 双实现解密](#五响应侧qqfock-密钥池--双实现解密)
6. [容器格式：tar + CSV 双结构](#六容器格式tar--csv-双结构)
7. [★本地缓存体系：把「在线源」改造成「离线可读」](#七本地缓存体系把在线源改造成离线可读)
8. [登录体系：ptlogin 短信/扫码 + Cookie 自管](#八登录体系ptlogin-短信扫码--cookie-自管)
9. [段评注入：正文段落级气泡 + useweb 面板](#九段评注入正文段落级气泡--useweb-面板)
10. [自动购买：订单前置校验与冷却](#十自动购买订单前置校验与冷却)
11. [工程纪律：K1~K22 避坑清单](#十一工程纪律k1k22-避坑清单)
12. [移植清单：换一个站要改什么](#十二移植清单换一个站要改什么)
13. [验证方法论](#十三验证方法论)

---

## 零、一句话总结

**当站点把正文封进「自定义二进制容器 + 响应加密 + 密钥池」时，不要试图用 CSS/JSONPath 去解析——把整套密码学搬进 jsLib，让规则退化成「发请求 → 拿 hex → 喂给解密函数」的两行代码。**

这套书源的全部精华可以概括成三句话：

1. **传输层**：用官方 `{"type":"hex"}` URL 选项把二进制响应以 hex 字符串拿进规则；
2. **解密层**：jsLib 里自实现 SHA256/AES/DES/CRC32/Inflate + 自定义信封，双实现（Rhino JS + Java 原生）互相兜底；
3. **缓存层**：解密结果落 `source.put()` 变量，实现「预缓存全本、断网可读」——这才是「纯本地」的真实含义。

---

## 一、适用识别：什么站值得走这条路

不是所有站都值得这么干。出现以下**三个及以上**特征时，才考虑「协议逆向 + 本地缓存」路线：

| 特征 | 观察点 |
|---|---|
| **有官方 App 且内容只在 App 里全** | 网页版阉割（试读/水印/少章节），App 版才是完整体 |
| **响应不是明文** | 抓包看到 hex/base64/二进制流，或响应头有 `content-encoding` 之外的自定义标记 |
| **接口带签名头** | 请求头里有 `csigs`/`sign`/`token` 之类每次变化的字段 |
| **正文按「包」下发** | 一次请求返回**多章**（批量接口），或返回 tar/zip 容器 |
| **有购买/订阅体系** | 章节有 `price`/`unlock`/`ticket` 字段，需要判断「已购/未购」 |
| **站点允许预下载** | App 有「缓存全本」功能 ⇒ 说明服务端支持批量拉取，书源也能蹭 |

QQ阅读全中。反例：如果站点只是简单的「HTML 页面 + CSS 选择器」，用常规规则 30 分钟就能搞定，**不要**上这套。

**成本预估**：这套方案的 jsLib 是 396KB、loginUrl 76KB，光是搞清楚结构就要通读几万行。所以先问一句：**这个站的独占内容值不值这个成本？** 值，才继续。

---

## 二、架构总览：四层结构

```
┌─ 规则层（ruleSearch / ruleBookInfo / ruleToc / ruleContent）────────────┐
│   全是 @js:，单条规则 5~80 行，职责 = 编排 + 异常兜底                    │
│   例：content 规则只做「解析URL → 查缓存 → 未命中则请求 → 解密 → 返回」 │
├─ 工具层（jsLib 396KB）───────────────────────────────────────────────┤
│   ├─ QQIbex  ：登录指纹专用（MD5/MD4/SHA/AES/DES + 自定义信封 nibLk）  │
│   ├─ QQFock  ：响应解密专用（SHA256/AES-CTR+CBC/Inflate + 密钥池）     │
│   ├─ QF 配置 ：GATEWAY / FUID / SIGN_SALT / 字段表 / 屏蔽词            │
│   └─ qf* 工具：URL 构造、缓存读写、目录解析、包探测、退避重试           │
├─ 面板层（loginUrl 76KB / loginUi 7KB）───────────────────────────────┤
│   短信登录 / 扫码登录 / 预缓存 / 自动购买 / 段评设置 / 净化设置 六个子页 │
└─ 数据层（source.put / book.putVariable / chapter.putVariable）───────┘
    缓存正文、密钥池、设备模板、开关配置、书籍类型标记
```

**关键设计思想：规则层只做编排，重活全在 jsLib。**

这条原则带来的直接好处：改一个算法只需要动 jsLib 一处；规则层保持短小，出问题时排查面收窄到「编排逻辑」和「算法实现」两个独立维度。

---

## 三、★hex 传输通道：官方 `{"type":"hex"}` 选项

这是整套方案的地基，也是**官方原生支持**的（很多写源的人不知道）。

### 3.1 源码实锤

`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt:461`：

```kotlin
suspend fun getStrResponseAwait(...): StrResponse {
    if (type != null) {
        return StrResponse(url, HexUtil.encodeHexStr(getByteArrayAwait()))
    }
    ...
}
```

`type` 来自 URL 选项 JSON 的 `type` 字段（`:280  type = option.getType()`，`:919  type = if (value.isNullOrBlank()) null else value`）。

**语义**：URL 尾部附 `,{"type":"hex"}` ⇒ 拿到的响应体是**原始字节的 hex 编码字符串**（小写、无分隔）。

### 3.2 用法

```javascript
// jsLib 里统一封装
function qfHexOption() { return ',{"type":"hex"}'; }

// 目录 URL（注意 hex 选项必须拼在最后）
function qfTocUrl(bid, rtype) {
    var u = QF.GATEWAY + '/ChapBatAuthWithPD?bookId=' + encodeURIComponent(bid)
        + '&type=0&tafauth=1&useindex=1&scids=0';
    if (rtype === '4') u += '&restype=' + rtype;
    return u + qfHexOption();      // ← 追加 ,{"type":"hex"}
}
```

### 3.3 拿到 hex 之后

规则里 `result` 就是 hex 字符串，需要先转成「每字符一字节」的 latin1 串才能解析 tar：

```javascript
// 有 Java 原生就用原生（快 10 倍以上）
function qfJavaHexToLatin1(hex) {
    if (!hex || !qfJv) return null;
    try {
        var b = qfJv.hexDecodeToByteArray(hex);      // java.hexDecodeToByteArray
        if (!b) return null;
        var s = String(qfJv.bytesToStr(b, 'ISO-8859-1'));   // java.bytesToStr(b, charset)
        if (s.length !== (hex.length >> 1)) return null;    // 长度自校验
        return s;
    } catch (e) { return null; }
}

// 纯 JS 兜底（分块避免 apply 参数上限）
function qfHexToLatin1JS(h) {
    var n = h.length >> 1, out = [], buf = [], i, c, hi, lo;
    for (i = 0; i < n; i++) {
        c = h.charCodeAt(i << 1);
        hi = c < 58 ? c - 48 : (c < 71 ? c - 55 : c - 87);
        c = h.charCodeAt((i << 1) + 1);
        lo = c < 58 ? c - 48 : (c < 71 ? c - 55 : c - 87);
        buf.push((hi << 4) | lo);
        if (buf.length >= 8192) { out.push(String.fromCharCode.apply(null, buf)); buf.length = 0; }
    }
    if (buf.length) out.push(String.fromCharCode.apply(null, buf));
    return out.join('');
}
```

### 3.4 ★三条硬约束

1. **hex 选项必须拼在 URL 末尾**，且与 URL 之间是**英文逗号**，不是 `?`/`&`。
2. **同一个 URL 不能既带 hex 又指望拿到文本**——`type != null` 时整条响应走 hex 分支，页面类接口别用。
3. **hex 字符串长度恒为字节数 × 2**；做 `s.length === hex.length >> 1` 自校验能第一时间发现「服务端返回了错误页（HTML 也是字节）」这种情况。

---

## 四、请求侧：设备指纹表 + 字段拼签

### 4.1 设备指纹表（43 字段）

`QQFockDevice.DEVICE` 是一张完整的「App 身份表」，每一条都参与服务端校验：

```javascript
var DEVICE = {
    'User-Agent': "okhttp/3.12.13",
    'c_platform': "android",
    'c_version': "qqreader_8.5.5.0888_android",
    'channel': "10001000",
    'qrsn': "1748c421a112b58c39172e1f10001ec1a905",
    'qrsn_new': "1748c421a112b58c39172e1f10001ec1a905",
    'mldt': "d116f07b39912247ac6f8612d82b2e3a...76e5b2d90e2fa859",  // 设备长指纹
    'sift': "216e4e6309534376721852f5dabf91fa...76e5b2d90e2fa859",  // 另一长指纹
    'ssign': "698c3369822efe4997b3dcc1f3946794",
    'ibex': "9hT7x1YEg2osIctJSRC6bhHeQeSLjI7m...",                  // 登录指纹密文
    'safekey': "3C63C1ED3C26E6A0C9751FD2417B5550",
    'trustedid': "F99DE4D28B4DB6ACC743436CD0CFD7191",
    'ywtoken': "EC84F622E98137328267BC357FBCBABC",
    // …共 43 项
};
```

**注意 `mldt` 与 `sift` 的尾部**：两者都以 `76e5b2d90e2fa859`（= `dn` 字段）结尾，说明服务端做**交叉一致性校验**——不能单独改其中一个。

### 4.2 字段拼签（csigs）

```javascript
var QF = {
    GATEWAY: 'https://newminerva-tgw.reader.qq.com',
    FUID: '80f2357fed274773914d98ef925e78d5',
    SIGN_SALT: 'B74H5a2Yh73gfu8F',
    SIGN_FIELDS: ['loginType', 'ywguid', 'ywkey', 'c_version', 'c_platform', 'channel',
        'qrsn', 'qrsn_new', 'gselect', 'server_sex', 'rcmd', 'youngerMode', 'ttime']
};

function qfSign(hd) {
    var out = {}, k;
    for (k in hd) { if (hd.hasOwnProperty(k)) out[k] = hd[k]; }
    out['ttime'] = String(new Date().getTime());          // ← 时间戳
    var sb = '';
    for (var i = 0; i < QF.SIGN_FIELDS.length; i++) sb += qfVal(out, QF.SIGN_FIELDS[i]) + '|';
    sb += QF.SIGN_SALT;
    var x = QQFock.bToHex(QQFock.sha256(QQFock.bFromStr(sb)));
    out['csigs'] = QQBCrypt.hash(QQFock.bFromStr(x), 4);   // ← 二次哈希
    return out;
}
```

**三个设计细节值得抄**：

1. **字段名大小写不敏感查找**（`qfVal`）：先精确匹配，失败则遍历小写比对——兼容服务端/客户端字段名大小写漂移；
2. **缺字段不报错，补空串**（`qfVal` 返回 `''`）：签名字段表可以在不破坏签名的前提下增删；
3. **签名结果带 TTL 缓存**：`qfHeaderJson` 缓存 20 秒（可配 `bs_sign_ttl`，上限 600 秒），避免同一次操作里多次重算 SHA256+BCrypt。

```javascript
var qfHdrCache = '', qfHdrCacheAt = 0, qfHdrCacheCk = '';
function qfHeaderJson(src, ck) {
    var now = new Date().getTime();
    var ttl = qfSignTtl(src);
    if (ttl > 0 && qfHdrCache && qfHdrCacheCk === ck && (now - qfHdrCacheAt) < ttl) return qfHdrCache;
    var js = JSON.stringify(qfSign(qfHeaders(ck)));
    qfHdrCache = js; qfHdrCacheAt = now; qfHdrCacheCk = ck;
    return js;
}
```

### 4.3 header 规则：自管 Cookie + 主动清除登录头

```javascript
// ruleSearch.header 等所有 header 字段
(function(){
  try { source.removeLoginHeader(); } catch(e) {}   // ★ 清掉 Legado 自动附加的登录头
  var ck = '';
  try { ck = String(source.get('bs_cookie') || ''); } catch(e) {}
  return qfHeaderJson(source, ck);
})()
```

**为什么必须 `removeLoginHeader()`**：Legado 会把 `loginHeader`（登录成功后 `putLoginHeader` 写入的）自动附加到**同域请求**。本源自己管理 `bs_cookie` 变量并在 `qfHeaders` 里解析 `ywkey`/`ywguid`，如果两套头同时存在，会出现「旧登录头 + 新签名头」混用 → 服务端判定会话不一致。

**这是「自管鉴权」型书源的标准姿势**：宁可完全不用 Legado 的登录头机制，也不要两套并存。

---

## 五、★响应侧：QQFock 密钥池 + 双实现解密

这是全源技术含量最高的部分。

### 5.1 加解密总流程

```
① 取密钥池   GET /sk?fuid={FUID}&type=1        → {"code":"0","pool":"<base64>"}
                ↓ pool bytes
② 解池       unwrapPool(pool, fuidHex)
                = CBC-Decrypt( key=tdExpand(hm), iv=hm[:16], pool )
                → "id1,id2,id3\r..."（keyId 候选列表）
                ↓
③ 读章节密文  GET /ChapBatAuthWithPD?...&scids=N ,{"type":"hex"}
                → hex → latin1 串 ct（≥256 字节）
                ↓
④ 拆头部     hdr = CBC-Decrypt( key=tdExpand(hm), iv=hm[:16], ct[:256] )
                hdr[0x00:0x80] = 指纹数字串（fp，用于校验密钥池是否漂移）
                hdr[0x80:0x100] = payload（前 128 字节正文头）
                ↓
⑤ 拼载荷     buf = hdr[0x80:0x100] + ct[256:]
                ↓
⑥ 逐 keyId 试解
                KA  = sha256(keyId + fuidHex + addKey)      ← contentKey
                stg = ksXor(KA, buf)                        ← 自定义流加密
                pt  = CBC-Decrypt( key=tdExpand(KA), iv=KA[:16], stg )
                ↓ 校验 gzip 魔数 1f 8b 08
⑦ 解压       gunzip(pt) → UTF-8 文本
```

其中 `hm = sha256(fuidHex + L_HDR)`，`L_HDR = 'KNVA76RTD8YZXZ6Z'`。

### 5.2 ★双实现：原生 Java 优先，JS 兜底

```javascript
function natCtx() {
    if (_nat !== undefined) return _nat;
    _nat = null;
    try {
        if (typeof Packages === 'undefined' || Packages === null) return _nat;
        _nat = {
            C: Packages.javax.crypto.Cipher,
            K: Packages.javax.crypto.spec.SecretKeySpec,
            V: Packages.javax.crypto.spec.IvParameterSpec,
            M: Packages.java.security.MessageDigest,
            S: Packages.java.lang.String,
            A: Packages.java.util.Arrays,
            BO: Packages.java.io.ByteArrayOutputStream,
            IZS: Packages.java.util.zip.InflaterInputStream
        };
        _nat.md = _nat.M.getInstance('SHA-256');
        _nat.C.getInstance('AES/CBC/NoPadding');      // ← 探测即验证可用性
        _nat.C.getInstance('AES/CTR/NoPadding');
    } catch (e) { _nat = null; }                      // ← 探测失败则整体降级
    return _nat;
}
```

**为什么要双实现**：

| | 原生 Java | 纯 JS |
|---|---|---|
| 速度 | 单章解密 **~1.7ms** | 单章 **数十~数百 ms** |
| 依赖 | 需要 `javax.crypto`（部分定制 App 阉割） | 无依赖，纯 Rhino |
| 用途 | 快路径 | 快路径抛异常时兜底 |

**探测即验证**（`getInstance` 写在 try 里）：只有在真能拿到 Cipher 实例时才算可用，比 `typeof Packages.javax.crypto.Cipher` 更可靠（部分环境类存在但 provider 缺失）。

### 5.3 ★指纹校验：防密钥池漂移污染

```javascript
var fp = peekIdStr(ct, QF.FUID);              // 从密文头部读指纹
if (goodFp && fp && fp !== goodFp) {
    return { ok: false, bad: true, fp: fp };  // ← 明确标记「不是本章的包」
}
```

**这个机制解决的问题**：密钥池有多个 keyId，服务端可能轮换。当某次请求拿到的密文其实是**另一个 keyId 加密的**时，暴力试解会失败；但更危险的情况是——**误用错误密钥解出了「看起来像文本」的垃圾**，然后被写进缓存。

**双保险设计**：
1. `peekId` 先读指纹，与「上次成功的指纹」比对，不一致直接拒绝（不进入试解循环）；
2. 试解循环里**必须**通过 gzip 魔数校验（`1f 8b 08` + `(pt[3] & 0xe0) === 0`）才接受结果。

```javascript
// 只有真解出来了才更新「好指纹」
if (r.ok) { if (fp) qfFpSet(fp); }
else if (!r.bad && qfFpKnown && fp && fp === qfGoodFp) {
    qfFpSet('');      // 原本的好指纹这次失败了 ⇒ 清掉，避免后续全部被拒
}
```

### 5.4 ★「拒绝包」处理：绝不返回文本

服务端会用 tar 包里的 `info.txt` 表达「这一章不给你」：

```javascript
function qfPkgInfo(mem) {
    var raw = mem['info.txt'];
    var arr = JSON.parse(qfLatin1ToUtf8(raw));    // [{"code":"-1","message":"..."}]
    // code=0 → ok；code 负数 → neg（被拒）
}
function qfPkgDenied(pi) {
    if (!pi || !pi.n) return 0;
    if (pi.ok) return 0;         // 有成功条目就不算拒绝
    if (!pi.neg) return 0;
    return 1;
}
```

处理策略（写在 `ruleContent` 里）：

```javascript
if (isDeny || pkg.bad || !pkg.n) {
    denyTries++;
    var dmax = qfDenyTries(source);
    if (denyTries < dmax && (a + 1) < tries) { continue; }   // 还有次数就重试
    if (isDeny) {
        throw new Error('服务端拒绝这一章（code=' + pkg.code + ... + '）...');
    }
    throw new Error('服务端没给这一章的内容...');
}
```

**核心纪律：宁可不返回，绝不返回可能被污染的文本。** 一旦把「服务端拒绝提示」当成正文存进缓存，用户下次打开这本书看到的就是这段提示，而且**不会自愈**（因为缓存命中了）。

### 5.5 自定义信封 nibLk（登录指纹专用）

`QQIbex` 里另有一套自研信封，用于**登录指纹串**（61 字段 `|` 分隔）的加解密：

```javascript
function nibLk(inp) {                      // 加密
    if (!inp.length || inp[0] === 0) return null;
    var h = crc32(inp);
    var h1;
    switch (h % 3) {                       // ① 哈希算法三选一（由 crc32 决定）
        case 0: h1 = hashVariant1(inp); break;    // 自定义哈希
        case 1: h1 = md4(inp); break;
        default: h1 = md5(inp); break;
    }
    var j = Math.floor(h / 256) % 3;       // ② 链式派生三选一
    var d2, d3;
    if (j === 0) { d2 = hashVariant1(h1); d3 = hashVariant1(d2); }
    else if (j === 1) { d2 = md4(h1); d3 = md4(d2); }
    else { d2 = md5(h1); d3 = md5(d2); }

    var seed = [];                          // ③ 种子 = d3 的 hex 字符 ASCII
    for (var i = 0; i < d3.length; i++) {
        var s = hex2(d3[i]);
        seed.push(s.charCodeAt(0), s.charCodeAt(1));
    }
    var h2 = crc32(seed);
    // ④ 双层加密，每层算法由 h2 的位决定
    var c1 = (h2 & 1) === 0 ? cipherAes256(inp, seed) : cipherDes(inp, seed);
    var body = (Math.floor(h2 / 16) & 1) === 0 ? cipherAes256(c1, seed) : cipherDes(c1, seed);
    return body.concat(seed);               // ⑤ 种子后置
}
```

**设计要点**：
- **算法选择器由内容哈希驱动**：同一份代码对不同输入走不同路径（AES 或 DES、单层或双层），逆向时必须把两条路径都实现；
- **种子后置且明文**：解密时从末尾取 32 字节当种子，无需额外传输；
- **`inp[0] === 0` 直接返回 null**：空输入保护（避免全零密文被误解）。

**为什么值得单独抄**：这是「**白盒化的自定义加密**」——没有用标准 CryptoJS，而是把 MD5/MD4/自定义哈希全自己实现了一遍。遇到这类站，**不要试图找「是不是某个标准算法的变体」**，直接把 JS 原样搬进 jsLib 是最省事、最不容易出错的路。

### 5.6 自定义流加密 keystream + ksXor

正文解密里还有一层自定义流加密（`ksInit`/`keystream`/`ksXor`），同样是自实现。要点：

```javascript
stg = ksXor(KA, buf, nblk);          // 自定义流加密
pt  = cbcDec(exp, KA.slice(0, 16), stg);   // 再走 AES-CBC
```

**顺序不能反**：先流加密再 CBC 解密（对应加密侧先 CBC 再流）。**验证方法**：拿一份能解出来的样本，两种顺序各试一遍，只有一种能通过 gzip 魔数。

---

## 六、容器格式：tar + CSV 双结构

### 6.1 tar 解析（512 字节块）

```javascript
function qfTarStr(s) {                     // s = latin1 串（每字符一字节）
    var out = {}, off = 0, i, name, sz;
    while (off + 512 <= s.length) {
        if (s.charCodeAt(off) === 0) break;              // 结束块
        name = '';
        for (i = 0; i < 100; i++) {                      // name[0:100]
            var c = s.charCodeAt(off + i);
            if (c === 0) break;
            name += String.fromCharCode(c);
        }
        var so = '';
        for (i = 124; i < 136; i++) {                    // size[124:136]，八进制 ASCII
            var c2 = s.charCodeAt(off + i);
            if (c2 === 0 || c2 === 32) break;
            so += String.fromCharCode(c2);
        }
        sz = parseInt(so, 8); if (isNaN(sz)) sz = 0;     // ★ 八进制！
        out[name] = s.substring(off + 512, off + 512 + sz);
        off += 512 + Math.ceil(sz / 512) * 512;          // 按 512 对齐
    }
    return out;
}
```

**三个易错点**：
1. **size 是八进制**（`parseInt(so, 8)`），不是十进制；
2. **数据区按 512 对齐**（`Math.ceil(sz/512)*512`），不是紧排；
3. **结束标志是首字节 0**（连续两个全零块，但检测第一个即可）。

### 6.2 目录 CSV（14 列）

```
cid, name, words, price, ?, ?, ?, uuid, ?, ?, time, unlock, ticket, cbid
 0     1     2      3     4  5  6    7     8   9   10     11      12     13
```

```javascript
out.push({
    cid: f[0], name: f[1], words: f[2],
    price: parseInt(f[3], 10) || 0,
    free: (parseInt(f[3], 10) || 0) === 0 ? 1 : 0,
    uuid: f[7], cbid: f[13] || '', time: f[10] || '',
    purchased: 0,
    unlock: parseInt(f[11], 10) || 0,      // 11 = 解锁类型（2 = 需全订）
    ticket: parseInt(f[12], 10) || 0,      // 12 = 月票张数
    bid: String(bid || '')
});
```

**过滤规则直接建在这几列上**（比按标题猜准得多）：

| 档位 | 判据 | 开关 |
|---|---|---|
| 月票章 | `ticket > 0` | `bs_toc_ticket` |
| 全订章 | `unlock === 2` | `bs_toc_full` |
| 请假章 | 免费 + 标题含「请」「假」+ 标题里没有「第…章」 | `bs_toc_leave` |
| 屏蔽词 | 标题命中词表（默认 `月票番外`） | 内置 |

**为什么用列不用标题**：标题是站点自己写的，同一本书里格式都可能不一致；而**列是协议的一部分**，服务端不会随意改。这是「结构化数据优先于文本匹配」的典型案例。

### 6.3 章节包成员命名

```
{bid}_{cid}_s          ← 密文成员（正则 ^\d+_\d+_s$）
preview.txt            ← 试读内容（明文）
info.txt               ← 拒绝/错误信息（JSON 数组）
{bookId}_ALL_o...      ← 目录 CSV（仅索引包）
```

**包类型靠成员名区分**，不靠请求参数——这是「一个接口同时服务目录和正文」时的常见设计。

---

## 七、★本地缓存体系：把「在线源」改造成「离线可读」

这是本源叫「纯本地」的原因，也是最值得复用的部分。

### 7.1 三层缓存键设计

```javascript
// ① 单章密文/文本
function qfStashKey(bid, cid) { return 'bs_ch_' + qfStr(bid) + '_' + qfStr(cid); }
//   值形态 A（密文）：{"n":"{bid}_{cid}_s", "h":"<hex>"}
//   值形态 B（文本）：{"t":"正文文本", "p":0|1}   p=1 表示这是试读

// ② 已缓存章节清单（用于增量补全）
function qfChListKey(bid) { ... }   // 'bs_chl_{bid}' → JSON 数组 [cid, cid, ...]

// ③ 密钥池
//    'bs_fock_pool' → base64 字符串
```

**设计要点**：
- **密文与文本分开存**：密文（`h`）可以在密钥池更新后重新解密，文本（`t`）是最终结果。**试读文本必须带标记 `p:1`**，否则「后来买到了全文」时无法区分。
- **章节清单单独一份**：用于「增量预缓存」——已缓存的不重复下载。

### 7.2 命中判定与降级

```javascript
var st0 = qfStashGet(source, bid, cid);
if (st0 && st0.text !== undefined) {
    if (st0.preview) {
        // 缓存里是试读 → 若已购买则丢弃重取，否则返回试读 + 说明
        var abS0 = abTry();
        if (!(abS0 && abS0.s === 'bought')) {
            if (qfNoPreview(source)) return '';        // 用户要求「试读不返回内容」
            return stText + '\n\n—— 以上为试读。原因可能是：...';
        }
        qfStashDrop(source, bid, cid);                 // ★ 丢弃过期试读
    } else {
        return stText;                                 // 完整正文，直接返回
    }
}
```

**关键：缓存不是无脑信任。** 「试读」这种半成品缓存必须能在条件变化时被识别并丢弃，否则用户买了书还只能看试读。

### 7.3 批量预缓存

```javascript
// 整本一次拉取：把 N 个 cid 拼成一个区间
function qfBatchIds(src, cid, span) {
    // 支持模板 '{c+N}'：bs_batch_list = "1,2,{c+0},{c+1},{c+2}"
    var out = tpl.replace(/\{c([+-]\d+)?\}/g, function (m, d) {
        var n = start + (d ? parseInt(d, 10) : 0);
        return n >= 1 ? String(n) : '';
    });
    ...
    return String(start) + '-' + String(start + span - 1);   // 默认区间形式 "100-107"
}
```

服务端接受 `scids=100-107` 这种**区间语法**（`qfSelArg` 里特意保留了 `%2D`→`-` 和 `%2C`→`,` 的还原）：

```javascript
function qfSelArg(v) {
    return encodeURIComponent(String(v)).replace(/%2C/g, ',').replace(/%2D/g, '-');
}
```

**批量包的处理**：

```javascript
function qfBatchTake(raw, bid, cid) {
    // 从一个大包里，挑出「本章」，其余全部落缓存
    for (k in mem) {
        mm = /^(\d+)_(\d+)_s$/.exec(k);
        if (String(mm[2]) === String(cid)) { mineName = k; mineCt = mem[k]; }   // 本章
        else if (String(mm[1]) === String(bid)) { keep.push([mm[2], k, mem[k]]); }  // 其余落缓存
    }
    for (i = 0; i < keep.length; i++) qfStashPut(bid, keep[i][0], keep[i][1], ...);
    return { name: mineName, hex: ... };   // 只解密本章，其余保持密文
}
```

**这个设计极妙**：一次请求拉 8 章，**只解密当前章**，其余 7 章存密文。用户翻到下一章时直接命中缓存（省一次网络），且密文比文本小（后续密钥更新还能重解）。

### 7.4 缓存与「离线可读」

预缓存完成后，`ruleContent` 的流程变成：

```
解析URL → 查 stash → 命中且非试读 → 直接返回（零网络）
                  ↘ 未命中 → 走网络 → 解密 → 写 stash → 返回
```

**离线时**：网络请求抛异常 → `loginCheckJs` 检测到网络错误 + 有缓存 → 用 `new StrResponse('http://localhost/', b)` 伪造响应把流程引导到正文规则 → 正文规则命中 stash → 正常返回。

```javascript
// loginCheckJs 里
var netFail = /Unable to resolve host|ConnectException|UnknownHost|timed out|.../i.test(b);
if (!netFail) return result;
var hasCache = false;
if (bid && cid) { hasCache = !!String(source.get('bs_ch_' + bid + '_' + cid) || ''); }
if (!hasCache) return result;
try {
    var SR = Packages.io.legado.app.help.http.StrResponse;
    return new SR('http://localhost/', b);      // ★ 伪造响应，让流程继续
} catch (e4) {}
return result;
```

**这是「网络失败兜底到缓存」的标准写法**：`loginCheckJs` 是响应拦截器，返回值会替换真实响应。用假 URL + 缓存内容构造 `StrResponse`，Legado 会当成正常响应继续走规则。

---

## 八、登录体系：ptlogin 短信/扫码 + Cookie 自管

### 8.1 双通道登录

```javascript
var BS_SDK   = 'https://ptlogin.yuewen.com/sdk/';
var BS_SDKV2 = 'https://ptlogin.yuewen.com/sdkv2/';

// 短信：sendphonecode → phonecodelogin
// 扫码：sdkv2/scanQRCodeLogin（轮询 scanStatus）
```

**扫码状态机**（`scanStatus`）：

| 值 | 含义 | 动作 |
|---|---|---|
| 0 | 未扫码 | 继续轮询 |
| 1 | 已扫码待确认 | 更新提示「请在 QQ 里确认」 |
| 3 | 用户取消 | 终止，提示重试 |
| 5 | 登录成功 | `d.ywKey` 落地，结束 |

**轮询要带「心跳去重」**：`bsQrLogin` 里用 `source.get(BS_QR_HB)` 读心跳（由 WebView 面板写入），连续两次相同则提前退出——避免用户关了面板还在空转 40 轮。

### 8.2 设备被限的处理

```javascript
var c = Number(j && j.code);
if (c !== 0 && (c === 3 || c === -11059)) {
    bsSay('该设备被限，换一台设备重试…');
    bsDevNew();                    // 重新生成设备指纹
    j = bsSmsSendOnce(phone, '', '', '');
}
```

**`code === 3 || code === -11059` 是「设备指纹被拉黑」的专用码**。对策 = 重新生成设备编辑项（`newDeviceEdits`）而不是换 IP。这类码要**写进规则常量**，不要靠猜。

### 8.3 登录态落地

```javascript
function bsSmsOk(d) {
    var ck = 'ywkey=' + d.ywKey + '; ywguid=' + d.ywGuid;
    bsApply(ck);                          // → source.put('bs_cookie', ck)
    try { source.put('bs_sms_sk', ''); } catch (e) {}
    try { source.put('bs_app_dev', ''); } catch (e) {}
    bsSay('登录成功: ' + d.ywGuid);
    try { java.reLoginView(); } catch (e) {}
}
function bsApply(ck) {
    bsKeep(ck);                           // 存变量
    try { source.removeLoginHeader(); } catch (e) {}   // ★ 清 Legado 登录头
}
```

**注意这里没有调用 `putLoginHeader`**。整条链路是「自己存变量 → header 规则里读变量 → 拼进签名头」。**Legado 的登录头机制被完全绕过**。

### 8.4 登录态探针

```javascript
function bsVerify() {
    var ck = bsHas();
    if (ck.indexOf('ywkey=') < 0) return '未登录';
    var url = 'https://book.qq.com/api/book/read/batchBuyPreview?bid=46077914&cid=1'
            + ',{"headers":{"Cookie":' + JSON.stringify(ck) + '}}';
    var j = JSON.parse(String(java.ajax(url) || '{}'));
    if (Number(j.code) === 0) return 'ok';
    return String(j.msg || j.code);
}
```

**探针三要素**：① 用一个**真实存在**的 bookId/cid；② 直接通过 URL 选项注入 Cookie（不依赖全局 header）；③ 以业务 `code` 判定，不看 HTTP 状态码。

---

## 九、段评注入：正文段落级气泡 + useweb 面板

### 9.1 段落偏移 → 气泡注入

```javascript
function qqcInsert(j, src, chapter, bid, cid, text) {
    var s = qqcStr(text);
    if (qqcSetting(src, QQ_CMT_REVIEW_KEY) === '0') return s;   // 开关
    var uuid = qqcUuidOf(chapter, '');          // ★ 从 chapter 变量取（目录阶段存进来的）
    var map = qqcCountMap(j, src, bid, cid, uuid);   // {段号: 评论数}
    var lines = s.split('\n');
    var out = [], pos = 0, hits = 0;
    for (var i = 0; i < lines.length; i++) {
        var n = i > 0 ? map[String(i)] : 0;
        if (n > 0) {
            out.push(raw + qqcBubble(j, src,
                qqcPayload(bid, cid, uuid, i, n, raw, pos, pos + raw.length), n) + cr);
        } else {
            out.push(raw + cr);
        }
        pos += raw.length + cr.length + 1;      // ★ 累计字符偏移（发评论时要回传）
    }
    return out.join('\n');
}
```

**三个要点**：
1. **段号从 1 开始**（第 0 行不加气泡，因为 `i > 0`）；
2. **`pos` 是累计字符偏移**，作为「段落起止位置」回传——服务端用这个定位评论锚点，算错会导致评论挂错段；
3. **`chapter.putVariable('cmtUuid', uuid)`** 在**目录阶段**存入 uuid，正文阶段取出——这是 Legado 的**章节级变量传递**通道（`chapter` 对象在目录→正文之间是同一个）。

### 9.2 气泡渲染：内联 SVG + 三种形态

```javascript
QQP_BUBBLE_PRESETS = {"1000017": {"name": "墨圈（灰色）", "svg": "<svg ...>"}, ...}
QQP_BUBBLE_BY_NAME = {"墨圈（灰色）": "1000017", "QD原生风格": "1000659", ...}
```

气泡是**内联 SVG**（不是图片），通过 `imageStyle: 'DEFAULT'` 让阅读器渲染。

**两种渲染模式**（用户可切）：
- `text` 模式：内联图，留白窄；
- `para` 模式：段评位，留白宽。

### 9.3 面板：`java.showBrowser` 四参

```javascript
j.showBrowser('', html, script, qqpShowCfgOf(this.source));
//   ↑url  ↑页面  ↑注入脚本  ↑配置对象
```

**这是 useweb 之外的另一条「弹面板」通道**：`showBrowser(url, html, script, cfg)` 可以只给 html+script（url 传空串），用于渲染自定义面板。

---

## 十、自动购买：订单前置校验与冷却

### 10.1 三段式 API

```
① 查已购    GET  https://androidtgw.reader.qq.com/v7_6_6/queryChapterLoad?bid={bid}
                  → {"cids":"1-50,55,60-70"}     ← 区间语法！
② 报价      GET  https://book.qq.com/api/book/read/batchBuyPreview?bid=&cid=
③ 下单      POST https://book.qq.com/api/book/read/batchBuy
```

### 10.2 区间解析

```javascript
function qfBoughtSet(cids) {
    // "1-50,55,60-70" → {1:1, 2:1, ..., 50:1, 55:1, 60:1, ...}
    var dash = p.indexOf('-');
    if (dash > 0) {
        a = parseInt(p.substring(0, dash), 10);
        b = parseInt(p.substring(dash + 1), 10);
        if (!(a >= 1) || !(b >= a) || b - a > 50000) continue;   // ★ 护栏
        for (n = a; n <= b; n++) o[n] = 1;
    } else {
        n = parseInt(p, 10);
        if (n >= 1) o[n] = 1;
    }
}
```

**`b - a > 50000` 是必须的护栏**：服务端若返回 `1-999999999`（异常数据），不加护栏会直接把 Rhino 内存打爆。

### 10.3 冷却与按书独立

```javascript
QF_AB_COOL_SOFT = 1800000;    // 30 分钟（软冷却）
QF_AB_COOL_HARD = 21600000;   // 6 小时（硬冷却，连续失败后）
QF_AB_OWN_TTL   = 600000;     // 已购列表缓存 10 分钟
QF_AB_OWN_FRESH = 60000;      // 刚买过的书 60 秒内不重查
QF_AB_LIST_KEY  = 'bs_ab_list';   // 已开启自动购买的书号列表
```

**「按书独立」是关键设计**：`bs_ab_list` 存书号数组，只有明确开启过的书才自动下单，其它书一概不动。**这是防止误扣费的底线**——自动购买功能如果不做范围限制，用户换个书就可能被扣币。

### 10.4 批量购买的「买得起多少买多少」

```javascript
// 从当前章往后数 N 章：已购/免费章不重复扣费，余额不够只买到买得起的章
// 全订解锁章、月票解锁章会停下（不买）
```

**这个「停下」逻辑很重要**：全订/月票章不是「花钱就能买」，硬买会失败并可能触发风控。规则里显式跳过它们，比事后报错体验好得多。

---

## 十一、工程纪律：K1~K22 避坑清单

| # | 坑 | 对策 |
|---|---|---|
| K1 | `{"type":"hex"}` 拼错位置（用 `&type=hex`） | 必须是 URL 末尾的 `,{"type":"hex"}`，逗号分隔 |
| K2 | 拿 hex 当文本直接 JSON.parse | hex 是**字节的 hex 编码**，必须先转 latin1 串 |
| K3 | `String.fromCharCode.apply(null, 大数组)` 爆栈 | 分块（8192/块），见 `qfHexToLatin1JS` |
| K4 | tar size 字段当十进制解析 | tar 头是**八进制**（`parseInt(so, 8)`） |
| K5 | tar 数据区当紧排 | 按 512 字节对齐（`Math.ceil(sz/512)*512`） |
| K6 | 只实现一种加密路径（AES 或 DES） | `nibLk` 的算法选择由内容哈希驱动，**两条路径都要实现** |
| K7 | 解密失败返回原文/空串 | 必须**抛错**或返回明确的错误结构，**绝不返回可疑文本** |
| K8 | 不校验 gzip 魔数就接受解密结果 | `1f 8b 08` + `(pt[3]&0xe0)===0` 是唯一的「解对了」证据 |
| K9 | 密钥池漂移时继续用旧 keyId | 用密文头部的**指纹**（`peekId`）做交叉校验 |
| K10 | 试读文本写进缓存后当完整正文 | 缓存结构里带 `p:1` 标记，购买成功后**主动丢弃** |
| K11 | 服务端拒绝包（`info.txt` code 负数）被当正文 | 识别后**抛错**，绝不落缓存 |
| K12 | 把「服务端拒绝」当成「网络失败」反复重试 | 区分 `deny`（有明确 code）与 `bad`（格式错），前者按 `dmax` 限次 |
| K13 | 重试不退避，把风控打醒 | `qfNap(180*a)` 递增退避，上限 2000ms |
| K14 | 用户取消（Cancel/Interrupt）被当成失败重试 | `qfIsCancel(e)` 检测后**直接抛出**，不重试 |
| K15 | 同时用 Legado 登录头 + 自管 Cookie | `removeLoginHeader()` 主动清除，只留一套 |
| K16 | 设备被限（code=3/-11059）时换 IP | 应**重新生成设备指纹**（`bsDevNew`） |
| K17 | 扫码轮询不看「用户已关面板」 | 心跳去重（连续两次相同即退出） |
| K18 | 区间解析无护栏，`1-999999999` 打爆内存 | `b - a > 50000` 直接跳过 |
| K19 | 自动购买无范围限制 | `bs_ab_list` 白名单，只对开启过的书生效 |
| K20 | 全订/月票章自动下单 | 显式跳过（`unlock===2` / `ticket>0`） |
| K21 | 大数组遍历用 `for...in` 后当数组用 | `for...in` 拿到的是**字符串键**，比较前统一 `String()` |
| K22 | 原生 API 探测用 `typeof` 判断存在性 | 用**调用一次**（`Cipher.getInstance`）判断可用性，类存在 ≠ provider 可用 |

---

## 十二、移植清单：换一个站要改什么

把这套架构搬到另一个「正版 App 协议站」时，按这个顺序改：

### 必改（不做则跑不通）

| 位置 | 内容 |
|---|---|
| `QF.GATEWAY` | 该站网关域名 |
| `QF.FUID` | 该站的「用户标识」（很多站是固定值或从登录响应取） |
| `QF.SIGN_SALT` | 签名盐 |
| `QF.SIGN_FIELDS` | 参与签名的字段列表（从抓包请求头里对出来） |
| `QQFockDevice.DEVICE` | 设备指纹表（**必须从真实抓包提取**，不要编） |
| `L_HDR` | 头部材料盐 |
| `qfTocUrl` / `qfChapterUrl` | 接口路径与参数 |
| `qqTarStr` | 容器解析（若该站不用 tar 则整段替换） |

### 选改（按站点能力）

| 功能 | 不做会怎样 |
|---|---|
| 密钥池（`qfPoolEnsure`） | 若该站不需要响应解密，整段可删 |
| 指纹校验（`peekId`/`qfFpSet`） | 单密钥站可简化，但**建议保留**（防御性） |
| 段评注入 | 删掉后正文更干净，`qqcInsert` 调用点直接返回原文 |
| 自动购买 | 删掉后未购章只给试读提示 |
| 预缓存 | 删掉后失去离线能力（但功能不受影响） |

### 保留不动（通用资产）

- `qqTarStr` / `qfHexToLatin1` / `qfB64ToBytes` —— 通用解析
- `natCtx` 双实现框架 —— 通用性能优化
- `qfStashGet/Put` 缓存三件套 —— 通用
- `qfNap` / `qfIsCancel` / `qfTries` —— 通用退避
- 全部工程纪律（K1~K22）

---

## 十三、验证方法论

### 13.1 分层验证（不要一次跑全链路）

```
第 1 层：hex 通道通不通？
   eval_js: java.ajax(目录URL+',{"type":"hex"}') → 看返回是否全 hex、长度是否符合预期

第 2 层：容器解析对不对？
   eval_js: qfTarStr(qfHexToLatin1(hex)) → 看成员名列表

第 3 层：密钥池拿没拿到？
   eval_js: qfPoolEnsure(source, u => java.ajax(u)) → true/false

第 4 层：单章能不能解出来？
   eval_js: qfDecryptFromHex(hex, bid, cid) → 看 r.ok / r.text.length / r.ms

第 5 层：全链路
   debug_source
```

**每层独立验证的价值**：第 4 层失败时，能立刻区分「是解密算法错」还是「是密钥池没拿到」——不分层的话只能看到「正文为空」，要重新排查一遍。

### 13.2 关键探针

```javascript
// 密钥池状态
qfPoolReady()                     // true/false
qfPoolCache.length                // 池字节数

// 单章解密诊断（本源已内置日志）
// FOCK_APP ok {bid}/{cid} len=xxx 解密 xxms 第N次 fp=xxx keyId=xxx
// FOCK_MISS 第N次 指纹不符 fp=xxx
// QF_STASH hit {bid}/{cid} xxB

// 原生/JS 模式
qfHexModeCache                    // 'java' | 'js' | ''
```

### 13.3 性能基准（本源实测）

| 操作 | 耗时 |
|---|---|
| 单章解密（原生 Java） | **~1.7ms** |
| 单章解密（纯 JS） | 数十~数百 ms |
| 整本预缓存（数百章） | 一次批量请求 + 逐章解密 |

**原生 vs JS 差 10~100 倍**，所以双实现的降级顺序不能反。

---

## 附：本源能力清单（速查）

| 能力 | 入口 | 说明 |
|---|---|---|
| 搜索 | `ruleSearch` | `/common/result/search_txt`，支持分页 |
| 详情 | `ruleBookInfo` | 含 `qfRestypeDetect` 判断普通版/EPUB 版 |
| 目录 | `ruleToc.chapterList` | tar+CSV 解析 + 四档过滤 + 已购标记 |
| 正文 | `ruleContent.content` | 缓存 → 网络 → 解密 三段式 |
| EPUB 正文 | `rt === '4'` 分支 | `qfEpubChapter`（另有一套 ZIP/XHTML 解析） |
| 发现 | `exploreUrl` | 男/女频 × 榜单/分类/书架 |
| 登录 | `loginUrl` | 短信 + 扫码 + 设备指纹管理 |
| 预缓存 | 登录面板 | 整本/增量/强制/自检 |
| 自动购买 | 登录面板 | 按书白名单 + 冷却 |
| 段评 | 正文注入 | 段落级气泡 + useweb 面板 |
| 净化 | 登录面板 | 四档屏蔽 + 作者话裁剪 |
| 调试 | `searchUrl` 特判 | 关键词 `fockselftest` / `shelfdiag` / `qfbench` 触发自检 |

**调试入口这个设计值得学**：把自检功能挂到 `searchUrl` 的关键词特判上（返回 `robots.txt` 这种无害 URL），用户只要搜一个特殊词就能跑诊断，不需要额外的按钮或外部工具。

---

## 结语：三条可以带走的经验

1. **重活进 jsLib，规则只做编排。** 规则越短，问题定位越快；算法集中，改一处全站受益。
2. **缓存要能「过期」，不能无脑信任。** 试读缓存、密钥池、指纹——每一样都要有「什么条件下该丢弃」的明确规则，否则错误会沉淀成「用户看到的最终结果」。
3. **宁可不返回，绝不返回可疑内容。** 解密失败、服务端拒绝、格式异常——这三种情况一律抛错，不要用「差不多能用」的数据填充。缓存的持久性会把一次小错误放大成长期故障。
