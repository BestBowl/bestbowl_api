# import filter
import json
import os
import weaviate
with open("./card_adder/filtered.json", "r", encoding="utf-8") as f:
    nocard = json.load(f)

from weaviate.embedded import EmbeddedOptions


client = None


def check_if_need_cards():

    items = [_ for _ in client.collections.get("Question").iterator()]
    questions = len(items)
    if client.collections.exists("Question") and questions != 0:
        print("Questions exist!")
        from . import total
        total.client = client
        # total.listAll()
    else:
        print("No questions in database! Adding no-card...")
        from . import import_nocard
        import_nocard.client = client
        import_nocard.add_objects(client)
