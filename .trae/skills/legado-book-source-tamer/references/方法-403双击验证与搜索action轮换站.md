# 方法：403双击验证站 + 搜索action轮换 + 搜索限频（xsbook 顶点小说实战）

> **沉淀来源**：🐾顶点小说xsbook（http://www.xsbook.org）修复实战（261031）。
> 该站集齐三类机制：①403双击Cookie验证 ②搜索action路径轮换 ③搜索接口30秒限频+惩罚叠加。
> Tengine 服务器、杰奇CMS风格，这三招在中小小说站中极具代表性。

---

## 一、403双击验证（核心机制）

### 1.1 站点行为

```
新会话(无Cookie)首击  → 403 + Set-Cookie × 2（时效Cookie 2h + session Cookie 10天）
带Cookie二击          → 200 正常页面
不带Cookie再击        → 仍403（每次403都重发新Cookie）
```

403 页面内容固定 110 字节：`<html>...<title></title>...<script> window.location.href ="/"; </script>`

### 1.2 甄别方法

- curl/python 裸请求 → 403，读 `Set-Cookie` 头
- 带 Cookie 重发 → 200 ⇒ 双击验证实锤
- 与 Cloudflare 区分：CF 是 JS 挑战计算，本类站点是纯服务端 Cookie 门槛，**无需执行 JS**

### 1.3 Legado 解法（源码级，已实测）

**三件套缺一不可**：

```json
{
  "enabledCookieJar": true,
  "searchUrl": "http://www.xsbook.org/search3d.html?searchkey={{key}},{\"retry\":2}",
  "headerMap": { "User-Agent": "..." }
}
```

| 组件 | 源码依据 |
|---|---|
| `enabledCookieJar:true` | `AnalyzeUrl.kt:126` `enabledCookieJar = source?.enabledCookieJar == true`；:770 `headerMap[cookieJarHeader]="1"` 才触发 networkInterceptor 的 Cookie 加载/保存 |
| 403 响应的 Cookie 也会被保存 | `CookieManager.saveCookiesFromHeaders` 不检查状态码；session Cookie 进内存、persistent Cookie 进数据库 |
| `retry:2`（URL 选项） | `OkHttpUtils.newCallResponse` 循环重发；每次重发重新走 interceptor 链 → `loadRequest` 带上刚存的 Cookie → 200 |

**请求时间线**：首击 403（~200ms，Cookie 已入库）→ retry 重发带 Cookie → 200。整个过程对规则透明，规则拿到的直接是 200 页面。

### 1.4 大坑：eval_js 调试环境不生效

`eval_js` 的 `java.ajax()` **没有 source 绑定** → `enabledCookieJar` 判定为 false → Cookie 既不加载也不保存 → 无论怎么 retry 都是 403。
**必须先把书源保存进 App，再调试/实测**。这就是"调试结果与线上行为不一致"的典型来源。

### 1.5 附带发现：快速连发触发 IP 级风控升级

短时间内（几秒内）连续多个请求 → 连 Set-Cookie 都不再下发（彻底 403，无 Cookie 可拿）→ 必须等冷却。
**表现**：sleep 后再请求，恢复下发 Cookie。做对照实验时若发现"连 Cookie 都没了"，先停手等冷却再继续，不要盲试。

---

## 二、搜索 action 路径轮换

### 2.1 站点行为

首页搜索表单 `action="/searchXX.html"`，后缀随机字母数字（本次实测 `search7b.html` → `search3d.html`）。
写死路径 → 站点换后缀后搜索 404。

### 2.2 正解：searchUrl 用 @js 动态提取

```json
"searchUrl": "@js:var base = \"http://www.xsbook.org\";var h = String(java.ajax(base + \"/,{\\\"retry\\\":2}\"));var m = h.match(/<form[^>]*action=\"([^\"]*)\"/);var act = m ? m[1] : \"/search7b.html\";base + act + \"?searchkey={{key}},{\\\"retry\\\":2}\""
```

要点：
- 提取请求本身也带 `retry:2`（首页也要过双击验证）
- `{{key}}` 保留在返回串里，Legado 后续自动替换+URL编码
- 必须有兜底 action（防提取失败）
- **旧版书源"动态提取action+removeCookie"的设计本意就是对付轮换**，但 removeCookie 每次清 Cookie 导致每次搜索都从 403 路径走，加上无 retry 直接死。修复时保留动态提取、去掉 removeCookie、补 retry。

### 2.3 甄别提示

搜索突然 404（非限频 alert）→ 先怀疑 action 轮换，抓首页 form action 对照书源里写死的路径。

---

## 三、搜索限频：30秒间隔 + 惩罚叠加

### 3.1 站点行为（三阶段实测）

| 阶段 | 表现 |
|---|---|
| 正常 | 返回搜索结果页（43本/29本…） |
| 触发限频 | **200 状态码 + 59字节**：`<script>alert("搜索间隔: 30 秒");window.history.go(-1);</script>` |
| 反复触发（惩罚叠加） | 限频冷却时间变长（30s→90s+仍限），类似 IP 信誉降级 |

### 3.2 关键判据

- **HTTP 200 + 极短响应（<100字节）+ 含 `alert("搜索间隔` = 限频页**，不是搜索失败也不是空结果
- 与「空结果伪装」（记忆 legado-search-signature-disguise）区分：限频页极短且含 alert 语句
- 正文/目录/分类页**不受搜索限频影响**（限频只针对 search 接口）

### 3.3 Legado 配置

```json
"concurrentRate": "1/31000"
```

站点明示 30 秒，配 31 秒留余量。**并发限速在 Legado 中是全站生效的**（ConcurrentRateLimiter 按 source 计），正文请求也会被节流到 31 秒/次——对阅读体验有影响但保证不触发风控；若站点只限搜索，正文密集请求可观察是否有独立限制再权衡。

### 3.4 排查纪律（本次踩坑实录）

1. **不要密集探测搜索接口**——每次探测都重置限频计时，还会叠加惩罚。用户明说"不要主动探测搜索访问频率"，要遵守。
2. 限频状态下：等（60s→90s→5min→10min 递增），每轮只发**一次**请求，且**必须单脚本内先 sleep 再请求**（分两次工具调用时，等待调用超时/被取消后，下一次调用立即发出又会重置计时）。
3. 对照实验用 MCP 浏览器通道（不同出口 IP）验证站点本身是否正常，区分"站点挂了"vs"我的IP被限"。

---

## 四、目录结构陷阱：最新章节段倒序重复

杰奇CMS风格详情页目录 `#list dl` 内三段：

```html
<dt>…最新章节</dt>
<a><dd>第70章</dd></a>  ← 最新9条，新→旧倒序
<dt>…全部章节目录（共1299章）</dt>
<a><dd>新书感言</dd></a>…<a><dd>第11章</dd></a>  ← 旧→新
<dt>点击展开更多章节</dt>
<a class="hc" style="display:none"><dd>第12章</dd></a>…<a><dd>第70章</dd></a>  ← 旧→新（display:none，jsoup 仍能选中）
```

直接 `id.list@dl>a` 得 1308 条 = 9条倒序重复（新→旧）+ 1299条正序（旧→新）。
**完整正序目录藏在"全部章节段+hc展开段"**，hc 区尾部已含最新章节。

### 4.1 保后去重 JS（chapterList 用）

```
id.list@dl>a
@js:var seen={};var out=[];for(var i=result.length-1;i>=0;i--){var u=String(result[i].attr("href")||"");if(u&&!seen[u]){seen[u]=1;out.unshift(result[i])}}out;
```

- 逆序遍历，首次出现的 href 保留（=原序中最后出现的保留）→ 丢弃前9条倒序重复，保留 1299 条正序
- `result` 在 chapterList 的 @js 中是 jsoup Elements，支持 `.length`/`[i]`/`.attr()`；返回 JS 数组 Legado 自动适配
- `dl>a`（直接子级）自动排除 dt 内的书名 a 和"点击展开更多章节"a；页尾推荐链接在 `</dl>` 之外不会混入

### 4.2 数据核对法

页头声称 `共1299章` → 保后去重结果必须 = 1299（实测一致）。数字对不上说明选择器/去重逻辑有错。

---

## 五、其他通用修复点（本站实测）

| 项 | 旧版错误 | 修复 |
|---|---|---|
| 搜索封面 | `img@src` 全是懒加载占位图 nocover.jpg | `img@data-original` |
| 详情简介 | 单一 `[property="og:description"]@content`，部分书为空 | `og:description || id.intro@text || [name="description"]@content` 三级兜底（meta description 是 SEO 模板句，可读） |
| 全本分页 | `/quanben/xclass/` 无页码参数 | 实测 `/quanben/xclass/{page}.html` |
| 排行榜 | 只有一个 `/rank/` | `/rank/allvisit/` `/rank/monthvisit/` `/rank/weekvisit/` `/rank/goodnum/` 四榜，每榜固定50条无分页 |
| 分类分页 | `/xclass/{id}/{page}.html` ✓ | 保持，末页841页 |

## 六、验证清单（全链路实测记录）

- [x] 搜索「剑来」43本 → 详情（og字段全取）→ 目录1299章正序 → 正文+章内分页2页
- [x] 发现页：分类玄幻36本/女频第2页36本/总排行榜50本/全本36本 全通
- [x] next_url 指向下一章时 Legado 自动截断（◇本章总页数:1），防串章机制生效
- [x] check_source 因限频误报「搜索失效」——限频期内校验必然失败，等冷却后自愈
- [x] LAN web 服务 `POST /saveBookSource`（x-legado-token 头）保存书源 200 isSuccess

## 七、可复用模板索引

- 403双击三件套 → 本文 1.3
- 动态 action searchUrl → 本文 2.2
- 保后去重 chapterList → 本文 4.1
- 限速与排查纪律 → 本文 3.3/3.4


---

## 八、第二轮实战修正（v2.4~v3.0：会话级限频的真相）

> 第一轮结论「惩罚叠加/等待冷却」是**错的**——被用户实测打脸（浏览器一直 30 秒间隔正常，App 却搜不了）。
> 正确结论：**限频是会话级配额制，不是 IP 级计时器**。

### 8.1 会话级搜索配额机制（修正后）

| 会话状态 | 搜索行为 |
|---|---|
| 新会话（无 Cookie）→ 403双击 → 新 Cookie | **配额重置**，搜索立即成功 |
| 同会话第 2 次搜索（间隔 >30 秒） | 仍弹 alert 限频页（**等再久都没用**） |
| 同会话第 2 次搜索（间隔 <30 秒） | alert「搜索间隔： 30 秒」 |

**判别实验**（对照）：
- 清 Cookie（`cookie.removeCookie`）→ 立即搜索 → 成功（43 本）
- 不清 Cookie 等 103 秒 → 搜索 → 仍限频

结论：**每个会话只能搜 1 次**（或极少次数），与间隔无关。浏览器能连续搜是因为浏览器每次请求的 Cookie 会话也在轮换/浏览器指纹被优待——但 App 侧解法明确：**每次搜索前换新会话**。

### 8.2 最终解法（v2.4 定案）：每次搜索换新会话

```
searchUrl = @js:
  cookie.removeCookie(base)           // ①清旧会话（会话级配额标记随之清除）
  h = java.ajax(base + "/,{"retry":2}") // ②403双击拿新Cookie
  act = h.match(/<form[^>]*action="([^"]*)"/)[1]  // ③动态提取轮换的action
  base + act + "?searchkey={{key}},{"retry":2}"  // ④带retry双击
```

**这就是旧书源 `cookie.removeCookie(url)` 的设计本意**——修复者当时就懂这个站，只是旧版缺 `enabledCookieJar:true` 和 `retry`，清了 Cookie 后死在 403 上。**修旧书源时，看似多余的代码先查清设计意图再删**。

### 8.3 HTTP 日志对照法（定位"为什么浏览器行、App 不行"）

本轮定位靠 `get_http_logs` 逐条对比成功/失败请求：
- UA 没生效 → 看 `User-Agent:` 头（发现是 App 默认 Chrome/152）
- Cookie 状态 → 看 `Cookie: [redacted]` 有无 + `CookieJar: 1`
- **URL 选项生效性** → 看请求 URL 尾部有无 `,{"retry":2}`（v2.5 的 `<js>` 前缀写法就丢了选择器结果）

### 8.4 URL 类规则追加选项的正确写法（v2.5 教训）

`bookUrl/chapterUrl/nextContentUrl` 要追加 `,{"retry":2}` 时：

```json
"chapterUrl": "href\n@js:String(result) + ',{\"retry\":2}'"
```

**错误写法**：`"<js>String(result) + ...</js>"` —— `<js>` 是新规则的起点，**丢弃前面选择器的 result**（换成整个元素的 HTML）。
**正确写法**：选择器规则 + 换行 + `@js:`（AnalyzeRule 规则链中前规则结果作为 result 传入）。

### 8.5 多元素选择器 + @js 的 List 陷阱（v2.8 教训）

页面有 2 个 `id="next_url"`（页首/页尾导航）→ `id.next_url.0@href` 用 `.0` 索引取单值，但传给 `@js` 的 `result` **仍是 Java List（单元素）** → `String(result)` = `[/path]`（带方括号）→ URL 拼坏 404。

**正确写法**（JS 里先解包 List）：

```
id.next_url.0@href
@js:var u=result;try{if(u.size){u=u.get(0)}}catch(e){}String(u)+',{"retry":2}'
```

判据：Legado 规则链里选择器结果进 @js 时，**数组永远是 Java List**，先 `.get(0)` 再 `String()`。

### 8.6 concurrentRate 的实测甜点值（v2.7~v3.0）

| 值 | 实测行为 |
|---|---|
| 1/31000 | 校验器 180 秒超时（4 阶段×31 秒排队），拖死一切 |
| 1/1000 | 站点把请求**挂起到 30 秒**才响应（弹性节流，间隔太短反而触发挂起） |
| **1/8000** | **甜点**：8 秒间隔站点直接放行，无挂起；校验/下载也可接受 |

经验：**站点有弹性节流时，间隔太短会被挂起惩罚（等效 30 秒），太长拖死全链路。取实测能"直接放行"的最短间隔。**

### 8.7 check_source 的局限

- 校验器判「搜索失效」≠ 书源坏：限频页/超时都会误报
- LAN `startBookSourceCheck` 需要 `{"sources":[完整对象],"keyword":"..."}`（不是 urls 数组）
- 校验队列可能卡住（状态停在 NEEDS_CHECK），App 内 `debug_source`/手动调试更可靠
- **最终判据是 HTTP 日志**（get_http_logs 逐条看请求/响应），不是校验器结论
