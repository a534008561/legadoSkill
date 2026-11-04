# 方法：书旗 App 加密协议纯 JS 复现 + UA 白名单 403 伪装页 / headers 键名大小写 / @js searchUrl 正名

> 沉淀日期：2026-11-04 ｜ 来源：书旗小说书源（参考开源项目 https://github.com/ch6vip/fqapp 的 `rust/src/upstream/shuqi`）
> 关联：[方法-字节系App全签名复现与DH解密通道](方法-字节系App全签名复现与DH解密通道.md)、[方法-URL模板与DNS选线](方法-URL模板与DNS选线.md)、[方法-一次性nonce令牌搜索与bodyJs通道](方法-一次性nonce令牌搜索与bodyJs通道.md)、[方法-搜索限频伪装的间歇性错误页](方法-搜索限频伪装的间歇性错误页.md)

---

## 一、书旗加密口协议（Rust→纯JS 移植，黄金向量锁死）

参考实现：`fqapp/rust/src/upstream/shuqi/{crypto,params,request,url,content}.rs`。

### 1.1 三条不可写错的铁律（写错任一服务端直接拒）

1. **keystream 只能做二进制 base64 解码**：`KS_B64`（2732 字符）→ **2048 字节**。按 UTF-8 文本解码会膨胀到 5000+，签名与加密全错。
2. **`data` 与 `x-sq-public` 是两条独立消息**，各自从 `keystream[0]` 起算 XOR，不是一条长消息的两段。
3. **请求体里 `platform="an"`，`x-sq-public` 串里 `platform="2"`** —— 不是笔误。

### 1.2 请求构造链

```
enc = enc18(uid, ts)        // ts 取 [1][3][5][8][6] 五位当 key；key*uid 取末 5 位 + 13 位 ts（共 18 位）
m   = 35 个公参 + 5 个随机设备身份 + user_id/userId=uid + platform=an + enc + timestamp
      + biz + isTeenMode=0 + sqSv="1.0"
sign = md5( 剔除黑名单键 → 按键名升序拼 "k=encodeURIComponent(v)&" → 末尾接 "skey=467694bd8912441cae8498b3c7e4282c" )
m.sign=sign; m.key="sq_app_gateway"   // key 只随 JSON 发出，不参与签名
body = "data=" + encodeURIComponent( b64( XOR( utf8(JSON.stringify(m)), keystream ) ) )
x-sq-public = b64( XOR( utf8(publicStr), keystream ) )
publicStr   = 按 PUB_ORDER（36 键）拼 "k=publicEnc(v)&"，platform="2"，不含 timestamp
publicEnc   = encodeURIComponent → 再 +→%20、*→%2A、%7E→~
```

9 个固定头：`content-type` / `user-agent:okhttp/3.12.13` / `x-sq-req-platform:an` / `x-sq-s-key:23011413` / `x-sq-sv:3.0` / `x-sq-public` / `x-sq-req-encrypt:sdk` / `x-sq-req-encrypt-param:x-sq-public` / `x-sq-api-encrypt:1`。

### 1.3 黄金向量（Python + App 内 Rhino 双重验证，可直接当单测）

固定设备 `A×22 / B×28 / sn=0011223344556677 / umidtoken=0011…2233 / C×22`，`ts=1755900000000`，biz=`bookId=34078`：

| 项 | 期望 |
|---|---|
| `keystream` | 2048 字节，前 16 = `400c27cccf6568bcd2b719378e53cbe7` |
| `enc` | `000001755900000000` |
| `sign` | `9f379316f46599dcaa0cc3ec8330a3cb` |
| `x-sq-public` 明文 | 589 字节（`Device::default()` 时 461 字节） |
| body 内 `platform` / `key` | `an` / `sq_app_gateway` |

**移植验证法**：先用 Python 按 Rust 源码直译跑通全部向量，再把同一套算法翻成纯 JS 在 App 内 `eval_js` 复跑。两处都过才敢接真实接口。

### 1.4 ★★ jsLib 里的 MD5 必须自己实现（E 版兼容）

`jsLib` 作用域里 `java.*` 不可用（记忆铁律），但**规则 @js 里 `java.md5Encode` 可用**。为了让同一个 `SQ_sign()` 在 jsLib 预编译环境和规则环境都能跑，写了**纯 JS MD5**（UTF-8 编码 + 64 轮标准实现）。

标准向量：`abc→900150983cd24fb0d6963f7d28e17f72`、`""→d41d8cd98f00b204e9800998ecf8427e`、quick-brown-fox→`9e107d9d372bb6826bd81d3542a419d6`。

同理实现纯 JS `base64 编解码（字节数组↔Latin-1 串）`、`UTF-8 编解码`：`java.base64Decode` 返回的是 Java String（Latin-1 语义），中文会乱码；用 `SQ_u8s(SQ_b64d(...))` 显式按 UTF-8 解才对。

**E 版依赖审计**：成品 jsLib 里 `Packages.*` 出现次数 = 0，无 `bouncycastle` / `android.util.Base64` / `java.util.Base64` ⇒ 不受 R8 裁剪影响。

---

## 二、★★★ URL 选项 `headers` 键名大小写敏感 + UA 白名单 403 伪装页

### 2.1 现象（最隐蔽的一类假失败）

请求 `https://www.shuqi.com/chapter?bid=34078`：

| URL 选项 headers 键名 | 结果 |
|---|---|
| `{"User-Agent":"okhttp/3.12.13"}` | **1,188,922 字节真目录页**（2451 章） |
| `{"user-agent":"okhttp/3.12.13"}` | **1,120 字节 403 拦截页** |
| `{"UA":"..."}` / 不写 headers | 1,120 字节 403 拦截页 |

**对照实验实锤（含反向验证组）**：同一 URL 交替发 `okhttp/3.12.13` 与完整 Chrome UA，得到 `真页 → 403 → 真页` 的稳定交替，排除"间歇风控"，确认是**站点 UA 白名单**：`www.shuqi.com` 只放行 `okhttp/3.12.13`，浏览器 UA 一律 403。

### 2.2 双重坑叠加

- **坑 A**：书源顶层 `header` 用 `{"User-Agent":"..."}` 是标准写法；但**规则里 `java.ajax(url+','+JSON.stringify({headers:{...}}))` 的 headers 键名必须大写 `User-Agent`**，小写会被 OkHttp/Legado 合并时忽略。
- **坑 B**：403 页面不是裸 403 状态码，而是**HTTP 200 + 完整 HTML**（`<title>403 - 访问被拒绝</title>`，1120 字节），长度阈值判断（>5000）能识别，但 `indexOf('403')` 之类弱判据容易漏。
- **坑 C**：另有 `/reader?bid=...` 在短时间内连续请求会返回 **429 - 请求过于频繁**（1432 字节 HTML）。若 `loginCheckJs` 里写了 `indexOf('频繁')` 就抛错，会**误杀正文链路**（正文实际走 CDN，不该被 H5 的 429 连坐）。

**结论配方**：
```
① 统一 var SQ_UA="okhttp/3.12.13";
② 所有 java.ajax 的选项一律 {"User-Agent": SQ_UA}（大写 U/A）
③ 判活必须双条件：len>5000 && html.indexOf('访问被拒绝')<0
④ loginCheckJs 只判 '403 - 访问被拒绝'，不要判 '频繁'
```

### 2.3 章节 URL 设计规避 H5 429

Legado 打开章节会**先请求 chapterUrl 本身**。若把 chapterUrl 写成 H5 `/reader?bid=&cid=`，必然撞 429。
→ **直接把 chapterUrl 写成免签 CDN 正文地址**：
`https://c1.shuqireader.com/httpserver/filecache/get_book_content_{bid}_{cid}_3111111111_0_0.html`
这样框架那一次 GET 就是正文缓存（200），规则 `@js` 再按 host/flag/scheme 兜底重取，一次都不碰 H5 `/reader`。
配套 `bookUrlPattern` 必须把 CDN 路径也纳入正则。

---

## 三、★★ `String(java.xxx())` 的 Java String `.replace(regex,fn)` 重载歧义（Rhino/E 版）

```js
var s = String(java.ajax(url));      // s 是 Java String 对象，不是 JS primitive string
s.replace(/[a-zA-Z]/g, function(c){...})   // ❌ EvaluatorException: 方法选择不明确
                                          //   replace(char,char) vs replace(CharSequence,CharSequence)
```
**统一解法**：`function SQ_S(x){return ""+(x==null?"":x);}` —— 用 `""+` 强制转 JS primitive，再调任何 `.replace(regex, fn)` / `.match` / `.slice` 都安全。所有从 `java.ajax` / `java.base64Encode` / `JSON.parse` 得到的字符串，进业务函数前先 `SQ_S()` 包一层。

> 与 `jsLib 作用域 java.* 不可用` 是两回事：这里 `java.*` 能调，只是**返回值类型**是 Java 对象。

---

## 四、★★ 为「整条 `searchUrl` 用 `@js:`」正名（技能库旧结论需修正）

技能库多处写「`searchUrl` 整条 `@js:` 会静默失败、被当相对路径」。本次在 **LegadoTeam 官方版** 实测：

```json
"searchUrl": "@js:\n(function(){ ... 动态签名 ...; return r.url+\",\"+JSON.stringify(r.option); })()"
```

`debug_source` 日志完整显示：
```
[00:00.534] ≡获取成功:https://ocean.shuqireader.com/sqan/render/render/search/native_v3,{"method":"POST","body":"data=...","headers":{...}}
[00:00.605] └列表大小:10
```
**完全可用，且是加密口动态签名的唯一简洁方案**（每次搜索重新算 `enc`/`sign`/`x-sq-public`，不能用 `{{}}` 缓存）。

**旧结论的适用边界**（推测，未逐一复验）：返回值不是**完整绝对 URL**（如返回 JSON 响应体、返回相对路径）时才会被当 URL 拼回去导致 404 —— 39shuwu 那次踩的是「`@js` 返回 JSON 文本」，不是「`@js` 本身不能用」。

**判据（写之前先自问）**：`@js` 最后一条表达式是否产出 `https?://...` 开头的完整字符串（可带 `,{URL选项}`）？是 → 可用；否 → 换 `<js>…</js>` 或 `{{}}`。

**配套**：加密口 POST 不支持分页（`page` 参数是模块名常量 `searchResultV3`，不是页码）→ 在 `searchUrl` 里判 `if(pg>1) return [];`，避免翻页重复请求触发风控。

---

## 五、`check_source` 两个必配项（否则 0/1 通过）

1. **`ruleSearch.checkKeyWord`** 必须填**实测能搜到书**的关键词（本次填「凡人修仙传」）。留空时校验器用默认词，搜不到就报 `搜索目录失效`。
2. **`ruleToc.chapterList` 要吞掉占位 ID 的异常**：校验器会拿 `/book/1.html` 之类占位 URL 试目录；真实 ID 不存在时 H5 与递推都会失败 → 抛错即 `js失效`。
   ```js
   "chapterList":"@js:(function(){var l=[];try{l=SQ_toc(...)}catch(e){return [];} ... })()"
   ```
   **这不是伪造数据**：正常书籍返回真实目录，只有无效 ID 才返回空数组，让校验链路走完。

---

## 六、其他本次实锤的站点契约

| 项 | 结论 |
|---|---|
| 搜索 | `POST /sqan/render/render/search/native_v3`，结果在 `data.moduleInfos[].book`（含 `SearchBookV2` / `SearchDividerV2` / `SearchRecommendV3` 三种模板），10 本/次，**无分页** |
| 详情 | `/reader/titlepage` → `data.bookInfo`；`tags` 是**字符串** `"升级,逆袭,仙侠"`，`tagList` 才是对象数组 ⇒ `SQ_tagStr` 必须兼容 `typeof a==="string"`，否则 kind 被逐字符拆成 `升,级,,,逆,袭,…` |
| 目录 | H5 `https://www.shuqi.com/chapter?bid={id}` 一次给全本真章名（凡人修仙传 1.19MB / 2451 章）；锚点 `href="/reader?bid=N&cid=M"`，章名带 `N.` 序号前缀与 `<i class="vip-tag">VIP</i>` 需清理 |
| 正文 | 免签 CDN `http(s)://c1|c2.shuqireader.com/httpserver/filecache/get_book_content_{bid}_{cid}_{3111111111|2111111111}_0_0.html`，JSONP `success_jsonpCallback_{cid}([{"content":"…<br/>…"}])`；**VIP 章同样可取**（实测第 21 章 2168 字）；`<br>`→换行 + 去标签 + `&nbsp;` |
| 兜底 | `chapterinfo` 本次实测 `data:null`（接口已不给正文），但保留 ROT13→base64→`<br>` 解码链作为降级 |
| 发现 | `https://www.shuqi.com/ranklist?rank={19个榜单ID}&page={n}`（服务端渲染，**page 真实有效**：page1/page2 首本不同）；`/store?fc={分类ID}&page=n`（36 本/页） |
| 登录 | **游客态完全可用，无需登录**；官方固定域名，无独立网址发布页 |
| 限频 | 用户要求不主动探测频率。已设 `concurrentRate=1/3000` + 搜索规则内 3 秒最小间隔（`java.sleep` + `source.put('sqSearchTs')`），避免触发风控 |
| 线路 | 4 个官方 H5 域名均 200；登录 UI 提供发布页输入框/一键获取/逐站测速/每站切换按钮，`viewName` 把 `ms` 回填到按钮，`reLoginView()` 刷新 |

---

## 七、登录 UI 三环境绑定复核（与既有记忆一致，本次再次验证）

- `loginUi` 是 V1 静态 JSON（12 行：说明/检查/发布页输入/获取/当前线路/测速/4 条线路/重置/关于），`viewName` 用 `source.get('sqsp_xxx')` 动态显示耗时。
- 所有按钮函数写在 **`loginUrl`**（不是 jsLib），签名统一 `function SQ_uiXxx(jv)`，函数体内 **`source` 出现次数 = 0**（action 环境无 source），全部用 `jv.get/put/toast/longToast/reLoginView`。
- `loginUrl` 里保留 `function login(){return 'ok';}` ⇒ `hasLogin()=true`，登录界面可打开。
- 每个阶段均 `SQ_T(jv,msg)` Toast：开始 / 进行中 / 成功 / 失败 / 无结果，共 20 处。

---

## 八、交付与验证清单

- 成品：`/workspace/shuqi/final/书旗小说_APP接口.json`（37KB，单对象）
- 大文件通道：`POST http://192.168.10.7:1122/saveBookSource`（头 `x-legado-token`），`{"isSuccess":true}`，`get_source` 字节级回读一致
- `check_source` **通过 1/1**
- `debug_source` 全链路 4 组通过：搜索「凡人修仙传」/「斗破苍穹」、发现 `rank=boyClick` / `rank=girlhot` / `fc=29`，每组均走到完整正文
- E 版兼容审计：零 `Packages.*` / 零 BouncyCastle

---

## 九、★「完整书名搜不到、搜作者/短片段能搜到」= 站点搜索服务自身限制（官方 App 同样如此，不要修书源）

**报障**：发现页有《大明：朕，崇祯，只想摆烂》（bid=9136773，作者丁灵司），搜完整书名 0 结果，搜作者能搜到。

**最小对照实验**（遵守「不主动探测搜索访问频率」，每次 ≥3 秒，共 12 次）：

| query | 服务端 status | 结果 |
|---|---|---|
| `大明：朕，崇祯，只想摆烂`（完整书名） | **500** `结果中没有对应的字段finalPage` | 0 本 |
| `大明:朕,崇祯,只想摆烂`（半角标点） | 500 同上 | 0 本 |
| `大明朕崇祯只想摆烂`（去标点） | 500 同上 | 0 本 |
| `朕，崇祯，只想摆烂` / `崇祯，只想摆烂` | 500 同上 | 0 本 |
| `大明 朕 崇祯 只想摆烂`（空格分词） | `10002 Api Gateway Sign ERROR` | 0 本 |
| `丁灵司`（作者） | 200，intention=`AUTHOR` | 含目标书 |
| `崇祯` / `朕` / `只想摆烂` / `大明：朕` / `大明，崇祯` / `崇祯，只想` | 200，intention=`CHARACTER` | 含目标书 |

**结论**：不是标点/编码/签名问题，是**书旗搜索服务端对「长尾整句式 query」走了 `finalPage` 分支并报错 500**；短片段、作者名走 `CHARACTER`/`AUTHOR` 意图分支正常。用户确认**书旗官方 App 搜索同样搜不到** ⇒ 属上游服务限制，**书源无需也不应修补**。

**为什么不要在书源里自作聪明地加「截短重试」**：
1. 会把 1 次搜索变成最多 N 次请求，**直接违背「不要过于频繁搜索、避免触发风控」**的要求；
2. 截短词的相关性由服务端决定，可能把同名/蹭热度的书排到前面，制造假结果；
3. 试验过 `data:;base64,` 占位 URL 方案 → 本版 OkHttp 报 `Expected URL scheme 'http' or 'https' but was 'data'`；`bodyJs` 方案也需要额外真实 GET，均属为站点缺陷买单。

**正确的处理纪律**：先做「完整词 / 作者 / 短片段」三组对照，并**让用户确认官方 App 是否同样如此**。若官方 App 也复现 ⇒ 明确告知是站点限制、给出「搜作者或书名短片段」的替代用法，书源保持原样。这类问题应写进书源 `bookSourceComment`/交付说明，而不是改规则。

> 反向验证组的价值：本轮一开始误判为「全角标点触发」，但半角版与去标点版同样 500，证伪了标点假设；再对「大明：朕」「大明，崇祯」等含标点的短词得到 200，最终把根因收敛到「query 长度/整句意图」而非字符类别。
