#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NBI JSON 转 XML 配置转换工具
将新版JSON格式转换为旧版XML格式的配置文件
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from xml.dom import minidom
import xml.etree.ElementTree as ET


def json_to_xml(json_path: str, output_xml_path: str = None) -> str:
    """
    将JSON配置文件转换为XML格式

    Args:
        json_path: JSON文件路径
        output_xml_path: 输出XML文件路径（如果为None，则输出到控制台）

    Returns:
        str: 生成的XML字符串
    """
    try:
        # 加载JSON文件
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print(f"正在转换: {json_path}")

        # 验证JSON结构
        if "NBIRules" not in config:
            raise ValueError("JSON文件中缺少 NBIRules 字段")

        nbi_rules = config.get("NBIRules", {})

        # 创建XML根元素
        root = ET.Element("NBIRules")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # 统计信息
        total_apps = len(nbi_rules)
        total_activities = 0
        converted_apps = 0

        # 按包名排序处理
        for package_name in sorted(nbi_rules.keys()):
            package_config = nbi_rules[package_name]

            # 检查是否启用
            enable = package_config.get("enable", False)
            if not enable:
                print(f"  跳过: {package_name} (enable=false)")
                continue

            # 获取应用名称（用于注释）
            app_name = package_config.get("name", "")

            # 转换activityRules为旧格式
            activity_rules = package_config.get("activityRules", {})
            if not activity_rules:
                print(f"  跳过: {package_name} (无activityRules)")
                continue

            # 构建activityRule字符串
            activity_rule_parts = []

            # 首先处理通配符规则（如果有）
            if "*" in activity_rules:
                rule = activity_rules["*"]
                mode = rule.get("mode", 0)
                color = rule.get("color")

                if mode == 1 and color is not None:
                    activity_rule_parts.append(f"*:{mode}:{color}")
                else:
                    activity_rule_parts.append(f"*:{mode}")

            # 处理其他具体Activity规则
            for activity_name, rule in activity_rules.items():
                if activity_name == "*":
                    continue  # 通配符已处理

                mode = rule.get("mode", 0)
                color = rule.get("color")

                # 构建规则字符串
                if mode == 1 and color is not None:
                    rule_str = f"{activity_name}:{mode}:{color}"
                else:
                    rule_str = f"{activity_name}:{mode}"

                activity_rule_parts.append(rule_str)

            # 如果有规则，创建package元素
            if activity_rule_parts:
                # 添加应用名称注释
                if app_name:
                    comment = ET.Comment(f" {app_name} ")
                    root.append(comment)

                # 创建package元素
                package_elem = ET.Element("package")
                package_elem.set("name", package_name)
                package_elem.set("enable", "true")

                # 构建activityRule属性值
                activity_rule_value = ",".join(activity_rule_parts)
                package_elem.set("activityRule", activity_rule_value)

                # 添加disableVersionCode（如果存在）
                disable_version = package_config.get("disableVersionCode")
                if disable_version:
                    package_elem.set("disableVersionCode", str(disable_version))

                root.append(package_elem)
                converted_apps += 1
                total_activities += len(activity_rule_parts)

                print(f"  转换: {package_name} ({len(activity_rule_parts)} 个规则)")

        # 生成XML字符串
        xml_str = ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

        # 美化XML格式
        xml_pretty = prettify_xml(xml_str)

        # 添加XML声明
        final_xml =  xml_pretty

        # 输出统计信息
        print("\n" + "=" * 60)
        print("转换统计信息:")
        print("=" * 60)
        print(f"JSON应用总数: {total_apps}")
        print(f"成功转换应用: {converted_apps}")
        print(f"总活动规则数: {total_activities}")

        # 保存或输出
        if output_xml_path:
            with open(output_xml_path, 'w', encoding='utf-8') as f:
                f.write(final_xml)
            print(f"\nXML文件已保存到: {output_xml_path}")

            # 验证转换结果
            print("\n验证转换结果...")
            verify_conversion(json_path, output_xml_path)
        else:
            print("\n生成的XML内容:")
            print("=" * 60)
            print(final_xml)

        return final_xml

    except FileNotFoundError:
        print(f"错误：文件 '{json_path}' 不存在")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误：JSON文件解析失败 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误：转换过程中发生错误 - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def prettify_xml(xml_str: str) -> str:
    """美化XML格式"""
    try:
        parsed = minidom.parseString(xml_str)
        pretty_xml = parsed.toprettyxml(indent="    ", encoding='utf-8')
        return pretty_xml.decode('utf-8')
    except:
        # 如果minidom失败，使用简单格式化
        return xml_str.replace('><', '>\n<')


def verify_conversion(json_path: str, xml_path: str) -> None:
    """
    验证转换结果，确保没有数据丢失
    """
    try:
        # 读取原始JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            original_config = json.load(f)

        # 读取生成的XML
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # 解析XML
        root = ET.fromstring(xml_content)

        # 统计
        json_apps = original_config.get("NBIRules", {})
        xml_packages = root.findall('package')

        # 检查启用的应用
        enabled_json_apps = []
        for pkg_name, pkg_config in json_apps.items():
            if pkg_config.get('enable', False) and pkg_config.get('activityRules'):
                enabled_json_apps.append(pkg_name)

        print(f"  JSON中启用的应用: {len(enabled_json_apps)}")
        print(f"  XML中生成的应用: {len(xml_packages)}")

        if len(enabled_json_apps) == len(xml_packages):
            print("  ✓ 应用数量一致")
        else:
            print(f"  ⚠ 应用数量不一致")

            # 找出差异
            json_set = set(enabled_json_apps)
            xml_set = {pkg.get('name') for pkg in xml_packages}

            missing = json_set - xml_set
            extra = xml_set - json_set

            if missing:
                print(f"    在XML中缺失: {missing}")
            if extra:
                print(f"    在XML中多余: {extra}")

        # 检查具体规则转换
        print("\n  规则转换详情:")
        for package_elem in xml_packages:
            pkg_name = package_elem.get('name')
            activity_rule = package_elem.get('activityRule', '')

            if pkg_name in json_apps:
                pkg_config = json_apps[pkg_name]
                json_rules = pkg_config.get('activityRules', {})

                # 解析XML规则
                xml_rules_list = activity_rule.split(',')

                print(f"    {pkg_name}:")
                print(f"      JSON规则数: {len(json_rules)}")
                print(f"      XML规则数: {len(xml_rules_list)}")

                # 验证mode和color转换
                for xml_rule in xml_rules_list[:3]:  # 只显示前3个
                    parts = xml_rule.split(':')
                    if len(parts) >= 2:
                        activity = parts[0]
                        mode = int(parts[1])
                        color = int(parts[2]) if len(parts) >= 3 else None

                        if activity in json_rules:
                            json_rule = json_rules[activity]
                            if json_rule.get('mode') == mode:
                                print(f"      ✓ {activity}: mode={mode}")
                            else:
                                print(f"      ✗ {activity}: mode不匹配 (JSON:{json_rule.get('mode')}, XML:{mode})")

    except Exception as e:
        print(f"  验证过程中出错: {e}")


def convert_json_files(json_files: List[str], output_dir: str = None) -> None:
    """
    批量转换多个JSON文件

    Args:
        json_files: JSON文件路径列表
        output_dir: 输出目录（如果为None，则输出到控制台）
    """
    for json_file in json_files:
        path = Path(json_file)
        if not path.exists():
            print(f"文件不存在: {json_file}")
            continue

        # 确定输出路径
        if output_dir:
            output_path = Path(output_dir) / f"{path.stem}.xml"
            json_to_xml(json_file, str(output_path))
        else:
            print(f"\n{'=' * 60}")
            print(f"转换文件: {json_file}")
            print('=' * 60)
            json_to_xml(json_file)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='将NBI JSON配置文件转换为XML格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
转换规则：
  1. 只转换 enable=true 的应用
  2. 只转换有 activityRules 的应用
  3. 按包名排序输出
  4. 应用名称作为注释添加在package元素前
  5. 通配符 * 规则排在前面

转换格式：
  JSON: {"mode": 1, "color": -16777216}
  XML: ActivityName:1:-16777216

示例：
  %(prog)s config.json -o output.xml
  %(prog)s config.json                    # 输出到控制台
  %(prog)s -b *.json -d output_xml        # 批量转换
        """
    )

    parser.add_argument('json_file', nargs='?', help='JSON文件路径')
    parser.add_argument('-o', '--output', help='输出XML文件路径')
    parser.add_argument('-b', '--batch', nargs='+', help='批量转换多个JSON文件')
    parser.add_argument('-d', '--directory', help='批量输出目录')
    parser.add_argument('-f', '--force', action='store_true', help='覆盖已存在的输出文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细转换信息')

    args = parser.parse_args()

    # 检查参数
    if not args.json_file and not args.batch:
        parser.print_help()
        print("\n错误：需要指定JSON文件或使用批量模式")
        return

    # 检查输出文件
    if args.output and not args.force:
        if os.path.exists(args.output):
            response = input(f"文件 '{args.output}' 已存在，是否覆盖？(y/N): ")
            if response.lower() != 'y':
                print("操作已取消")
                return

    # 执行转换
    if args.batch:
        # 批量转换模式
        if args.directory:
            os.makedirs(args.directory, exist_ok=True)

        print(f"批量转换 {len(args.batch)} 个JSON文件...")
        convert_json_files(args.batch, args.directory)
    else:
        # 单个文件转换
        json_to_xml(args.json_file, args.output)


def test_conversion():
    """运行转换测试"""
    print("运行JSON转XML测试...")

    # 创建测试JSON数据
    test_json = {
        "dataVersion": "250912",
        "modules": "navigation_bar_immersive_application_config_new",
        "modifyApps": "modifyApps",
        "NBIRules": {
            "com.example.app1": {
                "name": "测试应用1",
                "enable": True,
                "activityRules": {
                    "*": {"mode": 2, "color": None},
                    "MainActivity": {"mode": 1, "color": -16777216},
                    "SettingsActivity": {"mode": 0, "color": None}
                }
            },
            "com.example.app2": {
                "name": "测试应用2",
                "enable": True,
                "disableVersionCode": 100,
                "activityRules": {
                    "VideoActivity": {"mode": 1, "color": -1}
                }
            },
            "com.example.disabled": {
                "name": "禁用应用",
                "enable": False,  # 应该被跳过
                "activityRules": {
                    "MainActivity": {"mode": 1, "color": 255}
                }
            }
        }
    }

    # 保存测试JSON文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_json, f, ensure_ascii=False, indent=2)
        json_file = f.name

    print(f"创建测试文件: {json_file}")

    # 执行转换（输出到控制台）
    xml_result = json_to_xml(json_file)

    print("\n测试完成!")

    # 清理临时文件
    os.unlink(json_file)


if __name__ == "__main__":
    # 如果没有命令行参数，显示帮助信息
    if len(sys.argv) == 1:
        print("NBI JSON 转 XML 转换工具")
        print("=" * 50)
        print("使用方法: python json_to_xml.py <input.json> [-o output.xml]")
        print("\n示例:")
        print("  python json_to_xml.py config.json -o immerse_rules.xml")
        print("  python json_to_xml.py --test  # 运行测试")

        print("\n" + "=" * 50)
        print("运行测试示例:")
        try:
            test_conversion()
        except Exception as e:
            print(f"测试过程中发生错误: {e}")
    else:
        main()