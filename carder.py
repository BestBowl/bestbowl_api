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

def memoize(id, computation: callable): ## i feel so smart rn..and this is so gonna screw me up when i add more questions
    pathn = f"./memoize/{id}.json"
  
    if os.path.exists(pathn):
    
        with open(pathn, mode="r", encoding='utf-8') as f:
            return json.load(f)
    with open(pathn, mode="w", encoding="utf-8") as f:
        json_obj = computation()
        print(json_obj)
        json.dump(json_obj, f)
        return json_obj

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
            
# def subcategory(func):
#     '''
#     DO NOT USE
#     IMPLEMENTATION FLAW
#     '''
#     @wraps(func)
#     def wrapper(*args, subcategories=None, **kwargs):
#         ## assumes that the function it is wrapping returns either an array of weaviate cards or a weaviate card
#         result = func(*args, **kwargs)
#         if subcategories is None:
#             return result
#         def _filter_by_subcategories(card):
#             subcata = card["extra"]["subcategory_id"]
#             if subcata not in subcategories:
#                 return False
#             return True
#         if type(result) == list:
#             return list(filter(_filter_by_subcategories, result))
#         else:
#             raise RuntimeError("Subcategory decorator can only be used with a function that returns a list of cards")
#     return wrapper
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
                # print(card_match)
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

def _get_card_by_uuid(uuid):
    return to_dict(client.collections.get("Question").query.fetch_object_by_id(uuid=uuid))

get_card_by_uuid = extra_info(_get_card_by_uuid)
def _get_random_card(limit=1,subcategory=None, category=None, tournament=None, question_type=None, difficulty=None):
 
    def __get_random_card(subcategory=None, category=None, tournament=None, question_type=None, difficulty=None):
        def filterByProperty(prop, queryInfo):
            def wrapper(question):
              
                if (question[prop] in queryInfo):
                
                    return True
                return False
            return wrapper

        query_info = {
            "subcategory_id": subcategory,
            "category_id": category,
            "tournament_id": tournament,
            "difficulty": difficulty,
        }
        global base_filtered
       
        def get_subcat(prop, queryInfo, base_filtered):
            return list(filter(filterByProperty(prop, queryInfo), base_filtered))
            
        name = "-".join(list(map(lambda x: str(x), query_info.values())))
        def get_filtered():
         
            base_filtered = filtered.copy()
            
            for propid in query_info:
                if query_info[propid] is not None:
                    base_filtered = get_subcat(propid, query_info[propid], base_filtered)
            return base_filtered
         
       
        final_filtered = memoize(name, get_filtered)
        if len(final_filtered) == 0:
            return None
        rand = random.randint(0, len(final_filtered)-1)

        query_result = final_filtered[rand] ## wish i could do this with weaviate but its actually rlly hard to just get a random entry without loading the entire fricking database into memory. argh.
        final_query_result = get_card_by_uuid(query_result["uuid"])
     
        return final_query_result
    if limit > 1:
        result = [__get_random_card(subcategory=subcategory, category=category, tournament=tournament, question_type=question_type, difficulty=difficulty) for _ in range(limit)]
        ## filter out repeats
        new_result = []
        for card in result:
            if card not in new_result:
                new_result.append(card)
        return new_result
    return [__get_random_card(subcategory=subcategory, category=category, tournament=tournament, question_type=question_type, difficulty=difficulty)]

get_random_card = _get_random_card