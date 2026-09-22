# 方法-聚合源状态漂移修复与选站面板 —— rrssk聚合 44 域名实战

> **一句话**：靠 `sourceVariable` 全局变量（`GET/SET('server')`）分发的多域名聚合源，必然得"**全局状态漂移病**"（书架书正文为空 / 搜索中转失败 / check_source 洗变量炸相对 URL）。根治 = **正文与目录按 URL 自治**（SRV 推导，全局变量降级为纯 UI 状态）；选站入口做成**三件套**（登录面板 / 发现下拉 / 状态栏）并保证三者一致性。
>
> 实战案例：rrssk聚合（44 域名、14 套发现模板、v1→v8，check_source 1/1 ×3，每版全字段 md5 校验）。
> 配套架构篇：[聚合源多域名架构设计](聚合源多域名架构设计.md)（TEMPLATES/HOST_TEMPLATE_MAP/GET-SET 机制）。

## 一、适用场景识别

命中以下特征即属本文场景：

- 一个书源管理 N 个域名，`HOST_TEMPLATE_MAP`（域名→模板）+ `hosts` 数组（发现页下拉）
- 到处 `GET('server').indexOf('xxx') >= 0` 做分支（正文解码分支 / 目录接口 / 详情字段）
- 发现页一个 `type:select` 让用户切站，`server` 存在 `source.setVariable/putVariable` 里

蓝本：rrssk聚合（rrssk家族 + 菠萝猫双体系并存，44 域名）。

## 二、症状谱系与根因（全部真机实锤）

### 2.1 三张脸

| 症状 | 现场证据 | 机制 |
|---|---|---|
| **书架书过段时间打开正文为空**，要"发现页打开对应网站→选本书→回去刷新"才恢复 | App 变量实为 `{"server":"https://www.boluomao.com","bookId":"2017969"}` | 正文规则见 server 含 `boluomao` 就走 data-obf 解码分支 → 普通家族书 `.content@p@data-obf` 取空 → 内容为空；目录还拿全局 bookId（别站的书） |
| **搜索失败"未找到搜索中转入口"** | 全局 server 停在**死站** boluomao.com（连接重置） | searchUrl 第一步 `java.ajax(sourceUrl)` 首页取跳转 → 死站/无跳转 → throw |
| **check_source 炸 `Expected URL scheme http/https for /list-...`** | 校验器无 UI 态求值 exploreUrl | 见 §五 坑1 |

**用户恢复手法 = 手动把 server 拨回去**——理解了这一点，根因就闭环了。

### 2.2 存储与写者（源码级）

```
BaseSource.setVariable/putVariable/getVariable
  → CacheManager.put/get("sourceVariable_${getKey()}")   // BaseSource.kt:326/339/351
  → DB 表 Cache(deadline=0 永久) + 内存 LruCache 双层（重启不丢；clearSourceVariables 只清内存，DB 兜底）
```

**写者清单**（谁动 server 谁就是漂移源）：

1. 发现页下拉 select（原 kinds 求值期 `SET('server', infoMap['域名'])`）
2. 登录面板 `setSite`（v7 新增，正确入口）
3. `ruleBookInfo.init` 的 og:url 自动对齐（详情刷新时改写）
4. `began()` 初始化默认值
5. 旧版校验器无 UI 态的 `SET(server, undefined)` 洗残（见 §五）

> 病根不是"有全局变量"，而是"**正文/目录这种内容链路也读它**"。多个 UI 写者轮番改，内容链路跟着抽风。

## 三、根治：URL 自治五层改造（v6 最终形态）

原则：**正文、目录只信 URL（book.bookUrl / baseUrl），全局 server 只服务发现页 UI 与搜索入口。**

### 3.1 jsLib 新增 `SRV(url)` —— 从 URL 推导本书真实域名

```javascript
function SRV(u) {
  var m = String(u || '').match(/^(https?:\/\/[^\/]+)/i);
  var g = '';
  try { g = GET.call(this, 'server') || ''; } catch (e) { g = ''; }
  if (m) {
    var dh = m[1].toLowerCase().replace(/^https?:\/\//, '');
    var gh = g.toLowerCase().replace(/^https?:\/\//, '');
    if (g && gh === dh) return g;   // 同域时优先全局 scheme（init 统一过 https）
    return m[1];                     // ★漂移时忽略全局，用 URL 自带域名
  }
  return g;
}
```

- **正文**：`var sv = SRV(baseUrl);`（baseUrl=章节 URL，源码 BookContent.kt `setContent(body, baseUrl)` 确认）→ boluomao 分支判定、shoudaxsw `.conBox` 回退、replaceRegex 域名清洗全部改用它
- **目录**：`var serverUrl = SRV(_bu);` + `_mi = _bu.match(/\/book\/([^\/?#]+)\.html/)` 推导 id（不再读 GET('bookId')）

### 3.2 章节 URL 输出绝对地址，`chapterUrl` 改纯键

- chapterList 三处 push 前统一 `(/^https?:/i.test(href) ? href : serverUrl + href)`
- `ruleToc.chapterUrl`: `{{GET('server')}}{{$.chapterurl}}` → **`$.chapterurl`**
- 好处：存储即绝对，重刷目录永远正确；`{{}}` 模板不再持有可漂移表达式

### 3.3 `dataEncrypt(body, srv)` 显式缓存键 + scheme 兜底

```javascript
function dataEncrypt(body, srv) {
  var ck = srv || GET.call(this, 'server');
  let keys = cache.get(ck);
  if (!keys || keys == 'null') {              // http/https 互换兜底
    var alt = ck.indexOf('https:') === 0 ? ('http:' + ck.substring(5)) : ('https:' + ck.substring(4));
    keys = cache.get(alt) || keys;
  } ...
}
```

密钥缓存按域名存（`cache.put(sourceUrl, {secretKey, ivKey})`），key 必须与调用方推导出的域名一致——init 写入用 og:url 对齐域、目录读取用 SRV 推导域，同域时天然一致。

### 3.4 ★别名书：按页面 `data-aid` 实际值自纠

搜索结果的 deep-link 可能是**别名页**（实测 lwjh `book/hggjfg.html` 的 og 规范 id 是 `hgg`，`chapter/hggjfg.html` 存在但 `data-aid="hgg"`）：

```javascript
// 回退抓到 chapter 页后
pages = java.getElements(aid);                 // [data-aid=推导id] 可能0命中
if (pages.length == 0) {
  var am0 = String(so).match(/data-aid="([^"]+)"/);
  if (am0 && am0[1] && am0[1] != id) {
    id = am0[1];                                // ★纠成规范 id（POST 接口也用它）
    aid = `[data-aid="${id}"] li||[data-aid="${id}"] option`;
    pages = java.getElements(aid);
  }
}
```

外加**候选 id 循环**：`[推导id, 全局bookId]` 逐个尝试（全局值作第二候选兜底，不当首选）。

### 3.5 toc 取值链（兼容 `++` 调试只设 tocUrl）

```javascript
var _bk = (typeof book !== 'undefined' && book) ? book : null;
var _bu = _bk ? String(_bk.url || '') : '';
if (!_bu) { _bu = String((_bk && _bk.tocUrl) || ''); }
if (_bu && !/^https?:/i.test(_bu)) { _bu = String(baseUrl || ''); }   // data: 过滤
if (_bu && !/^https?:/i.test(_bu)) { _bu = ''; }
```

### 3.6 replaceRegex 空书名保护

`.*{{book.name}}.*` 在 book.name 为空时（`--` 调试/异常态）匹配全文清空正文 → 改 **`{{NBK(book)}}`**：

```javascript
function NBK(b) {   // ★htmlunit: Kotlin 空 Java String 是 truthy 对象，必须 length 判
  try { var n = b ? b.name : null;
        if (n !== null && n !== undefined && String(n).length > 0) return String(n); } catch (e) {}
  return '_NBNB_';   // 永不匹配的哨兵
}
```

> 翻车复盘：第一版写 `if (b && b.name)`，单测用普通 JS 对象（`{name:''}`→falsy→正常）全过，真 Book（`getName()` 返回 java.lang.String 空串→**truthy**）走进 return '' 仍然清空。**Java 值的真值判断只在单测环境验不出来，必须用真对象测。**

## 四、选站 UI 三件套

### 4.1 登录界面（loginUrl + loginUi）

**入口**：书源编辑 → ⋮ → 登录。`loginUrl` 顶层具名函数集（与 jsLib 共享 scope，GET/SET/hosts 直接可用）：

```javascript
function setSite(u) {
  try {
    var d = {}; try { d = JSON.parse(String(source.getVariable()) || '{}'); } catch (e) { d = {}; }
    d.server = u;
    source.putVariable(JSON.stringify(d));
    try {   // ★同步 infoMap 库：防发现页下拉的过期状态回写覆盖
      var ik = 'infoMap_' + String(source.getKey());
      var m = {}; try { m = JSON.parse(String(cache.get(ik)) || '{}') || {}; } catch (e) { m = {}; }
      m['域名'] = u;
      cache.put(ik, JSON.stringify(m));
    } catch (e) {}
    try { source.refreshExplore(); } catch (e) {}   // ★action 跑在 IO 线程，可过主线程检查
    ...toast + return '已切换: ' + s;
  } catch (e) { ...toast '失败' }
}
function siteNow() { ...读 getVariable 返回 '当前站点: xxx'; }   // 供 viewName
function fixExplore() { try { source.refreshExplore(); ...toast; } catch (e) {...}
                        try { java.refreshExplore(); } catch (e) {} return 'ok'; }
function login() { try { java.toast('本面板用于切换网站，无需账号'); } catch (e) {} return true; }
```

`loginUi` 用 **`<js>` 运行时生成**（零手抄、自动跟随 hosts 增减）：

```javascript
<js>
(function(){
  var rows = [];
  function btn(name, action, pct, viewName) {
    var r = { type: 'button', name: name, action: action,
              style: { layout_flexGrow: 1, layout_flexBasisPercent: pct } };
    if (viewName) { r.viewName = viewName; }
    rows.push(r);
  }
  btn('📍查看当前', "java.toast((function(){...读server...})())", 0.34,
      "'当前站点: '+(function(){...GET真值...})()");
  btn('⚙恢复默认', "setSite('https://www.kelexs.com')", 0.33);
  btn('🔄重建发现按钮', 'fixExplore()', 0.33);
  var H = []; try { H = hosts; } catch (e) { H = []; }
  if (!H || !H.length) { H = ['https://www.kelexs.com']; }
  for (var i = 0; i < H.length; i++) { (function (h) {
      var label = String(h).split('//')[1] || String(h);        // 零反斜杠：split/substring 截取
      if (label.indexOf('www.') === 0) label = label.substring(4);
      if (label.length > 4 && label.substring(label.length - 4) === '.com')
        label = label.substring(0, label.length - 4);
      btn(label, 'setSite(' + "'" + h + "'" + ')', 0.2);
  })(H[i]); }
  return JSON.stringify(rows);
})()
</js>
```

实测：**47 行**（3 控制 + 44 站，0.2 宽五列网格），NestedScrollView + FlexboxLayout 可滚动换行。

**源码级要点（SourceLoginDialog.kt / BaseSource.kt）**：

- `handleButtonClick` = `lifecycleScope.launch(IO)` → **action 在 IO 线程**，`source.refreshExplore()` 的 `isMainThread` 检查能过（它内部 runBlocking 清 kinds 两级缓存）
- `getLoginUiJs()` 吃 `<js>…</js>`（JS_PATTERN），`evalUiJs = evalJS(loginJS + code)` → 生成代码能用 jsLib 的 `hosts`、loginUrl 的函数
- `BaseSource.evalJS(jsStr, bindingsConfig=默认参数)` —— **Kotlin 默认参数不生成单参 JVM 重载，Rhino 调 `evalJS(str)` 报"找不到方法"**；测试复刻对话框逻辑时改用**同环境直 eval（loginJS + code 合成一串）**
- `login()` 只有 `loginData` 非空（存在非空 text/password 行）才被调用；纯按钮面板 ✓ 键走 `removeLoginInfo()+dismiss()`，login() 留占位即可（E 版会调，跨版本兼容）
- 行类型支持 `text/password/button/label/toggle/select`；button 的 `viewName` 走 `evalUiJs`（runCatching→null 回退 name，坏表达式不炸面板）

### 4.2 发现页下拉（select）

本 App 的 select 是**点击循环字符**（ExploreAdapter）：点击时 `infoMap[title] = char` → 再 `evalButtonClick(action)`。

```javascript
push('域名', '', 1, 1, {
  "type": "select",
  "chars": hosts,
  "default": GET('server') || hosts[0],          // ★重建后显示当前真值
  "action": "SET('server', infoMap['域名']); java.refreshExplore()"   // ★SET 移进 action
});
```

三条铁律：

1. **`evalButtonClick` 绑定 `java` + `infoMap`**（ExploreAdapter.kt:578 `put("java",…); put("infoMap",…)`）→ action 里能读到刚写入的 infoMap → select→server 的 SET 放这里链路闭环
2. **kinds 求值期绝不回写 server**：求值期拿到的 `infoMap` 是 **live InfoMap 对象**（`exploreInfoMapList` 进程级缓存），旧值会把登录面板刚选的站覆盖回去
3. `java.refreshExplore()` 在**发现上下文**=回调 `refreshExplore(item,pos,binding)`：清 kinds 两级缓存（aCache 文件 + exploreKindsMap 内存）→ `notifyItemChanged` 整行重建；在**登录上下文**=对话框 reUiView（重绘面板）。同一个方法，两个回调，别搞混。

### 4.3 状态栏（下拉正下方显示当前网址）

```javascript
res.push({ title: '当前网址', url: '', type: 'button',
  style: { layout_flexGrow: 1, layout_flexBasisPercent: 1, layout_justifySelf: 'flex_start' },
  viewName: "'🌐 当前网址: ' + (GET('server') || '未设置')",
  action: "java.toast('当前网址: ' + (GET('server') || '未设置'))" });
// kinds 求值时把当前站同步进 live infoMap → 下拉重建后显示当前站
try { if (infoMap && GET('server')) { infoMap['域名'] = GET('server'); } } catch (e) {}
```

- 行类型 `Type.url/button` 都支持 viewName：**`viewName.length in 3..19 && 首尾单引号` → 字面量；否则异步 eval**（表达式必须 >19 或不满足字面量条件）
- 状态栏**读 `GET('server')` 真值**，不依赖下拉显示状态——下拉滞后时它是唯一可信显示
- viewName 求值环境：`evalUiJs = source.evalJS(jsStr){put("infoMap",…)}`（不 prepend loginJS，但 evalJS 自动链 jsLib → GET 可用）
- `layout_justifySelf: flex_start` 左对齐（Type 分支支持 flex_start/flex_end/center）

### 4.4 一致性模型（谁在什么时候生效）

| 时机 | server 写者 | 下拉显示 | 状态栏 | 分类 URL |
|---|---|---|---|---|
| 登录面板点站点 | setSite（变量+infoMap库） | 重建前滞后 | 重建前滞后 | 已重建（setSite 清了 kinds 缓存） |
| 下拉循环点击 | select action SET | 即时（先写 live infoMap） | 重建后即时 | 重建后即时 |
| 打开书籍详情刷新 | init og:url 对齐 | 滞后（下次重建纠正） | 下次行重建纠正 | 下次重建纠正 |
| check_source | 无 UI，只读 | — | — | 用缓存/求值，已不回写 |

**时机闭环**：setSite / select 切站都会清 kinds 缓存 → 下次进发现页必然重新求值 → 同步行 `infoMap['域名']=GET('server')` 执行 → 下拉与状态栏一致。
**已知外观滞后**（进程内发现页未重建）四种刷新触发：点一下下拉、点任意行按钮、发现页菜单-刷新、登录面板🔄重建发现按钮。

## 五、check_source 校验器三坑（本源连续两轮校验失败的真凶）

源码链：`CheckSourceService.doCheckSource` = 源地址探测 → **checkSearch(getCheckKeyword)** → checkBook → **checkDiscovery**（`source.exploreKinds().firstOrNull { !it.url.isNullOrBlank() }?.url` → exploreBookAwait）。

1. **无 UI 态 infoMap 洗变量**：kinds 求值里 `SET('server', infoMap['域名'])`，校验器环境没有「域名」键 → `SET(server, undefined)` → JSON.stringify 丢键 → 变量变 `{"bookId":…}` → `sourceUrl=''` → 生成 `/list-1-{{page}}/` 相对 URL → `Expected URL scheme http/https`。
   **修复 = SET 整体移进 select action**（校验路径永远不执行 action），次选=存在性保护 `if (infoMap && infoMap['域名'])`。
2. **初始化哨兵不自愈残缺变量**：`source.getVariable()=="" || =='{}'` 对 `{"bookId":"X"}`（server 缺失）不触发 `began()` → 后续 sourceUrl 空。**改 `if (!GET('server')) { began(); }`**（覆盖 ''、'{}'、残缺三态）。
3. **kinds 两级缓存**：`aCache.getAsString(getExploreKindsKey())` + 内存 `exploreKindsMap`——切站不清缓存则分类 URL 冻结在旧站；`BaseSource.refreshExplore()`（= 清两级）必须在 **IO 线程**调用。

> 教训：**校验器 = 无 UI、无 infoMap、无前序状态的"裸环境"**——凡依赖 UI 状态的 kinds 求值代码都要问一句"校验器跑得到吗"。

## 六、模板引擎与 htmlunit 四条铁律

1. **`{{}}` 双通道**：不带括号的表达式被当**属性路径**解析——`{{book.name||'_NBNB_'}}` 恒得 `''`（不是 JS！）；**带括号才走 JS 求值**：`{{GET('server')}} / {{SRV(baseUrl)}} / {{NBK(book)}}` 正常。写模板保护条件必须用**函数调用形态**。
2. **htmlunit Rhino 真值铁律**：Kotlin/Java 空字符串是 **truthy 对象**——`if (b.name)` 对 `name=''` 为真 → `String(javaString)`='' 照样返回空。Java 值判空必须 `String(x).length > 0`；真值判断只对纯 JS 值可靠。
3. **Rhino 里 `java.lang.String` 没有 `.length` 属性**（返回 NaN/method 引用）→ 先 `String(...)` 包裹再取 length/substring（jsoup `.text()` `.attr()` 同族坑）。
4. **Kotlin 默认参数方法 Rhino 调不到单参形态**：`BaseSource.evalJS(str)` 报"找不到方法(string)" → 复刻 App 调用逻辑改用同环境直 eval 拼串。

## 七、交付与验证方法论（v1→v8 全记录）

1. **构建脚本纪律**：所有补丁用**精确锚点 + `assert count==1`** 落在原始 JSON 上（幂等可重跑）；每个 JS 块 `node --check`（23 块）；bookUrlPattern 编译 + 正负样本单测；**锚点差一个空行都会 assert 挂**——挂了就打印 repr 对齐。
2. **Node 行生成仿真**：桩 `source/java/cache/hosts/infoMap` 直跑 exploreUrl/loginUi/loginUrl，断言行数/行序/viewName/action/同步效果（本源：kinds 37 行、登录 47 行、infoMap 同步过期值→当前值）。
3. **真机 eval_js 探针**：SRV 单测（漂移/同域/无全局/无URL 四态）、kinds 求值（真 jsLib+真 infoMap）、viewName/action 直 eval、`setSite` 四要素回读（变量/infoMap库/清缓存/toast）。
4. **污染态对照**（最有说服力）：把变量故意置成故障态（server=死站 boluomao）→ `--章节URL` 调试正文必须非空、`++书籍URL` 调试目录必须推导正确 → 证明内容链路已不依赖全局。
5. **check_source ×N 全通过** + **每版全字段 md5 本地↔App**（顶层字段 + rule 子字段全比对；任何一版导入后先回读再继续）。
6. **大源交付通道**：48KB+ 超 save_source 内联上限（~19KB）→ `scripts/dpaste_upload.py`（字节级 md5 校验）→ `java.openUrl('legado://import/bookSource?src=…')` 深链 → 用户点确认 → **硬证据 = HTTP 日志 `GET raw → 200` + get_source 回读 md5**。深链一次只拉一次（防 429 → XML 语法错误误诊）。
7. **环境铁律**：proot `--kill-on-exit` → nohup 后台进程随 shell 死，批量探测必须**前台 + ThreadPoolExecutor 并行**（6 线程 16 站 ≈ 90s）。

## 八、避坑清单 K1~K18

| # | 坑 | 解法 |
|---|---|---|
| K1 | 正文/目录分支读全局 server → 漂移即空 | SRV(book.bookUrl/baseUrl) URL 自治 |
| K2 | chapterUrl 拼全局前缀，重刷即污染 | chapterList 输出绝对 URL + `chapterUrl=$.chapterurl` |
| K3 | 搜索 deep-link 别名 id ≠ og 规范 id → data-aid 失配目录炸 | 页面 data-aid 实际值自纠 + 全局 bookId 第二候选 |
| K4 | `.*{{book.name}}.*` 空名清空全文 | `{{NBK(book)}}` + length 判空 |
| K5 | `{{a||'x'}}` 被当属性路径恒得 '' | 模板保护条件用带括号函数形态 |
| K6 | htmlunit Java 空串 truthy，单测（JS 对象）测不出 | 真对象测 + `String(x).length>0` |
| K7 | kinds 求值期 SET 回写 → 过期 live InfoMap 覆盖登录选站 | SET 移进 select action（evalButtonClick 带 infoMap） |
| K8 | 校验器无 UI 态 infoMap 缺键 → 洗成 `{}` → `/list-` 相对 URL 炸 | 同 K7 + 存在性保护 |
| K9 | 初始化哨兵 `==''‖=='{}'` 对残缺变量不自愈 | `!GET('server')` 三态覆盖 |
| K10 | `refreshExplore` 主线程检查直接抛 | 放登录 action（IO 线程）里调 |
| K11 | `BaseSource.evalJS(str)` Rhino 单参调不到 | 同环境直 eval(loginJS+code) 拼串 |
| K12 | `login()` 调用条件（非空文本行才调） | 纯按钮面板留占位函数（E 版兼容） |
| K13 | kinds 两级缓存不清 → 切站后分类 URL 冻结 | setSite 内 `source.refreshExplore()` |
| K14 | 下拉显示与 server 真值分离（进程内滞后） | 状态栏读 GET 真值 + kinds 求值同步 infoMap |
| K15 | select 是点击循环不是弹窗，先写 infoMap 再执行 action | action 内直接 `infoMap['域名']` 取值 |
| K16 | MCP save_source 手抄大 JSON 转义必坏 | dpaste+深链（文件直传零转抄） |
| K17 | Contents API 中文路径未编码 → ascii 报错 | `urllib.parse.quote(path, safe='/:?=&')` |
| K18 | proot nohup 后台进程随 shell 死 | 前台 + ThreadPoolExecutor 并行 |

## 九、案例档案

- **rrssk聚合 v8**：44 域名 /14 模板 / 双体系（rrssk家族+菠萝猫）
  - 成品：`examples/rrssk聚合_44域名.json`（52532B，md5 `47b3976311e9286667f78f41b238f3a0`）
  - 案例页：[rrssk聚合_44域名多站聚合](../examples/rrssk聚合_44域名多站聚合.md)
  - 版本链：v6 五层修复 → v7 登录面板47行 → v8 状态栏+infoMap同步；dpaste：3CZ5PVANK / 82UASB49M / HXL2U96MA
  - 构建与探测：`build.py`（23 块 node 校验）/ `probe2.py`（前台并行探测）

## 十、验收 checklist

- [ ] 污染态（server=他站/死站/空）下 `--章节URL` 正文非空、`++书籍URL` 目录正确
- [ ] 搜索在任一 server 值下走中转正常（死站除外，需切站提示）
- [ ] 登录面板生成行数 = 3 + hosts 数；点站点 toast/变量/infoMap库/发现重建四要素
- [ ] 发现页行序：域名 select → 🌐 当前网址状态栏 → 搜索关键词
- [ ] 下拉循环切站后状态栏、分类 URL、搜索入口三者一致
- [ ] check_source 通过；全字段 md5 与交付文件一致
