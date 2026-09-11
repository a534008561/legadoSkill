# 方法-HttpTTS 朗读引擎与音色切换面板

> 适用：把任意 TTS 服务（自建 FastAPI/TTS 代理、云厂商接口、语音合成网关）接成 Legado「在线朗读引擎」，
> 并需要**音色切换 / 线路切换 / 测速 / 清缓存**这类**按钮面板**。
> 本文所有结论均来自 LegadoTeam 源码逐行核对 + 真机（阅读T + MCP）实测，非推测。
> 案例落地：起点 TTS 控制台（IFly + Minimax，`http://103.236.85.8:8000`），6 个引擎，5 音色按钮面板。

---

## 0. 一句话结论

**HttpTTS（在线朗读引擎）可以用「登录界面按钮」做功能面板** —— 这是官方给朗读引擎加按钮的**唯一**通道，
因为它复用了 `loginUrl` + `loginUi` + `loginCheckJs` + `header` + `jsLib` 全部 BaseSource 能力。

---

## 1. HttpTTS 实体全字段（源码：`data/entities/HttpTTS.kt`）

```kotlin
@Entity(tableName = "httpTTS")
data class HttpTTS(
    @PrimaryKey val id: Long = System.currentTimeMillis(),
    var name: String = "",
    var url: String = "",
    var contentType: String? = null,
    var pauseDuration: Int = 0,          // 0~10000ms，段落之间的静音（generateSilentWavBytes 生成静音段）
    override var concurrentRate: String? = "0",
    override var loginUrl: String? = null,
    override var loginUi: String? = null,
    override var header: String? = null,
    override var jsLib: String? = null,
    override var enabledCookieJar: Boolean? = false,
    var loginCheckJs: String? = null,
    var lastUpdateTime: Long = System.currentTimeMillis()
) : BaseSource
```

| 字段 | 用途 | 注意事项 |
|------|------|----------|
| `url` | 请求 URL，**支持 `<js>`/`@js:`/`{{}}`/URL 选项 JSON** | 见第 4 节，JSON body 必须 `JSON.stringify` |
| `contentType` | 音频类型，`audio/mpeg` 最常用 | 影响「非音频错误响应」的识别 |
| `pauseDuration` | 段间插静音（毫秒） | 站点 mp3 自带尾音时留 0；段间太紧给 200~400 |
| `concurrentRate` | 并发/限频，`次数/毫秒`，`"0"`=不限 | `1/200` = 5 次/秒 |
| `loginUrl` | **顶层具名函数集**（无 `@js:` 前缀） | 按钮 action 调用它；单行不换行最稳 |
| `loginUi` | RowUi JSON 数组（或 `<js>` 新版 UI） | 见第 3 节 |
| `loginCheckJs` | **每次请求后的响应拦截器** | `result`=StrResponse，必须原样 `return` |
| `header` | JSON 字符串，也支持 `<js>` | 不含则用 App 默认 UA |
| `jsLib` | 共享 JS 库 | 各 App 版本作用域差异大（见第 9 节），能不用就不用 |
| `enabledCookieJar` | 是否启用 CookieJar | 纯 API 类 TTS 一般 `false` |

---

## 2. 请求链路源码级拆解

### 2.1 url 规则的执行入口（`service/HttpReadAloudService.kt`）

```kotlin
val analyzeUrl = AnalyzeUrl(
    httpTts.url,
    speakText = speakText,      // 本条正文（已过 notReadAloudRegex 清洗）
    speakSpeed = speechRate,    // ★ = AppConfig.speechRatePlay + 5
    source = httpTts,           // ★ source 绑定就是 HttpTTS 本体
    readTimeout = 300 * 1000L,
    coroutineContext = currentCoroutineContext()
)
val response = analyzeUrl.getResponseAwait()
// loginCheckJs 在这里被调用：
if (!checkJs.isNullOrBlank()) analyzeUrl.evalJS(checkJs, it) as Response else it
```

失败路径同样会走 `loginCheckJs`（`getErrResponse(throwable)` 后回调一次，返回 `code==500` 才向上抛）。

### 2.2 url 里可用的绑定（`model/analyzeRule/AnalyzeUrl.kt` `buildScriptBindings`）

```kotlin
bindings["java"]       = this          // JsExtensions（ajax/head/toast/openUrl/... 全可用）
bindings["baseUrl"]    = baseUrl
bindings["cookie"]     = CookieStore
bindings["cache"]      = CacheManager
bindings["page"]       = page
bindings["key"]        = key
bindings["speakText"]  = speakText     // ★ TTS 专属
bindings["speakSpeed"] = speakSpeed    // ★ TTS 专属
bindings["source"]     = source        // ★ = HttpTTS，可 source.get/put 读写引擎私有变量
bindings["result"]     = result
bindings["infoMap"]    = infoMap
```

**关键推论**：TTS 引擎可以**自带持久化配置项**——`source.put(k,v)` / `source.get(k)` 走
`BaseSource` → `CacheManager`，键名 `v_{getKey()}_{k}`（`getKey()` = `httpTts:{id}`）。
未设置时 `get()` 返回 **`""`**（不是 null），所以**兜底判空必须写在规则里**。

### 2.3 `{{}}` 与 `<js>` 的执行顺序（`AnalyzeUrl.initUrl()`）

```
ruleUrl = mUrl
1) analyzeJs()        → 先执行 @js: / <js> 整段（evalJS 的返回值整体替换 ruleUrl）
2) replaceKeyPageJs() → 再跑 RuleAnalyzer.innerRule("{{","}}") 逐个 evalJS 替换
3) analyzeUrl()       → 切 ',' 前为 URL，后面按 UrlOption JSON 解析（GSONStrict）
```

- `<js>` 用 `AppPattern.JS_PATTERN = <js>([\w\W]*?)</js>|@js:([\w\W]*)` 匹配，**匹配到即整段替换**。
- `{{}}` 是**完整 JS 表达式**（`evalJS(it)`），可以写 `{{Math.min(100,speakSpeed*5)}}`。
- `UrlOption.setBody()`：body 是 JSON 对象 → 转 Map；`getBody()` 再 `GSON.toJson()` 发出去。

### 2.4 并发率语义（`help/ConcurrentRateLimiter.kt`）

`"n/t"` = **t 毫秒内最多 n 次**（`accessLimit`/`interval`）；`"0"`/空 = 不限。
超限抛 `ConcurrentException(需等待 xms)`，Legado 会自己排队重试。

---

## 3. 按钮面板：loginUi / RowUi 全解

### 3.1 入口链路（怎么点到按钮）

```
朗读界面 → 朗读菜单 → 语音引擎
   → 点某引擎右侧【编辑】(HttpTtsEditDialog)
      → 右上角 ⋮ 菜单 → 【登录】(menu_login)
         → 要求 loginUrl 非空，否则弹「登录url不能为空」
         → SourceLoginActivity(type="httpTts", key=id)
            → source.hasLoginForm() == true（loginUi 非空且不等于 "[]"）→ SourceLoginDialog（经典面板）
            → 否则 WebViewLoginFragment
```

> 编辑对话框里 `loginUrl / loginUi / loginCheckJs / header / jsLib / contentType / pauseDuration / concurrentRate`
> **全都能编辑**，还有「复制源/粘贴源」「查看登录头」「日志」「帮助」菜单 —— 即 HttpTTS 是完整的 BaseSource。

### 3.2 RowUi 字段（`data/entities/rule/RowUi.kt`）

```kotlin
data class RowUi(
    val name: String = "",                 // 键名（也是 getLoginData 的 key）
    val type: String = "text",             // text/password/button/label/toggle/select
    val action: String? = null,            // 按钮点击执行的 JS（或绝对 URL）
    val chars: Array<String?>? = null,     // toggle/select 的选项
    val default: String? = null,
    var viewName: String? = null,          // 显示文字（见 3.3 二义规则）
    val style: FlexChildStyle? = null,     // 布局
    val key: String? = null, val hint: String? = null,
    val value: String? = null, val options: List<String>? = null, val countdown: Int? = null,
)
```

### 3.3 ★button 的 viewName 二义规则（决定能不能做「动态文字」）

```kotlin
if (viewName == null)                       textView.text = name
else if (viewName.length in 3..19 && viewName.first()=='\'' && viewName.last()=='\'')
                                            textView.text = viewName.substring(1, len-1)   // 字面量
else { textView.text = name; evalUiJs(viewName) }  // ★ 当 JS 表达式求值
```

- 想要**静态文字**：省掉 `viewName`，直接写 `name`（最稳）。
- 想要**动态文字**（如「当前音色：关山」）：`"viewName": "curLabel()"` —— 不能带单引号包裹。
- `evalUiJs` 实际执行 `loginUrl + "\n" + viewName`，绑定 `result`(getLoginData)/`java`/`book`/`chapter`。
  求值失败按钮显示 `"err"`（仅外观，不影响其它按钮）；空串显示 `"null"`。

### 3.4 ★按钮点击的执行口径（`SourceLoginDialog.handleButtonClick`）

```kotlin
if (action.isAbsUrl()) context?.openUrl(action)          // action 直接写 http(s):// 就是打开浏览器
else if (action != null) {
    val buttonFunctionJS = action
    val loginJS = loginUrl ?: return                     // ★ loginUrl 为空则按钮什么也不做
    source.evalJS("$loginJS\n$buttonFunctionJS") {
        put("java", sourceLoginJsExtensions)             // SourceLoginJsExtensions
        put("result", getLoginData(rowUis))              // 面板当前值 Map（含 select 选中项）
        put("book", viewModel.book); put("chapter", viewModel.chapter)
        put("isLongClick", isLongClick)                  // 长按（>666ms）为 true
    }
}
```

BaseSource.evalJS 自己还会补 `source`(=this)、`baseUrl`(=getKey())、`cookie`、`cache`。

> `SourceLoginJsExtensions`（`ui/login/SourceLoginJsExtensions.kt`）继承链
> `SourceLoginJsExtensions → RssJsExtensions → io.legado.app.help.JsExtensions`，
> 因此 `java.ajax / java.head / java.toast / java.longToast / java.openUrl / java.startBrowser /
> java.getCookie / java.getVerificationCode` **全可用**，另有 **TTS 专属 `java.clearTtsCache()`**
> （清 `cacheDir/httpTTS/` 并 `ReadAloud.upReadAloudClass()`），以及 `java.reLoginView()/upLoginData()`（重绘面板）。

### 3.5 style（`data/entities/rule/FlexChildStyle.kt`）

```kotlin
data class FlexChildStyle(
    val layout_flexGrow: Float = 0F,
    val layout_flexShrink: Float = 1F,
    val layout_alignSelf: String = "auto",   // auto/flex_start/flex_end/center/baseline/stretch
    val layout_flexBasisPercent: Float = -1F,// ★ 宽度百分比，0.31 ≈ 一行三个
    val layout_wrapBefore: Boolean = false,  // ★ 强制换行，做「整行标题」用
    val layout_justifySelf: String = "auto"  // 影响文字/文本对齐
)
```

---

## 4. url 规则写法：★JSON body 必须 `JSON.stringify`

### 4.1 错误示范（会静默无声）

```
{host}/tts,{"method":"POST","headers":{"Content-Type":"application/json"},"body":{"text":"{{speakText}}","voice":4001}}
```

`{{}}` 在 **URL 选项 JSON 解析之前**做字符串替换，所以正文里只要出现一个 `"`，
body 的 JSON 就断掉 → `GSONStrict.fromJsonObject<UrlOption>` 失败（fallback GSON 也失败）
→ `urlOption == null` → **method 保持 GET、body 丢失** → 请求退化成 GET →
服务端返回 JSON/HTML 错误体 → 被当音频播放 → **朗读无声且不报任何错**。
（正文含 `\` 也会破坏 JSON。）

### 4.2 正确写法：`<js>` 整段 + `JSON.stringify`

```
<js>var Q=String.fromCharCode(34);
var bd={text:String(speakText),voice:4001,speed:50,volume:50};
'http://host/legado/ifly'+','+'{'+Q+'method'+Q+':'+Q+'POST'+Q+','+Q+'headers'+Q+':'+'{'+Q+'Content-Type'+Q+':'+Q+'application/json'+Q+'}'+','+Q+'body'+Q+':'+JSON.stringify(bd)+'}'</js>
```

要点：
- JS 里**最后一条表达式**的值就是规则结果（Rhino `evaluateString` 的 completion value 语义），**不要写顶层 `return`**。
- `JSON.stringify(bd)` 自动转义 `"`、`\`、换行、控制字符 —— 实测正文
  `他说:"你好",C:\path\x` 与多段换行 全部正常。
- 拼 URL 选项 JSON 的双引号用 `String.fromCharCode(34)`（记作 `Q`）生成，
  于是**源文本零双引号零反斜杠**，MCP/剪贴板/JSON 多层转义都不会失真。

### 4.3 多级 host/音色可配置（书源变量）

```
var pv=String(source.get('prov'));if(pv!=='ifly'&&pv!=='minimax'){pv='ifly';}   // 兜底
var vc=parseInt(String(source.get('voice')),10);if(isNaN(vc)||vc<1){vc=(pv==='minimax')?6001:4001;}
```

`source.get()` 未设置返回 `""` → `String("")=""` → `parseInt("")=NaN` → 走默认值，
所以**刚导入不点任何按钮也能正常朗读**（这点很重要，否则用户第一耳就是哑的）。

---

## 5. 语速映射的源码级推导（最容易做错的地方）

```
HttpReadAloudService:  speechRate = AppConfig.speechRatePlay + 5
AppConfig:             speechRatePlay = if (ttsFlowSys) defaultSpeechRate else ttsSpeechRate
                       defaultSpeechRate = 5；ttsSpeechRate 默认 5（PreferKey.ttsSpeechRate）
ReadAloudDialog:       seekTtsSpeechRate.max = 45
                       显示文字 = upTtsSpeechRateText(v) = (v + 5) / 10f      // v = ttsSpeechRate
```

推导：
- `speakSpeed = ttsSpeechRate + 5`，默认 = **10**；
- 界面显示值 = `speakSpeed / 10`，默认显示 **1.0**，滑杆范围 **0.5 ~ 5.0**；
- 所以规则里拿到 `speakSpeed` 要按「站点默认=显示1.0」对齐，而不是按 0~100 直觉写。

推荐映射（案例实测）：

| 模式 | 公式 | 显示 0.5 | 显示 1.0（默认） | 显示 2.0 | 显示 5.0 |
|------|------|----------|------------------|----------|----------|
| **标准（推荐）** | `clamp(speakSpeed*5, 0, 100)` | 25 | **50 = 站点默认** | 100（站点上限） | 100 |
| 全范围 | `clamp(speakSpeed*2, 0, 100)` | 10 | 20（偏慢） | 40 | 100 |

> 站点自带规则生成器用的是 `{{speakSpeed * 2}}` —— 默认只给到 20，偏慢；
> 想「默认正常 + 有可用加速空间」用 `*5`，并把「全范围」做成按钮给慢速党。

```
var sp=parseInt(String(speakSpeed),10);if(isNaN(sp)){sp=10;}
var sd=(md==='wide')?sp*2:sp*5;if(sd<0){sd=0;}if(sd>100){sd=100;}
```

---

## 6. loginCheckJs：把「没声音」变成「看得见的报错」

TTS 最常见的故障是**服务端 4xx 被当音频播放**（`contentType` 是 `audio/mpeg` 却返回
`{"detail":"text is required"}`），表现就是「突然不出声」，App 日志里也没有明显异常。

```js
(function(){
  var b=result.body;
  if(typeof b==='function'){b=b.call(result);}      // ★ 跨版本：官方版 body 是属性，部分改版是方法
  var s=String(b);
  if(s.length<800){
    var low=s.toLowerCase();
    if(s.indexOf('detail')>=0||low.indexOf('<html')>=0||low.indexOf('<!doctype')>=0){
      throw new Error('起点TTS 返回异常：'+s.substring(0,120));   // ★ 必须 throw new Error
    }
  }
  return result;                                     // ★ 必须原样返回 StrResponse
})()
```

- 只对 **<800 字节**的响应做文本嗅探（正常音频动辄 10KB+，开销可忽略，也不误伤）。
- `throw new Error(msg)` 会一路传播到朗读错误提示与 App 日志（实测可见）。
- JS 探针实测 6 场景全通：正常长 body 放行 / `detail` 拦截 / HTML 拦截 /
  body 是方法（改版）拦截 / body 是方法 + 正常音频放行 / body=null 放行。

---

## 7. 生产模板（改 host 即可复用）

### 7.1 引擎 JSON（主引擎：动态音色）

```json
{
 "id": 1757600001001,
 "name": "起点TTS·音色切换",
 "url": "<js>var Q=String.fromCharCode(34);var pv=String(source.get('prov'));if(pv!=='ifly'&&pv!=='minimax'){pv='ifly';}var vc=parseInt(String(source.get('voice')),10);if(isNaN(vc)||vc<1){vc=(pv==='minimax')?6001:4001;}var md=String(source.get('smap'));var sp=parseInt(String(speakSpeed),10);if(isNaN(sp)){sp=10;}var sd=(md==='wide')?sp*2:sp*5;if(sd<0){sd=0;}if(sd>100){sd=100;}var bd={text:String(speakText),voice:vc};if(pv==='ifly'){bd.speed=sd;bd.volume=50;}'http://HOST/legado/'+pv+','+'{'+Q+'method'+Q+':'+Q+'POST'+Q+','+Q+'headers'+Q+':'+'{'+Q+'Content-Type'+Q+':'+Q+'application/json'+Q+'}'+','+Q+'body'+Q+':'+JSON.stringify(bd)+'}'</js>",
 "contentType": "audio/mpeg",
 "pauseDuration": 0,
 "concurrentRate": "1/200",
 "loginUrl": "（见 7.2 函数集，单行）",
 "loginUi": "[{...RowUi 数组，见 7.3...}]",
 "loginCheckJs": "（见第 6 节）",
 "header": "<js>var Q=String.fromCharCode(34);'{'+Q+'User-Agent'+Q+':'+Q+'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36'+Q+'}'</js>",
 "jsLib": null,
 "enabledCookieJar": false,
 "lastUpdateTime": 1750000000000
}
```

### 7.2 loginUrl 函数集（音色按钮 + 状态 + 测速 + 清缓存）

```js
function _g(k,d){var v=String(source.get(k));if(v===''||v==='null'||v==='undefined'||v==='NaN'){return d;}return v;}
function _name(v){if(v==='4001'){return '关山'}if(v==='4002'){return '筱潇'}return '未知';}
function pick(n,p,v){source.put('prov',p);source.put('voice',String(v));
  java.longToast('已切换音色：'+n+String.fromCharCode(10)+'引擎 '+p+' / 音色号 '+v);}
function ifly1(){pick('🎙 关山（讯飞）','ifly',4001);}
function mnmx1(){pick('📖 说书先生（Minimax）','minimax',6001);}
function curLabel(){return '当前音色：'+_name(_g('voice','4001'))+'（'+_g('prov','ifly')+' '+_g('voice','4001')+'）';}
function smapLabel(){return _g('smap','std')==='std'?'语速映射：标准':'语速映射：全范围';}
function smap(){var m=_g('smap','std');if(m==='std'){source.put('smap','wide');
  java.longToast('语速映射已切换为「全范围」'+String.fromCharCode(10)+'朗读语速显示 5.0 才是站点上限 100');}
  else{source.put('smap','std');java.longToast('语速映射已切换为「标准」'+String.fromCharCode(10)+'朗读语速显示 1.0 = 站点 50（正常语速）');}}
function stat(){java.longToast('朗读引擎：'+String.fromCharCode(10)+'当前音色：'+_name(_g('voice','4001'))+String.fromCharCode(10)+'语速映射：'+_g('smap','std'));}
function help(){java.longToast('① 点音色按钮切换（有提示即成功）'+String.fromCharCode(10)+'② 返回小说直接朗读即生效'+String.fromCharCode(10)+'③ 语速用朗读菜单滑杆调（显示 1.0 = 正常）');}
function tst(){var Q=String.fromCharCode(34);var pv=_g('prov','ifly');var vc=_g('voice','4001');
  var bd='{'+Q+'text'+Q+':'+Q+'你好，这是试听。'+Q+','+Q+'voice'+Q+':'+vc+'}';
  var u='http://HOST/legado/'+pv+','+'{'+Q+'method'+Q+':'+Q+'POST'+Q+','+Q+'headers'+Q+':'+'{'+Q+'Content-Type'+Q+':'+Q+'application/json'+Q+'}'+','+Q+'body'+Q+':'+bd+'}';
  var t0=new Date().getTime();
  try{var s=String(java.ajax(u));var ms=new Date().getTime()-t0;
    if(s.length>800){java.longToast('✅ 合成成功'+String.fromCharCode(10)+'返回 '+s.length+' 字节 / '+ms+' 毫秒');}
    else{java.longToast('⚠️ 返回异常（'+s.length+' 字节）：'+s.substring(0,120));}}
  catch(e){java.longToast('❌ 连接失败：'+String(e).substring(0,150));}}
```

> 加一个「🔊 连通测试」按钮的收益极高：**用户报「没声音」时，第一步点它就能区分
> 「服务挂了 / 音色号错 / 网络不通」，而不是在规则里瞎猜。**

### 7.3 loginUi（RowUi 数组）

```json
[
 {"name":"ℹ️ 当前音色","type":"button","viewName":"curLabel()","action":"stat()",
  "style":{"layout_flexBasisPercent":1.0,"layout_wrapBefore":true}},
 {"name":"🎙 关山","type":"button","action":"ifly1()","style":{"layout_flexBasisPercent":0.31}},
 {"name":"🎙 筱潇","type":"button","action":"ifly2()","style":{"layout_flexBasisPercent":0.31}},
 {"name":"🎙 聆小琪","type":"button","action":"ifly3()","style":{"layout_flexBasisPercent":0.31}},
 {"name":"📖 说书先生","type":"button","action":"mnmx1()","style":{"layout_flexBasisPercent":0.31}},
 {"name":"🦊 狐狸小姐","type":"button","action":"mnmx2()","style":{"layout_flexBasisPercent":0.31}},
 {"name":"🎚","type":"button","viewName":"smapLabel()","action":"smap()","style":{"layout_flexBasisPercent":0.68}},
 {"name":"🔊 连通测试","type":"button","action":"tst()","style":{"layout_flexBasisPercent":0.31}},
 {"name":"🧹 清语音缓存","type":"button","action":"java.clearTtsCache()","style":{"layout_flexBasisPercent":0.5}},
 {"name":"❓ 使用说明","type":"button","action":"help()","style":{"layout_flexBasisPercent":0.48}}
]
```

### 7.4 何时改用「多引擎」而不是「多按钮」

| 方案 | 优点 | 缺点 |
|------|------|------|
| **单选引擎 + 音色按钮** | 朗读菜单里只占 1 个引擎位；一套规则管所有音色；能塞测速/清缓存等运维按钮 | 换音色要进「编辑 → ⋮ → 登录」，3 步 |
| **多引擎（每音色一个）** | 朗读菜单/引擎列表里**2 步切换**，无需进登录界面 | 引擎列表变长；每个都要维护 url |

**最佳实践：两者都给。** 主引擎（带按钮）+ N 个单音色引擎（相同 url 规则、写死 prov/voice）。
案例里两者字节数逐字节一致（动态取变量路径 = 写死路径），说明模板可共用。

---

## 8. 验证方法论（离线三道 + 真机三道）

### 8.1 离线（推送前拦住低级错）

1. **JSON/结构自检**：字段齐全、`header` 是 JSON 对象字符串、`loginUi` 能 `json.loads`、按钮 action/viewName 都能编译。
2. **`node --check` 每个 JS 块**（url / loginUrl / loginCheckJs）。
3. **语义仿真**（★最有价值）：
   - **url 规则仿真**：`new Function('source','speakText','speakSpeed','code','return eval(code);')`
     —— 必须用 `eval` 取「最后一条表达式的值」，`new Function` 直接执行**不会**返回末表达式值
     （与 Rhino 的 completion value 语义对齐）。
     用 stub `source.get/put` 造 8 组用例：全新安装 / 各音色 / 含引号换行反斜杠表情 / 语速各档 / wide。
     断言：URL 正确、`JSON.parse(选项)` 通过、`body.text` 与输入**逐字符相等**、speed 合法。
   - **按钮函数仿真**：把 `loginUrl` 整段用 `new Function` 跑起来，逐按钮调用并断言
     「写的变量对不对 / toast 文案含音色名且无 undefined、NaN / tst() 拼出的 URL 能被解析且音色=当前音色」，
     最后把按钮写入的变量直接喂给 url 规则做**联动断言**。

### 8.2 真机（MCP）

```
save_tts(引擎JSON)            → 推送
get_tts(id)                   → 回读，与本地文件做**字段级/字节级**比对（防传输层转义损坏）
test_tts(id, 文本)            → 真实走 AnalyzeUrl + header + loginCheckJs，返回「字节数/耗时」
eval_js(loginUrl代码 + stub)  → 在真机 Rhino 里实跑每个按钮函数（源文本零双引号，可直接当双引号字面量嵌入）
```

**证明「音色真的生效」的干净办法**：同一句文本跨引擎 `test_tts`，比对**字节数**；
再用服务端同文本 **md5** 交叉验证（`/api/voices` 里 identifier 相同的两个音色号，音频 md5 也可能不同）。
案例：`15120 / 14688 / 14688 / 33006 / 33006` 与沙盒 md5 表完全对应；主引擎与写死版同文本同字节数。

---

## 9. 跨版本 / 跨 App 兼容清单

| 风险点 | 表现 | 写法 |
|--------|------|------|
| `StrResponse.body` | 官方版是属性；部分改版是方法（`result.body` 返回函数引用） | `var b=result.body;if(typeof b==='function'){b=b.call(result);}` |
| `loginUi` v2 | 新版支持 `<js>` 返回 UI 描述（`isLoginUiV2()`）；**经典 RowUi 数组仍完全支持** | 优先经典 RowUi（跨版本稳），别赌 v2 schema |
| `type:"label"` | 源码里 `when(type)` 只实现了 text/password/button/toggle/select，label 不渲染 | 状态文字用 **button + 动态 viewName** 代替 |
| `jsLib` | 部分 App 版本 jsLib 作用域里 `java.ajax/source` 不可用或受限（历史踩坑） | **按钮函数与 url 规则自包含，不依赖 jsLib** |
| 顶层 `return` | Rhino `evaluateString` 不允许顶层 return | 末表达式出值；需要多步时用 IIFE `(function(){...return x;})()` |
| `new Date().getTime()` / `String.fromCharCode` | 全版本可用 | 计时/换行/引号一律用它，别用模板字符串（QuickJS/部分引擎不支持反引号） |
| `pauseDuration` | 新版字段，老版 App 可能忽略 | 用 0 保证兼容 |

---

## 10. 踩坑清单（本次真实翻车，全部已在构建脚本里加自检）

1. **多段 Python 字面量拼 JS 时漏掉 `+Q+`** → 生成 `':'{` → JS 语法错（`Unexpected token '{'`）。
   构建脚本必须内置 `node --check`，别靠肉眼。
2. **Python `%` 格式化渗进 JS**：`'服务地址：%s' % HOST` 写在 Python 字符串里没被替换 →
   JS 里留下字面量 `%s`，且 `'提示：…' % HOST` 变成了 JS 取模 → toast 显示 `NaN`。
   → 用 `@@HOST@@` 占位符 + `.replace()`，别在长模板上用 `%`。
3. **`new Function(code)` 不返回末表达式值** → 仿真必须 `return eval(code)`。
4. **`':'+Q+'{'` 这类拼接看起来对、实际错**：URL 选项 JSON 里内层对象 `"headers":{` 前面
   **必须再补一个 `+Q+`**（`+Q+':'+Q+'{'`）。仿真里断言 `JSON.parse(选项)` 通过即可拦住。
5. **`test_tts` 用不同文本对比字节数会误判音色**（长度可能撞车）→ 必须**同一文本**+服务端 md5。
6. **错误响应被当音频**：不加 `loginCheckJs` 时表现为「无声」，排查成本极高（见第 6 节）。
7. **源文本里的双引号/反斜杠**：在 MCP/剪贴板/多层 JSON 转义下极易损坏 →
   一律 `String.fromCharCode(34)` / `(10)` / `(39)` 生成，推完用 `get_tts` 回读比对。

---

## 11. 案例：起点 TTS 控制台（站点档案 + 实测）

**服务**：FastAPI，IFly + Minimax 双引擎，自带 Legado 规则生成器。

| 接口 | 说明 |
|------|------|
| `GET /api/health` `/api/voices` `/api/network` | 健康、音色表、本机网卡地址 |
| `POST /api/tts/{ifly\|minimax}` | body: `text`+`voice_type`(+ifly `speed`/`volume`) |
| `GET\|POST /legado/{provider}` | **Legado 专用入口**：body `text`+`voice`(+ifly `speed`/`volume`)；**GET 不支持**，缺 text 返回 `{"detail":"text is required"}` |
| `GET /api/legado/rules?base_url=&provider=&voice_type=` | 生成规则（注意它给的是 `{{speakSpeed * 2}}`，默认偏慢） |

- 音色：ifly `4001`关山 / `4002`筱潇 / `4003`聆小琪；minimax `6001`说书先生 / `6002`狐狸小姐。
  `/api/voices` 里 4002/4003 的 identifier 相同（控制台标注"同筱潇"），但**音频 md5 不同**，5 个都能用。
- 5000 字上限；无 UA 要求、无频控；错误用 HTTP 400 + `{"detail":...}`。
- 实测延迟：ifly 0.4~2.4s（128 字 → 172KB / 2.3s），minimax ≈3.7s 且**不吃 speed**。
- 成品：6 引擎（主引擎 `1757600001001` 音色切换版 + 5 个单音色版），
  `concurrentRate=1/200`、`pauseDuration=0`、`enabledCookieJar=false`。

**复用清单（换站只改这些）**：
1. `HOST`（url 规则 1 处 + loginUrl 里 `stat()`/`tst()` 各 1 处，**共 3 处**）
2. 音色表（`_name()` 映射 + 按钮函数 + `loginUi` 行）
3. 请求契约（provider 路径段、body 字段名 text/voice/speed/volume）
4. 语速映射系数（站点 speed 语义是 0-100 默认 50 → `*5`；别的站点按「默认值对齐」重算）
