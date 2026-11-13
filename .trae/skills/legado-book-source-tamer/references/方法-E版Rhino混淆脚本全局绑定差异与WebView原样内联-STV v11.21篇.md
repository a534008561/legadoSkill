# 方法：E 版 Rhino 混淆脚本全局绑定差异与 WebView 原样内联 — STV v11.21 篇

> 2026-11-13 · 蓝本：STV[api_1]（sangtacviet.vip）v11.20 → **v11.21**
> 独立成篇；前两篇分别是《方法-抓包驱动的官方App行为对齐-STV篇》（v11.19）与
> 《方法-会话绑定缓存失效与CookieJar分层写入-STV v11.20篇》。
> 验证通道：本次 LT 的 MCP/1122 掉线，**只有 E 版 web 服务 1125 可达**，全程用 E 版真机运行时探针 +
> `/saveBook` → `/refreshToc` → `/getBookContent` 集成实测，LT 侧用逐字节静态回归。

## 0. 一句话总结

**「LT 能看到正文、E 版打不开」且报『混淆脚本解析不出密钥』，根因不在网络/Cookie/登录态，
而在两版 Rhino 对 `eval()` 里裸全局函数（`btoa`/`atob`）的作用域解析不同。**
可靠修法不是去补全局绑定（会掉进 IIFE 作用域陷阱），而是**把混淆脚本原样内联进真实 WebView**：
浏览器原生自带 `window.btoa/atob`，且能保住 IIFE 写 `window.*` 的副作用。

---

## 1. 报障与症状指纹

用户原话：「同一本书（路明非不想成为东京大妖）Legado-team 版可以看到正文，Legado-E 版打不开正文」。

书：`fanqie/7616827493470719038`（番茄来源，420 章，有中文 `oridata`）。
E 版 `/getBookSource` 回读确认与 LT **同一份 v11.20**（不是版本分叉）。

E 版 `/getBookContent?index=0` 原文：

```
[STV 本章读不出来]
当前来源：fanqie  章节号 7616829622843343422 / 1
原因：正文为空
取密钥：fanqie 混淆脚本解析不出密钥（站点可能换了加密格式，或 WebView 兜底超时）
```

★症状指纹：**搜索 / 详情 / 420 章目录全部正常，唯一卡在 `grantOnce()` 铸密钥**。
STV 正文密钥来自 `GET /io/grantcontext/context?hostid=&bookid=`，响应是约 30 万字符的
JSFuck 风格混淆脚本 `(()=>{var ˋ︍︌︂︌︀=...; ...})()`，必须在本地 JS 引擎执行才能拿到
`window.app.reader.chapterkey`。

---

## 2. ★E 版真机运行时探针法（本次唯一可用通道）

LT 的 MCP 掉线时，E 版 web 服务自身就是完整真机调试台：

| 路由 | 用途 |
|---|---|
| `POST /saveBookSource` | 落库任意书源（**整体替换**；1125 免令牌） |
| `GET /getBookSource?url=` | 字节级回读确认落库版本 |
| `POST /saveBook` | 加测试书（`bookUrl` + `origin` + `name`） |
| `GET /refreshToc?url=&origin=` | 触发目录规则 |
| `GET /getBookContent?url=&index=N` | **在真机执行 ruleContent**，返回文本即诊断输出 |
| `POST /deleteBook` / `deleteBookSources` | 清理探针书/探针源 |

配方：造一个**独立探针源**（不要动正式源），`ruleContent.content` 写成
`(function(){ out.push('D1='+...); ...; return out.join(' || '); })()`，
每步 `try/catch` 包住把结果拼进返回串，`/getBookContent` 一次读出全部阶段。

★**双重缓存陷阱（再次实锤）**：
① `BookController` 缓存 bookSource，改规则后须删书重加或**换全新 bookUrl**；
② **`BookHelp` 正文缓存按 bookUrl+chapter 落盘，连「错误页」也缓存**——本次 index=0
在修复后仍返回旧版错误文本（连旧提示语都在），`deleteBook` 重加也没清掉。
判「修复是否生效」必须换**未取过的章节 index** 或**换 bookUrl**，不能只盯报错的那一章。

---

## 3. 探针结论（逐条实锤）

```
D1_java=object          D2_ajax=function       D3_webView=function
D4_Packages=object      D5_Base64Class=[JavaClass android.util.Base64]
D6_STVB64=[QUI=]        D7_STVB64D=[AB]        D8_getBytesISO=2
D9_fetch=len=302674
D10_evalSKEL=ok window=object btoa=function        ← window 上垫片挂上了
D11_evalBody=ERR:ReferenceError: "btoa" 未定义。   ← 裸 btoa 仍取不到
D12_webViewCall=len=0 val=
```

- `java.ajax` / `java.webView` / `Packages.android.util.Base64` / 自写 `STVB64/STVB64D` 垫片**全都可用**；
- `STVSKEL` 把 `btoa/atob` 挂到 `window` 上成功（`window.btoa=function`），
  但 E 版 `eval(body)` 内部抛 `ReferenceError: "btoa" 未定义`；
- 最小 WebView 探针 `window.__R="HELLO"` → `java.webView(...)` 返回 `HELLO`
  ⇒ **E 版 WebView 通道是好的**，旧兜底返回空是脚本/转义问题，不是 API 不可用。

### 为什么"补全局绑定"没用

试过在函数内 `eval('var btoa = STVB64; var atob = STVB64D;')`，
`F2_globalBtoa=btoa=function atob=function`，但 `F4_evalBody` 仍报 `btoa 未定义`。
混淆脚本是 IIFE，动态拼出标识符后从**它自己的作用域链/全局对象**取函数；
E 版 Rhino（`org.mozilla.javascript`，LT 是 `org.htmlunit.corejs`）对
间接 eval / `this` / 全局对象的绑定规则不同，**外层 var 进不去**。

### 混淆脚本的两个决定性形态

1. 全文搜索 `btoa(` / `atob(` / `window` 字面量**计数都是 0** —— 标识符是运行时拼出来的，
   无法靠字符串替换改成 `window.btoa(`；
2. 脚本是 `(()=>{ ... })()`，密钥**写到 `window.app.reader.chapterkey` 而不是 return**。
   所以 `String(eval(LIT))` / `String(<脚本>)` 永远得 `undefined`（探针 H2/H3 实锤），
   必须让脚本**作为语句原样执行**，再按 `window.app.reader.chapterkey` / `window.chapterkey` /
   `window.key` 三路兜底读取。

### Path B 验证（H4）

```
H4_browser_raw_with_skel = rawSkel=R=a7a737aa319ea13a3db9a134b040aab931a1a43aaaaab0a1a7ad40b6b9a437a43f3fbf872f67af74fefaf77179787ef2faff77878717af3fcf97a7eff7bff71e1e1eaefe6efeae3e7efe8ececeae7efefe8eaeaeaecefe1e3eceee7e8e1e8e
```

拿到完整密钥 ⇒ 修法成立。

---

## 4. v11.21 修法（`grantOnce()` 三通道）

```
// Path A：Rhino eval，LT 版可用；逐字未动（静态回归确认）
try { eval(STVSKEL); } catch(e1){}
try { window.STVB64=STVB64; window.STVB64D=STVB64D; } catch(ew){}
try { k = grab(eval(body)); } catch(e2){ k=''; }

// Path B ★新增：原样内联为浏览器 <script> 正文
if (k.length < 20) {
  var src = String(body).split('<'+SL).join('<'+SL);
  var script = STVPRE + 'window.__R="";try{' + src + ';}catch(e){...}'
    + 'if(window.__R.length<20){ window.__R=String(window.app.reader.chapterkey||""); }'
    + ... window.chapterkey / window.key ...;
  var html = '<html><head><meta charset=utf-8></head><body><script>'
    + script + '</'+'script></body></html>';
  k = String(java.webView(html,'about:blank',
    '(function(){return String(window.__R||String.fromCharCode());})()')||'');
}

// Path C：旧 eval(LIT) 形态留作最后兜底（老 WebView 构建）
if (k.length < 20) { ... STVPOST.split('LIT').join(lit) ... }
```

★**零反斜杠纪律**：拼进 `<script>` 的 JS 不能出现任何反斜杠；
闭合标签写成 `'</'+'script>'`，`</` 拆分用 `String.fromCharCode(47)`，
`window.__R=""` 用双引号字面量（规则里用 `String.fromCharCode(34)` 拼 Q 亦可）。
上一次 ACFAN/哔咔的教训就是多层转义吞掉一层导致 `unclosed string literal`。

★**Path A 必须保留**：LT 版 Rhino 本来就能跑通，主路径不触发 WebView 才快（省一次 WebView 启动）。
Path B 只在 `k.length<20` 即主路径失败时进入，对 LT 零影响 —— 本次用
`difflib` 逐行对账确认改动全部落在 `grantOnce()` 兜底段，Path A 三行字节一致。

---

## 5. E 版真机验收（修复后）

| 验证 | 结果 |
|---|---|
| `/saveBookSource` v11.21 → `/getBookSource` 回读 | 与本地成品**全字段相等** `True`，`Path B` 存在 |
| 同一本书 `index=3 / 7 / 19`（未取过的新章） | 第4/8/20章，6491 / 6271 / 6026 字符 `<usehtml>` 中文正文，无报错 |
| 全新 bookUrl 的 `index=0`（第1章） | 4670 字符完整中文正文，无报错 |
| 原书 `index=0` | 仍返回旧错误页 → **BookHelp 错误正文缓存**，非修复失效 |

清理：7 本探针书 + `https://stvprobe1120.local` 探针源全部删除，回读「未找到源」。

---

## 6. 通用纪律（可迁移）

1. **"LT 行 / E 不行"先按作用域与运行时分类**：`AnalyzeRule.getElements` NativeArray、
   `java.hexDecodeToByteArray`（限 coverDecodeJs/imageDecode）、`java.post(...,null)`、
   本次 `eval()` 全局绑定 —— 都是两版 Rhino/Kotlin 实现差异，不是站点变了。
2. **别把"API 可见"当成"API 可用"**：`typeof java.webView==='function'` 之后还要跑一个
   最小已知答案探针（本次 `HELLO`），才知道返回空是通道坏还是脚本坏。
3. **混淆/JSFuck 脚本优先交给真实 WebView**，不要试图在 Rhino 里补全局垫片；
   判断脚本形态（IIFE？写 window？返回值？）比补十个 shim 都管用。
4. **IIFE 脚本必须作为语句原样执行**，不要包 `eval(字符串)` / `String(...)`，
   副作用型密钥只能从 `window.*` 读。
5. **内联 script 零反斜杠**，闭合标签拆开拼。
6. **修复验证必须换未取过的章节/换 bookUrl**：错误正文也会被缓存，
   `deleteBook` 重加不清 BookHelp 缓存，只看报错那章会误判"没修好"。
7. **排查桩必须清理**：探针源、测试书、诊断书源全部删掉并回读确认，不留残留在用户书架。
8. 用户侧收尾提示：对原先报错的那一章，在阅读里点一次**刷新/重新加载**（或清该章缓存），
   绕过落盘的错误正文缓存即可看到正文。

---

## 7. 边界与未验证项

- 本次 LT 的 MCP/1122 全程掉线，LT 版**只做了逐字节静态回归**（Path A 未改），
  未做真机全链路；待通道恢复建议补一次 LT `debug_source`。
- `index=0` 旧缓存是 E 版 BookHelp 行为，书源侧无法主动清；需要用户手动刷新章节。
- 漫画来源 `cocomanga` 仍走官方独立通道，与本次无关。
- 最终必须在 Legado APP 真机实测：E 版打开《路明非不想成为东京大妖》任一新章 → 中文正文正常显示。
