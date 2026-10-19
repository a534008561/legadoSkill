# 方法：legado-E 列表条目必须 JSON 字符串化（`$.键` 取不到值的根因）

## 一句话

**legado-E 的 `AnalyzeRule.getString` 在条目是 `NativeObject` 时，只有「键值直接访问」一条路，没有 `Mode.Json` 分支。**
所以列表/目录规则返回 **JS 对象数组** 时，字段规则 `$.n` 会被当成属性名直取 -> `undefined`
-> `BookList.getSearchItem` 因书名为空而 `return null` -> **整条被丢弃**。

表现就是用户看到的现象：

- 搜索：**「列表大小:40」有数字，但书名/封面/简介全空**（总数最后也为 0 或只剩少数）
- 发现：**列表直接为空**

> 这是本源 v1.6→v1.7 修复的真实故障，不是推测。

## 故障机理（两版源码对照，真实差异）

### LT 版 `AnalyzeRule.getString`（`/workspace/legado_src/app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt:325`）

```kotlin
if (result is NativeObject) {
    result = when {
        sourceRule.mode == Mode.Js   -> evalJS(sourceRule.rule, result)
        sourceRule.mode == Mode.Json -> getAnalyzeByJSonPath(result).getString(sourceRule.rule)  // ✅ 有
        sourceRule.getParamSize() > 1 -> sourceRule.rule
        else -> result[sourceRule.rule]
    }?.let { replaceRegex(it.toString(), sourceRule) }
}
```

### E 版（`Luoyacheng/legado-E`, `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt:311`）

```kotlin
if (result is NativeObject) {
    result = if (sourceRule.getParamSize() > 1) {
        sourceRule.rule                       // get {{}}
    } else {
        result[sourceRule.rule]?.toString()   // ❌ 只有键值直接访问，没有 Mode.Json
    }?.let { replaceRegex(it, sourceRule) }
}
```

`$.n` 这个字符串被当作 JS 对象的属性名去取，对象里当然没有名为 `$.n` 的属性 -> `undefined`。

### 丢弃发生在哪里

`BookList.getSearchItem`：

```kotlin
searchBook.name = BookHelp.formatBookName(analyzeRule.getString(ruleName))
if (searchBook.name.isNotEmpty()) { /* 只有书名非空才继续取其余字段并入列表 */ }
return null   // 书名空 -> 整条丢弃
```

所以「列表大小」来自 `getElements().size`（**这一步是正常的，所以有数字**），
而「书籍总数」来自成功构造的条目数（**全被丢弃，所以是 0/空**）——两处数字不一致就是这个 bug 的指纹。

## 修法（一次改好，两版通用）

**列表/目录的 `@js:` 规则，每个条目返回 JSON 字符串，而不是 JS 对象。**

```js
// ❌ 旧写法：条目是 JS 对象 -> E 版取不到
out.push({n:name, u:href, c:cover, m:meta, k:cat});

// ✅ 新写法：条目是 JSON 字符串 -> 两版都走 JsonPath
out.push(String(JSON.stringify({n:name, u:href, c:cover, m:meta, k:cat})));
```

字段规则保持 `$.n` / `$.u` / `$.c` 不变。

**为什么这样两版都通：**

- 条目不再是 `NativeObject`，两版都会落到 `else` 分支 -> `Mode.Json` -> `JsonPath("$.n")`
- LT 版走 `getAnalyzeByJSonPath(result).getString(rule)` ✅
- E 版走 `Mode.Json -> getAnalyzeByJSonPath(result).getString(rule)` ✅

适用范围：`ruleSearch.bookList`、`ruleExplore.bookList`、`ruleToc.chapterList`
（**目录同样要改**，否则章节名/链接也会全空）。

## 实测验证（真机 Rhino，不是推断）

```js
var o={n:'射雕外传6卷桃花绿福', u:'/voddetail/28106.html'};

o['$.n']                                   // undefined      ← E 版旧写法（NativeObject 键值直取）
JsonPath.read(JSON.stringify(o), '$.n')    // '射雕外传...'   ← 新写法（JSON 字符串）
new AnalyzeRule().setContent(JSON.stringify(o)).getString('$.n')  // '射雕外传...'  ← LT 版也通
```

三条结果同时成立，才敢改。

## 排查清单（下次遇到「有列表大小、无书名」）

1. **先看两处数字**：debug 里 `列表大小` 有值、`书籍总数` 为 0/少 -> 就是条目被整条丢弃（不是解析出 0 条）。
2. **确认字段规则是 `$.键`** 而不是 `@js:`（`@js:` 在两版都能 eval，不会踩这个坑）。
3. **确认条目类型**：`typeof arr[0]` 是 `object` 就危险，必须是 `string`。
4. **不要改字段规则去迁就**（比如把 `$.n` 改成 `n`）——那在 LT 版会退化成键值直取，能取到但不通用；
   正解是**改条目为 JSON 字符串**，字段规则不动。
5. 改完必须 `node --check` 每个 JS 块，并回读 App 内存储确认落库。

## 附带修掉的一处 E 版 API 差异

登录面板里原来写：

```js
java.get('https://hd.huadudm.com/', null, 20000)   // ❌ E 版 headers 参数是 Map<String,String>，不接受 null
```

E 版签名：`fun get(urlStr: String, headers: Map<String, String>, timeout: Int?)`。
两版通用的带超时 GET 是：

```js
var r = java.connect('https://hd.huadudm.com/', null, 20000);   // ✅ 返回 StrResponse
var body = '';
try { body = String(r.body()); } catch(e) { try { body = String(r.body); } catch(e2){ body=''; } }
```

（`connect(url, headerJson, callTimeout)` 两版都有；`body` 在部分版本是属性、部分版本是方法，双通道取。）
实测：`connect 通道: ok=true 耗时=501ms 字节=190639`。

## 结论（通用铁律）

> **跨 LegadoTeam / legado-E 分发书源时，列表与目录的条目一律返回 JSON 字符串数组，字段规则用 `$.键`。**
> 这条能同时满足两版，且不需要为某一版写分支。

相关已记忆事实：LT 版 `getElements` 只接受 `List` / `Array` / `NativeArray`，**字符串返回值会得到空列表**
——所以是「**逐个条目 JSON 字符串化**」，不是「整个数组 JSON.stringify」。两者别混淆。
