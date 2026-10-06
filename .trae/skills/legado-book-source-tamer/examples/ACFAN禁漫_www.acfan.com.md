# ACFAN(禁漫) 动漫·漫画·视频·小说 书源 — www.acfan.com

> 成品：`examples/ACFAN禁漫_www.acfan.com.json`（与 App 内版本一致）
> 书源名：**ACFAN(禁漫)动漫·漫画·视频**　bookSourceUrl：`https://www.acfan.com`
> 版本：v15（2026-10-06 抓包重写）　check_source：**通过 1/1**

---

## 1 站点真相

- `https://www.acfan.com` 是**发布页**，只返回 `document.location='https://<线路域>'` 的跳转。
- 发布页线路 API：`GET {发布页}/web/new/address/api/list/{24位hex}` → `data.data[]`（`addressType==1` 才是内容站）。
- 内容站是同一后端的 Nuxt3/Vue SPA，**SSR 不出数据**，真正数据全走 JSON API。
- 内容形态四类：**视频 / 动漫 / 漫画 / 小说（2026-10 新增）**。

## 2 请求头体系（2026-10 升级后）

### 2.1 基础头（所有请求必需）

| 头 | 值 | 说明 |
|---|---|---|
| `t` | 毫秒时间戳 | **每次请求重新生成** |
| `s` | `md5(t.substring(3,8))` | 切片式签名 |
| `sdkVersion` / `sdk_version` | `1.1.9` | 注意大小写两种都发 |
| `appVersion` | `1.9.9` | |
| `fp_version` | `3.0.1` | |
| `hr` | `ver=1.9.9` | |
| `device_fingerprint` | 固定 64hex | 从抓包抄 |
| `deviceId` | `h5_<16hex>` | 可随机生成后持久化 |
| `device` / `clientType` | `Android` / `android` | |
| `User-Mark` | `xhp` | 注意连字符需引号 |
| `X-Requested-With` | `mark.via` | |
| `aut` | 登录 token | 登录时才有 |
| `sid` | 用户 ID | 登录时才有 |

★ **缺 t/s 的表现**：HTTP 200 + `content-length: 0`（静默空响应，零报错）。

### 2.2 敏感接口头（登录等写操作）

`X-Sensitive-Action:1` + `X-Request-Timestamp` + `X-Request-Nonce` + `X-Request-Body-SHA256` + `X-Request-Signature`

- `bodySha` = sha256(**键名升序的紧凑 JSON**)
- `signature` = sha256(`[METHOD, path, ts, nonce, bodySha, SECRET].join('\n')`)
- `SECRET` = `aB3!k9$zL2@mQ8#xV5^nY7*pW1(jH4&`（从抓包逆向 + 离线复算 MATCH）

## 3 响应形态

- **明文**：搜索 / 视频详情 / 漫画详情 / 漫画章节 / newGetByClassify / hot/list
- **encData（AES-256-CBC）**：classifyList / classList / getTags / classTypeListPc(登录时) / signKey / time
- **随登录态漂移**：classTypeListPc 匿名=明文、登录=密文
- 解密：`key = iv = token.substring(2,18)`，`Base64.decode(enc, 2)`

## 4 接口清单

| 用途 | 接口 | 方法 | 登录 |
|---|---|---|---|
| 搜索 | `/api/search/public/keyWord?searchWord=&page=&pageSize=` | GET | 否 |
| 视频详情 | `/api/video/public/getVideoById?videoId=` | GET | 否 |
| 视频分类列表 | `/api/video/public/newGetByClassify?classifyTitle=&sortType=&page=&pageSize=` | GET | 否 |
| 分类树（视频） | `/api/video/classTypeListPc?restricted=0&type=N` | GET | 否(明文)/是(密文) |
| 标签 | `/api/video/tags/getTags?classifyId=&page=&pageSize=&mark=2` | GET | 是 |
| 热词 | `/api/search/public/hot/list` | GET | 否 |
| 漫画列表 | `/api/comics/base/public/findListPc` | POST | 否 |
| 漫画详情 | `/api/comics/base/public/info?comicsId=` | GET | 否 |
| 漫画章节图 | `/api/comics/base/public/chapterInfo?chapterId=&comicsId=` | GET | 否 |
| **小说详情** | `/api/fiction/base/info?fictionId=` | GET | **是** |
| **小说列表** | `/api/fiction/base/findList` | POST | **是** |
| **小说章节** | `/api/fiction/base/chapterInfo?chapterId=&fictionId=` | GET | **是** |
| 播放（免签） | `/api/m3u8/public/decode/authPath?path=&auth_key=&hevc=1` | GET | 否 |
| 登录 | `/api/user/v1/public/account/login` | POST | - |
| 登录态检查 | `/api/user/base/info` | POST | 是 |
| 线路列表 | `/api/sys/public/group/list` | GET | 否 |

★ `authPath` 播放接口**不需要 t/s 头**（无头也返回 m3u8）。

## 5 四分区发现页

顶部「分区」下拉：**视频 / 漫画 / 动漫 / 小说**

| 分区 | 入口数 | 内容 |
|---|---|---|
| 视频 | 10 | 动漫/视频/里番/精选 × 最新/最热/最赞 |
| 动漫 | 43 | 动漫分类 + 热词（动态拉取） |
| 漫画 | 49 | 48 个主题分类 |
| 小说 | 9 | 分类（需登录） |

★ 小说分区未登录时返回**友好提示条目**（不抛异常中断列表）。

## 6 小说形态细节

- `fictionType==1` → 文字小说，`info` 字段是正文
- `fictionType==2` → 有声小说，`playPath` 是 mp3 绝对地址
- 章节列表在 `chapters[]`（`chapterId` / `chapterTitle` / `chapterNum`）
- `book.type`：文字=8、有声=32（**必须在 chapterList 里动态设**）

## 7 登录界面（21 行）

```
ID账号 / 密码
★ 登录 / ✖ 退出登录
发布页网址 / 当前线路网址
↓ 抓取线路（官方接口） / ✅ 应用网址
≡ 当前网址 / ▦ 当前状态 / 🔐 检查登录状态 / ⏱ 测当前网址延迟
[1]..[N] 线路按钮（带延迟 ms）
已登录 昵称 #UID
```

★ **🔐 检查登录状态**：调 `POST /api/user/base/info`，200→"✅ 登录有效"，301/1001→"❌ 登录失效请重新登录"。

## 8 实测记录

| 项 | 结果 |
|---|---|
| 搜索「原神」 | 24 条 ✅ |
| 视频详情 | 全字段 + data:base64 封面 ✅ |
| 视频目录/正文 | 2 章 + hls.js 播放页 ✅ |
| 漫画详情/目录/正文 | 58 张图片多域名轮换 ✅ |
| 小说详情 | 58 章（神女赋）✅ |
| 小说正文 | 文字正常显示 ✅ |
| 有声小说 | 返回 mp3 URL ✅ |
| 发现页四分区 | 10/49/43/9 入口 ✅ |
| 登录 | 爱而无畏 uid=74054529 ✅ |
| 登录态检查 | ok=true ✅ |
| 抓取线路 | 8 条带延迟 ✅ |
| check_source | 通过 1/1 ✅ |

## 9 交付通道

- 文件：`/workspace/acfan15/acfan_v15.json`（55KB，超出 MCP 内联上限）
- uguu 上传：`https://h.uguu.se/zepQvnmS.json`（字节校验 MATCH）
- 深链：`legado://import/bookSource?src=<urlencode(raw)>`
- 硬证据：HTTP 日志出现 `GET <raw> -> 200`

## 10 已知限制

- **小说分区需登录**（所有 fiction 接口都要 `aut`）
- 有声小说的加密流若 App 无 Widevine CDM 可能不可解（返回 URL 本身是正确的）
- 站点 CDN 域名频繁轮换（封面/图片走 `AC_doms` 池 + 响应自带 domain 优先）
- 视频播放走 `authPath`（免签），播放器只取 `.url` 与 `.headerMap`


---

## v16 修复（2026-10-07，用户反馈 6 项）

| # | 问题 | 根因 | 修复 |
|---|---|---|---|
| 1 | 视频不播放 | hls.js 播放页 `var SRC="..."` **缺右引号** → 整段 script SyntaxError | 补 `+Q+`；加 CDN 递归兜底 |
| 2 | 小说正文只有标题 | 只读了 `info`（209字预览），完整正文在 `playPath`(.txt) | 新增 `AC_ftxt`：拉 txt + 扫 UTF-8 中文起点去 101 字节头 |
| 3 | 文字/有声小说分开 | 混在一起 | 发现页独立入口 + 章节名 📖/🎧 前缀 |
| 4 | 有声小说不播放 | `playPath`(xxs830域) 403 | 改用 `mp4Domain + fictionUrl`（2MB ID3 正常） |
| 5 | 有声调起视频播放 | `book.type` 不对 | chapterList 强制 `32`(audio) / `8`(text) |
| 6 | 发现页按 H5 重置 | 自造分区与站点不符 | 按 H5 分类体系重建（101 行 / 90 可点） |

### 关键技术

**A. txt 混淆头**
- 每个 .txt = **101 字节混淆头 + UTF-8 正文**（头部前 4 字节固定 `a3c1a3c1`）
- 通用去头：扫描第一个 UTF-8 中文字符（`E4-E9` + `80-BF` + `80-BF`）
- App 实现：`java.get(url).bodyAsBytes()` → `Arrays.copyOfRange(b, start, len)` → `new String(sub,'UTF-8')`

**B. 音频地址**
- ❌ `playPath`（`xxs830.mallnn.xyz`）→ 403 / 16 字节
- ✅ `mp4Domain + fictionUrl`（如 `https://aevwi.jts3qsek.work/service/novel/xxx.mp3`）→ 2097152 字节 ID3

**C. hls.js 页面修复**
```js
// ✘ 缺右引号 → SyntaxError: Unexpected identifier 'none'
+'var SRC='+Q+m3u8+';'
// ✔
+'var SRC='+Q+U+Q+';'
```

**D. H5 分类体系（发现页）**
- 视频：精选/里番(type=1) + 动漫/视频/同人/国漫/3D/MMD/原神/崩坏3/番剧(type=2) + 热播/乱伦/国产/网黄/萝莉/AV/传媒/重口(type=4) + 伦理/少女/泄露/网红/窥视/抖音风(type=5)
- 漫画 13 分类；小说按 `fictionType=1/2` 分离文字/有声

### v16 验收

| 项 | 结果 |
|---|---|
| check_source | **通过 1/1** |
| 12 项功能矩阵 | 12/12 |
| 文字小说正文 | 5426 字完整显示 ✅ |
| 有声小说 | mp4Domain 地址 ✅ |
| 发现页 | 101 行(90 可点) ✅ |
| 各分区实测 | 9/9 有数据 ✅ |


---

## v17 发现页改版（2026-10-07，用户需求）

**需求**：发现列表用 select 把「视频 / 漫画 / 文字小说 / 有声小说」四类分开。

### 实现

顶部一个 select 下拉，`action:'ACZSET4(source,infoMap)'` 切换 `acZone` 变量，
exploreUrl 按 zone 分支生成对应分类列表：

```js
var MAP={'视频':'video','漫画':'comic','文字小说':'novel','有声小说':'audio'};
var zone=AC_g(sv,'acZone'); if(!zone||!CN[zone]) zone='video';
R.push({title:'分类',type:'select',url:null,
  chars:['视频','漫画','文字小说','有声小说'],
  default:CN[zone], action:'ACZSET4(source,infoMap)',
  style:{layout_flexBasisPercent:1}});
if(zone==='comic'){comic();} else if(zone==='novel'){novel();}
else if(zone==='audio'){audio();} else {video();}
```

### 四分区内容

| 分区 | 内容 | 实测 |
|---|---|---|
| 视频 | 精选/动漫/番剧/里番/视频（各3排序）+ 同人向/热播向/剧情向分类 + 实时热词 | 43~76 行 |
| 漫画 | 13 分类（最新/热门推荐/同人/CG·AI/韩漫/独家/国漫/日漫/单行本/BL/COS写真/3D/女性向） | 15 行/13 可点 |
| 文字小说 | 最新/最热 + 8 分类（都市激情/校园春色/武侠古典/家庭乱伦/另类小说/激情骚麦/午夜故事/短篇故事） | 13 行/10 可点 |
| 有声小说 | 最新/最热 | 6 行/2 可点 |

### 小说分类 classId 对照（实测反查）

| classId | 名称 | classId | 名称 |
|---|---|---|---|
| 1 | 都市激情 | 6 | 另类小说 |
| 2 | 校园春色 | 8 | 激情骚麦 |
| 3 | 武侠古典 | 9 | 午夜故事 |
| 5 | 家庭乱伦 | 10 | 短篇故事 |

★ 反查方法：用 classId 拉列表第一条 → 拿 fictionId 查详情 → 读 `classList[0].title`
（列表接口本身不返回分类名）

### v17 验收

| 项 | 结果 |
|---|---|
| check_source | **通过 1/1** |
| 14 项功能矩阵 | 14/14 |
| 四选一下拉 | 切换 audio→video ✓ |
| 四分区实测 | 24/24/24/24 条 ✓ |
| 章节前缀 | 🎧📖 ✓ |

---

## v18 精选分区 + 完整标签体系（2026-10-07）

**需求**：①有声小说有更多分类 ②增加精选分区

### 抓包分析关键发现

**1. tagIds 是数组参数**（此前用 `tagId` 单数**静默无效**）
```json
{"tagIds":[29,33,36,37,41],"fictionType":2,"page":1,"pageSize":15}
{"tagIds":[1,27],"fictionType":1,"page":1,"pageSize":15}
```

**2. 双标签体系（tagType）**
- `tagType=1`（18个）：文字小说标签
- `tagType=2`（15个）：有声小说标签

**3. 多标签是 AND 交集**（不同组合返回不同结果，故用「主+副」组合）

**4. 精选数据源**：`GET /api/station/stations?classifyId=4&pageSize=10&page=N`
- p1=10站 / p2=8站（共 18 站）
- 每站自带 `videoList`（4~6 视频），结构与视频列表一致 → 复用 AC_items

### 五分区结构

| 分区 | 内容 | 实测 |
|---|---|---|
| **精选** | 18 个官方推荐站点（进站必看/2026新番/经典里番/ASMR舔耳/乱伦禁忌...） | 14行/12可点 |
| **视频** | 精选/动漫/番剧/里番/视频 + 同人向/热播向/剧情向 + 热词 | 43行/35可点 |
| **漫画** | 13 分类 | 15行/13可点 |
| **文字小说** | 最新/最热 + 8 分类 + **18 标签** | 32行/28可点 |
| **有声小说** | 最新/最热 + **16 标签** | 21行/18可点 |

### 编码分配（★新增前缀前必查重）

| 前缀 | 用途 |
|---|---|
| `v:` | 视频分类 |
| `c:` | 漫画分类 |
| `n:` | 小说分类（classId） |
| `t:` | 小说标签（tagIds 数组）|
| `s:` | 精选站点 |
| `q:` | 热词搜索（**从 t: 改来**，因 t: 被标签占用）|

★ 踩坑：旧的 `t:` 热词分支未删除，新的 `t:` 标签分支永远不执行（返回 0 条）

### 标签全量实测

- **文字标签 18/18 有数据**（空姐 4 条，其余 24 条）
- **有声标签 16/16 有数据**（各 24 条）
- **精选站 18/18 有数据**（4~6 条/站）

### v18 验收

| 项 | 结果 |
|---|---|
| check_source | **通过 1/1** |
| 16 项功能矩阵 | 16/16 |
| 五选一下拉 | pick→audio→video ✓ |
| 标签筛选 | 34/34 全部有数据 ✓ |
| 精选站点 | 18/18 有数据 ✓ |

---

## v19 发现页排布优化（2026-10-07）

**反馈**：「一列直下太长了」

**根因**：条目用 `layout_flexBasisPercent:0.31`（期望 3 列）→ 被 divider/margin 挤成**一列直下**

**修复**：
```js
// ✘ 固定 basis（会被挤成竖排）
function row(t,c,w){R.push({title:t,url:B+c,style:{layout_flexBasisPercent:w||0.31}});}
// ✔ flexGrow 自动流式
function row(t,c){R.push({title:t,url:B+c,style:{layout_flexGrow:1}});}
```

**样式三段式**：
| 元素 | 样式 |
|---|---|
| 条目 | `{layout_flexGrow:1}` 自动流式 |
| 分区标题 | `{layout_flexBasisPercent:1,layout_wrapBefore:true,layout_justifySelf:'flex_start'}` |
| 顶部下拉 | `{layout_flexBasisPercent:1}` |

**验收**（各分区样式分布）：

| 分区 | flexGrow 条目 | basis1 整行 |
|---|---|---|
| 精选 | 18 | 2 |
| 视频 | 67 | 9 |
| 漫画 | 13 | 2 |
| 文字小说 | 28 | 4 |
| 有声小说 | 18 | 3 |

★ 「其他」样式 = 0（无遗漏）
