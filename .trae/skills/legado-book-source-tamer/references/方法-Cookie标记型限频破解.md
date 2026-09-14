# 方法：Cookie 标记型限频破解
## ——笔趣阁系(qsskel)/思思CMS/PTcms 通用：一个 Cookie 键就能骗过的搜索频控

> 沉淀日期：2026-09-14　｜　来源：ppxsw.cc、book630.org、xuken.net、lianaiya.com、ggd66.com、35sw.org 共 **6 个生产源同款机制**
> 关联：[方法-WAF与CF间歇故障及站点判活](方法-WAF与CF间歇故障及站点判活.md)、[方法-静默失败定位与探针法](方法-静默失败定位与探针法.md)

---

## 目录

1. [三类限频的鉴别决策树](#一三类限频的鉴别决策树)
2. [Cookie 标记型的原理：服务端只看键存不存在](#二cookie-标记型的原理服务端只看键存不存在)
3. [标准破解：searchUrl 前置删键 JS](#三标准破解searchurl-前置删键-js)
4. [★cookie.setCookie 是整体替换语义](#-cookiesetcookie-是整体替换语义)
5. [本 App 的 Cookie API 可用性清单](#五本-app-的-cookie-api-可用性清单)
6. [第二层：IP 级惩罚窗口（删 Cookie 也没用的时候）](#六第二层ip-级惩罚窗口删-cookie-也没用的时候)
7. [把倒计时透传给用户：loginCheckJs 兜底](#七把倒计时透传给用户logincheckjs-兜底)
8. [POST 与 GET 的差异坑](#八post-与-get-的差异坑)
9. [六站档案对照表](#九六站档案对照表)
10. [验证方法论](#十验证方法论)
11. [避坑清单](#十一避坑清单)

---

## 一、三类限频的鉴别决策树

拿到"搜索被拒/请 XX 秒后再搜索"，先分类再动手：

```
被拒后，清掉 Cookie 再搜一次：
├─ 立即放行 ────────────────► ★Cookie 标记型  ← 本篇主角，5 分钟可破
└─ 仍然被拒：
   静默等待，等到提示里的倒计时走完：
   ├─ 放行 ────────────────► 时间窗口型（服务端记 session/IP 时间戳）
   │                          对策：换随机 PHPSESSID（35sw 会话级）或只能等（IP 级）
   └─ 仍然被拒（甚至越等越久）─► ★IP 级惩罚型
                              对策：唯一办法是完全静默；失败请求本身也会刷新窗口
```

**判定实验（一次做完，别反复撞）**：

| 实验 | 操作 | 结论 |
|---|---|---|
| A | 被拒 → 删该 Cookie 键 → 立即搜 | 放行 = 标记型 |
| B | 被拒 → 干等倒计时结束 → 搜 | 放行 = 时间窗口型 |
| C | 被拒 → 等 10 分钟 → 搜 | 放行 = 短时 IP 惩罚 |
| D | 换全新 PHPSESSID → 搜 | 放行 = 会话级；仍拒 = IP 级 |

> 35sw 是 **B+D 双级**（会话级 60 秒 + IP 级长惩罚）；ppxsw/xuken/book630/ggd66 是纯 A（标记型）。**先做 A 最省事**，一次就定性。

---

## 二、Cookie 标记型的原理：服务端只看键存不存在

这是全系列（qsskel 系 `search_time`、思思CMS `ss_search_delay`）**共同的实现缺陷**：

```
第一次成功搜索 → 响应 Set-Cookie: search_time=1; Max-Age=120
下一次搜索     → 服务端检查【请求里有没有 search_time 这个键】
                 有 → 直接拒（返回 12 条推荐书 + 倒计时文案）
                 无 → 放行，并再次下发
★ 服务端从不更新该值，也从不校验它的值和时间戳
```

**三个必然后果**（全部实测过）：

1. 值是什么无所谓（`1`、时间戳、乱码都算存在）；
2. `Max-Age` 只影响浏览器自动删除，**干等/重试均无效**——倒计时提示只是装饰；
3. **每次尝试都会重新下发并重置倒计时**，所以撞得越勤越看不到头（ppxsw 实测：每次尝试重置 ~120s）。

→ 结论：**只要请求里不带这个键，服务端就当你是第一次搜索。永久绕过。**

---

## 三、标准破解：searchUrl 前置删键 JS

写法：把删除逻辑作为 `searchUrl` 的**前置 JS 段**（`<js>…</js>` 或 `@js:` 视字段而定），每次搜索前自愈。

```javascript
<js>
var Q = String.fromCharCode(34);
var url = 'https://www.ppxsw.cc/search.html';
try {
  var ck = String(java.getCookie() || '');
  if (ck.indexOf('search_time') >= 0) {
    var keep = [];
    var parts = ck.split(';');
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i].trim();
      if (!p) { continue; }
      if (p.split('=')[0].trim() !== 'search_time') { keep.push(p); }
    }
    java.setCookie(url, keep.join('; '));      // ★整体回写，见第四节
  }
} catch (e) { java.log('del search_time fail: ' + e); }
url + ',s={{key}}';
</js>
```

要点：

- **必须 try/catch**：任何改版（`java.setCookie` 缺失等）都不能让搜索整体崩掉，静默降级为"受限但可用"。
- 删完要把**其余键原样回写**，否则会连带删掉登录会话（ppxsw 的搜索**必须登录**，清错一次就要重登）。
- ggd66 的键名是 `ss_search_delay`，值是常量 `1`，`Max-Age=30s`；同理剔除即可，实测连搜 4 次无 IP 级惩罚。
- `searchUrl` 用 `{{}}` 模板产 URL，**不要整条 `@js:`**——`@js:` 在 `searchUrl` 上会**静默失败**（"获取成功"日志消失、URL 被当相对路径解析成 `https://api/...`）。若必须用 JS 产 URL，用 `<js>…</js>` 并确保最后一条表达式是完整 URL 字符串。

### 变体：把逻辑放 header 里

有些版本 `searchUrl` 前置 JS 不便拼 body，可改在 `header` 的 JS 里做（header 支持 `{{}}`）：

```json
"header": "{\"User-Agent\":\"...\",\"Cookie\":\"{{java.getCookie().replace('search_time=1','')}}\"}"
```

不推荐：`replace` 只删一个匹配、且无法处理键在中间时的 `; ;` 残留。**首选第三节的显式切分回写法。**

---

## 四、★cookie.setCookie 是整体替换语义

这是皮皮小说那次最贵的教训（memory 里标了"巨坑"）：

```javascript
cookie.setCookie(url, 'a=1')   // ✗ 不是"加一个 a"，是把该 URL 持久层 Cookie 全换成 a=1
                               //   → 登录会话 Cookie 一起没了
```

**改单键的唯一正确姿势 = 读全文 → 改 → 回写全文。**

```javascript
var all = String(cookie.getCookie(url) || '');   // 只读整域（库 + 会话层合并）
// 用 split(';') 显式过滤，不要用正则替换（值不定的键会漏）
cookie.setCookie(url, newAll);
```

两个补充事实：

- `cookie.removeCookie(url)` = **删整域**（含 WebView 层，危险，别用）；
- `cookie.removeCookie(url, key)` 两参签名在 **LegadoTeam 版报"找不到方法"**（ggd66 实测）；但 `removeCookie(url, key)` 在别的版本/上下文有实现——**API 存在性必须在真实调用上下文实测**，别信单一环境 `typeof` 探测（见[版本差异篇](方法-legado各版本行为差异对照.md)）。
- 本 App（LT 版）**没有** `java.setCookie`，只有 `java.getCookie()` + `cookie.setCookie(url, str)` 配对。ggd66 即用此配对。

---

## 五、本 App 的 Cookie API 可用性清单

| API | LT 版 | 备注 |
|---|---|---|
| `java.getCookie()` | ✅ | 读当前请求上下文相关 Cookie 串 |
| `cookie.getCookie(url)` | ✅ | 整域（持久 + 会话合并） |
| `cookie.setCookie(url, str)` | ✅ | **整体替换**该域持久层 |
| `cookie.removeCookie(url)` | ✅ | 删整域（含 WebView），**危险** |
| `cookie.removeCookie(url, key)` | ❌ 找不到方法 | 只能 get+set 配对 |
| `java.setCookie(...)` | ❌ 无 | — |
| `java.getCookieString(url)` | ✅ | 备用读法 |
| `source.putLoginHeader(json)` | ✅ | 登录成功后持久化登录头 |

> 规则 JS 上下文里 `cookie` 绑定确实存在（官方 `AnalyzeUrl` bindings[`"cookie"`] = `CookieStore`），`eval_js` 独立环境探测为 `undefined` **不代表规则里不能用**。

---

## 六、第二层：IP 级惩罚窗口（删 Cookie 也没用的时候）

标记型破了之后，**仍可能**因"请求频率/失败次数"被 IP 级拉黑。三种实测形态：

| 站点 | 形态 | 表现 | 恢复 |
|---|---|---|---|
| ppxsw | 每次尝试重置倒计时 | 120s 起，反复撞无限续 | 停手 1 次到位 |
| xuken | TCP RST 累计惩罚 | `ERR_CONNECTION_RESET`，可累计 **1.5h+** | 完全静默；删 Cookie 无效 |
| 35sw | IP 级长惩罚 | 持续数分钟甚至更久 | 实测 10 分钟完全静默可解封 |
| lianaiya | 接口频控 | 搜索接口拒答 | 降频 + `select` 上限 |

**通用对策**：

1. `concurrentRate` 收紧（如 `"1/1000"`，格式=次数/毫秒，源码 `ConcurrentRateLimiter` 确认；77shuku 用 `"2/1000"`）；
2. 全链路 URL 选项 `"retry":3`（官方 `AnalyzeUrl.getRetry` 原生支持）——但 **POST + retry 会撞 `oneShot` 坑**（见第八节），GET 才有效；
3. **排查期最忌"边验边撞"**：debug 循环（改规则→搜索→失败→再搜）会把自己 IP 打进长惩罚期，之后连正确规则都验不了。35sw 那次因此改用**离线法**：`eval_js` 里嵌入真实结果页 HTML + `new AnalyzeRule().setContent` → `getElements`/`getString` 模拟 `BookList` 全流程，**完全不消耗搜索配额**。
4. `debug_source` 页间连抓 9 页会触发封锁 → 页间 ≥1.5s，或分次跑。

---

## 七、把倒计时透传给用户：loginCheckJs 兜底

删 Cookie 是"尽最大努力"，仍可能因 IP 级被拒。**必须把静默 0 结果变成明确报错**，否则用户以为源坏了。

`loginCheckJs` 是**每次请求后的响应拦截器**（搜索/发现/详情/目录/正文 5 处都跑），`result` 是 `StrResponse`，**必须原样 return**：

```javascript<js>
(function () {
  var body = '';
  try {
    var b = result.body;                       // ★LT 版可能是属性
    if (typeof b === 'function') { b = b.call(result); }   // ★部分改版是方法
    body = String(b || '');
  } catch (e) { body = ''; }
  if (body.indexOf('两次搜索的间隔时间不得少于') >= 0
      || body.indexOf('后再进行搜索') >= 0
      || body.indexOf('搜索间隔') >= 0) {
    throw new Error('⏳ 站点搜索限频，请 60 秒后再试（连续失败会延长冷却，请勿反复重试）');
  }
  return result;
})();
</js>
```

四条硬约束（全部踩过）：

1. **不能顶层 `return`**——`loginCheckJs` 按**表达式**解析，必须 IIFE 包裹；
2. `result.body` 在 LT 版若写成属性访问，某些 build 返回的是**方法引用**（`typeof === 'function'`），必须双通道；写成 `result.body || ''` 会**静默失配** → 0 结果或诡异 NPE；
3. `throw` 必须是 `throw new Error(msg)`；`throw '串'` 表现不一致；
4. 抛错能正常传播到 `Debug.onError` 显示，用户侧也会看到——这是"把没结果变成原因"的正规手段。

---

## 八、POST 与 GET 的差异坑

| 项 | GET | POST |
|---|---|---|
| `"retry":3` | ✅ 正常重试 | ❌ **`oneShot` 报错**（OkHttp `RequestBody` 不可 rewind）→ 不是真重试 |
| 参数编码 | `{{key}}` 直接进 query | 见下 |
| charset | 默认 | URL 选项里显式 `"charset":"gbk"`；GBK 站服务端常**不 urldecode POST body**，必须 `s={{key}}` 原文 + charset（m.lzjxx 实锤） |

POST 搜索的重试需求，改用「前置 JS 里先探测再放行」或干脆提高 `concurrentRate` 的容忍度，别指望 `retry`。

---

## 九、六站档案对照表

| 站点 | 键名 | 窗口 | 触发接口 | 破法 | 二次惩罚 |
|---|---|---|---|---|---|
| www.ppxsw.cc | `search_time` | 值恒为 1，提示 ~120s | `POST /search.html` s= | searchUrl 前置删键 | 每次尝试重置 |
| book630.org | `search_time` | 20 秒 | `POST /search.html` s=（**须登录**） | 同上 | 轻微 |
| xuken.net | `search_time` | 提示文案同族 | `POST` s=（UA 决定 PC/移动模板） | 删键 + `retry:3` | **TCP RST 累计 1.5h+** |
| www.ggd66.com | `ss_search_delay` | 30s，`Max-Age=30` | `GET /search/?searchkey=` 或 `POST /search/` | `<js>` 内 getCookie→split→剔除→setCookie | 实测无 |
| lianaiya.com | WAF 挑战 Cookie（**非频控**） | token ~5 分钟过期 | `/sdfgsdyugfsdugf.html?s=…&q=`（实为 UTF-8） | 需维持 `waf_challenge`，见 WAF 篇 | 接口限频 |
| 35sw.org | 无 Cookie 标记，**纯时间窗口** | 60 秒 × 会话 + IP | `POST /novelsearch/search/result.html` | 每次生成全新随机 `PHPSESSID` + 静默策略 | 长，需 10min 静默 |

> 最后一行是**反例**：不是标记型，删 Cookie 没用，必须换会话标识。放进表里是为了提醒：**先鉴别再动手**。

---

## 十、验证方法论

1. **先定性**：做第一节的 A/B/C/D 四个实验，一步定位类别；
2. **改前基线**：记录"受限时的推荐书数"（ppxsw 是 12 条），改后应变成真实结果数（50 条）；
3. **连搜验证**：删键后连续搜 4 次，观察是否出现 IP 级惩罚（全过 = 该站只查标记）；
4. **回归登录态**：删键后确认仍处登录（检查响应里有没有登录页 302 / 未登录文案）；
5. **`check_source` 复核**：官方校验器会自己搜一次，通过说明前置 JS 在无会话的干净环境下也成立；
6. **别只看 `已保存`**：改完必须 `get_source` 回读 + 字段 md5 比对，见[交付质量闭环](方法-书源交付质量闭环.md)。

---

## 十一、避坑清单

| # | 坑 | 后果 | 对策 |
|---|---|---|---|
| 1 | 当成时间窗口型去干等 | 永远等不到，倒计时无限续 | 先做删 Cookie 实验定性 |
| 2 | `setCookie` 当"追加"用 | 登录会话被清 → 搜索 302 | 读全文→改→回写全文 |
| 3 | `cookie.removeCookie(url)` 清整域 | 连带删掉必需的会话/配对键 | 只删单键（get+set 配对） |
| 4 | `replace('k=1','')` 删键 | 只删首个匹配 / 值不定漏删 | `split(';')` 显式过滤 |
| 5 | 删键 JS 不 try/catch | 整个搜索崩 | 必包 try/catch |
| 6 | `searchUrl` 整条 `@js:` | **静默**降级成相对路径 | 用 `<js>…</js>` 或 `{{}}` 模板 |
| 7 | `loginCheckJs` 顶层 `return` | 规则不生效 | IIFE 包裹 |
| 8 | `result.body` 当属性取值 | 静默失配 → 诡异 0 结果 | `typeof` 双通道 |
| 9 | 排查期高频撞 | 自己 IP 打进长惩罚 | 离线 AnalyzeRule 模拟验证 |
| 10 | POST + `retry:3` | `oneShot` 假重试 | GET 才用 retry；POST 降频 |
| 11 | 把 lianaiya 的 WAF Cookie 当频控删 | 挑战态丢失 → 503 | 见 WAF 篇，两类不同 |

---

## 附：一段可直接抄的最小实现

```javascript
// 通用"删标记键"工具（把 KEY 换成站点键名）
function stripCk(url, KEY) {
  try {
    var all = String(java.getCookie() || '');
    if (all.indexOf(KEY) < 0) { return; }
    var keep = [], ps = all.split(';'), i, p;
    for (i = 0; i < ps.length; i++) {
      p = ps[i].trim();
      if (p && p.split('=')[0].trim() !== KEY) { keep.push(p); }
    }
    java.setCookie(url, keep.join('; '));
  } catch (e) { try { java.log('stripCk: ' + e); } catch (e2) {} }
}
```

> 注：`java.setCookie` 在 LT 版不存在 → 生产源里请把它换成 `cookie.setCookie(url, str)`，或直接内联展开（jsLib 作用域里 `java`/`source` 本身就受限，网络与 Cookie 操作**必须内联在各规则的 `@js` 里**——这是本 App 的普遍规律，见[版本差异篇](方法-legado各版本行为差异对照.md)）。
