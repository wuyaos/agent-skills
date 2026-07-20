# -*- coding: utf-8 -*-
"""
Zotero Word 动态域直接写入脚本（通用版）。

把 docx 正文中方括号引用标记（如 [8-13]、[42]）原地替换为
Zotero 可识别的 Word 动态域 ADDIN ZOTERO_ITEM CSL_CITATION {...}，
并在文末占位处插入 ADDIN ZOTERO_BIBL ... CSL_BIBLIOGRAPHY。

刷新由用户在 Word 里手动进行（Zotero Refresh），本脚本不自动触发。

核心约束（踩坑沉淀，详见 SKILL.md）：
  1. 每个 fldChar/instrText/display 独占一个 <w:r>...</w:r>，平级不嵌套
  2. instrText 只转义 & 和 <，不转义 " 和 >
  3. instrText 前导 + 尾随空格：" ADDIN ... "
  4. citationItems 嵌套结构 {id, uris, itemData:{...}}，id 为整数 itemID
  5. BIBL instrText 不含前导 ADDIN（complex_field 统一加）
  6. 写入后 ET.fromstring 验证良构

用法：
  python insert_zotero_fields.py --src IN.docx --out OUT.docx --map cite_map.json

cite_map.json 格式：
  {
    "USER_ID": "6207753",
    "markers": [
      {"marker": "[8-13]", "items": [
         {"key":"2YXT3NVJ","id":6107},
         {"key":"GZ35MXMN","id":717}
      ]},
      {"marker": "[42]", "items": [{"key":"XXXXXXXX","id":1234}]}
    ],
    "bibl_placeholder": "（此处由 Zotero 插入参考文献表）",
    "csl_cache": "csl_cache.json"   # 可选，缓存 Local API 取的 CSL JSON
  }

itemID（整数 id）需调用方预先用 Zotero MCP run_javascript
（Zotero.Items.getByLibraryAndKeyAsync(1, key).id）解析后填入。
"""
import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

ZOTERO_API = "http://localhost:23119/api"
SCHEMA = "https://github.com/citation-style-language/schema/raw/master/csl-citation.json"


def xml_escape(s: str) -> str:
    """对齐 Zotero 原生 test.docx：只转义 & 和 <，引号直出。"""
    return s.replace("&", "&amp;").replace("<", "&lt;")


def fetch_csl(user_id: str, key: str, cache: dict) -> dict:
    """从 Zotero Local API 取某 itemKey 的 CSL JSON。带缓存。"""
    if key in cache:
        return cache[key]
    url = f"{ZOTERO_API}/users/{user_id}/items/{key}?format=csljson"
    raw = urllib.request.urlopen(url, timeout=15).read().decode("utf-8")
    obj = json.loads(raw)
    if isinstance(obj, list):
        obj = obj[0]
    cache[key] = obj
    return obj


def build_citation_json(marker: str, items_spec: list, csl_items: dict, user_id: str) -> str:
    """构造 CSL_CITATION JSON。

    items_spec: [{"key":..., "id":<整数itemID>}]
    csl_items: {key: <api csljson dict>}  —— API 返回的 csljson 是平铺结构
    返回的 citationItems[i] = {id, uris, itemData:{...}} 嵌套结构。
    """
    citation_items = []
    for spec in items_spec:
        key = spec["key"]
        iid = int(spec["id"])
        src = dict(csl_items.get(key, {}))
        # API csljson 平铺在顶层；重组为 itemData 包裹
        item_data = {k: v for k, v in src.items() if k not in ("id", "uris")}
        item_data["id"] = iid
        citation_items.append({
            "id": iid,
            "uris": [f"http://zotero.org/users/{user_id}/items/{key}"],
            "itemData": item_data,
        })

    # citationID 用 marker 的稳定哈希派生（脚本里不能用 random/Date）
    cid = "cit" + str(abs(hash(marker)) % (10 ** 12))
    cit = {
        "citationID": cid,
        "properties": {
            "unsorted": False,
            "formattedCitation": marker,
            "plainCitation": marker,
            "noteIndex": 0,
        },
        "citationItems": citation_items,
        "schema": SCHEMA,
    }
    return json.dumps(cit, ensure_ascii=False)


def make_run(rpr: str, inner: str) -> str:
    return f"<w:r>{rpr}{inner}</w:r>"


def complex_field(instr_text: str, display_text: str, rpr: str) -> str:
    """生成完整 complex field，每个部件独占一个 <w:r>，平级不嵌套。
    instr_text 不含前导 ADDIN，本函数统一加 " ADDIN ... "。
    """
    instr = " ADDIN " + instr_text + " "
    return "".join([
        make_run(rpr, '<w:fldChar w:fldCharType="begin"/>'),
        make_run(rpr, f'<w:instrText xml:space="preserve">{xml_escape(instr)}</w:instrText>'),
        make_run(rpr, '<w:fldChar w:fldCharType="separate"/>'),
        make_run(rpr, f'<w:t>{xml_escape(display_text)}</w:t>'),
        make_run(rpr, '<w:fldChar w:fldCharType="end"/>'),
    ])


def replace_first_run_containing(doc: str, text: str, replacement: str) -> tuple:
    """定位 doc 中首次出现 text 的完整 <w:r>...</w:r>，整体替换为 replacement。
    返回 (new_doc, replaced_run_rpr)。找不到返回 (doc, None)。
    """
    idx = doc.find(text)
    if idx < 0:
        return doc, None
    rstart = doc.rfind("<w:r>", 0, idx)
    rend = doc.find("</w:r>", idx) + len("</w:r>")
    old_run = doc[rstart:rend]
    rpr_m = re.search(r"<w:rPr>.*?</w:rPr>", old_run, re.DOTALL)
    rpr = rpr_m.group(0) if rpr_m else ""
    new_doc = doc[:rstart] + replacement + doc[rend:]
    return new_doc, rpr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="输入 docx")
    ap.add_argument("--out", required=True, help="输出 docx")
    ap.add_argument("--map", required=True, help="cite_map.json 路径")
    args = ap.parse_args()

    cfg = json.loads(open(args.map, encoding="utf-8").read())
    user_id = cfg["USER_ID"]
    markers = cfg["markers"]
    bibl_placeholder = cfg.get("bibl_placeholder", "（此处由 Zotero 插入参考文献表）")
    csl_cache_path = cfg.get("csl_cache")

    # 加载 CSL 缓存
    cache = {}
    if csl_cache_path and os.path.exists(csl_cache_path):
        cache = json.loads(open(csl_cache_path, encoding="utf-8").read())

    shutil.copy2(args.src, args.out)
    with zipfile.ZipFile(args.out) as z:
        doc = z.read("word/document.xml").decode("utf-8")

    # 处理每个 marker
    replaced = 0
    missing_ids = []
    for m in markers:
        marker = m["marker"]
        items_spec = m["items"]
        # 校验 id
        for s in items_spec:
            if "id" not in s:
                missing_ids.append(s["key"])
        if missing_ids:
            continue
        # 取 CSL
        csl_items = {}
        ok = True
        for s in items_spec:
            try:
                csl_items[s["key"]] = fetch_csl(user_id, s["key"], cache)
            except Exception as e:
                print(f"CSL fetch FAIL {s['key']}: {e}")
                ok = False
        if not ok:
            continue
        cit_json = build_citation_json(marker, items_spec, csl_items, user_id)
        instr_item = f"ZOTERO_ITEM CSL_CITATION {cit_json}"
        # 先定位原 run 提取 rpr，再生成 field
        idx = doc.find(marker)
        if idx < 0:
            print(f"marker not found in doc: {marker}")
            continue
        rstart = doc.rfind("<w:r>", 0, idx)
        rend = doc.find("</w:r>", idx) + len("</w:r>")
        old_run = doc[rstart:rend]
        rpr_m = re.search(r"<w:rPr>.*?</w:rPr>", old_run, re.DOTALL)
        rpr = rpr_m.group(0) if rpr_m else ""
        item_field = complex_field(instr_item, marker, rpr)
        doc = doc[:rstart] + item_field + doc[rend:]
        replaced += 1
        print(f"replaced {marker} -> {len(items_spec)} items")

    # 插入 BIBL
    bibl_instr = 'ZOTERO_BIBL {"uncited":[],"omitted":[],"custom":[]} CSL_BIBLIOGRAPHY'
    bibl_field = complex_field(bibl_instr, "", rpr="")
    doc, _ = replace_first_run_containing(doc, bibl_placeholder, bibl_field)
    print(f"BIBL inserted at placeholder: {bibl_placeholder}")

    # 写回 zip
    tmp = args.out + ".tmp"
    with zipfile.ZipFile(args.out) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = doc.encode("utf-8")
            zout.writestr(item, data)
    os.replace(tmp, args.out)

    # 保存 CSL 缓存
    if csl_cache_path:
        open(csl_cache_path, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=2))

    # 验证良构
    try:
        ET.fromstring(doc)
        xml_ok = True
    except ET.ParseError as e:
        xml_ok = False
        print("XML PARSE ERROR:", e)

    print(f"xml_ok={xml_ok} markers_replaced={replaced} "
          f"ZOTERO_ITEM={doc.count('ZOTERO_ITEM')} "
          f"ZOTERO_BIBL={doc.count('ZOTERO_BIBL')} "
          f"ADDIN_ADDIN_dup={doc.count('ADDIN ADDIN')}")
    if missing_ids:
        print(f"WARNING missing itemID for keys: {missing_ids}")
        print("请用 Zotero MCP run_javascript 解析 itemID 后填入 cite_map")
    print(f"output={args.out}")
    if not xml_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
