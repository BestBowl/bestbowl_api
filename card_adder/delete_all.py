## deletes everything from the entire database
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
from weaviate.embedded import EmbeddedOptions

def delete_all(client):
    confirmation = input("you sure you want this? (type 'yes'): ")
    if confirmation == 'yes':
        client.collections.delete_all()