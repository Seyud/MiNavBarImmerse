#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量规则更新处理器
支持对immerse_rules.xml文件进行精细的增量修改操作
"""

import sys
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Optional, Tuple
import argparse

class IncrementalRuleUpdater:
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.tree = None
        self.root = None
        self.load_xml()
    
    def load_xml(self):
        """加载XML文件"""
        try:
            self.tree = ET.parse(self.xml_path)
            self.root = self.tree.getroot()
        except ET.ParseError as e:
            raise Exception(f"XML解析错误: {e}")
        except FileNotFoundError:
            raise Exception(f"XML文件不存在: {self.xml_path}")
    
    def find_package(self, package_name: str) -> Optional[ET.Element]:
        """查找指定包名的package元素"""
        for package in self.root.findall('package'):
            if package.get('name') == package_name:
                return package
        return None
    
    def parse_activity_rule(self, activity_rule: str) -> Dict[str, str]:
        """解析activityRule字符串为字典"""
        activities = {}
        if not activity_rule:
            return activities
        
        rules = activity_rule.split(',')
        for rule in rules:
            parts = rule.strip().split(':')
            if len(parts) >= 2:
                activity_name = parts[0]
                rule_value = ':'.join(parts[1:])  # 重新组合规则部分
                activities[activity_name] = rule_value
            elif len(parts) == 1:
                # 只有activity名称，无规则
                activities[parts[0]] = ""
        return activities
    
    def build_activity_rule(self, activities: Dict[str, str]) -> str:
        """将活动字典构建回activityRule字符串"""
        rules = []
        for activity, rule in activities.items():
            if rule:
                rules.append(f"{activity}:{rule}")
            else:
                rules.append(activity)
        return ','.join(rules)
    
    def add_activity_rule(self, package_name: str, activity_name: str, rule: str) -> bool:
        """添加Activity规则"""
        package = self.find_package(package_name)
        if package is None:
            print(f"警告: 包 {package_name} 不存在，无法添加Activity规则")
            return False
        
        current_rule = package.get('activityRule', '')
        activities = self.parse_activity_rule(current_rule)
        
        # 添加新的Activity规则
        activities[activity_name] = rule
        
        # 更新package的activityRule属性
        new_rule = self.build_activity_rule(activities)
        package.set('activityRule', new_rule)
        
        print(f"成功添加Activity规则: {activity_name}:{rule}")
        return True
    
    def modify_activity_rule(self, package_name: str, activity_name: str, new_rule: str) -> bool:
        """修改Activity规则"""
        package = self.find_package(package_name)
        if package is None:
            print(f"警告: 包 {package_name} 不存在，无法修改Activity规则")
            return False
        
        current_rule = package.get('activityRule', '')
        activities = self.parse_activity_rule(current_rule)
        
        if activity_name not in activities:
            print(f"警告: Activity {activity_name} 在包 {package_name} 中不存在")
            return False
        
        # 修改Activity规则
        activities[activity_name] = new_rule
        
        # 更新package的activityRule属性
        new_rule_str = self.build_activity_rule(activities)
        package.set('activityRule', new_rule_str)
        
        print(f"成功修改Activity规则: {activity_name}:{new_rule}")
        return True
    
    def delete_activity_rule(self, package_name: str, activity_name: str) -> bool:
        """删除Activity规则"""
        package = self.find_package(package_name)
        if package is None:
            print(f"警告: 包 {package_name} 不存在，无法删除Activity规则")
            return False
        
        current_rule = package.get('activityRule', '')
        activities = self.parse_activity_rule(current_rule)
        
        if activity_name not in activities:
            print(f"警告: Activity {activity_name} 在包 {package_name} 中不存在")
            return False
        
        # 删除Activity规则
        del activities[activity_name]
        
        # 更新package的activityRule属性
        if activities:
            new_rule = self.build_activity_rule(activities)
            package.set('activityRule', new_rule)
        else:
            # 如果没有activity规则了，移除activityRule属性
            if 'activityRule' in package.attrib:
                del package.attrib['activityRule']
        
        print(f"成功删除Activity规则: {activity_name}")
        return True
    
    def update_package_attribute(self, package_name: str, attribute: str, value: str) -> bool:
        """更新包属性"""
        package = self.find_package(package_name)
        if package is None:
            print(f"警告: 包 {package_name} 不存在，无法更新属性")
            return False
        
        if value is None or value == "":
            # 删除属性
            if attribute in package.attrib:
                del package.attrib[attribute]
                print(f"成功删除包属性: {attribute}")
        else:
            # 设置属性
            package.set(attribute, value)
            print(f"成功更新包属性: {attribute}={value}")
        
        return True
    
    def process_operations(self, operations: List[str], package_name: str) -> int:
        """处理批量操作"""
        success_count = 0
        
        for operation in operations:
            operation = operation.strip()
            if not operation:
                continue
            
            try:
                if operation.startswith('ADD:'):
                    parts = operation[4:].split(':', 1)
                    if len(parts) >= 2:
                        activity_name, rule = parts[0], parts[1]
                        if self.add_activity_rule(package_name, activity_name, rule):
                            success_count += 1
                    else:
                        print(f"错误: ADD操作格式不正确: {operation}")
                
                elif operation.startswith('MODIFY:'):
                    parts = operation[7:].split(':', 1)
                    if len(parts) >= 2:
                        activity_name, rule = parts[0], parts[1]
                        if self.modify_activity_rule(package_name, activity_name, rule):
                            success_count += 1
                    else:
                        print(f"错误: MODIFY操作格式不正确: {operation}")
                
                elif operation.startswith('DELETE:'):
                    activity_name = operation[7:]
                    if self.delete_activity_rule(package_name, activity_name):
                        success_count += 1
                
                else:
                    print(f"错误: 未知操作类型: {operation}")
            
            except Exception as e:
                print(f"处理操作 {operation} 时出错: {e}")
        
        return success_count
    
    def save_xml(self):
        """保存XML文件，保持格式化"""
        # 使用minidom进行格式化
        rough_string = ET.tostring(self.root, 'unicode')
        reparsed = minidom.parseString(rough_string)
        
        # 获取格式化的XML字符串
        formatted_xml = reparsed.toprettyxml(indent="    ")
        
        # 移除多余的空行
        lines = [line for line in formatted_xml.split('\n') if line.strip()]
        formatted_xml = '\n'.join(lines)
        
        # 写入文件
        with open(self.xml_path, 'w', encoding='utf-8') as f:
            f.write(formatted_xml)
        
        print(f"XML文件已保存: {self.xml_path}")

def main():
    parser = argparse.ArgumentParser(description='增量更新小白条规则')
    parser.add_argument('--xml-path', required=True, help='XML规则文件路径')
    parser.add_argument('--package-name', required=True, help='包名')
    parser.add_argument('--operations', required=True, help='操作列表（用换行符分隔）')
    parser.add_argument('--enable', help='包启用状态 (true/false)')
    parser.add_argument('--disable-version-code', help='禁用版本代码')
    
    args = parser.parse_args()
    
    try:
        updater = IncrementalRuleUpdater(args.xml_path)
        
        # 处理Activity操作
        operations = args.operations.split('\n')
        success_count = updater.process_operations(operations, args.package_name)
        
        # 更新包属性
        if args.enable and args.enable != "不修改":
            enable_value = "true" if args.enable == "启用 (true)" else "false"
            updater.update_package_attribute(args.package_name, 'enable', enable_value)
        
        if args.disable_version_code:
            updater.update_package_attribute(args.package_name, 'disableVersionCode', args.disable_version_code)
        
        # 保存文件
        updater.save_xml()
        
        print(f"\n处理完成！成功执行 {success_count}/{len([op for op in operations if op.strip()])} 个操作")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()