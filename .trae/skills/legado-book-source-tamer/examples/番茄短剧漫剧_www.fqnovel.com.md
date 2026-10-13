# 🍅番茄短剧·漫剧(APP)

- **bookSourceUrl**: `https://api5-normal-sinfonlineb.fqnovel.com##短剧版`
- **bookSourceType**: 4（视频）
- **分组**: 视频,番茄,AI
- **状态**: check_source 通过 1/1；LegadoTeam + legado-E 双版本实测可播

## 能力

| 功能 | 说明 |
|---|---|
| 发现页 | 3 频道：漫剧(tab_type=32) / 找剧(8) / 动漫(24)，两段式视频流，支持翻页 |
| 搜索 | `/reading/bookapi/search/suggest/v` 联想词通道（固定 10 条，含 video_data） |
| 详情/目录 | `multi_video_detail/v1` 一次拿全（book_info + video_list） |
| 播放 | shortplay 通道（aid=1967）+ CENC-AES-CTR 解密 + 本地 file:// 播放 |
| 画质 | 登录界面可切 360/480/540/720P（默认 360P） |
| 登录 | 无需登录，游客可看全集 |

## 关键技术

1. **两条通道分开走**：发现/详情走 aid=8662，播放走 aid=1967（后者各档位 bytevc1 可播，且 URL 是 base64 明文）
2. **CENC 完整清除 6 个 box**：encv→hev1、enca→mp4a、sinf/tenc/senc/saiz/saio→free
3. **file:// 路径动态探测**：`java.readFile('/')` 触发异常 → 从消息提取真实缓存目录（适配不同 App 包名）
4. **hex 用 BigInteger**：零 hutool 依赖，4MB 仅 330ms（纯 JS 需 80 秒）
5. **SM3 纯 JS**：零 bouncycastle 依赖（E 版 R8 裁剪）

## 四次报障演进

| 版本 | 报障 | 根因 | 解法 |
|---|---|---|---|
| v2 | `NoClassDefFoundError: java.awt.Color` | hutool 顶层引用 | BigInteger |
| v4 | 同上报错，堆栈在 `JavaMembers$MethodSignature` | Rhino 类成员枚举时触发 | 彻底移除所有第三方类 |
| v5 | Team 能播 / E 版不能 | `senc/saiz/saio` 残留 | 一并改 free |
| v7 | E 版仍不能 | **硬编码 Team 版包名路径** | 动态探测缓存目录 |

## 参考

- 开源项目：`github.com/ch6vip/fqapp`（番茄聚合客户端，Rust 核心逆向）
- 方法论：`references/方法-视频书源完全指南.md`（14124B，10 条播放条件链）
- 站点档案：`references/方法-字节系短剧App接口书源与CENC视频解密.md`（30938B）
