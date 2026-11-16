# 聚合源批量新增同族站点：EX_HOST 回退加固与 301 迁移域陷阱（rrssk v10.2 / 261116）

> 场景：一次给「rrssk聚合」这类多域名书源增量加入 5 个同搜索引擎站点，落库后 check_source 连爆两种非站点故障。本文记录从「8 个链接→跳过已有 3 个→新增 5 个」的完整决策链和两个可复用教训。

## 一、先 diff，别急着加

用户给 8 个链接，**先 diff 现有 HOST_TEMPLATE_MAP**，发现 `shuhaoxs.com`/`ishuku.com`/`mopbook.com` 已在 45 域名内 → 真正新增只有 5 个。这一步避免重复添加和不必要的规则改动。

## 二、判断"同族"的四个实证点

候选站是否走既有通用分支，不靠猜，逐站抓页验证：

1. **详情页** `/book/ID.html` 有 og:title/og:novel:author/og:image 全字段 + `data-aid` + `var articleid`
2. **目录密钥** 页面引用的 `/templates/js/随机名.js` 里能抠到 `AESCrypt('..');` 和 `.parse('..');`（init 的正则天然兼容随机文件名）
3. **目录分页** `[data-aid=ID] option/li` 给页数，`POST /index.php?action=loadChapterPage` 返回 code=0 章节数组
4. **正文** `.content` 或 `.conBox` + `text.下一页@href` 章内分页

四点全中 = 详情/目录/正文零改动，只需给发现页分配列表模板。

## 三、发现页模板按"分类页真实列表容器"分配

每站的 `list-4-1/` 分类页抓下来看容器 class，映射到已有/新建模板：

| 站点 | 分类页容器 | 模板 |
|---|---|---|
| uushuk | `speList font16` | 复用 shoudaxsw |
| yxshufang | `ul.flex` | 复用 xinghuowxw |
| llshuku | `picZList font14` | 复用 shuwuwan |
| lxiawx | `picList4 font14` | **新建**，字段 `.name@a@text`/`.author@a@text`/`.about@a@text`/`.about@span.2@text` |
| shubennet | `cateIBox font16 > div.list` | **新建**，字段 `.name@a@text`/`.about@a.0@text`/`.about@a.1@text` |

新模板字段先在 App 内用 org.jsoup 实测 30 本全中，再写进 TEMPLATES，别凭 HTML 片段直接写。

## 四、★★坑 C：EX_HOST 回退到不在 rules 里的死域名 → check_source 崩

**现象**：`check_source` 报 `TypeError: 无法读取 undefined 的属性 bookList`，指向 `let bookListRL = rules[EX_HOST(baseUrl)].bookList;`

**根因链**：
- 用户 variable.server 被历史书签漂移成 `klxs123.com`（一个早已不在 HOST_TEMPLATE_MAP 的死域名）
- debug/校验器传进来的 `baseUrl` 为空 → `EX_HOST('')` 回退到 `GET('server')` = klxs123
- `rules['https://www.klxs123.com']` = undefined → `.bookList` 抛异常

**修法**（通用加固，保护所有站）：

```js
// EX_HOST 末尾：回退的 sv 必须在 rules 中存在，否则用 hosts[0]
if (sv && rules[sv]) return sv;
return (hosts && hosts.length ? hosts[0] : 'https://www.kelexs.com');
```

**诊断纪律**：遇到 `rules[xxx].字段 undefined`，先用 eval_js 打印 `GET('server')`、`source.getVariable()`、`EX_HOST('')`、`typeof rules[sv]`，不要改模板字段。

## 五、★★坑 D：301 迁移域导致 EX_HOST 取错模板 → "发现失效"

**现象**：加固 C 后 check_source 变成 `发现失效`，debug 显示 kelexs.com/list-1-1 → 301 → klxs123.com/list-1-1 → 列表 0。

**根因**：EX_HOST 用的是**原始 baseUrl**（kelexs.com，在 rules 中，取 kelexs 模板），但页面内容来自重定向后的 klxs123.com。进一步查明 klxs123.com 就是「可乐小说」新域（kelexs 的 301 迁移目标），页面结构同为 `list dList`。真正的问题是迁移域不在 map → 若将来 baseUrl 直接是 klxs123（部分重定向链会改写 baseUrl），回退就错位。

**修法**：把迁移域作为别名加入 HOST_TEMPLATE_MAP（映射到同一模板）+ bookUrlPattern：

```
'https://www.klxs123.com': 'kelexs',   // kelexs.com 301迁移目标
```

**通用原则**：老域名 301 到新域名时，新域名必须作为别名进 map，否则"域名自治"链在重定向后失效。

## 六、登录面板线路池的增量合并

`rrssk_speed_hosts` 一旦写进 cache 就固定，新增域名永远进不去选站面板。修法=rrHosts() 与 loginUi 初始化都改成：

```js
var _all = hosts.slice();
for (var _i = 0; _i < _all.length; _i++) {
  if (H.indexOf(_all[_i]) < 0) H.push(_all[_i]);
}
```

保留用户已有测速结果，只补缺失的新域名。

## 七、交付与验证

- 成品 72KB 超 save_source 内联上限 → LAN `POST /saveBookSource`（令牌头 x-legado-token）落库
- 门禁三件套：get_source 回读 14 字段字节级一致 + check_source 1/1 + 每站 `::list-4-1/` 全链路 debug（发现→详情→目录→正文）
- 搜索链路单独验：设 server=新站 → 搜"斗破苍穹" → 结果 URL 落在新域 → 目录正文全通
- 跨日签名站点：signJs v=日期 当天有效，换日需重验

配套成品：`examples/rrssk聚合_51域名_v10.7.json`（最终版，含后续 v10.3~v10.7 全部修复，同书源覆盖旧版）
