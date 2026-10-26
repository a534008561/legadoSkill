# 方法：封面解密钩子（coverDecodeJs）返回值类型与三层缓存中毒

> 沉淀日期：2026-10-27　｜　来源：黄果短剧 v8.x 封面排查（AI短剧站，AES-128-CBC 加密图）
> 症状：列表封面全部不显示，但 HTTP 日志显示图片请求全部 200。

---

## 0 结论速查

| 现象 | 根因 | 处置 |
| --- | --- | --- |
| 钩子探针文件永不出现 | Glide `DiskCacheStrategy.ALL` 缓存了**密文**，命中缓存不再发网络请求 → 钩子无执行机会 | coverUrl 拼 `?v=N` 换缓存 key |
| 钩子探针文件永不出现（换 key 后仍不出现） | `failUrl` 进程级拉黑：修复前密文解码失败 → URL 进黑名单 → 本进程永久跳过 | **重启 App**（内存级）清 failUrl |
| 钩子执行了但封面仍不显示 | 返回 JS 数组字面量 → Rhino `NativeArray`（非 `Wrapper`）→ Kotlin `as ByteArray` 强转失败 | **返回 Java `byte[]`**：`Packages.java.util.Arrays.copyOf(dec, n)` |
| 详情页封面正常、列表封面不显示 | `persistedCoverUrl` 非空 → `getCoverSourceOrigin()` 返回 null | 清除自定义封面 |

---

## 1 ★ 返回类型必须是 Java `byte[]`（最隐蔽的坑）

`legado_src/modules/rhino/src/main/java/com/script/rhino/RhinoScriptEngine.kt:235`

```kotlin
fun unwrapReturnValue(result: Any?): Any? {
    var result1 = result
    if (result1 is Wrapper) result1 = result1.unwrap()   // ← 只 unwrap Wrapper
    if (result1 is ConsString) result1 = result1.toString()
    return if (result1 is Undefined) null else result1
}
```

| JS 返回值 | Rhino 类型 | `unwrap` 后 | Kotlin `as ByteArray` |
| --- | --- | --- | --- |
| `Packages.java.util.Arrays.copyOf(dec, n)` | `NativeJavaArray`（**是 Wrapper**） | 真实 `byte[]` | ✅ 成功 |
| `new byte[]{...}` | `NativeJavaArray` | 真实 `byte[]` | ✅ 成功 |
| `[1,2,3,...]`（JS 数组字面量） | `NativeArray`（**不是 Wrapper**） | `NativeArray` | ❌ **ClassCastException** |

失败链路（**全程无任何可见报错**）：

```
ImageUtils.decode → kotlin.runCatching { evalJS(...) as ByteArray }
                     .onFailure { AppLog.putDebug("解密错误", it) }   // 仅 DEBUG 日志
                     .getOrNull() → null
→ onStreamReady(null) → failUrl.add(url) + onLoadFailed("封面二次解密失败")
→ 该 URL 本进程内永久跳过
```

`ImageUtils.decode` 源码（`utils/ImageUtils.kt`）：

```kotlin
fun decode(src: String, inputStream: InputStream, isCover: Boolean, source: BaseSource?, book: Book?): InputStream? {
    val ruleJs = getRuleJs(source, isCover)
    if (ruleJs.isNullOrBlank()) return inputStream
    return kotlin.runCatching {
        val bytes = source?.evalJS(ruleJs) { put("result", inputStream) } as ByteArray
        ByteArrayInputStream(bytes)
    }.onFailure { AppLog.putDebug("${src}解密错误", it) }.getOrNull()
}
```

**正确模板（coverDecodeJs，InputStream 版）**：

```js
(function(){
try{
var baos=new Packages.java.io.ByteArrayOutputStream();
var buf=new Packages.java.lang.String('00000000000000000000000000000000').getBytes();
var n=result.read(buf);
while(n>0){baos.write(buf,0,n);n=result.read(buf)}
var enc=baos.toByteArray();
if(!enc||enc.length<32)return enc;
// ★ 魔数双保险：已是明文图则原样返回
var b0=(enc[0]+256)%256,b1=(enc[1]+256)%256,b2=(enc[2]+256)%256;
if((b0===255&&b1===216)||(b0===137&&b1===80&&b2===78)||(b0===71&&b1===73&&b2===70)||(b0===82&&b1===73&&b2===70))return enc;
if(enc.length%16!==0)return enc;
var Cipher=Packages.javax.crypto.Cipher;
var SKS=Packages.javax.crypto.spec.SecretKeySpec;
var IVS=Packages.javax.crypto.spec.IvParameterSpec;
var c=Cipher.getInstance('AES/CBC/NoPadding');
c.init(Cipher.DECRYPT_MODE,new SKS(new Packages.java.lang.String('<KEY>').getBytes('UTF-8'),'AES'),new IVS(new Packages.java.lang.String('<IV>').getBytes('UTF-8'))));
var dec=c.doFinal(enc);
if(!dec||dec.length<32)return enc;
// ★ NoPadding 解密后尾部有垃圾字节（原文非 16 倍数）→ 找 FFD9 截断
var eoi=-1;
for(var i=dec.length-2;i>0;i--){
  if((dec[i]+256)%256===255&&(dec[i+1]+256)%256===217){eoi=i;break}
}
if(eoi>0&&eoi+2<dec.length)return Packages.java.util.Arrays.copyOf(dec,eoi+2);
return dec;
}catch(e){return null}
})()
```

> ⚠️ 循环里 `dec[i]` 是**有符号 byte**，必须写 `(dec[i]+256)%256`。

---

## 2 三层缓存中毒（钩子不执行的原因）

`help/glide/OkHttpStreamFetcher.kt` 链路：

```
loadData → failUrl.contains(url) ? 直接 onLoadFailed("跳过加载失败的图片") : ...
onResponse → ImageUtils.skipDecode(source, !manga) ? 直接透传 : Coroutine.async { ImageUtils.decode(...) }
onStreamReady(null) → failUrl.add(url) + onLoadFailed("封面二次解密失败")
```

| 层 | 机制 | 清除手段 |
| --- | --- | --- |
| ① Glide 磁盘缓存 | `DiskCacheStrategy.ALL` 把**密文**写进缓存；命中缓存直接用密文渲染，不再发网络请求 → 钩子无机会 | coverUrl 拼 `?v=N` 换 key（key 基于 URL 字符串） |
| ② `failUrl` 拉黑 | `companion object { private val failUrl = hashSetOf<String>() }`，进程级，URL 永久跳过 | **重启 App** |
| ③ BookHelp 文件缓存 | 正文图按 `MD5(url)` 落盘，失败也写盘 | 清缓存/换 URL |

**换 key 的前提**：图床/CDN 接受未知查询参数。实测（黄果 pic.drleao.cn）：加 `&v=2` / `&v=9` / `&hgimgv=1` 后长度与魔数完全一致（196816 / `[79,232]`），参数被忽略。

---

## 3 `sourceOrigin` 传递链（为什么列表封面钩子不触发）

```
CoverImageView.load(searchBook, ...)            // ui/book/search/SearchAdapter.kt:93
  → load(path, name, author, loadOnlyWifi, sourceOrigin = searchBook.origin, ...)
    → if (sourceOrigin != null) options.set(OkHttpModelLoader.sourceOriginOption, sourceOrigin)
      → OkHttpStreamFetcher.loadData: options.get(sourceOriginOption)?.let { source = SourceHelp.getSource(it) }
        → ImageUtils.skipDecode(source, isCover)   // source 为 null → true → 密文直接透传！
```

**危险点**：`sourceOrigin == null` 时**不报错**，只是不解密 → Glide 拿到密文 → 解码失败 → 表现同样是「封面不显示」。

`sourceOrigin` 为 null 的两种情况：

```kotlin
// data/entities/Book.kt:179
fun getCoverSourceOrigin() = if (persistedCoverUrl.isNullOrEmpty()) {
    coverSourceOrigin(origin, customCoverUrl)
} else {
    null          // ★ persistedCoverUrl 非空（用户手动换封面）→ null
}
```

- `persistedCoverUrl` 非空（用户改过封面）
- `customCoverUrl` 与 `origin` 不同源

**搜索/发现列表走 `searchBook.origin`（= `bookSource.bookSourceUrl`），正常有值**；
**详情页/书架走 `book.getCoverSourceOrigin()`，可能被自定义封面影响**。

---

## 4 data: URI 路线在封面场景不可用

`help/glide/LegadoDataUrlLoader.kt`：

```kotlin
override fun buildLoadData(...): ModelLoader.LoadData<InputStream>? {
    if (options.get(OkHttpModelLoader.mangaOption) == false) return null
    // ↑ 非漫画场景直接放弃 → data: URI 走 Glide 默认 String loader → 失败
```

⇒ 规则侧「下载→解密→base64→`data:image/jpeg;base64,...`」**只对漫画正文图片有效**，封面无效。

（base64 编码用 `Packages.android.util.Base64.encodeToString(bytes, Packages.android.util.Base64.NO_WRAP)`；
`java.base64Encode(str)` 收的是 **String 不是 byte[]**，传数组会得到错误结果。）

---

## 5 排查手册（按顺序）

```
1. 查 HTTP 日志有没有对图床的请求
   ├─ 没有 → URL 没提取到（规则问题）
   └─ 有且 200 → 继续第 2 步
2. 写探针版 coverDecodeJs（每次被调用就写文件）
   钩子文件出现 → 钩子执行 → 问题在返回值类型/解密逻辑
   钩子文件不出现 → 继续第 3 步
3. 换 URL 缓存 key（&v=N）
   还不行 → failUrl 拉黑 → ★重启 App★
4. 钩子执行了但仍不显示 → 检查返回值类型
   必须是 Java byte[]（Arrays.copyOf），不能是 JS 数组字面量
5. 对照实验：coverUrl 指向站点自己的明文 PNG + coverDecodeJs 置空
   显示 → Glide 通道正常，问题在加密
   不显示 → Glide/钩子链路问题
```

---

## 6 沙盒为什么测不出来

`eval_js` 环境里 `java.get(url).bodyStream()` 能读出完整密文、AES 能解出 `FFD8` 开头、截断后尾部是标准 `FFD9` —— **一切正确**。

但沙盒**无法验证**：

- Rhino 返回值到 Kotlin `as ByteArray` 的强转（沙盒能写数组也能过 `ByteArrayOutputStream.write`，但那不等于 Kotlin 的 `instanceof byte[]`）
- Glide 缓存 / failUrl 拉黑状态

⇒ **封面类问题必须手机侧实测**，沙盒通过不代表显示。

---

## 7 关联

- `方法-图床AES加密图片解密.md`：魔数双保险、三层缓存总览
- `方法-图片不显示排查总表-加密之外的三条路.md`：四象限归因、换主机、data 内置

---

## 8 多结构站点合并进单个书源（黄果 v9.0 实例）

用户要求「不要分成两个书源」时，**同一站点存在 2~3 种列表结构**的合并做法：

### 8.1 三容器隔离矩阵（先量，后写）

| 页面 | `.hg-card-grid .hg-drama-card` | `.hg-rank-item` | `.hg-topic-grid .hg-topic-card` |
| --- | --- | --- | --- |
| 分类页 | 85 | 0 | 0 |
| 排行榜 | 0 | 20 | 0 |
| 专题详情页 | 24 | 0 | 4（相关推荐） |
| 专题列表页 | 0 | 0 | 9 |

⇒ 在 `.hg-list-page` 之后三容器**互不重叠**，可安全放进同一个多选 `bookList`。

### 8.2 前提：字段级选择器在多选 bookList 下会失效

```css
bookList = .a, .b
name = .a__title, .b__title      /* ← 返回空 / 索引错位 */
```

实测 `name` 返回空字符串、`书籍总数:0`。**根因**：多选择器的元素集合与字段选择器**不按索引对应**。

⇒ **所有字段必须统一 `@js:` 自解析**，从整卡 HTML 用**该结构专属锚点**取值：

```js
// 三种结构共存时的 name 字段范式
@js:
(function(){
var h=String(result);
var m=h.match(/data-track-title="([^"]*)"/);        // ① 作品卡
if(m)return m[1];
var tp=h.match(/class="hg-topic-card__title">([^<]+)</);  // ② 专题卡
if(tp)return tp[1].trim();
var a=h.match(/class="hg-drama-card__title"[^>]*>[\s\S]*?<a[^>]*>([\s\S]*?)<\/a>/)
     ||h.match(/class="hg-rank-item__title"[^>]*>[\s\S]*?<a[^>]*>([\s\S]*?)<\/a>/);
if(a)return a[1].replace(/<[^>]*>/g,'').trim();       // ③ 排行榜卡
return '';
})()
```

### 8.3 bookUrl 必须按结构分流

同一份 `bookUrl` 规则要同时吐出 `/video/N/` 与 `/topics/xxx/`：

```js
var tp=h.match(/href="(\/topics\/[a-zA-Z0-9\-]+\/)"/);
if(tp)return root+tp[1];
var mv=h.match(/href="(\/video\/\d+\/)"/);
if(mv)return root+mv[1];
```

### 8.4 ruleBookInfo / ruleToc 双结构兼容

同一书源里「视频页」和「专题页」是两种详情页：

| | 视频页 `/video/N/` | 专题页 `/topics/xxx/` |
| --- | --- | --- |
| 标题 | `<h1 class="hg-web-play__title">` | `<h1>`（带「介绍」后缀） |
| 集数 | `data-track-total-episode="33"` | 无 |
| 章节 | 按集数生成 `/video/N/ep-K/` | 把专题内 24 个视频作为章节 |

`ruleToc.chapterList` 用**特征判据分流**：

```js
var m=h.match(/data-track-total-episode="(\d+)"/);
if(m){ /* 视频页：按集数 */ }
// 否则：专题页 → 抓页内 data-track-title + /video/N/ 作为章节
```

### 8.5 容器后缀限定是「去重」也是「提纯」

分类页 `.hg-drama-card` 有 84 个（4 个 tab 面板各 21 个），加 `.hg-card-grid` 限定后只取当前 tab 的 21 个 —— 既是去重也是**语义正确**（原本 84 本是 4 个 tab 混在一起的假象）。

### 8.6 合并后的残留：相关推荐

专题详情页会额外命中同容器的「相关推荐」专题卡（4 个）。**这不是 bug**：它们同样是专题卡，`bookUrl` 指向专题页，章节 = 该专题内视频，行为一致。若要排除需用父级 class 区分（`.hg-topic-related` vs `.hg-topic-grid`）。
