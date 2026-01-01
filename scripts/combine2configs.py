#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NBI JSON配置文件合并工具
用于合并两个NBI配置文件，重复应用以第二个文件覆盖第一个的相同activity
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


def load_json_file(file_path: str) -> Dict[str, Any]:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 不存在")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误：JSON文件解析失败 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误：读取文件失败 - {e}")
        sys.exit(1)


def save_json_file(file_path: str, data: Dict[str, Any]) -> None:
    """保存JSON文件，确保name字段排在第一位"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            # 使用自定义序列化函数，确保name字段排在第一位
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False,
                      separators=(',', ': '), default=custom_serializer)
        print(f"成功保存到: {file_path}")
    except Exception as e:
        print(f"错误：保存文件失败 - {e}")
        sys.exit(1)


def custom_serializer(obj):
    """自定义序列化器"""
    if isinstance(obj, dict):
        # 重新排序字典，确保name字段在第一
        sorted_dict = {}

        # 首先添加name字段
        if 'name' in obj:
            sorted_dict['name'] = obj['name']

        # 然后添加其他字段，按字母顺序排序
        other_keys = [k for k in obj.keys() if k != 'name']
        for key in sorted(other_keys):
            sorted_dict[key] = obj[key]

        return sorted_dict

    # 对于非字典对象，使用默认序列化
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def order_package_config(package_config: Dict[str, Any]) -> Dict[str, Any]:
    """重新排序应用配置，确保name字段在第一"""
    if not isinstance(package_config, dict):
        return package_config

    ordered_config = {}

    # 1. name字段永远第一
    if 'name' in package_config:
        ordered_config['name'] = package_config['name']

    # 2. enable字段第二
    if 'enable' in package_config:
        ordered_config['enable'] = package_config['enable']

    # 3. activityRules字段第三
    if 'activityRules' in package_config:
        ordered_config['activityRules'] = package_config['activityRules']

    # 4. 其他字段按字母顺序
    other_keys = [k for k in package_config.keys()
                  if k not in ['name', 'enable', 'activityRules']]
    for key in sorted(other_keys):
        ordered_config[key] = package_config[key]

    return ordered_config


def merge_nbi_configs(config1: Dict[str, Any], config2: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并两个NBI配置文件

    合并规则：
    1. 使用第二个文件的 metadata（dataVersion, modules, modifyApps）
    2. 合并NBIRules：
       - 第二个文件中的应用完全覆盖第一个文件中的相同应用
       - 不同应用则合并
       - 相同应用的activityRules中，第二个文件覆盖第一个文件的相同activity

    返回：合并后的配置字典
    """

    # 创建合并结果的副本，从第二个文件开始
    merged_config = config2.copy()

    # 确保NBIRules存在
    if "NBIRules" not in merged_config:
        merged_config["NBIRules"] = {}

    # 获取两个配置的NBIRules
    nbi_rules1 = config1.get("NBIRules", {})
    nbi_rules2 = config2.get("NBIRules", {})

    # 开始合并
    merged_rules = {}

    # 首先添加第一个文件的所有规则
    for package_name, package_config in nbi_rules1.items():
        merged_rules[package_name] = package_config.copy()

    # 然后用第二个文件的规则覆盖/添加
    for package_name, package_config2 in nbi_rules2.items():
        if package_name in merged_rules:
            # 应用已存在，合并activityRules
            package_config1 = merged_rules[package_name]

            # 创建合并后的包配置，优先使用第二个文件的基础配置
            merged_package_config = package_config2.copy()

            # 合并activityRules
            if "activityRules" in package_config1:
                activity_rules1 = package_config1.get("activityRules", {})
                activity_rules2 = package_config2.get("activityRules", {})

                # 合并activityRules：第二个覆盖第一个
                merged_activity_rules = activity_rules1.copy()
                merged_activity_rules.update(activity_rules2)

                merged_package_config["activityRules"] = merged_activity_rules

            # 如果第一个文件有name而第二个没有，保留第一个的name
            if "name" in package_config1 and "name" not in package_config2:
                merged_package_config["name"] = package_config1["name"]

            # 如果两个都有enable，使用第二个的
            if "enable" in package_config2:
                merged_package_config["enable"] = package_config2["enable"]
            elif "enable" in package_config1:
                merged_package_config["enable"] = package_config1["enable"]

            # 应用排序，确保name在第一
            merged_package_config = order_package_config(merged_package_config)

            merged_rules[package_name] = merged_package_config
        else:
            # 新应用，直接添加，并确保排序
            package_config2 = order_package_config(package_config2.copy())
            merged_rules[package_name] = package_config2

    # 对合并后的所有应用配置进行排序
    merged_rules = {k: order_package_config(v) for k, v in merged_rules.items()}

    merged_config["NBIRules"] = merged_rules

    return merged_config


def merge_json_files(file1: str, file2: str, output_file: str = None) -> Dict[str, Any]:
    """
    合并两个JSON文件

    Args:
        file1: 第一个JSON文件路径
        file2: 第二个JSON文件路径（优先级高）
        output_file: 输出文件路径，如果为None则输出到控制台

    Returns:
        合并后的配置字典
    """

    print(f"正在合并配置文件...")
    print(f"文件1: {file1}")
    print(f"文件2: {file2} (优先级高)")

    # 加载文件
    config1 = load_json_file(file1)
    config2 = load_json_file(file2)

    # 验证文件结构
    if "NBIRules" not in config1:
        print(f"警告：文件1缺少NBIRules字段")
        config1["NBIRules"] = {}

    if "NBIRules" not in config2:
        print(f"警告：文件2缺少NBIRules字段")
        config2["NBIRules"] = {}

    # 合并配置
    merged_config = merge_nbi_configs(config1, config2)

    # 输出统计信息
    stats1 = get_config_stats(config1)
    stats2 = get_config_stats(config2)
    stats_merged = get_config_stats(merged_config)

    print("\n" + "=" * 60)
    print("合并统计信息:")
    print("=" * 60)
    print(f"{'项目':<25} {'文件1':<10} {'文件2':<10} {'合并后':<10} {'变化':<10}")
    print("-" * 60)
    print(f"{'应用数量':<25} {stats1['app_count']:<10} {stats2['app_count']:<10} {stats_merged['app_count']:<10} {stats_merged['app_count'] - stats1['app_count']:>+9}")
    print(f"{'活动规则总数':<25} {stats1['activity_count']:<10} {stats2['activity_count']:<10} {stats_merged['activity_count']:<10} {stats_merged['activity_count'] - stats1['activity_count']:>+9}")
    print(f"{'通配符规则(*:x)':<25} {stats1['wildcard_count']:<10} {stats2['wildcard_count']:<10} {stats_merged['wildcard_count']:<10} {stats_merged['wildcard_count'] - stats1['wildcard_count']:>+9}")
    print(f"{'启用沉浸的应用':<25} {stats1['enabled_count']:<10} {stats2['enabled_count']:<10} {stats_merged['enabled_count']:<10} {stats_merged['enabled_count'] - stats1['enabled_count']:>+9}")
    print("=" * 60)

    # 查找冲突的应用
    conflicting_apps = find_conflicting_apps(config1, config2)
    if conflicting_apps:
        print("\n应用合并详情（存在冲突的应用）:")
        print("-" * 60)
        for app_id in conflicting_apps:
            print(f"\n应用: {app_id}")
            app1 = config1["NBIRules"].get(app_id, {})
            app2 = config2["NBIRules"].get(app_id, {})
            app_merged = merged_config["NBIRules"][app_id]

            print(f"  文件1: {len(app1.get('activityRules', {}))} 个活动规则")
            print(f"  文件2: {len(app2.get('activityRules', {}))} 个活动规则")
            print(f"  合并后: {len(app_merged.get('activityRules', {}))} 个活动规则")

            # 查找具体的冲突activity
            if app_id in config1["NBIRules"] and app_id in config2["NBIRules"]:
                activities1 = set(app1.get('activityRules', {}).keys())
                activities2 = set(app2.get('activityRules', {}).keys())
                common = activities1 & activities2
                if common:
                    print(f"  冲突的活动规则: {len(common)} 个")
                    for activity in sorted(common)[:5]:  # 只显示前5个
                        mode1 = app1['activityRules'][activity].get('mode', 'N/A')
                        mode2 = app2['activityRules'][activity].get('mode', 'N/A')
                        print(f"    - {activity}: mode {mode1} → {mode2} (文件2覆盖)")
                    if len(common) > 5:
                        print(f"    ... 还有 {len(common) - 5} 个")

    # 输出或保存
    if output_file:
        save_json_file(output_file, merged_config)
    else:
        print("\n合并后的JSON配置:")
        print("=" * 60)
        # 使用自定义序列化器确保name字段在第一
        print(json.dumps(merged_config, ensure_ascii=False, indent=2,
                         sort_keys=False, default=custom_serializer))

    return merged_config


def get_config_stats(config: Dict[str, Any]) -> Dict[str, int]:
    """获取配置文件的统计信息"""
    nbi_rules = config.get("NBIRules", {})

    app_count = len(nbi_rules)
    activity_count = 0
    wildcard_count = 0
    enabled_count = 0

    for app_id, app_config in nbi_rules.items():
        activity_rules = app_config.get("activityRules", {})
        activity_count += len(activity_rules)

        # 统计通配符规则
        if "*" in activity_rules:
            wildcard_count += 1

        # 统计启用沉浸的应用
        if app_config.get("enable", False):
            enabled_count += 1

    return {
        "app_count": app_count,
        "activity_count": activity_count,
        "wildcard_count": wildcard_count,
        "enabled_count": enabled_count
    }


def find_conflicting_apps(config1: Dict[str, Any], config2: Dict[str, Any]) -> List[str]:
    """查找在两个文件中都存在的应用"""
    apps1 = set(config1.get("NBIRules", {}).keys())
    apps2 = set(config2.get("NBIRules", {}).keys())
    return sorted(apps1 & apps2)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='合并两个NBI JSON配置文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
合并规则：
  1. 第二个文件的配置优先（覆盖第一个文件）
  2. 相同应用的activityRules中，第二个文件覆盖第一个
  3. metadata（dataVersion等）使用第二个文件
  4. name字段始终排在应用配置的第一位

示例：
  %(prog)s base.json update.json -o merged.json
  %(prog)s old.json new.json          # 输出到控制台
  %(prog)s --test                     # 运行测试
        """
    )

    parser.add_argument('file1', nargs='?', help='第一个JSON文件（基础文件）')
    parser.add_argument('file2', nargs='?', help='第二个JSON文件（更新文件，优先级高）')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    parser.add_argument('-f', '--force', action='store_true', help='覆盖已存在的输出文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细合并信息')
    parser.add_argument('--test', action='store_true', help='运行测试')

    args = parser.parse_args()

    # 运行测试
    if args.test:
        run_test()
        return

    # 验证参数
    if not args.file1 or not args.file2:
        parser.print_help()
        print("\n错误：需要指定两个输入文件")
        return

    # 检查输出文件
    if args.output and not args.force:
        if os.path.exists(args.output):
            response = input(f"文件 '{args.output}' 已存在，是否覆盖？(y/N): ")
            if response.lower() != 'y':
                print("操作已取消")
                return

    # 执行合并
    merge_json_files(args.file1, args.file2, args.output)


def run_test():
    """运行测试"""
    print("运行合并测试...")
    print("验证name字段是否始终在第一位置\n")

    # 创建测试数据
    config1 = {
        "dataVersion": "20240101",
        "modules": "navigation_bar_immersive_application_config_new",
        "modifyApps": "modifyApps",
        "NBIRules": {
            "com.example.app1": {
                "enable": True,
                "name": "测试应用1",  # name不在第一位置
                "activityRules": {
                    "MainActivity": {"mode": 1, "color": 255},
                    "SettingsActivity": {"mode": 0, "color": None},
                    "*": {"mode": 2, "color": None}
                }
            },
            "com.example.app2": {
                "name": "测试应用2",  # name在第一位置
                "enable": False,
                "activityRules": {
                    "MainActivity": {"mode": 0, "color": None}
                }
            }
        }
    }

    config2 = {
        "dataVersion": "20250101",
        "modules": "navigation_bar_immersive_application_config_new",
        "modifyApps": "modifyApps",
        "NBIRules": {
            "com.example.app1": {
                "enable": False,  # 覆盖enable
                "activityRules": {  # 没有name字段
                    "MainActivity": {"mode": 2, "color": 16777215},  # 覆盖
                    "VideoActivity": {"mode": 1, "color": 255}  # 新增
                }
            },
            "com.example.app3": {
                "name": "新应用3",
                "enable": True,
                "activityRules": {
                    "*": {"mode": 3, "color": None}
                }
            }
        }
    }

    # 保存测试文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
        json.dump(config1, f1, ensure_ascii=False, indent=2)
        file1 = f1.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
        json.dump(config2, f2, ensure_ascii=False, indent=2)
        file2 = f2.name

    print(f"创建测试文件: {file1}, {file2}")

    # 执行合并
    merged = merge_nbi_configs(config1, config2)

    print("\n测试结果:")
    print("=" * 60)

    # 验证name字段是否在第一位置
    all_correct = True
    for app_id, app_config in merged.get("NBIRules", {}).items():
        keys = list(app_config.keys())
        if 'name' in app_config:
            if keys[0] != 'name':
                print(f"✗ {app_id}: name字段不在第一位置，顺序为: {keys}")
                all_correct = False
            else:
                print(f"✓ {app_id}: name字段在第一位置")
        else:
            print(f"⚠ {app_id}: 没有name字段")

    print("\n合并后配置示例:")
    print("=" * 60)

    # 显示一个应用的配置，验证排序
    example_app = "com.example.app1"
    if example_app in merged.get("NBIRules", {}):
        print(f"{example_app} 的配置顺序:")
        app_config = merged["NBIRules"][example_app]
        for i, (key, value) in enumerate(app_config.items(), 1):
            if key == 'activityRules':
                print(f"  {i}. {key}: {len(value)}个活动规则")
            else:
                print(f"  {i}. {key}: {value}")

    # 验证合并逻辑
    expected_app1_config = {
        "name": "测试应用1",  # 从config1继承，应该在第一位置
        "enable": False,  # 被config2覆盖
        "activityRules": {
            "MainActivity": {"mode": 2, "color": 16777215},  # config2覆盖
            "SettingsActivity": {"mode": 0, "color": None},  # config1保留
            "*": {"mode": 2, "color": None},  # config1保留
            "VideoActivity": {"mode": 1, "color": 255}  # config2新增
        }
    }

    # 检查排序后的配置
    actual_app1_config = merged.get("NBIRules", {}).get("com.example.app1", {})

    # 验证字段顺序
    actual_keys = list(actual_app1_config.keys())
    expected_order = ['name', 'enable', 'activityRules']

    print(f"\n字段顺序验证:")
    print(f"期望顺序: {expected_order}")
    print(f"实际顺序: {actual_keys}")

    # 检查前三个字段的顺序
    if actual_keys[:3] == expected_order:
        print("✓ 字段顺序正确")
    else:
        print("✗ 字段顺序不正确")
        all_correct = False

    # 验证内容
    content_correct = True
    for key in ['name', 'enable']:
        if actual_app1_config.get(key) != expected_app1_config.get(key):
            print(f"✗ {key} 字段值不正确")
            content_correct = False

    if 'activityRules' in actual_app1_config:
        actual_activities = set(actual_app1_config['activityRules'].keys())
        expected_activities = set(expected_app1_config['activityRules'].keys())
        if actual_activities == expected_activities:
            print("✓ activityRules 包含正确数量的活动")
        else:
            print(f"✗ activityRules 不正确")
            print(f"  缺少: {expected_activities - actual_activities}")
            print(f"  多余: {actual_activities - expected_activities}")
            content_correct = False

    if all_correct and content_correct:
        print("\n✓ 所有测试通过！")
    else:
        print("\n✗ 测试失败")

    # 清理临时文件
    os.unlink(file1)
    os.unlink(file2)


def print_formatted_json(data: Dict[str, Any]) -> None:
    """格式化输出JSON，确保name字段在第一"""
    import json
    print(json.dumps(data, ensure_ascii=False, indent=2,
                     sort_keys=False, default=custom_serializer))


if __name__ == "__main__":
    main()