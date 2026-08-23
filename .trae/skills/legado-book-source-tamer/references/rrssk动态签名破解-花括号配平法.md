# rrssk 动态签名破解 —— 花括号配平法提取签名函数

> 适用：rrssk.com 及其聚合家族站（kelexs/x630xsw/369shuba/qpmk/ishuku/菠萝猫等 24 站）的搜索接口

## 一、问题背景

rrssk 家族搜索接口 `POST /?action=search` 要求携带动态签名参数：

```
_t=<页面令牌>&_ts=<unix秒>&_s=<8位hex签名>&keyword=<关键词>
```

反爬演进过程：

| 阶段 | 机制 | 破解难度 |
|------|------|---------|
| v1 | AES-256-CBC 固定密钥加密 keyword（`?action=result` 接口） | 低 |
| v2 | 页面内联 JS 计算 `window.__SIGN`，可 eval 执行 | 中 |
| v3（当前） | 签名算法由服务端**每日下发**（`/?action=signJs&v=16-YYYYMMDD`），且**同一天内随机轮换多个算法变体**（变量名/常量/结构不同），并带浏览器环境检测 | 高 |

v3 的关键难点：
1. signJs 是 IIFE，内部先做环境指纹计算（`document.*` 检查求和，浏览器中=45）
2. 签名入口 `window["__"+"SIGN"]` 带环境检测：`if(_6a45c3!==45) return "00000000"` 和用户交互检测 `_8fc2ce!==1`
3. **真正有用的只有内层签名函数**（三参 `(s,t,ts)`，FNV 变体哈希 + 环境常量 XOR）
4. 固定正则提取会因变体轮换随机失败（变量名 `_6a45c3`/`_c90f24`/`inner` 等每次不同、嵌套结构不同）

## 二、破解思路

1. **不执行整个 signJs**（环境检测在 Legado 的 JS 引擎中必失败），只提取内层纯计算函数
2. 用**花括号配平法**代替固定正则：遍历所有 `function` 候选 → 数括号取完整函数体 → 按**结构特征**识别（函数体内同时含 `=function`、`slice(-8)`、`charCodeAt`）
3. **环境常量替换**：从整段 JS 的 `变量!==数字` 检查中，找出真正被签名函数引用的那个环境变量，把它的所有出现替换为要求的常量值（如 `_6a45c3` → `45`）
4. RFC3986 编码 keyword 后计算签名

## 三、核心代码（Legado searchUrl @js 内实测可用）

```javascript
// ===== 花括号配平法提取内层签名函数 =====
let cre = /function\s*[\w$]*\s*\(([^)]*)\)\s*\{/g, cm, fn = null;
while ((cm = cre.exec(res)) !== null) {
  if (cm[1].split(",").length < 3) continue;   // 签名函数固定三参(s,t,ts)，排除无参IIFE/单参回调
  let depth = 0, ci = cre.lastIndex - 1, cend = -1;
  for (; ci < res.length; ci++) {              // 花括号配平取完整函数体
    let ch = res.charAt(ci);
    if (ch === '{') depth++;
    else if (ch === '}') { depth--; if (!depth) { cend = ci; break; } }
  }
  if (cend < 0) continue;
  let body = res.substring(cm.index, cend + 1);
  // 结构特征识别：内含嵌套函数 + 8位hex截断 + charCodeAt哈希
  if (body.indexOf('=function') !== -1 && body.indexOf('slice(-8)') !== -1
      && body.indexOf('charCodeAt') !== -1) { fn = body; break; }
}
if (!fn) throw new Error('签名函数提取失败，站点可能已更新');

// 环境检测变量 → 常量（只替换被签名函数引用的那个，避免误替换交互标志变量）
let ere = /([\w$]+)!==(\d+)\)/g, em;
while ((em = ere.exec(res)) !== null) {
  if (fn.indexOf(em[1]) !== -1) { fn = fn.split(em[1]).join(em[2]); break; }
}
var q = eval('(' + fn + ')');

// ===== 签名与提交 =====
function enc(x){ return encodeURIComponent(String(x)).replace(/[!'()*]/g,
  function(c){ return '%' + c.charCodeAt(0).toString(16).toUpperCase(); }); } // RFC3986
var ts = Math.floor(Date.now() / 1000);
var s = q(enc(key), _t, ts);
let body = '_t=' + _t + '&_ts=' + ts + '&_s=' + s + '&keyword=' + enc(key);
// POST {baseHost}/?action=search 后取 Location 头即为结果页地址
```

## 四、验证数据

- 同日连续抓取 6 次 signJs，命中 6 个不同变体，提取+签名成功率 **6/6**
- 服务端校验通过（POST 返回 302 Location 指向 `?action=find&v=15&q=<加密串>`）
- 多关键词（剑来/诡秘之主/十日终焉/系统）全通过

## 五、要点与风险

| 要点 | 说明 |
|------|------|
| 三参过滤 | `cm[1].split(",").length < 3` 一行同时排除无参 IIFE 和事件回调，是防误匹配的关键 |
| 环境变量选择 | 必须校验 `fn.indexOf(em[1]) !== -1`——JS 里有两个 `!==数字` 检查（环境指纹45、交互标志1），替换错变量签名必错 |
| RFC3986 | 与 PHP `rawurlencode` 对齐，`!'()*` 六字符必须大写百分号编码，否则服务端校验失败 |
| 会话 | `_t` 与 PHP session 绑定，GET 中转页与 POST 必须同会话（Legado `enabledCookieJar:true` 自动处理） |
| 风险 | 算法结构大改（如不再输出 `slice(-8)` 特征）需更新特征串；每日轮换的只是变量名/常量，结构特征至今稳定 |
