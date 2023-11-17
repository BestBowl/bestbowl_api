import json
import os

FILENAME = "./card_adder/categories.json"

with open(FILENAME, mode="r", encoding="utf-8") as f:
    contents = json.load(f)

with open(FILENAME, mode="w", encoding="utf-8") as f:
    json.dump(contents, f, indent=4)