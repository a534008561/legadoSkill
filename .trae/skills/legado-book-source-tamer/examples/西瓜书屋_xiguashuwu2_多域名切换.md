# 案例：西瓜书屋多域名切换书源（v3）

## 站点情报（2026-10-29 实测）
- 主站 `www.xiguashuwu2.com`：CF managed challenge，`/search/*` 必中
- 备用 `www.xiguashuwu.net` / `www.xiguashuwu.com`：站点自建土盾（Cookie `nginx_waf_passed=1` 恒定值，直连免验证）
- 搜索 `GET /search/<urlencoded kw>`，无分页；隐藏表单端点 `/sdfgsdyugfsdugf.html`（`keyword` 参数）是空壳，别用
- 详情 `/book/{id}/` og:meta 全字段；**og:image 路径有重复段 bug（`image/files/article/image/...`）不可用**，封面用页内 `BGsectionOne-top-left img@_src`
- 目录 `/book/{id}/catalog/`，>100章分页 `catalog/{页}.html`（100条/页），「下一页」是 JS 跳转**无 href** → nextTocUrl 用 `text.下一页@href##.*\('(\d+)','(\d+)'\).*##/book/$1/catalog/$2.html` 从 onclick 还原
- 正文三形态：静态 `#C0NTENT` / UpWz 乱序（meta[7] b64 + codeurl）/ AES（newcon+passphrase，md5前16=iv后16=key）
- 发现分类 ID：玄幻1 修真2 都市3 历史4 网游5 科幻6 言情7 其他8 经典9 同人10 高辣11 耽美12 情欲13 复古耽美14 复古言情15 + 全部0 + finish + rank

## v3 书源设计
- 登录面板 6 按钮：状态栏(viewName动态)/切换网址(循环三站+种Cookie)/回主站/用备用站/检查连接/手动过CF
- 全部规则相对路径 → 切站全链路跟随
- loginCheckJs 弹**带关键词的 baseUrl** 过 CF（修复旧源弹空搜索页丢关键词的 bug），不 removeCookie
- 正文单 `<js>` IIFE 三形态适配（纯字符串切片，不用 jsoup），广告正则覆盖 simishuwu 空格变体
- 双版本兼容：`createSymmetricCrypto`/`md5Encode`/`base64Decode`/`getVariable`/`setVariable`/`cookie.setCookie` 两版 API 一致

## 实测结果（App Web API 全链路）
| 环节 | 结果 |
|---|---|
| 搜索(App内真机) | 16本 ✓（过盾后） |
| 详情 | og:meta+页面字段 ✓ |
| 目录 | 2章/34章/20章三本书 ✓（100条/页分页规则就位） |
| 正文静态页 | 1549B ✓ |
| 正文UpWz乱序+跨页拼接 | 4679B，p1尾p2首无缝 ✓ |
| 广告清理 | 新章无残留 ✓（旧章=缓存，非规则问题） |
| net 域结构 | 分类/搜索结构一致 ✓ |

## 交付物
- `/workspace/xiguashuwu/西瓜书屋v3.json`（12133B）
- 经验文档：references/方法-站点自建土盾与CF盾双域名切换体系-西瓜书屋.md

## 最终形态补记（261029 晚）
- **搜索通道分版本路由**：searchUrl 用 `@js:` 探测 `typeof source.getLoginUiJs==='function'`——LT 有此方法→返回 `,{"webView":true,"webViewDelayTime":1800,"timeout":30000,"retry":1}` 走 BackstageWebView（CF 指纹放行直出结果）；E 无→返回 `,{"timeout":30000,"retry":1}` 走 OkHttp+loginCheckJs 人工过盾（E 的 cf_clearance 会话保持好，过一次长期有效）。实测：LT webView 搜索成功；E webView 通道 60s 超时（TimeoutCancellationException），改 OkHttp 人工过盾后正常
- **正文最终算法=四层判据**（plainLen=容器内块去标签总字数）：nid=='C0NTENT'→静态拼块；plainLen<10 且有 newcon→AES 解密（空壳干扰页）；b64 序号数==块数且 plainLen≥10→UpWz 还原；否则直接拼块。单章实测四页混用四形态（静态/乱序/明文干扰/乱序）17686B 无缝拼接
- **Rhino 铁律**：content <js> 必须 IIFE+return；跨 try/catch 变量顶部 var 声明（"ReferenceError: out 未定义"实锤）；node 测试桩必须从书源 JSON 提取（手抄桩含 var 声明→沙盒全绿真机炸）
