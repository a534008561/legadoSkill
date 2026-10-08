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

### 5. hanime1 视频书源 v3.9（bookSourceType=4 标杆案例 · 全链路）

- 文件：[`hanime1_视频书源_案例.md`](hanime1_视频书源_案例.md) + 成品 [`hanime1_视频书源_v39.json`](hanime1_视频书源_v39.json)
- 站点：`hanime1.me` / `hanime1.com`（Laravel SSR + Cloudflare + CDN77 媒体域）
- 技术要点：正文输出**带时效签名的 mp4 直链**；`dnsIp` 多 IP failover；**CDN 原生主机名替换**绕 SNI 封锁；
  `<useweb>` 活视图面板 + `ruleContent.callBackJs` 实现"播放切集，简介实时跟随"；
  登录 UI V2 控制台（域名/hosts/代理/清晰度/封面模式/跨域登录态同步）
- 方法论：[`references/方法-视频书源完全指南.md`](../references/方法-视频书源完全指南.md)

### 6. rrssk聚合 44域名多站聚合（状态漂移修复 + 选站三件套）

- 源：`rrssk聚合`（44 域名 / 14 套发现模板 / 双体系 rrssk家族+菠萝猫）
- 文件：`examples/rrssk聚合_44域名多站聚合.md` + 成品 `examples/rrssk聚合_44域名.json`（52532B，md5 `47b3976311e9286667f78f41b238f3a0`，check_source 1/1×3）
- 亮点：
  - ★**书架书正文为空根因**：全局 server 漂移（停在 boluomao 死站）→ 正文走 data-obf 分支取空；用户恢复手法=手动拨回 server
  - ★**URL 自治五层**：`SRV` 推导域名 / 章节绝对 URL + `chapterUrl=$.chapterurl` / `dataEncrypt` 显式键 / **别名书 data-aid 实际值自纠**（hggjfg→hgg）/ toc 取值链
  - ★**选站三件套**：登录面板 `<js>` 运行时生成 47 行 + 下拉 SET **移进 action**（防过期 live InfoMap 覆盖）+ 下拉下方**状态栏**读 server 真值
  - ★**check_source 三坑 + 模板引擎四铁律**（`{{}}` 无括号=属性路径 / Java 空串 truthy / evalJS 单参调不到 / 哨兵改 `!GET(key)`）
- 对应方法论：`references/方法-聚合源状态漂移修复与选站面板-rrssk.md`、`references/聚合源多域名架构设计.md`

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

- 禁漫天堂Pro（小说/漫画/视频三合一）[JSON](禁漫天堂Pro_三合一.json) / [案例说明](禁漫天堂Pro_三合一.md) — 成熟三合一范本：发现页下拉切形态、#/! 前缀分搜索、unified parser、useweb 收藏面板、作者芯片搜索

如果你有优秀的书源案例，欢迎添加到本目录！

案例格式要求：
- 文件命名：`网站名称.json` 或 `网站名称.json 参考.txt`
- 必须包含 `bookSourceComment` 说明网站特点和技术要点
- 书源功能完整（至少包含搜索规则）
- 规则注释清晰

---

**提示**：案例库按需加载，当前只加载了索引。需要具体案例时再读取对应文件。
- 69书吧_www.69shuba.tw [JSON](69书吧_www.69shuba.tw.json) — ★AEGIS(ALTCHA PoW)deny挑战类站首例：WebView通道传输层+loginCheckJs替换响应，验证页16字节keyPrefix=不可解判活法
- 次元姬小说_api.hwnovel.com [JSON](次元姬小说_api.hwnovel.com.json) / [案例说明](次元姬小说_api.hwnovel.com.md) — App官方API书源总纲：设备号服务端设备库风控（新16hex→`400网络繁忙`，共享已验证号+登录面板可改）；DES-ECB+MD5四件套签名（timestamp必须数字、签名无时间窗→永久签名URL书架长生）；VIP code=101免费预览；★★发现页固定basis列数必被divider挤成竖排→`layout_flexGrow:1`自动流式布局；签到提示走loginCheckJs；crates.io拆包逆向挖全套端点密钥
- ACFAN(禁漫)动漫·漫画·视频_www.acfan.com [JSON](ACFAN禁漫_www.acfan.com.json) / [案例说明](ACFAN禁漫_www.acfan.com.md) — ★**切片签名头 + 响应加密状态漂移**双堵点首例：站点 2026-10 升级后新增 `t`+`s`(=md5(t[3:8])) 签名头，缺头表现=HTTP 200 但 content-length:0 静默失败（四组对照实验定位）；同一接口响应明文/encData 随登录态漂移（双兼容解析）；敏感接口 5 头签名（bodySha 用键名升序紧凑 JSON）；登录态权威探针 POST /api/user/base/info；四分区发现页（视频/漫画/动漫/小说）+ fiction 小说新形态（文字=8/有声=32）

- QQ阅读(纯本地)_book.qq.com [案例说明](QQ阅读_纯本地_book.qq.com.md) — ★**正版 App 协议逆向 + 本地缓存型书源**（jsLib 396KB / loginUrl 76KB / 规则全 @js，本技能库体积最大的源）：官方 `{"type":"hex"}` URL 选项（二进制响应以 hex 进规则）+ 自实现完整密码学栈（SHA256/AES/DES/CRC32/Inflate + 自定义信封）+ 原生 Java 与纯 JS 双实现互备 + 响应头部指纹校验防密钥池漂移 + 试读/全文双态缓存 + 服务端拒绝包显式识别（绝不返回可疑文本）+ tar 容器一次拉 8 章只解密当前章 + 网络失败兜底本地缓存（伪造 StrResponse 实现离线可读）+ 设备指纹 43 字段表（被限时重生成而非换 IP）+ 段落级评论气泡注入 + 自动购买三护栏 + searchUrl 关键词特判触发自检；配套方法论见 [方法-正版App协议逆向与本地缓存书源-QQ阅读.md](../references/方法-正版App协议逆向与本地缓存书源-QQ阅读.md)

- STV越南聚合_sangtacviet.vip [JSON](STV越南聚合_sangtacviet.vip.json) / [案例说明](STV越南聚合_sangtacviet.vip.md) — ★**越南小说聚合翻译站（v11.11）**：票据式鉴权（grantcontext 发 key）+ **会话铸语义**（正文语种由「铸 key 那次请求的 Cookie」`transmode=chinese` 决定）+ 响应双数据字段（`data` 越南语 / `oridata` 中文）；★★**v11.11 分隔符型目录解析修复**：站点目录数据 `-//-` 分记录 + `-/-` 分字段，旧「平铺扫描」遇「标题含 `/`」→ 🔑 标记丢 4379 个（应 5460 实显 1081）；改为结构化解析 + `psegFlat()` 回退；**服务端 `unvip` 计数当免费真值交叉验证**；10 来源样本矩阵回归（9 个逐字节一致 + ptwxz 修正 1 条）；配套方法论见 [方法-抓包驱动的官方App行为对齐-STV篇.md](../references/方法-抓包驱动的官方App行为对齐-STV篇.md) §12
