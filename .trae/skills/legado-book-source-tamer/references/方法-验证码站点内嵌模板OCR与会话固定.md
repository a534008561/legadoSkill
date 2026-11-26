# 方法：验证码站点的书源内嵌模板 OCR 与会话固定（261127 蔓延书城实锤）

## 何时用

站点搜索/接口强制图形验证码（如 4 位字母数字），没有免验证码通道，也不能依赖外部 OCR 服务。目标是在书源 JS 内自包含完成识别，且同时兼容 LegadoTeam(LT) 与 legado-E。

## 一、先定性验证码

1. 打开搜索页，确认是否返回「请输入验证码」+ `/searchcode.php` 之类取图接口。
2. 对照实验：同会话 POST `keyword=...&code=错误值` 仍回到验证码页；正确值返回真实结果页。
3. 采集 100+ 张真验证码，本地用 `ddddocr` 打标：`ddddocr.DdddOcr(show_ad=False).classification(png_bytes)`。实测一次即可读对，且可用 POST 是否出结果反证标签正确。

## 二、训练模板（离线，生成一次即可）

- 按固定字符槽切图（蔓延书城 190x40，4 槽 x=[0,32]/[40,74]/[88,124]/[136,168]，y=3..39）。
- 每槽二值化 `L<200` →取 bbox→**最近邻**缩放到 16x24→384 bit。
- 每个字符保留**全部样本**作为模板；1NN 汉明距离比对。实测 512 模板 leave-one-out 准确率 99.6%；按字符求平均模板只有 69%，不可用。
- 打包：每模板 49 字节 = `1 字节字符索引 + 48 字节位图（8 像素/字节）`；整体 base64 成 JS 常量；运行时 `java.base64DecodeToByteArray(TB)`。
- 字符池按实测收缩（蔓延书城只有 44 个：`23456789ABCEFGMNPRSTVYZabcdefghkmnprstuvwxyz`），不要假设 0-9a-zA-Z 全有。

## 三、App 内解码铁律

```js
// ❌ 错：java.ajax 取 PNG 会按文本解码而损坏；UTF-16LE 编回也因 CP1252 映射不稳定失败
// ✅ 对：downloadFile -> readFile -> BitmapFactory
var p = String(java.downloadFile(BASE + '/searchcode.php?t=' + Date.now()));
var b = java.readFile(p);
try { java.deleteFile(p) } catch (e) {}
var bmp = Packages.android.graphics.BitmapFactory.decodeByteArray(b, 0, b.length);
var w = bmp.getWidth(), h = bmp.getHeight();
var c = bmp.getPixel(x, y);                 // ARGB int
var gray = ((c>>16&255)*299 + (c>>8&255)*587 + (c&255)*114) / 1000;
```

- Android **没有** `javax.imageio.ImageIO`：`Packages.javax.imageio.ImageIO` 只是 JavaPackage，`read` 是 object 不是函数。
- 站点偶发首次 TCP 15s 超时：取图最多重试 3 次（间隔 600ms）；**不要重试搜索提交**，避免高频触碰风控。
- searchUrl 末尾必须返回标准 `URL,{"method":"POST","body":"..."}`。`data:text/html;base64,...` 作搜索 URL 会被 OkHttp 拒绝（Expected URL scheme 'http' or 'https' but was 'data'），LT/E 都不行。

## 四、★★★E 版会话固定（最大坑）

E 版 `java.downloadFile` 取验证码图时**不会把 Set-Cookie(PHPSESSID) 回写 CookieJar**，而 LT 版会。表现：OCR 出的验证码是对的，POST 后仍回到验证码页 → 搜索结果 0；日志看不出异常。

修法（两版通吃）：取图前自己固定会话 ID。

```js
try {
  var sid = 'mys' + Date.now() + Math.floor(Math.random()*100000);
  cookie.removeCookie(BASE + '/');
  cookie.setCookie(BASE + '/', 'PHPSESSID=' + sid);
} catch (e) {}
```

PHP 默认接受客户端指定的 PHPSESSID，随后 `java.downloadFile` 取图与框架 POST 搜索共用同一会话。

## 五、配套清洗坑

- 私有区图标实体常**无分号**且紧跟数字：`&#xe848</i>61章` 去标签后变成 `&#xe848 61章`，若用通用 `&#x([0-9a-fA-F]+);?` 会贪婪吞掉 `61`（十六进制数字），得到「章 完结章」。正解：先固定长度删图标 `&#xe8[0-9a-fA-F]{2};?`，再用**强制分号**的 `&#x([0-9a-fA-F]+);` 处理其余实体。
- 正文广告两类：句内 `【<a href="...">XX站</a>】` 整块删；裸 `www.xxx.me` 水印正则删。故事自身的【滴！…】无 a 标签，不受影响。
- 发现列表封面不显示：@js `bookList` 必须把榜单模板 `div.image img@data-original`（或 src）放进 JSON 的 `coverUrl`，并在 `ruleExplore` 写 `"coverUrl":"$.coverUrl"`；只写详情页 coverUrl 不会让发现页显示封面。

## 六、验证顺序

1. LT：`mcp debug_source(keyword)` 搜索 → 详情 → 目录 → 正文；`--URL` 验章内分页；`::URL` 验发现；`check_source` 收尾。
2. E：LAN 1125 `POST /saveBookSource`（整体替换，勿读全部书源），WS 1126 `/bookSourceDebug` 分别发 `{"tag":"<bookSourceUrl>","key":"关键词"|"--URL"|"++URL"|"::URL"}`。
3. 大文件（本例 44.5KB）必须走 LAN，不要塞 MCP 单对象参数。

关联：[[方法-对照实验驱动的接口逆向与正文排版]]、`topics/legado-captcha-template-ocr.md`、`areas/manyanshu-book-source.md`。
