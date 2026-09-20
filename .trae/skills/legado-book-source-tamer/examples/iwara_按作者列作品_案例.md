# 案例：iwara 详情页 →「打开作者全部视频合集」

> 站点：`iwara.tv`（MMD/3DCG 动画站，纯 JSON API + Cloudflare）
> 日期：2026-09-20 ｜ 版本：v13 ｜ 状态：**check_source 2/2 通过**，真机全链路验证通过
> 方法论文档：[方法-按作者列作品-API参数逆向.md](../references/方法-按作者列作品-API参数逆向.md)

---

## 一、需求

把两个 iwara 书源（`https://api.iwara.tv` 与 `https://api.iwara.tv###`）
**详情页 useweb 简介里的「🏠 作者主页」按钮**改成
**「打开该作者的全部视频列表合集」**。

---

## 二、最终效果

详情页作者行变为三个按钮：

| 按钮 | 行为 |
|---|---|
| `＋ 关注作者 <名字>` / `√ 已关注 <名字>` | 关注/取关（原有；未登录显示 `🔒 登录后可关注`） |
| **`📚 全部作品`** | **点一下把该作者全部视频变成一本合集书打开** ← 新功能 |
| `🌐 主页` | 内置浏览器打开网页版作者主页（原有，URL 已修正） |

自己的视频显示 `📚 我的全部作品` + `🌐 主页`。

**「合集书」的呈现**（真机实测）：
```
书名    @aide · 全部作品（51 个）
作者    Ameng
分类    📚 作者合集 · 共 51 个视频 · 本页 50 个（本页 一般向0/里向50）
字数    15.9GB
最新章节 最新 21.阿罗娜的节日礼物Arona
简介    作者 @aide / 共 51 个公开作品，当前显示第 1 页 50 个 / 前 20 条列表
封面    自动取第一件作品的缩略图（可内置为 data URI）
目录    001 … 050（每页50，翻页到 071 止），编号跨页连续
```

---

## 三、技术核心

### 3.1 ★正确的作者作品接口

```
GET https://api.iwara.tv/videos?user=<作者UUID>&page=N&limit=50&sort=date
```

**来源**：GitHub 开源项目 **yt-dlp** 的 `IwaraUserIE`：

```python
query = {'page': page, 'sort': 'date', 'user': user_id, 'limit': 32}
#                                        ^^^^^^^^^ 值是 UUID，不是 username
```

### 3.2 ★失败路径速查（都返回站内热门而非报错）

| 尝试 | 结果 |
|---|---|
| `?userid=<UUID>` | ✗ **count 正确但 results 全是站内热门**（count=51 对，命中 0/50） |
| `?user=<用户名>` | ✗ count=0 |
| `/user/{id}/content/videos` | ✗ `errors.forbidden` |
| `?userId=` / `?createdBy=` / `?author=` / `?u=` | ✗ 站内热门 |
| **`?user=<UUID>`** | ✅ 命中率 100% |

实测命中率：

| 作者 | count | 返回 | 命中 |
|---|---|---|---|
| pastapaprika | 44 | 44 | 44/44 |
| aide | 51 | 50 | 50/50 |
| fearess | 51 | 50 | 50/50 |
| user3207206 | 22 | 22 | 22/22 |

### 3.3 翻页（`nextTocUrl` 链式单 URL）

```
ruleToc.nextTocUrl = @js:IWRAFNX(java,source,baseUrl,result)
```

真机实测（aide，51 个作品）：
```
page=0 n=50 → nextTocUrl=...&page=1...
page=1 n=22 → nextTocUrl=(空,终止 ✓)
```

### 3.4 归属校验（防串作者）

```js
function IWRAFVFY(o,uid){
  // 1) uid 必须是完整 UUID
  // 2) results[].user.id 必须匹配
  // 不匹配 → throw 明确中文提示
}
```

**没有这一步**：用户点「全部作品」会看到别人的视频且毫不知情。

---

## 四、验证记录

### 真机 debug_source（A 源 · pastapaprika）
```
≡获取成功: .../videos?user=e5c40cb9-...&page=0&limit=50&sort=date&un=pastapaprika
┌获取书名     → @pastapaprika · 全部作品（44 个）
┌获取作者     → PastaPaprika
┌获取分类     → 📚 作者合集 · 共 44 个视频 · 本页 44 个（本页 一般向0/里向44）
┌获取字数     → 8.5GB
┌获取最新章节 → 最新 Nahida Cute and Funny Mo
└列表大小:44
◇章节名称:001 Big Sis Yixuan & Ju Fufu   [09:00]
◇目录总数:44
[正文] → https://herta.iwara.tv/view?hash=... (播放直链 OK)
```

### 真机 debug_source（A 源 · aide，51 个）
```
┌获取书名 → @aide · 全部作品（51 个）
└列表大小:50
作者行按钮：＋ 关注作者 Ameng | 📚 全部作品 | 🌐 主页   ✓
```

### 用户真机点击（B 源）—— HTTP 日志硬证据
```
GET https://api.iwara.tv/videos?user=73387536-0890-452d-823f-4311b2f7a308&page=0&limit=50&sort=date&un=user40616 -> 200
```

### 校验
```
check_source        → 通过 2/2
dpaste 字节级校验    → PASS（A 103792B / B 109160B）
深链导入硬证据       → GET dpaste.com/7S258PFXQ.txt -> 200
```

---

## 五、成品

| 源 | bookSourceUrl | dpaste | md5 |
|---|---|---|---|
| A | `https://api.iwara.tv` | `7S258PFXQ.txt` | `c991e8b96f26e34e222366669ed4d6d3` |
| B | `https://api.iwara.tv###` | `CXBPUKMAY.txt` | `968cf8602eb3841310aaaff0fc220eea` |

导入深链：
```
legado://import/bookSource?src=https%3A%2F%2Fdpaste.com%2F7S258PFXQ.txt
legado://import/bookSource?src=https%3A%2F%2Fdpaste.com%2FCXBPUKMAY.txt
```

---

## 六、顺带修复的问题

1. **`🌐 主页` 指向 API 地址** → 用户看到一堆 JSON；改为网页地址
   `https://www.iwara.tv/users/<name>`
2. **未登录时作者行整行消失** → `IWRFAROW` 开头 `if(iwTk==''){return L;}`；
   改为登录判据下推到「关注」按钮内部，三个按钮未登录也可见
3. **`IWRFAU` 取不到作者** → 作者响应的 `user` 在 `results[].user`，补兜底
4. **`bookUrlPattern` 不匹配作者书** → 扩展 `user` 分支 + `(?=[,?]|$)`

---

## 七、原始功能回归（全部未受影响）

- 单视频（目录 = 清晰度档位）
- 播放列表/合集（目录 = 每行一集）
- 搜索 / 发现页（68+ 标签入口）
- 关注 / 收藏夹 / 播放列表管理
- 封面内置、通道诊断、播放域名切换等登录面板功能
