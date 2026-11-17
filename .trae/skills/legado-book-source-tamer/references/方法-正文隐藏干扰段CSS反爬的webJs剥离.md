# 方法：正文隐藏干扰段 CSS 反爬的 webJs 剥离

> 案例：哔哩轻小说 www.bilinovel.net，2026-11-17。用户连续两次纠错后定案。

## 适用症状

- 正文段落"排序错位"：编号列表（一/二/三/四）被拆散、对话上下句颠倒、简介段落穿插错乱
- 或正文出现**重复段落**（同一句话出现多次）
- 5 次重复抓取顺序完全一致（服务端固定，不是随机）

## ★核心定性（别走弯路）

真相不是"段落被 JS 重排"，而是：

**服务端在正文里混入隐藏干扰段，并在 `<head>` 注入 CSS 把它们藏起来：**
```css
#acontent p[data-k123456789] { position: absolute; transform: scale(0); }
```

- 真实浏览器按 CSS 隐藏这些段 → 剩下的段落**顺序本来就正确**
- Legado `java.ajax` 拿不到这套 `<style>`（或拿到 body 但没执行 CSS）→ 全部显示 → 又重复又乱序

### 被证伪的错误方向（我踩过的坑，别再走）

1. ❌ "段落 Fisher-Yates 重排，需要逆洗牌" —— 去解混淆、拟合 PRNG（9302/49397/233280）全部失败，浪费大量时间
2. ❌ "内容判据（三四要素间距）触发 webView 重抓" —— 依赖具体书名语句，插图章没有这些词，判据不命中
3. ❌ "段落去重保留首次即可" —— 只能去掉重复文本，**修不好被隐藏段撑乱的顺序**（用户当场指出简介后半段仍乱）
4. ❌ 在 webJs 里 `dispatchEvent(scroll/wheel)` 想触发站点 JS 重排 —— 无效

## ★正解：webJs 在浏览器内按 CSS 规则剥离隐藏段

关键机制：**URL 选项 `webJs` 的返回值就是 `java.ajax` 的 body**（普通 webView 抓 DOM 拿不到正确结果）。

```js
var WJS = '(function(){'
 +'var hid={};'
 +'for(var k=0;k<document.styleSheets.length;k++){try{'
 +'var rs=document.styleSheets[k].cssRules;'
 +'for(var j=0;j<rs.length;j++){var css=rs[j].cssText||"";'
 +'var mm=css.match(/data-k(\\d+)[^}]*scale\\(0\\)/);if(mm)hid[mm[1]]=1;}}catch(e){}}'
 +'var ac=document.getElementById("acontent");if(!ac)return "NOAC";'
 +'var ps=ac.querySelectorAll("p");'
 +'for(var i=ps.length-1;i>=0;i--){var p=ps[i],dk="";'
 +'for(var a=0;a<p.attributes.length;a++){var nm=p.attributes[a].name;'
 +'if(nm.indexOf("data-k")===0)dk=nm.substring(6);}'
 +'if(hid[dk])p.parentNode.removeChild(p);}'
 +'return ac.innerHTML;})()';
var html = String(java.ajax(curUrl + ',{"webView":true,"webViewDelayTime":500,"webJs":'+JSON.stringify(WJS)+'}'));
// html 就是已剔除隐藏干扰段的干净正文
```

### 实现要点

| 点 | 说明 |
|---|---|
| webJs 返回值 | 即 ajax body，必须 `return ac.innerHTML`，不能指望默认抓 DOM |
| CSS 来源 | `document.styleSheets[k].cssRules[].cssText`，跨 sheet 遍历，try/catch 包住（跨域 sheet 读 cssRules 会抛） |
| 隐藏判据 | `/data-k(\d+)[^}]*scale\(0\)/`：`position:absolute;transform:scale(0)` |
| data-k 属性名 | 是 `data-k123456789`（数字直接拼进属性名，**不是** `data-k="123"`），用 `attr.name.indexOf('data-k')===0` 取，substring(6) 得数字 |
| 删除方向 | 从后往前 `removeChild`，避免索引错位 |
| URL 拼接 | 从 result 的 `ReadParams`（`url_home/articleid/chapterid/page`）拼当前页 URL，跟随线路域名，不写死 |
| 兜底 | webView 失败要 fallback 到普通 `java.ajax(url)` 解析，保证不崩 |
| 图片 | 服务端返回的多是 `data-src`+`src=/images/sloading.svg` 懒加载，要转 `data-src`→`src`、去占位 src、去 `lazyload` class；多图挤同一 `<p>` 时拆成每张独立 `<p>` |
| 广告 | CSS 隐藏段剥离后可能混入 `(adsbygoogle...).push({})` 脚本节点，用正则清掉 |

## 验证方法

对同一站点找两种章节各一：
1. **长正文章**（无重复段但顺序乱）——判据：某固定编号项（如"一/二/三/四"）间距应从数千字符缩到相邻
2. **插图/特殊章**（有重复段且顺序乱）——判据：被拆散的简介应恢复成连贯叙述

用 `debug_source --<章节URL>` 看正文输出，两段都连贯即全绿。**不要只看"重复段没了"就宣布修好**（这是 v3 的教训）。

## 通用教训

- "乱序"先做**服务端 CSS 隐藏规则**检查，再考虑 JS shuffle；很多站点的反爬是"隐藏干扰段"而非"真重排"
- 用户连续纠错时，前一次的"看起来对了"要全部推翻重查，不要修补错误假设
- 沙盒机房 IP 常被此类站判机器人：正文截断、webView 60s 超时；结论必须回真机验证，不要伪称全绿
- 图床可能需 Referer（无 Referer 403，带 `Referer: https://主域/` 200）；书源 header 要带正确 Referer
