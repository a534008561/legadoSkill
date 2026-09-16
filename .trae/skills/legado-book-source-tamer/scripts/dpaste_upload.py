#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dpaste 上传 + 字节级校验 + 生成 Legado 深链（深链保存书源通道）

用法：
    python3 dpaste_upload.py my_source.json                # 默认 365 天
    python3 dpaste_upload.py my_source.json --expiry 30
    python3 dpaste_upload.py my_source.json --no-verify    # 跳过回读校验（慎用，见 K5）
    python3 dpaste_upload.py my_source.json --deeplink-only URL

对应文档：references/方法-深链保存书源与dpaste通道.md

★ 要点（踩过的坑，勿改）：
  - API 必须带尾斜杠 https://dpaste.com/api/v2/   （漏了返回 API 文档 HTML，200）
  - 过期字段名是 expiry_days（1~365）；写 expiration_days 会静默变成默认 7 天
  - raw 链接 = 返回 URL + ".txt"（不是 .raw）
  - 匿名粘贴公开且无法删除 → 别传含账号/密码/Cookie/token 的内容
  - 只允许拉一次 raw（>1 req/s 会 429 HTML → 导入器报「XML 语法错误」）
"""

import argparse
import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://dpaste.com/api/v2/"          # ★必须带尾斜杠
UA = {"User-Agent": "legado-deeplink/1.0"}  # dpaste ToS 要求带 UA
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def upload(content_bytes, expiry=365, syntax="json", title=None):
    """上传内容，返回 (item_url, raw_url)。"""
    params = {
        "content": content_bytes.decode("utf-8"),
        "syntax": syntax,
        "expiry_days": str(expiry),         # ★正确键名
    }
    if title:
        params["title"] = title
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(API, data=data, headers=UA)
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=CTX)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        raise SystemExit("dpaste 上传失败 HTTP %s: %s" % (e.code, body))
    if resp.status != 201:
        raise SystemExit("dpaste 上传失败，状态码 %s（应为 201）" % resp.status)
    item_url = resp.read().decode("utf-8", "replace").strip()
    return item_url, item_url + ".txt"      # ★.txt 才是纯文本


def fetch_raw(raw_url):
    """回读 raw，返回 (bytes, content_type)。★整个流程只调用一次。"""
    req = urllib.request.Request(raw_url, headers=UA)
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=CTX)
    except urllib.error.HTTPError as e:
        ct = e.headers.get("Content-Type") or ""
        hint = "（429/HTML → 导入时会报「XML 语法错误」）" if "html" in ct.lower() else ""
        raise SystemExit("raw 回读失败 HTTP %s %s %s" % (e.code, ct, hint))
    return resp.read(), resp.headers.get("Content-Type")


def make_deeplink(raw_url, path="bookSource"):
    """生成深链。★src 必须整体 URL 编码，否则 # & 中文会截断参数。"""
    return "legado://import/%s?src=%s" % (path, urllib.parse.quote(raw_url, safe=""))


def verify(local_bytes, raw_url):
    remote, ct = fetch_raw(raw_url)
    lmd5 = hashlib.md5(local_bytes).hexdigest()
    rmd5 = hashlib.md5(remote).hexdigest()
    ok = (lmd5 == rmd5 and len(local_bytes) == len(remote))
    print("local   : %d bytes md5 %s" % (len(local_bytes), lmd5))
    print("remote  : %d bytes md5 %s ct=%s" % (len(remote), rmd5, ct))
    if not ok:
        print("VERIFY  : FAIL ❌ 字节不一致——检查是否被转义/BOM/尾换行污染")
        print("  local tail :", repr(local_bytes[-40:]))
        print("  remote tail:", repr(remote[-40:]))
    else:
        print("VERIFY  : PASS ✅ 字节级一致")
    return ok


def main():
    ap = argparse.ArgumentParser(description="dpaste 上传 + 校验 + 生成 Legado 深链")
    ap.add_argument("file", nargs="?", help="书源 JSON/JS 文件路径")
    ap.add_argument("--expiry", type=int, default=365, help="过期天数 1~365（默认 365）")
    ap.add_argument("--syntax", default="json", help="dpaste 语法标记，默认 json")
    ap.add_argument("--title", default=None, help="dpaste 标题（可选）")
    ap.add_argument("--path", default="bookSource", help="深链 path，默认 bookSource")
    ap.add_argument("--no-verify", action="store_true", help="跳过回读校验（省一次请求）")
    ap.add_argument("--deeplink-only", metavar="URL", help="不重传，只为已有 raw URL 生成深链")
    ap.add_argument("--out", default="dpaste_result.json", help="结果留档路径")
    args = ap.parse_args()

    if args.deeplink_only:
        dl = make_deeplink(args.deeplink_only, args.path)
        print("deeplink:", dl)
        return

    if not args.file:
        ap.error("需要文件路径，或用 --deeplink-only URL")
    if not (1 <= args.expiry <= 365):
        raise SystemExit("expiry 必须在 1~365（实测越界返回 400）")

    local_bytes = open(args.file, "rb").read()
    print("file    : %s (%d bytes)" % (args.file, len(local_bytes)))

    item_url, raw_url = upload(local_bytes, expiry=args.expiry,
                              syntax=args.syntax, title=args.title)
    print("dpaste  :", item_url)
    print("raw     :", raw_url)

    ok = True
    if not args.no_verify:
        ok = verify(local_bytes, raw_url)

    dl = make_deeplink(raw_url, args.path)
    print("deeplink:", dl)
    print()
    print("手机侧唤起（MCP eval_js）：")
    print("  java.openUrl('%s');" % dl)
    print("之后用 get_http_logs 看 GET .../%s -> 200 作为深链生效的硬证据。"
          % raw_url.rsplit("/", 1)[-1])

    json.dump({
        "file": args.file,
        "url": item_url,
        "raw": raw_url,
        "md5": hashlib.md5(local_bytes).hexdigest(),
        "bytes": len(local_bytes),
        "expiry_days": args.expiry,
        "deeplink": dl,
        "verify": ok,
    }, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("结果已留档:", args.out)

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
