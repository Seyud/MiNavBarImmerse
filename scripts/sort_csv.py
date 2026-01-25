import csv
from pathlib import Path
from collections import defaultdict, OrderedDict
from pypinyin import lazy_pinyin, Style

def sort_csv(csv_path: Path) -> bool:
    """
    排序 CSV 文件
    """
    # ====== 更新：硬编码当前CSV标头 ======
    STANDARD_HEADER = ["应用名称", "应用包名", "适配前", "适配后", "适配效果", "更新日期", ""]

    # 读取 CSV 内容并按行拆分
    text = csv_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 先基于 csv 解析识别并去除重复的单字符组头（支持带逗号的形式，如 "A,,,"），仅保留首次出现
    reader_rows = list(csv.reader(lines))
    seen_headers = set()
    new_rows = []
    changed_headers = False
    for row in reader_rows:
        if len(row) >= 1 and row[0] and len(row[0].strip()) == 1 and (row[0].strip().isdigit() or row[0].strip().upper().isalpha()) and all((not c or not str(c).strip()) for c in row[1:]):
            ch = row[0].strip().upper()
            if ch in seen_headers:
                changed_headers = True
                continue
            seen_headers.add(ch)
            new_rows.append(row)
        else:
            new_rows.append(row)
    if changed_headers:
        # 写回清理后的 CSV 内容
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for r in new_rows:
                writer.writerow(r)
        # 刷新文本与行
        text = csv_path.read_text(encoding="utf-8")
        lines = text.splitlines()

    if not lines:
        print(f"Empty CSV: {csv_path}")
        return False

    # 使用 csv 模块解析行
    reader = list(csv.reader(lines))
    if not reader:
        print(f"Empty CSV: {csv_path}")
        return False

    # ====== 更新：去除所有重复表头，仅保留顶部一个 ======
    def is_standard_header(row):
        return [c.strip() for c in row] == [c.strip() for c in STANDARD_HEADER]

    # 收集所有非表头行，统计表头出现次数
    filtered_rows = []
    header_found = False
    for row in reader:
        if is_standard_header(row):
            if not header_found:
                header_found = True
                filtered_rows.append(STANDARD_HEADER)
            # 跳过后续所有表头
            continue
        filtered_rows.append(row)
    if not header_found:
        # 顶部插入标准表头
        filtered_rows = [STANDARD_HEADER] + filtered_rows

    # 重新赋值 header, raw_rows
    header = filtered_rows[0]
    raw_rows = filtered_rows[1:]

    # 去除全为空的空行
    cleaned = [r for r in raw_rows if any((cell and str(cell).strip()) for cell in r)]

    # 忽略之前可能插入的单字符组头行：第一列为单字符字母/数字，其余列为空
    entries = []
    for r in cleaned:
        if len(r) >= 1 and r[0] and len(str(r[0]).strip()) == 1 and (str(r[0]).strip().isdigit() or str(r[0]).strip().upper().isalpha()) and all((not str(c).strip()) for c in r[1:]):
            continue
        entries.append(r)

    # 按单字符分组（0-9 / A-Z / Z）
    groups = defaultdict(list)
    for r in entries:
        name = (r[0].strip() if len(r) > 0 else "")
        if not name:
            continue
        first = name[0]
        if first.isascii() and (first.isalpha() or first.isdigit()):
            header_char = first.upper()
        else:
            try:
                py = lazy_pinyin(name, style=Style.FIRST_LETTER)
                candidate = (py[0] if py and py[0] else "")
            except Exception:
                candidate = ""
            candidate = (candidate or name[0]).upper()
            if len(candidate) == 1 and (candidate.isdigit() or ("A" <= candidate <= "Z")):
                header_char = candidate
            else:
                header_char = "Z"
        groups[header_char].append(r)

    sorted_initials = sorted(groups.keys())

    # 判断原始首行是否是真正的 CSV 表头（包含多个字段）
    def _is_single_char_group(hrow):
        try:
            return len(hrow) == 1 and isinstance(hrow[0], str) and len(hrow[0].strip()) == 1 and (
                    hrow[0].strip().isdigit() or ("A" <= hrow[0].strip().upper() <= "Z")
            )
        except Exception:
            return False

    header_is_real = not _is_single_char_group(header)

    # 确定输出列数：优先使用真实表头列数，否则使用文件中最大的行列数，默认 6
    if header_is_real:
        col_count = len(header)
    else:
        col_count = max((len(r) for r in reader), default=6)

    # 重建输出：可选真实表头，然后按组输出。空行与组头均填充为 col_count 列，便于 GitHub 预览
    # 如果有真实表头，先放表头，并确保表头和第一个分组之间有一个空行
    out_rows = []
    if header_is_real:
        out_rows.append(header)
        # 明确在表头后插入一个空行，保证表头和第一个分组之间有空行
        out_rows.append([""] * col_count)

    first_group = True
    for initial in sorted_initials:
        # 在每个分组头之前插入一个空行：无论是第一个分组（与总表头之间）还是后续分组（与上一个分组之间）
        if out_rows and (not out_rows[-1] or any(cell != "" for cell in out_rows[-1])):
            # 如果最后一行不是空行，则插入空行
            out_rows.append([""] * col_count)
        # 添加分组头
        out_rows.append([initial] + [""] * (col_count - 1))

        # 组内排序：ASCII/数字开头的先按 ASCII 排序，中文按每字首字母拼接排序
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
            # 拼接每个字的首字母后进行排序
            return "".join(lazy_pinyin(name, style=Style.FIRST_LETTER)).lower()

        others_sorted = sorted(others, key=py_sort_key)
        sorted_group = ascii_items_sorted + others_sorted

        # 填充/截断每行以匹配 col_count
        for rr in sorted_group:
            rr_list = list(rr)
            if len(rr_list) < col_count:
                rr_list += [""] * (col_count - len(rr_list))
            else:
                rr_list = rr_list[:col_count]
            out_rows.append(rr_list)

    # 写回文件
    out_path = csv_path
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in out_rows:
            row_to_write = list(row)
            if len(row_to_write) < col_count:
                row_to_write += [""] * (col_count - len(row_to_write))
            else:
                row_to_write = row_to_write[:col_count]
            writer.writerow(row_to_write)

    print(f"Formatted and globally sorted {sum(len(g) for g in groups.values())} data rows in {csv_path}")
    return True
sort_csv(Path("list.csv"))