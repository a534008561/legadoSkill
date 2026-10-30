# 方法-订阅源动态线路与rel=next正文翻页（MissKon 实战）

> 261030 MissKon(https://misskon.us/zh/) 写真图集订阅源制作全过程提炼。适用：写真/图集类订阅源、多线路轮换站、正文多页图集。LT版(LegadoTeam)与E版(legado-E)双兼容。

## 一、站点档案速查

| 项 | 值 |
|---|---|
| 技术栈 | Laravel+Livewire 服务端渲染，UTF-8 |
| 首页 | /zh/ 56卡片 |
| 列表页 | /zh/albums 与 /zh/series/{slug} 各24卡片/页，`<link rel="next">` 分页 |
| 搜索 | `/zh/albums/search?q=`（大小写不敏感；分页 `&page=N`，HTML里 `&amp;` 需还原） |
| 正文 | /zh/albums/{slug}?page=N 每页20张；photoViewer(JSON) + 明文img并存 |
| 图片域 | images.misskon.us，无防盗链（无Referer也200） |
| 发布页 | misskon.cc（列当前 us + 备用 org） |
| 限频 | robots.txt 官方声明 /albums 60 req/min（应用级） |
| 登录 | 无需登录 |

## 二、核心设计（双版本兼容）

### 2.1 sortUrl：@js: 产出 `名称::URL` 纯文本

E 版 `RssSourceExtensions.sortUrls()` 只认：
- 纯文本 `名称::URL`（`&&`或换行分隔）
- `<js>/@js:` 脚本产出（**结果有 ACache 缓存**，改线路后需清缓存；LT 版 RssSortActivity 菜单有「清理排序缓存」入口）

**JSON 对象格式 E 版不认**（LT 版 isJsonObject 分支是 LT 专有）。双版本通吃 = `@js:` 产纯文本。

```javascript
@js:
var d = '';
try { d = String(source.get('mkLine')); } catch (e) { d = ''; }
if (d === 'null' || d === 'undefined' || d === '') d = 'https://misskon.us';
var L = [];
L.push("最新图集::" + d + "/zh/albums");
// ...61系列
L.join('\n');
```

### 2.2 searchUrl：单 {{}} IIFE 整串产出

`AnalyzeUrl.replaceKeyPageJs` 走 `RuleAnalyzer.innerRule("{{","}}")` 的 **chompCodeBalanced**：`{{}}` 内的花括号必须配平（body 内不能有单独的 `}}` 或不平衡 `{`），否则整段求值失败 URL 按字面发出 404。

```javascript
{{(function(){var d='';try{d=String(source.get('mkLine'))}catch(e){}if(d==='null'||d==='undefined'||!d)d='https://misskon.us';return d+'/zh/albums/search?q='+encodeURIComponent(key)})()}}
```

### 2.3 正文 rel=next 全页图片收集（ruleContent @js: IIFE）

```javascript
@js:
(function () {
  var NL = String.fromCharCode(10);
  var MROOT = MkRoot();   // jsLib: 双通道读 mkLine
  var HDR = '{"User-Agent":"..."}';
  function fetchPage(url) {
    try {
      var r = java.connect(url, HDR, 15000);
      if (r == null) return '';
      var b = '';
      try { b = String(r.body()); } catch (e) { b = ''; }
      return b;
    } catch (e) { return ''; }
  }
  // 双形态正则吃 明文img + photoViewer 的 \/ 转义
  var re = /photos\\?\\/([A-Za-z0-9-]+)\\?\\/(\\d+)\\?\\.webp/g;
  // 循环: baseUrl 开始, rel=next 递进, seenPage 去重, guard 30页
  // 汇总: 标题/模型/keywords/datePublished/总张数 meta行 + 全量 img
})();
```

四判停：`!body`/`body<1000`/`无图片`/`无rel=next`/`seenPage命中` 任意触发即终止。

## 三、登录面板（V1静态 + viewName 动态文本 + 12线路位）

loginUi（JSON 数组）：
- mkPub 发布页输入框（viewName 用静态 hint：`'发布页地址(默认cc)'`，3..19字符+单引号包裹走字面量分支）
- 🧭获取发布页线路 `MK_fetchPub()`
- ⏱测试延时 `MK_testAll(true)`（自动切最快+reLoginView）
- 线路1..12：`action: "MK_switch(N)"`（索引制，MK_bases() 顺序即线路顺序），`viewName: "MK_lineBtn(N)"`（动态显示 `▶⚡域名 ms延时`）

**viewName 求值环境=source.evalJS（有 source 绑定）**；action 环境=handleButtonClick `source.evalJS("$loginJS\n$buttonFunctionJS"){put("java", SourceLoginJsExtensions)}`（java 被覆盖成 SourceLoginJsExtensions，source 仍绑定）。两环境都执行 loginUrl 的函数库。

各阶段 longToast：开始/完成/最优/已切换/失败原因。`java.reLoginView()` try/catch 包裹（E版 SourceLoginJsExtensions 有 @JvmOverloads 可用）。

## 四、交付纪律（订阅源）

**MCP save_source 是 BookSource 专用**（BookSourceController.saveSource→GSON.fromJsonObject<BookSource>）。订阅源必须走 LAN web 服务：
- 保存：`POST http://<IP>:1122/saveRssSources`，body = **RssSource JSON 数组**，头 `x-legado-token`
- 回读：`GET /getRssSources` → `{"data":[...]}`，逐字段比对（17项校验）

MCP debug_source 也只找 BookSource（订阅源 debug 报"未找到书源"）。**订阅源 App 内验证 = eval_js 小探针**（**长参数（>1KB）会被传输层截断污染**，控制在 400B 内；复杂逻辑沙盒 node mock（eval 语义=Rhino 完成值语义，注意 `eval(src + ';""')` 会吃掉完成值）。

## 五、本次踩坑清单（8条）

1. **searchUrl 括号必须配平**：`{{(function(){...})()}}` IIFE 尾多一个 `}` → RuleAnalyzer chompCodeBalanced 失败 → 整段被吞 → URL 字面发出 404。**验证法：数 `{`/`}` 相等且 body 内无内部 `}}`**。
2. **E版 JsNull truthy**：`source.get('未设置') || '默认'` 不走兜底（JsNull 是 truthy 对象）；String() 后='null'。必须三态归一 `d==='null'||d==='undefined'||!d`。
3. **订阅源正文环境 source=JsExtensions 无 put/get**（有 getVariable）→ jsLib 函数 try source.get catch 转 getVariable 双通道。
4. **正文 HTML 双转义形态**（明文 `photos/` + photoViewer `photos\/`），单形态正则漏抓；`photos\\?\\/...` 一次吃双形态，**slug 取 group(1)（m[0] 前缀是 photos）**。
5. **sortUrl 缓存**：E 版 @js: sortUrl 结果有 ACache 缓存（key=md5(sourceUrl+sortUrl)），**切线路后需清缓存**（LT 版 RssSortActivity 菜单；E 版重新进入页时 RssSortViewModel.initData 不清缓存，需要手动清或重存源）。
6. **MCP save_source 不能保存订阅源**；LAN /saveRssSources 是唯一通道（body=数组）。
7. **MCP eval_js/save_source 长参数会被传输层截断污染**（实测 >1.3KB 出现 token 注入漂移），小探针控制在 400B 内。
8. **robots.txt 是限频信息金矿**：官方声明 Crawl-delay/应用级限频注释、搜索接口格式、sitemap。**不主动探测限频边界**（用户纪律）。
9. **★★订阅源 ruleContent 首行 `//` 注释必须加 `@js:` 前缀**（用户实测报障）：订阅源 ruleContent 无书源侧 <usehtml> 通道，AnalyzeRule.splitSourceRule 模式识别（AnalyzeRule.kt:690 `startsWith("/")` → Mode.XPath）把首行 `// ===` 注释当 XPath 执行 → XpathSyntaxErrorException。列表正常但正文炸的指纹：列表规则是 tag./class. 开头（jsoup）而正文是裸 JS。修复 = `@js:` 单独一行 + JS 从第二行开始。
10. **★★图集站「正文比网站慢」→ URL 直构取代翻页抓取**（用户实测反馈）：v1 rel=next 链串行抓 3-5 页 HTML 才显示（6-8s）。先验证站点不变量：**图片按 `photos/{slug}/{1..N}.webp` 连续编号 + 第1页含总张数（"N 张照片"）**——4 图集实测尾页图号=总数连续一致、构造 URL 直连 200 ⇒ 只抓第 1 页拿 slug+total+meta，其余 URL 按 1..total 直构，串行请求 4→1 **秒开**。slug/total 解析失败回退 rel=next 链兜底。**方法论：图集/漫画站先验证「连续编号+总数可取」，成立就直构。**
11. **★★慢CDN下 App 端唯一有效手段=布局与体验优化**（用户反馈「慢慢浮现但能看」+定量实测）：正文 HTML 首页 App 端仅 1.3s（规则已到头），图片单张 5.6-22.8s 波动=网络层。三项否决实验：公共图片反代（weserv/wsrv/statically 全被墙 ConnectionReset）；站点缩略参数（?w= 恒返原图、尺寸变体 404、无 srcset）；加速线路（图片域无备选）。⇒ 有效手段=正文图区 CSS grid 双列（@media≥600px 三列）+ shimmer 骨架动画背景 + alt 序号。**另：LT/E 双 App 数据完全独立，源更新必须双端各存一次（各自 web 服务端口）**。
12. **★★★源码纠错：订阅源正文环境 source=RssSource 本体（有 put/get）；「双通道 getVariable 兜底」写法是错的且有危险副作用**：`Rss.analyzeContentPage → AnalyzeRule(rssArticle, rssSource) → evalJS bindings["source"]=rssSource`（两版一致）⇒ 正文 @js: 里 `source.get('key')` 直接可用。★`JsExtensions.get(urlStr, headers)` 是 **HTTP GET 请求**、`getVariable()` 是**无参签名**——带参 `getVariable('key')` 会重载错位到 `get(url,headers)` **变成发 HTTP 请求**。旧文档「正文环境无 put/get」结论作废。
13. **站点无低清源时「画质切换」的诚实落地**：三项实验定性（S3+CF 无处理参数/cdn-cgi 404；cover.webp 反而更大；公共反代全被墙）⇒ 物理上无法减下载量，档位=显示形态：HD=双列 grid（≥600px 三列）/ lite=单列大图，loginUi 画质按钮 source.put('mkQuality')+viewName 动态显示，content.js 读变量分支 CSS。切档后旧文章须清存档（缓存不重跑规则）。

## 六、App 内实测清单（用户侧）

1. 订阅源列表找到「MissKon写真图库」，打开发现页 → 应见 63 个分类 tab
2. 点「最新图集」→ 24 卡片（封面+标题+相对时间）
3. 底部加载更多 → PAGE 分页自动 page+1
4. 搜索「Abby」→ 24 结果
5. 打开任一图集 → 应显示全本图片+meta行（作者/标签/日期/总张数）
6. 登录面板 → 各按钮 Toast 提示、线路按钮显示延时、切换后重开发现页生效(如未生效：排序页菜单「清理排序缓存」）
7. ⚠站点限频 60 req/min，勿高频刷新
