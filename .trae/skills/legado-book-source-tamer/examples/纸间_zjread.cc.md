# 纸间（zjread.cc）· 全加密 API 书源案例

> 拆解日期：2026-10-09　｜　站点：https://www.zjread.cc　｜　类型：`bookSourceType=0` 小说
> 关联方法论文档：[方法-全加密API书源逆向与客户端可信重放](../references/方法-全加密API书源逆向与客户端可信重放.md)

---

## 一、三句话总结

1. **全站业务 API 走 AES-256-GCM 加密 + HMAC 五头签名**，唯一的明文接口是 `GET /api/bootstrap`（握手，下发 `session_id` + `key_material`）。
2. **正文额外走「章节级密钥」**：服务端在响应里回传 `key_mode:"chapter"` + `book_id/chapter_id`，客户端用 HKDF 从 `key_material` **本地重派生**解密密钥——**密钥不落盘、不传输**。
3. **人机验证是 ALTCHA PoW**（challenge 参数明文），书源侧**本地求解 ~1.2 秒**自助换取 `captcha_token`，**无需人工**。

---

## 二、站点档案

| 项 | 值 |
|---|---|
| 域名 | `https://www.zjread.cc` |
| 编码 | UTF-8（内容**繁体**，源站为 qidian 等） |
| 反爬 | 全站 API 加密 + 签名 + ALTCHA 人机验证 |
| 登录 | **不需要**（全部接口匿名可用） |
| Cookie | 不需要（`enabledCookieJar=false`） |
| 封面 | 独立加密通道（本地生成加密 URL） |
| 分页 | 搜索接口支持 `page` 参数 |
| 章内分页 | 无（单章单请求） |

### 两个并存源

| | A「纸间」 | B「zjread（纸间）」 |
|---|---|---|
| `bookSourceUrl` | `https://www.zjread.cc` | `https://www.zjread.cc##` |
| 发现页 | ✅ 16 分类 | ❌ |
| 繁转简 | ✅（`java.t2s`） | ❌（繁体直出） |
| `updateTime` | ❌ | ✅ |
| `bookSourceComment` | ❌ | ✅ 协议说明 |
| 缓存隔离 | `v_..._cc_...` | `v_..._cc##_...`（天然隔离） |

---

## 三、协议全貌（实测）

```
【握手】GET /api/bootstrap  ← 唯一明文接口
        → {"code":0,"data":{
             "expires_at":1791497768,                    # TTL 6 小时
             "key_id":"v1",
             "key_material":"PScb4ldCPLHBsjjbXvNPG1Vuxk1R1ivfoR70uRYPmY0=",  # 32B
             "session_id":"0aziA2frsHU6rX5pogAXzbtQf1y70Igx"}}              # 32 字符

【派生】HKDF-Expand 单轮，L=32
        会话：PRK = HMAC(key=sid_bytes, msg=km)
              aesKey  = HMAC(key=PRK, msg="novel-api-aes-v1" || 0x01)
              hmacKey = HMAC(key=PRK, msg="novel-hmac-v1"    || 0x01)
        章节：PRK = HMAC(key=ikm, msg=km)
              ck      = HMAC(key=PRK, msg="novel-chapter-aes-v1" || 0x01)
              ikm = hexDecode(hex(bid+"\n"+cid+"\n"+ver) + hex(nonce))   # ★双层 hex

【请求体】{"version":1,"algorithm":"AES-256-GCM","data":b64,"nonce":b64(12B)}
【请求头】X-Session-ID / X-Timestamp / X-Nonce / X-Signature / X-Key-Version
          X-Signature = b64(HMAC-SHA256(hmacKey,
                          "POST\n{path}\n{ts}\n{nonce}\n{sha256hex(body)}\n{sid}"))

【响应】{"version":1,"algorithm":"AES-256-GCM","data":..,"nonce":..,
         "key_mode":"session"|"chapter",
         "book_id":..,"chapter_id":..,     # 仅 chapter 模式
         "code":0,"message":..}

【人机】GET  /api/captcha/altcha/challenge → 明文 challenge
        PoW 本地求解 → POST /api/captcha/altcha/verify {payload: b64(...)}
        → captcha_token（300 秒有效）

【封面】GET /api/cover?session_id=..&data=b64url(GCM(JSON{book_id,size}))&nonce=b64url
```

### 四个业务接口

| 接口 | 参数 | key_mode |
|---|---|---|
| `/api/search` | `{keyword, page}` | session |
| `/api/book/detail` | `{book_id}` | session |
| `/api/book/catalog` | `{book_id}` | session |
| `/api/book/content` | `{chapter_id, captcha_token}` | **chapter** |

---

## 四、关键实测数据

### 4.1 破坏性单变量实验（11 组）

| 篡改项 | 结果 |
|---|---|
| baseline | 200 ✔ |
| `X-Signature` 改全 A / 删除 | **401** |
| `X-Nonce` 改值 | **401** |
| `X-Timestamp` 改值 / ±300s / -3600s | **401** |
| `X-Session-ID` 改值 | **401** |
| `X-Key-Version` = "2" / "0" | **401** |

⇒ **全字段强校验，时间戳容差 < 300 秒**。

### 4.2 密钥派生逐字节对比

```
会话 aesKey（手工复现 vs jsLib）：
  2bd2e7919ddb56badbbd0d15d18f876921a1257336c983a54a89659325118484  ==  ✔

章节 chapterKey（手工复现 vs jsLib）：
  aed4a28c9354c4960eb5a81411da96155cc6c54557b77d77d21af1091557525e  ==  ✔
  ikm 长度 = 53+1+64+1+1+12 = 132 字节 ✔
```

### 4.3 key_mode 降级（★重要）

| 场景 | key_mode | 响应含 book_id/chapter_id | code |
|---|---|---|---|
| 正文 + 有效 captcha_token | `chapter` | ✅ | 0 |
| 正文 + **缺失** captcha_token | `session`（降级） | ❌ | **4001** |

### 4.4 ALTCHA PoW

```
challenge: {algorithm:"SHA-256", salt, nonce, cost:80, keyLength:32, keyPrefix:"c886ab45..."}
求解耗时 ~1.2s，counter=33 命中
derivedKey = "231443dda383a15ae789686b9a38c8376eb5c76a13319575a2a6cee11c13c361"
keyPrefix 匹配前 32 字符 ✔
缓存命中时 0ms
```

### 4.5 缓存污染自愈（4 场景全过）

| 污染形态 | 结果 |
|---|---|
| 长度不对（4 字符） | 重建 ✔ |
| 完全垃圾 JSON | 重建 ✔ |
| 空字符串 | 重建 ✔ |
| 缺 `km` 字段 | 重建 ✔ |

### 4.6 端到端全链路（实测）

```
搜索「凡人」→ 24 条
→ 第一条《让仙门再次伟大》（繁转简生效）
→ 详情：作者 鶴守月滿池 / 玄幻 / 连载中 / 最新章
→ 目录：460 章
→ 正文：4069 字（繁转简）
→ 封面：77466 字节真实 JPEG
```

### 4.7 性能

| 环节 | 耗时 |
|---|---|
| bootstrap | 0.4~2.4s |
| 搜索 | 1.1~2.9s |
| 详情 | 0.6s |
| 目录 460 章 | ~2.3s |
| 正文（含 ALTCHA 首解） | 5.8s |
| 正文（token 缓存命中） | ~1.5s |
| 封面 77KB | 4.6s |

---

## 五、可复用的四个设计

### 5.1 用明文 GET 当参数载体

书源 URL 形态：
```
详情：{BASE}/api/bootstrap?zjb={book_id}
章节：{BASE}/api/bootstrap?zjc={chapter_id}
搜索：{BASE}/api/bootstrap?zjk={keyword}&zjp={page}
```
这些 URL **永远不会被请求**（数据由 `ruleBookInfo.init` / `chapterList` 执行时读取），只是**参数容器**。

```js
function zjUrl(param, value){ return BASE + "/api/bootstrap?" + param + "=" + encodeURIComponent(String(value)); }
function zjParam(url, param){
  var m = String(url||"").match(new RegExp("[?&]"+param+"=([^&]+)"));
  return m ? decodeURIComponent(m[1]) : "";
}
```
**实测**：`b~A+B/C=D&E?F#G` 编码往返一致 ✔

### 5.2 会话缓存不存过期时间（靠 401 自愈）

```js
function zjPost(path, body){
  var err = null;
  for (var a=0; a<2; a++){
    var r = K( k(a===1), path, body );    // ★ a=0 用缓存会话，a=1 强制新建
    if (r.plain !== undefined) return r.plain;
    err = r.err;
    if (!r.retry) throw "zjPost 失败("+path+"): "+err;
  }
  throw "zjPost 失败("+path+"): "+err;
}
```

### 5.3 三级错误分类

```js
{err, retry:true}    // 网络异常 / HTTP 401 / 业务 401 → 重建会话重试
{err, verify:true}   // HTTP 403 / 业务 403 / 4001 → 清 captcha 缓存重试
{err}                // 终态 → 直接抛错（带中文消息）
```

**实测错误消息**：
```
zjPost 失败(/api/book/detail): 业务错误 code=400 无效书籍
zjPost 失败(/api/book/content): 业务错误 code=400 无效章节
```

### 5.4 缓存校验三条件

```js
if (c && c.length===32 && s && s.length===32 && u && u.length>0) return {...};
// 否则重建 —— 实测 4 种污染形态全部自愈
```

---

## 六、踩过的坑

| # | 坑 | 表现 | 解法 |
|---|---|---|---|
| 1 | **嵌套函数参数顺序反直觉** | 解密一直 `AEADBadTagException` | `l(e,r)` 内部调 `h(r,e)`；**纸上展开一次** |
| 2 | **章节 ikm 是双层 hex** | 密钥不对 | `hexDecode(hex(bid)+hex(cid)+hex(ver)+hex(nonce))` |
| 3 | **响应 key_mode 会降级** | 缺 token 时解析崩溃 | 读响应 `key_mode` 决定用哪个密钥 |
| 4 | **响应里的 cover URL 不能直接用** | 直接请求 401 | 本地生成加密 URL |
| 5 | **签名 nonce ≠ body nonce** | 签名不通过 | 两个独立随机值（18B vs 12B） |
| 6 | **签名里的哈希是 hex 文本** | 签名不通过 | `digestHex()` 返回 64 字符字符串 |
| 7 | **设备时间不准 → 全 401** | 规则明明对却全失败 | 时间戳容差 < 300 秒，先查系统时间 |
| 8 | **`zjd` 全局键跨书串数据** | 字段偶发错乱 | 键名带上书籍 ID 更安全 |
| 9 | **`eval(jsLib)` 嵌套调用丢作用域** | `hexDecodeToByteArray` 找不到 | 测试用 `new Function(...)` 显式传参 |
| 10 | **Rhino 里 `java` 遮蔽 `java.*` 包名** | 写 `java.lang.String` 报错 | 用 `Packages.java.lang.String` |

---

## 七、导入与验证

**导入**：书源 JSON 约 12KB（A）/ 11KB（B），可直接用 MCP `save_source` 或深链导入。

**验证清单**：
```
1. 握手明文可读          → GET /api/bootstrap 返回 session_id + key_material
2. 密钥派生逐字节对比     → 手工复现 == jsLib 结果
3. 破坏性实验            → 11 组全 401（除 baseline）
4. 端到端全链路          → 搜索→详情→目录→正文
5. 缓存污染自愈          → 4 种污染形态全部重建
6. 错误路径              → 无效 ID 返回中文错误
```

**checkKeyWord**：`凡人`（实测 24 条结果）
