# 实战案例库

本目录包含 Legado 书源的实战案例，每个案例都是经过验证的完整书源。

## 实战案例参考

详细案例请查看(这个是假的，后面我会加真的案例)：
- [API 搜索案例集](references/api-search-examples.md)
- [加密参数处理](references/encrypted-api-guide.md)
- [反爬措施应对](references/anti-crawling.md)

## API 搜索案例
- [全本小说网](examples/api-search.md#全本小说网) - POST 请求，加密参数
- [笔趣阁](examples/api-search.md#笔趣阁) - GET 请求，简单参数

## 加密参数案例
- [动态变量加密](examples/encrypted-api.md#动态变量) - JS 提取变量
- [时间戳签名](examples/encrypted-api.md#时间戳) - 实时计算签名


## 📚 案例列表

### 1. 番茄小说 zym888
- **文件**: [番茄小说 zym888.json](./番茄小说 zym888.json)
- **类型**: 小说网站
- **特点**: 
  - 移动站点（m.zym888.com）
  - 搜索需要动态获取大量加密参数（20+ 变量）
  - 提供发现（分类）功能
  - 完整的搜索、详情、目录、正文规则
- **技术要点**:
  - JavaScript 动态提取页面 JS 变量
  - POST 请求构建复杂参数字符串
  - JSONPath 解析 API 响应
  - 发现规则使用自定义 URL 格式
- **适用场景**: 学习如何处理加密参数 API

### 2. 喜漫漫画
- **文件**: [喜漫漫画.json 参考.txt](./喜漫漫画.json 参考.txt)
- **类型**: 漫画网站
- **特点**:
  - 需要 CloudFlare 防护绕过
  - 有滑块验证码
  - 图片需要解密
  - 使用 WebView 获取内容
- **技术要点**:
  - CloudFlare 防护检测与绕过
  - 滑块验证码自动处理（轨迹记录与回放）
  - 漫画图片解密规则
  - WebView 与 AJAX 混合使用
  - Cookie 管理
- **适用场景**: 学习如何处理有防护的网站

### 3. 霹雳书屋
- **文件**: [霹雳书屋.json 参考.txt](./霹雳书屋.json 参考.txt)
- **类型**: 小说网站
- **特点**:
  - 有人机验证（CloudFlare + 滑块）
  - 多接口切换（4 个备用接口）
  - 丰富的发现分类
  - 详细的书源注释
- **技术要点**:
  - 自动验证大佬（完整的验证处理逻辑）
  - 多接口设置与切换
  - 发现分类动态生成
  - 轨迹记录与统计
  - 加密器创建与使用
- **适用场景**: 学习复杂验证处理和多接口配置

### 4. 3a 小说
- **文件**: [3a.json 参考.txt](./3a.json 参考.txt)
- **类型**: 小说网站
- **特点**:
  - CloudFlare 防护
  - 需要 WebView 绕过
  - 自定义图片解密
- **技术要点**:
  - CloudFlare 检测与绕过
  - WebView 获取 HTML
  - 图片解密 JavaScript
- **适用场景**: 学习 CloudFlare 防护处理

### 5. 皮皮小说（登录+验证码+限频破解完整版）
- **文件**: [皮皮小说_www.ppxsw.cc.json](./皮皮小说_www.ppxsw.cc.json)
- **类型**: 小说网站（需登录）
- **特点**:
  - 搜索必须登录会话，服务端以 search_time Cookie 做搜索限频
  - 登录需图形验证码（会话绑定）
  - 正文 base64 反爬（加密对象名每书随机）
  - 分类页/目录页按 UA 返回双模板
- **技术要点**:
  - loginUrl 具名函数集 + loginUi 按钮黄金范式（startBrowser 看图手填）
  - searchUrl 前置 JS 删 search_time 实现无限搜索（setCookie 整体替换语义规避）
  - 动态提取 `_keyStr` 对象名做 base64 解码
  - `class.br-b-1` 过滤最新倒序区修复目录乱序
  - og:url 正则重组 tocUrl（含 ruleBookInfo 字段位置坑）
  - loginCheckJs StrResponse 透传契约
- **配套文档**: [登录注册验证码与限频破解实战-ppxsw篇](../references/登录注册验证码与限频破解实战-ppxsw篇.md)
- **适用场景**: 学习登录态书源、Cookie 精细操作、反爬正文解码

### 6. 皮皮小说网ppxsw（注册接口参考版）
- **文件**: [皮皮小说网ppxsw_注册版参考.json](./皮皮小说网ppxsw_注册版参考.json)
- **类型**: 小说网站（登录+注册双功能样本）
- **特点**:
  - 同站另一实现风格：dl()/zc() 双按钮（登录+注册）
  - 注册端点 /qs_register_go.php 参数体系（name/mobile/pass/pass2/code）
  - source.getLoginInfoMap() 取 UI 值风格
- **技术要点**:
  - 注册与登录参数名对照（user_name→name、user_pass→pass+pass2、多 mobile）
  - 取码前 cookie.removeCookie 重置会话保证图码同源
  - Packages.java.lang.Thread.sleep 唯一延迟手段（此 App 无 java.sleep）
  - 正文兜底链：base64 特征匹配失败 → java.getString 直取 #txt
  - nextContentUrl 用 [rel$=prefetch] 锚点 + `_N.html` 正则校验分页
- **⚠️ 已知限制**: 该版本在对话框上下文直接调 java.getVerificationCode，lyc 版此上下文不弹窗；实际部署请改 startBrowser 方案（见配套文档第 2 节方案树）
- **适用场景**: 学习注册接口接入与参数体系分析

### 7. NicoManga 生肉漫画（图片源 + Next.js RSC 混淆解码）
- **文件**: [尼科漫画生肉_www.nicomanga.com.json](./尼科漫画生肉_www.nicomanga.com.json) + 案例解析 [尼科漫画生肉_www.nicomanga.com.md](./尼科漫画生肉_www.nicomanga.com.md)
- **类型**: 漫画网站（bookSourceType=2 图片 / 免登录）
- **特点**:
  - 详情/阅读页是 Next.js(Turbopack) 客户端壳，数据藏在 RSC flight 流(self.__next_f.push)的 chaotic_payload
  - 混淆算法：密文字符 = UTF8字节 ⊕ 循环密钥"NicoMangaX2" + 19968，全串严格落在 U+4E00-U+4EFF
  - 列表/搜索/分类页仍是服务端渲染（新旧混合站：新壳旧芯）
  - 图床 ihlv1.xyz 无 UA 403（Referer 不需要）→ UA 是生死线
  - 目录上限最近 ~148-169 话＝站点自身限制（已按 UI Show All 逻辑实锤）
- **技术要点**:
  - jsLib 纯 Rhino 解码引擎 NM：push反转义拼接 → 最长CJK段 → XOR → 手写UTF8解码 → 大括号配平截JSON
  - chapterList/bookList @js 返回 NativeObject 数组 + 键值直取（AnalyzeRule 源码级通道，绕 AnalyzeByJSoup 污染）
  - 章节数组 reverse 成升序；exploreUrl `<js>` 动态生成（api_genres.php b64 标签 54 按钮）
  - 整话图片一次给全无 nextContentUrl；content 用 `<img src=…>` 拼接输出
  - **MCP 零转义写法**：全书源 JS 改零反斜杠零内嵌双引号（fromCharCode(34)/(92)、[.]/[0-9]）解决 save_source 双重转义损坏
- **配套方法论**: [references/方法-NextJS-RSC-flight的chaotic_payload解码.md](../references/方法-NextJS-RSC-flight的chaotic_payload解码.md)
- **适用场景**: 学习 Next.js 壳站数据解码、图片漫画源配置、MCP 大书源安全提交

### 8. 小小阅读/书香之家 App 聚合（APP接口聚合书源）
- **文件**: [小小阅读书香之家app_s.wendulou.com.json](./小小阅读书香之家app_s.wendulou.com.json) + 案例解析 [小小阅读书香之家app_s.wendulou.com.md](./小小阅读书香之家app_s.wendulou.com.md)
- **类型**: 小说网站（多App聚合 JSON API，免登录免Cookie无频控）
- **特点**:
  - 一批看书App（小小阅读/书香之家/点点阅读/追书大师…）共用后端：搜索/详情/分类/目录/正文全JSON无HTML
  - 同一本书聚合10+来源站，书架设书籍变量即切换（init改写tocUrl）
  - 同一后端12+镜像域名，改bookSourceUrl即换线路
  - 双层加密：动态种子信封AES-256-CBC（搜索/详情/分类）+固定密钥AES-128（目录/正文）
- **技术要点**:
  - 子域名推导 `source.getKey().replace('//s','//book')` 一处改全链路跟随
  - 鉴权=UA尾部`_{package}`后缀（sign/time实测不校验，破坏性实验定位）
  - IV派生陷阱：md5Encode是hex字符串、前16ASCII字节⊕种子⊕0xFF；CBC错IV只毁首块
  - bookSourceComment存decode()公共库eval复用；发现页动态分类树+Flex网格
  - searchUrl存词java.put('key',key)+v1明文接口回退+三通道bookList通吃三种容器
- **配套方法论**: [references/方法-APP接口聚合书源拆解.md](../references/方法-APP接口聚合书源拆解.md)
- **适用场景**: 学习App接口逆向、多层AES信封解密、单书源多站换源聚合

## 🎯 如何使用案例

### 方式 1：直接导入 Legado
1. 复制案例 JSON 内容
2. 打开 Legado APP
3. 我的 → 书源管理 → 右上角菜单 → 导入书源 → 剪贴板导入
4. 测试书源功能

### 方式 2：学习参考
1. 阅读案例的 `bookSourceComment` 了解网站特点
2. 分析 `searchUrl` 学习请求配置
3. 研究 `ruleSearch` 学习规则编写
4. 对比不同案例的实现差异

### 方式 3：修改适配
1. 基于相似案例修改
2. 修改 `bookSourceUrl` 为目标网站
3. 调整规则选择器匹配目标网站
4. 测试并调试

## 📖 案例解析示例

以**番茄小说**为例：

### 搜索规则分析
```javascript
// 1. 获取首页提取加密变量
var html = java.ajax('https://m.zym888.com/');
var params = {};
var matches = html.match(/var\s+(\w+)\s*=\s*"([^"]+)"/g);

// 2. 解析所有变量
if(matches) {
    for(var i = 0; i < matches.length; i++) {
        var m = matches[i].match(/var\s+(\w+)\s*=\s*"([^"]+)"/);
        if(m) params[m[1]] = m[2];
    }
}

// 3. 添加搜索关键字
params['q'] = String(key);

// 4. 构建完整参数字符串
var body = 'q=' + params.q + '&vw=' + params.vw + '&abw=' + params.abw + ...;

// 5. 返回 POST 请求配置
var url = 'https://m.zym888.com/api/search,' + JSON.stringify({
    'method': 'POST', 
    'body': String(java.encodeURI(body))
});
url;
```

### 规则提取分析
```json
{
  "ruleSearch": {
    "bookList": "$.data[*]",      // JSONPath 提取数据数组
    "name": "$.name",             // 提取书名
    "author": "$.author",         // 提取作者
    "bookUrl": "$.url",           // 提取书籍链接
    "coverUrl": "$.img",          // 提取封面图片
    "intro": "$.intro",           // 提取简介
    "kind": "$.category",         // 提取分类
    "lastChapter": "$.last"       // 提取最新章节
  }
}
```

## 🔑 关键技术模式

### 模式 1：动态参数提取
```javascript
// 适用于需要动态变量的网站
var html = java.ajax(url);
var params = {};
html.replace(/var\s+(\w+)\s*=\s*"([^"]+)"/g, (m, k, v) => params[k] = v);
```

### 模式 2：CloudFlare 绕过
```javascript
// 检测 CloudFlare
if(html.includes("Just a moment") || html.includes("Checking your browser")) {
    // 使用 WebView 绕过
    var result = java.webView(url, url, "document.documentElement.outerHTML");
}
```

### 模式 3：滑块验证码
```javascript
// 记录成功轨迹，下次直接使用
var savedTrack = source.get("success_track");
if(savedTrack) {
    // 使用保存的轨迹
    // ...
}
```

### 模式 4：多接口切换
```javascript
// 设置多个备用接口
var interfaces = {
    0: ["主站", "https://www.example.com"],
    1: ["二站", "https://www.example2.com"],
    2: ["三站", "https://www.example3.com"]
};
var current = source.getVariable() || 0;
var url = interfaces[current][1];
```

## 💡 学习建议

1. **从简单开始**：先学习番茄小说（纯 API，无验证）
2. **逐步深入**：再学习 3a 小说（CloudFlare 防护）
3. **挑战复杂**：最后学习喜漫漫画和霹雳书屋（完整验证处理）
4. **对比学习**：对比不同案例的相同功能实现
5. **实践修改**：基于案例修改适配新网站

## 📝 贡献案例

如果你有优秀的书源案例，欢迎添加到本目录！

案例格式要求：
- 文件命名：`网站名称.json` 或 `网站名称.json 参考.txt`
- 必须包含 `bookSourceComment` 说明网站特点和技术要点
- 书源功能完整（至少包含搜索规则）
- 规则注释清晰

### N. 晋江文学城（VIP 付费站顶级案例）
- **文件**: [晋江文学城_www.jjwxc.net.json](./晋江文学城_www.jjwxc.net.json) + [晋江书源经验模板_www.jjwxc.net.json](./晋江书源经验模板_www.jjwxc.net.json)
- **类型**: 小说网站（VIP 付费 / 需登录）
- **特点**:
  - 多接口拼装（搜索/详情/目录/正文/购买 走 4 个不同域名 5 个不同接口）
  - **双层密钥反爬**：固定 DES/CBC (`key=KW8Dvm2N iv=1ae2c94b`) + 响应头 `accesskey/keystring` 动态派生
  - 多通道登录：账密（含设备验证自动重试 6018/221003）+ 扫码登录（startBrowserAwait + data: URL）
  - `tocUrl` 自销毁设计：把 token 绑入 data:URL，preUpdateJs 失效自检 + java.refreshTocUrl
  - `payAction` 三段式：余额预查→DES 签名购买→result=true 触发自动重载
  - `java.ajaxAll` 批量预取 60 本书详情
  - 30+ 排行榜/分类 exploreUrl（用 style 分组）
  - 完整 13 章 740 行技术拆解文档（见 references/）
- **技术要点**:
  - `java.get(url,{}).header("accesskey")` 拿响应头（`java.ajax` 拿不到）
  - Rhino/Jetpack 双框架登录头读写兼容（getLoginHeaderMap vs getLoginHeader）
  - `cache.get("jjtime")` 3.2h 节流每日签到
  - 设备验证绕过：`checktype=phone/email + checkdevicecode="000000"`（任意非空值即可）
  - buy 接口只解析 URL 查询串（POST body 会被忽略）
  - tocUrl 兼容 data: URL 和 HTTP URL（bDe 函数）
- **适用场景**: 学习 VIP 付费站完整闭环（登录+浏览+购买+签到）/ 通用双层密钥反爬应对 / 复杂多接口拼装

---

**提示**：案例库按需加载，当前只加载了索引。需要具体案例时再读取对应文件。

### 8. 黑料网（useweb 内嵌浏览器 + legado-E 跨版本兼容）
- **文件**: /workspace/hlwf6/hlwf6.json（本地成品，含 build.py 构建脚本）
- **类型**: 成人吃瓜资讯站（发布页多线路轮换）
- **特点**:
  - 发布页 hlwf6.com → 多线路轮换主站（搜书吧模式自动测速选线，3分钟TTL）
  - 图文正文 + dplayer 视频文章（m3u8 签名约 1 小时时效）
  - **简介 useweb 真 WebView**：播放按钮+悬浮播放+🌐内嵌 iframe 完整播放页
  - **legado-E 跨版本兼容修复实战**（v3.1）：发现列表“列表大小15但字段全空”+目录获取失败根因
- **技术要点**:
  - ★E 版 getString 对 @js: 列表条目只做键值直取 → chapterList/bookList 返回 **JSON 字符串数组**+纯键名规则 $.name/$.url
  - ★iframe 内嵌完整网页 = 真·内置浏览器（站点无 X-Frame-Options 时），比 startBrowser 更无缝
  - ★🌐章节方案：目录造虚拟章节（#browser fragment 保 URL 唯一）→ ruleContent 规则上下文调 java.startBrowser（两版可用），失败 openUrl 兜底
  - 按钮点击时 fetch 重抓详情页解析最新 m3u8，烘焙直链回退
  - baseUrl fragment 污染清洗（chapterList/intro 统一 split('#')[0]）
- **适用场景**: 学习 useweb 页面编程 / iframe 内嵌方案 / legado-E 与 LegadoTeam 双版本兼容 / 视频站书源

相关方法论文档：[references/方法-简介useweb内嵌页面与浏览器调起.md](../references/方法-简介useweb内嵌页面与浏览器调起.md)

### 9. 起点 TTS 朗读引擎（HttpTTS 在线朗读引擎 · 音色切换面板）
- **文件**: [起点TTS_朗读引擎6个.json](./起点TTS_朗读引擎6个.json) + [起点TTS朗读引擎_103.236.85.8.md](./起点TTS朗读引擎_103.236.85.8.md)
- **类型**: 在线朗读引擎（HttpTTS，**非书源**，导入位置=朗读引擎）
- **特点**:
  - 服务 = FastAPI「起点 TTS 控制台」（IFly + Minimax 双引擎，TTS 专用 `/legado/{provider}` 入口）
  - 6 个引擎：主引擎「起点TTS·音色切换」（登录界面带 5 音色按钮 + 连通测试 + 清语音缓存 + 语速映射）+ 5 个单音色引擎（朗读菜单 2 步切换）
  - 音色：ifly 4001 关山 / 4002 筱潇 / 4003 聆小琪、minimax 6001 说书先生 / 6002 狐狸小姐（5 个音频 md5 全不同）
- **技术要点**:
  - ★给朗读引擎加按钮的唯一官方通道：编辑朗读引擎 → ⋮ 菜单 →「登录」→ SourceLoginDialog 渲染 loginUi（RowUi）按钮
  - ★url 用 `<js>` 整段 + `JSON.stringify(bd)` 拼 body —— 正文含英文引号/反斜杠/换行不会破坏 URL 选项 JSON（否则静默退化成 GET → 朗读无声且零报错）
  - ★音色/语速模式存 `source.put/get`（BaseSource→CacheManager），规则内兜底默认值 → 刚导入不点按钮也能朗读
  - ★`viewName` 不带引号包裹时当 JS 表达式求值 → 「ℹ️ 当前音色：关山（ifly 4001）」动态按钮文字
  - ★语速映射：Legado `speakSpeed=设置语速+5`、界面显示=speakSpeed/10（默认 1.0，滑杆 max45），对齐站点 0-100/默认 50 → `clamp(speakSpeed*5,0,100)`
  - `loginCheckJs` 拦 <800 字节的 detail/html 响应并 throw 中文报错（服务端 4xx 会被当音频播放成"无声"）
- **实测**: App 内 test_tts 同文本 5 音色字节 15120/14688/14688/33006/33006，与沙盒 md5 表一一对应；含引号反斜杠压力文本 39312B/963ms
- **适用场景**: 学习在线朗读引擎制作 / TTS 音色切换面板 / 语速映射对齐 / BaseSource 变量持久化 / loginUi 按钮面板编程

相关方法论文档：[references/方法-HttpTTS朗读引擎与音色切换面板.md](../references/方法-HttpTTS朗读引擎与音色切换面板.md)


### 10. hanime1 视频书源 v2.0（登录UI V2 首个生产案例）

- 站点：`https://hanime1.me`（视频源,CF托管+视频CDN被墙）
- 文件：`examples/hanime1视频_www.hanime1.me.json`
- 亮点：**登录UI V2(`loginUi={"version":2}`)**——域名/hosts下拉选择、测速选线、代理开关(header动态注入proxy键解决视频CDN被墙)、已登录时/login返回404的陷阱识别、登录令牌meta/input双通道
- 对应方法论：references/方法-登录UI-V2新版面板.md


### 11. hanime1 视频书源 v3.9（视频源标杆案例 · 全链路）

- 站点：`https://hanime1.me` / `hanime1.com`（Laravel SSR + Cloudflare + CDN77 媒体域，成人向 MMD/3D 动漫）
- 文件：`examples/hanime1_视频书源_案例.md` + 成品 `examples/hanime1_视频书源_v39.json`（89739B，md5 `62eef4b3…94de`，check_source 1/1）
- 类型：`bookSourceType=4`（视频），一集(P)一行、正文输出**带时效签名的 mp4 直链**（约 10 分钟过期）
- 亮点：
  - ★`dnsIp` 多 IP failover + `{{}}` 每次请求二次求值 ⇒ 换线路后书架旧 URL 全部自愈
  - ★CDN **原生主机名替换**绕 SNI 封锁（`vdownload.hembed.com` → `1497203185.rsc.cdn77.org`，签名只绑路径）
  - ★`<useweb>` 活视图面板 + `ruleContent.callBackJs`(`eventListener=true`) ⇒ **播放切集，简介/封面/收藏态实时跟随**
  - ★面板零网络快绘（同步桥会冻结 WebView JS 线程）+ 封面 `data:` 内置（`blockNetworkImage` 真相）
  - ★登录态判据避开 `_token`（匿名也下发）+ 跨镜像域 Cookie 同步；控制台 38 行（域名/hosts/代理/清晰度/CDN/封面模式）
- 对应方法论：`references/方法-视频书源完全指南.md`（主）、`方法-详情页交互按钮选型树.md`、`方法-登录UI-V2新版面板.md`、`方法-URL模板与DNS选线.md`、`方法-图片不显示排查总表.md`

### 12. iwara 视频书源 v13（「打开作者全部作品」合集书）

- 站点：`https://api.iwara.tv`（纯 JSON API + Cloudflare，MMD/3DCG 动画站）
- 文件：`examples/iwara_按作者列作品_案例.md` + 成品 `examples/iwara_A_v13_author.json`（103792B，md5 `c991e8b9…4e6d3`，check_source 2/2）
- 亮点：
  - ★**头号陷阱**：`?userid=<UUID>` 返回**正确的 count 却把 results 换成站内热门**（不报错）→ 必须做**归属校验** `results[].user.id === 请求uid`
  - ★**破局第一优先=查 GitHub 开源实现**：yt-dlp `IwaraUserIE` 揭示正确形态 **`/videos?user=<UUID>`**（参数名叫 user 但值是 **UUID 不是用户名**）
  - ★**书籍URL直接就是可用 API 地址**（用 `/user/{uuid}` 这类非真实端点会 404，在 `init` 之前就失败）
  - ★`nextTocUrl` **只返回 1 个 URL** → 走 `while` 串行 → 顺序天然保证（0个=停/1个=串行/多个=并发乱序）
  - 上下文（uid/un/pg）注入进 init 返回的 JSON，**不用全局变量**（请求间串数据）
  - 作者响应的 `user` 在 `results[].user` **不在顶层** → 不兜底则**作者行整行不渲染**
- 对应方法论：`references/方法-按作者列作品-API参数逆向.md`

### hanime1.me 视频书源 · legado-E 兼容版

- [案例说明](hanime1_E兼容版_www.hanime1.me.md)
- 成品：`hanime1_E兼容版_www.hanime1.me.json`
- 要点：E 版无 V2 登录面板 / 无 callBackJs / 无 useweb / 无 video 类型 / 无 dnsIp
  → V1 面板 37 行 + 列表字段纯键名 + 简介降级纯文本 + 代理通道；`##E兼容版` 独立源不覆盖原源

### hanime1.me 视频书源 · legado-E 兼容版（v3.14E）

- [案例说明](hanime1_E兼容版_www.hanime1.me.md)
- 成品：`hanime1_E兼容版_www.hanime1.me.json`
- 要点：E 版只认**数组** loginUi（`{"version":2}` → 面板空白）+ 列表字段必须**纯键名**
  → 数组面板 43 行（含**一键选域名按钮** ①~④ + 查看当前配置）+ `H1CARDS` 预生成 `u/cover/kind`；
  **简介保持原版 useweb 面板未降级**；`##E兼容版` 独立源不覆盖原源。
- ★ 附送教训：**拉 E 版源码必须先确认默认分支**（`main` 不是 `master`，否则误判 useweb/video/dnsIp 等 8 项能力）

### 13. rrssk聚合 44域名多站聚合（状态漂移修复 + 选站三件套）

- 源：`rrssk聚合`（44 域名 / 14 套发现模板 / 双体系 rrssk家族+菠萝猫）
- 文件：`examples/rrssk聚合_44域名多站聚合.md` + 成品 `examples/rrssk聚合_44域名.json`（52532B，md5 `47b3976311e9286667f78f41b238f3a0`，check_source 1/1×3）
- 亮点：
  - ★**书架书正文为空根因**：全局 server 漂移（停在 boluomao 死站）→ 正文走 data-obf 分支取空；用户恢复手法=手动拨回 server
  - ★**URL 自治五层**：`SRV` 推导域名 / 章节绝对 URL + `chapterUrl=$.chapterurl` / `dataEncrypt` 显式键 / **别名书 data-aid 实际值自纠**（hggjfg→hgg）/ toc 取值链
  - ★**选站三件套**：登录面板 `<js>` 运行时生成 47 行 + 下拉 SET **移进 action**（防过期 live InfoMap 覆盖）+ 下拉下方**状态栏**读 server 真值
  - ★**check_source 三坑 + 模板引擎四铁律**（`{{}}` 无括号=属性路径 / Java 空串 truthy / evalJS 单参调不到 / 哨兵改 `!GET(key)`）
- 对应方法论：`references/方法-聚合源状态漂移修复与选站面板-rrssk.md`、`references/聚合源多域名架构设计.md`


### 14. 禁漫天堂Pro（小说/漫画/视频三合一书源）
- 方法论：[references/方法-小说漫画视频三合一书源详解.md](../references/方法-小说漫画视频三合一书源详解.md)
- 成品：[禁漫天堂Pro_三合一.json](禁漫天堂Pro_三合一.json) · [案例说明](禁漫天堂Pro_三合一.md)
- 要点：发现页下拉切三形态、#/! 前缀分搜索、统一 jmParseList、book.type 动态设置、useweb 收藏面板三态+重复收藏识别、kind 头部作者芯片搜索、发布页测速选线、K1~K14 避坑

### 15. 69书吧（AEGIS/ALTCHA PoW 首例 · WebView 通道书源）
- 方法论：[references/方法-AEGIS-ALTCHA验证与WebView通道书源.md](../references/方法-AEGIS-ALTCHA验证与WebView通道书源.md)
- 成品：[69书吧_www.69shuba.tw.json](69书吧_www.69shuba.tw.json) · [案例说明](69书吧_www.69shuba.tw.md)
- 要点：32hex keyPrefix=deny挑战判活铁律、java.webView 真浏览器通道 + loginCheckJs 整体替换响应、Cookie 跨栈不升级实锤、目录链接 JS 水合需渲染 DOM、ruleContent 字段名是 content、K1~K8 避坑
### 16. 次元姬小说（App官方API · 设备号风控 + 发现页排布终极案例）
- 方法论：[references/方法-App官方API书源与设备号风控-次元姬.md](../references/方法-App官方API书源与设备号风控-次元姬.md)
- 成品：[次元姬小说_api.hwnovel.com.json](次元姬小说_api.hwnovel.com.json) · [案例说明](次元姬小说_api.hwnovel.com.md)
- 要点：设备号服务端设备库风控（新16hex→`400网络繁忙`，共享已验证号+登录面板可改）；DES-ECB+MD5四件套签名（timestamp必须数字、签名无时间窗→永久签名URL）；VIP code=101免费预览；★★发现页固定basis列数必被divider挤成竖排→`layout_flexGrow:1`自动流式布局；签到提示走loginCheckJs；crates.io拆包逆向挖全套端点密钥

- ACFAN(禁漫)动漫·漫画·视频_www.acfan.com [JSON](ACFAN禁漫_www.acfan.com.json) · [案例说明](ACFAN禁漫_www.acfan.com.md)
- 要点：★★**切片签名头**（站点2026-10升级新增`t`+`s`=md5(t[3:8])，缺头=HTTP200+content-length:0静默失败，四组对照实验定位）+**响应encData/明文双兼容**（同一接口匿名明文/登录密文，key=iv=token[2:18]）+**敏感接口5头签名**（bodySha=键名升序紧凑JSON）；★★**文本混淆头**（txt=101字节头+UTF-8正文，扫首个合法UTF-8中文去头）+**媒体多域**（playPath域403→mp4Domain+fictionUrl才是真地址）；★★**有声book.type=32强制**（否则调起视频播放器）+**hls.js页SRC引号成对**（漏+Q+→SyntaxError静默失效）+CDN递归兜底；★★**发现页五分区select**（精选18站/视频/漫画/文字小说18标签/有声小说16标签，`tagIds`数组参数+tagType双体系+AND交集）+**flexGrow自动流式排布**（固定basis被divider挤成竖排）


### 17. QQ阅读(纯本地)（正版 App 协议逆向 · 本地缓存型书源）

- 案例说明：[QQ阅读_纯本地_book.qq.com.md](QQ阅读_纯本地_book.qq.com.md)
- 配套方法论：[方法-正版App协议逆向与本地缓存书源-QQ阅读.md](../references/方法-正版App协议逆向与本地缓存书源-QQ阅读.md)
- 规模：**jsLib 396KB / loginUrl 76KB（145 个顶层函数）/ 全部规则为 `@js:`** —— 目前技能库中体积最大的书源，20 个基础字段 + 5 个规则对象
- 要点：★★★**官方 `{"type":"hex"}` URL 选项**（`AnalyzeUrl.kt:461` 源码实锤，把二进制响应以 hex 字符串送进规则，加密 API 站的入场券；三条硬约束：末尾英文逗号/不能同 URL 又要 hex 又要文本/长度恒为字节×2 可自校验）；★★**自实现完整密码学栈**（SHA256/AES-256-CBC/CTR/DES/CRC32/MD4/自定义哈希/Inflate）+**原生 Java 与纯 JS 双实现互备**（`Cipher.getInstance` 调用即验证可用性，原生 1.7ms vs JS 数十 ms）；★★**响应头部指纹校验**（`peekId` 读密文头数字串比对上次成功值，防密钥池漂移时「解出垃圾当正文」）+**gzip 魔数双保险**；★★**试读/全文双态缓存**（`{"t":...,"p":1}` 标记，购买后主动丢弃）+**服务端拒绝包显式识别**（tar 内 `info.txt` code 负数 ⇒ 抛错，绝不返回可疑文本）；★★**tar 容器一次拉 8 章只解密当前章**（`scids=100-107` 区间语法 + 其余存密文）+ 三易错点（size 八进制/数据区 512 对齐/结束标志首字节 0）；★★**网络失败兜底本地缓存**（`new StrResponse('http://localhost/', b)` 伪造响应实现离线可读）；★**设备指纹 43 字段表**（`mldt`/`sift` 都以 `dn` 结尾⇒交叉校验不可单改）+**设备被限专用码 code=3/-11059 ⇒ 重生成指纹而非换 IP**；★**自管鉴权标准姿势**（`removeLoginHeader()` 主动清除，绝不让两套头并存）；★**段落级评论气泡注入** + **自动购买三护栏**（按书白名单/软硬冷却/全订月票章跳过）+ **searchUrl 关键词特判触发自检**（`fockselftest`/`shelfdiag`/`qfbench`）；K1~K22 避坑 + 移植清单三档 + 分层验证法

### 18. STV 越南聚合（sangtacviet.vip · 分隔符型目录解析修复）

- 案例说明：[STV越南聚合_sangtacviet.vip.md](STV越南聚合_sangtacviet.vip.md)
- 成品书源：[STV越南聚合_sangtacviet.vip.json](STV越南聚合_sangtacviet.vip.json)（v11.11，152 404 B）
- 配套方法论：[方法-抓包驱动的官方App行为对齐-STV篇.md](../references/方法-抓包驱动的官方App行为对齐-STV篇.md) §12
- 规模：jsLib 约 47KB / 规则全 `@js:` / 单源聚合 12+ 镜像域 / 10+ 来源站换源
- 要点：★★★**「不是章节缺失，是标记缺失」—— 平铺扫描解析器遇到「标题含分隔符」就散架**。站点目录数据格式是 `-//-` 分记录、`-/-` 分字段（`[序号, 章节ID, 标题, 状态?]`，状态取 `unvip` 已解锁🔑 / `vip` 未解锁🔒 / 缺省免费）；旧 `pseg()` 是 v9.x 遗留的**平铺扫描**（把整份数据 `split('/')` 切开再靠「前后邻槽是不是数字」猜字段），**只有标题不含 `/` 时才碰巧正确**。faloo/770959 实测 5551 章里 **4384 章标题含 `/`**（`h073 vòng bằng hữu quan tuyên?2/30`），被切碎后：🔑 应 5460 实显 **1081**（丢 4379）、标题截断 4384 个、中间碎片 9939 条、连带 `n=` 参数写成 9939。**修复**=`split('-//-')` 分记录 + `split('-/-')` 分字段 + 标题含 `-/-` 时回粘 + `psegFlat()` 回退，三处同步替换（`ruleToc.chapterList` / `ruleContent.content` / `ruleBookInfo.init`）。
- ★★**验证方法论**：① **服务端自带计数 = 免费真值**（响应顶层 `unvip: 5460`，修复后 🔑 数量必须精确等于它）；② **跨来源样本矩阵（必须）**——抓 10 个来源同类接口：faloo 暴露 bug、ptwxz 暴露旧版自身缺陷（1 章被拆成 2 条→正确合并）、其余 8 个逐字节一致（**单样本 = 赌博**）；③ 真实规则 × 真实抓包数据离线仿真；④ 真机 Rhino `eval_js` 复跑（node 通过 ≠ Rhino 通过）。
- ★**通用结论**：「恰好通过」的解析器最危险（9/10 样本正常，第 10 个暴露）；**写解析器前先问「数据格式有没有正式的分隔符」，有就用它，别猜**；自由文本字段（标题/作者/简介）是分隔符的天然污染源。

### 19. 红果短剧（网页版）（SSR 内联 JSON · 括号配平提取）

- 成品：[红果短剧_www.hongguoduanju.com.json](红果短剧_www.hongguoduanju.com.json) · [案例说明](红果短剧_www.hongguoduanju.com.md)
- 配套方法论：[方法-SSR内联JSON书源的括号配平提取.md](../references/方法-SSR内联JSON书源的括号配平提取.md)
- 规模：单文件 14435 B / jsLib 7141 字符 / 全部规则 `@js:` + IIFE
- 要点：★★★**括号配平状态机取内联 JSON**（Modern.js 的 `_ROUTER_DATA`，贪婪正则吃尾、非贪婪在内层 `}` 截断、`lastIndexOf` 会吃到后续 JSON；必须处理字符串状态 + 转义 + 单引号三态）；★★**`loaderData` 键名随路由变化**（`detail_page` / `player_(series_id)/(vid)/page` / `search_(keyword)/page` / `category_$` / `rank_hot-drama/page`）→ 必须按特征字段名遍历而非写死 key；★★**`key`/`page` 在 bookList 上下文不存在**（`AnalyzeRule.kt:896-914` bindings 全表无 key，`BookList.kt` 从不 `setLocal`）→ searchUrl 携带自造参数 `?hgk={{java.encodeURI(key)}}` + 规则内从 baseUrl 反解；★★**`@js:` 顶层禁止 return**（Rhino `compileString` 报「返回的值无效」）→ 一律 IIFE；★★**`tocUrl = bookUrl` 零请求目录**（`BookInfo.kt:157-161` + `WebBook.kt:312` 源码级复用 `tocHtml`）；★**多形态站点在 chapterList 里 `book.setType()`**（`WebBook.kt:306` 的 `removeAllBookType()` 会冲掉详情页设的 type）；★**网页版硬限制如实标注**（红果每部剧仅前 3 集可播，9 种绕过方案全失败 = 服务端策略）；★播放直链 mp4 免防盗链但带 15 分钟时效签名 → 每次实时解析不缓存；★零双引号零反斜杠纪律 + `md5` 比较必须 `String()` 包裹

### 20. 红果短剧（网页版）· 官方 App 接口签名门槛调研

- 案例说明：[红果短剧_www.hongguoduanju.com.md](红果短剧_www.hongguoduanju.com.md)
- 配套方法论：[方法-字节系官方App接口签名门槛与降级.md](../references/方法-字节系官方App接口签名门槛与降级.md)
- 要点：★★★**判断"能否突破"的决策树**（404→找其它入口 / 静默降级→加客户端校验 / 有官方App→查接口签名方式 / native so→书源侧不可行 / 全不可行→降级交付）；★★**字节系签名门槛实测**：`api5-normal-sinfonlineb.fqnovel.com`（红果 aid=**8662**，非番茄的 1967），`multi_video_detail/v1/`+`multi_video_model/v1/` 必签（**`{"Code":110001}` 是签名失败码，不是参数错误**），`bookmall/cell/change/v` 免签可用；★★**桌面版为什么能看全集**：内置 `unidbg-sign.jar`（`com.hongguo.sign.FqTrace serve 0`）用 unidbg 模拟 Android so 库生成 X-Argus —— **架构不匹配，书源侧无法实现**；★★**线索链方法论**：发布仓库的 **PR/Issue 暴露架构级信息**（`desktop_bootstrap.patch` 一眼看出 unidbg）+ 同族项目调研（`N3urda/hongguoTV` 的接口研究文档给出完整路径表）；★★**服务端静默降级**：红果漫画忽略 `vid` 参数恒返回第 1 话（`next_vid` 循环指向自己）→ **必须加参数-响应一致性校验**；★降级交付三原则（如实标注/明确提示/不伪造）+ `#fragment` 伪 URL 技巧（不发请求、天然唯一）+ 三段式提示文案

### 21. 红果短剧 API 版（纯 JS 复现字节跳动 X-Argus 签名 · 突破全集限制）★ 里程碑

- 成品：[红果短剧API版.json](红果短剧API版.json)（23843 B，`check_source` 通过 1/1）· [案例说明](红果短剧_www.hongguoduanju.com.md)
- 配套方法论：[方法-字节跳动X-Argus签名纯JS复现与红果短剧API书源.md](../references/方法-字节跳动X-Argus签名纯JS复现与红果短剧API书源.md)
- 规模：jsLib 18877 B / 全部规则 `@js:` + IIFE / 8 个功能函数
- 要点：★★★**X-Argus / X-Gorgon / X-Ladon 三件套纯 JS 复现** —— 社区普遍认为必须 unidbg 模拟 so 库（桌面版 `hongguo-desktop-releases` 就依赖 `unidbg-sign.jar` 常驻），实则只是 **SIMON-128 分组密码 + SM3 哈希 + AES-CBC 外壳 + protobuf 手工编码**，全部可在 Rhino 内跑通，**无需外部签名服务**（继纸间 zjread.cc 之后「客户端能算的，书源都能算」的又一实证）；★★★**BouncyCastle SM3 在 Legado 可用**（`Packages.org.bouncycastle.jcajce.provider.digest.SM3` 是 class，必须 `new SM3.Digest()`；标准 `MessageDigest.getInstance("SM3")` 抛 NoSuchAlgorithmException；实测 `SM3("abc")` 与标准值逐字节一致）；★★★**byte[] 互转的唯一可靠姿势**（`Packages.java.lang.reflect.Array.newInstance(Byte.TYPE, n)` 在 Rhino **不可用** ⇒ 借道 `String` + `ISO-8859-1` 编码往返，单字节映射 0x00-0xFF 无损）；★★★**jsLib 里 `java.ajax` 是 object 不是 function**（老坑第 N 次复现）⇒ 所有联网函数把 `java`/`source` **作为参数显式传入**（`HG_API(JV, path, body, extra)`）；★★★**列表规则必须返回 JS 数组**（LT 版 `getElements` 对 `Mode.Js` 只接受 List/Array/NativeArray，返回 String 直接得空列表）⇒ 数组元素各自 `JSON.stringify` + 字段规则用 `$.name` 纯键名（LT/E 双版本通用）；★★★**签名失败与参数错误的严格区分**（`code:101000` + `debug_info:"pack ret empty"` = 签名不过；`code:100001` + `"video platform invalid, param:0"` = 签名已过、业务参数缺失）；★★**红果接口全档案**（分集详情 `POST /novel/player/multi_video_detail/v1/`；播放地址 `POST /novel/player/multi_video_model/preload/v1` **必须带 `biz_param.video_platform:1024`** + `mixed_video_id_map:{'1004':[vid]}`，`video_model` 是 **JSON 字符串需二次 parse**，返回 5 档 360p~1080p 明文 MP4、`url_expire` 约 3 小时；搜索与发现走网页版 `/search/{kw}` 的 `"searchList":[...]` 与 `/rank/hot-*`、`/category/*` 的 HTML）；★★**「参数容器 URL」模式**（书籍 URL 写成 `/detail?series_id=xxx` 这类**永不被请求**的容器，规则 `@js:` 内反解参数）；★**网页版 vs API 版能力对比**（网页版仅前 3 集且第 4 集 404，API 版全集 + 5 档清晰度 + 明文 MP4 无 DRM）；★**分层验证法**（密码学原语 → 签名生成 → **签名有效性（真实调 API 看 code）** → 业务接口 → 播放地址 → 直链可播 → 全链路 debug → `check_source` → 逐字段 md5）；★**MCP 长参数不稳定**（`eval_js` 传 >10KB 报「参数 js 不能为空」，长脚本一律走 dpaste + 深链 + debug_source）

---

### 20. 番茄漫画（fqapp 逆向 / 混合类型自动判型）

- 书源文件：[番茄漫画_www.fanqienovel.com.json](番茄漫画_www.fanqienovel.com.json)
- 配套方法论：[方法-番茄漫画书源与混合类型自动判型](../references/方法-番茄漫画书源与混合类型自动判型.md)
- 规模：jsLib 34896 B / 全部规则 `@js:` + IIFE / 14 个功能函数 / check_source 通过 1/1（发现页经实测确认番茄漫画**无任何可用分类接口**，只保留 1 个真实入口，详见方法文档第 11 章）
- 要点：★★★**「图片加密」是假象，先验魔数再写解密**——按 fqapp 源码 `manga.rs` 的 `encrypt_key + picInfos + AES-256-GCM` 假设绕了很久，`AEADBadTagException` 调不对；真相是 `java.ajax` 默认 UTF-8 解码把二进制搞坏，用 `{"type":"hex"}` 一看魔数 `ffd8ffdb`（标准 JPEG），**图片根本没加密**；★★★**漫画链路**（`reader/full/v` 与 `search/tab/v` 均已废弃返回 Invalid/空 ⇒ 改走 CM DH 通道 `novelfm-hl/playerapi/full/mget/v1`，HTML 内嵌 `materials`+`skeleton`，`&` 是 `&#34;` 实体须先 `unescapeEntities`，**图序必须按 skeleton 的 elementInfo 而非 Object.keys**，图片域 `p3/p6-novel.byteimg.com/origin/{web_uri}`）；★★★**混合类型自动判型**（fanqiesdk 搜索返回全站混合结果无法过滤 ⇒ 用 `book_info.comic_book_type`（漫画专有、小说为 `undefined`）判型，漫画出 `<img>`、小说出文本，**漫画通路必须是安静版函数**否则 `throw` 永远走不到小说分支）；★★**Rhino 中文必须用 UTF-8 字面量**（`String.fromCharCode(高位码点)` 经 `throw new Error()` 后变成「没格为章埋获」这类乱码）；★★**同站点多源共存用 `##` 后缀**（`bookSourceUrl=https://fanqienovel.com##漫画版` 与小说源并存互不覆盖，但 `##` URL 不能当详情入口请求）；★★**jsLib 里 `java.*` 必须作参数显式传入**（老坑第 N 次复现）
- 关联案例：番茄小说（APP 接口版，见 `method-正版App协议逆向与本地缓存书源-QQ阅读` 同族签名栈）

### 22. 花都动漫（hd.huadudm.com · 飞飞CMS 影视站 · player_data 解密）

- 成品：[花都动漫_hd.huadudm.com.json](花都动漫_hd.huadudm.com.json)（18174 B / v1.6，`check_source` 通过 1/1）· [案例说明](花都动漫_hd.huadudm.com.md)
- ★**v1.6 修复「发现列表只显示一页」**：站点 p1/p2/p3 各 40 条零重复（排除站点），`{{page}}` 替换正常（排除规则）；真因是 App `upData()` 里 `adapter.itemCount == books.size` 就 `noMore()`，**任一页没新增书即永久停翻页**。三处加固：页码归一化（`Number(page)`+`>0`，否则 URL 出现字面量 `null` → 站点 7157B 空壳）、URL 追加 `{"timeout":20000,"retry":2}`、空页分流（`第X/Y页` 里 `cur>=tot` 才是真到底，否则抛错弹重试）。另加「翻页自检」按钮读 `hgpg` 变量。详见 `references/方法-发现页只显示一页的排查与加固.md`
- 配套方法论：
  - [方法-飞飞CMS影视站视频书源制作.md](../references/方法-飞飞CMS影视站视频书源制作.md)
  - [方法-CDN短时频控与假UA敏感误判.md](../references/方法-CDN短时频控与假UA敏感误判.md)
- 规模：单文件 14193 B / 无 jsLib / 5 个 `@js:` 规则 / 25 字段
- 要点：
  - ★★★**「带某 header 就 404、去掉就 200」几乎不是 UA 敏感，而是短时频控**（本次最大教训）。用**基线穿插法**（A/B/A/B 交替）才能证伪：如果"无头基线"在第 5 次也挂，就是时间维度的频控。我差点据此写下"CDN 拒绝一切显式请求头、必须留空 header"的错误结论，并把它实现进规则。判据：**同一 (URL, header) 在不同时刻结果不同 = 时间维度问题**。正确做法是用 `concurrentRate` 节流，而不是阉割 header。
  - ★★**飞飞CMS 高度模板化**：认准 `var feifeicms=` / `ffcms_wd` / `ul.stui-vodlist` / `player_data` 四特征，一套规则可横扫几十个同模板站（改 4 个常量即可移植）。
  - ★★**分页连字符段数不同**：`vodshow` 是 12 段（`type-area-lang-year-letter-state-money-page-order`），`vodsearch` 是 10 段。别凭感觉数，**直接抄站点自己生成的分页 href**。
  - ★★**详情字段是 `div.detail-item` 键值对**（站点不用 `og:` meta），必须**按标签名取值**而非索引——不同书之间字段数量会变（有的没"类别"、有的没"时长"）。
  - ★★**列表页有多个 `ul.stui-vodlist`**（详情页更会混入"猜你喜欢"）→ 取 **li 数量最多**的那个，一套解析器同时服务搜索与发现。
  - ★★**目录必须按 `bookUrl` 里的 id 过滤** `a[href*=vodplay]`，否则"猜你喜欢"里其他书的链接会被当成章节。
  - ★★**正文解密**：`player_data.encrypt=2` → `base64Decode` → **多层 `decodeURIComponent` 必须循环到稳定**（层数不固定）→ 末尾 `indexOf('http')===0` 校验，防把垃圾当直链。
  - ★**`tocUrl` 返回空串** → Legado 复用详情页 HTML，目录零额外请求（`BookInfo.kt:157`）。
  - ★**每作品固定 1 个视频**（标题写"第18-50集"的也是单个长视频）——目录只显示 1 章是**正确行为**，不是规则缺陷，已在 comment 里写明以免后续维护者误判。
  - ★**WebView 实播验证**：`java.webView` 注入 `<video src=m3u8>` 探针，实测 `{rs:4, dur:3306, w:1280, h:720, err:0}` —— 证明直链可直接播放，而不只是"规则能解出 URL"。
  - ★**裸 IIFE 必须加 `@js:` 前缀**（老坑复现：不加会被当 CSS 选择器抛 `SelectorParseException`），构建脚本已加闸门强制校验 5 个规则字段的前缀。
  - ★★★**发现页分页槽位 bug（v1.4→v1.5）**：把 `{{page}}` 拼在 `.html` **后面**，生成 `/vodshow/1--hits---------.html1`。**站点对畸形 URL 返回 200 + 完整正常页面**（内容是第 1 页）⇒ `debug_source` 全绿、`check_source` 通过 1/1，但**翻页永远停在第 1 页**。是靠 `get_http_logs` 看到 `GET .../html1 -> 200` 才发现的。正解=**从站点真实分页 href 反推段位**（`vodshow` 12 段，页码在 index 8），验证三件套：① `pgUrl()` 输出必须与站点 href 逐字符相等 ② 第 2 页首条 ≠ 第 1 页（`仙子的修行4下` vs `慕名雪的私人拍摄`）③ `page=1` 与站点省略页码段形式返回同页。**通用教训：`check_source` 通过 ≠ 分页正确，分页必须单独验证。**

### 23. 八叉书库（8xsk.cc · 线路自愈反代源 · 书源自助运维面板）

- 书源文件：[八叉书库_ip-ddns反代源.json](八叉书库_ip-ddns反代源.json)（99550 B / v7.1，`check_source` 通过）
- 案例说明：[八叉书库_ip-ddns反代源.md](八叉书库_ip-ddns反代源.md)
- 配套方法论：
  - [方法-线路自愈与登录面板运维套件](../references/方法-线路自愈与登录面板运维套件.md)
  - [方法-书源自助运维面板与站点特色功能拆解](../references/方法-书源自助运维面板与站点特色功能拆解.md)
- 规模：99550 B / jsLib 15253 字符 / 登录面板 35 按钮 / 19 个 jsLib 功能函数
- 要点：
  - ★★★**多域名线路自愈**（5 备用域名 + 发布页取址）：登录界面线路按钮 → `source.putLoginInfo({'网址':u})` → `getsurl()` 单点读取。铁律：**除 `getsurl()` 内部，任何规则不许直接读 `source.get('网址')`**（破例必漏改 →「部分功能能用」）。探活三判据（长度下限+反例关键词+正例关键词），**不能只看 HTTP 200**（劫持页/年龄闸门/维护页全是 200）；只对 `BX_DEAD` 探活，测速排序取 `ok[0]`。
  - ★★★**发布页取址用纯 HTTP**：`webView:true` 抓发布页 8xsk.org 被网络环境阻断超时 60s，纯 HTTP `java.connect` 406ms 拿 7 站点——**WebView 与书源 OkHttp 是两套网络栈**，不能拿 WebView 失败断言站点不可达。
  - ★★★**书架双向同步**（网站→Legado）：深链批量 `legado://import/addToBookshelf?src=...` **必须 `sleep(700)`**（否则 7 本只进 2~3 本）+ `,{"origin":"{bookSourceUrl}"}` 防抢 + **书架 id 是 `aid` 不是 `bid`** + 手机 c_row 模板字段映射 + `readbookcase.php?bid=&aid=&cid=` 转详情 `getsurl()+'/book/'+aid+'.html'`。
  - ★★★**SVG 验证码当输入框**：`java.getVerificationCode('data:image/svg+xml;base64,'+svg)` 语义是「显示一张图让用户输入」⇒ 图里画操作说明、用户输命令，**零新增 UI**，可移植到任何需要文本输入的书源。
  - ★★**exploreUrl {{}} 模板的三元+逗号陷阱**（v7.1 书架失效根因）：`cond ? urlA : toast(),'dataURI'` 是逗号表达式，**求值恒为最后的 data URI**，urlA 被静默丢弃 → 有副作用的兜底必须括号包裹 `(toast(),'dataURI')`。
  - ★★**年龄闸门 Cookie**：固定带 `age18_ok=1`；`cookie.setCookie` **整体替换语义**会把它冲掉（合并 Cookie 只合并不替换）。
  - ★★**putLoginHeader 必须传 JSON**：纯 Cookie 串被 `getHeaderMap(true)` 静默丢弃 →「登录成功但 VIP 章读不了」；配套 `ckget(so)` 兼容函数。
  - ★★**VIP 章节三态**：目录里 VIP 章 URL 是 `/modules/obook/reader.php`（非 /read/），正文规则自动改走 obook 入口；未订阅显示预览+订阅指引。
  - ★★**阅读预下载与批量下载分流**（v7）：下载时 `book.durChapterIndex` 不动、`chapter.index` 是目标章 → 阅读限速/随机延迟对下载是纯浪费（40~61s/章）甚至空正文；`dn==1` 全跳过后 0.9~1.5s/章。另有 `cache.getFromMemory` 返回 Java 包装对象字符串拼接死循环，`Number()` 归一修复。
  - ★**购买成功分支也要走解密**（v6）：购买返回的正文页同样加密，直接赋值让阅读器拿密文显示空 → 解密封装 `decContent()` 三路共用。
  - ★**黑名单落地**=`name` 规则返回 `''`（`BookList.getSearchItem` 的 `name.isBlank() → return null` 过滤口）；★**SVG 现场生成封面**（7 字切行 tspan 竖排，data URI 当 coverUrl 永不 404）；★**版本更新检查**（gitee commits 当版本号源）；★**重置保留用户资产**。

### 24. 蕃茄小说（m.dzrjk.com · 搜索签名伪装成空结果）
- **文件**: [蕃茄小说_m.dzrjk.com.json](./蕃茄小说_m.dzrjk.com.json) ｜ [详细拆解](./蕃茄小说_m.dzrjk.com.md)
- **类型**: 小说网站（服务端渲染 HTML + JSON 搜索 API）
- **状态**: `check_source` 通过 1/1，全链路实测（搜索/详情/目录/正文/发现）通过
- **核心难点**:
  - 搜索接口 `/api/search` 需 POST **31 个混淆校验变量 + sign**，值每次随机，必须从 `/user/search.html?q=` 页面正则抓取
  - ★ **`bgt` 必须截断末位**：站点 `search_before()` 里 `if (document.cookie != "") bgt = bgt.slice(0, len-1)`，浏览器必带 SID cookie，故真实请求的 bgt 永远截断
  - ★ **校验失败不报错**：返回 `{"code":0,"data":{"search":[]}}` 伪装成"无结果"，曾误判为接口失效 2 小时
  - IP 级 3 秒限频；`concurrentRate` 单位是**毫秒**，须写 `1/2000`
  - 分类页 URL 数字**不是页码**（1/2/100 内容相同），每个分类固定 30 本
  - 目录单页全量（实测 5461 章），无需 `nextTocUrl`
- **沉淀文档**: [方法-搜索签名失败伪装成空结果](../references/方法-搜索签名失败伪装成空结果.md)

### 25. 黄果短剧（Flutter Dart AOT 站点 · 三容器单源整合 · E 版兼容登录面板）
- **文件**: [黄果短剧_www.huangguoai.cc.json](./黄果短剧_www.huangguoai.cc.json) ｜ [案例说明](黄果短剧_案例说明.md)
- **类型**: 视频书源（`bookSourceType=4`），站点为 Flutter Dart AOT 客户端 + 服务端渲染 Web
- **状态**: `check_source` 通过 1/1；发现页 7 项（4 分类 + 排行榜 + 精品专题 + 全部专题）+ 搜索全链路实测通过；封面已修复
- **核心难点**:
  - ★★★**封面解密钩子返回值必须是 Java `byte[]`**：源码 `RhinoScriptEngine.kt:235` `unwrapReturnValue` 只 unwrap `Wrapper` —— `Packages.java.util.Arrays.copyOf(...)`→`NativeJavaArray`（是 Wrapper）✅；JS 数组字面量→`NativeArray`（非 Wrapper）→强转失败→`runCatching` **静默吞掉**→`onStreamReady(null)`→Glide 拉黑 URL→「封面二次解密失败」
  - ★★★**三层缓存叠加**：Glide 密文缓存（加 `&hgimgv=2` 换 key）/ Glide `failUrl` **进程级黑名单**（改完**必须重启 App**）/ 正文缓存（旧书须删书重加）
  - ★★★**登录面板 `loginUi` 字段格式非法 = 所有功能全失效**：既不是 V1 的 JSON 数组、也不是 V2 的 `{"version":2}` 对象 → `GSON.fromJsonArray<RowUi>` 失败 → 界面能开但每行都不工作
  - ★★★**E 版兼容只能选 V1 静态数组**；**V1 的 `viewName` 是 JS 动态文本机制**（`rowUiBuilder` 里 `execute{evalUiJs(viewName)}`）⇒ 12 个固定线路位 + `viewName:"FQ_siteName(i)"` = 固定行数 + 动态面板，且不依赖 `reLoginView`
  - ★★**多选 `bookList` 后字段级选择器不按索引对应**（`name` 返回空）→ 所有字段统一 `@js:` 自解析，按结构用各自锚点（video `data-track-title` / rank `.hg-rank-item__title` / topic `.hg-topic-card__title`）
  - ★★**先量隔离矩阵再写规则**：`.hg-list-page` 之后 drama-card / rank-item / topic-card 三容器互不重叠
  - ★**`bookUrl` 必须自拼绝对 URL**：源码用 `baseUrl`（当前列表页）解析相对路径 → `/ranks/hot/` 页的 `/video/323/` 会拼成 `/ranks/hot/video/323/` → 404
  - ★**传输层会吃掉 `##`** → 用 `String.fromCharCode(35,35)` 构造
  - ★**并发测速用 `java.ajaxAll`**（61 候选 54ms，串行 88 秒）；**Rhino 里 `StrResponse.code/callTime/body` 是方法**必须 `r.raw.code()` / `r.callTime()` / `r.body()`
  - ★**`java.ajaxTestAll` 是 `isTest=true` 不真正发请求**，不可用于测速
- **沉淀文档**: [方法-封面钩子返回值必须是Java-byte数组与三层缓存中毒](../references/方法-封面钩子返回值必须是Java-byte数组与三层缓存中毒.md) · [方法-登录面板三协议辨析与E版兼容](../references/方法-登录面板三协议辨析与E版兼容.md) · [方法-多结构站点合并进单书源与封面钩子返回类型](../references/方法-多结构站点合并进单书源与封面钩子返回类型.md) · [方法-黄果短剧发布页寻线与换源登录面板实战](../references/方法-黄果短剧发布页寻线与换源登录面板实战.md)
