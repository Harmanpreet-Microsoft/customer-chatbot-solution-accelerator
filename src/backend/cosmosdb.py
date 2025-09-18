from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from app.config import settings

endpoint = settings.cosmos_endpoint
db_name = settings.cosmos_db
key = settings.cosmos_key
container_name = settings.cosmos_container

client = CosmosClient(endpoint, key)
db = client.get_database_client(db_name)
container = db.get_container_client(container_name)


order = {
    "id": "order-002",
    "customerid": "CUST-002",
    "productid": 3,
    "price": 24.99,
    "quantity": 2,
    "description": "5m RGB LED strip with remote"
}
container.upsert_item(order)


