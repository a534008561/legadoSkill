# 方法：字节系官方 App 接口的签名门槛与降级策略（红果短剧实战）

> 蓝本：`红果短剧（网页版）`（`https://hongguoduanju.com`）——从「只有官网 SSR」到「摸清官方 App API 全貌」的完整调研
> 调研日期：2026-10-10
> 触发场景：用户要求「修复全集播放」，最终确认**服务端硬限制**并给出诚实降级
> 交叉引用：
> - SSR 内联 JSON 取数 → `方法-SSR内联JSON书源的括号配平提取.md`
> - 网页版限制与绕过尝试 → 本文 §3
> - 官方 App 协议逆向（番茄系）→ `方法-正版App协议逆向与本地缓存书源-QQ阅读.md`

---

## 目录

- 一、核心结论（先看这一节）
- 二、★如何找到"官方 App 接口"的完整线索链
- 三、红果官方 API 全貌（含路径/参数/签名要求）
- 四、★X-Argus 签名门槛：为什么书源侧无法实现
- 五、免签接口清单（可直接用）
- 六、★降级策略：把"做不到"做成"用户能理解"
- 七、★漫画"点下一话重复第一话"的根因与修复
- 八、通用方法论：判断"能否突破"的决策树
- 九、避坑清单 K1~K12
- 十、验证方法

---

# 一、核心结论

| 问题 | 结论 |
|---|---|
| 红果网页版为什么只有前 3 集？ | **服务端策略**：`accessible_episode_cnt` 恒为 3，第 4 集起 `/player/{sid}/{vid}` 返回 404（无 `<a>` 标签、无解锁入口） |
| 官方 App API 能用吗？ | **不能**。核心接口（`multi_video_detail`/`multi_video_model`）需要 **X-Argus 签名**，该签名由 so 库内算法生成，书源侧无法实现 |
| 桌面版为什么能看全集？ | 它内置 `unidbg-sign.jar`（`com.hongguo.sign.FqTrace serve 0`）——**用 unidbg 模拟 Android so 库**生成签名，这不是纯 HTTP 方案 |
| 漫画"点下一话重复第一话"能修吗？ | **能修（已修）**：服务端忽略 `vid` 参数恒返回第 1 话 → 加 vid 校验，不一致时明确报错而不是静默重复 |
| 正确的做法是什么？ | **如实标注 + 中文提示 + 目录标记**，不要伪造数据、不要静默失败 |

---

# 二、★如何找到"官方 App 接口"的完整线索链

这次调研的价值不只在结论，更在**方法**。完整链条：

## 2.1 从用户给的仓库找"非公开"线索

用户给的 `waligoraamodio288-rgb/hongguo-desktop-releases` 是**发布仓库**（无源码），但有三个金矿：

1. **PR #120**（社区贡献）的 `desktop_bootstrap.patch` 直接暴露了后端启动方式：
```diff
+        from windows_java_paths import java_runtime
+        jre = java_runtime(root, data)
         signer = subprocess.Popen(
-            [str(root / "jre/bin/java.exe"), ...
+            [str(jre / "bin/java.exe"), "-Djava.net.preferIPv4Stack=true", "--add-opens", ...
              "-Xmx512m", "-XX:+ExitOnOutOfMemoryError", "-cp", "unidbg-sign.jar",
              "com.hongguo.sign.FqTrace", "serve", "0"],
             cwd=root / "sign", stdin=subprocess.DEVNULL,
```
→ **一眼看出**：`unidbg-sign.jar` + `com.hongguo.sign.FqTrace serve 0` = unidbg 模拟 so 库做签名

2. **Issues 里的错误信息**：
   - `"播放服务已响应，但未能取得剧集列表（HTTP 500）"` → 说明有独立的剧集列表接口
   - `"search_request_failed, reason: invalid_payload, status: 200"` → 说明搜索接口对参数敏感
   - `"signer 回环监听"` → 签名服务是**本地 HTTP 服务**

3. **README 的分享链接格式**：`novelquickapp.com/s/...` → 说明有 App 侧域名

## 2.2 用"同族项目调研"补齐接口

在 GitHub 搜索红果/番茄相关项目，找到一个**专门做接口调研的项目**：`N3urda/hongguoTV`，它的 `docs/research/2026-09-21-hongguo-open-source.md` 是一份**现成的接口清单**：

```
| 用途 | 路径 | 证据 |
| 搜索 | GET /reading/bookapi/search/tab/v | zhangbaio/hongguo、drpys、danmu_api |
| 分集详情 | POST /novel/player/multi_video_detail/v1/ | zhangbaio/hongguo、danmu_api |
| 视频模型 | POST /novel/player/multi_video_model/v1/ | zhangbaio/hongguo、drpys |
| 预加载版详情 | POST /novel/player/multi_video_detail/preload/v1 | zhenyong97/hongguo-downloader |
| 预加载版模型 | POST /novel/player/multi_video_model/preload/v1 | zhenyong97/hongguo-downloader |
```

## 2.3 读实现代码拿"完整参数"

`zhenyong97/hongguo-downloader` 的 `src/native/hongguo.js` 给出了**完整的公共参数表**（这是最省时间的一步）：

```js
const COMMON_QUERY = {
  klink_egdi: "AAI29o4dI-eMiO73_SRSbZ_0By1v3fUSriNeu8-L951MoXhWT88pzj5B",
  iid: "3788260546453235",
  device_id: "538083340353620",
  ac: "wifi",
  channel: "oppo_8662_64",
  aid: "8662",                    // ★ 红果的 aid（番茄小说是 1967）
  app_name: "novelread",
  version_code: "71532",
  device_platform: "android",
  ...
};
const HEADERS = {
  "User-Agent": "com.phoenix.read/71532 (Linux; U; Android 9; SM-N9860; ...)",
  "Accept": "application/json; charset=utf-8,application/x-protobuf",
  "Content-Type": "application/json; charset=utf-8",
};
```

## 2.4 ★关键发现：签名要求的"分级"

`zhangbaio/hongguo` 的 `hongguo.py` 里有一段**决定性注释**：

```python
# 列表类接口(landpage 筛选/最新上架 + bookmall/cell 榜单)经实测红果不校验 X-Argus 签名,
# 游客态、并发均返回 code=0。默认对这些接口免签,把高频轮询(latest/rank/filters/browse)
# 从签名后端(unidbg)彻底卸载,避免其被打爆/OOM。
```

**这条注释告诉我们：接口分两类**——免签（列表/榜单/筛选）与必签（详情/播放）。

---

# 三、红果官方 API 全貌

## 3.1 基础信息

| 项 | 值 |
|---|---|
| 域名 | `api5-normal-sinfonlineb.fqnovel.com` |
| 红果 aid | **8662**（番茄小说是 1967，别混） |
| 红果 UA | `com.phoenix.read/71532 (Linux; U; Android 9; SM-N9860; ...)` |
| 必带头 | `Content-Type: application/json; charset=utf-8` |
| body 校验头 | `x-ss-stub` = MD5(body).upper()（**仅此还不够**） |

## 3.2 接口表（实测）

| 用途 | 方法 | 路径 | 签名 | 实测结果 |
|---|---|---|---|---|
| 搜索 | GET | `/reading/bookapi/search/tab/v` | ❌ 需签 | `len=0`（被拒） |
| 搜索（旧） | GET | `/reading/bookapi/search/page/v` | ❌ 需签 | `{"code":100103,"message":"PARAM_INVALID"}` |
| 榜单/筛选 | GET | `/reading/distribution/category/landpage/v` | ✅ 免签 | `len=0`（参数需调） |
| 榜单 cell | GET | `/reading/bookapi/bookmall/cell/change/v` | ✅ **免签** | `{"code":0,"message":"SUCCESS",...}` **200 OK** |
| 分集详情 | POST | `/novel/player/multi_video_detail/v1/` | ❌ **需签** | `{"Code":110001,"Message":"未知异常"}` |
| 视频模型 | POST | `/novel/player/multi_video_model/v1/` | ❌ **需签** | 同上 |

## 3.3 签名失败的两种表现

| 响应 | 含义 |
|---|---|
| `len=0`（空响应） | 请求被网关直接丢弃 |
| `{"Code":110001,"Message":"未知异常","BaseResp":{"StatusCode":110001}}` | 通过网关但签名校验失败 |

**重要**：`110001` **不是参数错误**。我一开始误以为是参数问题，反复调参浪费了很多时间。看到 `110001` 就应该想到**签名**。

## 3.4 详情接口的完整 body（供参考）

```json
{
  "biz_param": {
    "detail_page_version": 0,
    "disable_digg_stat": false,
    "disable_video_relate_book": false,
    "image_shrink_datas_str": "W3siaW1hZ2VfdHlwZSI6MywiaW1hZ2Vfd2lkdGgiOjkwMCwic2hyaW5rX3R5cGUiOjN9LHsiaW1hZ2VfdHlwZSI6NCwiaW1hZ2Vfd2lkdGgiOjU0LCJzaHJpbmtfdHlwZSI6NH1d",
    "need_all_video_definition": false,
    "need_mp4_align": false,
    "screen_width_px": "900",
    "source": 7,
    "use_os_player": false,
    "use_server_dns": false
  },
  "series_id": "7572458140411628568"
}
```

---

# 四、★X-Argus 签名门槛

## 4.1 签名是什么

字节系的请求签名由 **so 库（native 层）** 生成，包含：
- `X-Argus`：主签名
- `X-Gorgon` / `X-Khronos`：辅助签名（部分接口）
- `X-Ladon`：部分接口

这些**无法用纯 JS/HTTP 复现**，因为算法在 `libcms.so` 之类的 native 库里。

## 4.2 桌面版怎么解决的

```
desktop_bootstrap.py
  └─ subprocess.Popen([jre/bin/java.exe, "-cp", "unidbg-sign.jar",
                       "com.hongguo.sign.FqTrace", "serve", "0"])
     └─ unidbg（基于 Unicorn 的 ARM 模拟器）
        └─ 加载红果 App 的 so 库 → 调用签名函数 → 返回 X-Argus
```

**成本**：需要打包 JRE（~40MB）+ unidbg + so 库，且签名服务要常驻。

## 4.3 书源侧为什么做不到

| 障碍 | 说明 |
|---|---|
| Rhino 无法执行 ARM 机器码 | 书源的 JS 引擎是 Rhino（Java 实现），不是 native 执行环境 |
| 需要 so 库文件 | 书源无法携带二进制依赖 |
| 需要常驻服务 | 书源是"一次性脚本"模型，无法维持长驻进程 |
| 即便能算也违规 | 绕过客户端签名属于对抗平台安全机制 |

**结论：书源侧实现 X-Argus 签名不可行，这不是"技术难度"问题，而是"架构不匹配"问题。**

---

# 五、免签接口清单（可直接用）

实测**免签可用**：

```
GET /reading/bookapi/bookmall/cell/change/v
  参数: cell_id=1&offset=0&count=20
  返回: {"code":0,"message":"SUCCESS","data":{"cell_view":{...},"has_more":false,...}}
```

**注意**：免签接口返回的是"外壳"（cell_view 元信息），**实际的书籍列表仍需签名**才能拿到内容。所以免签接口只能用于：
- 探测站点存活
- 获取榜单结构元信息

**不能用于**：获取书籍列表、详情、播放地址。

---

# 六、★降级策略：把"做不到"做成"用户能理解"

## 6.1 三条原则

| 原则 | 反例（不要做） | 正例（应该做） |
|---|---|---|
| **如实标注** | 目录只列前 3 集，让用户以为全剧只有 3 集 | 目录列出全部集数，不可播的标「需App」 |
| **明确提示** | 返回空字符串（用户以为卡了） | 返回中文说明 + 原因 + 出路 |
| **不伪造** | 用第 1 集冒充第 2 集 | 检测到不一致时明确报错 |

## 6.2 具体实现（红果 v13）

**目录层**：不可播集数用 `locked#` 伪 URL 标记
```js
if(i<acc){
  out.push(String(JSON.stringify({name:nm,url:u})));
}else{
  out.push(String(JSON.stringify({name:nm+'（需App）',url:HG_BASE+'/locked#'+i})));
}
```

**正文层**：识别标记并给出结构化提示
```js
if(bu.indexOf('/locked#')>=0){
  return '⚠ 本集需要红果官方 App 才能观看。\n\n· 红果网页版每部剧仅开放前 3 集试看\n· 第 4 集起请在官方 App 观看（免费）\n· 目录中带「需App」标记的即为这类集数';
}
```

**★伪 URL 的技巧**：用 `#fragment` 而不是新路径，因为：
- 不会发出真实 HTTP 请求（Legado 对 `#` 后的内容不发往服务器）
- 天然唯一（不会与其他章节去重冲突）
- 可携带参数（`#3` 表示第 3 集）

## 6.3 提示文案的写法

好的提示应该包含三段：
```
⚠ [问题是什么]
· [为什么]
· [怎么办]
· [怎么识别]
```

---

# 七、★漫画"点下一话重复第一话"的根因与修复

## 7.1 现象

用户点漫画第 2 话，显示的内容是第 1 话。

## 7.2 根因（实测）

红果漫画的服务端**完全忽略 `vid` 参数**：

```
/comic/7111943588446997534                       → item=262990 (第1话)
/comic/7111943588446997534?vid=262990            → item=262990 ✅
/comic/7111943588446997534?vid=233287            → item=262990 ❌ 还是第1话
/comic/7111943588446997534?vid=283022            → item=262990 ❌ 还是第1话
```

`next_vid` 字段也指向同一个值（形成循环）：
```
第1次: cur=(空) → item=262990 next=233287
第2次: cur=233287 → item=262990 next=233287   ← 循环
```

## 7.3 修复：vid 校验

```js
function HG_REQVID(u){
  u=String(u||'');
  var i=u.indexOf('vid=');
  if(i<0)return '';
  var s=u.substring(i+4);
  var q=s.indexOf('&');
  if(q>=0)s=s.substring(0,q);
  return s;
}
function HG_MANGA_ITEM(h){
  // 从响应里取实际返回的 item_id
  var d=HG_DECODE(h,'content');
  if(!d)return '';
  var cs=String(d.content||'');
  if(!cs||cs==='undefined')return '';
  var o=null;
  try{o=JSON.parse(cs);}catch(e){return '';}
  var cl=o.chapter_info_list||[];
  if(cl.length<1)return '';
  return String(cl[0].item_id||'');
}
```

正文规则：
```js
var reqVid=HG_REQVID(bu);
var gotVid=HG_MANGA_ITEM(h);
if(reqVid&&gotVid&&reqVid!==gotVid){
  return '⚠ 本话需要红果官方 App 才能观看。\n\n· 红果网页版漫画仅开放第 1 话试看\n· 其余话数请在官方 App 观看（免费）';
}
```

## 7.4 ★通用模式：**"服务端静默降级"必须加客户端校验**

当站点用"返回默认数据"代替"返回错误"时（而不是 404），书源侧**必须主动校验**请求参数与响应数据是否一致。

识别信号：
- 请求不同参数，响应完全相同
- 响应里有"当前项 ID"字段，与请求参数不符
- 存在 `next_xxx` 字段但循环指向自己

---

# 八、通用方法论：判断"能否突破"的决策树

```
遇到"只有前 N 集/章"的限制
  │
  ├─ 1. 站点是否返回 404 / 明确的错误？
  │     ├─ 是 → 检查是否有其它入口（API/App/分享链接）
  │     └─ 否（返回默认数据）→ ★服务端静默降级，加客户端校验
  │
  ├─ 2. 是否存在官方 App / 桌面版客户端？
  │     ├─ 是 → 找它的接口（见 §2 线索链）
  │     │     ├─ 接口是否需要签名？
  │     │     │    ├─ 否 → ★可直接用！
  │     │     │    └─ 是 → 看签名实现方式
  │     │     │         ├─ 纯 JS/哈希 → 可复现
  │     │     │         └─ native so 库 / unidbg → ★书源侧不可行
  │     │     └─ 是否有免签的接口子集？
  │     │          └─ 有 → 可用于探测/列表（但可能拿不到内容）
  │     └─ 否 → 检查网页版是否有其它路由
  │
  └─ 3. 全部不可行 → 降级交付
        ├─ 如实标注限制
        ├─ 目录标出不可用项
        └─ 给出可操作的中文提示
```

## 8.1 判断"签名是否可实现"的快速方法

| 信号 | 判断 |
|---|---|
| 签名算法在 JS 里（能搜到 `md5`/`sha`/`hmac`） | ✅ 可实现 |
| 有开源项目用纯 Python/Node 实现 | ✅ 可实现 |
| 开源项目依赖 `frida` / `unidbg` / `jadx` | ❌ 不可实现 |
| 文档提到 `so 库` / `native` / `X-Argus` / `X-Gorgon` | ❌ 不可实现 |
| 桌面版客户端内置 `.jar` / `.so` / JRE | ❌ 不可实现 |

---

# 九、避坑清单 K1~K12

| # | 坑 | 教训 |
|---|---|---|
| K1 | 把 `110001` 当参数错误 | 这是**签名失败**，调参无用 |
| K2 | 用番茄的 `aid=1967` 请求红果 | 红果是 **8662**，app_name 是 `novelread` |
| K3 | 路径少尾斜杠 | `multi_video_detail/v1` 无尾斜杠会 404，**必须 `/v1/`** |
| K4 | 以为 `x-ss-stub` 就够了 | 它只是 body 校验，**不等于签名** |
| K5 | 在书源里尝试复现 native 签名 | 架构不匹配（Rhino 无法执行 ARM） |
| K6 | 服务端返回默认数据时静默接受 | 必须加**参数-响应一致性校验** |
| K7 | 用新路径做"不可用"标记 | 用 `#fragment`（不发请求、天然唯一） |
| K8 | 目录只列可播项 | 应列全部 + 标记，让用户知道真实集数 |
| K9 | 提示只写"失败" | 三段式：问题+原因+出路+识别方法 |
| K10 | 忽略发布仓库的 PR/Issue | 它们常暴露**架构级信息**（如 unidbg） |
| K11 | 只读 README 不读源码 | 参数表/路径在**实现文件**里 |
| K12 | 用户说"开源项目"就只找那个项目 | 应扩展到**同族项目调研**（找专门做接口研究的） |

---

# 十、验证方法

## 10.1 接口可达性三层验证

```js
// 第 1 层：域名可达
java.ajax(API+'/')            // 404 也算可达（TLB 响应）

// 第 2 层：路径存在
java.ajax(API+'/reading/bookapi/bookmall/cell/change/v?...')  // 返回 JSON = 路径对

// 第 3 层：签名通过
// {"Code":110001} = 签名失败
// {"code":0} = 成功
```

## 10.2 签名要求验证（对照实验）

```js
// 同一请求，只改一个变量
A: 带完整参数 + 无签名 → 110001
B: 带完整参数 + x-ss-stub → 110001
C: 带完整参数 + 完整头 → 110001
// 三组都失败 → 确认是签名门槛，而非参数问题
```

## 10.3 静默降级验证

```js
// 用不同参数请求，比对响应的"当前项 ID"
reqVid=262990 → gotVid=262990 ✅
reqVid=233287 → gotVid=262990 ❌  ← 证明服务端忽略参数
```

---

# 十一、通用结论

1. **先查有没有官方 App/桌面版，再决定方案**——网页版往往是"阉割版"，而 App 接口可能免签。
2. **签名门槛要看"实现方式"而不是"是否存在"**——纯 JS 可实现，native so 不可实现。
3. **接口有"签名分级"**——列表/榜单类常免签，详情/播放类必签。先摸清哪些免签。
4. **`110001` 是字节系的签名失败码**，见到它别再调参数。
5. **服务端静默降级必须客户端校验**——这是"点了没反应/重复第一集"类 bug 的通用根因。
6. **降级交付要做成"用户能理解"**：如实标注 + 目录标记 + 三段式提示。
7. **发布仓库的 PR/Issue 是信息金矿**——架构级信息（如 unidbg、签名服务）常在那里暴露。
8. **同族项目调研比单点挖掘高效**——找"专门做接口研究"的项目，能省几天时间。
