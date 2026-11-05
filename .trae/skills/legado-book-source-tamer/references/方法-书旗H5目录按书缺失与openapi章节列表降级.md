# 方法：书旗 H5 目录「按书缺失」与 openapi 章节列表降级（含卷首名显示规则）

> 沉淀日期：2026-11-05 ｜ 来源：修复「🌙 书旗小说(APP接口)」书源目录加载失败报障
> 关联：[方法-书旗App加密协议与UA白名单403伪装](方法-书旗App加密协议与UA白名单403伪装.md)、[方法-搜索限频伪装的间歇性错误页](方法-搜索限频伪装的间歇性错误页.md)、[方法-对照实验驱动的接口逆向](方法-对照实验驱动的接口逆向与正文排版.md)

---

## 一、故障现象与定性（三组对照实验）

用户报：搜「高位禁锢」「两个爸爸一萌娃」「总裁他非让我拖家带口住豪宅」及「广青刀」作者三本，**搜索正常、详情正常，目录加载失败**（`TocEmptyException: 目录列表为空`）。

`debug_source` 复现 + HTTP 日志实锤：

| 通道 | 问题书（bid=9334636） | 正常书（bid=34078） |
|---|---|---|
| H5 目录 `www.shuqi.com/chapter?bid=` | **55 字节 `<script>location.replace("/book/N.html")</script>`** | 1.19MB 完整真目录（2451 章） |
| 封面 `www.shuqi.com/book/N.html` | 22KB 空壳：`<title>《》…</title>`、书名为空、无 `cid=` | 正常渲染 |
| 加密口 `titlepage` | `chapterTotalNum:205` 正常返回 | 正常 |
| 加密口 `chapterinfo`（旧降级） | `{"status":"200","data":null}`（**带真实 chapterId 也是 null**） | 同样 null |
| 浏览器 UA 401/403 | 无关，UA 已是 `okhttp/3.12.13` | — |

**结论**：不是限频/签名/编码问题，是**站点按书分流**——这批新书 H5 站点完全无网页数据目录页重定向回空壳封面页；旧「chapterinfo 拿首章 ID + `base+i` 递推」降级彻底失效（既拿不到 base，且实测章节 ID **根本不连续**：《高位禁锢》首章 2545562、末章 2639258，中间断档巨大）。

对照组不可省：正常书 + 历史日志里另一本问题书（bid=8168055）也复现同一 55 字节重定向，证明是「一类书」而非单本偶发。

---

## 二、根因修复：启用书旗 H5 开放目录接口

书旗 H5 自身有独立于 App 加密口的 `openapi/book/chapterlist`，对**所有**书（含 H5 目录页缺失的新书）返回完整目录。线索来自 Yiove 书源仓库的 `t.shuqi.com/catalog/{bid}` + `bscpubKey` 签名链路，用现成 `SQ_md5`（纯 JS 自实现，E 版兼容）即可复现。

### 2.1 签名与 URL（黄金链路）

```
key  = 37e81a9d8f02596e1b895d07c171d5c9   // t.shuqi.com/catalog/{bid} 页内 bscpubKey，实测 9 本书完全一致（全站固定，可硬编码）
uid  = 8000000
ts   = floor(Date.now()/1000)
sign = md5( bid + ts + uid + key )

主： https://content.shuqireader.com/openapi/book/chapterlist?shuqi_h5=205&platform=0&bookId={bid}&user_id={uid}&timestamp={ts}&sign={sign}
备： https://ocean.shuqireader.com/api/bcspub/qswebapi/book/chapterlist?_=&bookId=...&user_id=...&timestamp=...&sign=...
```

- 响应 `{"state":"200","data":{...}}`，**无需 App 加密口签名、无需登录、无需 Cookie**；UA 沿用 `okhttp/3.12.13` 即可。
- 备用域返回体略小但字段同构，可作为主域失败兜底。

### 2.2 数据结构大坑：`chapterList` 是「卷数组」，不是章节数组

```json
"data": {
  "chapterNum": "205",
  "chapterList": [                       // ← 卷数组（长度=卷数）
    { "volumeId":1, "volumeName":"正文", "volumeOrder":1,
      "volumeList": [                   // ← 才是章节数组（205 个）
        {"chapterId":"2545562","chapterName":"第1章 罗网","payStatus":"0",
         "contUrlSuffix":"?bookId=...&chapterId=...&sign=...","chapterOrdid":"1", ...},
        ...
      ]}
  ]
}
```

**踩坑实录**：第一版写 `arr = data.chapterList`，结果 9 本书「解析章数=1/4」（把卷当章），首末章全 `undefined`。必须逐卷展平 `vol.volumeList`（兼容别名 `chapterList`/`chapter`）。社区规则 `$..volumeList[*]` 正是此意。

### 2.3 chapterUrl 复用现有 CDN 正文链路

`chapterId` 直接拼既有免签 CDN：

```
https://{c1|c2}.shuqireader.com/httpserver/filecache/get_book_content_{bid}_{chapterId}_3111111111_0_0.html
```

实测 6/6 全绿（含 `payStatus=3` 的 VIP 末章，正文 2395~3975 字）；**正文规则一行都不用改**。这也再次说明：新目录源不要另起正文协议，优先复用已验证链路。

### 2.4 双通道优先级（零回归）

```
1. H5 目录页 /chapter?bid=（正常书原位保留，避免改变已可用书目行为）
2. 若 h.length<5000 / 不含 "cid=" → SQ_openToc（新 openapi 降级）
3. 彻底删除 chapterinfo 递推（伪降级，data:null + ID 不连续）
```

改公共函数后必跑三套上下文回归：`check_source` + `debug_source` + `eval_js`（历史教训：改 `SQ_*` 签名漏改调用点会 `ReferenceError`；`java.sleep` 在 AnalyzeUrl 环境不存在须 try/catch）。

---

## 三、卷首名显示规则（用户明确需求，通用化）

> 用户原话：「他本身有卷首名的，才显示卷首名，他本身没有的，你不用多此一举添加。而且只在他有那里显示就行了，不用每章都显示」

落地判据（两条目录通道共用同一规则）：

1. **站点本身分卷**（`marks.length>=2` 且卷名非空）才显示；单卷（哪怕卷名叫「两个爸爸一萌娃」「萌宝来袭」）**一律不加**；
2. 只在**每卷第一章**名前加一次 `【卷名】`；其余章节标题保持原样；
3. 若章名里**已内嵌该卷名**（老版《凡人修仙传》第 193 章原名「第三卷 第一百九十三章…」），`SQ_volMark` 直接返回原标题，避免重复；
4. H5 页卷名来自 `<div class="vol_name"><span>第一卷</span></div>`，按其在 HTML 中的 `pos` 找该卷区间内第一个 `reader?...cid=` 链接作为卷首章（比对**位置**而非猜章节序号）。

实测《凡人修仙传》2451 章：仅第 1/100/172/193 章 4 处带卷名，第 2 章「第2章 青牛镇」、第 101 章「第101章 钱财惹祸」等一概原样。

**通用教训**：「显示卷名」是多卷书的目录导航信息，不是每章的装饰；把用户措辞翻成可执行判据时要带反向验证组（单卷书 + 第 2 章），否则极易做成每行加前缀的噪音。

---

## 四、排查方法论 Checklist（可迁移到其它「部分书目录空」站点）

1. 先抓 HTTP 日志看目录请求**真实响应体长度/内容**：`200` + 55 字节 JS 跳转 ≠ 正常页，`200` + `data:null` ≠ 成功；
2. 分三组：报障书 / 正常书（反向验证）/ 同症状历史书，确认是「按书分流」还是全站改版；
3. 详情页/搜索结果里若有 `chapterTotalNum` 等章节总数，说明**服务端必有目录数据源**，去 H5 移动站/开放 API 找，不要困在加密口；
4. 社区书源（Yiove 等）是找**老接口**的高价值线索，但签名算法/结构须现场抓响应验证，不能照抄；
5. 找到新目录源后，检查章节 ID 是否连续——不连续就**必须**拿真 ID 列表，绝不能 `base+i` 递推；
6. 新源优先复用已验证的正文 URL 规则，减少回归面；
7. 交付前：`check_source` 1/1 + 每本报障书 `debug_source` 到正文 + 正常书反向验证 + VIP 末章正文 + 卷名/无卷名两组抽查。

---

## 五、本次实测数据（2026-11-05）

| 书 | bid | 章数 | 卷数 | 首章 | 末章正文 |
|---|---|---|---|---|---|
| 高位禁锢 | 9334636 | 205 | 1（正文） | 第1章 罗网 | 3975 字（VIP） |
| 两个爸爸一萌娃 | 7131257 | 216 | 1 | Chapter1好狗不挡道 | 2639 字（VIP） |
| 总裁他非让我拖家带口住豪宅 | 7697319 | 269 | 1 | Chapter1专业护犊子 | 2701 字（VIP） |
| 广青刀① O装A后 | 9281948 | 274 | 1 | 第1章 发情期的omega | 2764 字 |
| 广青刀② 拜金捞子 | 9430162 | 132 | 1 | 第1章 哥哥看着心疼 | 2395 字 |
| 广青刀③ 逃离强制 | 9237967 | 236 | 1 | 第1章 周总，请自重 | 6112 字 |
| 凡人修仙传（对照·H5 正常） | 34078 | 2451 | 4 | 【第一卷】第1章 山边小村 | — |
| 美利坚房东（对照） | 9429921 | 137 | 1 | — | 2897 字 |
| 历史日志同症状书 | 8168055 | 494 | 1 | 第1章 逃跑成功 | 2463 字 |

`check_source` 1/1；三本报障书 `debug_source` 搜索→详情→目录→正文全绿；对照书 H5 主通道零回归。
