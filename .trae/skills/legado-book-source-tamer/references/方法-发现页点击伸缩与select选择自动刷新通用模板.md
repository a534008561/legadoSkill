# 发现页「点击伸缩 + select 选择 + 自动刷新」通用模板

> 适用范围：需要自己在 Legado 书源 `exploreUrl` 里搭发现页交互，包含「点一下展开、再点收起的下拉/分组」「select 下拉筛选」「select 选完自动刷新发现列表」。
> 本文是跨站通用模板，不绑定任何站点；与已有《方法-发现页本源搜索框与可伸缩分组列表.md》《方法-发现页select切换频道自动刷新UI的六种假象与真正根因.md》互补，把两类交互合成一份可直接照抄的骨架。

---

## 一、一句话结论

发现页交互不是 App 内置配置，而是 `exploreUrl` 生成的一组 `ExploreKind` 数据：

- 折叠条 = `type:'button'`，action 翻转 `source.getVariable()` 里的开关并 `java.refreshExplore()`。
- select = `type:'select'`，框架**自动写 `infoMap[title]`**，action 只需 `java.refreshExplore()`。
- 子项是否显示 = 求值时读同一个开关/ `infoMap`，决定是否 push 子项。
- URL 类入口 = `type:'url'`，筛选值在求值时烘焙进 URL。

---

## 二、源码级机制速查

| 机制 | 结论 |
|---|---|
| `exploreUrl` | 推荐写 `@js:` + IIFE，返回 `JSON.stringify(rows)`；求值环境注入 `source`、`java`、`infoMap`。 |
| `ExploreKind` | 字段：`title/url/type/action/chars/default/viewName/style`；`type` 常用 `url/text/button/select`。 |
| `action` | 必须是**单个字符串**，不是数组。数组会让 GSON 解析失败，整个发现页失效。 |
| select 赋值 | `ExploreAdapter` 在 `onItemSelected` 里先 `infoMap[title]=chars[position]`，再执行 action。**不要自己 SET/GET**（SET/GET 不是 Legado 内置函数，除非你的源 jsLib 自己定义了）。 |
| 自动刷新 | `java.refreshExplore()` → 清 `exploreKindsMap` + `aCache` → 重新求值 `exploreUrl` → 重绘发现页。缓存 key = `md5(bookSourceUrl + exploreUrl)`，不依赖 infoMap，但重求值时会读新 infoMap。 |
| 折叠状态 | 存 `source.getVariable()/setVariable()`（键 `sourceVariable_<源URL>`），与 `source.put/get`（键 `v_<源URL>_<key>`）是两个命名空间。 |
| 子项显隐 | 由 `exploreUrl` 求值时读状态决定，不要在 UI 层隐藏。 |

---

## 三、通用骨架（可直接照抄）

下面是 `exploreUrl` 字段的完整骨架模板：

```js
@js:(function () {
  // 1. 读持久化折叠状态。必须是 JSON 对象；保留用户已有字段。
  var CFG = {};
  try { CFG = JSON.parse(String(source.getVariable() || '{}')) || {}; } catch (e) {}

  var rows = [];
  var ROOT = '{{host(source)}}';                 // 换成你的站点 host 占位符
  var PG = "{{page>1?('/'+page):''}}";            // 列表分页；单页榜单用空守卫

  function pick(arr, v) {
    for (var i = 0; i < arr.length; i++) if (arr[i] === v) return v;
    return arr[0];
  }
  function val(k, def) {
    var v = '';
    try { v = infoMap[k]; } catch (e) {}
    v = String(v == null ? '' : v);
    return v === '' ? def : v;
  }
  function isOpen(k, defOpen) {
    return CFG[k] === undefined ? defOpen : CFG[k] !== 0;
  }

  // 2. select：框架已写 infoMap[title]，action 保持最简。
  function sel(title, chars, def, style) {
    rows.push({
      title: title,
      type: 'select',
      chars: chars,
      default: pick(chars, def),
      action: 'java.refreshExplore()',
      style: style || {}
    });
  }

  // 3. 点击伸缩条：翻转开关 + 持久化 + 重绘，三件事缺一不可。
  function fold(title, key, defOpen) {
    var q = JSON.stringify(key);
    var js = '(function(){var c={};'
      + 'try{c=JSON.parse(String(source.getVariable()||"{}"))||{};}catch(e){}'
      + 'c[' + q + ']=c[' + q + ']?0:1;'
      + 'source.setVariable(JSON.stringify(c));'
      + 'java.refreshExplore();})()';
    rows.push({
      title: (isOpen(key, defOpen) ? '▾ ' : '▸ ') + title,
      url: '',
      type: 'button',
      action: js,
      style: { layout_wrapBefore: true, layout_justifySelf: 'flex_start' }
    });
  }

  // 4. 直接入口 chip；筛选值在这里烘焙进 URL。
  function item(title, url, first) {
    rows.push({
      title: title,
      url: url,
      type: 'url',
      style: first ? { layout_wrapBefore: true } : {}
    });
  }

  // 5. 可选：标题行，url 为空即不可点。
  function head(title) {
    rows.push({ title: title, url: '', type: 'url', style: { layout_wrapBefore: true } });
  }

  // ===== 示例：频道 select =====
  var TYPE = val('类型', '小说');
  sel('类型', ['小说', '漫画', '视频'], TYPE, { layout_wrapBefore: true });

  // ===== 示例：筛选 select（选完自动刷新） =====
  var PERIOD = val('榜单周期', '日榜');
  sel('榜单周期', ['日榜', '周榜', '月榜', '年榜'], PERIOD, {});

  // ===== 示例：榜单入口（跟随 select） =====
  var pv = { '日榜': 'day', '周榜': 'week', '月榜': 'month', '年榜': 'year' }[PERIOD] || 'day';
  head('榜单');
  item('人气', ROOT + '/rank?sort=popular&period=' + pv + PG, true);
  item('收藏', ROOT + '/rank?sort=favorite&period=' + pv + PG, false);
  item('新作', ROOT + '/rank?sort=new&period=' + pv + PG, false);
  item('完结', ROOT + '/rank?sort=finished&period=' + pv + PG, false);

  // ===== 示例：点击展开的分类/标签 =====
  var key = 'cat_' + TYPE;
  fold('分类（点开/收起）', key, false);
  if (isOpen(key, false)) {
    var cats = [['全部', '/all'], ['都市', '/all/city'], ['校园', '/all/school']];
    for (var i = 0; i < cats.length; i++) {
      item(cats[i][0], ROOT + cats[i][1] + PG, i === 0);
    }
  }

  // 6. 必须保证任何折叠状态下至少有一个非空 url，
  //    否则 check_source 取不到 url，会误判「发现规则为空」。
  return JSON.stringify(rows);
})()
```

---

## 四、select 自动刷新的正确姿势

### 4.1 极简 action

```js
action: 'java.refreshExplore()'
```

如果确实要提示用户，可写：

```js
action: "java.toast('已切换');java.refreshExplore()"
```

但 `java.refreshExplore()` 必须是最后一句；它前面任何语句抛异常都会导致整段 action 中断，表现为「下拉标签变了但列表不变」。

### 4.2 不要照搬 SET/GET

`SET()` / `GET()` 不是 Legado 内置函数，是 rrssk 等源自己 jsLib 定义的。没有同名 jsLib 的源照搬会 `ReferenceError`，被 try/catch 吞掉后完全看不出错误。

正解：

- 求值端：`val('榜单周期', '日榜')` 直接读 `infoMap['榜单周期']`。
- action：只 `java.refreshExplore()`。
- 写值：交给框架。

### 4.3 筛选值如何进 URL

发现页 select 只是状态，不会自动改 URL。必须在 `exploreUrl` 求值时把状态烘焙进 URL：

```js
var st = val('状态', '全部');
var q = st === '全部' ? '' : '?status=' + statusMap[st];
item('全部', ROOT + '/all' + PG + q, true);
```

切换 select 后，因为 `java.refreshExplore()` 重求值，URL 会重建。

---

## 五、点击伸缩的正确姿势

### 5.1 三件套

1. `source.getVariable()` 读 JSON 配置。
2. `c[key] = c[key] ? 0 : 1` 翻转。
3. `source.setVariable(JSON.stringify(c)); java.refreshExplore();`

缺第 3 步就是「点了没反应」。

### 5.2 求值端同步判断

```js
if (isOpen(key, false)) {
  // 只有展开时才 push 子项
}
```

建议默认收起（尤其标签数量多时），避免发现页过长。

### 5.3 每个分组独立 key

```js
var key = 'tag_' + TYPE;       // 类型独立
var key = 'rank_' + TYPE;      // 榜单独立
var key = 'cat_' + TYPE + '_' + group;
```

不要所有分组共用一个 key，否则点开 A 会连带影响 B。

### 5.4 保留其它字段

错误写法：

```js
var c = {};                    // 会把用户其它配置全删掉
c.tag = 1;
source.setVariable(JSON.stringify(c));
```

正确写法见骨架中的 `fold()`：先解析原串，只改本次 key。

---

## 六、布局与可读性

- 折叠条：`layout_wrapBefore:true` + `layout_justifySelf:'flex_start'`，独占一行。
- 直接入口：
  - 数量少、名称短：可用自适应宽度。
  - 需要整齐网格：`layout_flexBasisPercent:0.31 + layout_flexGrow:1`（三列），比 0.23 四列更不容易截断 4 字中文。
- 长名称：不要写死三列/四列，文字会被 `ellipsize=end` 截断；优先自适应宽度。
- emoji 会占宽度并导致省略号，发现页分类/榜单标题尽量不用 emoji；功能性的 `▸/▾` 可保留。
- 任何折叠状态下都要留至少一个非空 URL，避免 `check_source` 误判空发现规则。

---

## 七、验证清单

1. **本地 qjs / JS mock**：造 `infoMap` 与 `source.getVariable()` 桩，覆盖「收起/展开」「select 日/周/月/年」两态，断言 rows 数量、标题、URL 的 `period`。
2. **App `eval_js` 真源**：
   - 读 `source.exploreUrl` 求值，确认数组可解析。
   - 调折叠 action 后回读 `source.getVariable()`，确认 key 翻转且其它字段保留。
   - 若可调用 `java.refreshExplore()`，确认不抛异常。
3. **`check_source`**：必须 1/1；失败优先看「第一个非空 URL 是否存在」。
4. **`debug_source`**：用 `::URL` 直接调试一个展开后的子项入口，确认列表/详情/目录/正文链通。
5. **真机**：点折叠条、切 select，确认列表刷新；若「标签变了列表不变」，先查 action 是否在 `refreshExplore()` 前抛错。

---

## 八、相关文档

- `references/方法-发现页本源搜索框与可伸缩分组列表.md`：91Hub 本源搜索 + 折叠的原始实测。
- `references/方法-发现页select切换频道自动刷新UI的六种假象与真正根因.md`：select action 字符串类型与六种假象。
- `references/方法-发现页per-kind动态URL绕exploreKinds缓存.md`：动态 host / 请求时求值。
- `references/方法-禁漫天堂v2.6发现页全量榜单.md`：本模板在 jmtt v2.6~v2.12 的连续实战记录。
