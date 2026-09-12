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
