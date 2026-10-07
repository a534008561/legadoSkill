# 案例：QQ阅读(纯本地) — `https://book.qq.com`

> 收录日期：2026-10-08　｜　类型：正版 App 协议逆向 + 本地缓存型书源（bookSourceType=0 小说）
> 配套方法论：[方法-正版App协议逆向与本地缓存书源-QQ阅读.md](../../references/方法-正版App协议逆向与本地缓存书源-QQ阅读.md)

---

## 一、源档案

| 项 | 值 |
|---|---|
| 书源名 | `QQ阅读(纯本地)` |
| bookSourceUrl | `https://book.qq.com` |
| 分组 | `QQ阅读,本地` |
| 类型 | `bookSourceType=0`（文本小说） |
| 并发 | `concurrentRate=3/1000` |
| Cookie | `enabledCookieJar=true` |
| 自定义按钮 | `customButton=true`（正文段评按钮） |
| bookUrlPattern | `https://commontgw\.reader\.qq\.com/book/queryBookInfo\?bid=\d+` |
| **jsLib** | **396,197 字符**（≈ 396KB） |
| **loginUrl** | **76,235 字符**（145 个顶层函数） |
| loginUi | 7,257 字符（`@js:` 动态生成，六个子页） |
| 规则字段 | 全 `@js:`，单条 5~80 行 |
| 全部字段 | 20 个基础 + 5 个规则对象 |

**规模提示**：这是目前技能库中**体积最大**的书源（jsLib 单项就超过多数完整源）。全部代码由 `@js:` 与 jsLib 构成，**没有一条 CSS/JSONPath 选择器**。

---

## 二、能力清单

| 能力 | 实现位置 | 说明 |
|---|---|---|
| 搜索 | `ruleSearch` | `/common/result/search_txt`，`start` 分页，每页 10 条 |
| 详情 | `ruleBookInfo` | 含 `qfRestypeDetect` 判断「普通版 / EPUB 版」双通道 |
| 目录 | `ruleToc.chapterList` | tar + CSV 解析 → 四档过滤 → 已购标记 → 输出 JSON 字符串数组 |
| 正文 | `ruleContent.content` | 缓存 → 网络 → 解密 三段式 + 试读识别 + 拒绝包处理 |
| EPUB 正文 | `rt === '4'` 分支 | 独立的 ZIP/XHTML 解析链（`qfEpubChapter`） |
| 发现 | `exploreUrl` | 男/女频切换 × 榜单(4×2) / 分类(15+11 大类 + 子类) / 我的书架 |
| 登录 | `loginUrl` | 短信验证码 + QQ 扫码 + 设备指纹管理（含设备被限自救） |
| 预缓存 | 登录面板 | 整本 / 按书号 / 强制全本 / 增量补全 / 停止 / 清空 / 自检 |
| 自动购买 | 登录面板 | 按书白名单 + 软硬冷却 + 全订月票章跳过 |
| 批量购买 | 登录面板 | 可配置一次买 N 章，余额不够只买买得起的 |
| 段评 | 正文注入 | 段落级气泡（内联 SVG）+ useweb 面板（`showBrowser`） |
| 净化 | 登录面板 | 月票章 / 作者话 / 请假章 / 全订章 / 试读章 五档开关 |
| 自检 | `searchUrl` 特判 | 关键词 `fockselftest` / `shelfdiag` / `qfbench` |

---

## 三、关键常量表（可直接抄）

### 3.1 网关与标识

```javascript
var QF = {
    GATEWAY: 'https://newminerva-tgw.reader.qq.com',      // 正文/目录网关
    FUID: '80f2357fed274773914d98ef925e78d5',             // 固定用户标识
    SIGN_SALT: 'B74H5a2Yh73gfu8F',                        // 签名盐
    BLOCK_WORDS: '月票番外',                               // 默认屏蔽词
    AUTHOR_WORDS: '作者的话,作者有话说,作者说',              // 作者话标记
    SIGN_FIELDS: ['loginType', 'ywguid', 'ywkey', 'c_version', 'c_platform', 'channel',
        'qrsn', 'qrsn_new', 'gselect', 'server_sex', 'rcmd', 'youngerMode', 'ttime']
};
var L_HDR = 'KNVA76RTD8YZXZ6Z';    // 头部材料盐（QQFock 内）
```

### 3.2 接口清单

| 用途 | 方法 | URL |
|---|---|---|
| 搜索 | GET | `https://commontgw.reader.qq.com/common/result/search_txt?key=&start=&n=10&searchFrom=909&needRewrite=1&...` |
| 详情 | GET | `https://commontgw.reader.qq.com/book/queryBookInfo?bid={bid}&lutime=0&lucc=0&luv=0&types=1,4,6` |
| 目录/正文 | GET | `https://newminerva-tgw.reader.qq.com/ChapBatAuthWithPD?bookId={bid}&type=0&tafauth=1&useindex=1&scids=0` + `,{"type":"hex"}` |
| 密钥池 | GET | `https://newminerva-tgw.reader.qq.com/sk?fuid={FUID}&type=1` |
| 已购列表 | GET | `https://androidtgw.reader.qq.com/v7_6_6/queryChapterLoad?bid={bid}` |
| 购买预览 | GET | `https://book.qq.com/api/book/read/batchBuyPreview?bid=&cid=` |
| 下单 | POST | `https://book.qq.com/api/book/read/batchBuy` |
| 书籍目录（网页） | GET | `https://book.qq.com/api/book/detail/chapters?bid=` |
| 榜单 | GET | `https://wxmini.reader.qq.com/api/rank/detail?cid={cid}&pageNo={page}&pageSize=20` |
| 分类 | GET | `https://wxmini.reader.qq.com/api/categories?c2={c2}&order=0&c3={c3}&tag=&free=-1&status=-1&word=-1&pageNo={page}&pageSize=20` |
| 书架 | GET | `https://bookshelf.reader.qq.com/v808/book/getBooks?page={page}&tid=3&gzip=0` |
| 封面 | GET | `https://bookcover.reader.qq.com/cover/{bid % 1000}/{bid}/t7_{bid}.webp` |
| 段评计数 | GET | `https://commontgw.reader.qq.com/v7_6_6/paraComment/getParagraphNoteCount/note?bid=&fromcid=&fromuuid=&count=1&resType=1` |
| 段评列表 | GET | `https://commontgw.reader.qq.com/v7_6_6/paraComment/getParagraphNoteList/note?...` |
| 段评点赞 | GET | `https://commontgw.reader.qq.com/v7_6_6/paraComment/agree?paraCmtId=` |
| 段评取消赞 | GET | `https://commontgw.reader.qq.com/community/booknote/disAgree?paraCmtId=` |
| 短信登录 | POST | `https://ptlogin.yuewen.com/sdk/sendphonecode` / `phonecodelogin` |
| 扫码登录 | POST | `https://ptlogin.yuewen.com/sdkv2/scanQRCodeLogin` |

### 3.3 榜单 cid 表

```javascript
var ranks = {
  "男频": [{cid:556259,title:"会员榜"},{cid:556260,title:"热门榜"},{cid:556261,title:"新书榜"},{cid:556262,title:"完结榜"}],
  "女频": [{cid:556263,title:"会员榜"},{cid:556264,title:"热门榜"},{cid:556265,title:"新书榜"},{cid:556266,title:"完结榜"}]
};
```

### 3.4 分类 cid 表（节选）

| 频道 | 大类 | cid | 子类（节选） |
|---|---|---|---|
| 男频 | 玄幻 | 20001 | 东方玄幻 20002 / 异世 20003 / 争霸 20082 / 高武 20004 |
| 男频 | 都市 | 20019 | 生活 20020 / 娱乐 20022 / 商场 20025 / 异能 20026 / 异术 20027 / 校园 20069 |
| 男频 | 历史 | 20028 | 架空 20029 / 先秦 20083 / 秦汉三国 20084 / 两晋隋唐 20085 / … / 传说 20094 |
| 男频 | 科幻 | 20042 | 星际 20043 / 穿梭 20044 / 未来 20045 / 机甲 20046 / 科技 20047 / 变异 20048 / 末世 20049 |
| 女频 | 古言 | 30013 | 女尊 30014 / 架空 30015 / 宅斗 30016 / 穿越 30017 / 宫斗 30018 / 种田 30019 / … |
| 女频 | 现言 | 30020 | 都市 30021 / 婚恋 30022 / 明星 30023 / 职场 30026 / 异能 30027 / 豪门 30028 / … |

（完整表见源内 `categorys` 对象：男频 15 大类 / 女频 11 大类）

### 3.5 设备指纹表（43 字段，节选关键项）

```javascript
var DEVICE = {
    'User-Agent': "okhttp/3.12.13",
    'c_platform': "android",
    'c_version': "qqreader_8.5.5.0888_android",
    'channel': "10001000",
    'ckey': "000011001100",
    'dete': "ccf899028e6ae8d0e6e5e5acc566851ed890962454463bb895eb4cdda2e2e444",
    'dn': "76e5b2d90e2fa859",
    'dt': "3d9fdcfd57cd461c57b9cfbdb394f8be2392aa21954cbafc9b0615679712c82879da5eba2ac8812ce8a7104aa6446a6e4c3ca7d7c2f15bb1",
    'gselect': "1",
    'ibex': "9hT7x1YEg2osIctJSRC6bhHeQeSLjI7m...",       // 登录指纹密文（长）
    'loginType': "1",
    'mldt': "d116f07b39912247ac6f8612d82b2e3a147a188c1dee0ebaa21c809733e31ea136462106e0e91387e5162817cd9ffdd176e5b2d90e2fa859",
    'mversion': "8.5.5.888",
    'os': "android",
    'osvn': "8924d1d8e52eefc2",
    'ov': "a1ee0fc37d31231259747493aa880d7c2ad2652c1693feb0791accbe2096595d",
    'qrsn': "1748c421a112b58c39172e1f10001ec1a905",
    'qrsn_new': "1748c421a112b58c39172e1f10001ec1a905",
    'qrsy': "772AEC2C980403285E2426C510AD19A1",
    'safekey': "3C63C1ED3C26E6A0C9751FD2417B5550",
    'sid': "",
    'sift': "216e4e6309534376721852f5dabf91fa...76e5b2d90e2fa859",
    'ssign': "698c3369822efe4997b3dcc1f3946794",
    'ssign_version': "1",
    'supportTS': "3",
    'themeid': "0",
    'trustedid': "F99DE4D28B4DB6ACC743436CD0CFD7191",
    'version_code': "421",
    'youngerMode': "0",
    'ywtoken': "EC84F622E98137328267BC357FBCBABC"
};
```

> **注意**：`mldt` 与 `sift` 都以 `dn`（`76e5b2d90e2fa859`）结尾——服务端做交叉一致性校验，不能单独改其中一个。

### 3.6 缓存键规范

| 键 | 内容 | 形态 |
|---|---|---|
| `bs_cookie` | 登录 Cookie（自管） | `"ywkey=...; ywguid=..."` |
| `bs_app_dev` | 设备编辑项 | `{"edits":[[idx,val],...],"qimei":"..."}` |
| `bs_fock_pool` | 密钥池 | base64 |
| `bs_fock_fp` | 好指纹 | 数字串 |
| `bs_fock_keyid` | 优先 keyId | 数字串 |
| `bs_ch_{bid}_{cid}` | 单章 | 密文 `{"n":"...","h":"<hex>"}` / 文本 `{"t":"...","p":0\|1}` |
| `bs_chl_{bid}` | 已缓存章节清单 | JSON 数组 |
| `bs_restype_{bid}` | 书籍类型 | `"0"` / `"4"` |
| `bs_bought_{bid}` | 已购 cid 串 | `"1-50,55,60-70"` |
| `bs_ab_list` | 自动购买白名单 | JSON 数组 |
| `bs_review` | 段评开关 | `"0"` 关闭 |
| `bs_no_preview` | 试读不返回 | `"1"` 开启 |
| `bs_sign_ttl` | 签名缓存 TTL | 毫秒（默认 20000） |
| `bs_fock_tries` | 正文重试次数 | 默认 10（2~30） |
| `bs_batch_span` | 批量预取跨度 | 默认 8（1~17） |

### 3.7 面板开关（净化档位）

| 开关 | 默认 | 作用 |
|---|---|---|
| `bs_toc_ticket` | 开 | 屏蔽月票解锁章（目录第 12 列 > 0） |
| `bs_toc_full` | 开 | 屏蔽全订解锁章（第 11 列 = 2） |
| `bs_toc_leave` | 开 | 屏蔽请假章（免费 + 标题含「请」「假」+ 无「第…章」） |
| `bs_cut_author` | 开 | 裁剪正文末尾作者话 |
| `bs_no_preview` | 关 | 试读章不返回内容（防污染缓存） |

---

## 四、核心代码骨架（可复用）

### 4.1 hex 通道三件套

```javascript
function qfHexOption() { return ',{"type":"hex"}'; }   // URL 选项
function qfHexToLatin1(hex) { /* java 优先，JS 兜底 */ } // hex → latin1 串
function qfTarStr(s) { /* 512 字节块解析，size 是八进制 */ }
```

### 4.2 签名头

```javascript
function qfSign(hd) {
    var out = {};
    for (var k in hd) if (hd.hasOwnProperty(k)) out[k] = hd[k];
    out['ttime'] = String(new Date().getTime());
    var sb = '';
    for (var i = 0; i < QF.SIGN_FIELDS.length; i++) sb += qfVal(out, QF.SIGN_FIELDS[i]) + '|';
    sb += QF.SIGN_SALT;
    var x = QQFock.bToHex(QQFock.sha256(QQFock.bFromStr(sb)));
    out['csigs'] = QQBCrypt.hash(QQFock.bFromStr(x), 4);
    return out;
}
```

### 4.3 正文规则主干（简化）

```javascript
(function(){
  var ids = qfIdsFromUrl(baseUrl);           // ① 解析 bid/cid
  var st0 = qfStashGet(source, bid, cid);    // ② 查缓存
  if (st0 && st0.text !== undefined) {
      if (!st0.preview) return st0.text;     //    完整正文直接返回
      // 试读：已购则丢弃重取，否则返回试读+说明
  }
  if (!qfPoolEnsure(source, qfAjax)) throw new Error('取密钥池失败');
  for (var a = 0; a < tries; a++) {          // ③ 网络 + 解密（含退避重试）
      if (a > 0) qfNap(a < 4 ? 180 * a : 720);
      var hex = String(java.ajax(qfChapterUrl(bid, cid, undefined, undefined, rt0)));
      var pkg = qfPkgProbe(hex);
      if (pkg && qfPkgDenied(pkg)) { /* 拒绝包：限次重试或抛错，绝不返回文本 */ }
      var r = qfDecryptFromHex(hex, bid, cid);
      if (r && r.ok) return r.text;
  }
  throw new Error('本章正文没取到...');
})()
```

### 4.4 loginCheckJs 网络兜底

```javascript
// 网络失败 + 有缓存 ⇒ 伪造响应让流程继续，正文规则会命中 stash
var SR = Packages.io.legado.app.help.http.StrResponse;
return new SR('http://localhost/', b);
```

---

## 五、本案例的「第一次」

| # | 首次出现的技术 | 价值 |
|---|---|---|
| 1 | **官方 `{"type":"hex"}` URL 选项**的系统性使用 | 官方原生支持，把二进制响应以 hex 形式送进规则 |
| 2 | **自实现完整密码学栈**（SHA256/AES-256/DES/CRC32/Inflate/MD4/自定义哈希） | 无 CryptoJS 依赖，Rhino 内可跑 |
| 3 | **原生 Java 与纯 JS 双实现互备** | 性能与兼容性兼得（1.7ms vs 数十ms） |
| 4 | **响应头部指纹校验**（`peekId`）防密钥池漂移 | 避免「解出垃圾当正文」 |
| 5 | **服务端拒绝包的显式识别**（`info.txt` code 负数） | 绝不把错误提示写进缓存 |
| 6 | **试读/全文双态缓存**（`p:1` 标记） | 购买后能自动丢弃过期试读 |
| 7 | **tar 容器内多章批量下发 + 单章解密** | 一次请求拉 8 章，只解密当前章 |
| 8 | **网络失败兜底到本地缓存**（伪造 StrResponse） | 真正实现「离线可读」 |
| 9 | **段落级评论气泡注入**（含字符偏移回传） | 正文阅读器内的社交功能 |
| 10 | **设备指纹被限的专用处理**（code=3/-11059） | 重生成设备而非换 IP |
| 11 | **`searchUrl` 关键词特判触发自检** | 无 UI 依赖的诊断入口 |
| 12 | **区间语法 `scids=100-107` 批量拉取** | 配合 `qfSelArg` 保留 `-` 与 `,` |

---

## 六、风险与限制

| 风险 | 说明 |
|---|---|
| **维护成本高** | 396KB jsLib + 76KB loginUrl，任何一处算法变更都要跟进 |
| **强依赖登录** | 未登录只能拿试读；设备指纹被限需要换设备 |
| **服务端协议可能变** | 密钥池格式、字段表、签名盐都可能更新 |
| **预缓存耗流量** | 整本预取会一次拉取全书章节包 |
| **自动购买涉及付费** | 默认按书白名单，但仍需用户明确开启 |
| **本技能库不附带完整 JSON** | 528KB 超交付体积；需要时从 App 内直接导出 |

---

## 七、移植建议

若要基于此源改造（换站/裁剪功能），按方法论文档第十二节的清单执行：

**必改**：`QF.GATEWAY` / `QF.FUID` / `QF.SIGN_SALT` / `QF.SIGN_FIELDS` / `DEVICE` 表 / `L_HDR` / 接口 URL
**选删**：密钥池（单密钥站可简化）/ 指纹校验 / 段评 / 自动购买 / 预缓存
**保留**：`qfTarStr` / `qfHexToLatin1` / `natCtx` 双实现框架 / 缓存三件套 / 退避工具 / K1~K22 纪律

---

## 八、速查：源内函数分组（370 个）

| 前缀 | 数量 | 职责 |
|---|---|---|
| `QQIbex` / `ibex` / `nib*` | ~40 | 登录指纹信封（MD5/MD4/SHA/AES/DES + nibLk） |
| `QQFock` / `nat*` / `cipher*` / `aes*` / `des*` | ~60 | 响应解密（密钥池 + 双层信封） |
| `qf*` | ~200 | 规则工具（URL/缓存/目录/包/退避/净化） |
| `qq*` / `QQ_CMT_*` | ~50 | 段评（列表/发布/点赞/面板） |
| `bs*`（loginUrl） | 145 | 登录与面板（短信/扫码/预缓存/购买/设置） |

**调试用探针关键词**（在搜索框输入即可触发）：

| 关键词 | 作用 |
|---|---|
| `fockselftest` | 跑 `qfSelfTest()`，验证解密链路 |
| `shelfdiag` | 诊断书架接口（含 explore 规则试跑） |
| `qfbench {bid} {cid}` | 基准测试单章解密耗时 |
