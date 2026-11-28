# 爱丽丝书屋（alicesw）新版书源 · 站点与实现说明 261128

## 站点现状

- 主域 `www.alicesw.com`：**A 记录存在（202.160.128.14）但连接超时**，同时被解析出不可路由的 Tera 段 IPv6，
  实际不可用；判定为"线路淘汰"，不是临时故障。
- 现行架构：Next.js App Router + 同源 REST `/api/v1/*`，旧 `/search.html`、`/novel/{id}.html`、`/all/*.html` 全部 404。
- 发布页链路（2026-11-28 实测）：
  `xn--vcsx64d.asw4.cc`（爱丽丝.asw4.cc）
  → `xn--vcsx64d.als1007.space`（2 秒跳转）
  → `www.alicesw1.quest`（选线页）
  → `www.alicesw5.homes` / `alicesw6.homes` / `alicesw7.homes`（真实站点，三站同库）
- 全站基本免费（`average_chapter_price=0`、`has_paid_chapters=false`），但保留付费/VIP 字段；
  阅读不要求登录，书架/评论/购买需要。

## API 契约（书源实际使用）

| 用途 | 端点 | 备注 |
|---|---|---|
| 搜索 | `/api/v1/search/books?q=&page=&page_size=20` | `data.items[]`，含 `id/book_no/title/author_name/synopsis/tags[]/cover_url/chapter_count/word_count` |
| 书库 | `/api/v1/books?page=&page_size=&sort_by=&sort_order=desc&category_id=&tag=&status=completed` | `sort_by ∈ hot/view_count/favorite_count/word_count/created_at/last_chapter_at` |
| 榜单 | `/api/v1/operations/blocks` → `/api/v1/operations/blocks/{id}/books?page=&period=` | **必须用数字 id**，用 `source`（hot）会 400；`period ∈ day/week/month/total` |
| 分类 | `/api/v1/categories` | `data[]`：id/name/slug |
| 热词 | `/api/v1/search/hot` | `data[]` 40 个字符串 |
| 详情 | `/api/v1/books/{id}` | **只认 id，不认 book_no**；`tags` 是对象数组（搜索里是字符串数组） |
| 书号→id | `/api/v1/books/by-no/{book_no}` | 只返回 `{book_no,id}`，用于兼容 `/books/{书号}` 链接 |
| 目录 | `/api/v1/books/{id}/chapters` | 一次返回全量（6926 章 ≈1.8MB），不支持 page/page_size |
| 正文 | `/api/v1/chapters/{chapter_no}` | `data.content` 为**纯文本**（`\n` 分段），`can_read=false` 表示需登录/购买 |
| 封面 | `/api/v1/media/{hash}` | 相对路径，WEBP，无需鉴权 |
| 验活 | `/api/v1/config/public` | 约 3KB，用于线路 ping/测速 |

## 书源实现要点

- `bookUrl` = `{host}/books/id/{id}`；`ruleBookInfo.init` 抓详情写 `book.putVariable("ASW", json)`，
  8 个字段全部 `@js` 读变量（一次请求出全部详情字段）。
- `tocUrl` = `/api/v1/books/{ASWID}/chapters`；`chapterList` 输出 `{t,u,v,f}` JSON 字符串数组。
- `chapterUrl` 只存 `chapter_no`，`@js` 拼接当前线路 → 换线后章节链接自动跟随。
- `ruleContent.content` 直接 `JSON.parse(result).data.content`，清理零宽字符（`\u2063` 等反拷贝填充）
  与行首全角空格。
- `preUpdateJs` 在换线后重写 `book.bookUrl/tocUrl` 并 `java.refreshTocUrl()`，老书自动换域。
- 发现页：榜单（动态拉 blocks）+ 6 种排序 + 完结 + 分类 + 40 热词，共 87 条入口，无页码上限。
- 登录面板：发布页输入框、一键获取线路（BFS 解析 + 验活 + 自动切最快）、测速写 ms、
  6 个线路按钮（viewName 动态显示 `✔ 线路N host 248ms`）、登录/检查登录状态/登出，全部带 Toast。

## 验证记录

- LT（MCP debug_source）：搜索 20 条、详情 8 字段、目录 6926 章、正文正常；`bookUrlPattern` 正负样例通过。
- E（LAN WS 1126 / HTTP 1125）：搜索 20 条字段齐全、`getChapterList` 47 章、`getBookContent` 正文正常。
- 登录实测：`POST /auth/captcha` 取图 → 人眼识别 4 位码 → `POST /auth/login` 返回 `code:200`
  （user `a534008561` / `534008561@qq.com`），证明 `email/password/captcha_id/captcha_answer` 契约正确。
- `check_source` 通过 1/1。
- 回读 diff：除 `variable`（运行时字段，接口不返回）外 29 个字段与本地 JSON 完全一致。

## v2（261128 二次交付）：恢复原界面与原功能

用户反馈「原来的界面功能都没了，直接给我新造了一个」⇒ v2 按**同界面同功能、只换后端**重做：

- 登录面板恢复原 25 行顺序：获取站源 / 站源1~4 / 用户名邮箱 / 密码 / 注册 / 登录 / 登出 / 信息 /
  评论展示开·关 / 切换分类排序 / 默认·时间·人气·字数 / 自定义标签 / ◎↓网络书架↓◎ / 书籍ID / 添加·移除·跳转，
  仅额外插入「发布页输入框」「测速」两行（任务书要求）。
- 详情简介恢复原结构：书籍ID / 当前站源 / 浏览·收藏 / 字数 / 标签 / 更新时间 / 简介 / **评论区（含楼中楼）**。
- 发现页在原 87 条基础上加回：用户中心（书架/阅读记录/等级）、最近更新、原创作品、分类按排序切换、自定义标签 ⇒ 92 条。
- 登录态改为 Bearer token 写入 `loginHeader`，全站请求自动带；书架/评论/阅读记录据此可用。
- 变量新增 `s/co/tags/tok/user`，并对旧结构 `{urls,sourl}` 做迁移；`www.alicesw.com` 显式拉黑。
- 实测：LT 全链路 + 评论区 7/99 条楼中楼、609 章目录、正文正常；E 端 47 章目录与正文正常、WS 搜索 20 条；双端回读 29 字段一致、check 1/1。
- 待真机确认：书架添加/移除（Legado 无 `java.delete`，移除走 jsoup DELETE）、发表评论、阅读记录列表。
