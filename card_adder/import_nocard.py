
import weaviate
import weaviate
import ijson
import weaviate.classes as wvc
import os
import dotenv
import json
import ijson
from weaviate.util import generate_uuid5


dotenv.load_dotenv()

    
# As of November 2023, WCS clusters are not yet compatible with the new API introduced in the v4 Python client.
# Accordingly, we show you how to connect to a local instance of Weaviate.
# Here, authentication is switched off, which is why you do not need to provide the Weaviate API key.
client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    headers={
        "X-OpenAI-Api-Key": os.environ["OPENAI_APIKEY"]  # Replace with your inference API key
    }
)

# Settings for displaying the import progress
counter = 0
interval = 20  # print progress every this many records; should be bigger than the batch_size

prefix = "n"
def add_object(obj) -> None:
    global counter
    # print(obj)
    properties = {
        'question': obj['text'],
        'answer': obj['answer'],
        'nid': prefix + str(obj['id'])
        
    }

    client.batch.configure(batch_size=100)  # Configure batch
    with client.batch as batch:
        # Add the object to the batch
        
        batch.add_object(
            properties=properties,
            collection='Question',
            uuid=generate_uuid5(properties)
            # If you Bring Your Own Vectors, add the `vector` parameter here
            # vector=obj.vector
        )

        # Calculate and display progress
        counter += 1
        if counter % interval == 0:
            print(f'Imported {counter} articles...')


if not client.collections.exists("Question"):
    print("MAKING NEW COLLECTION!!!")
    client.collections.create(
        name="Question", 
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),  # If set to "none" you must always provide vectors yourself. Could be any other "text2vec-*" also.
        generative_config=wvc.Configure.Generative.openai(),
        
    )
    
print('JSON streaming, to avoid running out of memory on large files...')
with open("./card_adder/filtered.json", "rb") as f:
    objects = ijson.items(f, '')
    for o in objects:
        for o2 in o:
            add_object(o2)


print(f'Finished importing {counter} articles.')
q = client.collections.get("Question")

