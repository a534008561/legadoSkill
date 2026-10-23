# 方法：目录分页 nextTocUrl 只返回单 URL 的源码级机制

> 适用场景：目录分页的书源，尤其是**短篇小说（目录只有 2~3 页）**和**长篇连载（几十页）**都要覆盖的书源。
>
> 结论先行：**`nextTocUrl` 一次只返回「下一页」1 个 URL，末页返回 `null`**。这是唯一能保证目录顺序正确的写法。

---

## 1. 源码级机制（BookChapterList.kt）

Legado 对 `nextTocUrl` 的处理分两条互斥分支，判据是**第 1 页求值出的 URL 个数**：

```kotlin
chapterList.addAll(chapterData.first)   // 第 1 页章节
when (chapterData.second.size) {
    0 -> Unit
    1 -> {                            // ★串行分支
        var nextUrl = chapterData.second[0]
        while (nextUrl.isNotEmpty() && !nextUrlList.contains(nextUrl)) {
            nextUrlList.add(nextUrl)
            val res = analyzeUrl.getStrResponseAwait()   // 串行请求
            res.body?.let { nextBody ->
                chapterData = analyzeChapterList(...)    // 会再求值一次 nextTocUrl
                nextUrl = chapterData.second.firstOrNull() ?: ""
                chapterList.addAll(chapterData.first)
            }
        }
        Debug.log(..., "◇目录总页数:${nextUrlList.size}")
    }
    else -> {                         // ★并发分支
        Debug.log(..., "◇并发解析目录,总页数:${chapterData.second.size}")
        flow { for (urlStr in chapterData.second) emit(urlStr) }
            .mapAsync(AppConfig.threadCount) { urlStr ->
                val res = analyzeUrl.getStrResponseAwait()
                // ★注意：getNextUrl = false，后续页不会再求值 nextTocUrl
                analyzeChapterList(..., getNextUrl = false, ...).first
            }
            .collect { chapterList.addAll(it) }
    }
}
```

三个必须记住的事实：

| # | 事实 | 影响 |
|---|---|---|
| ① | **只有 1 个 URL 走串行**，≥2 个走并发 | 分支完全由第 1 页的返回值个数决定 |
| ② | 并发分支用 `mapAsync` + `buffer(0)` + 信号量，**按完成顺序 emit** | 章节顺序不可控，长书必然乱序 |
| ③ | 并发分支 `getNextUrl=false`，**不会**用后续页的返回值；串行分支会 | 两边的翻页责任不同 |

`mapAsync` 的实现（`FlowExtensions.kt`）确认了乱序根因：

```kotlin
inline fun <T, R> Flow<T>.mapAsync(concurrency: Int, transform: suspend (T) -> R): Flow<R> =
    if (concurrency == 1) map { transform(it) }
    else Semaphore(concurrency).let { semaphore ->
        channelFlow {
            collect { semaphore.acquire(); send(async { transform(it) }) }
        }.map { it.await() }            // ← 谁先 await 完谁先 emit
         .onEach { semaphore.release() }
    }.buffer(0)                          // ← 无缓冲，无序重排
```

---

## 2. 为什么「一次返回全部页」是错的

这是最容易踩的坑。假设站点共 Y 页，`nextTocUrl` 一次返回 `[2,3,...,Y]`：

### 2.1 长篇书（Y ≥ 3）：并发乱序

第 1 页返回 Y-1 个 URL → 走**并发**分支。`collect { chapterList.addAll(it) }` 按**网络完成顺序**追加。

实测案例：桔纸书屋《完美世界》49 页，一次返回 48 个 URL，模拟结果——

```
抓取页数=81（期望 49）  每页章节数=45,45,45,45,45…45
总章节=3602  重复=1440
章节号范围=46987112~50308125
```

（`guard` 累加是因为模拟脚本自己也按后续页返回值翻页，App 里虽只请求 48 个 URL，但**顺序仍按完成时间**，首章常不是第一章。）

### 2.2 短篇书（Y = 2）：重复抓取 + 顺序轮转

第 1 页只返回 1 个 URL（`[2]`）→ **仍走串行分支**。于是：

1. 第 1 页：45 章 + nextTocUrl → `[page2]`
2. page2：28 章 + nextTocUrl → **又返回 page1**（因为 page2 的推算逻辑也是「除自己以外的所有页」）
3. `nextUrlList` 已含 page2，不含 page1 → `page1` 不在黑名单 → **page1 被再抓一次**

最终 `chapterList = [P1, P2, P1]`，经源码末尾的处理：

```kotlin
chapterList.reverse()              // [P1, P2, P1] → [P1', P2', P1']
val lh = LinkedHashSet(chapterList) // 去重保留首个 → [P1', P2']（注意是逆序的 P1）
val list = ArrayList(lh)
if (!book.getReverseToc()) list.reverse()  // → [P2', P1']
```

**顺序被轮转成「第 46 章 ~ 上架感言, 第 1 章 ~ 第 45 章」**。

模拟验证：

```
无重复:   first=1  last=73 len=73
重复page1: first=46 last=45 len=73  前5=46,47,48,49,50
```

与 App 实测现象完全吻合：目录总数仍是 73，但首章变成「第四十六章」。

---

## 3. 正确写法

```js
@js:(function(){
  var m = String(result).match(/当前第\s*(\d+)\s*页[，,]\s*共\s*(\d+)\s*页/);
  if(!m) return null;
  var cur = parseInt(m[1]), total = parseInt(m[2]);
  if (cur >= total) return null;              // ★末页必须终止
  var bm = String(baseUrl).match(/^(https?:\/\/[^\/]+)\/xs\/(\d+)/);
  if(!bm) return null;
  return [bm[1]+'/xs/'+bm[2]+'/'+(cur+1)+'/']; // ★只返回下一页
})()
```

四个要点：

| 要点 | 原因 |
|---|---|
| 只返回 1 个 URL | 强制走串行分支，顺序绝对可控 |
| 末页 `return null` | 终止串行 while 循环，避免回环 |
| 从 `baseUrl` 提 bookId | 站点 URL 常被归一化/改写，`replace(/\/\d+\/?$/,'')` 会把 bookId 一起删掉 |
| 返回值是**数组** | 源码 `chapterData.second[0]` / `firstOrNull()`，字符串也能工作但数组更稳 |

---

## 4. 排查 Checklist

遇到「目录顺序错 / 章节缺失 / 章节重复 / 首章不对」，按此顺序查：

1. **看日志分支标记**
   - `◇目录总页数:N` → 串行分支（`nextTocUrl` 第 1 页返回 1 个）
   - `◇并发解析目录,总页数:N` → 并发分支（返回 ≥2 个）
   - **并发分支 = 顺序不可控，必须改成单 URL**

2. **核对「目录总页数」与站点实际页数**
   - 短篇 2 页却显示 `3` → 末页没返回 null，发生了回环重复抓取

3. **核对「目录总数」与站点章节数**
   - 数量偏多 → 有页被重复抓取
   - 数量偏少 → 某页请求失败被跳过

4. **末页单独求值 `nextTocUrl`**
   ```js
   // 用 eval_js 单独跑末页，必须返回 null
   ```

5. **dump 全量目录比对单调性**
   ```js
   var nums = all.map(x => parseInt(x.h.match(/\/(\d+)\.html$/)[1]));
   var mono = all.every((x,i) => i===0 || nums[i] > nums[i-1]);
   ```

---

## 5. 常见站点分页条文案

不同模板的页码文案不同，正则需适配：

| 站点模板 | 文案 | 正则 |
|---|---|---|
| jieqiCMS（桔纸书屋） | `当前第1页，共2页，每页显示45章 【1】 2` | `/当前第\s*(\d+)\s*页[，,]\s*共\s*(\d+)\s*页/` |
| 部分模板 | `第1/2页` | `/第\s*(\d+)\s*\/\s*(\d+)\s*页/` |
| 部分模板 | `1/2` | `/^\s*(\d+)\s*\/\s*(\d+)\s*$/` |

注意 `[，,]` 要同时兼容中英文逗号。

---

## 6. 延伸：为什么不用 `nextContentUrl` 解决正文分页

同理，正文章内分页（`a.btn-info` 类下一页链接）也建议在 `@js` 里自己按页抓取：

- `nextContentUrl` 是 URL 类规则，**必须返回字符串或 `null`**，返回数组/对象会静默失败
- 站点常按字数硬截断，跨页会切断句子甚至切断 `&nbsp;` 实体，需要自己拼接修复
- 部分站点把整章重复输出多份，需要标记判据去重

详见「方法-正文跨页重复输出与整页去重.md」。

---

## 7. 一句话总结

> **`nextTocUrl` 永远只返回「下一页」1 个 URL，末页返回 `null`。** 一次返回多个 URL 时，长篇走并发分支会乱序，短篇走串行分支会回环重复抓取导致顺序轮转。这是源码 `when(nextUrlList.size)` 结构决定的，与站点无关。
