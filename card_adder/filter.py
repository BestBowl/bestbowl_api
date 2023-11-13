import json
import os

with open("./card_adder/unfiltered.json", mode="r", encoding="utf-8") as f:
    data = json.load(f)

data = data['data']

validity_indicators = ["For 10 points", "For ten points", "FTP"]


def filterf(datum):
    message: str = datum['formatted_text']
    for indicator in validity_indicators:
        if indicator.lower() in message.lower():
            return True
    return False
new_data = list(filter(filterf, data))
    
with open("./card_adder/filtered.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=4)
    
