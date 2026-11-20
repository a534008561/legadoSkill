# 方法：getElements 返回类型 / TocRule 字段名双坑与 XOR-Inflate 二进制正文解密

> 来源：2026-11-20 制作「爱看书免费小说」(com.mianfeia.book v8.2.7, cread.com 家族) API 书源。
> 三个坑都曾让 debug 日志出现"列表大小正常但章节/链接全空"的假象，源码级定位后一次修复。

## 坑一：目录章节名字段是 `chapterName`，不是 `chapterTitle`（最坑，排查最久）

`ruleToc` 里章节标题字段的合法键名是 **`chapterName`**（对应 `TocRule.chapterName`）。
写成 `chapterTitle` 时：Legado 不报错，`getElements` 也能拿到 N 个元素，但 `BookChapterList` 里
`bookChapter.title = analyzeRule.getString(nameRule)` 拿到空串 → `if (bookChapter.title.isNotEmpty())` 全部 false →
日志显示 `└列表大小:209` + `◇章节列表为空` + `TocEmptyException`，极具迷惑性。

**判据**：debug 日志出现「列表大小:N（N>0）」但紧接着「◇章节列表为空」→ 十有八九是 `chapterName` 写错。
正确 JSON：
```json
"ruleToc": {"chapterList": "...", "chapterName": "...", "chapterUrl": "..."}
```

## 坑二：`getElements` 的 @js 必须返回 JS 数组；元素传给孩子规则时 NativeObject 键值直取可能失效

源码 `AnalyzeRule.getElements`：`Mode.Js -> evalJS(rule, result)`，之后只处理 `List<*>`/`Array<*>`/`NativeArray`：
- `return JSON.stringify(arr)` 返回的是 **String** → 不匹配任何分支 → 返回空 ArrayList（列表大小 0）。
- `return arr`（JS 数组）→ NativeArray → 正确展开。

但展开后每个元素在 `chapterName`/`chapterUrl` 子规则里，`result` 是 NativeObject。**⚠️261120 重要修正**：
早期以为"元素用 `标题\nURL` 字符串 + 子规则 `@js:String(result).split()` 最稳"，实测 **LT 正常但 E 版目录全 null**
（E 版 `getString` 对字符串元素不走 `@js:` 分支，只走 JSONPath/键值直取，见 [[legado-dual-version-e-compat]]）。

**真正双版本通吃定式**（与发现页 null 修复同构）：
```js
// chapterList @js：必须是 Java ArrayList，每项 JSON.stringify
var list = new Packages.java.util.ArrayList();
list.add(JSON.stringify({name:nm, url:u+'?bid='+bid+'&cid='+cid+'&v='+ver}));
return list;
// chapterName / chapterUrl：统一 JSONPath
"chapterName": "$.name"
"chapterUrl":  "$.url"
```
为什么两版都通：Java `ArrayList` 被 Rhino 包成 Wrapper → `unwrapReturnValue` 还原成 `List`，两版 `getElements` 都接受；
每项是 JSON 字符串，`getString` 的 JSONPath 分支两版都能取。TS：字符串数组 + `@js` split 只在 LT 可用，**不要再用于新源**。

## 坑三：`ruleSearch.bookUrl` 的 @js 里 `result` 是 NativeObject，不是 JSON 字符串

源码 `BookList.getSearchItem`：`analyzeRule.setContent(item)` → `getString(ruleBookUrl, isUrl=true)`。
`item` 是 JSONPath `$.list[*]` 切出的 **NativeObject**，所以：
- 错：`JSON.parse(String(result))` → String(NativeObject) = `[object Object]` → parse 失败 → catch 返回 ''。
- 对：`result.id`（直接属性访问）。

而且 `getString(isUrl=true)` 末尾有：空串 → 回退 `baseUrl`（=searchUrl）。这就是"详情页链接显示成 searchbooks"
的伪装现象。同理 `ruleExplore.bookUrl` 用 `result.bookid`。

另注：组合规则 `id##https://host/path?bookid=___` 里的 `?` 会被 URL 解析干扰，改用 @js 直出完整 URL 更稳。

## 坑四：cread.com（爱看书免费小说）`.dat` 正文 = MD5(char低字节) XOR + Inflate + GB18030

抓 `.dat`（Content-Type `application/x-ns-proxy-autoconfig`）得到的是二进制密文，不是容器头。
从 APK 逆向 `b.d.a.c.b/a/c` 得到完整算法：

```
keystr = bookId + '-' + chapterId + '-' + version + '-3u5k41jj94mijuef3b8ljbo19o'
key    = MD5( 每个 char 强制转 byte（取低8位）后的 byte[] )   // 不是 UTF-8 编码！
plain  = Inflate( ciphertext XOR 循环 key )
text   = new String(plain, "GB18030")
```
- `bookId/chapterId/version` 来自目录 JSON 的 `bookChapters[].bookid/id/version`（version 常为 0，必须带上）。
- 章节 URL 形如 `http://book-resources.cread.com/resources/books/{bid}/{cid}-0.dat`，
  书源里在 URL 后拼 `?bid=&cid=&v=` 供正文 JS 解析（URL 选项不会被站点在意，因为请求时 `split('?')[0]`）。

**Legado JS 落地铁律（与 [[legado-binary-response-bytes]] 一致）**：
1. 二进制必须 okhttp 原生 bytes（`OkHttpClient().newCall(Request).execute().body().bytes()`）；
   `java.ajax` 会把字节按 UTF-16 解成 U+FFFD，不可逆。
2. bytes↔hex 用 `new BigInteger(1,bytes).toString(16)`（手动补前导0）/ `java.hexDecodeToByteArray(hex)`；
   前者防 OOM，后者在 LT 版纯 hex 场景正常。
3. key 派生：`StringBuilder` + `String.fromCharCode(ch & 255)` + `getBytes(ISO_8859_1)` → `MessageDigest MD5`。
4. `InflaterInputStream` + `ByteArrayOutputStream`，buf 用 `java.hexDecodeToByteArray('00'.repeat(512))`
   （Rhino 下 `java.lang.reflect.Array.newInstance` / `java.lang.Byte.TYPE` 不可用，会报"newInstance 不是函数"）。
5. `new Packages.java.lang.String(plain,'GB18030')` 解码中文。

## 接口清单（cread.com / 爱看书免费小说 v8.2.7）

| 用途 | 接口 | 关键参数 |
|---|---|---|
| 搜索 | POST `https://cxb-pro.cread.com/cx/searchbooks` | body `keyword={key}&pageNo={page}&version=8.2.7` |
| 详情 | GET `https://cxb-pro.cread.com/cx/bookDetailYS?bookid={id}` | 需要 header uid/cnid/version |
| 目录 | GET `https://cxb-pro.cread.com/cx/itf/getvolume?bookId={id}` | 全量章节，单页返回（可 7000+ 章） |
| 正文 | GET `http://book-resources.cread.com/resources/books/{bid}/{cid}-0.dat` | UA=Dalvik，二进制密文 |
| 发现/分类 | GET `https://cxb-pro.cread.com/cx/new/catelistnew?...` | **query 必须带 uid/cnid/version**，否则 dataList 空（header 里带了也没用） |
| 封面 | `http://images-pro.cread.com/211/images/{id}.jpg` | |

header 需带：UA(WebView Chrome 83)、Accept-Language、uid、cnid=12001、version=8.2.7、umeng、
packname=com.mianfeia.book、oscode、vcode、channelId、platform=android、appname=cxb 等（抓包原样）。
免登录；搜索未见限频，但按用户要求不要主动探测频率。


## 坑五：@js 规则里的 `\n` 转义触发 check_source「字符串文字没有限制」

check_source 校验器把 `@js` 段包进 `<script>` 编译时，规则里的 `'\n'`（反斜杠+n）会被当成非法字符串字面量换行，
报「js失效 | 字符串文字没有限制」，列位置正好指向 `\n`。debug_source 未必复现（两套编译路径），
所以必须以 check_source 为准。

**正解**：凡 `@js` 规则里要表示换行/拼接分隔符，用 `String.fromCharCode(10)` 代替 `'\n'`：
```js
out.push(title + String.fromCharCode(10) + url);
@js:String(result).split(String.fromCharCode(10))[0]
```
注意正文正文里的 `split(/\r?\n/)`、`arr.join('\n')` 经实测 check_source 能通过（在正则/join参数上下文），
但新写的规则优先用 fromCharCode 可彻底规避。


## 补充：发现页两大可分页接口与频道映射（抓包实证）

1. **分类** `GET /cx/new/catelistnew?uid=&cnid=12001&version=8.2.7&flid={flid}&thirdCateId=0&sortType=1&bookStatus=0&wordnumType=0&pageSize=20&curpage={page}`
   - 响应：`$.dataList[*]`（字段 newBookName/authorName/categoryName/wordCount/intro/cover/bookid）
   - 主分类 flid 映射（App 分类页实证）：1100玄幻大陆/1200热血都市/1300魔幻世界/1400奇幻修真/1500架空王朝/1600星际未来/1700虚拟游戏/1800悬疑冒险；2100古色古香/2200玄幻仙侠/2300婚恋情缘/2400豪门世家/2500校园纯情/2600唯美小说；3100文学小说/3200古代名著/3300职场励志/3400美食菜谱/3500恋爱秘籍/3600科学科普/3800亲子育儿/3900生活实用。
   - 每个主分类还有 `cateListTwo.thirdCateList`（子分类 id/name），可做二级频道。
2. **榜单** `GET /cx/new/rankList?uid=&cnid=12001&bdid={bdid}&name=男频|女频&index=1&pageSize=50&curpage={page}`
   - 响应：`$.data.dataList[*]`（**多一层 data**），榜名在 `$.data.bdname`（可能带脏数字后缀如"追更榜420"，取干净名）。
   - 榜单 bdid：461追更/463完结/465热搜/466飙升/467新书/475人气/904好评（男频）；817现言/818古言/819总裁（女频）。也有 470/471/473/474 等重复榜（数据少），可不用。
3. **两种 JSON 结构在一条 ruleExplore 里兼容**：`@js` bookList 用 `var d=j.dataList||(j.data&&j.data.dataList)||[]` 统一取列表，再把字段按 `String.fromCharCode(1)` 拼成单字段字符串，各子规则 split 取值——一次解决结构差异与 NativeObject 键值直取兼容性。
4. `getConfigItems` 首页接口（`data.bangdan`，含爆款神作/全网大热等）是内置书单、不能翻页，不适合做发现频道；发现页只用 catelistnew + rankList。


## 坑六：发现页 select 切换无效——SET/GET 不是内置函数（照搬 rrssk 翻车）

把 rrssk 聚合源的 select 范式 `SET('server', infoMap['域名']); java.refreshExplore()` 照搬到一个**没有 jsLib** 的书源，切换后列表完全不变、手动刷新也无效。

源码级根因：
- `SET`/`GET` **不是 Legado 内置**（JsExtensions.kt 只有 `get(url,headers)` HTTP 方法）——它们是 rrssk 自己 jsLib 里定义的。无 jsLib 的源调用 `SET(...)` 抛 `ReferenceError`，被 `evalButtonClick` 的 try/catch 吞掉 → 后面的 `java.refreshExplore()` 根本没执行；exploreUrl 里 `GET(...)` 同样抛异常被 catch 吞 → 永远返回默认值。
- 但 `check_source` 和 debug 都发现不了（异常被吞），只有用户实测才暴露。

正解（源码 ExploreAdapter.kt:541-553 + BookSourceExtensions.kt）：
1. select 切换时框架**已自动写 `infoMap[title] = chars[position]`**（line 548），action 里不用再 SET。
2. action 只写：`java.toast('已切到' + infoMap['频道']); java.refreshExplore()`。
3. exploreUrl 的 `@js` 求值**注入 infoMap**：`evalJS(exploreUrl.substring(4)){ put("infoMap", exploreInfoMap) }`，直接 `var v = infoMap && infoMap['频道']` 读取即可。
4. `java.refreshExplore()` → `clearExploreKindsCache()`（清 aCache + exploreKindsMap）→ 重新求值 exploreUrl → 重绘；链路有效。缓存 key = md5(bookSourceUrl+exploreUrl)，不含 infoMap，但因为清缓存后重求值读新 infoMap，能联动。

判据：select 切换后列表不变且 toast 不弹 ⇒ action JS 抛异常被吞，检查 action 里是否有未定义函数（SET/GET/自定义函数未放 jsLib）。action 必须是**单个字符串**（不是数组）。

## 坑七：封面字段是 `coverUrl`，不是 `cover`（BookListRule / BookInfoRule 都同理）

Legado 书源 JSON 的封面规则字段名是 **`coverUrl`**（源码 `BookListRule.coverUrl`、`BookInfoRule.coverUrl`），
写成 `cover` 时 Legado 完全不读这个规则：debug 日志里「┌获取封面链接」直接为空，但接口 JSON 的 cover 字段本身有值。

**判据**：发现/搜索/详情接口里封面 URL 有值，但 debug 日志「获取封面链接」为空 → 先查 JSON 里是否误写成 `cover`。

正确写法：
```json
"ruleSearch":  {"coverUrl": "cover"},
"ruleBookInfo":{"coverUrl": "bookImg"},
"ruleExplore": {"coverUrl": "$.cover"}
```
即：**规则键名永远是 `coverUrl`**，右侧值才是接口字段名（或 JSONPath）。
注意封面 URL 多为 http，Legado 默认不混用明文 HTTP 图片时需要在 App 设置里允许；书源侧规则只需保证 debug 日志能取到 URL。


## 坑八：E 版目录 null——`getString` 对字符串元素不走 `@js:`，只走 JSONPath（坑二的 E 版症状）

同一本源：LT 版目录全绿（列表 N 章、章节名/链接正常），**E 版目录条目全显示 null**。
根因就是坑二修正条里说的：早期用「`chapterList` 返回字符串数组 + 子规则 `@js:String(result).split()`」，
LT 版 `getString` 对字符串元素走 `Mode.Js` 分支正常，但 **E 版 `getString` 对字符串元素只有 JSONPath/键值直取，不进 `@js:`** →
章节名/链接全 null（目录列表条数正常，只是每个条目内容 null）。这是发现页 null 的同构问题（见 [[legado-dual-version-e-compat]]）。

**判据**：目录列表大小正常但 E 版章节名/链接 null，而 LT 正常 → 检查 `chapterName`/`chapterUrl` 是否用了 `@js:` 拆分字符串元素。

**修法**：与发现页定式完全一致，把 `ruleToc` 改成 Java ArrayList + JSONPath：
```json
"chapterList": "@js:(function(){...var list=new Packages.java.util.ArrayList();list.add(JSON.stringify({name:nm,url:u+'?bid='+bid+'&cid='+cid+'&v='+ver}));return list;})()",
"chapterName": "$.name",
"chapterUrl":  "$.url"
```
改完三端保存、`check_source` 1/1、LT debug 目录+正文全绿；E 版请用户刷新目录缓存实测确认。

**经验升级**：凡是 `getElements` 产出的列表，其**子字段规则一律用 JSONPath（`$.key`）**，列表本身返回
`new Packages.java.util.ArrayList()` + 每项 `JSON.stringify({...})`——这个定式一次覆盖搜索/详情/发现/目录所有列表链路，
不要再为"LT 能用"而保留字符串数组 + `@js` split 的写法。
