# 番茄小说「纯 APP 接口」书源（+ legado-E 兼容）

> **书源**：`🍅番茄小说(APP)` · `https://fanqienovel.com`
> **状态**：`check_source` 通过 1/1 · 全链路 debug 实测 · 发现页 **29 入口** · **LT / E 双版本兼容**

## 一、这是什么

**完全不碰网页版**（网页版有字体反爬），全程走官方 App 私有接口，并在 Legado 的 Rhino 内**纯 JS 复现字节系三大签名**：

| 环节 | 接口 | 是否需签名 |
|---|---|---|
| 搜索 | `api.fanqiesdk.com/api/novel/channel/homepage/search/search/v1/` | ❌ 免签 |
| 详情 + 目录 | `api5-normal-sinfonlineb.fqnovel.com/reading/bookapi/directory/all_items/v` | ✅ |
| 榜单 / 分类榜 | `.../reading/bookapi/bookmall/cell/change/v1/` | ✅ |
| 频道 tab | `.../reading/bookapi/bookmall/tab/v` | ✅ |
| **正文** | `novelfm-hl.snssdk.com/novelfm/playerapi/full/mget/v1/` | ✅ + DH 解密 |
| 设备注册 | `log.snssdk.com/service/2/device_register/` | ttEnc |

## 二、三项核心技术

### 1. x-argus（SIMON-128 + 手写 protobuf）
`pad → SIMON-128-ECB(72轮) → magic8 xor → reverse → "ao" → pad → AES-128-CBC-NoPadding → base64`

★ **两个必坑**：Bean 的 `version_name` 必须从 query 实时提取（硬编码会 verify fail）；
手工 pad 后**必须用 NoPadding**（用 PKCS5 会多补 16 字节被服务端拒绝）。

### 2. CM 通道正文解密（3072 位 MODP DH）
```
pk  = random(256) % (P-1)
pub = 2^pk mod P
key = b64(iv + AES-128-CBC-PKCS5(pubBytes, REQ_KEY, iv))
shared = srv^pk mod P
aesKey = sharedBytes[:32]           ← ★ 去前导零后取前 32 字节
plain = AES-256-CBC(ct, aesKey, iv) → String(...,"UTF-8")
```

### 3. legado-E 兼容（BouncyCastle 不可用）
E 版 R8 裁剪后 `Packages.org.bouncycastle...SM3.Digest` 返回的是 **JavaPackage 对象**，调用即
`TypeError: ... 不是函数，它是 object`。

解法 = **把密码学全部改成纯 JS**：
- `FQ_sm3` — 纯 JS SM3（已验 3 个国密标准向量：`abc` / 空串 / 512 位）
- `FQ_b64eJS` / `FQ_b64dJS` — 纯 JS Base64，与 `java.util.Base64` 组成**双通道兜底**
- 依赖审计：正则抓出全部 `Packages.*` 后逐个 `typeof` 探测，分成「高风险 / 安全」两类

## 三、Legado 环境五大坑

1. **jsLib 作用域 `java.*` 全部不可用** → 只能用 `Packages.*`，或把 `java` 作参数传进函数
2. **`Packages.android.util.Base64.decode` 返回全零**（坏实现）→ 用 `Packages.java.util.Base64.getDecoder()`
3. **byte[] → JS 字符串** 必须 `new Packages.java.lang.String(b, Charset.forName('ISO-8859-1'))`；
   用 `b[i]&255` 循环逐字节会**失真**（hex 差 1）
4. **`@js:` 顶层不能 `return`** → 一律 IIFE 包裹，否则报「返回的值无效」
5. **bookUrl 分隔符必须单 `#`**；`exploreUrl` 必须**真实可请求**，否则 check_source 报「发现目录失效」

## 四、发现页分类体系（29 入口）

```
📊 排行榜  → 🔥推荐榜 🏆完本榜 👑巅峰榜 💬口碑榜
📚 分类榜  → 🌀穿越 🎯系统 🏙都市 💕现代言情 ⚔️玄幻 🏮古代言情 ♻️重生 🏛架空
             🌏东方玄幻 👊打脸 🧚奇幻仙侠 🌆都市脑洞 🚀科幻末世 🧠玄幻脑洞 🎭衍生
📖 频道    → ✨推荐 📜经典 🎓知识 📄短篇 🖼漫画
🏠 首页    → 🎁首页精选
```

- **16 个分类 ID**：`37穿越/19系统/1都市/3现代言情/7玄幻/5古代言情/36重生/452架空/511东方玄幻/522打脸/259奇幻仙侠/262都市脑洞/8科幻末世/257玄幻脑洞/1079衍生/0全部`
- **4 个榜单**：`101推荐/100完本/200巅峰/104口碑`
- **频道 tab 真实 ID（非顺序索引）**：`2推荐/11经典/12知识/5听书/8看剧/16视频/103短篇/9漫画/15买书`

**实现模式**：`exploreUrl` 写 `标题::https://fanqienovel.com?t=rank&cat=37&algo=101`，
`ruleExplore.bookList` 一个函数按 `t=` / `tt=` 参数分发；
**分组标题用「标题::」空 URL** → Legado 渲染成不可点击的标题行。

## 五、性能

| 操作 | 耗时 |
|---|---|
| 搜索（10 条） | 0.4 s |
| 详情（含目录请求） | 1.0 s |
| 目录 1496 章 | 0.8 s |
| 正文 3486 字（含 DH） | 1.5 s |
| 发现页 16 本 | 2.0 s |

## 六、已知限制

- **听书 / 看剧 / 视频 / 买书** 频道返回空 —— 需专门的 audio/video 接口，未适配
- **漫画**频道正文是图片 JSON（`materials.img_N.data.web_uri`，`aes-256-gcm` 加密图），需图床拼装，未适配
- 设备池存于 `source.put('fqPool', ...)`，建议保留 2~3 个设备轮换

## 七、文件

- 成品：`番茄小说_APP版_www.fanqienovel.com.json`（36 KB，格式化）/ `_one.json`（单行，导入用）
- 方法：`references/方法-字节系App全签名复现与DH解密通道.md`（18 KB / 13 章 / K1~K26）
