# Legado 规则语法陷阱大全 —— 实战踩坑记录（附复现与解法）

> 全部来自真实调试，每条都附错误现象与验证方法

## 1. `@js:` 规则字符串内不能包含 `##`

**现象**：wordCount 规则 `@js: ... java.getString('.t_c.2@text##字数：') ...` 报错
`字符串文字没有限制`（unterminated string literal），脚本在 `##` 处被截断。

**原因**：Legado 规则解析器**先于 JS 执行**处理 `##`（正则替换分隔符），把 `##` 之后的内容当成替换参数，JS 被腰斩。

**解法**：`##` 处理移入 JS 内部：

```javascript
// ✗ 错误
java.getString('.t_c.2@text##字数：');
// ✓ 正确
var w = String(java.getString('.t_c.2@text'));
w.replace('字数：', '');
```

## 2. `:contains()` 不是 Legado 规则语法

**现象**：`@css:.info dl dt:contains(分类) + dd a@text` 返回空。
**原因**：Legado 规则引擎不支持 `:contains()`（jsoup 原生支持但规则层不透传）。
**解法**：改用索引定位。如 `.info@dl.0@dd@a@text`（第0个dl里的dd>a）。
**教训**：写规则前先确认语法在 Legado 体系内有效，jsoup 能跑 ≠ Legado 能跑。

## 3. 顶层 `return` 不可靠

**现象**：`<js>...</js>` 规则内顶层 `return JSON.stringify(res);` 报 `返回的值无效`。
**原因**：部分执行路径把 JS 当顶层脚本而非函数体，顶层 return 非法。
**解法**：用 if/else 结构隔离分支，让每个分支自然流到末尾表达式；必须提前退出的用 IIFE 包裹（如 `(function(){ ... return x; })()`）。

## 4. Java String 与 JS String 混用

**现象**：`source.getVariable()` 返回空时，`"" || "{}"` 不生效，`JSON.parse` 报 `Empty JSON string`。
**原因**：Rhino 里 Java String 即使为空也是 truthy 对象，`||` 短路失效。
**解法**：

```javascript
// ✗ d = JSON.parse(source.getVariable() || "{}");
// ✓
var v = String(source.getVariable() || "");
var d = v.length ? JSON.parse(v) : {};
```

同理 `java.ajax()` 返回的 Java String 调 `.replace()` 会报方法重载歧义：
`对应于 JavaScript 参数类型 (object,string) 的 Java 方法 java.lang.String.replace 的选择不明确`
**解法**：一律 `String(...)` 包裹后再用 JS 方法。

## 5. ConsString 拼接串问题

**现象**：JS 拼接的字符串（`a + b`）传给某些 Java 方法时行为异常。
**解法**：拼接结果传给 Java API 前统一 `String(...)` 包装。所有 `java.get/post/ajax` 的 url 参数建议都包。

## 6. `source.header` 只作用于分析器请求

**现象**：书源 header 设了移动 UA，JS 里 `java.get(url)` 发出的请求仍是默认 UA，触发 WAF。
**原因**：JS 的 java.* 网络方法需要**自己传 headers**。
**解法**：

```javascript
var hd = {"User-Agent": "移动端UA", "Accept-Language": "zh-CN,zh;q=0.9"};
java.get(url, hd)
// POST: java.post(url, body, hd)
// 或选项对象: java.ajax(url + "," + JSON.stringify({body, method, headers: JSON.stringify(hd)}))
```

排查工具：开启 HTTP 日志，对比 JS 请求与分析器请求的实际 UA/Cookie。

## 7. StrResponse 没有 `.code()`

**现象**：`java.get(url).code()` 报 `找不到函数 code`。
**解法**：Legado StrResponse 常用方法是 `.body()`、`.headers()`、`.header(name)`。状态码判断改用内容特征（如 WAF 页特征串）。

## 8. `header("Location")` 大小写

okhttp 头查找大小写不敏感，`resp.header("location")` 与 `"Location"` 均可；但注意 POST 默认**跟随重定向**，若要拿 302 的 Location 需确认该客户端配置，或直接用 `resp.header("Location")`（跟随前仍可取到头）。

## 9. `@js:` 内嵌正则的转义层级

JSON 里的规则字符串，正则要经过 **JSON 转义 + JS 转义**两层：

```
JS源码:   /window\.open\('([^']+)/
JSON存储: "window\\\\.open\\\\('([^']+)/"
```

手写易错，建议用 Python `json.dump` 生成而非手拼。

## 10. 发现页 select 控件的取值时机

`infoMap['域名']` 在脚本执行时才求值；切换下拉后必须 `java.refreshExplore()` 重跑脚本，且脚本里要 `SET('server', infoMap['域名'])` 持久化——其他规则（搜索/详情）读的是持久化变量，不是 infoMap。

## 11. `webView:true` 的代价

章节 URL 追加 `,{"webView":true}` 可过部分 JS 挑战，但每章都起 WebView：实测 13 页目录耗时 25 秒（每页注册 ServiceWorker）。能用 okhttp 直连的站不要用 webView。

## 12. 搜索 URL 的返回格式

searchUrl @js 返回值可以是：
- 纯 URL 字符串（GET）
- `url,{json选项}` 逗号拼接（POST 等），如：
  `baseHost + '/?action=search,' + JSON.stringify({"method":"POST","body":body})`
- 返回 `''` 表示放弃本次搜索（如关键词校验不过）

## 13. 调试方法论

1. **分层定位**：先 eval_js 手动复现 JS 逻辑（快），再 debug_source 验证完整管道（准）
2. **HTTP 日志**：`set_http_log_recording(true)` 后对比"预期请求"与"实际请求"的 UA/Cookie/头差异
3. **逐段打日志**：`java.log()` 输出中间变量，debug 日志里看断点位置
4. **最小复现**：把可疑规则单独拎到 eval_js 里跑，排除管道干扰
