#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import json
import re
import sys
from typing import Dict, List, Optional, Any, Tuple


def extract_comments_from_xml(xml_content: str) -> Dict[int, str]:
    """
    从XML内容中提取注释及其行号
    """
    comments = {}
    lines = xml_content.split('\n')

    for i, line in enumerate(lines):
        line = line.strip()
        # 匹配 <!-- 注释内容 -->
        if line.startswith('<!--') and line.endswith('-->'):
            comment_content = line[4:-3].strip()  # 移除 <!-- 和 -->
            comments[i] = comment_content

    return comments


def find_nearest_comment(package_line_num: int, comments: Dict[int, str]) -> Optional[str]:
    """
    查找距离package元素最近的注释
    """
    if not comments:
        return None

    # 找到在package之前的最近注释
    nearest_line = -1
    nearest_comment = None

    for comment_line, comment_content in comments.items():
        if comment_line < package_line_num and comment_line > nearest_line:
            nearest_line = comment_line
            nearest_comment = comment_content

    return nearest_comment


def parse_old_xml_to_json(xml_content: str) -> Dict[str, Any]:
    """
    将旧版XML格式转换为新版JSON格式
    """

    # 先提取所有注释
    comments = extract_comments_from_xml(xml_content)

    # 解析XML
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        # 如果解析失败，尝试清理XML（有时会有编码问题）
        # 移除可能的BOM字符
        if xml_content.startswith('\ufeff'):
            xml_content = xml_content[1:]
        root = ET.fromstring(xml_content)

    # 创建新的JSON结构
    nbi_rules = {}

    # 获取所有行号信息
    lines = xml_content.split('\n')

    # 遍历XML中的所有package元素
    for package_elem in root.findall('package'):
        # 提取包名和属性
        package_name = package_elem.attrib.get("name", "")
        if not package_name:
            continue

        enable = package_elem.attrib.get("enable", "false").lower() == "true"
        activity_rule_str = package_elem.attrib.get("activityRule", "")

        # 查找package在原始XML中的行号
        package_line_num = -1
        for i, line in enumerate(lines):
            if package_name in line and 'name="' in line:
                package_line_num = i
                break

        # 获取最近的注释作为应用名称
        app_name = ""
        if package_line_num != -1:
            comment = find_nearest_comment(package_line_num, comments)
            if comment:
                # 清理注释内容，只取应用名称部分
                # 移除可能的多余空格和特殊字符
                app_name = comment.strip()
                # 移除"应用名"、"软件名"等后缀

        # 解析activityRule字符串
        activity_rules = {}
        if activity_rule_str:
            rules = activity_rule_str.split(',')
            for rule in rules:
                rule = rule.strip()
                if not rule:
                    continue

                parts = rule.split(':')
                if len(parts) < 2:
                    continue

                activity_name = parts[0].strip()

                try:
                    mode = int(parts[1].strip())
                except ValueError:
                    mode = 0  # 默认值

                color = None
                # 只有mode=1时才可能有color
                if mode == 1 and len(parts) >= 3:
                    try:
                        color_val = parts[2].strip()
                        if color_val:  # 检查是否为空字符串
                            color = int(color_val)
                    except (ValueError, IndexError):
                        color = None

                activity_rules[activity_name] = {
                    "mode": mode,
                    "color": color
                }

        # 构建应用配置
        app_config = {
            "name": "未知",
            "enable": enable,
            "activityRules": activity_rules
        }

        # 如果有提取到应用名称，添加到配置中
        if app_name:
            app_config["name"] = app_name

        nbi_rules[package_name] = app_config

    return nbi_rules


def convert_xml_file_to_json(xml_file_path: str, output_json_path: str = None) -> None:
    """
    将XML文件转换为JSON文件
    """

    try:
        # 读取XML文件内容
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # 移除XML声明前面的任何空白字符
        xml_content = xml_content.strip()

        # 解析并转换
        nbi_rules = parse_old_xml_to_json(xml_content)

        # 构建完整的JSON结构（只包含NBIRules部分）
        result = {
            "NBIRules": nbi_rules
        }

        # 输出结果
        if output_json_path:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"转换完成！JSON文件已保存到: {output_json_path}")
        else:
            # 输出到控制台
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except ET.ParseError as e:
        print(f"XML解析错误: {e}")
        print("请检查XML文件格式是否正确")
        sys.exit(1)
    except Exception as e:
        print(f"转换过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    主函数：处理命令行参数
    """
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description='将旧版NBI XML规则文件转换为新版JSON格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s input.xml                    # 输出到控制台
  %(prog)s input.xml -o output.json     # 输出到文件
  %(prog)s -f input.xml                 # 输出到控制台（同第一种）
        """
    )

    parser.add_argument('input_file', help='输入的XML文件路径')
    parser.add_argument('-o', '--output', help='输出的JSON文件路径（可选）')
    parser.add_argument('-f', '--force', action='store_true',
                        help='如果输出文件已存在，则覆盖')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细输出')

    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误：输入文件 '{args.input_file}' 不存在")
        sys.exit(1)

    # 检查输出文件是否存在
    if args.output and not args.force:
        if os.path.exists(args.output):
            response = input(f"文件 {args.output} 已存在，是否覆盖？(y/N): ")
            if response.lower() != 'y':
                print("操作已取消")
                sys.exit(0)

    # 执行转换
    convert_xml_file_to_json(args.input_file, args.output)

    if args.verbose and args.output:
        print(f"\n已转换 {args.input_file} -> {args.output}")


def test_conversion():
    """
    测试转换函数
    """
    test_xml = """<?xml version="1.0" encoding="utf-8"?>
<NBIRules xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:noNamespaceSchemaLocation="immerse_rules.xsd">

    <!-- 斗鱼 -->
    <package name="air.tv.douyu.android" enable="true" activityRule="com.douyu.module.player.p.socialinteraction.functions.switch_room.AudioPlayerPagerActivity:0,com.douyu.module.list.view.activity.CustomHomeSetupBActivity:1:1,com.douyu.sdk.rn.activity.DYReactActivity:1:-1,com.douyu.module.vod.p.voddownload.VodDownloadActivity:1:1"/>

    <!-- MT管理器 -->
    <package name="bin.mt.plus" enable="true" activityRule="*:2,com.byyoung.setting.HomePage.activitys.MainActivity:0"/>

    <!-- 测试应用 -->
    <package name="com.example.test" enable="false" activityRule="MainActivity:1,SettingsActivity:0,VideoActivity:1:16777215"/>

    <!-- 只有通配符的应用 -->
    <package name="com.example.wildcard" enable="true" activityRule="*:3"/>

</NBIRules>"""

    print("测试转换:")
    print("输入XML:")
    print(test_xml)
    print("\n" + "=" * 50 + "\n")
    print("输出JSON:")

    result = parse_old_xml_to_json(test_xml)
    full_result = {"NBIRules": result}
    print(json.dumps(full_result, ensure_ascii=False, indent=2))

    # 显示统计信息
    print("\n" + "=" * 50)
    print("转换统计:")
    print(f"总应用数: {len(result)}")
    total_activities = 0
    for app_id, app_config in result.items():
        activities = len(app_config.get('activityRules', {}))
        total_activities += activities
        print(f"  {app_id}: {activities} 个活动规则")
    print(f"总活动规则数: {total_activities}")


if __name__ == "__main__":
    # 如果没有命令行参数，显示帮助信息并运行测试
    if len(sys.argv) == 1:
        print("NBI XML转JSON转换工具")
        print("=" * 50)
        print("使用方法: python convert_nbi.py <input.xml> [-o output.json]")
        print("\n参数说明:")
        print("  <input.xml>    : 输入的XML文件路径")
        print("  -o output.json : 输出的JSON文件路径（可选）")
        print("  -f             : 强制覆盖已存在的输出文件")
        print("  -v             : 显示详细输出")
        print("\n示例:")
        print("  python convert_nbi.py old_rules.xml")
        print("  python convert_nbi.py old_rules.xml -o new_rules.json")
        print("  python convert_nbi.py old_rules.xml -o new_rules.json -f -v")

        print("\n" + "=" * 50)
        print("运行测试示例:")
        try:
            test_conversion()
        except Exception as e:
            print(f"测试过程中发生错误: {e}")
            import traceback

            traceback.print_exc()
    else:
        main()
