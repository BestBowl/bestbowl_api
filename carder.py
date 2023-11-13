## interfaces with weaviate


import weaviate
import weaviate.classes as wvc
import os
import random
import dotenv
dotenv.load_dotenv()
client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    headers={
        "X-OpenAI-Api-Key": os.environ["OPENAI_APIKEY"]  # Replace with your inference API key
    }
)
question = client.collections.get("Question")
database = [a for a in question.iterator()]

def get_near_card(word, limit):
    q = client.collections.get("Question")
    limit = int(limit)
    if (limit > 50):
        limit = 50
    similar = q.query.near_text(query=word,limit=limit)
    results = [obj for obj in similar.objects]
    return results

def get_card_by_uuid(uuid):
    return client.collections.get("Question").query.fetch_object_by_id(uuid=uuid, include_vector=True)
def get_random_card():
    '''
    returns a random card from weaviate
    '''
    rand = random.randint(0, len(database))
    query_result = database[rand] ## wish i could do this with weaviate but its actually rlly hard to just get a random entry without loading the entire fricking database into memory. argh.
    return query_result