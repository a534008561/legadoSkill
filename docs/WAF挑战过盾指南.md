# WAF 挑战过盾指南

> 基于 m.lianaiya.com（笔趣阁移动版）实战总结，适用于采用「503 验证页 + JS 设置 Cookie」模式的 WAF 站点（宝塔/Cloudflare JS Challenge 等变体）。
>
> 最后更新：2026-08-23

---

## 一、WAF 挑战页识别

### 1.1 典型表现

| 特征 | 值 |
|---|---|
| HTTP 状态码 | **503** |
| 页面标题 | `Verifying your browser...` |
| JS 核心代码 | `var token='<动态长字符串>'` |
| Cookie 操作 | `document.cookie='waf_challenge=<token>; expires=...; path=/; SameSite=Lax'` |
| 自动行为 | `window.location.reload()`（设置 Cookie 后立即刷新） |
| 前端过期时间 | 5 分钟 |
| 服务端过期时间 | ≈ 5 分钟（实测旧 Token 被拒，返回新挑战页） |

### 1.2 服务端行为

- 无有效 Cookie → 返回 503 挑战页
- Cookie 有效 → 返回 200 正常页面
- Token 按 **IP + User-Agent** 绑定（换 UA 后旧 Token 作废）
- 无频率限制（同一有效 Token 可正常请求多次）

### 1.3 快速验证脚本

```python
import requests, re

s = requests.Session()
UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) ..."
s.headers.update({"User-Agent": UA})

r = s.get(target_url)
if r.status_code == 503 and "waf_challenge" in r.text:
    token = re.search(r"var token='([^']+)'", r.text).group(1)
    s.cookies.set("waf_challenge", token, domain="目标域名")
    r = s.get(target_url)  # 第二次请求：正常
print(r.status_code)  # 200
```

---

## 二、Legado 书源处理方案

### 2.1 可用 API 清单

| API | 用途 | 注意事项 |
|---|---|---|
| `java.ajax(url)` | HTTP GET，返回 body 字符串 | ✅ 可用（函数） |
| `java.getCookie(host)` | 获取当前 Cookie | ✅ 可用（函数） |
| `cookie.setCookie(host, cookieStr)` | **设置 Cookie** | ✅ 推荐使用 |
| `java.setCookie(host, cookieStr)` | 设置 Cookie | ❌ 部分版本不存在 |
| `java.get(url)` | 返回 StrResponse 对象 | `.body()` 获取内容 |

> ⚠️ 统一使用 `cookie.setCookie()` 而非 `java.setCookie()`，兼容所有版本。

### 2.2 jsLib 作用域陷阱（重要！）

**现象**：部分版本 Legado（HtmlUnit Rhino 引擎）的 **jsLib 中 `java.ajax` 是 object 而非 function**：

```
TypeError: ajax 不是函数，它是 object
```

**原因**：jsLib 的执行作用域与规则脚本不同，`java` 对象的绑定存在差异。

**验证方法**：

```
# 步骤 1：在 app 内 eval_js（不绑定任何书源）测试
typeof java.ajax   → "function"  ✅ 主作用域正常

# 步骤 2：绑定书源后 eval_js
typeof java.ajax   → "function"  ✅ 绑定后主作用域仍正常

# 步骤 3：在 jsLib 中定义探测函数
function probe() { return typeof java.ajax; }

# 步骤 4：在 searchUrl 的 @js: 中调用 probe()
probe()            → "object"    ❌ jsLib 作用域异常！
```

**诊断捷径**（无需改 jsLib，直接在 searchUrl 探测）：

```js
@js:(function(){
    return 'https://example.com/?d='+typeof java.ajax;
})()
```

debug 日志会输出：`≈获取成功:https://example.com/?d=function` 或 `d=object`，据此判断。

**解决方案**：将所有 WAF 处理逻辑 **内联到各 JS 字段**（searchUrl / exploreUrl / tocUrl / content），不依赖 jsLib。

### 2.3 推荐实现：全内联

#### 搜索页 JS（含 WAF 预处理）

```js
@js:(function(){
    function wt(h){
        var m=String(h).match(/var token='([^']+)'/);
        return m?m[1]:null;
    }
    var host='https://目标域名/';
    var h=String(java.ajax(host));
    var t=wt(h);
    if(t){try{cookie.setCookie(host,'waf_challenge='+t);}catch(e){}}
    function enc(s){
        try{return java.urlEncode(s);}
        catch(ex){return encodeURIComponent(s);}
    }
    return 'https://目标域名/search?q='+enc(key);
})()
```

#### 目录页 tocUrl JS

```js
@js:(function(){
    function wt(h){
        var m=String(h).match(/var token='([^']+)'/);
        return m?m[1]:null;
    }
    var host='https://目标域名/';
    var h=String(java.ajax(host));
    var t=wt(h);
    if(t){try{cookie.setCookie(host,'waf_challenge='+t);}catch(e){}}
    return baseUrl;  // baseUrl = bookUrl（详情页 URL）
})()
```

#### 正文页 JS（含每页自愈 + 分页合并）

```js
@js:(function(){
    function wt(h){
        var m=String(h).match(/var token='([^']+)'/);
        return m?m[1]:null;
    }
    function wg(url){
        var h=String(java.ajax(url));
        var t=wt(h);
        if(t){
            try{cookie.setCookie('https://目标域名/','waf_challenge='+t);}catch(e){}
            h=String(java.ajax(url));  // 重试
        }
        return h;
    }
    // ... pick() 提取内容函数
    // ... clean() 清理广告函数
    // ... nextPage() 查找下一页JS变量
    var html=String(result);
    if(wt(html)){html=wg(baseUrl);}  // 首次加载：如果已是挑战页则自愈
    var first=pick(html);
    if(first===null)return '正文获取失败';
    var parts=[clean(first)];
    var next=nextPage(html),guard=0;
    while(next && /_\d+\.html$/.test(next) && guard++<60){
        html=wg(next);      // 每页都带自愈
        var c=pick(html);
        if(c===null)break;
        parts.push(clean(c));
        next=nextPage(html);
    }
    return parts.join('<br><br>');
})()
```

### 2.4 书源配置要点

```jsonc
{
  "enabledCookieJar": true,        // 必须！否则 cookie.setCookie 无效
  "header": "{\"User-Agent\": \"Mozilla/5.0 (Linux; Android 14; ...) \"}", // 手机 UA（PC UA 可能被站点屏蔽）
  "concurrentRate": "1000",         // 并发间隔 1 秒（防搜索限频）
  "jsLib": "",                       // 留空，避免 jsLib 作用域问题
  "bookUrlPattern": ".*目标域名\.com/book/.+"  // 书籍URL正则，防止其他链接误触发
}
```

---

## 三、自愈机制设计

### 3.1 原理

WAF Token 有效 ≈ 5 分钟，阅读过程中必然失效。自愈设计让每次 HTTP 请求都具备"发现问题→修复→重试"能力：

```
请求 URL
  ↓
响应是挑战页？（匹配 "var token='"）
  ├─ 否 → 正常处理
  └─ 是 → 提取新 token → cookie.setCookie → 重取当前 URL → 继续处理
```

### 3.2 正文分页合并时的自愈

```
第1页（result） → 检查/自愈 → 提取内容
  ↓ 查找下一页 nav_xxx 变量
第2页（wg(url)） → 检查/自愈 → 提取内容
  ↓
第3页 ...
  ↓
最后一页（innerHtml = '下一章'） → 停止 → 返回合并文本
```

每一页都独立执行自愈，即使 Cookie 在合并过程中过期，也不会中断。

### 3.3 渐进式修复

| 触发时机 | 自愈来源 |
|---|---|
| 打开书源（搜索/发现） | searchUrl/exploreUrl 的内联 wafEnsure |
| 点击书 → 详情页 | **不触发**（首次打开无 Cookie 时可能失败，但 tocUrl 会修复） |
| 详情 → 目录（tocUrl） | tocUrl 的 wafEnsure（修复详情 Cookie） |
| 进入章节 → 正文 | ruleContent 内联 wafGet（首次自愈） |
| 阅读中 Cookie 过期 | 下一个章节的 wg() 自愈 |
| 手动搜索刷新 | searchUrl 的 wafEnsure（补充 5 分钟有效期） |

---

## 四、实战案例：m.lianaiya.com（笔趣阁移动版）

### 4.1 站点特征速览

| 项目 | 值 |
|---|---|
| WAF 类型 | 503 + `var token` → `waf_challenge` Cookie（宝塔/自研） |
| 搜索 | GET `/sdfgsdyugfsdugf.html?s=...&ie=gbk&q=`（**实际需 UTF-8 编码**，表单标注 ie=gbk 无效） |
| 正文分页 | `chapterId_N.html`，JS 变量 `nav_xxx` 提供下一页 URL |
| 目录结构 | 两个 `.book_last` div：第一个是「最新章节预览」（5条），第二个是「全部章节列表」（全量） |
| PC UA 屏蔽 | PC UA 返回全屏 iframe 错误页（"网页无法加载"），必须用手机 UA |

### 4.2 书源成品

见 [../temp/恋爱呀/笔趣阁·恋爱呀.json](../temp/恋爱呀/笔趣阁·恋爱呀.json)

---

## 五、调试技巧

### 5.1 eval_js 探测法

绑定书源后（`url` 参数传入 `bookSourceUrl`），在 `eval_js` 中测试：

```js
// 测试 WAF 处理函数是否正常工作
function wt(h){var m=String(h).match(/var token='([^']+)'/);return m?m[1]:null;}
var h = String(java.ajax('https://目标域名/'));
var t = wt(h);
if(t) cookie.setCookie('https://目标域名/', 'waf_challenge='+t);
java.log("token=" + (t||'none') + ", cookie=" + java.getCookie('https://目标域名/').substring(0,50));
```

### 5.2 返回值探测法（诊断 API 绑定）

```js
// 临时修改 searchUrl 为以下内容，debug 后看日志中的 URL
@js:(function(){
    var info = [
        typeof java.ajax,
        typeof cookie,
        typeof cookie.setCookie,
        typeof java.urlEncode
    ].join('|');
    return 'https://example.com/?debug=' + encodeURIComponent(info);
})()

// 日志输出：≈获取成功:https://example.com/?debug=function|object|function|function
// 代表所有 API 均可用 ✅
```

### 5.3 分步验证

| 步骤 | 操作 | 预期 |
|---|---|---|
| 1 | `debug_source` 搜索关键词 | 日志显示 WAF 处理后正常获取搜索结果 |
| 2 | `debug_source` 输入书籍 URL | 目录数 = 站点真实章节数（全部章节列表） |
| 3 | `eval_js` 运行正文模拟 | 4页章节合并成功，无垃圾文本 |
| 4 | `check_source` | 结果：通过 |
| 5 | Legado APP 手动浏览 | 搜索 → 书 → 目录 → 多页章节正文，全部正常 |

---

## 六、其他常见 WAF 类型对比

| 类型 | 特征 | 书源处理方式 |
|---|---|---|
| **JS Token Cookie**（本文） | 503 + `var token` + `document.cookie` + `reload()` | 提取 token → setCookie → 重取 |
| Cloudflare Turnstile | 503 + iframe + `cf-turnstile-response` | 需 WebView 或 Cloudflare 绕过服务（见 `captcha-detection-guide.md`） |
| 360WZB | 503 + `<meta http-equiv="refresh" content="5;url=...">` | 等待跳转或提取跳转 URL |
| 宝塔防火墙 v3 | 503 + `BaCk` 验证码 | 需人工介入或 OCR 识别 |
| Cloudflare JS Challenge | 503 + `cf_chl_rc_*` | `enabledCookieJar` + WebView |

---

## 七、完整验证清单

制作完 WAF 站点书源后，用此清单逐项确认：

- [ ] `enabledCookieJar` 已开启（`true`）
- [ ] `header` 设置为手机端 UA（PC UA 可能被站点屏蔽）
- [ ] `searchUrl` JS 中包含 wafEnsure（搜索前刷新 Cookie）
- [ ] `exploreUrl` JS 中包含 wafEnsure（发现页前刷新 Cookie）
- [ ] `tocUrl` 规则中包含 wafEnsure（目录加载前刷新 Cookie）
- [ ] `ruleContent` 规则中包含 wafGet（正文每页自愈）
- [ ] `jsLib` 已留空或仅放非网络相关函数（避免 jsLib 作用域 java 绑定异常）
- [ ] `bookUrlPattern` 已设置（防止同域名其他页面误匹配）
- [ ] 搜索/正文的编码处理正确（表单标注编码可能与实际不符，实测验证）
- [ ] `ruleToc.chapterList` 正确指向完整章节列表（避免"最新预览"节点）
- [ ] `concurrentRate` 已设置（防触发站点搜索限频）
- [ ] MCP `debug_source` 全链路通过（搜索→详情→目录→正文）
- [ ] MCP `check_source` 校验通过
- [ ] 在 Legado APP 中手动实测：搜索 → 点击书 → 查看详情 → 打开目录 → 进入**多页分页章节** → 翻页 → 确认正文无垃圾
