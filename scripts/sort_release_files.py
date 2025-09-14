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


def sort_xml(xml_path: Path) -> bool:
    text = xml_path.read_text(encoding='utf-8')

    # Find all package blocks including preceding comments
    pattern = re.compile(r'(?:\s*(?:<!--.*?-->\s*)*)\s*<package\b[^>]*?/>', re.DOTALL)
    matches = list(pattern.finditer(text))
    if not matches:
        print(f"No <package/> blocks found in {xml_path}")
        return False

    header_start = 0
    header_end = matches[0].start()
    footer_start = matches[-1].end()

    header = text[header_start:header_end]
    footer = text[footer_start:]

    blocks = [m.group(0) for m in matches]

    def pkg_name(block: str) -> str:
        m = re.search(r'name\s*=\s*"([^"]+)"', block)
        return m.group(1) if m else ''

    sorted_blocks = sorted(blocks, key=lambda b: pkg_name(b).lower())

    new_text = header + ''.join(sorted_blocks) + footer

    if new_text != text:
        xml_path.write_text(new_text, encoding='utf-8')
        print(f"Sorted {len(blocks)} <package/> blocks in {xml_path}")
        return True
    else:
        print(f"{xml_path} already sorted")
        return False


def sort_csv(csv_path: Path) -> bool:
    text = csv_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    if not lines:
        print(f"Empty CSV: {csv_path}")
        return False

    # Use csv module to parse rows reliably
    reader = list(csv.reader(lines))
    header = reader[0]
    rows = reader[1:]

    # Keep only rows that have a package name (second column non-empty)
    entries = [r for r in rows if len(r) > 1 and r[1].strip()]

    if not entries:
        print(f"No data rows with package names in {csv_path}")
        return False

    # Sort by application name (first column), fallback to package name
    def key_fn(r):
        name = r[0].strip() if r and r[0] else ''
        pkg = r[1].strip() if len(r) > 1 else ''
        return (name.lower(), pkg.lower())

    entries_sorted = sorted(entries, key=key_fn)

    # Reconstruct CSV: header followed by sorted entries
    out_lines = []
    out = []
    out.append(header)
    out.extend(entries_sorted)

    # Write back using csv.writer to preserve quoting
    out_path = csv_path
    with out_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in out:
            writer.writerow(row)

    print(f"Sorted {len(entries_sorted)} rows in {csv_path}")
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
