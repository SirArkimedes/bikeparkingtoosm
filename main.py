# importing os module for environment variables
import os
# importing necessary functions from dotenv library
from dotenv import load_dotenv 
import osmapi

# loading variables from .env file
load_dotenv() 
 
# accessing and printing value
osm_client_id = os.getenv("OSM_CLIENT_ID")
osm_client_secret = os.getenv("OSM_CLIENT_SECRET")

api = osmapi.OsmApi()
print(api.NodeGet(123))
