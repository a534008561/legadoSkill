# 方法：AES 图片解密后的 `FFD9` 截断 + 站点假分页陷阱

> 沉淀来源：黄果短剧 v6（2026-10-27）。两个 bug 都是「看起来成功了其实没成功」型：
> 解密后魔数正确但封面仍不显示；分页参数写对格式但站点忽略。

---

## 一、AES-CBC-NoPadding 解密后必须截断到 `FFD9`

### 1.1 症状

`coverDecodeJs` 解密后：

```
decMagic=[255,216,255]   ← SOI 正确！
isJPEG=true
```

**但封面还是不显示**。

### 1.2 实锤：尾部有垃圾字节

```
decLen=196816
lastEOI=196807          ← 真正的 JPEG 结束标记位置
trailing=7              ← EOI 之后还有 7 字节
trailingAllZero=false   ← 且不是零填充
```

**根因**：服务端加密时把原图**填充到 16 的倍数**（`196816 % 16 === 0` 是填充后的结果，
不是原图长度）。`NoPadding` 解密把填充字节一起解出来 → `FFD9` 之后残留垃圾 →
Glide 的 `BitmapFactory.decodeStream` 读到非法尾部 → **解码失败**。

### 1.3 修法：`Arrays.copyOf` 截断

```javascript
var eoi=-1;
for(var i=dec.length-2;i>0;i--){
  if((dec[i]+256)%256===255&&(dec[i+1]+256)%256===217){eoi=i;break}
}
if(eoi>0&&eoi+2<dec.length) return Packages.java.util.Arrays.copyOf(dec,eoi+2);
return dec;
```

**验证**：`trimLen=196809`（= eoi+2）、`head=[255,216,255]`、`tail=[255,217]`。

### 1.4 两个 Rhino 坑

| 写法 | 结果 |
| --- | --- |
| `new Packages.java.lang.reflect.Array.newInstance(Byte.TYPE, n)` | ❌ `[JavaPackage ...] 不是函数，它是 object` |
| `Packages.java.util.Arrays.copyOf(dec, n)` | ✅ |

`java.lang.reflect.Array.newInstance` 是**反射构造器**，不是普通静态方法，Rhino 不认。
要用 `java.util.Arrays.copyOf`。

> JS 数组下标取值必须 `(dec[i]+256)%256`——Rhino 的 Java byte[] 是**有符号**的，
> `0xFF` 会变成 `-1`。

---

## 二、站点假分页：格式对但参数被忽略

### 2.1 症状

`exploreUrl` 写了 `/ai-duanju/page/{{page}}/`，翻页后**每页内容一样**。

### 2.2 根因：分页 URL 格式猜错

站点真实格式是 `/ai-duanju/{{page}}/`，`/page/N/` 被**静默忽略**——
服务端不报错，直接返回第 1 页 SSR 数据。

**实锤方法**：从页面 HTML 里挖分页条，不要猜。

```javascript
var m = h.match(/href="([^"]*(?:page|p|\?)[^"]*)"/g);        // 分页链接
var m3 = h.match(/data-page[^=]*="[^"]*"/g);                  // data-page / data-pages
```

本站结果：

```html
<div class="hg-list-page" data-page="1" data-pages="62">
  <a href="https://l205.arj2ftl0.cc/ai-duanju/2/">   ← 真实格式，无 page 段
```

### 2.3 验证分页是否真生效（必做）

不能只看 `列表大小`——**每页卡片数可能碰巧相同**。要比**唯一 ID 集合**：

```javascript
function probe(u){
  var h=String(java.ajax(u));
  var m=h.match(/data-page="(\d+)"/);
  var ids=(h.match(/\/video\/(\d+)\//g)||[]);
  var uniq=Array.from(new Set(ids));
  return {page:m?m[1]:'?', uniqIds:uniq.length, first3:uniq.slice(0,3)};
}
```

本站实测：

| URL | data-page | 唯一 ID | 前3个 ID |
| --- | --- | --- | --- |
| `/ai-duanju/` | 1 | 64 | 10492, 10481, 10449 |
| `/ai-duanju/2/` | 2 | 82 | 10355, 10351, 10346 |
| `/ai-duanju/3/` | 3 | 89 | 10167, 10159, 10154 |

**判据**：`data-page` 递增 **且** `first3` 不同 ⇒ 分页真生效。
只有 `data-page` 变但 ID 不变 ⇒ 假分页。

> ⚠️ **置顶推荐会干扰**：本站每页首条都是「疯狂小杨哥」（置顶），
> 不能因为首条相同就判定假分页，要看**第 2、3 条**或唯一 ID 总数。

---

## 三、通用 Checklist

### AES 图片解密

```
[ ] 解密后检查 lastEOI 与 trailing 字节
[ ] trailing > 0 且非零 ⇒ 必须 Arrays.copyOf 截断
[ ] 用 java.util.Arrays.copyOf，不要用 reflect.Array.newInstance
[ ] byte[] 取值一律 (b[i]+256)%256
[ ] 截断后 head=FFD8FF、tail=FFD9 双验证
```

### 分页

```
[ ] 从页面挖真实分页链接，不猜格式
[ ] 读 data-page / data-pages 拿当前页与总页数
[ ] 对比唯一 ID 集合（不是列表大小）
[ ] 排除置顶项干扰（看第 2、3 条）
[ ] 每个入口分别验证（不同入口格式可能不同）
```

---

## 四、关联

- `方法-站点自带crypto-image插件的AES图片解密.md`：密钥位置与 `coverDecodeJs` 基础写法
- `方法-图床AES加密图片解密.md`：`coverDecodeJs` / `imageDecode` 双钩子触发链路
