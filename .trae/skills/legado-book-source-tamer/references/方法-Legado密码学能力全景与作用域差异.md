# 方法-Legado 密码学能力全景与作用域差异

> 2026-10-10 全量实测沉淀（红果短剧 X-Argus 签名复现过程中发现既有文档严重不足）
> 适用：一切需要加密/解密/签名/哈希的书源（加密 API 站、字体反爬、图片解密、登录鉴权）

---

## 0 核心结论（先看这个）

| 事实 | 说明 |
|---|---|
| **官方密码学 API 齐全** | `java.digestHex` / `HMacHex` / `createSymmetricCrypto` / `createAsymmetricCrypto` / `createSign` / `md5Encode` 全部可用 |
| **算法覆盖面远超预期** | SM3 / SM4 / SHA3 / BLAKE2 / ChaCha20 / RC4 / Blowfish / RC2 全都支持 |
| **`Packages.*` 是终极后门** | 任何官方 API 覆盖不到的算法，都可直接 `Packages.javax.crypto.Cipher` 手写 |
| **★作用域差异是最大陷阱** | **jsLib 里 `java.*` 全部不可用**（不只是 ajax！），`Packages.*` 才可用 |
| **既有 `方法-加密解密.md` 是 API 抄本** | 只有方法名和签名，**没有算法支持矩阵、没有作用域差异、没有坑位说明** —— 本文补齐 |

---

## 1 作用域差异（★★★ 最重要）

### 1.1 三作用域实测对照表

| API / 对象 | **eval_js**（绑定书源） | **规则上下文**（@js:） | **jsLib 函数内** |
|---|---|---|---|
| `java.md5Encode` | ✅ function | ✅ function | ❌ **object**（不是函数） |
| `java.digestHex` | ✅ | ✅ | ❌ object |
| `java.HMacHex` | ✅ | ✅ | ❌ object |
| `java.createSymmetricCrypto` | ✅ | ✅ | ❌ object |
| `java.base64Encode` | ✅ | ✅ | ❌ object |
| `java.hexDecodeToString` | ✅ | ✅ | ❌ object |
| `java.strToBytes` | ✅ | ✅ | ❌ object |
| `java.randomUUID` | ✅ | ✅ | ❌ object |
| `java.encodeURI` | ✅ | ✅ | ❌ object |
| `java.decodeURI` | ❌ undefined | — | ❌ |
| `java.ajax` / `get` / `post` / `head` | ✅ | ✅ | ❌ object |
| `java.toast` / `longToast` / `log` | ✅ | ✅ | ❌ object |
| **`Packages.java.security.MessageDigest`** | ✅ | ✅ | ✅ **function** |
| **`Packages.org.bouncycastle...SM3`** | ✅ | ✅ | ✅ **function** |
| **`Packages.javax.crypto.Cipher`** | ✅ | ✅ | ✅ **function** |
| `source` 变量 | ✅ | ✅ | ❌ undefined |

### 1.2 实测证据 A —— jsLib 内（`PROBE_SCOPE()` 返回值，函数写在 jsLib 字段里）

```
{"md5Encode":"ERR:TypeError: md5Encode 不是函数，它是 object。",
 "digestHex":"ERR:TypeError: digestHex 不是函数，它是 object。",
 "HMacHex":"ERR:TypeError: HMacHex 不是函数，它是 object。",
 "symCrypto":"ERR:TypeError: createSymmetricCrypto 不是函数，它是 obje",
 "base64Encode":"ERR:TypeError: base64Encode 不是函数，它是 object。",
 "hexDecodeToString":"ERR:TypeError: hexDecodeToString 不是函数，它是 object。",
 "strToBytes":"ERR:TypeError: strToBytes 不是函数，它是 object。",
 "randomUUID":"ERR:TypeError: randomUUID 不是函数，它是 object。",
 "encodeURI":"ERR:TypeError: encodeURI 不是函数，它是 object。",
 "decodeURI":"ERR:TypeError: decodeURI 不是函数，它是 object。",
 "ajax":"OK:object", "get":"OK:object", "post":"OK:object", "toast":"OK:object",
 "Packages":"OK:object",
 "MsgDigest":"OK:function", "SM3cls":"OK:function", "Cipher":"OK:function",
 "sourceVar":"OK:undefined"}
```

### 1.2b 实测证据 B —— 规则上下文（`@js:` 规则体，同一份探测逻辑）

```
{"md5Encode":"OK:900150983cd24fb0d6963f7d28e17f72",
 "digestHex":"OK:900150983cd24fb0d6963f7d28e17f72",
 "digestHexSM3":"OK:66c7f0f462eeedd9",
 "HMacHex":"OK:40e7d441cadb17b07f050341aa23a682",
 "symCrypto":"OK:5Zk+zP5W9vbM6S3qG0C21w==",
 "base64Encode":"OK:YWJj",
 "hexDecodeToString":"OK:abc",
 "strToBytes":"OK:1",
 "randomUUID":"OK:49bd40a4-12f2-4c84-919a-fc554545...",
 "encodeURI":"OK:a+b",
 "ajax":"OK:function", "post":"OK:function", "toast":"OK:function",
 "Packages":"OK:object",
 "MsgDigest":"OK:function", "SM3cls":"OK:function",
 "source":"OK:object"}
```

**A/B 对照一目了然**：同一段代码，写在 jsLib 里 `java.*` 全灭，写在 `@js:` 规则里 `java.*` 全活。

### 1.2c 但 jsLib 的函数**可以**从规则上下文调用

红果源实测：`ruleContent.content` 里 `HG_play(java, vid, sid)`（`HG_play` 定义在 jsLib）**正常工作**。
⇒ 正确姿势 = **jsLib 定义函数 + 规则里传 `java` 进去**，函数内部用 `Packages.*` 或收到的 `java` 参数。

### 1.3 结论：jsLib 里的正确写法

**jsLib 顶层函数里，一切密码学操作必须走 `Packages.*`**，不能用 `java.*`：

```js
// ✘ jsLib 里会报 "xxx 不是函数，它是 object"
function bad(){
  return java.md5Encode('abc');
}

// ✔ jsLib 里正确
function good(){
  var d = Packages.java.security.MessageDigest.getInstance('MD5');
  d.update(new Packages.java.lang.String('abc').getBytes('UTF-8'));
  var r = d.digest();
  var h = '';
  for(var i=0;i<r.length;i++){ var b=r[i]&0xff; h += (b<16?'0':'')+b.toString(16); }
  return h;
}

// ✔ 或者：把 java 作为参数注入（推荐，代码更简洁）
function better(JV){ return JV.md5Encode('abc'); }   // 调用方传 java
```

**为什么？** `java` 在 jsLib 作用域绑定的是 **BookSource 对象本身**（`BaseSource : JsExtensions`），
而 BookSource 上的 `md5Encode` 等方法是 **Kotlin 默认参数方法 / 未标注 `@JavascriptInterface`**，
Rhino 访问时得到的是 JavaPackage 包装对象而非可调用函数。
`Packages.*` 走的是 Rhino 原生的 Java 包反射，不受此限制。

---

## 2 官方密码学 API 全表

### 2.1 摘要 / 哈希

```js
java.digestHex(data, algorithm)        // → 16 进制字符串
java.digestBase64Str(data, algorithm)  // → Base64 字符串
```

**实测支持的算法**（`digestHex('abc', algo)`）：

| 算法 | 结果 | 状态 |
|---|---|---|
| `MD5` | `900150983cd24fb0d6963f7d28e17f72` | ✅ |
| `SHA-1` | `a9993e364706816aba3e25717850c26c9cd0d89d` | ✅ |
| `SHA-256` | `ba7816bf8f01cfea...f20015ad` | ✅ |
| `SHA-384` | `cb00753f45a35e8b...` | ✅ |
| `SHA-512` | `ddaf35a193617aba...` | ✅ |
| **`SM3`** | `66c7f0f462eeedd9...f4ba8e0` | ✅ **国密可用！** |
| `SHA3-256` | `3a985da74fe225b2...` | ✅ |
| `BLAKE2B-256` | `bddd813c63423972...` | ✅ |
| `SM2` | — | ❌ NoSuchAlgorithm（SM2 是**非对称**算法，不是摘要） |

### 2.2 HMAC

```js
java.HMacHex(data, algorithm, key)     // → 16 进制
java.HMacBase64(data, algorithm, key)  // → Base64
```

**实测支持**：`HmacMD5` / `HmacSHA1` / `HmacSHA256` / `HmacSHA384` / `HmacSHA512` / **`HmacSM3`** / `HmacSHA3-256`

### 2.3 对称加密

```js
java.createSymmetricCrypto(transformation, key, iv)  // 三参
java.createSymmetricCrypto(transformation, key)      // 两参（ECB 无需 iv）
// key/iv 可以是 String（按 UTF-8 转 byte[]）或 byte[]
```

**实测支持的 transformation**：

| transformation | iv | 实测结果 |
|---|---|---|
| `AES/ECB/PKCS5Padding` | 不需要 | ✅ |
| `AES/CBC/PKCS5Padding` | 需要 | ✅ |
| `AES/CTR/NoPadding` | 需要 | ✅ |
| `AES/GCM/NoPadding` | 需要 | ✅（含 tag） |
| `AES/OFB/NoPadding` | 需要 | ✅ |
| `AES/CFB/NoPadding` | 需要 | ✅ |
| `AES/ECB/NoPadding` | 不需要 | ✅（需自行补齐） |
| `DES/ECB/PKCS5Padding` | 不需要 | ✅ |
| `DES/CBC/PKCS5Padding` | 需要 | ✅ |
| `DESede/ECB/PKCS5Padding` | 不需要 | ✅ |
| **`SM4/ECB/PKCS5Padding`** | 不需要 | ✅ **国密可用！** |
| **`SM4/CBC/PKCS5Padding`** | 需要 | ✅ |
| `Blowfish/ECB/PKCS5Padding` | 不需要 | ✅ |
| `RC2/ECB/PKCS5Padding` | 不需要 | ✅ |
| `RC4` | 不需要 | ✅ |
| `ChaCha20` | 需要 | ✅ |

**对象方法**：
```js
c.encryptBase64(str)   // → Base64 密文
c.encryptHex(str)      // → Hex 密文
c.encrypt(byte[])      // → byte[]
c.decryptStr(str)      // ← ★自动识别 Base64 / Hex（源码见下）
c.decrypt(byte[])      // ← byte[]
c.decryptStr(byte[])   // ← 也可
```

**★ `decryptStr` 的自动识别源码**（`SymmetricCryptoAndroid.kt`）：
```kotlin
override fun decrypt(data: String): ByteArray {
    val bytes = if (data.isHex()) HexUtil.decodeHex(data) else Base64.decode(data)
    return decrypt(bytes)
}
```
⇒ 传入的密文是 Hex 还是 Base64 **自动判断**，无需手动转换。实测两者都能解出。

### 2.4 非对称 / 签名

```js
java.createAsymmetricCrypto('RSA')      // → AsymmetricCrypto 对象
java.createSign('SHA256withRSA')        // → Sign 对象
```

### 2.5 MD5 快捷方法

```js
java.md5Encode(str)    // 32 位小写
java.md5Encode16(str)  // 中间 16 位
```

**⚠️ 限制**：`md5Encode` **只接受单参 String**。传两参（如 charset）会报
`找不到方法 "BookSource.md5Encode(java.lang.String,string)"`。
需要 byte[] 输入时用 `MessageDigest`。

### 2.6 编码 / 转换工具

```js
java.base64Encode(str)              // → Base64
java.base64Decode(str)              // → 原文
java.base64DecodeToByteArray(str)   // → byte[]
java.hexDecodeToString(hex)         // → 原文
java.hexDecodeToByteArray(hex)      // → byte[]
java.hexEncodeToString(byte[])      // → hex（见下方坑）
java.strToBytes(str, 'UTF-8')       // → byte[]
java.bytesToStr(byte[], 'UTF-8')    // → 原文
java.encodeURI(str)                 // → URL 编码
java.randomUUID()                   // → UUID
```

**⚠️ 无 `java.decodeURI`**（实测 undefined）→ 用 JS 原生 `decodeURIComponent`。

### 2.7 已废弃但仍可用（web 端需要，勿删）

`aesDecodeToString` / `aesBase64DecodeToString` / `aesEncodeToString` /
`desDecodeToString` / `desBase64DecodeToString` / `tripleDESDecodeStr` 等
—— 源码标注 `@Deprecated` 但保留 `@JavascriptInterface`，**实测全部可用**。
老书源若在用，无需改动。

---

## 3 ★byte[] 互转的唯一可靠姿势

**这是 Rhino 里最大的坑之一。**

### 3.1 不可用的方式

```js
// ✘ 报 "newInstance 不是函数，它是 object"
Packages.java.lang.reflect.Array.newInstance(Packages.java.lang.Byte.TYPE, n);

// ✘ java.strToBytes 返回的对象不能直接当 byte[] 传给需要 byte[] 的方法
```

### 3.2 唯一可靠：String + ISO-8859-1 往返

```js
var CS = Packages.java.nio.charset.Charset.forName('ISO-8859-1');

// Uint8Array → java byte[]
function jb(u8){
  var s = '';
  for(var i=0;i<u8.length;i++) s += String.fromCharCode(u8[i] & 0xff);
  return new Packages.java.lang.String(s).getBytes(CS);
}

// java byte[] → Uint8Array
function j2u(jarr){
  var o = new Uint8Array(jarr.length);
  for(var i=0;i<jarr.length;i++) o[i] = jarr[i] & 0xff;
  return o;
}
```

ISO-8859-1 是**单字节映射**，`0x00-0xFF` 无损往返，是 byte[] 通道的完美载体。

### 3.3 如果只是要字符串

```js
// String → byte[]（简单场景）
var b = java.strToBytes('hello','UTF-8');

// byte[] → String
var s = java.bytesToStr(b,'UTF-8');
```

---

## 4 官方 API 覆盖不到时：直调 Java

### 4.1 手写 Cipher

```js
var C = Packages.javax.crypto.Cipher;
var c = C.getInstance('AES/CBC/PKCS5Padding');
c.init(C.ENCRYPT_MODE,
  new Packages.javax.crypto.spec.SecretKeySpec(keyBytes,'AES'),
  new Packages.javax.crypto.spec.IvParameterSpec(ivBytes));
var out = c.doFinal(dataBytes);
```

### 4.2 BouncyCastle 直接实例化（绕过 provider）

```js
// 标准 API 找不到的算法，BC 类可能可用
var d = new Packages.org.bouncycastle.jcajce.provider.digest.SM3.Digest();
var b = jb(inputBytes);
d.update(b, 0, b.length);
var r = j2u(d.digest());
```

**⚠️ 注意**：`Packages.org.bouncycastle.jcajce.provider.digest.SM3` 是 **class**（`typeof === 'function'`），
必须 `new SM3.Digest()` 才能拿到实例。`new SM3()` 会失败。

**不过**：`java.digestHex('abc','SM3')` 已经直接可用，**不需要**绕道 BouncyCastle。
只有在需要**增量 update** 或**原始字节输出**时才用 BC。

### 4.3 判断某算法是否可用

```js
try {
  Packages.java.security.MessageDigest.getInstance('SM3');
  // 可用
} catch(e) {
  // NoSuchAlgorithmException
}
```

---

## 5 实战选型决策树

```
需要哈希/摘要？
├─ 是 → java.digestHex(data, algo)          ← 首选
│        算法不在列表？→ Packages...MessageDigest / BouncyCastle
└─ 否
需要 HMAC？
├─ 是 → java.HMacHex(data, algo, key)       ← 首选
└─ 否
需要对称加解密？
├─ 是 → java.createSymmetricCrypto(tf, k, iv)   ← 首选
│        ├─ transformation 在实测列表里 → 直接用
│        └─ 不在 → Packages.javax.crypto.Cipher 手写
└─ 否
需要非对称/签名？
├─ 是 → java.createAsymmetricCrypto / createSign
└─ 否 → 只需编码转换 → java.base64Encode / hexDecodeToString / strToBytes

★ 以上全部在 jsLib 里使用时：改用 Packages.* 或参数注入 java
```

---

## 6 避坑清单

| # | 坑 | 真相 | 解法 |
|---|---|---|---|
| K1 | jsLib 里 `java.ajax` 不可用 | **不止 ajax** —— jsLib 里 `java.*` **全部**不可用 | 用 `Packages.*`，或参数注入 `f(JV)` 传 `java` |
| K2 | `Array.newInstance` 报"不是函数" | Rhino 不支持 | `String` + `ISO-8859-1` 往返 |
| K3 | `java.md5Encode(str, charset)` 报找不到方法 | 只接受单参 | 用 `MessageDigest.getInstance('MD5')` |
| K4 | `java.decodeURI` 是 undefined | 本 App 无此方法 | 用 JS 原生 `decodeURIComponent` |
| K5 | `setIv('string')` 报找不到方法 | 只接受 byte[] | `c.setIv(java.strToBytes(iv,'UTF-8'))` |
| K6 | `SM3` 用 `MessageDigest.getInstance` 报 NoSuchAlgorithm | 标准 provider 无 SM3 | 用 `java.digestHex(s,'SM3')` 或 `new SM3.Digest()` |
| K7 | `new Packages...SM3()` 失败 | SM3 是 class 不是实例 | `new SM3.Digest()` |
| K8 | AES 15 字节 key 报 InvalidKey | AES 只接受 16/24/32 字节 | 补零或换算法 |
| K9 | `encryptToString` 不存在 | 只有 `encryptBase64` / `encryptHex` / `encrypt` | 用这三个 |
| K10 | 密文是 Hex 还是 Base64 分不清 | `decryptStr` **自动识别** | 直接传，不用手动转 |
| K11 | `digestHex(s,'SM2')` 报 NoSuchAlgorithm | SM2 是非对称算法 | 用 `createAsymmetricCrypto('SM2')` |
| K12 | 大文件加密内存爆 | `encrypt(byte[])` 全量载入 | 分块处理 |

---

## 7 完整能力矩阵（速查表）

### 摘要（`java.digestHex` / `digestBase64Str`）
```
MD5 ✅  SHA-1 ✅  SHA-256 ✅  SHA-384 ✅  SHA-512 ✅
SM3 ✅  SHA3-256 ✅  BLAKE2B-256 ✅
SM2 ❌（非对称）
```

### HMAC（`java.HMacHex` / `HMacBase64`）
```
HmacMD5 ✅  HmacSHA1 ✅  HmacSHA256 ✅  HmacSHA384 ✅
HmacSHA512 ✅  HmacSM3 ✅  HmacSHA3-256 ✅
```

### 对称加密（`java.createSymmetricCrypto`）
```
AES: ECB/CBC/CTR/GCM/OFB/CFB ✅（PKCS5Padding 或 NoPadding）
DES: ECB/CBC ✅
DESede(3DES): ECB ✅
SM4: ECB/CBC ✅
Blowfish ✅  RC2 ✅  RC4 ✅  ChaCha20 ✅
```

### 非对称 / 签名
```
createAsymmetricCrypto('RSA'|'SM2'|...) ✅
createSign('SHA256withRSA'|...) ✅
```

### 编码工具
```
base64Encode/Decode/DecodeToByteArray ✅
hexDecodeToString/ToByteArray ✅  hexEncodeToString ✅
strToBytes / bytesToStr ✅
encodeURI ✅（decodeURI ❌ → 用 JS 原生）
randomUUID ✅
```

---

## 8 与既有文档的关系

| 文档 | 内容 | 本文补充 |
|---|---|---|
| `方法-加密解密.md` | 官方 JsHelp **API 抄本**（方法名 + 参数签名） | **算法支持矩阵 + 作用域差异 + byte[] 互转 + 12 条坑位** |
| `方法-全加密API书源逆向与客户端可信重放.md` | L4 加密站**协议逆向方法论**（握手/派生/签名/信封） | 本文是**底层能力底座**，那篇是上层协议设计 |
| `方法-图床AES加密图片解密.md` | 图床图片 AES 解密的**专项应用** | 本文是通用能力，那篇是 imageDecode 钩子专项 |
| `方法-多层密钥AES与轮换签名逆向.md` | 多层密钥 + 签名轮换的**协议设计** | 同上 |

**一句话**：本文回答「**Legado 能算什么**」，其他文档回答「**怎么用这些能力对付某个站**」。

---

## 9 验证方法论

本次全部结论均由 **App 内真实执行** 得出（非源码推测）：

1. **API 存在性探测**：`typeof java.xxx` 逐个枚举
2. **算法支持矩阵**：对每个算法跑一次真实运算并输出结果
3. **作用域差异**：把探测函数**写入书源 jsLib**，用 `eval_js` 调用 → 得到 jsLib 真实作用域结果（⚠️ **不能用 eval 模拟**，会得到错误结论）
4. **交叉验证**：关键算法（如 SM3）与标准值比对（`SM3("abc")` = `66c7f0f4...`）

**⚠️ 重要教训**：**作用域探测必须用真实 jsLib**。
在 `eval_js` 顶层 `eval(fnText)` 得到的结论是**错的** —— 顶层 eval 会继承 eval_js 的作用域（那里 `java` 是完整 BookSource），
只有把函数**真正写进书源 jsLib 字段**再调用，才能看到 jsLib 的真实限制。

**实测对照（三轮）**：

| 探测方式 | `java.md5Encode` | `java.ajax` | 结论有效性 |
|---|---|---|---|
| `eval_js` 顶层 `eval(fnText)` | ✅ 可用 | ✅ 可用 | ❌ **误导**（继承 eval_js 作用域） |
| 函数写入 jsLib，`eval_js` 调用 | ❌ object | ❌ object | ✅ **真实 jsLib 限制** |
| 函数体写在 `@js:` 规则里 | ✅ 可用 | ✅ 可用 | ✅ **真实规则上下文** |

⇒ 只有后两种能反映真实情况，第一种会得出完全相反的结论。
