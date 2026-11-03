# 方法-动态线路host的模板占位符双坑（exploreUrl JS生成发现页 + check_source 才暴露）

> 来源：花都动漫 v2.0 修复（2026-11-03）。两个坑都在「把可切换 host 写进发现页 kind URL」这个需求下触发，
> 且 **debug_source 全绿、唯独 check_source 失败**，极易误判为校验器误报。

## 背景架构

发布页线路管理面板：登录面板 `FQ_switch(h)` 把用户选的 host 存 `source.put('hdHost',h)`；
发现页/搜索页 URL 里的 `{{}}` 占位符运行时读取该变量拼接 host。

## 坑 1：外层 `<js>` 里的 `{{}}` 占位符不能与内部表达式共用单引号语境

**症状**：check_source 报 `Expected URL scheme 'http' or 'https' but was 'com.script.ScriptException'`——
ScriptException 的**异常文本本身被当成了 URL** 去请求。

**根因**：
- `AnalyzeUrl.replaceKeyPageJs()` 对 URL 做 `{{...}}` 内嵌求值；**`<js>` 外层脚本同样先过这一步**（{{}} 优先于 `<js>` 求值）。
- 首版把 host 占位符嵌进外层脚本的**单引号字符串**：`var H='https://{{(function(){...source.get('hdHost')...})()}}';`
  内层表达式里也有单引号 → 外层字符串字面量被截断 → 整个外层脚本语法错误 → 求值抛 ScriptException。
- 求值异常时 Legado 把 `com.script.ScriptException` 的 message 拼进 URL 继续走，
  于是 `getAbsoluteURL` 收到一个以异常类名开头的"URL"，报 `Expected URL scheme ... but was 'com.script.ScriptException'`。

**修法（两条铁律）**：
1. **外层 `<js>` 生成脚本必须自包含**：不引用 `source`/`java`（它们的绑定在 check_source 的
   `exploreKinds()` 求值环境里可能缺失/行为不同），需要动态值一律放进 kind URL 的 `{{}}` 占位符。
2. **kind URL 里的 `{{}}` 占位符必须包在双引号字符串里**，占位符表达式内部只允许用单引号：
   ```js
   // ✅ 正确形态
   function pg(slug){
     return "{{(function(){var h='';try{h=String(source.get('hdHost')||'');}catch(e0){}return ...;})()}}/vodshow/"+slug+"------{{...page...}}---.html";
   }
   ```
   这样外层脚本里没有任何嵌套引号冲突，能原样编译；`{{}}` 在后续 URL 求值时才被替换。

**验证手段**：`eval_js` 里对 `source.getExploreUrl()` 做 `new Function(code)` 编译检查。
注意：**改完必须重新 save_source 再验证**——eval_js 读的是已保存书源，旧版验证结果会误导（本次实测踩过）。

## 坑 2：kind URL 的 host 占位符返回值必须带协议，否则被当相对路径

**症状**：check_source 报"发现失效"，HTTP 日志里实际请求：
```
GET https://hd.huadudm.com/hd.huadudm.com/vodshow/zhongwenzimu--------1---.html -> 404
```
host 重复拼接。

**根因**：host 表达式返回了裸 `hd.huadudm.com`（不带 `https://`），
kind URL 整串变成 `hd.huadudm.com/vodshow/...`，
`NetworkUtils.getAbsoluteURL(baseUrl, url)` 判定无 scheme → **按相对路径拼到 baseUrl 后面**。
搜索页没事是因为 searchUrl 写死 `https://{{host}}` 前缀。

**修法**：占位符表达式内自己保证输出完整绝对 URL：
```js
return (h.indexOf('.')>0)?('https://'+h):'https://hd.huadudm.com';
```
或者模板外层写死协议 `https://{{host表达式只返回host}}` —— 两者选一，不能两头都带协议（会 https://https://）。

## 为什么 debug_source 全绿也必须跑 check_source

`debug_source` 的发现页调试传 `名称::URL`，URL 是直接给的，**完全绕过 exploreUrl 外层脚本和 kind URL 占位符求值**。
所以「debug 发现页正常 + check_source 发现失效」≠ 校验器误报，而是 exploreUrl 生成链路只在 check/真发现页走。
本次两坑全部只在 check_source 暴露。

## 排查模板（复用）

```js
// eval_js：编译检查已保存书源的 exploreUrl
var raw=String(source.getExploreUrl());
var m=raw.match(/^<js>([\s\S]*)<\/js>\s*$/);
var code=m[1];
new Function(code);          // 先编译
var arr=JSON.parse((new Function('return '+code))());  // 再求值（自包含脚本应成功）
arr.length;                   // kinds 数量
// 再模拟占位符替换：arr[i].url.replace(/\{\{([\s\S]*?)\}\}/g, eval each with page/source stubs)
```
配合 `get_http_logs` 看 check_source 实际请求的 URL 形态——404 的畸形 URL 直接指出占位符产物问题。

## eval_js 调用 loginUrl 函数的正确姿势

eval_js 用的是**空白书源环境**，不加载目标书源的 loginUrl 函数（`FQ_xxx is not defined` 是预期现象）。
要验证 loginUrl 里的函数，用括号配平法摘出函数源码注入当前作用域执行：

```js
var code=String(source.getLoginUrl());
function grab(name){
  var i=code.indexOf('function '+name+'(');
  if(i<0) return '';
  var depth=0,j=code.indexOf('{',i),k=j;
  for(;k<code.length;k++){
    if(code.charAt(k)==='{') depth++;
    else if(code.charAt(k)==='}'){ depth--; if(depth===0) break; }
  }
  return code.slice(i,k+1);
}
var seg=grab('getPub')+grab('FQ_fetchLines')+grab('toast')+grab('refreshUi');
var fn=new Function('source','java', seg+'; return FQ_fetchLines();');
fn(source,java);
```
