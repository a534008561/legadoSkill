# 方法：CF拦截切备用域三坑（charset触发nginx403 / 相对URL主域补齐 / check_source动态exploreUrl假阴性）

> 来源：2026-11-16 轻小说文库(www.wenku8.net)书源全链路修复实战。
> 适用：主域被 Cloudflare 拦、需整体切到备用域；或"eval 能拿到数据但 debug/体检失败"的排查。

---

## 背景现象

用户报"搜索没结果"。书源原本一切正常（历史全绿），突然全链路失效。
排查发现是**三层叠加**，任何一层没看破都会卡住。

## 坑一：主域被 CF 全站 Challenge，必须切备用域

- 主域 `www.wenku8.net` 连**首页**都返回 Cloudflare：
  - 有时是 `Just a moment...`（Challenge 页，HTTP 403，LEN≈6000）
  - 有时是 `Sorry, you have been blocked`（WAF 直接封，LEN≈6000）
- 对照实验：`eval_js` 里 `java.connect` 分别请求 `.net / .cc / .com`：
  - `.net` 全路径 403（含首页、详情、正文）
  - `.com` 同样被 CF 拦
  - **`.cc` 首页/详情/目录/正文/榜单全 200**
- 结论：主域不可用时，不要死磕过盾，先系统测所有备用域的全路径可达性（用 `java.connect` 批量探测，打印 CODE/LEN/标题/关键结构锚点如 373px）。

## 坑二：备用域 nginx 对 `charset=gbk` query 参数返回 403，option 语法可绕过

这是本次最关键、最反直觉的一坑。

**现象**：`www.wenku8.cc` 上：

```
# 触发 403（LEN=139 nginx 错误页）
.../search.php?...&charset=gbk
.../search.php?...&charset=GBK       # 大小写无效
.../search.php?charset=gbk&...       # 换位置无效
.../search.php?...&%63harset=gbk     # 编码键名无效

# 200 正常
.../search.php?searchtype=...&searchkey=...&page=1
```

只要真实 query 里出现 `charset=...`（任何形态）就 403。

**解法**：Legado 的 charset 不必放 query，放到**逗号 option** 里：

```
# 书源 searchUrl / exploreUrl 条目 URL 写法
https://www.wenku8.cc/modules/article/search.php?searchtype=articlename&searchkey={{key}}&page={{page}},{"charset":"gbk"}
```

- option 里的 `charset` 是 Legado AnalyzeUrl 的指令，**不会进入 HTTP 真实 query**，故不触发 .cc 的 nginx 403。
- AnalyzeUrl 源码级事实：`encodeParams` 用 option 的 charset 编码 `{{key}}`，`OkHttpUtils.text` 用同一 charset 解码响应 —— 所以 GBK 编码 + GBK 解码一步到位。
- 由此 `{{java.encodeURI(key,"GBK")}}` 可简化为 `{{key}}`（后者更稳：裸环境跑 encodeURI 会抛 ScriptException）。
- 验证方法：debug 日志里书名中文正常（`关于我帮助迷路小女孩后…`）即解码正确；出现 `title=t`/乱码则是解码失败。

**注意 exploreUrl 的 `<js>` 内嵌（★★交付后翻车点，务必重视）**：option 的 `{"charset":"gbk"}` 写在 JS **双引号字符串**里必须转义为 `{\"charset\":\"gbk\"}`（JS 源码里恰好 1 个反斜杠），否则字符串被提前闭合，整个 `<js>` 编译报 `ScriptException: 在属性列表的后面缺少 "}"`（属性列表=对象字面量 `{...}`）。

真实翻车复盘：批量替换 `&charset=gbk&page=` → `&page=...,{"charset":"gbk"}` 时用了裸双引号，103 处全错；但当时**只测了 `debug_source key="::URL"` 直连**（该模式跳过 `<js>` 编译，直接请求给定 URL）和搜索路径，**都没触发 `<js>` 编译**，结果交付后用户一开发现页就报错。

**★★验证铁律（动态 `<js>` exploreUrl 必做）**：

```
// eval_js 里执行整个 <js> 全文，复现 App 编译
var ex=String(source.exploreUrl||'');
var code=ex.replace(/^<js>/,'').replace(/<\/js>\s*$/,'');
var out=eval(code);          // 抛错=语法坏，等同用户看到的 ScriptException
var arr=JSON.parse(out);     // 确认输出合法 JSON
java.log('count='+arr.length+' item1='+arr[1].url);
// 切换分支再验：source.put('wkmode','标签'); eval(code) ...
```

- `::URL` 直连测不到 `<js>` 编译错误，不能代替此验证。
- 转义层数核对法：读回字符串后定位 `charset` 前字符，`ord==92`（单个反斜杠）才对；终端 `repr`/JSON dump 显示的 `\\` 是转义假象，别据此误判层数。
- JS 求值后 `{\"charset\":\"gbk\"}` → `{"charset":"gbk"}`（真双引号），再 `JSON.stringify` 自动转义回来，`JSON.parse` 正常。

## 坑三：相对 URL 被 bookSourceUrl 主域补齐 —— eval 与 debug 结果矛盾的根因

**最迷惑的现象**：

- `eval_js` 里手写 `java.connect('https://www.wenku8.cc/...')` → 拿 373 卡片，正常。
- `debug_source` 跑同一书源 → 一直"列表大小 0"，即使规则一字不差。

排查手段（关键）：**用 `get_http_logs` 看 App 真实发出的请求 URL**，不要只看 debug 日志里的"获取成功:..."（它显示的是规则里的相对串）。

日志实锤：

```
GET https://www.wenku8.net/modules/article/search.php?... -> 403   ← debug 实际发这里
GET https://www.wenku8.cc/modules/article/search.php?...  -> 200   ← eval 发这里
```

根因：searchUrl 写成相对路径 `/modules/article/search.php?...`，AnalyzeUrl 用 **bookSourceUrl 的主域**（`.net##`）补齐 host。就算在 exploreUrl/规则 JS 里写了 `.cc`，searchUrl 的相对串仍指向被封的 `.net`。

**解法**：searchUrl 必须写**绝对 URL**：

```
# 错（相对，被主域补齐到 .net）
/modules/article/search.php?searchkey={{key}}...

# 对（绝对 .cc）
https://www.wenku8.cc/modules/article/search.php?searchkey={{key}}...
```

## 坑四（附带）：check_source 对动态 `<js>` exploreUrl 的假阴性

修完后 `check_source` 报 `Expected URL scheme ... but was 'com.script.ScriptException'`，但 debug 全链路全绿。

二分实验定位（用临时主键克隆，不动正式源）：

- isoA：保留动态 `<js>` exploreUrl、清空 loginUrl/loginUi/jsLib → **体检失败**
- isoB：exploreUrl 改静态、保留完整登录 JS → **体检通过**

结论：ScriptException **只来自动态 `<js>` exploreUrl 在 check 裸环境的执行**（无 source/java 绑定），登录 JS 本身没问题。这是"登录站 + 动态发现页"书源的**体检固有局限**，不影响真实使用。

处置原则：不要为过体检去改坏正常功能（用户偏好：只改点名的、不动正常部件）。如实说明"体检假阴性、真机全绿"即可。

## 坑五（附带）：单结果 302 跳详情无需自己写兜底

精确书名搜索时站点返回 302 到 `/book/{aid}.htm`，Legado 原生链路完美处理：

```
≡检测到重定向(302) → 重定向后地址 /book/3115.htm
≡链接为详情页 → 执行详情页初始化规则
≡已获取目录链接,跳过详情页 → 目录 → 正文
```

不要在 bookList 的 @js 里加"无卡片则构造详情书"的兜底——那是多余的，且未验证的代码只会引入风险（本次试加后主动回退保持纯净）。

## 标准排查清单（切备用域类修复）

1. `java.connect` 批量探测主域/各备用域的首页+详情+搜索，打印 CODE/LEN/标题/结构锚点 → 定可用域。
2. 检查各 URL 的 query 是否含触发 WAF 的参数（如 charset）→ 尝试移到 option。
3. **searchUrl 必须绝对 URL**（相对串会被主域补齐）。
4. debug 与 eval 矛盾时，第一反应查 `get_http_logs` 的真实出口 URL。
5. charset 用 option 的写法，中文解码用书名正常与否验证。
6. check_source 失败先二分（静态化 exploreUrl）再定性，别动正常功能。
7. 交付闭环：LAN `saveBookSources` → `getBookSource` 回读 md5 → debug 全链路 → （体检假阴性如实标注）。
