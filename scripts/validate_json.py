#!/usr/bin/env python3
"""
Validate an json file.
Usage: python scripts/validate_json.py module/immerse_rules.json
"""
import json
import sys
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="输入的json文件路径")
args = parser.parse_args()

input_file = Path(args.input_file)

if not input_file.exists():
    print(f"json文件未找到: {input_file}")
    sys.exit(1)

try:
    json.load(open(input_file))
    print("json文件校验成功")
    sys.exit(0)
except Exception as e:
    print("json文件校验失败:", e)
    sys.exit(1)
