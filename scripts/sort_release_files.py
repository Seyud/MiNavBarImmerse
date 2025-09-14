#!/usr/bin/env python3
"""
按规则格式化并排序 `module/immerse_rules.xml` 与 `list.csv`。

目标：在发布前统一排序以保证分发的 zip 内容稳定。

功能概述：
- 对 XML：只重排 `<package .../>` 自闭合节点（包含它们前面的注释），保留文件头/尾。
- 对 CSV：处理应用列表，按分组（0-9 / A-Z / Z）排序，支持中文按拼音排序，并将英文/数字开头的条目放在组内前面。

用法：
    python3 scripts/sort_release_files.py module/immerse_rules.xml list.csv
"""

import argparse
import re
import csv
import sys
from pathlib import Path
from collections import defaultdict

try:
    from pypinyin import lazy_pinyin, Style
except ImportError:
    print("Missing pypinyin, installing...")
    import subprocess

    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pypinyin'], check=True)
    from pypinyin import lazy_pinyin, Style


def sort_xml(xml_path: Path) -> bool:
    text = xml_path.read_text(encoding='utf-8')

    # 查找所有 <package .../> 块（包括前置注释），支持自闭合形式。
    pattern = re.compile(r'(?:\s*(?:<!--.*?-->\s*)*)\s*<package\b[^>]*?/>', re.DOTALL)
    matches = list(pattern.finditer(text))
    if not matches:
        print(f"No <package/> blocks found in {xml_path}")
        return False

    header = text[: matches[0].start()]
    footer = text[matches[-1].end():]

    blocks = []
    for m in matches:
        blk = m.group(0)
        # 分割注释部分和 package 部分
        pkg_idx = blk.rfind('<package')
        comment_part = blk[:pkg_idx]
        pkg_part = blk[pkg_idx:]

        # 提取注释并规范为单行、缩进格式
        comments = re.findall(r'<!--(.*?)-->', comment_part, re.DOTALL)
        comment_lines = ''
        for c in comments:
            c_text = ' '.join(line.strip() for line in c.splitlines())
            comment_lines += '    <!-- ' + c_text + ' -->\n'

        # 规范 package 行的缩进并压成单行
        pkg_line = '    ' + ' '.join(pkg_part.split()) + '\n'

        normalized = comment_lines + pkg_line + '\n'
        blocks.append((normalized, pkg_part))

    def extract_name(raw_pkg: str) -> str:
        m = re.search(r'name\s*=\s*"([^"]+)"', raw_pkg)
        return m.group(1) if m else ''

    blocks_sorted = sorted(blocks, key=lambda t: extract_name(t[1]).lower())

    # 重建 XML 文件：保留原始头部，插入已排序的 blocks，再加上尾部。
    new_text = header.rstrip() + '\n\n' + ''.join(b[0] for b in blocks_sorted) + footer.lstrip()

    if new_text != text:
        xml_path.write_text(new_text, encoding='utf-8')
        print(f"Formatted and sorted {len(blocks_sorted)} <package/> blocks in {xml_path}")
        return True
    else:
        print(f"{xml_path} already formatted and sorted")
        return False


def sort_csv(csv_path: Path) -> bool:
    # 读取 CSV 内容并按行拆分
    text = csv_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    # First, remove duplicate single-character header lines (e.g. 'A' or 'K,,,,,,')
    # Keep only the first occurrence of each allowed header (0-9, A-Z).
    import re as _re
    seen_headers = set()
    new_lines = []
    changed_headers = False
    header_pattern = _re.compile(r'^\s*([A-Za-z0-9])(?:\s*,\s*)*$')
    for ln in lines:
        m = header_pattern.match(ln)
        if m:
            ch = m.group(1).upper()
            if ch in seen_headers:
                changed_headers = True
                continue
            seen_headers.add(ch)
            new_lines.append(ln)
        else:
            new_lines.append(ln)
    if changed_headers:
        # 如果发现重复的单字符头则写回清理后的文件并刷新内存内容
        csv_path.write_text('\n'.join(new_lines) + ('\n' if new_lines and not new_lines[-1].endswith('\n') else ''), encoding='utf-8')
        text = '\n'.join(new_lines)
        lines = text.splitlines()
    if not lines:
        print(f"Empty CSV: {csv_path}")
        return False
    # Use csv module to parse rows reliably
    reader = list(csv.reader(lines))
    if not reader:
        print(f"Empty CSV: {csv_path}")
        return False

    # CSV 的第一行可能是真正的表头（包含多个字段），也可能是单字符分区头。
    header = reader[0]
    raw_rows = reader[1:]

    # 去除全为空的空行
    cleaned = [r for r in raw_rows if any((cell and cell.strip()) for cell in r)]
    # Also ignore previously-inserted single-character header rows (0-9 or A-Z)
    entries = []
    for r in cleaned:
        # A header row we previously inserted is a single non-empty cell whose value is a single char 0-9/A-Z
        if len(r) == 1 and r[0] and len(r[0].strip()) == 1:
            ch = r[0].strip().upper()
            if ch.isdigit() or ('A' <= ch <= 'Z'):
                # skip this header row as data
                continue
        entries.append(r)

    # Global reorder: group all entries by a single-character header.
    # Allowed headers: digits 0-9 and uppercase A-Z. Everything else maps to 'Z'.
    # 按单字符分组（0-9 / A-Z / Z）
    groups = defaultdict(list)
    for r in entries:
        name = (r[0].strip() if len(r) > 0 else '')
        if not name:
            continue
        # Detect if name starts with ASCII letter or digit - prefer grouping by that
        first = name[0]
        if first.isascii() and (first.isalpha() or first.isdigit()):
            header = first.upper()
        else:
            # For non-ascii (likely Chinese), use pinyin first letter if possible
            try:
                py = lazy_pinyin(name, style=Style.FIRST_LETTER)
                candidate = (py[0] if py and py[0] else '')
            except Exception:
                candidate = ''

            candidate = (candidate or name[0]).upper()
            if len(candidate) == 1 and (candidate.isdigit() or ('A' <= candidate <= 'Z')):
                header = candidate
            else:
                header = 'Z'

        groups[header].append(r)

    sorted_initials = sorted(groups.keys())

    # 判断原始首行是否是真正的 CSV 表头（包含多个字段）
    def _is_single_char_group(hrow):
        try:
            return len(hrow) == 1 and isinstance(hrow[0], str) and len(hrow[0].strip()) == 1 and (
                    hrow[0].strip().isdigit() or ('A' <= hrow[0].strip().upper() <= 'Z')
            )
        except Exception:
            return False

    header_is_real = not _is_single_char_group(header)

    # 重建输出行：仅当原始 header 真实存在时才写回
    out_rows = [header] if header_is_real else []
    first = True
    for initial in sorted_initials:
        if not first:
            out_rows.append([])  # blank line
        first = False
        out_rows.append([initial])

        # Within a group, put ASCII-starting names (A-Z/0-9) first, sorted by ASCII order,
        # then put the others (likely Chinese) sorted by full pinyin.
        ascii_items = []
        others = []
        for r in groups[initial]:
            n = r[0].strip()
            if n and n[0].isascii() and (n[0].isalpha() or n[0].isdigit()):
                ascii_items.append(r)
            else:
                others.append(r)

        ascii_items_sorted = sorted(ascii_items, key=lambda rr: rr[0].strip().upper())

        def py_sort_key(r):
            name = r[0].strip()
            # 拼接每个字的首字母拼音后整体排序
            py_full = ''.join(lazy_pinyin(name, style=Style.FIRST_LETTER)).lower()
            return py_full

        others_sorted = sorted(others, key=py_sort_key)
        sorted_group = ascii_items_sorted + others_sorted
        out_rows.extend(sorted_group)

    # 写回文件（使用 csv.writer 以保留必要的引号）
    out_path = csv_path
    with out_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in out_rows:
            writer.writerow(row)

    print(f"Formatted and globally sorted {sum(len(g) for g in groups.values())} data rows in {csv_path}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('xml', help='path to immerse_rules.xml')
    parser.add_argument('csv', help='path to list.csv')
    args = parser.parse_args()

    xml_path = Path(args.xml)
    csv_path = Path(args.csv)

    changed = False
    if xml_path.exists():
        try:
            changed |= sort_xml(xml_path)
        except Exception as e:
            print(f"Error sorting XML: {e}")
            sys.exit(2)
    else:
        print(f"XML file not found: {xml_path}")

    if csv_path.exists():
        try:
            changed |= sort_csv(csv_path)
        except Exception as e:
            print(f"Error sorting CSV: {e}")
            sys.exit(3)
    else:
        print(f"CSV file not found: {csv_path}")

    sys.exit(0 if changed else 0)


if __name__ == '__main__':
    main()
