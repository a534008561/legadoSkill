# 方法：Legado 各版本行为差异对照
## ——同一份书源在 LegadoTeam / legado-E(Lyc/Luoyacheng) / 官方版上为什么会坏

> 沉淀日期：2026-09-14　｜　来源：hlwf6 v3.1 双版实测、pixiv 三源、novelServices、米游社、63sg、hanime1 v2~v3.9
> 关联：[方法-AnalyzeByJSoup状态污染与绕开总表](方法-AnalyzeByJSoup状态污染与绕开总表.md)、[方法-URL模板与DNS选线](方法-URL模板与DNS选线.md)

---

## 目录

1. [为什么必须关心版本](#一为什么必须关心版本)
2. [版本谱系与识别](#二版本谱系与识别)
3. [★差异总表（20 项，实测/源码双证）](#三差异总表20-项实测源码双证)
4. [头号差异：列表规则的返回值协议](#四头号差异列表规则的返回值协议)
5. [Kotlin 属性 vs 方法：Rhino 里的取值适配](#五kotlin-属性-vs-方法rhino-里的取值适配)
6. [jsLib / loginUrl / 规则 三作用域能力矩阵](#六jslib--loginurl--规则-三作用域能力矩阵)
7. [Book.type 位掩码与刷目录冲掉 type](#七booktype-位掩码与刷目录冲掉-type)
8. [Cookie 与请求栈差异（-100 配对错乱案）](#八cookie-与请求栈差异-100-配对错乱案)
9. [跨版本分发纪律](#九跨版本分发纪律)
10. [如何自己做版本 diff（源码级）](#十如何自己做版本-diff源码级)
11. [API 存在性判定方法论（含一次误判复盘）](#十一api-存在性判定方法论含一次误判复盘)

---

## 一、为什么必须关心版本

三次真实翻车，根因全是"版本差异"，且报错信息都不指向真因：

1. **hlwf6**：LT 版一切正常，用户报 legado-E 上"发现列表 15 条但**字段全空**、目录获取失败"。→ `getString` 的 `NativeObject` 分支两版不同。
2. **米游社定时任务**：官方 LegadoTeam 版一直 `-100`，改版正常。→ `AnalyzeUrl.setCookie()` 无条件 merge 库内旧会话键，配对断裂。
3. **pixiv 免 VPN**：老 `login()` 在手机上全部 HTTP 栈失败。→ GFW 对 `*.pixiv.net` 做 SNI 重置 + nginx 对 h2 强制校验 SNI↔Host。

> 一句话：**书源不是"写完就能给所有人用"的，跨版本分发必须双版本实测。**

---

## 二、版本谱系与识别

| 常称 | 仓库/包名线索 | 脚本引擎 | 特点 |
|---|---|---|---|
| 官方 Legado | `gedoor/legado` | rhino-1.7.14 | 基线 |
| **LegadoTeam 版（LT）** | 我们主力环境 | **htmlunit corejs** | 列表规则支持 `Mode.Js → NativeArray` 键访问；`BookType.kt` 位掩码新值 |
| **legado-E / Lyc / Luoyacheng** | `luoyacheng` 系改版 | **原版 rhino-1.7.14** | `NativeArray` 实现 `java.util.List`；`getString` **无 Mode.Js 分支**；`exploreKinds` 有 `aCache` 持久缓存 |
| 各种"阅读3.0"第三方打包 | — | 混合 | 必须逐项实测 |

快速识别（在目标 App 内 `eval_js`）：

```javascript
// 1) 引擎线索
typeof Packages.org.htmlunit.corejs.javascript.Context !== 'undefined' ? 'htmlunit-corejs(LT)' : 'rhino(E/官方)';
// 2) 版本线索：包名
java.getClass ? '' : '';   // getClass 在 Rhino 返回 null，别用
```

**更实用的识别法**：跑一次"列表规则返回 JS 对象数组"的最小源（见第四节），字段全空 = E 版行为；正常 = LT 版。

---

## 三、差异总表（20 项，实测/源码双证）

| # | 项 | LT 版（主力） | legado-E / Lyc / 官方 | 处置 |
|---|---|---|---|---|
| 1 | `getString`/`getStringList` 的 **NativeObject 分支** | 有 `Mode.Js → evalJS` | **无** → 条目是 NativeObject 时把规则当键名直取 → undefined | 列表规则返回 **JSON 字符串数组** + 纯键名字段（两版一致） |
 2 | `result.body`（StrResponse） | **方法引用**（`typeof==='function'`），必须 `result.body()` | 属性 | 双通道 `gv()` |
| 3 | Kotlin data class 任意属性 | 同上，是方法 | 部分是属性 | 统一 `gv(o,k)` 双兼容 |
| 4 | `jsLib` 作用域 `java.ajax` | **不是函数**（`JavaPackage`）/"ajax 不是函数" | 较宽松 | 网络操作**内联进规则 `@js`**；或参数注入法把 `java`/`source` 当实参传进函数 |
| 5 | `jsLib` 作用域 `source` | **未定义** | 部分有 | 同上 |
| 6 | `java.setCookie` | ❌ 无 | 有 | 用 `cookie.getCookie`+`cookie.setCookie` 配对 |
| 7 | `cookie.removeCookie(url,key)` 两参 | ❌ 找不到方法 | 有 | 只能 get→过滤→set 整体回写 |
| 8 | `java.getVerificationCode(url)`（弹窗取验证码） | ✅ **有**（签名 `String(String)`） | 有 | ⚠️ 曾在 `eval_js` 探测为 undefined 而误判"不存在"——见第十一节 |
| 9 | `java.sleep(ms)` | ❌ 无 | 无 | `Packages.java.lang.Thread.sleep(ms)` |
| 10 | `java.show(...)`（定时任务） | ❌ 无 | — | 三级降级 `longToast → toast → copyText` |
| 11 | `Book.type` 位掩码 | **video=4 text=8 audio=32 image=64** | 旧值 0/1/2 | 按 LT 值写；`setType` 后立刻回读校验 |
| 12 | `WebBook.getChapterListAwait` 刷目录 | 每次 `removeAllBookType()` + `addType(source.getBookType())` **冲掉详情页 type** | 同 | **详情 + 目录规则双 `setType`** |
| 13 | `ruleToc.chapterUrl` 纯 `@js:` | ✅ 可执行（zhaoshu 实锤，推翻早期结论） | 可 | 但 `"选择器@js:"` 组合形式不执行 → 改 `{{}}` 插值 |
| 14 | `ruleToc.tocUrl` 位置 | 必须在 `ruleBookInfo` 内；放 `ruleToc` 被**反序列化静默丢弃** | 同 | 且**不支持 `\|\|` 兜底** |
| 15 | `AnalyzeUrl` URL 选项 | 原生 `dnsIp/resolveIp`、`retry`、`timeout` | 老版无 `dnsIp` | 被墙站的分发要写降级路径 |
| 16 | `enabledCookieJar` → Cookie 注入 | `AnalyzeUrl.setCookie()` **无条件 merge** 库内 Cookie | 官方 OkHttp `.cookieJar()` 被注释 | 手动 Cookie 鉴权必须**全量发送**，勿清域 |
| 17 | `useweb` 里 `java.openUrl` | 直接开 | 走 `OpenUrlConfirmActivity` = **外部浏览器确认页** | 内置浏览器/播放器用 `startBrowser`/`openVideoPlayer`（规则上下文两版都行） |
| 18 | `java.startBrowser` 在 useweb 页面 | 有注解？→ **无 @JavascriptInterface**，页面 JS 调不到；**规则上下文可调用** | 同 | 简介按钮走 `<usehtml>` + `@onclick:`（跑完整 JsExtensions 环境） |
| 19 | `loginUi` | 经典 RowUi 数组；部分新 build 支持 `{"version":2}` | 多为 V1 | V2 面板在 V1 上不渲染 |
| 20 | `ExploreRule.checkKeyWord` | **无此字段**（GSON 丢弃） | 无 | `checkKeyWord` 放 `ruleSearch` 内（`BookSource.kt:217` 只读 `ruleSearch?.checkKeyWord`） |
| 21 | `BookList.kt:62/64` | `baseUrl.matches(bookUrlPattern)` → 搜索/探索结果**按详情页解析** | 同 | **pattern 绝不能匹配搜索/列表 URL** |
| 22 | 变量 API | `eval_js`/`BookSource` 侧**没有** `getVariable/setVariable`，只有 `put/get`（`CacheManager`，进程内存级） | 同 | 规则上下文 `source`=`JsExtensions`，`getVariable()`（**无参**，读写**书籍级** `book.variable`，随书持久）→ 两类语义不同，跨上下文读必须**双通道 + `String()` 归一化**（详见[字体反爬篇第六节](方法-字体反爬三代方案演进.md)） |

---

## 四、头号差异：列表规则的返回值协议

**这是唯一会导致"整源在别人手机上全空"的差异，必须当成铁律。**

### ✗ 只在 LT 版能用

```javascript
"bookList": "@js:result = [{name:'A',url:'/1.html'},{name:'B',url:'/2.html'}]",
"name": "@js:result.name"          // ← E 版：把 "@js:result.name" 当键取 → undefined → 条目被丢
```

### ✓ 两版通用

```javascript
// 列表规则返回【JSON 字符串数组】
"bookList": "@js:var a=[]; ... a.push(String(JSON.stringify({name:n,url:u}))); return a;",
// 字段规则用【纯键名】
"name": "$.name",
"bookUrl": "$.url"
```

原理：字符串条目两版都走 `Mode.Json` → jsonpath 直取；LT 版的 `NativeObject → getString` 键访问只是"额外能力"，不能作为分发基线。

> 同理 `chapterList` 也必须返回字符串数组。**`ruleSearch` 若源自 JSONPath（`$.book[*]`），条目是 `LinkedTreeMap`，两版都有直取分支，不受此影响。**

---

## 五、Kotlin 属性 vs 方法：Rhino 里的取值适配

35sw 那次最诡异的 bug 根源：`loginCheckJs` 里写 `result.body` 拿到的是**函数**，静默失配 → 限频页 0 结果，甚至 `null as StrResponse` NPE。

统一双兼容工具（写进每个要读 Java 对象的 `@js`）：

```javascript
function gv(o, k) {
  if (!o) { return null; }
  var f = o[k];
  return (typeof f === 'function') ? f.call(o) : f;
}
var body = String(gv(result, 'body') || '');
```

Rhino 相关限制（一并记住）：

- `obj.getClass()` → **返回 `null`**，不可用；反射探测请用 `for (var k in obj)` 枚举；
- Kotlin `internal` 成员名带 `$legado_app_appRelease` 后缀；
- `Class.forName` 基本被封；`Packages.io.legado.app.data.entities.BookSource`、`...help.JsExtensions`、`cn.hutool`、`com.jayway.jsonpath` 直接可见；`SourceManager`/`AppDatabase`/DAO/`Gson` 不可见（R8 改名）；
- QuickJS（书源以外的场景）不支持反引号模板字符串 → 页面脚本统一单引号。

---

## 六、jsLib / loginUrl / 规则 三作用域能力矩阵

三个作用域各自编译、互不相通——这是本 App 级最大坑，也是"函数该放哪"的唯一依据。

| 能力 | `jsLib` | `loginUrl` / `loginUi.action` | 规则 `@js:` | `loginCheckJs` | 定时任务 `script` |
|---|---|---|---|---|---|
| `java.ajax/get/post/connect` | ❌ 受限 | ✅ | ✅ | ✅ | ✅ |
| `source` | ❌ 未定义 | ✅ | ✅ | ✅ | — |
| `result` 含义 | — | `getLoginData()`（按 RowUi 的 **name** 为键，取值 `.get('键名')`） | 上游字段值 | **StrResponse，必须原样 return** | — |
| 顶层 `return` | 函数体内 OK | 函数体内 OK | `@js:` 内 OK | ❌ **按表达式解析，必须 IIFE** | ❌ 顶层 return 报"返回的值无效" |
| 顶层具名函数 → UI 按钮 action 直调 | — | ✅ 必需 | — | — | — |

### 参数注入法（jsLib 里要用 java/source 时的唯一解）

```javascript
// jsLib
function pickLine(Jv, Sv, fc) {      // ★把 java / source 作为实参传进来
  var h = String(Jv.ajax('https://pub.example/lines.txt') || '');
  ...
  Sv.put('line', best);
  return best;
}
// 规则里
"exploreUrl": "@js:pickLine(java, source, 300)"
```

`loginUrl` 则必须**自包含**：把 jsLib 的工具函数复制一份进去（不能引用 jsLib）。

---

## 七、Book.type 位掩码与刷目录冲掉 type

`BookType.kt`（LT 版）：`video=4, text=8, audio=32, image=64`（旧值 0/1/2 **无效**）。

**致命链**：`WebBook.getChapterListAwait()` 每次刷目录都
`book.removeAllBookType(); book.addType(bookSource.getBookType())`
→ 详情页设的 `setType(64)` 被书源的 `text(8)` 冲掉 → 漫画/视频/听书又变回文字。

**唯一稳妥做法**：详情规则**和**目录规则**都** `setType`（novelServices 与 pixiv 漫画版双处实测）。

听书：`setType(32)` 才会走 `AudioPlay`；此时正文规则必须返回**纯 URL**（`cotent.trim()` 直接当 `durPlayUrl`）。音频失败时正文规则可做"自动重试 tone_id 1~4"自愈。

---

## 八、Cookie 与请求栈差异（-100 配对错乱案）

米游社三层真相，通用性极高（任何"手动 Cookie 鉴权 + 站点有会话配对键"的站都适用）：

1. LT 版 OkHttp 的 `.cookieJar()` **被注释**，不装 jar；注入路径是 `NetworkInterceptor`（仅 `enabledCookieJar=true` 触发）+ `AnalyzeUrl.setCookie()`（**无条件执行，关不掉**）；
2. `setCookie()` 的 merge 语义：`mergeCookies(dbCookie, manualCookie)` → reduce 为后传覆盖先传 → **手动头键优先，库中"手动头没有的键"被补进来**；
3. 米哈游服务端校验 `ltoken_v2` ↔ `ltmid_v2` **配对**。库里的旧 `ltmid_v2`（旧 WebView 会话）被 merge 进来 → 配对手 → `-100 登录失效`。

**最终对策（v9g）**：登录 UI 一个 Cookie 框粘 `document.cookie` 全量 → `source.put('mhyCookie', raw)` 整存 → 请求**全量发送**（手动头含全部键，merge 无损）+ `enabledCookieJar=false`。

推广结论：

> 手动 Cookie 鉴权 + 该域库里有旧键 → 要么**全量发送**，要么 `removeCookie(url, key)` **精准**删单键。**绝不整域清**（`cookie.removeCookie(url)` 会删掉配对必需键，两版都翻车）。
> 诊断法：换环境对照——token 在另一端可用 → merge 污染；两端都死 → 吊销或缺配对键。

**HTTP 栈层面**（pixiv 案）：手机侧所有 Legado HTTP 栈（`java.post`/jsoup、`java.connect`/OkHttp）**都会协商 h2**；被 GFW SNI 重置的站 + nginx 对 h2 强制校验 SNI↔Host（返回 421）→ 唯一通路是**原始 TLS 套接字 + 无 ALPN + 手写 HTTP/1.1**：

```javascript
var sf = Packages.javax.net.ssl.SSLSocketFactory.getDefault();
var sk = sf.createSocket(ip, 443);        // URL 用 IP ⇒ 不发 SNI、无 ALPN
// 手写 "POST /oauth/token HTTP/1.1\r\nHost: oauth.secure.pixiv.net\r\n..."
// 证书是公共 CA 签的（含 *.pixiv.net SAN）⇒ 系统默认信任，校验照常过
```

---

## 九、跨版本分发纪律

1. **基线取最小公约**：列表规则返回 JSON 字符串数组、字段纯键名、`gv()` 双兼容、`Thread.sleep`、`longToast` 降级、URL 选项降级路径（无 `dnsIp` 时回退 hosts/换域名）。
2. **交付前逐块语法体检**：抽取书源全部 JS 块（`jsLib`/`loginUrl`/`@js:`/`<js>`）逐个 `node --check`。
   **⚠️ `loginUi` 不要查**——它是宽容解析器（字符串内真实换行 + 无引号键名合法），`node` 必误报。
3. **必须双版本实测**才算"可分发"。只在自己的 LT 上过测 = 未验证。
4. **注释纪律**：minified `jsLib` 里在对象字面量方法间插 `//` 注释，**注释后必须紧跟真实换行**，否则注释吞掉其后所有代码直至下一个换行 → 诡异语法错。

---

## 十、如何自己做版本 diff（源码级）

不要靠猜。三步：

```python
# 1) GitHub Contents API 拉两版同一文件（api.github.com 可达；git+https 可能被墙）
def get(owner, repo, path, ref):
    u = f'https://api.github.com/repos/{owner}/{repo}/contents/{quote(path)}?ref={ref}'
    return base64.b64decode(json.loads(api(u))['content']).decode('utf-8','replace')
a = get('gedoor','legado','app/src/.../AnalyzeRule.kt','master')       # 官方/系 E
b = get('LegadoTeam','legado','app/src/.../AnalyzeRule.kt','main')     # LT
# 2) difflib 只看 getString/getStringList 的分支差异
# 3) 差异点立刻转成"最小复现书源"在两台手机各跑一次
```

**已从中实锤的差异**：E 版 `getString`/`getStringList` 的 `NativeObject` 分支**缺** `Mode.Js → evalJS`（LT 有）——这一条直接决定了第四节的铁律。

- 常量/枚举以 GitHub 源码为准，不要信记忆；
- `.class` 文件可用 `rhino jar` 或 `javap` 反查签名；
- 离线模拟 E 版行为：在 LT 上手工走"字符串条目 → Mode.Json"路径对照。

---

## 十一、API 存在性判定方法论（含一次误判复盘）

**教训**：ppxsw 那次曾用 `eval_js` 探测 `java.getVerification` / `getVerificationCode` 得 `undefined`，据此写下"官方 API 不存在、仅 eval_js 可弹窗"的结论，并推上了 GitHub。**用户指正后重测：两版都存在**（`getVerificationCode` 签名 `String(String)`）。误判原因：`eval_js` 独立环境的 `java` 能力本身就受限（与 `jsLib` 作用域 `java.ajax` 不可用是同一类现象）。

**正确方法论（按可信度排序）**：

```
书源实跑（在真实调用上下文里调一次）
  > 官方/改版源码 grep（@JavascriptInterface 注解、函数签名）
  > 反射枚举成员（for (var k in java)）
  > 单一环境的 typeof 探测        ← 只能证"有"，不能证"无"
```

**规则**：

- 判"不存在"必须给出**两个以上独立证据**（源码 + 真实上下文实跑），且注明探测环境；
- `typeof x === 'undefined'` 的三种可能：真的没有 / **作用域不对** / 名字被 R8 改了。先换上下文再下结论；
- 旧记忆里的"API 不存在"属于**可过期结论**，用到时先复测一次（成本 1 次 debug）。

---

## 附：交付前的"跨版本 6 问"

1. 列表/目录规则是不是返回 **JSON 字符串数组**、字段是不是 **纯键名**？
2. 所有读 Java 对象的地方是不是 **`gv()` 双兼容**？
3. 网络/Cookie 操作是不是 **内联在规则里**（而不是躲在 jsLib）？
4. `type` 是不是 **详情 + 目录双设**（位掩码用 4/8/32/64）？
5. 手动 Cookie 是不是 **全量发送**（而不是清域后拼几把键）？
6. `checkKeyWord` 是不是放在 **`ruleSearch` 内**（不是顶层、不是 `ExploreRule`）？

六个"是"齐了，才叫"可以发给别人"。
