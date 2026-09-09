# 方法-APP接口聚合书源拆解（s.wendulou.com 小小阅读/书香之家类）

> 拆解对象：`小小阅读/书香之家app`（bookSourceUrl=https://s.wendulou.com，模板署名 20231225By_遇知，解密 by 尐哖 & landseer）
> 实测时间：2026-09-09（App 内 debug_source 全链路通过：搜索→详情→目录1441章→正文；沙箱 Python 逐接口验证）
> 文档目标：把这类「多 App 后端聚合 API」书源的全部制作经验沉淀为可复用知识，下次遇到同构站点可直接照抄。

---

## 1. 这是什么类型的站

**不是网页小说站，而是一批"看书 App"共用的后端 JSON API**。一个书源同时聚合了多个 App（小小阅读/书香之家/点点阅读/追书大师/追书大全/天天追书/小小追书/极速笔趣/笔趣阁开心版…）的数据：

- 全部接口返回 `{"code":1,"msg":"success","data":{...}}` 纯 JSON，无 HTML 页面；
- 内容多层加密（信封式动态密钥 + 字段级固定密钥两套体系，见第 4 章）；
- 同一本书聚合了多个盗版来源站（qu/us23/qk/sky/slmh…），可在阅读内一键切换；
- 同一后端服务挂在 12+ 个域名上（s.wendulou.com / s.mysignal.cn / s.chuangke.tv…），**改 bookSourceUrl 即换线路，规则零修改**。

识别特征：搜索 URL 形如 `/v4/1/lists.api?keyword=xxx&form=1`；响应是单行 JSON 且 `data.content` 是一段 base64 乱码。

## 2. 站点架构全景

### 2.1 子域名矩阵（职责分离）

一个主域名下用子域名分服务，书源里用 `source.getKey().replace('//s','//xxx')` 从注册域名推导全部子域：

| 子域 | 用途 | 推导写法 |
|---|---|---|
| s.{主域} | 搜索 API | bookSourceUrl 本身（getKey()） |
| book.{主域} | 发现/分类/书城 | `.replace('//s','//book')` |
| d.{主域} | 书籍详情/换源列表 | `.replace('//s','//d')` |
| catalog.{主域} | 目录（路径第一段=来源站ID） | `.replace('//s','//catalog')` |
| chapter.{主域} | 正文 | `.replace('//s','//chapter')` |
| res.{主域} | 封面图片 | `.replace('//s','//res')` |

> 注意 `//s` 会匹配 `https://s.` 中的 `//s`，所以必须用双斜杠做锚。这是「子域名推导」模式的核心一行：**换主域名（书源 URL）后全链路自动跟随，因为所有 URL 都从 getKey() 派生**。

### 2.2 备用域名存活状态（2026-09-09 实测）

| 域名 | 状态 |
|---|---|
| s.wendulou.com（当前） | ✅ 正常，全链路 |
| s.mysignal.cn | ✅ 存活，同后端同库（搜索深空彼岸返回 100 条） |
| s.chuangke.tv（小小阅读官方） | ✅ 存活，同后端同库 |
| s.fjwhcbsh.com | ⚠️ 返回非 JSON |
| s.hngxt.cn / s.lansheweb.com | ⚠️ SSL 证书异常（加信任可能可用） |
| s.ibbxtx.com | ⚠️ 超时 |
| s.mocaiys.com | ⚠️ 读超时 |
| s.pjxhmy.com / s.klzdp.com / s.4billion.tv / s.bzatgv.com / s.lhdqsb.cn | ❌ DNS 已失效 |

> **结论：这些 s.* 域名是同一聚合 API 的多镜像/别名。** 用同一个 package 头在存活域名上搜索返回相同数据，因此**切换 bookSourceUrl 到任一存活域名即可整体迁移**。目录/正文路径（catalog/chapter 子域）同样按新主域推导。

### 2.3 多 App 聚合关系

书源 comment 里维护着 App 清单（package 名 + 官网），header 里改一行 package 即可切换 App 身份：

```
值得阅读: com.ruffianhankin.meritreader   https://zdydapp.com
点点阅读: com.diandianbook.androidreading https://ddydapp.com
小小追书: com.xiaoxiaobook.zuiread        https://xxzs.app
小小阅读: com.xxyuedu.chasingbooks        https://xxydapps.com/xxyd/
追书大师: com.zhuishudashi.read           https://zsdsapps.com
追书大全: com.zshuall.fread               https://zsdq6.com
书香之家: com.shuxiangzhijia.xyz          https://shuxiangzhijiaapp.com
极速笔趣: com.kkmfxs.xsfmkkapp            https://biqugejisuapp.com
```

## 3. 鉴权真相（本次实测最重要的发现）

书源 header 用 @js 动态生成 4 个头 + 1 个带 package 后缀的 UA：

```js
package = "com.xxyuedu.chasingbooks";
time = Math.round(new Date()/1000);
sign = java.md5Encode(package + 1 + time + "vhjJVz1St6tK7!8n#B0MqRIuE2Dh7!C#");
JSON.stringify({
  "pt": 1, "time": time, "sign": sign, "package": package,
  "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 7_1_2 like Mac OS X) AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile/11D167 Safari/9537.53_" + package
});
```

### 3.1 逐项破坏性实测结论（矩阵实验）

| 实验 | 结果 | 结论 |
|---|---|---|
| sign 正确 | 100 条结果 | 基线 |
| **sign 填死值 deadbeef…** | **code=1 success 正常** | **sign 完全不校验** |
| 不带任何头（裸 UA） | code=1 但结果为空 | 头还是要带 |
| **UA 去掉尾部 `_{package}` 后缀** | **code=1 但 books=0** | **UA 尾部 package 后缀才是身份鉴别** |
| UA 正常、package 头换成点点阅读 | books=0 | package 决定内容分发 |

> **方法论价值：像验证"哪个参数真的被校验"这种问题，必须做逐项破坏实验（每项只改一个变量），不能照抄模板就完事。** 本例中 sign/time/pt 三个参数全是装饰，真正起作用的只有两处：`package` 请求头 + `User-Agent` 尾部的 `_{package}` 后缀。若站方未来开始严格校验 sign，模板里的算法（md5(package+pt+time+固定盐)）已经给出，无需逆向。

### 3.2 可复用要点

- 该类 API **无 Cookie、无频控**（实测连续 20+ 请求无拦截），`enabledCookieJar` 可设 false；
- UA 里的 package 后缀不可省略——这是"内容白名单"而非签名；
- 固定盐 `vhjJVz1St6tK7!8n#B0MqRIuE2Dh7!C#` 是 App 端硬编码，多个镜像域名共用。

## 4. 双层加密体系（核心难点）

### 4.1 体系 A：动态种子信封加密（搜索/详情/分类/换源列表）

服务端每次响应随机生成密钥，密文自带种子，结构：

```
base64Decode(content) = [16字节key种子(ASCII)] + [AES-256-CBC密文] + [16字节IV种子(ASCII)]
```

算法逐步拆解（已用 Python 复现并与 App 实测结果比对一致）：

1. **key 种子**：密文头 16 字节，形如 `RUMTANYX6A5SQWZX`（大写字母+数字）；
2. **IV 种子**：密文尾 16 字节，形如 `JDLCGRSEG2K4U19C`；
3. **AES key（32字节）** = `SHA256(key种子字符串)` 的 hex → 再两两转字节（等价 `digest()`）；
4. **IV（16字节）** = `md5(IV种子).hexdigest()` 是 32 个 hex **字符**，`getBytes()` 后**取前 16 个字符的 ASCII 字节**，逐位 `XOR IV种子字节 XOR 0xFF`；
5. 中间段 AES-256-CBC + PKCS5Padding 解密即得纯 JSON。

> **最大的坑在这里：`java.md5Encode()` 返回 32 位 hex 字符串，源码里 `v.getBytes()` 后只取 `i<16` 的部分——也就是 hex 字符串的前 16 个 ASCII 字符，不是 md5 的 raw digest！** 逆向时用 raw digest 做 IV 会出现"只有第一个块解坏、后续块正常"的诡异现象（CBC 特性：错 IV 只毁首块），正好可以用来定位"key 对、IV 错"。这是本次最值得记住的调试技巧。

书源里的 Legado JS 实现（存于 bookSourceComment，被各规则 eval 复用，已加注释）：

```js
var javaImport = new JavaImporter();
javaImport.importPackage(Packages.java.lang, Packages.javax.crypto.spec,
    Packages.javax.crypto, Packages.java.util, Packages.java.io);
with(javaImport) {
    function decode(str) {
        data = java.base64DecodeToByteArray(str);          // 全量字节
        datas = Arrays.copyOfRange(data,16,data.length-16); // 密文体
        // ---- key: SHA256(头16字节的字符串) 的 hex 再转32字节 ----
        k = String(Arrays.copyOfRange(data, 0, 16));        // ASCII种子
        k = java.digestHex(k,'sha-256');                    // 64位hex
        ks = []; length = k.length();
        if (length % 2 == 1) { length++; k = "0" + k; }     // 防御奇数
        for (i=0,i2=0; i<length; i+=2)
            ks[i2++] = intToByte(Integer.parseInt(k.substring(i,i+2),16));
        // ---- IV: md5 hex 字符串前16字符 XOR 尾16字节 XOR -1 ----
        i = String(Arrays.copyOfRange(data,data.length-16,data.length));
        v = java.md5Encode(i);                              // 32位hex字符串!
        bytes = i.getBytes(); bytes2 = v.getBytes();
        ivs = [];
        for (i=0; i<16; i++) ivs[i] = (bytes2[i] ^ bytes[i]) ^ (-1);
        key = SecretKeySpec(ks, "AES"); iv = IvParameterSpec(ivs);
        var cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher.init(2, key, iv);                            // 2=DECRYPT_MODE
        return String(cipher.doFinal(datas));
    }
}
function intToByte(i){ // Java byte 有符号(-128~127)，JS 0~255 需转换
    var b = i & 0xFF, c = 0;
    if (b >= 128) { c = b % 128; c = -1 * (128 - c); } else c = b;
    return c;
}
```

Python 参考实现（逆向/批量验证用）：

```python
import hashlib, base64
from Crypto.Cipher import AES
def decode(content_b64):
    data = base64.b64decode(content_b64 + "=" * (-len(content_b64) % 4))
    kseed, ivseed, ct = data[:16], data[-16:], data[16:-16]
    key  = hashlib.sha256(kseed).digest()                       # 32字节
    hexc = hashlib.md5(ivseed).hexdigest().encode()             # 32个hex字符
    iv   = bytes([(hexc[i] ^ ivseed[i]) ^ 0xFF for i in range(16)])
    pt   = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
    return pt[:-pt[-1]].decode('utf-8')                         # PKCS5去填充
```

> **注意 `String(Arrays.copyOfRange(...))` 隐含假设种子是 ASCII**（实测恒为大写字母数字）。若未来站点把种子改成非 ASCII，Java 平台默认字符集 round-trip 会失真——那就是另一场逆向了。

### 4.2 体系 B：固定密钥 AES-128（目录章名 + 正文）

目录的每一章 `name` 和正文的 `content` 用**固定密钥**单独加密（比体系 A 更老的一代接口）：

```
key = "Pxga!h*e4@T8xfOm"   (16字符 → AES-128)
iv  = "E&z!EHGLd$fli*8R"   (16字符)
模式 = AES/CBC/PKCS5Padding，输入是 base64（可能缺 = 填充）
```

规则写法（Legado 内置 4 参签名，底层 hutool `createSymmetricCrypto`）：

```
ruleToc.chapterName:  $.name@js:java.aesBase64DecodeToString(result,"Pxga!h*e4@T8xfOm","AES/CBC/PKCS5Padding","E&z!EHGLd$fli*8R")
ruleContent.content:  $..content@js:java.aesBase64DecodeToString(result,"Pxga!h*e4@T8xfOm","AES/CBC/PKCS5Padding","E&z!EHGLd$fli*8R")
```

> **`java.aesBase64DecodeToString(str,key,transformation,iv)` 的 base64 解码对缺 padding 宽容**（hutool），Python 里要手动补 `=`。正文章节 JSON 还带 `is_encrypt` 标志和 `num_words`，可用于校验。
>
> **`$..content` 递归下降 JSONPath** 在"正文包在多层对象里"的场景特别好用——不用关心确切的层级路径。

### 4.3 为什么会有两套？

推断：搜索/详情/分类是新接口（v4），每次随机密钥防通用爬虫；目录/正文沿用旧接口（固定密钥）。**做同类站逆向时，先假设"每个接口的加密方式可能不同"，逐接口验证，不要用一个解法套全部。**（本次 classify 接口用体系 A 解法解目录 name 失败就是这个原因。）

## 5. 接口清单（2026-09-09 实测）

### 5.1 搜索

```
GET https://s.{主域}/v4/1/lists.api?keyword={kw}&form=1
→ data.content（体系A解密）= {"book":[100项], "author":[搜到的作者]}
  book[]字段: book_id, name, author, ltype(大类), stype(小类), status(1=完结),
              score, words_number, image(相对路径), remark, sex, tags, form,
              chapter_count, is_search_recommend
```

- `v4/{N}` 的 N 不是页码（1/2 实测返回相同）；搜索固定 100 条/页无翻页；
- `form=1` 全量、`form=3` 部分结果、`form=2` 空（性别过滤？未深究）；
- **v1 明文回退**：`GET /v1/lists.api?keyword={kw}` 的 `data` 直接是**未加密数组**（字段同 book[]），v4 空结果时兜底。

### 5.2 详情 + 换源列表

```
GET https://d.{主域}/book/details/v4/{book_id/1000整数除法}/{book_id}.html
→ data.content 解密 = {name, author, ltype, stype, status, score, words_number,
   updated_at("2026-08-22 02:58:15"字符串), image, remark, last_chapter_name,
   source_count, view_count, fav_count, comment_number, related_data, ...}

GET https://d.{主域}/book/source/v4/{book_id/1000}/{book_id}.html
→ data.content 解密 = [ {site_id, site_name, crawl_book_id, site_path,
   site_path_reload, choose("59.71%"选用率), updated_at, last_chapter_name}, ... ]
```

> **详情 URL 的路径段 `book_id/1000`（整数除法）是分桶目录**——大量平台用这种 hash 分桶压缩 URL 目录树（晋江的 `/book2/分组号/书号` 同理）。规则里 `{{parseInt(java.getString('$.book_id')/1000)}}` 一步生成。

### 5.3 目录（catalog，路径第一段=来源站ID）

```
GET https://catalog.{主域}/{site_path}            // site_path 如 qu/298/9b/04/231.html
→ data = [ {name(体系B加密章名), url(原站真实URL泄漏!), is_content, path, updated_at(unix秒)} × N ]
```

- `url` 字段泄漏来源站真实页面地址（本例 mianhua.la），可做旁证/兜底；
- `path` 是拼到 chapter.{主域} 的正文相对路径；
- **`site_path_reload`（如 231_reload.html）返回 `{updated_at}` 单对象**，是增量检查接口——源站有更新时返回新时间戳。书源未使用它，直接用 `preUpdateJs: java.refreshTocUrl()` 整目录重拉（简单可靠）。

### 5.4 正文

```
GET https://chapter.{主域}/{章path}
→ data = {content(体系B加密), name(加密), num_words, is_encrypt}
```

### 5.5 发现/书城

```
GET https://book.{主域}/book_city/v7_more/index/1/20/{栏目1~6}/{page}.html
→ data.content 解密 = 纯数组 [{book_id,name,author,ltype,stype,status,score,image,remark,...}]
  栏目: 1每日优选 2高分好书 3真香新书 4爆肝书单 5宝藏好书 6猜你喜欢
  ⚠️ page 超界时 data.content = null（解出字面量 null）→ Legado 解析为 0 结果自然终止，无需特判

GET https://book.{主域}/classify/v4/index.html
→ data.content 解密 = {male:[{ltype_name,ltype_id,ltype_list:[{stype_name,stype_id}]}],
                       female:[...]}        // 动态分类元数据（书源不硬编码分类!）

GET https://book.{主域}/classify/v4/all/{gender 1男|2女}/{ltype_id}/{stype_id}/-1/-1/{page}.html
→ data.content 解密 = {"limit":20,"lists":[...]}    // 注意键是 lists 不是 book!
```

> **同类站把"分类树"做成接口而不是写死在书源里**——发现页规则动态拉取并生成按钮（见 6.2 模式），分类改版时书源不用更新。三个接口的列表容器键不同（book[] / 纯数组 / lists[]），书源用 JSONPath 兜底链 `$.book[*]||$..lists[*]||$.[*]` 一条规则通吃三种形态。

## 6. 书源设计模式精讲（可直接复用）

### 6.1 bookSourceComment 当 JS 公共库

`decode()` 函数存放在 `bookSourceComment` 字段（注释区），各规则需要时：

```js
eval(String(source.bookSourceComment));   // 加载公共函数到当前作用域
info = JSON.parse(decode(JSON.parse(result).data.content));
```

- 优点：导入/导出时 comment 跟着走，不依赖 jsLib 字段（旧版 App 兼容）；一处维护多处使用；
- 注意：comment 开头的说明文字必须用 `//` 或 `/* */` 包好，保证 eval 时不报错；`decode` 定义在 `with(JavaImporter){}` 块里，eval 后暴露到顶层。

### 6.2 动态分类发现页（不硬编码分类）

```js
// exploreUrl @js: 关键骨架
sort=[];
burl = source.getKey().replace('//s','//book');
push=(title,url,type1,type2)=>sort.push({title:title, url:url,
    style:{layout_flexGrow:type1, layout_flexBasisPercent:type2}});

// ① 固定推荐栏目
tj = ["每日优选","高分好书","真香新书","爆肝书单","宝藏好书","猜你喜欢"];
tj.map((title,type)=>push(title, burl+`/book_city/v7_more/index/1/20/${type+1}/{{page}}.html`, 1, 0.25));

// ② 动态分类树（加密接口 → 解密 → 男女频遍历）
eval(String(source.bookSourceComment));
fl_url = burl + "/classify/v4/index.html";
fl = JSON.parse(decode(JSON.parse(java.ajax(fl_url)).data.content));
[["❤男频-分类","1",fl.male], ["❤女频-分类","2",fl.female]].map(([title,gender,list])=>{
    push(title, null, 1, 1);          // url=null 的一级项 = 纯分组标题行!
    list.map(($)=>{
        push("@"+$.ltype_name+"@", burl+`/classify/v4/all/${gender}/${$.ltype_id}/-1/-1/-1/{{page}}.html`, 1, 1);
        $.ltype_list.map(($,index)=>{
            url = burl+`/classify/v4/all/${gender}/${$.ltype_id}/${$.stype_id}/-1/-1/{{page}}.html`;
            // 按 3 列网格排版：整除3的行 flexBasisPercent=0.25，尾巴 0.29
            if($.ltype_list.length>3 && $.ltype_list.length!=4){
                push(title,url, index+1<=len-len%3 ?1:0, index+1<=len-len%3?0.25:0.29);
            } else push(title,url,1, len==4?0.4:0.25);
        });
    });
});
JSON.stringify(sort);
```

要点：
- **`{title, url:null}` 的项是分组标题行**（不可点，纯排版）；
- `style.layout_flexGrow / layout_flexBasisPercent` 控制 Flex 网格（0.25=四列，0.4=两列半，余数行给 0.29 补齐）；
- `"@"+名+"@"` 只是视觉装饰；
- ⚠️ 这段代码用了箭头函数/模板串/数组解构参数，**在本 App 的 Rhino 下实测可用**；若在更老的 Legado 分发版遇到解析错误，改 ES5 写法（function/字符串拼接）。

### 6.3 换源聚合（本源的灵魂）

详情页 `ruleBookInfo.init` 做了四件事：

```js
eval(String(source.bookSourceComment));
result = JSON.parse(decode(JSON.parse(result).data.content));   // 解密详情
source_url = baseUrl.replace('/details/','/source/');           // 详情URL→换源URL
$ = JSON.parse(decode(JSON.parse(java.ajax(source_url)).data.content));  // 换源列表
v = String(book.getVariable("custom"));                          // 读书籍变量
x = v.match(/^\d+$/) ? v : 0;
x = parseInt(x) < $.length ? x : 0;                              // 越界回退0
result.tocUrl  = source.getKey().replace('//s','//catalog')+"/"+$[x].site_path;
result.image   = source.getKey().replace('//s','//res')+"/"+result.image;
result.updated_at = $[x].updated_at;
result.last_chapter_name = $[x].last_chapter_name;
if ($.length>1) {   // 把全部来源写进 remark，用户看得见
    y = '\n📌使用说明： 根据序号设置书籍变量后刷新来切换来源(默认0)\n🎯当前源：序号🔺'+x+'🔻【'+$[x].site_name+'】'+(x==0?' (默认)':'');
    for (i in $) y += '\n❤序号🔺'+i+'🔻【'+$[i].site_name+'】 \n选用率：'+$[i].choose+' \n更新时间： '+$[i].updated_at+'\n最新章节： '+$[i].last_chapter_name;
    result.remark += y;
}
result = JSON.stringify(result);
```

机制拆解：
1. **书籍变量**（书架长按书籍→编辑变量，填数字）选定来源序号 `custom`，init 里读取并校验（非数字/越界→0）；
2. `tocUrl` 动态指向所选来源的 catalog 路径 → **目录、正文全部跟随所选来源**（catalog/chapter 路径第一段是来源站ID）；
3. 所有来源的选用率/更新时间/最新章节写入 `remark` 展示在详情页，用户可决策；
4. `ruleToc.preUpdateJs: java.refreshTocUrl()` → 用户改变量后点"刷新目录"，Legado 重新执行详情 init（源码确认：refreshTocUrl 只能在 preUpdateJs 里调，内部重跑 `WebBook.getBookInfoAwait`，且 isFromBookInfo 时跳过防递归）→ **换源生效，无需删书重加**。

> 这是"单书源内多站聚合"的标准姿势：**tocUrl 不写死，init 里按变量拼**。比起做 N 个书源，用户体验好一个量级。

### 6.4 搜索词缓存 + 明文接口回退

```js
// searchUrl 里把关键词存起来
"/v4/1/lists.api?keyword={{java.put('key',key)}}&form=1"

// ruleSearch.bookList JS：v4 空结果自动换 v1 明文接口
eval(String(source.bookSourceComment));
result = JSON.parse(decode(JSON.parse(result).data.content));
if (baseUrl.match(/\?keyword=/)) {              // 只在搜索场景（发现页不回退）
    if (result.book[0] == undefined) {
        sourl = source.getKey()+"/v1/lists.api?keyword="+java.get('key');
        result = JSON.parse(java.ajax(sourl)).data;   // v1 的 data 是明文数组
    }
}
result = JSON.stringify(result);

// 之后的三通道兜底（同一规则适配三种列表容器）：
$.book[*]||$..lists[*]||$.[*]
```

- `java.put(key,value)`（AnalyzeRule.kt:853）沿 chapter→book→ruleData→source 缓存链存值，`java.get(key)`（:872）同链读取——**在 searchUrl 里存、在 bookList 里取**，避免解析 baseUrl 反推关键词；
- `baseUrl.match(/\?keyword=/)` 判定"当前是搜索而非发现"，防止发现页误走回退；
- `$.[*]` 兜住 v1 明文数组与 book_city 纯数组；`$..lists[*]` 兜住 classify 的 `{limit,lists}` 包装。

### 6.5 kind 多行 {{}} 模板（分类/状态/评分/日期一次拼齐）

```
"kind": "{{$.ltype}}\n{{$.stype}}\n{{r=java.getString('$.status');\nif(r!=\"\") r=='1'?'完结':'连载';}}\n{{r=java.getString('$.score');\nr!=0.0?r+'分':\"\";}}\n{{$.updated_at## .*}}"
```

- **多行 = 多个 kind 项**，Legado 最终 `getStringList().joinToString(",")`；
- 每行独立 `{{}}` 表达式：字段直接取 / 三元判断（status==1→完结） / 条件拼接（score!=0.0→"8.74分"） / 正则裁剪（`$.updated_at## .*` 去掉时间只留日期）；
- **字段不存在时 `java.getString('$.x')` 返回空串 → if 不执行 → 该行输出空**，天然容错（搜索结果没有 score/status 字段也不会报错）。
- ⚠️ 结合既往经验（lzjxx/rrssk）：kind 字段在 BookList 走 getStringList 通道，**值尽量用纯 `$.x` 直取或简单模板**，避免复杂 JS 拼接在真实环境静默变空。

### 6.6 简介断句换行

```
"intro": "$.remark##(^|[。！？]+[”」）】]?)##$1<br>"
```

在句尾标点（可跟引号括号）后插 `<br>`，长简介自动断行；`^` 保证句首不空。可复用于任何长文本美化。

### 6.7 封面域推导

```
搜索: "coverUrl": "{{source.getKey().replace('//s','//res')}}/{{$.image}}"
详情: init 里 result.image = source.getKey().replace('//s','//res')+'/'+result.image
```

图片相对路径（`qd/66/14/xxx.jpg` 第一段是来源站）+ res 域推导，与换源体系一致。

### 6.8 目录时间格式化

```
"updateTime": "{{java.timeFormatUTC(java.getString('$.updated_at')*1000,'yyyy-MM-dd',8)}}"
```

目录接口的 updated_at 是 unix 秒 → ×1000 → UTC+8 格式化（JsExtensions.timeFormatUTC(time,format,sh)）。

## 7. 踩坑实录（按付出代价排序）

1. **md5Encode 是 hex 不是 raw digest**：IV 派生用 `md5(seed).hexdigest()[:16]` 的 ASCII 字节；用 raw digest 会出现"首块 16 字节乱码、后续正常"——**CBC 错 IV 只毁首块**，反过来说：看到首块乱码就查 IV，全乱才查 key。
2. **两套加密并存**：目录 name/正文 content 是固定密钥（AES-128），别拿动态种子解法去套；`is_encrypt` 字段是明牌提示。
3. **base64 可能缺 `=` 填充**：Java/hutool 宽容，Python 必须 `+ "=" * (-len(s) % 4)`，否则 `Incorrect padding`。
4. **响应体是 gzip**：urllib 不会自动解压（即使 Accept-Encoding: identity，部分接口仍返回 gzip），Python 探测 `raw[:2]==b'\x1f\x8b'` 后 `gzip.decompress`；Legado 的 java.ajax 自动处理无需操心。
5. **book_city 超页返回 content=null**：解出字符串 `"null"`，`$.book[*]` 取不到 → 0 结果自然终止分页，不需要特判；但自己写解密代码时要 `json.loads("null")` 得 None 的防御。
6. **`v4/{N}` 不是页码**，搜索无翻页；`form` 参数影响结果集（1 全量）。
7. **`classify/v4/all` 返回 `{limit,lists}`** 与搜索的 `{book,author}` 容器不同——三通道 bookList 就是为此设计的，仿写时别丢 `$..lists[*]`。
8. **sign/time 参数实测不校验**，但别删——保留模板原样是向后兼容的做法（万一站方开启校验）。
9. **目录站点路径第一段=来源站ID**（qu/us23/qk…），同一 catalog/chapter 域名服务所有来源站；换源时只需换 site_path，不用换域名。
10. **detail 接口的 updated_at 是字符串**（"2026-08-22 02:58:15"），catalog 的 updated_at 是 unix 秒——同名不同型，格式化规则要分别写。

## 8. 同类站制作 Checklist

遇到"App 的 JSON API"站，按此流程：

1. 抓包/反编译 App 拿到：接口清单、header 集、签名算法、加密方式（frida/小辣椒/jadx 找 `sign`、`AES`、`Cipher` 关键字）；
2. **破坏性实验**逐项验证 header 必要性（改一个发一次）——别给不校验的参数写复杂逻辑，也别漏掉真正校验的（本例是 UA 尾缀！）；
3. 逆向加密：先看密文结构（有没有固定头尾 16 字节？base64 长度是否 16 倍数？），再定 key 派生；**用"首块是否正常"区分 key 错/IV 错**；
4. 用 Python 复现解密并与 App 端 `java.aesBase64DecodeToString`/`decode()` 比对一致后再写规则；
5. 书源结构：header @js 动态签名 → searchUrl 存关键词 → bookList 三通道 → init 换源 → preUpdateJs 刷新；
6. 分类树走接口不硬编码，发现页动态生成 + Flex style 网格；
7. 全部子域从 getKey() 推导，为镜像域名迁移留后路；
8. App 内 debug_source 全链路实测（搜索→详情→目录→正文→换源变量切换）才算完成。

## 9. 2026-09-09 实测档案

- 搜索《深空彼岸》：100 条，bookUrl=`https://d.wendulou.com/book/details/v4/736/736673.html`
- 详情：10 个来源站（qu 59.71% 选用率，更新 2026-08-22），tocUrl=`https://catalog.wendulou.com/qu/298/9b/04/231.html`
- 目录 1441 章，章名解密正常（第一章 旧土）
- 正文 `https://chapter.wendulou.com/qu/298/9b/04/231/1690.html` 解密正常，约 2.6KB/章
- 发现页（book_city 每日优选）13 本 → 详情 → 目录 3934 章 → 正文全通
- 换源演示：详情页 remark 列出全部序号/选用率，设书籍变量即切换

成品书源：`examples/小小阅读书香之家app_s.wendulou.com.json`（与 App 内版本一致）
