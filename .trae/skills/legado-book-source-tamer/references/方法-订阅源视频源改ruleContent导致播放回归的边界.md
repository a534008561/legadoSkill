# 方法：视频订阅源「能播」的边界——ruleContent 一个字节都不能改

> 蓝本：91PORN 订阅源 261113 十三轮，用户实测纠正。
> 这是本会话最有价值的一条：**用户实机对照 > 源码推理 > 沙盒/WS 规则输出**。

---

## 0. 用户原话与 LAN 实锤

> 「现在一直加载，不能播放。我把 E 版退回原版封面不显示那版，视频可以播放」

LAN `/getRssSources` 双版回读：

| | lastUpdateTime | ruleContent | 播放 |
|---|---|---|---|
| E 版 91PORN（用户退回的「原版」） | 1794139497524 | **3851 B**（261108 v5） | ✅ 能播 |
| LT 版 91PORN（本次改过的） | 1794573600000 | **6091 B**（v6） | ❌ 一直加载 |

两版逐字段差异只有 6 项：`customOrder` / `enableReadRecord` / `lastUpdateTime` /
`loginUi` / `loginUrl` / `ruleContent` / `ruleImage` / `sourceComment`。
其中**唯一影响播放的是 `ruleContent`**。

---

## 1. 我这次做错的三件事（按时间序）

### ① v6：在 3851B 的 `ruleContent` 内层追加「签名时效预检」
v5 内层 1425B：`strencode2` → `/vlk.php` → 明文 `<source>` 三级兜底，
**最后 `url;` 输出裸 mp4 URL 字符串**。

我在内层插入 `if (url) { ... Date.now() ... java.post('/vlk.php') ... }` 换链段，
`ruleContent` 3851 → 6091 B。WS 回归看起来「全绿」（照样输出完整 `&f=` 直链），
**但用户点播放一直加载**。

### ② v7：把正文改成 `<video preload="auto">` HTML 播放器页
理由看似充分（源码 `clHtml` 默认样式含 `video{...}`、裸串被当纯文本），
页内 JS 还因引号冲突踩了 Rhino 语法错误，改成 base64 内嵌 `atob` 后 WS 全绿。
**用户：点播放加载一下就停。**

### ③ 反复在源码里绕
拉 `ReadRssViewModel` / `ReadRssActivity` / `RssWebResourceProxy` live 源码，
怀疑 Cronet 子资源代理、206 Range、`shouldInterceptRequest`……
用户答「Cronet 关着」⇒ 整条代理链根本不生效，推理全部作废。

### ★ 决定性答案
用户答：**「A. 页面里直接出现一个播放器/黑框，点播放能出画面（Legado 内置播放）」**
⇒ **Legado 对「正文输出裸 mp4 URL 字符串」有内置播放接管**（`type=2` 视频源 +
`loadDataWithBaseURL` 后的 WebView/内置播放器对网络 URL 的处理）。
一旦正文变成 HTML、或规则内多做一次网络换链，这个接管链路就断。

**铁律：这个源的 `ruleContent` 必须字节级保持 v5 的 3851 B，只输出裸 mp4 URL。
任何 HTML 包装 / 页内 JS / 规则内动态换链 / `<video>` 标签，都会让「点播放加载一下就停」。**

---

## 2. 为什么 WS「全绿」却不能播（最重要的判据纠错）

| 判据 | 能证明 | 不能证明 |
|---|---|---|
| WS `内容页解析完成` 前有完整直链/HTML | 规则链执行成功、签名正确 | **能不能出画面** |
| `java.head(直链)` 200 video/mp4 | CDN 可达、签名有效 | 内置播放器是否接管 |
| 源码 `clHtml` 含 `video{...}` | 支持 video 标签 | 该源该形态下播放器会不会被破坏 |

⇒ **视频源必须让用户实机点一次播放确认**；WS 全绿 ≠ 能播。
本会话连续三轮（v6/v7/v8 之前）都栽在「拿规则输出当播放成功」。

---

## 3. 正确做法：以「能播对象」为基线做字段级叠加

```python
base = LAN 回读用户确认能播的那个对象        # 3851B ruleContent
fix  = 本次修复来源
TAKE = ['ruleImage','loginUrl','loginUi','sourceComment']   # 只取不动 ruleContent 的

d = dict(base)
for k in TAKE: d[k] = fix[k]                 # 叠加封面/线路/面板
d['lastUpdateTime'] = ...

assert d['ruleContent'] == base['ruleContent']        # ★ 字节级断言
for k in 播放相关25字段: assert d.get(k)==base.get(k)
assert '<video' not in d['ruleContent'] and not d.get('preloadJs')
```

**v8 交付**：`ruleContent=3851B`（E 版能播原样）+ 封面 `i2.wp.com?w=320` 反代
+ 默认线路 418 + 测速自动选快 + 面板「🚀 一键切到最快线路」+ 封面代理开关。
其余 25 个播放相关字段（`ruleLink`/`ruleArticles`/`header`/`jsLib`/`sortUrl`/
`style`/`type`/`loadWithBaseUrl`/`singleUrl`/`ruleDescription`/`injectJs`/
`preloadJs`/`contentWhitelist`/`contentBlacklist`/`shouldOverrideUrlLoading`…）
**全部原样**。

---

## 4. 排查这类报障的正确顺序

1. **先问「改之前能播吗、哪一版能播」**，并 LAN 回读双版对象做逐字段 diff。
   用户的「退回某版就好了」是最高优先级证据，比任何源码推理都准。
2. 用 diff 把范围缩到**单个字段**，不要同时改多处。
3. 一次只回退一个字段，让用户实机点播放确认，再决定下一刀。
4. **不要拿 WS 规则输出当播放成功**；视频源唯一绿判据是用户看到画面。
5. 用户明确说「能播」的形态，就把它当**不可变基线**；优化只能叠加在
   不影响渲染/播放链路的字段上。

---

## 5. 顺带记录：确实存在的两个真实风险（但本轮不动）

- **正文永久缓存 × 2h 签名**：`loadContent` 把带 `&e=` 的直链写进
  `rssArticle.description`；`resolveRssReadLoadTarget` 对 description 非空直接
  `CachedContent` 不跑规则。反向验证：把 `e` 改成 2 小时前 → `HEAD 302`
  `Location: 1729130453.rsc.cdn77.org`（被墙域）。
  兜底：`refresh()` 在 `ruleDescription` 为空时走 `start(true, openUrl=link)`
  → `initData` 的 `openUrl` 分支 → `loadContent()` 强制重跑规则拿新链。
  ⇒ 用户「回看旧视频加载一下就停」时，**下拉刷新**即可，不要改 ruleContent。
- **封面图床 CDN 偶发 SSLHandshakeException**：`i2.wp.com` 代理 12/12 主要成功，
  但 HTTP 日志里仍有零星 -1；属网络层，不影响播放。

---

## 6. 方法论沉淀

- ★ 用户实测的跨版本对照（「E 版退回原版能播」）优先于我的源码推理与 WS 日志。
- ★ 「能播优先于优化」：为治卡顿去改播放链路，结果把能播改没了，是净负收益。
- ★ 诊断结论随排查演变时，每步都要对照实验实锤、不能停留上一假设；
  且**实验操作本身会改变环境状态**（本轮多次覆盖落库，最后必须重存正式版）。
- ★ 复杂页内 JS / HTML 播放器页不是默认增强项，只有用户确认形态后才可动。
