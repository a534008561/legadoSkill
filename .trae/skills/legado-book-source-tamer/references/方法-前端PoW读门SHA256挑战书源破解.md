---
name: 方法-前端PoW读门SHA256挑战书源破解
description: 站点正文改前端JS动态加载+SHA256 PoW读门(challenge→base64url proof→unlock→Cookie clearance)的通用逆向与书源实现配方，附书海阁261119实战
aliases: [PoW读门, SHA256挑战, read-gate, queryReadPage, 正文动态加载, 书海阁改版]
---

# 前端 PoW 读门（SHA-256 挑战）书源破解配方

> 261119 书海阁(book.washai.net)站点改版实战提炼。跨站可复用：凡「章节页正文占位 loading + JS 调 API 取正文 + 需挑战」的站点均适用。

## 一、识别信号（先定性再动手）

章节页 HTML 出现以下任一，即说明正文不再 SSR 直出，旧 CSS 正文规则必然取空：

1. `#showReading`/`#content` 内是「正文加载中...」占位（`<div class="readGateLoading" id="readGateStatus">`）。
2. 底部有 `<script type="application/json" id="readPageBootstrap">{...,"readLocked":true}</script>`。
3. 页面引用 `reader_content.js`/`book_content_page.js` 之类 reader JS。

→ 去该 JS 搜 `ajax`/`fetch`/`challenge`/`unlock`/`digest`/`sha256`/`/book/query`，能找到完整协议。

## 二、四步协议（书海阁实测，模式通用）

| 步骤 | 请求 | 关键参数 | 返回 |
|---|---|---|---|
| ①取正文 | GET `/book/queryReadPage?bookId=&bookIndexId=&contentFormat=html` | 头见坑1 | `data.contentHtml`（readLocked:true 则需②） |
| ②挑战 | POST `/book/read/challenge` | body `bookId=&bookIndexId=` | `data.challenge` + `data.waitMs`(500) |
| ③证明 | 纯前端 SHA-256 | 输入=`"<前缀>/read-gate-proof/v1"+NUL+challenge+NUL+browserToken` | proof=SHA256 的 **base64url** |
| ④解锁 | POST `/book/read/unlock` | body `bookId=&bookIndexId=&challenge=&proof=` | Set-Cookie `novel_read_clearance`（expiresInSec=1200） |

⑤再调①，readLocked 变 false，contentHtml 出全文。

★关键：clearance Cookie 全站/长期有效——解锁任一章后 TTL(实测20分钟)内所有章节①直接返回正文。规则必须「先①，locked 才②③④⑤」，不能每章无脑全走。

## 三、三个必踩的坑

### 坑1：JSON API 头缺一即 403「请求无效」
必须同时带：`X-Browser-Token`(=Cookie novel_browser_token) + `X-Requested-With: XMLHttpRequest` + `Referer`=章节页完整URL + `Origin`=站点根 + `Accept: application/json, text/javascript, */*; q=0.01`。实测仅 token 无 Referer/Origin → 403；齐全 → 200。token Cookie 由任意 SSR 页 Set-Cookie 下发，冷启动访问首页/章节页自动获得，无需登录。

### 坑2：proof 的 base64url 与 NUL 分隔
分隔符是 `String.fromCharCode(0)`(NUL)，不是空格/竖线。`java.digestBase64Str(input,'SHA-256')` 返回标准 base64，须 `.replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/g,'')` 转 base64url。站点用 WebCrypto subtle.digest+btoa，语义一致。

### 坑3：给 java.ajax 单次请求加头 = UrlOption
`java.ajax(url+','+JSON.stringify({headers:{...},method:'POST',body:'...'}))`。源码 `AnalyzeUrl.kt`：`paramPattern=Pattern.compile("\\s*,\\s*(?=\\{)")`，URL 尾部 `,{...}` 解析为 UrlOption，headers 合并进 headerMap。这是唯一写法——`java.ajax(url, headerStr)` 两参不存在（报「找不到方法 ajax(string,string)」）。

## 四、书源实现骨架（ruleContent @js）

```js
@js:(function(){
  var url=String(baseUrl||''); // 内容环境 baseUrl=章节URL
  var m=url.match(/\/book\/(\d+)\/(\d+)\.html/);
  if(!m) return '<p>无法解析章节地址</p>';
  var bid=m[1],cid=m[2],base='https://book.washai.net';
  function fetch(api,isPost,body){
    var tk=String(java.getCookie(base,'novel_browser_token')||'');
    var H={'X-Browser-Token':tk,'X-Requested-With':'XMLHttpRequest',
           'Referer':base+'/book/'+bid+'/'+cid+'.html','Origin':base,
           'Accept':'application/json, text/javascript, */*; q=0.01'};
    var opt={headers:H};
    if(isPost){opt.method='POST';opt.body=body;
      opt.headers['Content-Type']='application/x-www-form-urlencoded;charset=UTF-8';}
    try{return String(java.ajax(api+','+JSON.stringify(opt))||'');}catch(e){return '';}
  }
  var tk=String(java.getCookie(base,'novel_browser_token')||'');
  if(!tk) java.ajax(base+'/book/'+bid+'/'+cid+'.html'); // 冷启动补 token
  var raw=fetch(base+'/book/queryReadPage?bookId='+bid+'&bookIndexId='+cid+'&contentFormat=html',false,'');
  var j=JSON.parse(raw); if(j.code!==200||!j.data) return '<p>加载失败</p>';
  var data=j.data;
  if(data.readLocked){
    var ch=JSON.parse(fetch(base+'/book/read/challenge',true,'bookId='+bid+'&bookIndexId='+cid));
    var wait=parseInt(ch.data.waitMs||0,10); if(wait>0&&wait<5000){var end=Date.now()+wait;while(Date.now()<end){}}
    var tk2=String(java.getCookie(base,'novel_browser_token')||'');
    var input='go-novel/read-gate-proof/v1'+String.fromCharCode(0)+ch.data.challenge+String.fromCharCode(0)+tk2;
    var b64=String(java.digestBase64Str(input,'SHA-256')||'');
    var proof=b64.replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/g,'');
    var ub='bookId='+bid+'&bookIndexId='+cid+'&challenge='+encodeURIComponent(ch.data.challenge)+'&proof='+encodeURIComponent(proof);
    fetch(base+'/book/read/unlock',true,ub);
    var raw2=fetch(base+'/book/queryReadPage?bookId='+bid+'&bookIndexId='+cid+'&contentFormat=html',false,'');
    try{var j2=JSON.parse(raw2);if(j2.code===200&&j2.data)data=j2.data;}catch(e3){}
  }
  var html=String(data.contentHtml||'').replace(/<script[\s\S]*?<\/script>/gi,'').replace(/<style[\s\S]*?<\/style>/gi,'');
  return html||'<p>本章暂无内容</p>';
})()
```

## 五、配套：搜索/发现提速与全局限速

- **搜索慢**：有 JSON 列表 API(如 `/book/searchByPage?keyword=&page=`)则改 `@js searchUrl` 注入头 + JSONPath 列表规则(`$.data.list`)，比 SSR 大页快一倍。JSON 对象在 Rhino 用 `result.get('key')` 取值。
- **发现不显示**：源码 `ExploreShowViewModel.loadCategories()` 会过滤 `url.isNullOrBlank()` 的项；静态 exploreUrl JSON 数组里**不要放空 url 的分组标题项**，每项都给真实 url。
- **取消全局 concurrentRate**：PoW 正文需多次内部请求，全局限速会乘倍拖慢；若站点无搜索限频(common.js 无 search_delay/setTimeout 节流)则删掉 concurrentRate。

## 六、交付前自检（本次踩坑）

1. **逐条 eval 语法自检**：MCP 保存巨 JSON 时手工转录 `@js` 极易漏括号。用 `eval(String(source.规则).replace(/^@js:/,''))`（eval_js 先补 `var result/baseUrl/key/page`）确认每条编译通过。本次 bookUrl 漏一个 `}` 导致全链搜索字段全空。
2. **debug 429 ≠ 规则错**：高频自测 unlock 触发读门冷却返回 429，真实阅读 20 分钟才解锁一次不会发生；规则内遵守 waitMs 即可。
3. **debug 日志只显示正文首段**：别因首段像 fallback 就误判，用 eval_js 直接跑规则返回全长交叉验证。
4. 冷启动(clear_cookies)后跑一次全链 debug，确认 token 自动补齐 + 正文完整。
