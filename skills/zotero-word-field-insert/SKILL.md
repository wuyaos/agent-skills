---
name: zotero-word-field-insert
description: >
  Load when the user asks to "把方括号引用转成 Zotero 动态域"、"insert Zotero citation fields into docx"、
  "批量插入 Zotero 引用"、"convert [n] markers to Zotero fields"，且 Word/Zotero 都在 Windows 端、
  要求不破坏 Word 格式。Do not use for LibreOffice backend 流程、单处 GUI 点选插入、
  或从零新建引用（本 skill 只转换已存在的方括号标记）。
version: "1.0"
---

# Zotero Word 动态域直接写入

把 docx 正文已有的**方括号引用标记**（`[8-13]`/`[42]`/`[n,m]`）原地替换为 Zotero 可识别的 Word 动态域 `ADDIN ZOTERO_ITEM CSL_CITATION {...}`，文末插 `ADDIN ZOTERO_BIBL ... CSL_BIBLIOGRAPHY`。刷新由用户在 Word 手动进行，脚本不自动触发。

## 何时使用

- 正文已写成静态方括号编号，要转 Zotero 动态域。
- 格式优先，不能用 LibreOffice backend（会打乱 Word 布局）。
- Zotero + Word 都在 Windows，Local API `http://localhost:23119` 可用。

Anti-trigger：从零新建引用、单处 GUI 点选、LibreOffice 路线 → 不用本 skill。

## 核心约束（踩坑沉淀，调试 Word 打不开时必读）

1. **run 平级不嵌套**：每个 `fldChar`/`instrText`/显示文本独占一个 `<w:r>...</w:r>`。替换时必须**完整删除**目标 run（`<w:r>` 到 `</w:r>`），残留旧 run 开头再接新 run 会形成 `<w:r>...<w:r>` 嵌套 → XML 非良构 → Word 报"无法读取内容"。
2. **instrText 只转义 `&` 和 `<`**，不转义 `"` 和 `>`（对齐 Zotero 原生 test.docx，JSON 引号直出）。
3. **instrText 前导+尾随空格**：` ADDIN ZOTERO_ITEM ...} `。
4. **citationItems 嵌套结构**：`{id, uris, itemData:{...}}`。Local API 返回的 csljson 是平铺的（`type/title` 在顶层），必须重组为 `itemData` 包裹，否则刷新后 citation 为空。
5. **id 必须是整数 itemID**（非 itemKey、非 URI）。Local API 不返回整数 itemID，需用 MCP `run_javascript`（`Zotero.Items.getByLibraryAndKeyAsync(1,key).id`）预解析后填入 cite_map。
6. **BIBL 不重复 ADDIN**：`complex_field` 已统一加 ` ADDIN ` 前缀，调用方传 `ZOTERO_BIBL {...} CSL_BIBLIOGRAPHY`（不含前导 ADDIN），否则 `ADDIN ADDIN ZOTERO_BIBL` → BIBL 刷新后参考文献表为空。
7. **验证标准**：写入后必须 `xml.etree.ElementTree.fromstring(doc)` 良构通过，不能只看字段计数+zip 完整性。

## 使用流程

### 1. 预解析 itemID（用 Zotero MCP）

Local API 取不到整数 itemID，必须先用 MCP `run_javascript` 批量解析：

```javascript
var keys = ["2YXT3NVJ","GZ35MXMN"];
var out = [];
for (var k of keys) {
  var it = await Zotero.Items.getByLibraryAndKeyAsync(1, k);
  out.push({key:k, id: it ? it.id : null});
}
return out;
```

### 2. 写 cite_map.json

```json
{
  "USER_ID": "6207753",
  "markers": [
    {"marker": "[8-13]", "items": [
      {"key": "2YXT3NVJ", "id": 6107},
      {"key": "GZ35MXMN", "id": 717},
      {"key": "DCN6G7IG", "id": 8444},
      {"key": "8ZVRJCPK", "id": 8445},
      {"key": "FI8X7RJ5", "id": 2581},
      {"key": "DI7K4TEU", "id": 5940}
    ]},
    {"marker": "[42]", "items": [{"key": "XXXXXXXX", "id": 1234}]}
  ],
  "bibl_placeholder": "（此处由 Zotero 插入参考文献表）",
  "csl_cache": "csl_cache.json"
}
```

- `marker`：正文中要替换的标记（脚本按**首次出现**替换；替换后该标记消失，不误伤）。
- `items`：`{key, id}` 列表，id 为上一步解析的整数 itemID，按引用顺序。
- `bibl_placeholder`：文末参考文献表占位文本，替换为 BIBL 域。
- `csl_cache`：可选，缓存 Local API 取的 CSL JSON，重复跑省时。

### 3. 运行脚本

⚠️ 运行前确认目标 docx 未被 Word 打开（否则 `PermissionError`）：

```bash
# 关闭残留 Word 进程
powershell -Command "Get-Process WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force"

python .claude/skills/zotero-word-field-insert/insert_zotero_fields.py \
  --src manuscript_template_aligned.docx \
  --out manuscript_zotero_fields.docx \
  --map cite_map.json
```

## 验证（必须全过才算成功）

1. 脚本输出 `xml_ok=True`，`ADDIN_ADDIN_dup=0`，`markers_replaced=N`。Exit 0？→ 继续。
2. Word COM 打开验证：`OPEN_OK fields=<数>`。失败 → 回到约束 1 查 run 嵌套。
3. 任一步失败：修第一个错误，从步骤 1 重跑。最多 3 轮，仍失败则报告并停。

Word 打开验证命令：

```bash
powershell -Command "
\$w = New-Object -ComObject Word.Application; \$w.Visible=\$false; \$w.DisplayAlerts=0;
try { \$d = \$w.Documents.Open('OUT.docx', \$false, \$true); Write-Output ('OPEN_OK fields=' + \$d.Fields.Count); \$d.Close(\$false) }
catch { Write-Output ('OPEN_FAIL: ' + \$_) }; \$w.Quit()"
```

### 4. 人工刷新（不在脚本内）

Word 打开输出文件 → Zotero 工具栏 **Refresh**（或宏 `ZoteroRefresh`）。
- 首次可能弹文档首选项，选数字顺序编码样式（`[n]`）。
- 刷新后标记按 Zotero 实际编号重排，文末 BIBL 生成参考文献表。
- **Zotero 按正文出现顺序重新编号，原方括号编号不保留**——预期行为。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| Word 报"无法读取内容" | XML 非良构，多半 `<w:r>` 嵌套 | `ET.fromstring` 定位 mismatched tag，查替换边界是否完整删旧 run |
| ZOTERO_ITEM 计数对但刷新后 citation 空 | itemData 平铺未嵌套，或 id 非整数 | 查 citationItems 为 `{id,uris,itemData}`，id 为整数 itemID |
| BIBL 刷新后参考文献表空 | `ADDIN ADDIN ZOTERO_BIBL` 重复 | BIBL instrText 不含前导 ADDIN |
| Local API 取 CSL 失败 | Zotero 未运行/API 未开 | 确认 `http://localhost:23119/api/users/<UID>/items/<KEY>?format=csljson` 可访问 |
| `PermissionError` 写文件 | Word 仍开着该文件 | 关闭所有 WINWORD 进程重跑 |
| itemKey 解析不到 itemID | key 不在用户库 | MCP `run_javascript` 复核 `getByLibraryAndKeyAsync(1, key)` |

## 已验证 OOXML 结构（对齐 test.docx）

```xml
<w:r><w:rPr>...</w:rPr><w:fldChar w:fldCharType="begin"/></w:r>
<w:r><w:rPr>...</w:rPr><w:instrText xml:space="preserve"> ADDIN ZOTERO_ITEM CSL_CITATION {...} </w:instrText></w:r>
<w:r><w:rPr>...</w:rPr><w:fldChar w:fldCharType="separate"/></w:r>
<w:r><w:rPr>...</w:rPr><w:t>[8-13]</w:t></w:r>
<w:r><w:rPr>...</w:rPr><w:fldChar w:fldCharType="end"/></w:r>
```

rPr 从被替换的原 run 复制，保证字体一致。刷新宏名：`ZoteroRefresh`（刷新全部）、`ZoteroAddEditCitation`、`ZoteroAddEditBibliography`、`ZoteroSetDocPrefs`。`ZoteroUpdate`/`ZoteroUpdateCitations` 不存在。
