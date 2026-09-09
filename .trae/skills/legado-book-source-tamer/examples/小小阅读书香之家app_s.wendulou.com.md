# 案例：小小阅读/书香之家 App 聚合书源（s.wendulou.com）

> 模板作者：遇知（20231225）；解密：尐哖 & landseer；本文档为 2026-09-09 拆解实测。
> 完整经验文档：[references/方法-APP接口聚合书源拆解.md](../references/方法-APP接口聚合书源拆解.md)
> 成品：[小小阅读书香之家app_s.wendulou.com.json](./小小阅读书香之家app_s.wendulou.com.json)

## 一句话架构

一批"看书 App"共用一个 JSON API 后端，书源聚合多 App 数据源：**搜索/详情/分类走"动态种子信封 AES-256"，目录章名/正文走"固定密钥 AES-128"，换源靠详情 init 改写 tocUrl + 书籍变量选站**。

## 全链路（实测通过 2026-09-09）

```
搜索 /v4/1/lists.api?keyword={kw}&form=1 → {book:[100]}   (体系A动态解密)
详情 /book/details/v4/{id/1000}/{id}.html                  (体系A)
换源 /book/source/v4/{id/1000}/{id}.html → [{site_id,site_path,choose,...}]
目录 /catalog.{主域}/{site_path} → [{name:AES-128加密章名, path, updated_at}]
正文 /chapter.{主域}/{path} → {content: AES-128加密}
发现 /book_city/v7_more/index/1/20/{1-6}/{page}.html (纯数组)
     /classify/v4/index.html (分类树,动态生成发现按钮)
     /classify/v4/all/{gender}/{ltype}/{stype}/-1/-1/{page}.html → {limit,lists}
回退 /v1/lists.api?keyword={kw} → 明文数组 (v4空结果时用)
```

## 五个最值钱的技巧（详见拆解文档）

1. **子域推导**：所有 URL 从 `source.getKey().replace('//s','//子域')` 派生 → 换主域名整体迁移，规则零修改（实测 s.mysignal.cn / s.chuangke.tv 同库可用）。
2. **鉴权真相**：sign/time 实测不校验（填乱值照常返回），**真正校验的是 User-Agent 尾部的 `_{package}` 后缀**——逐项破坏性实验定位。
3. **CBC 排错铁律**：错 IV 只毁首个 16 字节块（后续块正常），错 key 全乱。逆向时先看首块。
4. **md5Encode 是 hex 字符串**：IV = md5(iv种子) 的 hex 字符串前 16 个 ASCII 字节 XOR 种子 XOR 0xFF，不是 raw digest。
5. **单书源多站换源**：init 读 `book.getVariable("custom")` 选来源 → tocUrl 动态指向 `catalog/{来源}/...` → preUpdateJs=`java.refreshTocUrl()` 刷新生效，来源列表+选用率写进 remark 展示。

## 踩坑记录

- 目录/正文是**另一套固定密钥**（`Pxga!h*e4@T8xfOm` / `E&z!EHGLd$fli*8R`，AES-128-CBC），与体系 A 不同，`java.aesBase64DecodeToString(result,key,trans,iv)` 四参签名直接解。
- base64 缺 `=` 填充：hutool 宽容，Python 要手动补。
- 响应 gzip：Python 侧要探测 `\x1f\x8b` 魔数手动解压。
- book_city 超页返回 content=null：`$.book[*]` 自然取空终止分页。
- 三种列表容器：`{book[]}` / 纯数组 / `{limit,lists[]}` → bookList 用 `$.book[*]||$..lists[*]||$.[*]` 通吃。
- detail 的 updated_at 是字符串、catalog 的是 unix 秒，格式化规则分别写。
- 搜索无翻页；`v4/{N}` 的 N 不是页码。
- exploreUrl 里 `{url:null, style:{...}}` 项 = 发现页分组标题行；`layout_flexBasisPercent` 控制网格列宽。

## 验证档案

- debug_source 全链路：搜索《深空彼岸》100 条 → 详情 10 来源 → 目录 1441 章 → 正文解密正常
- 发现页"每日优选"13 本 → 目录 3934 章 → 正文全通
- Python 独立复现双层解密与 App 结果一致
- 备用域名实测：mysignal.cn/chuangke.tv 存活同库；pjxhmy/klzdp/4billion/bzatgv/lhdqsb DNS 已死
