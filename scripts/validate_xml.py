#!/usr/bin/env python3
"""
Validate an XML file against an XSD using xmlschema.
Usage: python scripts/validate_xml.py --xsd module/immerse_rules.xsd --xml module/immerse_rules.xml
Defaults: xsd=module/immerse_rules.xsd, xml=module/immerse_rules.xml
"""
import sys
from pathlib import Path
import argparse

try:
    import xmlschema
except Exception:
    print('Missing xmlschema module. Please install with: pip install xmlschema')
    sys.exit(2)

parser = argparse.ArgumentParser()
parser.add_argument('--xsd', default='module/immerse_rules.xsd')
parser.add_argument('--xml', default='module/immerse_rules.xml')
args = parser.parse_args()

xsd = Path(args.xsd)
xml = Path(args.xml)

if not xsd.exists():
    print(f'XSD schema file not found: {xsd}')
    sys.exit(1)
if not xml.exists():
    print(f'XML file not found: {xml}')
    sys.exit(1)

try:
    schema = xmlschema.XMLSchema(str(xsd))
    schema.validate(str(xml))
    print('XML validated against XSD')
    sys.exit(0)
except Exception as e:
    print('XML validation failed:', e)
    sys.exit(1)

