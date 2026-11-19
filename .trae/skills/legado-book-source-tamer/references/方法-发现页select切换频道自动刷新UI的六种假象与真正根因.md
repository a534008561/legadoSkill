# 方法：发现页 select 切换频道后自动刷新 UI —— 六种假象与真正根因

> 来源：追书神器免费版书源 261119，v18d~v18j 连续 6 版排查。用户反馈"切换频道后下拉标签变了，但下面榜单/分类完全不变"，LT(legadoteam) 与 legado-E 两版都不行。
> 适用：所有用 `exploreUrl` 动态生成 select 频道切换的 Legado 书源/订阅源。
> 一句话结论：**`ExploreKind.action` 是单个字符串 `String?`，不是数组。action 写成数组会导致 GSON 解析失败，select 的刷新动作整个丢失——下拉值照变（框架自己写的），列表永不刷新。**

---

## 0. 现象（用户原话）

- "切换了频道之后没有自动刷新发现页"
- "只有下拉标签那里变了，下面的榜单子分类之类的全部没变"
- "E、LT 版，都是没有变"

这个现象组合极其特征：**下拉值变 = infoMap 被框架写入了；列表不变 = action 没执行**。

---

## 1. 源码级机制（LT 与 E 版相同）

### 1.1 ExploreKind 数据模型（决定性）

`app/src/main/java/io/legado/app/data/entities/rule/ExploreKind.kt`：
```kotlin
data class ExploreKind(
    val title: String = "",
    val url: String? = null,
    val type: String = "url",
    val action: String? = null,          // ★★单个字符串！
    val chars: Array<String?>? = null,   // chars 才是数组
    val default: String? = null,
    var viewName: String? = null,
    val style: FlexChildStyle? = null
)
```

**`action: String?` —— 必须是单个字符串。**

### 1.2 select 点击处理（ExploreAdapter.kt）

```kotlin
Type.select -> {
    ...
    val infoV = infoMap[title]
    val char = if (infoV.isNullOrEmpty()) {
        (kind.default ?: chars[0]).also { infoMap[title] = it }
    } else infoV
    ...
    selector.onItemSelectedListener = object : OnItemSelectedListener {
        var isInitializing = true
        override fun onItemSelected(...) {
            if (isInitializing) { isInitializing = false; return }
            infoMap[title] = chars[position]        // ★框架自动写选中值到 infoMap
            if (kind.action != null) {
                callBack.scope.launch(IO) {
                    evalButtonClick(kind.action, source, infoMap, title, sourceJsExtensions)
                }
            }
        }
    }
}
```

三条铁律：
1. **框架自动写 `infoMap[title]=选中值`**，与 action 无关 ⇒ 即使 action 完全失效，下拉标签也会变。
2. action 是"点击后额外要做的事"，本场景唯一要做的就是 `java.refreshExplore()`。
3. `evalButtonClick` = `source.evalJS(jsStr){ put("java",java); put("infoMap",infoMap) }`。

### 1.3 refreshExplore 链路（有效，不用怀疑）

```
java.refreshExplore()
  → SourceLoginJsExtensions.refreshExplore() = callbackRef.get()?.reUiView()
  → ExploreAdapter.refreshExplore(item, exIndex, binding)
  → source.clearExploreKindsCache()   // aCache 文件 + exploreKindsMap 内存双清
  → source.exploreKinds()             // 重新求值 exploreUrl
  → upKindList()                      // 重绘控件
```

`clearExploreKindsCache()` 确实同时清两级缓存，`exploreKinds()` 的缓存 key = `md5(bookSourceUrl + exploreUrl)`。**这条链路本身没问题，不要在这里浪费时间。**

---

## 2. 真正根因

追书神器从 v17 起生成 select 的代码是：

```js
function act(v){ ... return '(function(){...})()'; }
var ca=[]; for(var i=0;i<chans.length;i++) ca.push(act(chans[i]));
out.push({title:'频道',type:'select',chars:chans,default:g,action:ca});   // ★★★ action 是数组
```

GSON 反序列化 `["...","..."]` 到 `val action: String?` → `Expected a string but was BEGIN_ARRAY` → 解析失败 → **select 的 action 丢失**。

对照 rrssk 聚合源（长期验证有效）：
```js
push('域名', '', 1, 1, {
  "type": "select",
  "chars": hosts,
  "default": GET('server') || hosts[0],
  "action": "SET('server', infoMap['域名']); java.refreshExplore()"   // ★单字符串
});
```

**这就是全部根因**。下拉变（框架写 infoMap）+ 列表不变（action 从未被解析）完全吻合。

---

## 3. 正解（最小修复）

```js
var chans=['男生','女生','出版','阅文好书','17K好书'];
var chanAction='java.refreshExplore();';   // 单字符串；框架已写 infoMap['频道']，action 无需写值
out.push({title:'频道',type:'select',chars:chans,default:g,action:chanAction});
```

同时 exploreUrl 求值开头直接读框架写入的值：
```js
var im=infoMap||{};
var g=String(im['频道']||'男生');
```

不需要 `java.put`、不需要 `source.putVariable`、不需要 jsLib 的 SET/GET、不需要多个 action。**一个字符串 `java.refreshExplore()` 足矣。**

---

## 4. 六种假象（我踩过的坑，逐一排除）

排查过程中先后怀疑并"验证通过"过 6 种错误方向，全部不是根因。列出供后来者避坑：

| # | 假象/错误方向 | 为什么看似合理 | 为什么错 |
|---|---|---|---|
| 1 | 频道值没持久化，live infoMap 进程级缓存滞后 | rrssk 经验里确有 live infoMap 缓存说法 | 框架 select 点击必写 `infoMap[title]`，本场景读的就是它；"缓存滞后"是别的场景 |
| 2 | action 里没写 `java.put`/`source.putVariable` 存频道 | 以为要自己存值 | 框架已写 infoMap；写值语句在 action 环境还会抛错带崩后续 refresh |
| 3 | action 环境无 source 绑定，`source.putVariable` 静默失败 | 确实无 source（真） | 但根本不需要 source；且这是第 2 条的衍生 |
| 4 | action 环境的 java 是假对象，`java.put` 报"put 不是函数" | 真机探针确实复现 | 但你根本不该在 action 里 put；真正问题是 action 根本没被解析 |
| 5 | jsLib 的 `this.source` 通道才能写值 | rrssk SET 确实这么干 | 那是 rrssk 的"选服务器"场景；本场景无需持久化，且 action 是数组时一切都白搭 |
| 6 | action 前序写值语句抛错带崩 refreshExplore | 逻辑上成立 | 前提错误：action 是数组时压根没有可执行 action；把 action 内容改来改去全无效 |

**共同教训**：6 版都在改 action 的**内容**，从未检查 action 的**字段类型**。用 eval_js 自证"通过"更糟——eval_js 直接读 JS 对象，绕过了 GSON 反序列化这一层，所以 `action` 是数组也能跑，恰恰掩盖了真机解析失败。

---

## 5. 验证铁律（必做）

### 5.1 dump 字段类型对照 data class
```js
var sel=JSON.parse(eval(exploreUrlBody))[0];
// 正确：typeof action === 'string' && !Array.isArray(action)
// 错误：typeof action === 'object' && Array.isArray(action)
```
**任何控件"显示对但行为不触发"，第一优先是 dump 控件对象字段类型，逐字段对照 `ExploreKind.kt`。** 不是猜执行环境、不是猜缓存。

### 5.2 真机 GSON 链路意识
eval_js 里 `eval(exploreUrl)` 得到的是 JS 对象，**绕过了 GSON**。真机必经 `GSON.fromJsonArray<ExploreKind>(ruleStr)`。凡是字段类型不符（数组给 String?、对象给 String、数字给 Boolean），eval_js 全绿而真机失效。

### 5.3 若真要验证 action 执行（进阶）
用 `source.evalJS(actionStr, {java: java, infoMap: im})` 模拟 `evalButtonClick`，不要用裸 `eval(actionStr)`——裸 eval 的全量绑定会掩盖 action 环境的假绑定问题。但**先做 5.1**，否则你验证的 action 可能根本没被真机加载。

---

## 6. 照抄范式的正确姿势

用户说"参考 rrssk 聚合源"时，正确做法是**逐字段对照**，而不是只看"大概意思"：

| 字段 | rrssk | 错误照抄 | 正确 |
|---|---|---|---|
| type | `"select"` | `"select"` | `"select"` |
| chars | 数组 `hosts` | 数组 `chans` | 数组 `chans` ✅ |
| default | 单值字符串 | 单值 `g` | 单值 `g` ✅ |
| **action** | **单字符串** | **数组 `ca`** ❌ | **单字符串 `'java.refreshExplore();'`** ✅ |

**逐字段核对类型，是"参考成熟源"的唯一可靠方式。**

---

## 7. 完整检查清单（发现页 select 不刷新时）

1. [ ] `JSON.parse(eval(exploreUrl))` 后，select 项 `typeof action === 'string'`？（最常见死因）
2. [ ] `chars` 是数组、`default` 是字符串、`type==='select'`？
3. [ ] action 内容极简，只有 `java.refreshExplore();`，无任何可能抛错的前序写值？
4. [ ] exploreUrl 开头读 `infoMap['频道']`（框架写入），而不是 java.get/source 变量？
5. [ ] 用真机 GSON 解析路径验证，而非仅 eval_js？
6. [ ] 若仍不行，再查 `clearExploreKindsCache`/`exploreKinds` 链路（本场景已证明有效，通常不是它）？

---

## 8. 交付记录（追书神器 v18j）

- 修正后 select.action 从数组变为单字符串 `java.refreshExplore()`，与 rrssk 同构。
- 真机验证 `typeof action=string, isArray=false`。
- LT(1122) + E(1125) 双端 LAN `saveBookSource` isSuccess=true。
- 配套经验：前面 v18b(jsLib ajax)、v18c(token 限流缓存)、v18d(HTML 分支字段名)、v18e(板块 alias)、v18f~i(action 各种错误方向) 的记录见 `/areas/zhuishushenqi-book-source.md`。
