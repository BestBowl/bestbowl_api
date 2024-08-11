## interfaces with weaviate


import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import Configure, Property, DataType
import os
import random
from dataclasses import asdict
from functools import wraps
import dotenv
import json
DEBUG = True
dotenv.load_dotenv()
from weaviate.embedded import EmbeddedOptions

client = None

def init():
    if not client.collections.exists("Question"):
        print("MAKING NEW COLLECTION!!!")
        # client.collections.create(
        #     name="Question", 
        #     vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),  # If set to "none" you must always provide vectors yourself. Could be any other "text2vec-*" also.
        #     generative_config=wvc.Configure.Generative.openai(),
            
        # )
        client.collections.create(
            "Question",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(),
            # gen
        )
    question = client.collections.get("Question")

def memoize(id, computation: callable): ## i feel so smart rn..and this is so gonna screw me up when i add more questions
    pathn = f"./memoize/{id}.json"
    if not DEBUG:
        if os.path.exists(pathn):
        
            with open(pathn, mode="r", encoding='utf-8') as f:
                return json.load(f)
    with open(pathn, mode="w", encoding="utf-8") as f:
        json_obj = computation()
        # print(json_obj)
        if not DEBUG:
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
    # print(obj)

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
class StreamArray(list):
    """
    Converts a generator into a list object that can be json serialisable
    while still retaining the iterative nature of a generator.

    IE. It converts it to a list without having to exhaust the generator
    and keep it's contents in memory.
    """
    def __init__(self, generator):
        self.generator = generator
        self._len = 1

    def __iter__(self):
        self._len = 0
        for item in self.generator:
            yield item
            self._len += 1

    def __len__(self):
        """
        Json parser looks for a this method to confirm whether or not it can
        be parsed
        """
        return self._len

def reindex():
    ## reindex database
    collection = client.collections.get("Question")
    uuids = [] #
    with open('./index/UUIDs.txt', 'w') as outfile: ##writes json file incrementally as to not kill memory
        all_cards_gen = collection.iterator()
        i = 0
        for card in all_cards_gen:
            outfile.write(str(card.uuid) + "\n")
            i += 1
            catagory = str(int(card.properties['category_id']))
            with open(f'./index/UUIDs-f{catagory}.txt', "a+") as f:
                f.write(str(card.uuid) + "\n")
            print(f"Added {i} cards")





    
def extra_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ## assumes that the function it is wrapping returns either an array of weaviate cards or a weaviate card
        result = func(*args, **kwargs)
        return result ## not useful anymore, this wrapper
        def _get_extra_info(card): 
            try:
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
            except:
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
    item = client.collections.get("Question").query.fetch_object_by_id(uuid=uuid)
    assert item is not None
    return {
        "uuid": str(item.uuid),
        "properties": item.properties
    }
def _get_random_card(limit=1, query="", subcategory=None, category=None, tournament=None, question_type=None, difficulty=None):
 
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
         
            # base_filtered = filtered.copy() ## this uses the entire nocard database as search reference
            if query != "":
                base_filtered = client.collections.get("Question").query.bm25(query=query, limit=1000)
    
            else:
                base_filtered = client.collections.get("Question").query.fetch_objects(limit=1000)
            
            for propid in query_info:
                if query_info[propid] is not None:
                    base_filtered = get_subcat(propid, query_info[propid], base_filtered)
            return base_filtered
         
       
        final_filtered= memoize(name, get_filtered)
        if len(final_filtered.objects) == 0:
            return None
        print("Total Database Entries: " + str(len(final_filtered.objects)))
        rand = random.randint(0, len(final_filtered.objects)-1)
        query_result = final_filtered.objects[rand] ## wish i could do this with weaviate but its actually rlly hard to just get a random entry without loading the entire fricking database into memory. argh.
        
        
        assert query_result is not None
     
        final_query_result = get_card_by_uuid(query_result.uuid)
        # print(final_query_result)
        assert final_query_result is not None
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




def search(limit=1, query="silly", subcategory=None, category=None, tournament=None, question_type=None, difficulty=None):
 
    def __search(subcategory=None, category=None, tournament=None, question_type=None, difficulty=None):
        def filterByProperty(prop, queryInfo):
         
            def wrapper(question):
             
                if (question.properties[prop] in queryInfo):
                
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
         
            # base_filtered = filtered.copy() ## this uses the entire nocard database as search reference
           
            base_filtered = client.collections.get("Question").query.bm25(query=query, limit=1000).objects
    
            
            for propid in query_info:
                if query_info[propid] is not None:
                    base_filtered = get_subcat(propid, query_info[propid], base_filtered)
            return base_filtered
         
       
        final_filtered= memoize(name, get_filtered)
        if len(final_filtered) == 0:
            return None
        print("Total Database Entries: " + str(len(final_filtered)))
        rand = random.randint(0, len(final_filtered)-1)
        query_result = final_filtered[rand] ## wish i could do this with weaviate but its actually rlly hard to just get a random entry without loading the entire fricking database into memory. argh.
        
        
        assert query_result is not None
     
        final_query_result = get_card_by_uuid(query_result.uuid)
        # print(final_query_result)
        assert final_query_result is not None
        return final_query_result
    if limit > 1:
        result = [__search(subcategory=subcategory, category=category, tournament=tournament, question_type=question_type, difficulty=difficulty) for _ in range(limit)]
        ## filter out repeats
        new_result = []
        for card in result:
            if card not in new_result:
                new_result.append(card)
        return new_result
    return [__search(subcategory=subcategory, category=category, tournament=tournament, question_type=question_type, difficulty=difficulty)]




get_card_by_uuid = extra_info(_get_card_by_uuid)
def _get_random_card(limit=1, category=None):
 
    def __get_random_card(category=None):
        def filterByProperty(prop, queryInfo):
            def wrapper(question):
              
                if (question[prop] in queryInfo):
                
                    return True
                return False
            return wrapper

        query_info = {
            "category_id": category,

        }
        global base_filtered
       
        def get_subcat(prop, queryInfo, base_filtered):
            return list(filter(filterByProperty(prop, queryInfo), base_filtered))
            
        name = "-".join(list(map(lambda x: str(x), query_info.values())))
        print(category)
        def get_filtered():
            ## using indexed UUIDs, catagory-only search
            if (category is not None):
                print("catagory found!!!")
                r = random.randrange(0, len(category))
                random_cata = category[r]
                print("randomcata: " + str(random_cata))
                with open(f"./index/UUIDs-f{random_cata}.txt", "r") as f:
                    d = f.readlines()
                    lines = len(d)
                    chosenLine = random.randrange(0, lines)
                    uuid = d[chosenLine].replace("\n", "")
                    return uuid
            else:
                with open(f"./index/UUIDs.txt", "r") as f:
                    d = f.readlines()
                    lines = len(d)
                    chosenLine = random.randrange(0, lines)
                    uuid = d[chosenLine].replace("\n", "")
                    return uuid

       
        
        query_result = get_filtered()
   
        assert query_result is not None
       
        final_query_result = client.collections.get("Question").query.fetch_object_by_id(query_result)
        
        # print(final_query_result)
        assert final_query_result is not None
        return final_query_result
    if limit > 1:
        result = [__get_random_card(category=category) for _ in range(limit)]
        ## filter out repeats
        new_result = []
        for card in result:
            if card not in new_result:
                new_result.append(card)
        return new_result
    return [__get_random_card(category=category)]

get_random_card = _get_random_card