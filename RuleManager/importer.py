import json

from utils import *
from rule import*

def importFromOS33(path:str):
    with open(path, "r",encoding="utf-8") as f:
        data=json.load(f)
    return Rule.fromData("33", data)
def importFromOS30(path:str):
    with open(path, "r",encoding="utf-8") as f:
        data=json.load(f)
    return Rule.fromData("30", data)
def importFromOS22(path:str):
    data=xml_to_dict(path)
    return Rule.fromData("22", data)

# print(importFromOS33("../backup/backup_251104.json").toData("22"))
# print(importFromOS30("../backup/backup_250912.json").toData("22"))
# print(importFromOS22(r"C:\Users\93322\Downloads\immerse_rules.xml").toData("33"))
# print(importFromOS33("../backup/backup_251104.json").toData("dict"))
print(importFromOS30("../module/immerse_rules.json").updateFromRule(importFromOS33("../backup/backup_251104.json")).toData("33"))