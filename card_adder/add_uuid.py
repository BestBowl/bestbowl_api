from weaviate.util import generate_uuid5
import json
FILENAME = "./card_adder/filtered.json"

with open(FILENAME, mode="r", encoding="utf-8") as f:
    contents = json.load(f)

prefix = "n"
for c in contents:
    properties = {
        'question': c['text'],
        'answer': c['answer'],
        'nid': prefix + str(c['id'])
    }
    uuid = generate_uuid5(properties)
    c['uuid'] = uuid ## deterministic UUIDs for the win lets gooooo

with open(FILENAME, mode="w", encoding="utf-8") as f:
    json.dump(contents, f, indent=4)