# 方法：AEGIS-ALTCHA 盾 E 版兼容与双版本 WebView 通道

> 来源：2026-11-25 半夏小说（www.banxia.tw）书源制作。LT 版全程正常、E 版（legado-E 最新 main）搜索/发现全 0，
> 经诊断源水印法定位到三个叠加坑，均已修复。本文沉淀可复用的双版本过盾配方。

## 0 一句话结论

**AEGIS-ALTCHA 盾必须走 Legado 后台 WebView 通道；两版 API 签名虽一致，但 E 版有三个专属坑：
`webViewGetSource` 第 3 参 js 必须显式传字符串、loginCheckJs 失败绝不能 throw、面板按钮不能在 UI 线程调 webView。**

## 1 站点盾型判据

- 原生请求（OkHttp/Cronet）全部 `403 + x-mitigated: challenge + <altcha-widget>` 验证页；
- 验证页 challenge 的 `keyPrefix` 若长达 **32 hex**，是 deny-by-design（给非浏览器指纹的不可解挑战），
  别写 PoW 求解器，必须换通道；
- 浏览器档挑战前缀很短，WebView 内 `auto="onload"` 的 widget 能自动水解并 reload；
- UA / Client Hints 对照实验对 deny 无效——**判级只看 TLS/JA4 指纹**。

## 2 三坑详解

### 坑 1：E 版 `webViewGetSource` 第 3 参 js 必须显式传字符串
```js
// ✗ LT 能过、E 版拿验证页：
java.webViewGetSource('', u, null, '', false, 5000)
// ✓ 两版都过（诊断实测 E 版 len=6893 / altcha=-1 / title=真结果页）：
java.webViewGetSource('', u, 'document.documentElement.outerHTML', '', false, 5000)
```
两版 `StrResponse` 构造器/包名（`io.legado.app.help.http.StrResponse`）、`webViewGetSource` 6 参签名、
`loginCheckJs` 的 `as StrResponse` 调用点全部一致；差异在 E 版对 `js=null` 默认 JS 的处理不稳定。
**生产配方：永远显式传 js 字符串，不依赖默认 JS。**

### 坑 2：loginCheckJs 过盾失败时绝不能 throw
E 版 `WebBook.kt`（以及 LT 类似）的 loginCheckJs 调用链：
```kotlin
runCatching { evalJS(checkJs, resp) as StrResponse }.getOrElse {
    val errResponse = getErrStrResponse(it)
    (evalJS(checkJs, errResponse) as StrResponse).also { if (it.code()==500) throw it }
}
```
若你的脚本在过盾失败时 `throw new Error(...)`，E 版会拿 errResponse **二次调用**你的脚本，再 throw →
搜索整体抛异常 → 搜索全 0 + 白屏。
**正确写法：失败时降级返回原响应**：
```js
(function(){
  var r=result, b=''; try{b=String(r.body());}catch(e){}
  if (b.indexOf('altcha-widget')<0 && b.indexOf('aegis_altcha')<0) return r;
  var u=String(r.url()), src=null;
  try{src=java.webViewGetSource('',u,'document.documentElement.outerHTML','',false,5000);}catch(e){}
  var t=src?String(src):'';
  if (t.length>800 && t.indexOf('altcha-widget')<0) {
    return new Packages.io.legado.app.help.http.StrResponse(u,t);
  }
  return new Packages.io.legado.app.help.http.StrResponse(u,b);  // ★降级，不 throw
})()
```

### 坑 3：登录面板按钮在 UI 线程，不能调 webView
E 版 `JsExtensions.webViewGetSource` 源码：
```kotlin
if (isMainThread) error("webViewGetSource must be called on a background thread")
```
按钮 action 环境有 `java`（SourceLoginJsExtensions）但运行于 UI 线程，直接调 webView/webViewGetSource 会抛异常
并卡住 WebView 池（现象：按钮报错 → 打开网站白屏一直加载）。
**面板配方**：检查状态用后台通道（`java.ajax(url + ',{"webView":true}')`）或显式 JS 的 webViewGetSource
（若该 App 版本面板 action 在后台）；过盾/打开网站用 `java.startBrowser`（UI 线程安全）。
所有按钮各阶段 Toast 提示。

## 3 诊断方法（E 版无法 evalJs / WS 调试断连时）

E 版 LAN WS（HTTP 端口 + 1，如 1125 → 1126）的 `/bookSourceDebug` 在解析阶段必断连（清空规则也断，
属调试通道本身不稳，**不可作判据**）。用「诊断源水印法」：
1. 建一个新 origin 的诊断源（如 `https://site#e_diag`），避免 BookSource 内存缓存旧规则；
2. 在 loginCheckJs 里把 `webViewGetSource` 的返回/异常**拼进搜索结果第一本书的书名**：
   `DIAG OK len=6893 altcha=-1 title=...` 或 `DIAG EXCEPTION:...`；
3. 在 E 版搜任意词，直接读书名拿诊断结果——一次定位「能过盾/抛异常/拿验证页」三种状态。

**同 origin 反复覆盖会缓存旧 BookSource**：改了规则现象不变时，换新 origin 重存再测，别误判「改动无关」。

## 4 生产交付清单（两版通用）

1. `loginCheckJs`：显式 js 字符串 + 不 throw 降级 + altcha 哨兵判断；
2. `concurrentRate` 设小值（如 `2/1500`）；
3. 面板：检查/过盾/打开三按钮，UI 线程安全，各阶段 Toast；
4. LT 版 `debug_source` 回归全链路（改 E 兼容不能坏 LT）；
5. E 版用「新 origin + 诊断水印」验证过盾链路，再切回正式源；
6. 目录翻页字段是 `ruleToc.nextTocUrl`（**不是** `nextContentUrl`，后者是正文字段，GSON 静默丢弃）。

## 5 关联

- [[方法-AEGIS-ALTCHA验证与WebView通道书源]]（双通道总纲：被动拦截式 + 主动预取式）
- [[书源规则易错点]]（nextTocUrl 字段名坑）
