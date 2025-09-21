#!/usr/bin/env python3
"""
更新 changelog.md：
- 使用最近提交的提交时间（北京时间）作为日期；
- 仅在有内容时显示“新增/优化/贡献者”分区（空区块隐藏）；
- changelog.md 默认显示最近有实际更新内容的一天的日志；
- 将不是目标日期的历史条目移动并合并到 changelog-full.md。

用法：在仓库根目录运行，CI 中可直接运行：
    python3 scripts/update_changelog.py

依赖：仅标准库
"""
from datetime import datetime, timedelta, timezone
import subprocess
from pathlib import Path
import csv
import sys
import os
import re
import xml.etree.ElementTree as ET
from collections import OrderedDict

ROOT = Path(__file__).resolve().parents[1]
CHLOG = ROOT / 'changelog.md'
CHLOG_FULL = ROOT / 'changelog-full.md'
LIST_CSV = ROOT / 'list.csv'


def git_show(path: str):
    try:
        out = subprocess.check_output(['git', 'show', 'HEAD^:' + path], cwd=ROOT, stderr=subprocess.DEVNULL)
        return out.decode('utf-8')
    except subprocess.CalledProcessError:
        return None


def git_changed_files():
    try:
        out = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD^', 'HEAD'], cwd=ROOT)
        return out.decode('utf-8').splitlines()
    except subprocess.CalledProcessError:
        return []


def parse_csv_text(text):
    rows = []
    if text is None:
        return rows
    reader = csv.reader(text.splitlines())
    for r in reader:
        if any((c and c.strip()) for c in r):
            rows.append([c.strip() for c in r])
    return rows


def rows_by_name(rows):
    d = {}
    for r in rows:
        if len(r) > 0:
            d[r[0]] = r
    return d


def read_blocks_from_text(text: str):
    # 按日期标题分块，标题格式为: # YYYY-MM-DD
    if not text:
        return []
    lines = text.splitlines()
    blocks = []
    cur = []
    for ln in lines:
        # 支持 '# ' 或 '## ' 开头的日期标题
        if re.match(r'^#{1,2}\s', ln):
            if cur:
                blocks.append('\n'.join(cur))
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        blocks.append('\n'.join(cur))
    return blocks


def block_date(b: str):
    first = b.splitlines()[0].strip()
    # 支持 '# ' 或 '## ' 等
    m = re.match(r'^#{1,2}\s+(.*)', first)
    if m:
        return m.group(1).strip()
    return ''


def block_has_content(b: str):
    # 判断分块中是否有实际新增/优化/贡献者内容（非空）
    lines = b.splitlines()
    for ln in lines:
        if ln.strip().startswith('- '):
            return True
    return False


def merge_into_full(blocks):
    if not blocks:
        return

    full_text = CHLOG_FULL.read_text(encoding='utf-8') if CHLOG_FULL.exists() else '# 完整更新日志\n'

    # helper: ensure display items have a space before '(__@user__)' if missing
    def format_display_item(item_text: str) -> str:
        if not item_text:
            return item_text
        s = item_text
        # only target parentheses that contain an @username (with optional surrounding underscores),
        # and only when there's no whitespace before the '('
        s = re.sub(r'(?<!\s)\((__?@[^)]+__?)\)', r' (\1)', s)
        return s

    # parse existing full into mapping date -> OrderedDict(section_title -> [items])
    existing = OrderedDict()
    for eb in read_blocks_from_text(full_text):
        date = block_date(eb)
        if not date or date == '完整更新日志':
            continue
        secs = parse_day_sections(eb)
        if date not in existing:
            existing[date] = OrderedDict()
        # merge sections preserving order
        for title, items in secs.items():
            if title not in existing[date]:
                existing[date][title] = []
            # append items if not duplicate (normalize)
            seen = {normalize_item(it, title if title in ('新增', '优化', '贡献者') else '新增'): True for it in existing[date][title]}
            for it in items:
                key = normalize_item(it, title if title in ('新增', '优化', '贡献者') else '新增')
                if key and key not in seen:
                    seen[key] = True
                    existing[date][title].append(format_display_item(it))

    # parse incoming blocks and merge (incoming should be considered newest -> placed first)
    incoming = OrderedDict()
    for ib in blocks:
        date = block_date(ib)
        if not date:
            continue
        secs = parse_day_sections(ib)
        if date not in incoming:
            incoming[date] = OrderedDict()
        for title, items in secs.items():
            if title not in incoming[date]:
                incoming[date][title] = []
            seen = {normalize_item(it, title if title in ('新增', '优化', '贡献者') else '新增'): True for it in incoming[date][title]}
            for it in items:
                key = normalize_item(it, title if title in ('新增', '优化', '贡献者') else '新增')
                if key and key not in seen:
                    seen[key] = True
                    incoming[date][title].append(format_display_item(it))

    # merge incoming into existing: incoming items appended to existing sections (avoid duplicates)
    # and incoming dates inserted at front (newest first)
    for date in reversed(list(incoming.keys())):
        if date in existing:
            # merge per-section
            for title, items in incoming[date].items():
                if title not in existing[date]:
                    existing[date][title] = []
                seen = {normalize_item(it, title if title in ('新增', '优化', '贡献者') else '新增'): True for it in existing[date][title]}
                for it in items:
                    key = normalize_item(it, title if title in ('新增', '优化', '贡献者') else '新增')
                    if key and key not in seen:
                        seen[key] = True
                        existing[date][title].append(format_display_item(it))
        else:
            # insert new date at front
            existing = OrderedDict([(date, incoming[date])] + list(existing.items()))

    # build output: head, one blank line, then date blocks with 3 blank lines between
    head = '# 完整更新日志'
    sep = '\n' * 4

    date_blocks = []
    for date, secs in existing.items():
        # skip empty dates
        has = any(secs.get(t) for t in secs)
        if not has:
            continue
        lines = [f'## {date}']
        for title, items in secs.items():
            if not items:
                continue
            # normalize '贡献者' spacing by using title directly trimmed
            clean_title = re.sub(r'\s+', ' ', title).strip()
            lines.append(f'### {clean_title}')
            lines.extend(items)
            lines.append('')
        date_blocks.append('\n'.join(lines).rstrip())

    if not date_blocks:
        new_full = head + '\n'
    else:
        first = date_blocks[0]
        rest = date_blocks[1:]
        if rest:
            body = first + (sep + sep.join(rest))
        else:
            body = first
        new_full = head + '\n' + body + '\n'

    if not new_full.endswith('\n'):
        new_full += '\n'

    CHLOG_FULL.write_text(new_full, encoding='utf-8')


def get_commit_beijing_date():
    # 获取最近一次提交的 unix 时间戳（秒），转换为北京时间日期字符串 YYYY-MM-DD
    try:
        out = subprocess.check_output(['git', 'log', '-1', '--format=%ct'], cwd=ROOT)
        ts = int(out.decode('utf-8').strip())
        # 使用时区感知的 UTC 时间，再转换为北京时间（UTC+8）
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
        dt = dt_utc.astimezone(timezone(timedelta(hours=8)))
        return dt.strftime('%Y-%m-%d'), dt
    except Exception:
        # 回退到本地当前时间（时区感知）
        dt = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
        return dt.strftime('%Y-%m-%d'), dt


def merge_blocks_by_date(blocks):
    """把同一日期的多个块合并成单个块，保持块内顺序并用一个空行分隔原始块。"""
    from collections import OrderedDict
    grouped = OrderedDict()
    for b in blocks:
        dt = block_date(b)
        if not dt:
            continue
        if dt not in grouped:
            grouped[dt] = []
        grouped[dt].append(b)
    merged = []
    for dt, blist in grouped.items():
        # 清理每个子块的 footer 行（如果有），保留原空行结构
        cleaned_subs = []
        for sb in blist:
            lines = []
            for ln in sb.splitlines():
                s = ln.strip()
                if s.startswith('*') and ('查看完整日志' in s or '完整历史' in s or '由于管理器篇幅限制' in s):
                    continue
                lines.append(ln)
            if lines:
                cleaned_subs.append('\n'.join(lines).rstrip())
        if not cleaned_subs:
            continue
        merged_block = '\n\n'.join(cleaned_subs).rstrip() + '\n'
        merged.append(merged_block)
    return merged


def parse_xml_packages(text):
    """从 XML 文本中提取 package 节点，返回 {package_name: serialized_node_text}。"""
    res = {}
    if not text:
        return res
    try:
        root = ET.fromstring(text)
        # 查找所有 package 节点
        for pkg in root.findall('.//package'):
            name = pkg.attrib.get('name')
            if not name:
                # 尝试其他可能命名空间或属性
                name = pkg.attrib.get('{http://schemas.android.com/apk/res/android}name')
            if not name:
                continue
            # 序列化元素为字符串用于比较
            s = ET.tostring(pkg, encoding='utf-8').decode('utf-8')
            res[name] = s
        return res
    except Exception:
        # 回退：使用正则提取自闭合 package 标签
        pattern = re.compile(r'<package\b[^>]*?/?>', re.DOTALL)
        for m in pattern.finditer(text):
            s = m.group(0)
            mname = re.search(r'name\s*=\s*"([^"]+)"', s)
            if mname:
                res[mname.group(1)] = s
        return res


# Replace the parse_day_sections and build_day_block implementations with a single normalized version
from collections import OrderedDict as _OrderedDict


def parse_day_sections(block_text: str):
    """解析日期块，返回 OrderedDict 保留分区出现顺序。
    标题 '### X' 会被规范化（多余空白去除）。条目去重并保留显示文本顺序。
    """
    sections = _OrderedDict()
    if not block_text:
        return sections
    lines = block_text.splitlines()
    cur = None
    for ln in lines[1:]:  # skip date header
        s = ln.rstrip()
        s_strip = s.strip()
        if s_strip.startswith('###'):
            m = re.match(r'^###\s*(.*)', s_strip)
            if m:
                title = re.sub(r'\s+', ' ', m.group(1)).strip()
                if title not in sections:
                    sections[title] = []
                cur = title
            else:
                cur = None
            continue
        if not cur:
            continue
        if s_strip == '':
            continue
        # treat '- ' lines and contributor link lines uniformly
        if s_strip.startswith('- ') or s_strip.startswith('['):
            sections[cur].append(s_strip)
    # dedupe items per section, preserve order
    for k in list(sections.keys()):
        seen = _OrderedDict()
        new_items = []
        for it in sections[k]:
            key = it.strip()
            if key and key not in seen:
                seen[key] = True
                new_items.append(it)
        sections[k] = new_items
    return sections


def build_day_block(date_str: str, sections: dict, include_footer: bool = False):
    parts = [f'# {date_str}']
    # sections is an OrderedDict of title -> list(items)
    for title, items in sections.items():
        if not items:
            continue
        parts.append(f'### {title}')
        parts.extend(items)
        parts.append('')
    text = '\n'.join(parts).rstrip() + '\n'
    if include_footer:
        footer = '*由于管理器篇幅限制，查看完整日志请 [点击此处](https://github.com/Ianzb/MiNavBarImmerse/blob/main/changelog-full.md)*'
        text = text + '\n' + footer + '\n'
    return text


def normalize_item(item_text: str, kind: str) -> str:
    """将条目规范化为用于去重的键。
    kind: '新增'/'优化'/'贡献者'
    返回小写的规范键（不含多余空格）。
    """
    if not item_text:
        return ''
    s = item_text.strip()
    if kind in ('新增', '优化'):
        m = re.match(r'^-\s*(.*?)\s*(\(.*\))?$', s)
        name = m.group(1) if m else s
        key = re.sub(r'\s+', ' ', name).strip().lower()
        return key
    if kind == '贡献者':
        m = re.search(r'@([A-Za-z0-9_\-]+)', s)
        if m:
            return m.group(1).strip().lower()
        return s.lower()
    return s.lower()


def main():
    if not LIST_CSV.exists():
        print('list.csv not found, skipping changelog update')
        return 0

    commit_date_str, commit_dt = get_commit_beijing_date()

    current_text = LIST_CSV.read_text(encoding='utf-8')
    prev_text = git_show('list.csv')

    # 如果 git_show 返回 None，可能是因为没有父提交或文件在父提交中不存在。
    # 为避免在手动运行（无父提交可比对）时把所有条目误判为新增：
    # - 如果仓库没有父提交（HEAD^ 不存在），则将 prev_text 设为 current_text（认为无变更）；
    # - 如果父提交存在但文件在父提交中确实不存在，则保留 prev_text=''（表示文件首次加入），此时新增列表应包含所有条目。
    if prev_text is None:
        try:
            # 检查是否存在父提交
            subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD^'], cwd=ROOT, stderr=subprocess.DEVNULL)
            # 父提交存在，但 git_show 未能读取 list.csv（可能文件在父提交中不存在）
            prev_text = ''
            print('Previous list.csv not found in parent commit; treating as newly added file.')
        except subprocess.CalledProcessError:
            # 没有父提交（例如在本地手动运行、单提交仓库或 CI 的浅克隆），将 prev 视为当前，避免将所有应用标记为新增
            prev_text = current_text
            print('No parent commit found; treating previous list.csv as identical to current to avoid false additions.')

    # 读取并比对 XML
    xml_cur_text = (ROOT / 'module' / 'immerse_rules.xml').read_text(encoding='utf-8') if (ROOT / 'module' / 'immerse_rules.xml').exists() else None
    xml_prev_text = git_show('module/immerse_rules.xml')

    xml_cur_map = parse_xml_packages(xml_cur_text)
    xml_prev_map = parse_xml_packages(xml_prev_text)

    # 解析 CSV
    current_rows = parse_csv_text(current_text)
    prev_rows = parse_csv_text(prev_text)

    cur_map = rows_by_name(current_rows)
    prev_map = rows_by_name(prev_rows)

    # package -> app name 映射（基于当前 CSV）
    package_to_app = {}
    for r in current_rows:
        if len(r) > 1 and r[1]:
            package_to_app[r[1]] = r[0]

    added = []
    changed = []

    # 优先使用 XML 的新增/变更作为日志来源（以 package name 为准），并用 CSV 映射获取可读应用名
    # 如果不存在历史 XML（xml_prev_text 为 None），则退回到基于 CSV 的比较
    if xml_prev_text is not None and xml_cur_map:
        xml_added = [p for p in xml_cur_map.keys() if p not in xml_prev_map]
        xml_changed = [p for p in xml_cur_map.keys() if p in xml_prev_map and xml_cur_map.get(p) != xml_prev_map.get(p)]

        for pkg in xml_added:
            app = package_to_app.get(pkg, pkg)
            if not any(app == a for a, _ in added):
                added.append((app, None))

        for pkg in xml_changed:
            app = package_to_app.get(pkg, pkg)
            if any(app == a for a, _ in added):
                continue
            if not any(app == a for a, _ in changed):
                changed.append((app, None))
    else:
        # 回退：没有历史 XML（首次提交等），使用 CSV 比较作为日志来源
        for name, row in cur_map.items():
            if name not in prev_map:
                added.append((name, None))
            else:
                if row != prev_map[name]:
                    changed.append((name, None))

    # contributors：优先使用 GITHUB_ACTOR，否则使用最近提交作者名
    actor = None
    if 'GITHUB_ACTOR' in os.environ and os.environ.get('GITHUB_ACTOR'):
        actor = os.environ.get('GITHUB_ACTOR')
    else:
        try:
            actor = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%an'], cwd=ROOT).decode('utf-8').strip()
        except Exception:
            actor = None

    contribs = set()
    if actor:
        contribs.add(actor)

    # 读取并分离原有 changelog.md
    ch_text = CHLOG.read_text(encoding='utf-8') if CHLOG.exists() else ''
    existing_blocks = read_blocks_from_text(ch_text)

    # 合并相同日期的多个块为单个块，避免同一天重复标题
    merged_existing_blocks = merge_blocks_by_date(existing_blocks)

    # 目标日期为 commit_date_str；将不是目标日期的历史条目移动到 changelog-full
    # merged_existing_blocks 是按日期合并后的块列表，包含每个日期的单个块
    other_blocks = [b for b in merged_existing_blocks if block_date(b) != commit_date_str]
    # 如果存在已合并的当日块，保留它为 existing_today_block（无 footer）以便合并到 full
    existing_today_blocks = [b for b in merged_existing_blocks if block_date(b) == commit_date_str]
    existing_today_block = existing_today_blocks[0] if existing_today_blocks else None
    # 先把非当日块合并到 full
    merge_into_full(other_blocks)

    # 构建新的当天块，仅在有实际内容时包含对应分区
    # 合并 existing_today_block 的分区与当前新增/变更，并去重，优先保留已有条目
    existing_sections = parse_day_sections(existing_today_block) if existing_today_block else {'新增': [], '优化': [], '贡献者': []}

    # 当前计算出的新增/变更转为文本条目形式
    added_items = []
    for n, _ in added:
        if actor:
            added_items.append(f'- {n} (__@{actor}__)')
        else:
            added_items.append(f'- {n}')
    changed_items = []
    for n, _ in changed:
        if actor:
            changed_items.append(f'- {n} (__@{actor}__)')
        else:
            changed_items.append(f'- {n}')

    # contributors lines
    contrib_lines = []
    if contribs:
        # do not append extra trailing spaces to contributor links
        contrib_lines = [f'[@{c}](https://github.com/{c})' for c in sorted(contribs)]

    # 合并分区：先保持 existing 的顺序，然后追加新的、去重
    def merge_lists(existing_list, new_list):
        od = OrderedDict()
        for it in existing_list:
            key = it.strip()
            if key:
                od[key] = it
        for it in new_list:
            key = it.strip()
            if key and key not in od:
                od[key] = it
        return list(od.values())

    merged_new = merge_lists(existing_sections.get('新增', []), added_items)
    merged_opt = merge_lists(existing_sections.get('优化', []), changed_items)
    merged_contrib = merge_lists(existing_sections.get('贡献者', []), contrib_lines)

    sections_for_today = {'新增': merged_new, '优化': merged_opt, '贡献者': merged_contrib}

    # changelog.md 需要包含 footer 提示行；full 中不包含 footer
    new_block_text = build_day_block(commit_date_str, sections_for_today, include_footer=True)
    full_block_text = build_day_block(commit_date_str, sections_for_today, include_footer=False)

    if (sections_for_today['新增'] or sections_for_today['优化'] or sections_for_today['贡献者']):
        CHLOG.write_text(new_block_text, encoding='utf-8')
        # 将当天合并后的块与其他非当日块合并到 full
        merge_into_full([full_block_text] + other_blocks)
        print(f'Wrote changelog for {commit_date_str} and merged into changelog-full.md')
    else:
        # 无内容：从 changelog-full（已合并）寻找最近有内容的块并写入；否则保留原有（如果存在），或写最接近的空模板
        # 先尝试从原 existing_blocks 中找到最近有内容的块（按顺序），否则从 changelog-full 查找
        candidate = None
        # existing_blocks are in original order; check in reverse for latest
        for b in reversed(existing_blocks):
            if block_has_content(b):
                candidate = b
                break
        if not candidate and CHLOG_FULL.exists():
            full_blocks = read_blocks_from_text(CHLOG_FULL.read_text(encoding='utf-8'))
            for b in full_blocks:
                if block_has_content(b):
                    candidate = b
                    break
        if candidate:
            # 写回 changelog.md（并确保 footer 存在）
            # candidate 可能包含多个子区块，解析并保证 footer
            cand_sections = parse_day_sections(candidate)
            cand_block = build_day_block(block_date(candidate), cand_sections, include_footer=True)
            CHLOG.write_text(cand_block, encoding='utf-8')
            # 确保 full 包含该块（不带 footer）
            merge_into_full([build_day_block(block_date(candidate), cand_sections, include_footer=False)])
            print('No new changes; restored most recent non-empty block to changelog.md and ensured it exists in changelog-full.md')
        else:
            # no candidate: 写入一个仅含日期和提示的模板（不显示空分区）
            tpl = f"# {commit_date_str}\n\n*暂无更新记录，查看完整历史请[点击此处](https://github.com/Ianzb/MiNavBarImmerse/blob/main/changelog-full.md)*\n"
            CHLOG.write_text(tpl, encoding='utf-8')

    return 0


if __name__ == '__main__':
    sys.exit(main())
