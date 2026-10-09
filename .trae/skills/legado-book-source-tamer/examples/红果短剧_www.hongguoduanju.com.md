# 红果短剧 API 版书源（hongguoduanju.com / api5-normal-sinfonlineb.fqnovel.com）

## 一句话总结

用**纯 JS 复现字节跳动 X-Argus 签名**（SIMON-128 + SM3 + AES-CBC），
直连官方 App API 拿到**全集剧集与明文 MP4 直链**，突破网页版「仅前 3 集」限制。

## 站点与接口

| 项 | 值 |
|---|---|
| 网页版 | https://hongguoduanju.com |
| App API | https://api5-normal-sinfonlineb.fqnovel.com |
| aid | 8662 |
| app_name | novelread |
| UA | `com.phoenix.read/72932 (Linux; U; Android 12; zh_CN; V2284A; Build/V417IR;tt-ok/3.12.13.20)` |

## 能力清单

| 功能 | 实现路径 |
|---|---|
| 搜索 | 网页版 `/search/{kw}` → 解析 `"searchList":[...]` |
| 发现（7 入口） | 网页版 `/rank/hot-{drama,real-drama,ai-drama,comic-drama}` + `/category/{real-drama,ai-drama,comic-drama}` → HTML 解析 |
| 详情 | API `POST /novel/player/multi_video_detail/v1/` |
| 目录（全集） | 同上，取 `video_data.video_list[]` |
| 正文（播放直链） | API `POST /novel/player/multi_video_model/preload/v1` |
| 站点状态检查 | 登录界面按钮（`HG_check`） |

## 关键参数

```js
// 详情
{ biz_param: {...}, series_id: '7503745441910017049' }

// 播放（★ video_platform 必须 1024，且在 biz_param 内部）
{
  biz_param: { ..., video_platform: 1024 },
  dr_scene: 'preload',
  mixed_video_id_map: { '1004': [vid] }
}
```

## 实测数据

- 《宴律，你的白月光回国了》76 集
- 《人到中年，系统逼我年少轻狂》118 集
- 《聚宝仙盆之杂灵根才是真BOSS第十三季》222 集
- 清晰度：360p / 480p / 540p / 720p / 1080p（自动选最高）
- 直链验证：Range `bytes=0-1023` → 返回 1024 字节真实数据
- 目录顺序：76/118/222 集全部连续无错位

## 验证状态

- ✅ `check_source` 官方校验通过 1/1
- ✅ `debug_source` 全链路（搜索 → 详情 → 目录 → 正文）
- ✅ 8/8 字段 md5 字节级一致
- ✅ 7 个发现页全部正常（20-24 条）
- ✅ 登录界面按钮实测可执行

## 与网页版书源的对比

| 能力 | 网页版 | API 版（本源） |
|---|---|---|
| 搜索 | ✅ | ✅ |
| 发现 | ✅ | ✅ |
| 详情 | ✅ | ✅ |
| 全集目录 | ❌ 仅前 3 集 | ✅ 全部 |
| 播放 | ❌ 第 4 集 404 | ✅ 全集 |
| 清晰度 | 单一 | 5 档 |

## 开源项目参考

| 项目 | 提供的关键信息 |
|---|---|
| `waligoraamodio288-rgb/hongguo-desktop-releases` | 桌面版架构（unidbg 方案，书源不可移植） |
| `zhenyong97/hongguo-downloader` | ★ `video_platform:1024` + `mixed_video_id_map` + 官网兜底 |
| `huangxd-/danmu_api` | ★ **纯 JS X-Argus 签名实现**（SIMON + SM3） |
| `N3urda/hongguoTV` | 接口路径表 |
