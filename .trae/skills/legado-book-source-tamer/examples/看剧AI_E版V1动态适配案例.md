# 案例：看剧AI 书源+订阅源 登录界面适配 Legado-E（V2→V1 动态，261117）

> 用户报「修复登录界面适配 e 版（看剧AI）书源订阅源」，E 版 web 服务 1125 提供 LAN 落库通道。一次修两个源：书源 `看剧AI`（https://kanju.ai）+ 订阅源 `看剧AI·视频线路`（https://kanju44.com）。

## 1 根因（源码级）
两个源原本 `loginUi = {"version":2}` 都是 V2 面板。E 版（legado-E main）源码的 `SourceLoginDialog` **无 V2 delegate**（无 `getLoginUiJs()/isLoginUiV2()/evalLoginUiV2`），`GSON.fromJsonArray<RowUi>('{"version":2}')` 解析失败 → 登录面板空白/失效。LT 版 V2 正常，故只在 E 版暴露。
E 版 `evalUiJs` 源码实锤（`app/src/main/java/io/legado/app/ui/login/SourceLoginDialog.kt`）：
```
fun evalUiJs(jsStr) = source.evalJS("$loginJS\n$jsStr"){ put("result",...);put("book",...);put("chapter",...) }
```
⇒ V1 动态生成函数环境 **有 source、无 java**；按钮 action 环境 `source.evalJS("$loginJS\n$action"){put("java",...)}` **有 java**。

## 2 修复形态
两源都改 `loginUi = "@js:kjV1Rows()"`（书源）/ `"@js:kjvRows()"`（订阅源），用 `@js:` 不用 `<js>`（避免代码里的 `<` 被 `lastIndexOf('<')` 截断）。V2 的 `state.msg/who/note/ping_map/cur` 全改用变量存；状态行用 `type:'button'`（E 版 label 不渲染）；每动作末尾 `java.longToast + java.reLoginView(true)` 触发重绘；loginUrl 顶层补 `function login(){return 'ok';}`（否则点✓关面板报 `Function login not implements!!!`）。

## 3 ★两源的关键差异：状态键空间不同
| | 书源 kanju.ai | 订阅源 kanju44.com |
|---|---|---|
| 规则层读线路 | `source.get('kj_host')` | `java.get('kj_host')`（jsLib 共享 java 键空间） |
| 迁移做法 | 全用 source 变量 | **双键空间镜像**：action 里 `java.put('kj_host')`（规则层生效）+ `source.put('kjv_host')`（显示镜像）；生成函数从 source 读显示 |
⇒ 通用铁律：V1 动态迁移先看原源状态键空间，规则层用 java 键空间的必须做 source 镜像，否则生成函数 java.get 直接 ReferenceError → 面板空白。

## 4 验证闭环
1. jsLib 与 loginUrl 函数名交集=空（kj* vs kjl*/kjV1*/kjv*）
2. eval_js 绑定真源 eval(loginUrl) 后调生成函数 → 书源 15 行 / 订阅源 6 行，全 button、action 齐全、逐函数 typeof=function、`login()`=ok
3. java 桩实调 kjV1Use/kjV1Logout（书源写 source）、kjvUse（订阅源 java+source 双写）、kjvPing（存 source），全部通过
4. LAN 落库：`POST /saveBookSource`（书源，1122 LT + 1125 E 双端）、`POST /saveRssSource`（订阅源，1125 E）；回读 get_source / getBookSource?url= / getRssSources → loginUi/loginUrl 一致，业务字段零变化
5. 运维坑：E 版 `getBookSources` 全量会打崩 web 服务（Empty reply+端口临时关闭），单源回读用 `getBookSource?url=<urlencoded>`（响应包在 `{data:...}`）

## 5 成品
- 书源：`看剧AI_E版V1动态修复.json`（单对象，导入数组 `_导入.json`）
- 订阅源：`看剧AI视频线路订阅源_E版V1动态修复.json`
- 方法总纲：references/方法-legadoE登录面板V1动态与发现页点选化.md §7（书源）/§8（订阅源）
