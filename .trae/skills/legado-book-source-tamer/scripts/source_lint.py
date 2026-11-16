#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""书源落库前静态门禁（261116 家族级隐患批量修复沉淀，全部对应实际踩过的坑）

用法:
  python3 scripts/source_lint.py a.json [b.json ...]        # 仅本地静态检查
  python3 scripts/source_lint.py --peers p1.json p2.json --devices http://IP:1122,http://IP:1125 x.json

检查项：
  G1 多文件之间 bookSourceUrl 不得相同（Legado 以此为主键，相同=推送即静默覆盖对方）
  G2 header 里不得出现 Accept-Encoding（手写会关闭 OkHttp 透明解压；CDN 可能无视 identity 照样 gzip）
  G3 不得残留 *_LIST_LIST 之类的占位符拼接笔误
  G4 header 有 User-Agent 时，规则里不得再引用未定义的 jsLib 函数（@js 段扫一遍）
  G5 凡出现 id.slice(0,-N) 的按位数切前缀 URL 构造，必须有 len(id)<=N 的边界处理（DPRE/DPATH 或等价）
  G6 建议项：bookUrlPattern / concurrentRate / 跨页状态键是否含页码（indexOf('.html') 写法）
  G7 顶层 return 检查：@js 段必须是 IIFE 包裹（Rhino 顶层 return 非法）
"""
import json, re, sys, urllib.request, urllib.parse

def load(p):
    return json.load(open(p, encoding='utf-8'))

def js_bodies(src):
    out = []
    for grp in ('ruleSearch', 'ruleBookInfo', 'ruleToc', 'ruleContent', 'ruleExplore'):
        for k, v in (src.get(grp) or {}).items():
            if isinstance(v, str) and v.startswith('@js:'):
                out.append((grp + '.' + k, v[4:]))
    for k in ('exploreUrl', 'loginUrl', 'jsLib'):
        v = src.get(k)
        if isinstance(v, str):
            if v.startswith('@js:'): out.append((k, v[4:]))
            elif v.startswith('<js>'): out.append((k, v[4:v.rfind('</js>')]))
            else: out.append((k, v))
    return out

def lint(path, peers=None):
    src = load(path); errs = []; warns = []
    name = src.get('bookSourceName', '?'); key = src.get('bookSourceUrl', '')
    blob = json.dumps(src, ensure_ascii=False)
    # G1
    for other, okey in (peers or []):
        if okey and okey == key:
            errs.append('G1 bookSourceUrl 与「%s」完全相同(%s)：推送会静默覆盖对方源' % (other, key))
    # G2
    try:
        h = json.loads(src.get('header') or '{}')
        if any(k.lower() == 'accept-encoding' for k in h):
            errs.append('G2 header 含 Accept-Encoding：会关闭 OkHttp 透明解压，CDN 可能无视 identity 仍返回 gzip')
    except Exception as e:
        errs.append('G2 header 不是合法 JSON: %s' % e)
    # G3
    bad = re.findall(r'[A-Za-z]{2}_LIST_LIST|[A-Za-z]+_[A-Z]{2}_LIST\b', blob)
    if bad: errs.append('G3 疑似占位符拼接笔误: %s' % sorted(set(bad)))
    # G4 未定义函数引用（定义可能分散在 jsLib / loginUrl / 各规则体内；先把注释剥掉再找引用）
    def strip_comments(t):
        t = re.sub(r'/\*[\s\S]*?\*/', ' ', t or '')
        t = re.sub(r'^\s*//.*$', ' ', t, flags=re.M)
        return t
    src_all = '\n'.join([src.get('jsLib') or '', src.get('loginUrl') or ''] + [b for _, b in js_bodies(src)])
    defined = set(re.findall(r'function\s+([A-Za-z_]\w*)\s*\(', src_all))
    builtin = {'JSON', 'Math', 'String', 'Number', 'Array', 'Object', 'Boolean', 'encodeURIComponent',
               'decodeURIComponent', 'parseInt', 'parseFloat', 'isNaN', 'Packages', 'java', 'source',
               'baseUrl', 'result', 'book', 'chapter', 'key', 'page', 'title', 'src', 'infoMap'}
    used = set()
    for tag, body in js_bodies(src):
        used |= set(re.findall(r'\b([A-Za-z_]\w*)\s*\(', strip_comments(body)))
    miss = sorted(u for u in used - defined - builtin
                  if re.match(r'^(D|F|P2|P8|EX|EXD|DPRE|DPATH|MK|MN|MC|CVAR|SEL|SRCLIST|OBJS|BOOKS|U8|D8|[A-Z]{2}_.*)$', u)
                  or u.endswith('_LIST'))
    if miss: errs.append('G4 引用了未定义函数: %s' % miss)
    # G5 slice(0,-N) 边界：逐段检查（整包里有 DPRE 不代表每处都用了它）
    for tag, body in js_bodies(src) + [('jsLib', src.get('jsLib') or ''), ('loginUrl', src.get('loginUrl') or '')]:
        for line in strip_comments(body).split('\n'):
            m = re.search(r'([A-Za-z_$][\w$.]*(?:\([^)]*\))?)\.slice\(0,\s*-(\d+)\)', line)
            if not m: continue
            n = m.group(2)
            # 只有「按位数切前缀来拼 URL 路径」才是危险形态：同行出现 .html 或 '/'+id 之类的路径拼接
            looks_like_url_build = ('.html' in line) or re.search(r"\+\s*'/?'\s*\+", line) or ('v4/' in line) or ('/book/' in line)
            if looks_like_url_build and 'DPRE' not in line and 'DPATH' not in line and ('length>' + n) not in line.replace(' ', ''):
                errs.append('G5 %s: `%s...slice(0,-%s)` 直接拼 URL，id<=%s 位时前缀为空 -> `//` 死链；应走 DPRE()/DPATH()' % (tag, m.group(1), n, n))
    # G6 建议项
    if not src.get('bookUrlPattern'):
        warns.append('G6 缺 bookUrlPattern：发现页空列表回退时可能收下幽灵条目，且换源/导入识别变弱')
    if not src.get('concurrentRate'):
        warns.append('G6 缺 concurrentRate：无节流，批量翻页/换源有风控敞口')
    el = src.get('ruleExplore', {}).get('bookList', '') or ''
    if "indexOf('.html')" in el:
        errs.append('G6 跨页状态键用 indexOf(\'.html\') 截断 -> 页码会留在 key 里，终止逻辑失效；应截到最后一个 /')
    # G7 顶层 return
    def top_level_return(txt):
        d = 0; i = 0; q = None; esc = False; n = len(txt)
        while i < n:
            ch = txt[i]
            if q:
                if esc: esc = False
                elif ch == '\\': esc = True
                elif ch == q: q = None
                i += 1; continue
            if ch in ('"', "'"): q = ch; i += 1; continue
            if ch == '/' and i + 1 < n and txt[i+1] == '/':
                j = txt.find('\n', i); i = n if j < 0 else j; continue
            if ch == '/' and i + 1 < n and txt[i+1] == '*':
                j = txt.find('*/', i); i = n if j < 0 else j + 2; continue
            if ch == '{' or ch == '(' or ch == '[': d += 1
            elif ch == '}' or ch == ')' or ch == ']': d -= 1
            elif d == 0 and txt.startswith('return', i) and (i == 0 or not (txt[i-1].isalnum() or txt[i-1] == '_')) \
                 and (i + 6 >= n or not (txt[i+6].isalnum() or txt[i+6] == '_')):
                return True
            i += 1
        return False
    for tag, body in js_bodies(src):
        if top_level_return(body):
            errs.append('G7 %s 存在顶层 return：Rhino 把整段当脚本求值，顶层 return 报「返回的值无效」——请用 (function(){...})() 包裹' % tag)
    return name, key, errs, warns

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    peers, devices = [], []
    if '--peers' in sys.argv:
        i = sys.argv.index('--peers'); ps = []
        while i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
            ps.append(sys.argv[i + 1]); i += 1
        for p in ps: peers.append((load(p).get('bookSourceName', p), load(p).get('bookSourceUrl', '')))
        args = [a for a in args if a not in ps]
    if '--devices' in sys.argv:
        i = sys.argv.index('--devices')
        devices = sys.argv[i + 1].split(','); args = [a for a in args if a != sys.argv[i + 1]]
    bad = 0
    for p in args:
        if p.endswith('.py'): continue
        name, key, errs, warns = lint(p, peers)
        print('◆ %s  「%s」  key=%s' % (p.split('/')[-1], name, key))
        for e in errs: print('   ✗', e); bad += 1
        for w in warns: print('   ⚠', w)
        if not errs and not warns: print('   ✓ 静态门禁全通过')
    for base in devices:                      # 主键占用体检（真机）
        tok = 'a7894563'
        for p in args:
            if p.endswith('.py'): continue
            key = load(p).get('bookSourceUrl', '')
            try:
                r = urllib.request.Request(base.rstrip('/') + '/getBookSource?url=' + urllib.parse.quote(key, safe=''),
                                           headers={'Content-Type': 'application/json', 'x-legado-token': tok})
                cur = json.loads(urllib.request.urlopen(r, timeout=20).read().decode('utf-8', 'replace')).get('data')
            except Exception as e:
                print('   ! %s 查询失败 %s' % (base, e)); continue
            if not cur: print('◆[%s] %s -> 主键空闲（新增安全）' % (base, key))
            elif cur.get('bookSourceName') == load(p).get('bookSourceName'):
                print('◆[%s] %s -> 同名更新（安全）' % (base, key))
            else:
                print('◆[%s] %s -> ✗ 主键被「%s」占用，禁止盲推' % (base, key, cur.get('bookSourceName'))); bad += 1
    print('\n结论：', '存在 %d 项必须修复' % bad if bad else '全通过，可推送（仍建议再跑 Rhino 编译门禁与 check_source）')
    print('设备侧编译门禁片段：对每段 @js 执行  try{new Function(jsBody)}catch(e)=>语法错误')
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
