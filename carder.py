## interfaces with weaviate


import weaviate
import weaviate.classes as wvc
import os
import random
from dataclasses import asdict
from functools import wraps
import dotenv
import json
dotenv.load_dotenv()
client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    headers={
        "X-OpenAI-Api-Key": os.environ["OPENAI_APIKEY"]  # Replace with your inference API key
    }
)
if not client.collections.exists("Question"):
    print("MAKING NEW COLLECTION!!!")
    client.collections.create(
        name="Question", 
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),  # If set to "none" you must always provide vectors yourself. Could be any other "text2vec-*" also.
        generative_config=wvc.Configure.Generative.openai(),
        
    )
question = client.collections.get("Question")
database = question.query.fetch_objects(limit=20_000)

with open("./public/subcategories.json", mode="r", encoding="utf-8") as f:
    subcategories = json.load(f) ###AHHH THE MEMORY REQUIREMENTS GO CRAZYYYYYY
with open("./card_adder/filtered.json", mode="r", encoding="utf-8") as f:
    filtered = json.load(f)
        
def get_keys_of(cls):
    return [a for a in dir(cls) if not a.startswith('_') and not callable(getattr(cls, a))]
def to_dict(obj):
    '''
    converts arbritary _object to dictionary
    '''
    # data = {}
    # def _recursive(obj):
    #     keys = get_keys_of(obj)
    #     print(keys)
    #     for key in keys:
    #         data[key] = obj.__dict__[key]
    #         if hasattr(data[key], "__dict__"):
    #             _recursive(data[key])
    # _recursive(obj)
    # # print(data)
    # return data
    return asdict(obj=obj)
            
def subcategory(func):
    @wraps(func)
    def wrapper(*args, subcategories=None, **kwargs):
        ## assumes that the function it is wrapping returns either an array of weaviate cards or a weaviate card
        result = func(*args, **kwargs)
        if subcategories is None:
            return result
        def _filter_by_subcategories(card):
            subcata = card["extra"]["subcategory_id"]
            if subcata not in subcategories:
                return False
            return True
        if type(result) == list:
            return list(filter(_filter_by_subcategories, result))
        else:
            raise RuntimeError("Subcategory decorator can only be used with a function that returns a list of cards")
    return wrapper
def extra_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ## assumes that the function it is wrapping returns either an array of weaviate cards or a weaviate card
        result = func(*args, **kwargs)
        def _get_extra_info(card): 
            properties = card['properties']
            nid = properties['nid']
            if nid[0] == "n":
                ## this means the card was sourced from n ocard.
                id = nid[1:]
                
                # print(id)
                card_match = list(filter(lambda x: str(x["id"]) == id, filtered))
                if len(card_match) == 0:
                    print(f"No match found for {str(id)}")
                    return result
                card_match = card_match[0].copy()
                print(card_match)
                del card_match["text"]
                del card_match["answer"]
                del card_match["formatted_answer"]
                del card_match["formatted_text"]
               
                card["extra"] = card_match
                
                # print(result.__dict__)
                # print(card_match)
                return card
        if type(result) == list:
            return list(map(_get_extra_info, result))
        else:
            return _get_extra_info(result)
    return wrapper
def _get_near_card(word, limit):
    q = client.collections.get("Question")
    limit = int(limit)
    # if (limit > 50):
    #     limit = 50
    similar = q.query.near_text(query=word,limit=limit)
    results = [to_dict(obj) for obj in similar.objects]
    return results
get_near_card = extra_info(_get_near_card)
get_near_card = subcategory(get_near_card)
def get_card_by_uuid(uuid):
    return to_dict(client.collections.get("Question").query.fetch_object_by_id(uuid=uuid, include_vector=True))


def _get_random_card():
    '''
    returns a random card from weaviate
    '''
    rand = random.randint(0, len(database))
    query_result = database[rand] ## wish i could do this with weaviate but its actually rlly hard to just get a random entry without loading the entire fricking database into memory. argh.
    return to_dict(query_result)

get_random_card = extra_info(_get_random_card)