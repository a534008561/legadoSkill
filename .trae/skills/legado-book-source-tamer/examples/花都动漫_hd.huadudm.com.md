# ▶ 花都动漫（hd.huadudm.com）视频书源

## 一句话
飞飞CMS(FeifeiCMS) 影视站，HTML 直出，正文是 `player_data` 里的 **base64 + 多层 url-encode** 加密 m3u8 直链。

## 成品
| 项 | 值 |
|---|---|
| 文件 | `/workspace/huadudm/huadudm.json` |
| 大小 / md5 | 18174 B / `96e1bb0c44722b7f4055b9b040d74883`（v1.6） |
| 书源名 | `▶ 花都动漫` |
| bookSourceUrl | `https://hd.huadudm.com` |
| bookSourceType | 4（视频） |
| 分组 | 视频 |
| check_source | **通过 1/1** |

## 站点档案（全部实测）

| 项 | 实测结果 |
|---|---|
| 引擎 | 飞飞CMS (FeifeiCMS)，`feifeicms={"path":"","mid":"1"}` |
| 编码 | UTF-8 |
| WAF / CF | 无（`Server: IIS` + `X-Cache-Status`） |
| 登录 | **无需登录**，全站匿名可读可播 |
| UA | 不敏感（PC / 手机 / 无 UA 返回**逐字节相同**的 65,973 B） |
| 搜索限频 | 搜索框写着「搜索请间隔10秒...」，**但实测连续搜索不限流**（连搜多次均正常） |
| 单页条数 | 搜索 40 条 / 分类 40 条 |
| 每作品集数 | **固定 1 个视频**（标题含"第X集"的实为整段长视频） |

### URL 结构
```
搜索    /vodsearch/{关键词}----------{页码}---.html
分类    /vodshow/{分类}--------{页码}---.html
排序    /vodshow/{分类}--{time|hits|up}------{页码}---.html
详情    /voddetail/{id}.html
播放    /vodplay/{id}-{线路}-{集数}.html
```
> 分类共 16 个（1~16），全部有效；**分类 0 是空壳**（1072 B 占位页）。

### 分页参数位（12 段，用 `-` 连接）
```
/vodshow/{type}-{area}-{lang}-{year}-{letter}-{state}-{money}-{page}-{order}.html
          0      1      2      3       4       5       6      7      8
```
- 第 7 段 = 页码；第 8 段 = 排序（`time`/`hits`/`up`）
- 实测：`/vodshow/15--------2---.html` = 第 2 页；`/vodshow/15--hits------2---.html` = 人气榜第 2 页

> ★★★ **踩过的坑（v1.4→v1.5 修复）**：第一版把 `{{page}}` 拼在 `.html` **后面**
> （`/vodshow/1--hits---------.html{{page}}`），生成出
> `/vodshow/1--hits---------.html1` 这种 URL。
> **站点对畸形 URL 返回 200 + 正常页面**，所以 debug 看起来一切正常，
> 但翻页永远停在第 1 页。是 HTTP 日志里的 `GET .../html1` 才暴露的。
> 正解：页码必须落在**第 8 段槽位**：
> ```js
> function pgUrl(type,order){
>   var o=order?('--'+order):'--';
>   return '/vodshow/'+type+o+'------{{page}}---.html';
> }
> ```
> 第 1 页显式写 `1` 与站点省略页码段的形式**实测返回同一页**，所以统一用 `{{page}}` 最简。

### ★★★ v1.6：发现列表只显示一页（用户实测报障）

**排查结论：站点与规则都没有问题，问题在 App 的"翻页终止判定"链路。**

站点侧全部实测通过（这是排除法的关键，避免乱改规则）：

| 检查项 | 实测结果 |
|---|---|
| 分类 15 第 1/2/3 页 | 各 40 条，两两**零重复** |
| 分类 1 第 1/2 页 | 各 40 条，零重复 |
| 人气榜 hits 第 1/2 页 | 各 40 条，零重复 |
| 搜索「中字」第 1/2 页 | 40 条 / 4 条（共 44 条，2 页） |
| `{{page}}` 替换 | debug 显示 `/vodshow/16--------2---.html`，替换正常 |
| 连续打 8 页 | 全部 200、各 40 条、首条各不相同 |

**真正的失败机制（源码级）**：`ExploreShowViewModel.upData()` 里
```kotlin
} else if (adapter.getActualItemCount() == books.size) {
    loadMoreView.noMore()      // 判定"到底了"
}
```
只要某一页**没有新增任何书**（返回 0 条 / 全部重复），就会立刻 `noMore()`，
**之后滚到底也不再请求**。而 `books` 是 `linkedSetOf<SearchBook>`，去重键是 `bookUrl`。

于是三种情况都会造成"永久只有一页"：
1. 某页请求失败 → `books` 不增长 → `noMore()`
2. 某页返回空壳页（站点限流 7157B）→ `books` 不增长 → `noMore()`
3. 某页解析出 0 条 → 同上

**根因候选与对策**：

| 候选 | 实测 | 对策 |
|---|---|---|
| `page` 为 null/空/0 → URL 变成字面量 `null` → 站点返回 7157B 空壳（0 条） | `/vodshow/15--------null---.html` 实测 7157B / 0 条 | **页码归一化**：`Number(page)` 且 `>0`，否则取 1 |
| 单页偶发失败 → 直接 noMore | CDN 有短时频控（见下） | URL 追加 `{"timeout":20000,"retry":2}` |
| 空页被当成"真到底" | 越界页（5/4）与空壳页在 HTML 上**都能识别** | 读 `span.stats-text` 的 `第X/Y页`：`cur>=tot` 才算真到底，否则**抛错**（App 弹出可重试提示，不写 noMore） |

**v1.6 三处改动**：
```js
// 1) 页码归一化（写进 URL 模板，App 每次请求都会求值）
{{(function(){var p=Number(page);if(!(p>0)){p=1;}p=Math.floor(p);
   try{source.put(String.fromCharCode(104,103,112,103),String(p));}catch(e){}return p;})()}}

// 2) 每页追加超时 + 重试
'/vodshow/'+type+o+'------'+<上面的表达式>+'---.html,{"timeout":20000,"retry":2}'

// 3) 空页分流（关键）
var sm = statsText.match(/第([0-9]+)[/]([0-9]+)页/);
if (cur > 0 && tot > 0 && cur >= tot) return [];   // 真·到底
throw new Error('第N页返回空页面（站点可能临时限流），请点「重试」');  // 假空页
```

> `String.fromCharCode(104,103,112,103)` = `"hgpg"`。
> 用 charCode 拼键名是为了让这段表达式能安全嵌进**单引号 JS 字符串**里（零引号）。

**新增「翻页自检」按钮**（登录面板）：读出 `hgpg` 变量，
即 App 最近一次实际请求的页码。用它一步区分：
- 长期停在 `1` → App 压根没请求第 2 页（UI 层没触发翻页）
- 出现过 `2+` → 翻页链路正常
- 显示「无记录」 → App 没走到 URL 模板替换

**验证记录（v1.6）**：
| 用例 | 结果 |
|---|---|
| 分类 16 第 1 页 | 40 条 ✅ |
| 分类 16 第 2 页 | 40 条，首条 `长生录` ≠ 第 1 页 `美丽新世界` ✅ |
| 分类 16 第 4 页（末页） | 35 条 ✅ |
| 分类 16 第 5 页（越界） | 0 条，走"真到底"分支 ✅ |
| 搜索「中字」 | 40 条 + 详情 + 目录 + 正文 m3u8 ✅ |
| `hgpg` 变量 | 请求后写入 `1` ✅ |
| check_source | **通过 1/1** ✅ |

## 规则设计要点

### 1. 列表解析器（搜索 / 发现共用同一个 `@js:`）
```js
@js:(function(){
  // result 在 ruleSearch 是 Element，在 ruleExplore 也是 Element；双兼容
  var doc=(typeof result.select==='function')?result:Jsoup.parse(String(result));