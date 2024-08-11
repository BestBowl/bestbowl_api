import weaviate
import weaviate
import ijson
import weaviate.classes as wvc
import os
import dotenv
import json
import ijson

dotenv.load_dotenv()

    
# As of November 2023, WCS clusters are not yet compatible with the new API introduced in the v4 Python client.
# Accordingly, we show you how to connect to a local instance of Weaviate.
# Here, authentication is switched off, which is why you do not need to provide the Weaviate API key.

client = None
def listAll():

    q = client.collections.get("Question")
    for q2 in q.iterator():
        print(q2)
