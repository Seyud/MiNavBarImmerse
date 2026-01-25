import sys

from rule import *

try:
    importFromOS33("module/immerse_rules.json").toData("33")
    sys.exit(0)
except:
    sys.exit(1)