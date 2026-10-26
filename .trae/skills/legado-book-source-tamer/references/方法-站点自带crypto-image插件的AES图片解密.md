# 方法：站点自带 `crypto-image` 插件的 AES-128-CBC 图片解密

> 沉淀来源：黄果短剧 v5（2026-10-27）。用户反馈「封面不显示」，
> 前两轮误判为 `blockNetworkImage` 竞态 → 又误判为「明文 JPEG」，
> 最终实锤：**站点用自带前端插件做 AES-128-CBC 图片加密，密钥就写在公开 JS 里**。

---

## 0. 误判链复盘（三层，每层都有实锤才往下走）

| 轮次 | 假设 | 实锤方法 | 结果 |
| --- | --- | --- | --- |
| 1 | `blockNetworkImage` 竞态 | 参考文档 + `coverDecodeJs` 改透传 | ❌ 封面仍不显示 |
| 2 | 明文 JPEG，无需解密 | `java.get` 读字节看魔数 | ❌ 魔数 `[79,232,151]` != `[255,216,255]` |
| 3 | 站点 AES 加密 | 读站点 `crypto-image.js` + `crypto-image-protocol.js` | ✅ 密钥明文写在 JS 里 |

**教训**：**「沙盒 curl 200 + Content-Length 正常」完全不能证明图是明文**。
第一轮用沙盒 urllib 拿到 196KB 就断言"图片公开"，实际 magic 是 `4fe897a4`（「黄果」UTF-8）而非 `ffd8ffe0`。
**必须 `java.get(...).bodyAsBytes()` 看魔数**。

---

## 1. 识别特征

| 现象 | 说明 |
| --- | --- |
| `Content-Type: binary/octet-stream` | 不是 `image/jpeg`，服务端不当图片发 |
| 文件头是**中文**（如「黄果」UTF-8 = `4F E8 97 A4`） | 密文恰好以可读字符开头，极具迷惑性 |
| 无 JPEG SOI（`FF D8 FF`）/ PNG 签名（`89 50 4E 47`） | 但文件长度是 16 的整数倍 |
| 页面引用 `crypto-image.js` / `crypto-worker.js` / `crypto-image-protocol.js` | 最强特征 |

---

## 2. 密钥位置：三个 JS 文件

### 2.1 `crypto-image-protocol.js` —— 密钥就在这里

```javascript
window.CryptoImageProtocol = Object.freeze({
  "decryptEnabled": true,
  "decryptKey": "f5d965df75336270",   // 16 字符 = 128 bit
  "decryptIV":   "97b60394abc2fbe1"   // 16 字符 = 128 bit
})
```

**注意**：`Object.freeze` + 注释写"独立于后台配置"——这是**硬编码静态密钥**，
不会随时间/URL 变化，可以安全写死在书源里。

### 2.2 `crypto-image.js` —— 主逻辑（34KB）

关键片段：

```javascript
const valid = value => {
  if (typeof value !== 'string' || !value.trim() || /^(CHANGE_ME|REPLACE_WITH_|YOUR_)/i.test(value.trim()) || /^<.*>$/.test(value.trim())) return false
  try { return unescape(encodeURIComponent(value)).length === 16 } catch (_) { return false }
}
const enabled = current.decryptEnabled === true && valid(current.decryptKey) && current.decryptIV
```

`valid()` 要求 **UTF-8 长度恰好 16 字节** => AES-128。

### 2.3 `crypto-worker.js` —— 算法与模式（11KB）

```javascript
mode: CryptoJS.mode.CBC,
padding: CryptoJS.pad.NoPadding
```

WebCrypto 分支：`importKey('raw', utf8(credentials.key), { name: 'AES-CBC' }, ...)`

=> **AES-128-CBC + NoPadding**，key/iv 都是 UTF-8 字符串原样 16 字节。

---

## 3. `coverDecodeJs` 正确写法（InputStream -> byte[]）

```javascript
(function(){
try{
  var baos=new Packages.java.io.ByteArrayOutputStream();
  var buf=new Packages.java.lang.String('00000000000000000000000000000000').getBytes();
  var n=result.read(buf);
  while(n>0){baos.write(buf,0,n);n=result.read(buf)}
  var enc=baos.toByteArray();
  if(!enc||enc.length<32||enc.length%16!==0)return enc;      // 非16对齐=不是AES密文，透传
  var Cipher=Packages.javax.crypto.Cipher;
  var SKS=Packages.javax.crypto.spec.SecretKeySpec;
  var IVS=Packages.javax.crypto.spec.IvParameterSpec;
  var kb=new Packages.java.lang.String('f5d965df75336270').getBytes('UTF-8');
  var vb=new Packages.java.lang.String('97b60394abc2fbe1').getBytes('UTF-8');
  var c=Cipher.getInstance('AES/CBC/NoPadding');
  c.init(Cipher.DECRYPT_MODE,new SKS(kb,'AES'),new IVS(vb));
  var dec=c.doFinal(enc);
  var b0=(dec[0]+256)%256,b1=(dec[1]+256)%256,b2=(dec[2]+256)%256;
  if((b0===255&&b1===216)||(b0===137&&b1===80&&b2===78)||(b0===71&&b1===73&&b2===70)||(b0===82&&b1===73&&b2===70))return dec;
  return enc;                                                // 魔数不对=本就是明文，透传
}catch(e){return null}
})()
```

**四个要点**：

1. **`result` 是 InputStream**（不是 URL！URL 在 `src`）——`evalJS` 时 App 已 `put("result", inputStream)` 且 `put("src", 图片URL)`
2. **`%16 !== 0` 必须判**：明文图（未加密的少数图）长度不一定是 16 倍数，直接 `doFinal` 会抛 `IllegalBlockSizeException`
3. **魔数双保险**：解密后是 JPEG/PNG/GIF/WebP 才用密文解密结果，否则透传原文（防站点部分图不加密）
4. **返回 byte[]**（强转 `as ByteArray`），不要 base64

---

## 4. 实测记录（App 内 eval_js 真 Rhino 环境）

```
encLen=196816  encAligned=true
decLen=196816  decMagic=[255,216,255]  isJPEG=true
```

沙盒侧同 URL 用 pycryptodome 交叉验证：

```
SOI@0  DQT@2  SOF0@136  DHT@155  SOS@575  EOI@196807
```

完全标准 JPEG 结构 => 解密正确。

---

## 5. 排查 Checklist（图片不显示时）

```
[ ] java.get(url).bodyAsBytes() 看魔数 —— 不是 FFD8FF/89504E47 就是密文
[ ] Content-Type 是否 binary/octet-stream
[ ] 文件长度是否 16 的倍数
[ ] 页面是否引用 crypto-image*.js
[ ] 抓 crypto-image-protocol.js 找 decryptKey/decryptIV（Object.freeze 静态）
[ ] 抓 crypto-worker.js 确认 mode/padding（CBC/NoPadding）
[ ] coverDecodeJs 用 InputStream 读法 + %16 护栏 + 魔数双保险
[ ] App 内 eval_js 实测 doFinal 后魔数 = FFD8FF
```

> **通用推论**：凡站点带 `crypto-image` 这类"前端解密插件"的，密钥**几乎必然硬编码在某个公开 JS 里**
> （否则前端没法解）。优先翻 `*-protocol.js` / `*-config.js` / `window.XxxProtocol = Object.freeze({...})`。
> 比盲猜 XOR/置换快得多——盲猜 XOR 曾浪费大量时间。

---

## 6. 关联

- `方法-图床AES加密图片解密.md`：`coverDecodeJs` / `imageDecode` 双钩子的触发链路与源码定位
- `方法-图片不显示排查总表-加密之外的三条路.md`：非加密因素（换主机/SNI/blockNetworkImage）
- 本站 m3u8 也带 `auth_key` 时效签名，但那是**防盗链**不是加密（播放器原生支持 HLS+AES-128 分片），与封面这套不是一回事
