# 方法-站点模板改版甄别与最小diff修复（霹雳书屋 261031）

> 适用场景：书源某功能突然失效（本次是详情页），站点其他功能正常 → 八成是站点改版了部分模板。
> 本篇沉淀「改版甄别流程 + 镜像域名甄别 + LAN 字节级直传修复配方」。

## 1. 改版甄别流程（先定位改版范围，再动规则）

失效功能与正常功能**同站对比**：逐页抓真实 HTML，统计新旧类名出现次数（如 `x-detail` 与 `custom-` 各出现多少次），快速圈定改版面：

- 详情页：`x-detail` 0 次 / `custom-` 全量 → 详情模板全改
- 搜索/发现页：`x-book` 201 次 → 未改版
- 目录页：`ol`+`li` 结构未动 → 未改版
- 正文：getchapter JSON 接口原样返回 → 未改版

**结论先行**：只重写失效部分（本次只动 ruleBookInfo），正常部分一律不动——这是最小 diff 原则，改得越少风险越小。

## 2. 镜像域名甄别（同名不同站，不能做线路池）

书源 jsLib 里 `var api=[...]` 的四个域名不等于同站线路池。判别方法：**用同一资源 ID（/5/387/info.html）逐一访问**：

- 真站 pilishuwu.com → 《戎先生的失恋日记》
- mozishuwu.com 同 ID → 《[清穿+红楼]点石成金》书名不同，是另一本书库；xiarishuwu.com 同 ID → 种田文

判据：**同 ID 不同书 = 同名不同站镜像**（盗版克隆站用了同名字同 URL 结构但书库不同），不能做换源线路池，否则搜索结果会串站。

## 3. ★★ LAN Web 服务字节级直传修复配方（大文件/混淆 jsLib 唯一可靠通道）

save_source 同 URL=全量 REPLACE、MCP 参数手工转录大 JSON 必损坏，所以大书源修复必须走 LAN 直传四步：

```
① GET /getBookSource?url=<quote(url)> (x-legado-token) → 完整 JSON
② Python json.load → 只改目标字段（外科手术）→ json.dumps
③ POST /saveBookSource (x-legado-token) → isSuccess:true
④ GET 回读逐字段核对 + debug_source 全链路实测
```

本次实测保真数据：jsLib 14126B、variableComment 748B 字节级一致，payload 21KB 直传无损。
Content-Type 必须是 application/json；令牌值由用户会话内提供，凭据不入库。

## 3.1 MCP eval_js 的 source 绑定不可靠

MCP eval_js 的 `source` 统绑定闪断：有时完整（jsLib 14126 可读），有时全空。因此**不能在 eval_js 里现场构建完整 JSON 再保存**——绑定闪断时会把空值写进库。修复必须用 LAN 通道读出→改→写回。

## 3.2 Packages 全是 JavaPackage 假象

书源运行时 classloader 不含 app 类，`Packages.io.legado.app.*` 返回 JavaPackage 占位对象（typeof 显示 "object" 但方法调用全失败，`new Gson()`、`db.getBookSourceDao()` 全报"不是函数，它是 object"）。**进程内 DAO/反射路线死路**，别再试。

## 4. 交付闸门（本次实测数据）

- 详情：书名/作者/分类/标签/封面/简介/更新时间全取到
- 目录：77 章（短篇）与 1647 章（长篇）单页全量
- 正文：getchapter JSON `$..content[*]` 原样兼容
- 搜索：4 结果 → 详情 → 目录 1647 章 → 正文全链路
- 回读校验：jsLib/variableComment 字节级一致、ruleBookInfo 新规则全字段核对通过

## 5. 一图流配方

```
失效功能 → 同站逐页对比新旧类名计数 → 圈定改版面 → 只重写失效字段
        → LAN GET 读出 → Python 外科手术 → POST 写回 → 回读核对 → debug 全链路
```
