#!/usr/bin/env python3
"""
Sort module/immerse_rules.xml by package name attribute and list.csv by application name.

This script is intended to be run in CI before packaging so the distributed zip contains
consistent ordering. It preserves non-package header/footer in the XML file and only
reorders the <package .../> blocks (including their immediately preceding comments).

For CSV the script keeps the header line and sorts rows that have a package name
(second column) by the first column (application name). Lines without a package
name (group separators or blank lines) are dropped to keep the CSV compact.

Usage:
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

    # Find all package blocks including preceding comments. Support self-closing <package .../>.
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
        # split into comment part and package part
        pkg_idx = blk.rfind('<package')
        comment_part = blk[:pkg_idx]
        pkg_part = blk[pkg_idx:]

        # Extract comments and normalize each as a single indented line
        comments = re.findall(r'<!--(.*?)-->', comment_part, re.DOTALL)
        comment_lines = ''
        for c in comments:
            c_text = ' '.join(line.strip() for line in c.splitlines())
            comment_lines += '    <!-- ' + c_text + ' -->\n'

        # Normalize package line indentation and ensure single-line
        pkg_line = '    ' + ' '.join(pkg_part.split()) + '\n'

        normalized = comment_lines + pkg_line + '\n'
        blocks.append((normalized, pkg_part))

    def extract_name(raw_pkg: str) -> str:
        m = re.search(r'name\s*=\s*"([^"]+)"', raw_pkg)
        return m.group(1) if m else ''

    blocks_sorted = sorted(blocks, key=lambda t: extract_name(t[1]).lower())

    # Rebuild file: keep header, then sorted normalized blocks, then footer
    new_text = header.rstrip() + '\n\n' + ''.join(b[0] for b in blocks_sorted) + footer.lstrip()

    if new_text != text:
        xml_path.write_text(new_text, encoding='utf-8')
        print(f"Formatted and sorted {len(blocks_sorted)} <package/> blocks in {xml_path}")
        return True
    else:
        print(f"{xml_path} already formatted and sorted")
        return False


def sort_csv(csv_path: Path) -> bool:
    text = csv_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    if not lines:
        print(f"Empty CSV: {csv_path}")
        return False
    # Use csv module to parse rows reliably
    reader = list(csv.reader(lines))
    if not reader:
        print(f"Empty CSV: {csv_path}")
        return False

    header = reader[0]
    raw_rows = reader[1:]

    # Remove useless blank rows (rows where all cells are empty)
    entries = [r for r in raw_rows if any((cell and cell.strip()) for cell in r)]

    # Global reorder: group all entries by pinyin initial
    groups = defaultdict(list)
    for r in entries:
        name = (r[0].strip() if len(r) > 0 else '')
        if not name:
            continue
        py = lazy_pinyin(name, style=Style.FIRST_LETTER)
        initial = py[0].upper() if py and py[0].isalpha() else name[0].upper()
        groups[initial].append(r)

    sorted_initials = sorted(groups.keys())

    # Rebuild CSV: header, then for each group: blank line, initial header, group rows sorted by full pinyin
    out_rows = [header]
    first = True
    for initial in sorted_initials:
        if not first:
            out_rows.append([])  # blank line
        first = False
        out_rows.append([initial])

        def py_sort_key(r):
            name = r[0].strip()
            py_full = ''.join(lazy_pinyin(name)).lower()
            return py_full

        sorted_group = sorted(groups[initial], key=py_sort_key)
        out_rows.extend(sorted_group)

    # Write back using csv.writer to preserve quoting
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
