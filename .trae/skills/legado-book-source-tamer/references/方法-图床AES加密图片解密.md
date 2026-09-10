# 图床 AES 加密图片解密方法论
## ——封面/正文图片不显示的通用排查与修复（含缓存中毒三层机制）

> 沉淀来源：黑料网（hlwf6.com）pic.nsxxlj.cn 图床全站 AES-128-CBC 加密破解实战（2026-09-11，v3.3）
> 适用症状：**图片请求返回 200、规则提取 URL 全部正确，但 App 里封面/正文图片就是不显示**；网页端打开却正常。
> 适用范围：任何"图片本体加密"站点（图床整体加密 / 懒加载 Worker 解密类），小说源封面、漫画源正文、RSS 源均适用。

---

## 目录
1. [识别与定位：魔数探测定位法（黄金三分钟）](#一识别与定位魔数探测定位法黄金三分钟)
2. [逆向网页端解密逻辑与密钥提取套路](#二逆向网页端解密逻辑与密钥提取套路)
3. [LegadoTeam 双钩子机制（源码级）](#三legado-双钩子机制源码级)
4. [缓存中毒三层机制与"前几张不显示"根因](#四缓存中毒三层机制与前几张不显示根因)
5. [完整模板代码](#五完整模板代码)
6. [验证清单与调试方法论](#六验证清单与调试方法论)
7. [避坑清单](#七避坑清单)
8. [已知样本档案](#八已知样本档案)

---

## 一、识别与定位：魔数探测定位法（黄金三分钟）

图片"下载成功但不显示"时，**第一件事永远是看首字节魔数**，不要急着怀疑规则写错。图片格式魔数对照表：

| 格式 | 首字节(hex) | 备注 |
|---|---|---|
| JPEG | `ff d8 ff` | |
| PNG | `89 50 4e 47` | |
| GIF | `47 49 46 38` | |
| WebP | `52 49 46 56`(RIFF) | |
| **密文** | **以上都不是** | 加密图片首字节无规律（如 `dd e2 8c 47`、`4f e8 97 a4`） |

**判定铁律**：
- 魔数正常 → 问题在规则/防盗链/UA/缓存，去查 HTTP 层，与解密无关。
- 魔数异常 + `Content-Type: binary/octet-stream` + **网页端 F12 能看到正常图片** → 图片本体加密，本文档适用的场景实锤。
- 魔数异常 + 网页端也看不到原图（显示的是别的 URL） → 你拿到的不是真正图片地址，先查懒加载属性（`z-image-loader-url`/`data-src`/`data-original`）。

### eval_js 探测模板（直连图床拿首字节）

```js
(function(){
function rawBytes(u){                       // java.net.URL 直连，不走 AnalyzeUrl
  var U=new Packages.java.net.URL(u);
  var conn=U.openConnection();
  conn.setConnectTimeout(8000);conn.setReadTimeout(8000);
  conn.setRequestProperty('User-Agent','<书源同款UA>');
  var is=conn.getInputStream();
  var baos=new Packages.java.io.ByteArrayOutputStream();
  var s=new Packages.java.lang.String('00000000').getBytes();  // ★buffer 用 String.getBytes 造
  var n=is.read(s);
  while(n>0){baos.write(s,0,n);n=is.read(s)}
  is.close();
  return baos.toByteArray();
}
var u='https://图床域名/xxx.png';
var enc=rawBytes(u);
var hex='';
for(var k=0;k<16;k++){var c=(enc[k]+256)%256;hex+=((c<16?'0':'')+c.toString(16))}
return 'len='+enc.length+' head='+hex;      // 对照魔数表判定
})()
```

> ⚠️ 探测必踩坑：`java.lang.reflect.Array.newInstance(byte.class, 8192)` 在 LegadoTeam 的 Rhino 里报 `newInstance 不是函数`——byte buffer 用 `new Packages.java.lang.String('00000000').getBytes()` 生成最省事。byte[] 元素是**有符号数**，取值前必须 `(enc[k]+256)%256` 归一化成正数再比魔数。

**对照实验法**（30秒确证探测有效）：同一代码探测一个已知明文图片（如百度 logo PNG），应得 `89 50 4e 47`；再探测目标图床图片，若得到乱七八糟的首字节，加密实锤。

---

## 二、逆向网页端解密逻辑与密钥提取套路

网页端既然能显示，浏览器里一定有解密代码。定位方法：

1. F12 → Network → 过滤 JS → 找体积极大的文件（本次是 280KB 的 `/static/v4/__base/js/image.js`），名字常含 image/photo/decode。
2. 在其中搜关键词：`CryptoJS`、`AES`、`decrypt`、`Worker`、`createObjectURL`、`readAsDataURL`。
3. 典型实现链：`fetch(imgUrl) → blob → FileReader.readAsDataURL → base64 → CryptoJS.AES.decrypt → atob → Blob → createObjectURL` → 赋给 `<img src>`。**图片 src 在浏览器里显示为 blob: URL** 是强特征。

### 密钥混淆的三种常见藏法与提取

**套路A：字符码数组混淆（本次实战）**
```js
function cc(a){a=a.split("_");var b=[];for(var i=0;i<a.length;i++)b.push(a[i]-0);return String.fromCharCode.apply(null,b)}
// key = cc("102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48")
```
提取方法：把下划线分隔的数字逐个 `String.fromCharCode(n)` 拼起来。本例：
- `102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48` → `f5d965df75336270`
- `57_55_98_54_48_51_57_52_97_98_99_50_102_98_101_49` → `97b60394abc2fbe1`

提取脚本（离线即可，不必在 App 里）：
```js
"102_53_100".split("_").map(n=>String.fromCharCode(+n)).join("")
```

**套路B：atob/双层 base64** —— `atob('ZjVkOTY1...')` 之类，直接解码。
**套路C：_0x 十六进制混淆** —— 常见 obfuscator.io 特征，用浏览器控制台直接调该函数最省事（把页面 JS 粘到控制台跑一次看返回值）。

### 算法参数判定

- **块对齐验证**：密文长度 `% 16 == 0` → `NoPadding`；密文长度 16 整除且结尾有规律填充字节 → `PKCS5Padding`/`PKCS7Padding`。本次 258096 = 16×16131 整除 → NoPadding。
- **密钥长度**：key 字符串 16 字节 → AES-128；24/32 → AES-192/256。
- **key/iv 是 hex 字符串还是 raw bytes**：图床 JS 用的 CryptoJS `parse` 还是直接传字符串。本次 key='f5d965df75336270' 直接 `getBytes('UTF-8')` 即 16 字节密钥（不是 hex 解码后的 8 字节）。**两种理解都试一遍，哪个解密出魔数就是哪个**——这是暴力但可靠的定位法。
- **CBC/ECB**：先按 CBC+iv 试（有 iv 字段）；失败再试 ECB。

### 密钥有效性验证（eval_js 实跑，javax.crypto 直调）

```js
(function(){
// enc = 上节 rawBytes() 拿到的真实密文
var Cipher=Packages.javax.crypto.Cipher;
var SKS=Packages.javax.crypto.spec.SecretKeySpec;
var IVS=Packages.javax.crypto.spec.IvParameterSpec;
var kb=new Packages.java.lang.String('f5d965df75336270').getBytes('UTF-8');
var vb=new Packages.java.lang.String('97b60394abc2fbe1').getBytes('UTF-8');
var c=Cipher.getInstance('AES/CBC/NoPadding');
c.init(Cipher.DECRYPT_MODE,new SKS(kb,'AES'),new IVS(vb));
var d=c.doFinal(enc);
var hex='';
for(var k=0;k<8;k++){var b=(d[k]+256)%256;hex+=((b<16?'0':'')+b.toString(16))}
return 'decrypted head: '+hex;   // ffd8ff(JPEG)/89504e47(PNG) = 密钥正确
})()
```

**多时间点取样**：抽不同日期上传的图片（本次验证 2026-02 旧图与 09 月新图同 key）→ 确认 key 全局固定不随图轮换。若每图不同 key，则必须从页面 JS 里动态提取（key 会随响应下发），复杂度上升一个量级。

---

## 三、LegadoTeam 双钩子机制（源码级）

LegadoTeam 版（LegadoReader/legado fork 现役主仓库，gedoor/legado 官方仓库已清空）原生支持**图片解密 JS 钩子**，不需要改任何图片提取规则，规则只管产出**密文图片的原始 URL**。

### 触发链路（源码实锤）

**封面（Glide 通道）**：
```
BookCover.load(context, path, sourceOrigin=book.getCoverSourceOrigin())
  → options.set(OkHttpModelLoader.sourceOriginOption, sourceOrigin)
  → Glide → OkHttpModelLoader → OkHttpStreamFetcher.loadData
  → options.get(sourceOriginOption) → SourceHelp.getSource(origin) 取书源对象
  → okHttpClient 请求 → onResponse
  → ImageUtils.skipDecode(source, isCover=true)?  // coverDecodeJs 为空则透传
  → ImageUtils.decode(src, responseBody.byteStream(), isCover=true, source)
      → source.evalJS(coverDecodeJs){ put("result", inputStream) }
      → as ByteArray → ByteArrayInputStream → onStreamReady
```

**正文图片（BookHelp 通道，漫画源/图文正文里的 img）**：
```
BookHelp.saveImages → saveImage → fetchImage
  → AnalyzeUrl(src, source=bookSource).getByteArrayAwait()   // 下载密文
  → ImageUtils.decode(src, bytes, isCover=false, bookSource, book)
      → source.evalJS(ruleContent.imageDecode){ put("result", bytes) } as ByteArray
  → writeImage 落盘
```

### 两个钩子字段的关键差异

| | `coverDecodeJs` | `ruleContent.imageDecode` |
|---|---|---|
| 位置 | **书源 JSON 顶层字段** | `ruleContent` 对象内 |
| result 类型 | **InputStream**（需先读成 byte[]） | **byte[]** |
| 触发场景 | 封面（Glide，含搜索列表/书架/详情页封面） | 正文/漫画图片（下载保存时） |
| 返回要求 | **都必须返回 byte[]**（`evalJS(...) as ByteArray` 强转） | 同左 |
| 误放位置后果 | 放进 `ruleContent` 内会被 GSON **静默丢弃**（ContentRule 无此字段），表现为 imageDecode 在而封面钩子丢失 | 放顶层同理失效 |

### 封面钩子的隐藏前提：sourceOrigin 必须传递

封面走 Glide，钩子触发依赖 `book.getCoverSourceOrigin()` 把书源 URL 传进 Glide options：
- 从书源搜索/发现添加的书：origin 自动正确。
- **换过源的书 / 手动编辑过 URL 的书 / 缓存里 origin 缺失的书**：钩子不触发，表现为"别的书封面正常，就这几本不行"——遇到时先换源重加或检查 `book variable`。
- RSS 源同样支持 `coverDecodeJs`（RssSource 分支）。

### 魔数双保险（强烈推荐标配）

两个钩子开头都做魔数检查，已是合法图片则原样返回。防三种场景：图床部分图片不加密、未来下线加密、调试期间混入的明文缓存：

```js
var b0=(result[0]+256)%256,b1=(result[1]+256)%256,b2=(result[2]+256)%256;
if((b0===255&&b1===216)||(b0===137&&b1===80&&b2===78)||(b0===71&&b1===73&&b2===70)||(b0===82&&b1===73&&b2===70)){
  return result   // JPEG/PNG/GIF/WebP 明文，透传
}
// ...否则走解密
```

`coverDecodeJs` 的 InputStream 版（先读流再判断）：

```js
(function(){
var baos=new Packages.java.io.ByteArrayOutputStream();
var buf=new Packages.java.lang.String('00000000000000000000000000000000').getBytes();
var n=result.read(buf);
while(n>0){baos.write(buf,0,n);n=result.read(buf)}
var enc=baos.toByteArray();
var b0=(enc[0]+256)%256,b1=(enc[1]+256)%256,b2=(enc[2]+256)%256;
if((b0===255&&b1===216)||(b0===137&&b1===80&&b2===78)||(b0===71&&b1===73&&b2===70)||(b0===82&&b1===73&&b2===70)){return enc}
var Cipher=Packages.javax.crypto.Cipher;
var SKS=Packages.javax.crypto.spec.SecretKeySpec;
var IVS=Packages.javax.crypto.spec.IvParameterSpec;
var kb=new Packages.java.lang.String('<KEY>').getBytes('UTF-8');
var vb=new Packages.java.lang.String('<IV>').getBytes('UTF-8');
var c=Cipher.getInstance('AES/CBC/NoPadding');
c.init(Cipher.DECRYPT_MODE,new SKS(kb,'AES'),new IVS(vb));
return c.doFinal(enc);
})()
```

> `ruleContent.imageDecode` 的 result 直接就是 byte[]，省去读流步骤，其余完全同构。
> `ImageUtils.decode` 内部是 `kotlin.runCatching{...}.getOrNull()`——**钩子抛任何异常都静默变 null** → `onStreamReady(null)` → `failUrl.add(url)`（见下节缓存中毒），**没有任何可见报错**。所以钩子 JS 必须防御性编程：所有索引/解析包裹 try/catch，失败时返回原密文（让图正常失败）也比抛异常好——不，抛异常和返回 null 等价；**返回原样 bytes 至少能进"明文检查重试"路径**。

---

## 四、缓存中毒三层机制与"前几张不显示"根因

### 症状特征（极强诊断价值）

> **书源修复（加解密钩子）之后：发现/搜索列表里，先出现的几个封面不显示，后出现的正常显示。**

这不是规则问题、不是密钥问题（后面正常的都解密成功了），而是**修复之前浏览过的头部条目被三层缓存记住了"坏结果"**：

### 三层缓存机制（源码逐条拆解）

**① Glide 磁盘缓存（DiskCacheStrategy.ALL）——密文缓存中毒（主根因）**

`BookCover.load` 的 RequestBuilder 用了 `DiskCacheStrategy.ALL`：**原始密文在网络层就被缓存进 Glide 磁盘**。修复前你浏览列表时，头部条目的封面密文已经写进 Glide 缓存；修复后 Glide 命中缓存**直接用缓存里的密文渲染，不再发起网络请求 → OkHttpStreamFetcher 的解密钩子根本没有执行机会** → 永远解不开。而列表后面的条目是修复后才第一次加载的，走网络→解密→缓存明文→正常。

> 关键：**Glide 缓存的 key 是 URL，缓存的是"数据流的原始字节"（DiskCacheStrategy.ALL 含 DATA 层）**，钩子解密发生在 OkHttpStreamFetcher.onResponse（数据层之后），所以缓存命中时完全绕过钩子。这是设计使然，不是 bug。

**② failUrl 进程级拉黑（OkHttpStreamFetcher companion object）**

```kotlin
companion object {
    private val failUrl = hashSetOf<String>()
}
// onResponse 非 2xx 或 decodeResult==null 时：
if (!manga) failUrl.add(url.toStringUrl())
// loadData 开头：
if (failUrl.contains(url.toStringUrl())) {
    callback.onLoadFailed(NoStackTraceException("跳过加载失败的图片"))
    return   // 本进程内该 URL 永久不再尝试
}
```
修复之前（未配钩子），密文解码为 Bitmap 必然失败 → 该 URL 进拉黑名单 → **即使修复后，只要 App 进程不重启，这些 URL 的封面永远跳过加载**。重启 App 即清空（内存级）。

**③ BookHelp 文件缓存（正文图片/漫画，按书文件夹+MD5键）**

```kotlin
fun getImage(book: Book, src: String): File
    = downloadDir.getFile("book_cache", book.getFolderName(), "images",
        "${MD5Utils.md5Encode16(src)}.${getImageSuffix(src)}")
```
正文图片按 `MD5(url)` 落盘。**特别阴险**：`saveImage` 里 `checkImage(it)` 失败（密文不是合法图）**也照样 writeImage 写盘**（源码注释明说"无论如何都要将数据写入到文件里，避免每次进正文重复请求"）→ 修复前读过的正文图片，磁盘上是密文；修复后 `isImageExist` 直接命中密文文件，不重下载、不触发 `fetchImage` 里的解密钩子。

### 修复手段对照表

| 手段 | 操作 | 清除范围 |
|---|---|---|
| 重启 App | 杀进程重开 | failUrl（内存级） |
| 阅读设置→清除缓存 | "我的"页清缓存/清书缓存 | BookHelp book_cache（正文图），**不含 Glide** |
| 应用详情→清除存储 or Glide 磁盘清理 | 系统设置里清 App 存储 | Glide 磁盘缓存（含密文封面） |
| 书架长按→清缓存 | 单书清理 | 该书 book_cache |
| **规则侧自愈：URL 换查询参数** | coverUrl 拼接 `?v=N` | 三层全部绕过（key 变了） |

### 规则侧自愈方案：查询参数换缓存 key（换版即强制刷新）

多数图床/CDN 忽略未知查询参数（黑料网图床已实测 `?hlcv=2` 返回同样密文）。原理：Glide 缓存 key、failUrl、MD5 文件名全部基于 URL 字符串——**URL 一变，三层缓存全部 miss，强制走网络+钩子**。

coverUrl 规则示例（黑料网 ruleBookInfo.coverUrl 同思路）：

```js
@js:CU((function(){
  var d=J(result);
  var im=d.select('div.xxx img');
  var o=im.size()>0?String(im.first().attr('z-image-loader-url')||''):'';
  // 图片解密版本号：改这个值=全网封面强制重新拉取
  var V='2';
  return o?o+(o.indexOf('?')<0?'?':'&')+'hlcv='+V:'';
})())
```

版本变量可用 `source.get('imgv')` 存书源变量，登录 UI 加个"图片缓存修复"按钮一键升版——升一次版本号，所有封面强制重拉并重解密，旧缓存自然作废被淘汰。

> 注意：查询参数方案的**前提是先用魔数探测验证图床接受参数**（`?v=2` 后返回同样内容且仍 200）。少数严格 CDN 会 404/403 带参数请求，那就只能走清缓存路线。

### "先坏后好"的另一种可能（排除清单）

修复前浏览位置 = 缓存中毒范围，所以症状总表现为"**先出现的（=以前看过的顶部）坏、后出现的（=新条目）好**"。若症状是"随机分布的坏"，另查：
- 换源书/手动改过 URL 的书缺 sourceOrigin（封面钩子不触发）；
- 部分图片真的未加密（魔数双保险可兼容）；
- 图床分域名：不同子域部分加密部分不加密（黑料网 `pic.nsxxlj.cn` 全加密、`hc237`广告图也同域）；
- 限频/UA：429 时 failUrl 拉黑，与加密无关。

---

## 五、完整模板代码

### 5.1 书源 JSON 关键字段（黑料网 v3.3 生产版，可直接抄改）

```jsonc
{
  // ...常规字段省略...
  "header": "{\"User-Agent\": \"Mozilla/5.0 (Linux; Android 14; Pixel 8) ...\"}",
  // 顶层字段：封面解密钩子（result=InputStream）
  "coverDecodeJs": "(function(){var baos=new Packages.java.io.ByteArrayOutputStream();var buf=new Packages.java.lang.String('00000000000000000000000000000000').getBytes();var n=result.read(buf);while(n>0){baos.write(buf,0,n);n=result.read(buf)}var enc=baos.toByteArray();var b0=(enc[0]+256)%256;var b1=(enc[1]+256)%256;var b2=(enc[2]+256)%256;if((b0===255&&b1===216)||(b0===137&&b1===80&&b2===78)||(b0===71&&b1===73&&b2===70)||(b0===82&&b1===73&&b2===70)){return enc}var Cipher=Packages.javax.crypto.Cipher;var SKS=Packages.javax.crypto.spec.SecretKeySpec;var IVS=Packages.javax.crypto.spec.IvParameterSpec;var kb=new Packages.java.lang.String('KEY').getBytes('UTF-8');var vb=new Packages.java.lang.String('IV').getBytes('UTF-8');var c=Cipher.getInstance('AES/CBC/NoPadding');c.init(Cipher.DECRYPT_MODE,new SKS(kb,'AES'),new IVS(vb));return c.doFinal(enc);})()",
  "ruleContent": {
    // ...content 规则正常写，img 输出密文原始URL...
    // 对象内字段：正文图片解密钩子（result=byte[]）
    "imageDecode": "(function(){var b0=(result[0]+256)%256;var b1=(result[1]+256)%256;var b2=(result[2]+256)%256;if((b0===255&&b1===216)||(b0===137&&b1===80&&b2===78)||(b0===71&&b1===73&&b2===70)||(b0===82&&b1===73&&b2===70)){return result}var Cipher=Packages.javax.crypto.Cipher;var SKS=Packages.javax.crypto.spec.SecretKeySpec;var IVS=Packages.javax.crypto.spec.IvParameterSpec;var kb=new Packages.java.lang.String('KEY').getBytes('UTF-8');var vb=new Packages.java.lang.String('IV').getBytes('UTF-8');var c=Cipher.getInstance('AES/CBC/NoPadding');c.init(Cipher.DECRYPT_MODE,new SKS(kb,'AES'),new IVS(vb));return c.doFinal(result);})()"
  }
}
```

### 5.2 懒加载属性兼容链（ruleBookInfo.coverUrl / 正文 img）

加密图床站普遍配合懒加载，真实地址藏在自定义属性，按优先级兜底：
```js
var s=String(im.attr('z-image-loader-url')||im.attr('data-image-zoom')||im.attr('src')||'');
```
常见变体：`data-src` / `data-original` / `data-url` / `z-image-loader-url`。抓详情页时 `curl`/`java.ajax` 拿到的是 SSR 原文（懒加载未执行），属性值完整可取——**这正是无头取数比 WebView 快的原因，也是懒加载+加密双反爬的薄弱点**。

---

## 六、验证清单与调试方法论

1. **密钥单测**（eval_js）：真实密文 + javax.crypto 解密 → 首字节魔数比对 ✓
2. **多时间点取样**：不同上传日期的图各抽 1 张，key 一致性 ✓（确认全局固定 key）
3. **参数接受度测试**（若计划用 ?v= 自愈）：`?hlcv=2` 后仍 200 且密文同长 ✓
4. **debug_source 全链路**：搜索→详情（封面 URL 提取）→正文（img 列表）——debug 不加载图片本体，但可验证 URL 正确性
5. **check_source**：通过后仍要手机实测——**校验器不触发图片下载，封面/正文图片显示必须手机看**
6. **修复后必做**：重启 App（清 failUrl）+ 清图片缓存（见 4.4 对照表）+ 老书刷新目录；**出现"前几张不显示"按第四节排查，十有八九是缓存中毒而不是规则回退**

诊断口诀：**魔数定性质，重启定拉黑，版本参数破缓存，换源重加定 origin**。

---

## 七、避坑清单

1. **coverDecodeJs 必须是顶层字段**——放进 ruleContent 被 GSON 静默丢弃，无任何报错。
2. **两个钩子都必须返回 byte[]**——`evalJS(...) as ByteArray` 强转，返回 InputStream 直接 ClassCastException（封面链）。
3. **byte[] 索引是负数**（Java 有符号 byte），比较前 `(x+256)%256` 归一化。
4. **byte buffer 造法**：`String('0000').getBytes()`；`java.lang.reflect.Array.newInstance` 在此 Rhino 不可用（`newInstance 不是函数`）。
5. **ImageUtils.decode 全程 runCatching**：钩子任何异常 → 静默 null → failUrl 拉黑。钩子内 try/catch 兜底，失败宁可返回原密文。
6. **解密后 contentLength**：`ByteArrayInputStream.available()` 是精确值，Glide 的 ContentLengthInputStream 处理正常；不用管。
7. **key 的两种语义都试**：hex 字符串当 key 原文 getBytes（本例）vs hex 解码后 8 字节。哪个出魔数哪个对。
8. **NoPadding vs PKCS5**：密文 16 整除 → NoPadding；解密后长度略减 → PKCS5。
9. **魔数检查必须放在解密前**，兼容明文/密文混存。
10. **MCP save_source 高密度转义必坏**：钩子 JS 单行压缩、零反斜杠、零内嵌双引号（`String.fromCharCode(34)` 生成引号，单引号包字符串）；手抄两次共出 7 处笔误且 save 回显"已保存"不报错——**必须脚本构建 + node --check 逐块校验 + 保存后 get_source 逐字段回读**。
11. **check_source 报 `Expected URL scheme ... but was 'com.script.ScriptException'`** = 损坏的钩子 JS 执行抛 ScriptException，错误串被 AnalyzeUrl 当 URL 解析——校验报错嵌套进 URL 错误，要还原根因。
12. **failUrl 只拉黑封面通道**（`if (!manga)` 才 add），漫画正文通道不拉黑；但 BookHelp 的密文落盘更隐蔽。
13. **密钥可能轮换**：上线后每隔一段时间用魔数探测抽检一次；轮换了就从最新 image.js 重新提取，换 key 即换缓存版本号 ?v=N 一并强制刷新。
14. **别把 query 参数方案用于正文图片**：正文走 BookHelp 的 MD5(url) 文件名，换 URL = 旧缓存文件永远不删（占空间）；封面换版 OK，正文老老实实清缓存。
15. **R8 混淆后反射不可靠**：`Class.forName("io.legado.app.utils.ImageUtils")` 等被封；以 GitHub 源码为准（gedoor/legado 已空仓库，现役主仓库是 LegadoTeam/legado，default=master）。

---

## 八、已知样本档案

### pic.nsxxlj.cn（黑料网图床，2026-09 实测）
- 算法：`AES-128-CBC/NoPadding`，key=`f5d965df75336270`，iv=`97b60394abc2fbe1`（均为 UTF-8 bytes 直接作 key/iv，非 hex 解码）
- 密钥来源：`/static/v4/__base/js/image.js`（280KB）内 `cc("102_53_100_...")` 字符码混淆；全站全局固定（2026-02 旧图同 key）
- 密文特征：PNG 密文首字节 `dd e2 8c 47`，JPEG 密文首字节不定（`4f e8 97`/`10 2f e8`/`3e aa 70` 均见）；`Content-Type: binary/octet-stream`
- 懒加载属性：`z-image-loader-url`（真图）/`data-image-zoom`/`src`（占位）
- 图床接受任意查询参数（`?hlcv=2` 同样内容）→ ?v= 自愈方案可用
- 书源：黑料网 hlwf6.com v3.3（LegadoTeam 版，双钩子 + 魔数双保险）
- 成品备份：`/workspace/hlwf6/hlwf6_v33.json`、`hlwf6_v33_one.json`

### 套路对照表（持续积累）
| 站点 | 算法 | key 藏法 | 备注 |
|---|---|---|---|
| 黑料网 pic.nsxxlj.cn | AES-128-CBC NoPadding | 字符码数组混淆（image.js） | 全局固定 key |
| （待积累） | | | |

---

*本方法论文档由黑料网书源实战沉淀，欢迎后续站点按第八节样本档案格式补充。*
