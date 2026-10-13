# 📻 番茄听书 (APP) — Legado 音频书源

- **书源名**：📻番茄听书(APP)
- **bookSourceUrl**：`https://fanqienovel.com##听书版`
- **书源类型**：`bookSourceType = 1`（音频），`BookType.audio = 32`
- **书源分组**：听书,番茄,AI
- **校验状态**：`check_source` 通过 1/1
- **成品文件**：`final.json`（45709 B，md5 `08dcb192852339eecfbe68e3cac18c34`）
- **构建脚本**：`build.py`（11 项闸门）
- **直链备份**：https://d.uguu.se/xyraVOzE.json

## 1. 功能清单（全部实测通过）

| 功能 | 状态 | 说明 |
|---|---|---|
| 搜索 | ✅ | `api.fanqiesdk.com` 免签接口，10 条/页 |
| 发现页 | ✅ | `tab_type=5` 听书频道，12 本/页 |
| 详情 | ✅ | `audio/detail`（名称、作者、分类、简介、封面、音色表、总章数） |
| 目录 | ✅ | 与小说共用 `directory/all_items/v`，实测 184/272/468 章 |
| 正文（音频） | ✅ | 下载 → CENC 解密 → 写 `.m4a` → 返回 `file://` |
| 音色选择 | ✅ | 登录界面 3 个按钮 + Toast |
| 缓存复用 | ✅ | 487 ms 秒播（首次约 17 s） |
| 缓存清理 | ✅ | 自动保留 6 个 + 手动清空 |
| 登录需求 | ❌ | 匿名全功能，**无需登录** |

## 2. ⚠️ 用户必须确认的路径硬编码

`FQ_CACHE` 在 jsLib 中硬编码为：

```js
var FQ_CACHE='/storage/emulated/0/Android/data/com.legado.app.release/cache';
```

- **release 版**（`com.legado.app.release`）可直接用
- **debug 版**（`com.legado.app.debug`）需改包名
- **legado-E / 其他分支**包名可能不同，需自行替换

## 3. 核心技术链路

### 3.1 音频播放地址（本轮最大突破）

```
POST https://api5-sinfonlineb.novelfm.com/novelfm/playerapi/video_model/mget/v1
```

**必须同时满足**（否则 `{"code":4000,"message":"bad request"}` 或 404）：

- query 里带 `aid=3040` + 完整 `device_type=UGFFI55` + `app_name=novelapp` + `version_code=58932` + `channel=0`
- body：`{audio_type:0, bgm_used:0, book_id, device_score:0, item_ids:[...], multi_shift:false, source:"default", tone_id, user_select_start_para:0, user_select_start_para_off:0}`
- 签名：`x-argus`/`x-ladon`/`x-ss-stub`（= MD5(body)）+ UA `com.dragon.read`

响应 `data.video_model_datas[0].video_model` 是 **JSON 字符串**，需二次 `JSON.parse`，取 `video_list["0"]`。

> 注：`/reading/reader/audio/playinfo/` 只返回 tone（音色）列表，不返回播放地址；用它会拿到 `content-length: 0`。

### 3.2 main_url 是明文 URL（不需要 spade URL 解密）

`video_model.video_list[0].main_url` **直接就是 https 明文**，可下载（8.6 MB 约 1.8 s）。
`fallback_api` 里的 `video_list.video_1.main_url` 才是 spade 密文 + 伴随 `data.key_seed` —— **本链路不需要它们**。

### 3.3 CENC 内容密钥派生（spade_a → 16 字节 key）

```js
raw = base64Decode(spade_a)
v8  = len(raw) - (raw[0]^raw[1]^raw[2]) + 47      // 钳到 len-1
work = raw[1 : 1+v8]
a=85, b=246
for i in 0..v8:
    prev = (i&1) ? a : b
    if (i&1) a = work[i] else b = work[i]
    work[i] = (-21 - popcount(i) + (prev ^ work[i])) & 255
key = ascii(work[1:33])      // 32 个 ASCII 字符 = 16 字节
```

实测本例：`spade_a = "o7wt9WeNL/BTthTOW4cg/Fq1FvlasRD/XbIn/2uBJNFrniOMjA=="`
→ `key = "b33b1fd00a72cca355412646b53f6759"`

### 3.4 MP4 box 定位与逐样本解密

关键 box（本例实际偏移）：

```
ftyp@0/28  moov@28/271365
stsd@433/183   → enca@449  (fourcc type 字段在 453)
stsc@648/76    → 5 条：[1,2822][2,2821][3,2822][7,2821][8,2781]
stsz@724/90152 → 22533 个样本，dflt=0，逐样本 size
stco@90876/48  → 8 个 chunk，ch[0]=271409
senc@90924/180280 → 22533 个 IV（每样本 8 字节）
```

解密：

```
每样本：iv16 = senc[i*8 : i*8+8] + 8×0x00
        AES/CTR/NoPadding DECRYPT
```

**解密成功判据**：首样本头变为 `2111450014500146fff10a5a5a5a5a5a`（AAC-HE ADTS，`FF F1 0A 5A`）。

### 3.5 fourcc 修复（只扫 moov 范围，0 ms）

```
enca → mp4a
sinf → free（并清零 sinf body）
```

**必须限定范围**（本例 `mend=400000`）。若全文件 8.6 MB 逐字节扫 4 字符，实测 **46.9 秒**；限定 moov 后 0 ms。

### 3.6 写文件与播放

```js
var hex = HexUtil.encodeHexStr(bytes);
var path = java.downloadFile(hex, 'https://x/fa'+tone+'_'+itemId.substring(0,18)+'.m4a,{"type":"m4a"}');
return 'file:///storage/emulated/0/Android/data/com.legado.app.release/cache' + path;
```

音频书 `ruleContent.content` 返回值即播放地址（源码 `AudioPlay.contentLoadFinish`：`durPlayUrl = content`）。

## 4. 音色选择（登录界面）

`loginUi` 三个按钮，action 调用 jsLib 函数，全部带 Toast：

| 按钮 | action | 行为 |
|---|---|---|
| 🎙 切换音色 | `FQ_atoneBtn(source,java)` | 循环切到下一个音色，`toast('已切换音色：X')` |
| 🎵 当前音色 | `FQ_atoneShow(source,java)` | `toast('当前音色：X（ID n）')` |
| ↩️ 恢复默认 | `FQ_atoneReset(source,java)` | 置 0，`toast('音色已重置为默认(推荐)')` |
| 🔍 检查状态 | `FQ_acheck(source,java)` | 设备池/音色/测试书，`longToast` 多行 |
| 🗑 清空缓存 | `FQ_aclear(source,java)` | 删文件 + `toast('已清空音频缓存（N 个文件）')` |

音色存 `source.put('fqTone', id)`；正文 `subContent` 音色名（阅读时显示在副标题）。

实测音色差异：默认(0)、甜美少女音(1)、清亮青叔音(2)、成熟大叔音(4)、大叔音升级版(74)、升级版·多角色(97)…… `toneinfo` 接口可拿本书完整音色表（`data.tones` 逗号串），jsLib 内置 24 个常用项。

## 5. 缓存设计

- 键：`fqA_<bookId>_<itemId>_<toneId>` → 相对路径
- 键列表：`fqAKeys`
- **文件名必须唯一**（`fa<tone>_<itemId前18位>.m4a`）。早期版本固定文件名导致三本书互覆盖、缓存全失效（实测同一路径 `85c5a4e3adeba826.m4a`）
- 命中：先 `java.readFile(path)` 验证 `>100000` 字节，487 ms 返回
- 淘汰：保留最近 6 个，超出的 `java.deleteFile`

## 6. 性能

| 阶段 | 耗时 |
|---|---|
| 搜索 | ~0.4 s |
| 发现页 | ~1.6 s |
| 详情 + 目录 | ~3 s |
| 音频下载（8.6 MB hex） | 1.8 s |
| CENC 解密（22533 样本） | 7.8 s |
| fourcc 修复 | 0 ms |
| 写文件 | ~1 s |
| **首次播放合计** | **~17 s** |
| **缓存命中** | **0.49 s** |

## 7. 已知限制

1. **首次播放需等 17 s**（Rhino 无法流式解密，必须完整文件才能修 moov）
2. **文件大小上限 22 MB**（App 堆内存 256 MB，hex 字符串约 4× 文件字节），超出提示换音色
3. **缓存路径硬编码 release 包名**，跨版本需改
4. 缓存文件在 App cache 目录，系统清理后需重新解密
5. 部分书可能无音频（`tts_status=0` 或接口返回空），此时正文规则抛中文错误



## 9. ★ 音色选择 UI（260913 修正版）

### 9.1 落点选择

| 落点 | 状态 | 说明 |
|---|---|---|
| **登录界面** | ✅ 主用 | 28 个按钮（说明/当前音色/24 音色/重置/检查/清空），`loginUi` 用 `<js>FQ_atoneRows()</js>` 运行时生成 |
| **发现页** | ⚠️ 简化 | 只保留"点一下切换"的音色按钮；**去掉搜索输入框**（本 App 不注入 infoMap，取不到输入内容） |

### 9.2 三条硬约束（实测）

1. **`loginUrl` 必须非空**（至少 `function login(){return 'ok';}`）—— 否则登录界面不显示
2. **`loginUi` 的 `<js>` 环境没有 `source`/`java`/`infoMap`**（只有 `result`/`book`/`chapter`）→ 生成函数必须**无参且不访问 source**
3. **按钮 `action` 环境只有 `java`（+ 部分版本有 `infoMap`），没有 `source`** → 函数签名统一 `function FQ_xxx(jv)`，用 `jv.put/get/toast/longToast/reLoginView`

### 9.3 音色提示三重保险

```js
try{jv.toast('已切换音色：'+nm);}catch(e){}
try{jv.longToast('🎙 已切换音色：'+nm+'\n（重新进入章节生效）');}catch(e){}
try{jv.put('fqLastMsg','🎙 当前音色：'+nm);}catch(e){}
try{jv.reLoginView(false);}catch(e){try{jv.reUiView(false);}catch(e2){}}
```

### 9.4 输入框方案的失败记录（勿重试）

实测 dump：
```
fqDiag2 = "bindKw@1791868143707 | infoMapType=undefined | got="
```
text 的 action **确实触发**，但 `infoMap` 为 `undefined` → 本 App 版本不注入 infoMap → 输入框取词不可行。需要用户输入的交互请用 `jv.searchBook('')` 打开系统搜索页。

## 8. 与同族书源的关系

| 书源 | 类型 | 说明 |
|---|---|---|
| 🍅番茄小说(APP) | 文本 | 同一套签名 + CM DH 解密 |
| 🍅番茄漫画(APP) | 图片 | 同一套签名 |
| 🔴红果短剧API版 | 视频 | CENC 解密同源算法（hev1 修复） |
| **📻番茄听书(APP)** | **音频** | 本文档，CENC 解密 + mp4a 修复 |

CENC 解密三件套（spade 派生 / 逐样本 CTR / fourcc 修复）与红果通用，但**听书的 fourcc 是 `enca→mp4a`**（红果是 `encv→hev1`），且**听书的 main_url 是明文**（红果需 spade URL 解密）。
