
import weaviate
import weaviate
import ijson
import weaviate.classes as wvc
import os
import dotenv
from weaviate.classes.config import Configure, Property, DataType
from weaviate.util import generate_uuid5

davidlimit = 20

dotenv.load_dotenv()

    
# As of November 2023, WCS clusters are not yet compatible with the new API introduced in the v4 Python client.
# Accordingly, we show you how to connect to a local instance of Weaviate.
# Here, authentication is switched off, which is why you do not need to provide the Weaviate API key.
# client = None
def add_objects(client): 

    # Settings for displaying the import progress
    global counter
    counter = 0
    interval = 25  # print progress every this many records; should be bigger than the batch_size

 
    def add_object(obj, batch) -> None:
        global counter
        # print(obj)
        del obj['uuid']
        obj['nocard'] = True
        obj['nid'] = obj['id']  ## weaviate doesnt like id in things
        del obj['id']
        properties = obj

        # client.batch.configure(batch_size=100)  # Configure batch
        # from weaviate.util import generate_uuid5  # Generate a deterministic ID

        # data_rows = [{"title": f"Object {i+1}"} for i in range(5)]

       
        # obj_uuid = generate_uuid5(data_row)
        batch.add_object(
            properties=properties,
            uuid=generate_uuid5(properties)
        )
        global counter
        counter += 1
        if counter % interval == 0:
            print(f'Imported {counter} articles...')
       
            


    if not client.collections.exists("Question"):
        print("MAKING NEW COLLECTION!!!")
        client.collections.create(
            "Question",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(),
            # gen
        )
        
    print('JSON streaming, to avoid running out of memory on large files...')
    collection = client.collections.get("Question")  
    with collection.batch.fixed_size(batch_size=200) as batch:
        with open("./card_adder/filtered.json", "rb") as f:
            objects = ijson.items(f, '')
            for o in objects:
                for i,o2 in enumerate(o):
           
                    add_object(o2, batch)
    print(collection.batch.failed_objects)

    input("Waiting for input")
    print(f'Finished importing {counter} articles.')
    q = client.collections.get("Question")

