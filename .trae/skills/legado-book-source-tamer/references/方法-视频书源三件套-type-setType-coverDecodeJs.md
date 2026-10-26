# 方法：视频书源三件套 —— bookSourceType / setType / coverDecodeJs

> 沉淀来源：黄果短剧 v4（2026-10-27）。用户反馈「封面不显示、播放器不调取、正文显示裸 URL」三连，
> 根因是**同一族错误**：把视频站当文本站写。
> 标杆参照：红果短剧（`examples/红果短剧_www.hongguoduanju.com.json`，同类型 AI 短剧站）。

---

## 0. 症状 → 根因速查表

| 症状 | 根因 | 修法 |
| --- | --- | --- |
| 正文显示裸 URL（`https://xxx.m3u8?...`） | `bookSourceType=0`（文本），Legado 把正文当文字渲染 | `bookSourceType=4` |
| 播放器不调取 / 点了没反应 | 同上；且 `book.type` 被刷目录冲掉 | `chapterList` 内 `book.setType(4)` |
| 封面不显示（URL 提取正常、HTTP 200） | `BackstageWebView.blockNetworkImage=true` 竞态 | `coverDecodeJs` 规则侧下载转字节 |

**三招必须一起上**，只改一个不解决问题。

---

## 1. `bookSourceType=4`（视频型）

```json
"bookSourceType": 4
```

`BookType` 位掩码（`constant/BookType.kt`，LT 版）：

```
video = 4
text  = 8
audio = 32
image = 64
```

> ⚠️ **旧值 0/1/2 在 LT 版无效**。写 `bookSourceType: 0` 时 Legado 走 `TextView` 渲染正文，
> 于是一个 `.m3u8` 地址就原样显示成一行文字——**这就是「正文显示裸 URL」的直接原因**。

---

## 2. `book.setType(4)` 必须写在 `chapterList` 里（双设保险）

### 源码级铁律

`WebBook.getChapterListAwait()` **每次刷目录都执行**：

```kotlin
book.removeAllBookType()
book.addType(bookSource.getBookType())
```

⇒ 详情页设的 type 被**冲掉**，视频/漫画/听书又变回文字。

### 唯一稳妥做法：详情 + 目录双 `setType`

```json
"ruleToc": {
  "chapterList": "@js:\n(function(){\ntry{book.setType(4)}catch(e){}\n...\n})()"
}
```

> `try/catch` 必须带——老版本/其他分支可能没有 `setType`，裸调会让整个目录规则崩掉。

---

## 3. 封面：`coverDecodeJs`（封面专用下载钩子）

### 为什么不能自己写 `@js:` 转 base64

**`"选择器@js:"` 组合形式不执行**（`方法-legado各版本行为差异对照.md` 差异总表 #13）。
我第一版把 `coverUrl` 从 `img.0@data-src` 改成纯 `@js:`，结果 `result` 拿到的是
**整张卡片的 HTML**（选择器丢了），封面链接变成
`https://l205.arj2ftl0.cc/<div class="hg-drama-card">...`。

### 正解：`coverUrl` 保持纯选择器 + `coverDecodeJs` 下载

```json
"coverDecodeJs": "(function(){\ntry{\nvar u=String(src||'');\nif(!u||u.indexOf('http')!=0)return null;\nvar r=java.get(u,null,20000);\nif(!r)return null;\nvar b=r.bodyAsBytes();\nif(!b||b.length<800||b.length>235520)return null;\nreturn b;\n}catch(e){return null}\n})()"
```

要点：
- 钩子内建变量叫 **`src`**（不是 `result`）
- **返回字节数组**（`bodyAsBytes()`），不是 base64 字符串——App 侧自己编码
- 长度护栏 `800 ~ 235520`（防占位图/超大图拖慢首屏）
- 失败 `return null` → App 回落到网络地址，不会白屏

### 顺带解决：`blockNetworkImage` 竞态

`BackstageWebView.createWebView()` 里 `settings.blockNetworkImage = true` **硬写**，
`WebViewPool.release()` 才复位。池化 WebView 有竞态：某个 WebView 被上一个使用者置成
"屏蔽网络图片"后直接被 `acquire()` 出去 → **该页所有 `<img src="http…">` 都画不出来，
但 `data:` URL 不受影响**。

症状：**沙盒里 URL 明明 200，App 里就是空白**；换本书又正常。
⇒ `coverDecodeJs` 让封面走"规则侧下载"通道，天然绕开这条竞态。

---

## 4. 封面选择器的两个坑

### 4.1 列表页 vs 详情页的 `img` 顺序完全不同

| 页面 | `img.0` 是什么 |
| --- | --- |
| 列表/搜索卡片 | **封面**（`data-src` 懒加载） |
| 详情页 | **Yandex 统计像素图**（`mc.yandex.ru/watch/...`，无 `data-src`） |

⇒ 详情页用 `img.0@data-src` **取不到任何东西**（第一个 img 没有 `data-src` 属性）。

### 4.2 属性选择器 + 索引双重收窄

详情页正确写法：

```json
"coverUrl": "img[data-src^=https://pic].0@data-src"
```

- `img[data-src^=https://pic]`：只选 data-src 以图床域开头的 img（本站 12 张）
- `.0`：只取第一张（**必须加**，否则 `getString` 返回 12 个 URL 拼接串）

> 反面对照：不加 `.0` 时 debug 输出 12 行 URL 全拼在一起——
> 这是 Legado 对多匹配的默认行为（`getString` 累积拼接）。

---

## 5.  Checklist（视频/短剧书源）

```
□ bookSourceType = 4（不是 0）
□ chapterList 第一行 try{book.setType(4)}catch(e){}
□ 详情页规则也可加 setType（双保险，防只进详情不刷目录的路径）
□ 正文 content 返回纯 URL（不要包 <video> 标签——会被剥）
□ coverDecodeJs 已写（钩子内变量是 src，返回 bodyAsBytes()）
□ coverUrl 保持纯选择器（不要改成 @js:，组合形式不执行）
□ 列表页 coverUrl = img.0@data-src
□ 详情页 coverUrl = img[data-src^=图床域].0@data-src（带 .0 索引！）
□ debug_source 实测：正文输出应为裸 m3u8 URL，封面输出应为单个 URL
```
