import os
import json
import logging
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType
)
from azure.core.credentials import AzureKeyCredential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "policies")

def create_search_index():
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("Azure Search endpoint and key must be set in environment variables")
        return False
    
    try:
        credential = AzureKeyCredential(AZURE_SEARCH_KEY)
        index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)
        
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String, searchable=True),
            SearchableField(name="content", type=SearchFieldDataType.String, searchable=True),
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(
                name="keywords",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=False,
                sortable=False,
                facetable=False
            ),
        ]
        
        index = SearchIndex(name=AZURE_SEARCH_INDEX_NAME, fields=fields)
        
        result = index_client.create_or_update_index(index)
        logger.info(f"✅ Search index '{AZURE_SEARCH_INDEX_NAME}' created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create search index: {e}")
        return False

def upload_documents():
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("Azure Search endpoint and key must be set in environment variables")
        return False
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        docs_file = os.path.join(script_dir, "policy-documents.json")
        
        if not os.path.exists(docs_file):
            logger.error(f"Policy documents file not found: {docs_file}")
            return False
        
        with open(docs_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        credential = AzureKeyCredential(AZURE_SEARCH_KEY)
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX_NAME,
            credential=credential
        )
        
        result = search_client.upload_documents(documents=documents)
        logger.info(f"✅ Uploaded {len(documents)} documents to search index")
        
        for item in result:
            if not item.succeeded:
                logger.error(f"❌ Failed to upload document {item.key}: {item.error_message}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to upload documents: {e}")
        return False

def main():
    logger.info("🔍 Setting up Azure AI Search index...")
    
    if not AZURE_SEARCH_ENDPOINT:
        logger.error("❌ AZURE_SEARCH_ENDPOINT environment variable not set")
        return
    
    if not AZURE_SEARCH_KEY:
        logger.error("❌ AZURE_SEARCH_KEY environment variable not set")
        return
    
    logger.info(f"📍 Endpoint: {AZURE_SEARCH_ENDPOINT}")
    logger.info(f"📇 Index Name: {AZURE_SEARCH_INDEX_NAME}")
    
    logger.info("\n📋 Step 1: Creating search index...")
    if not create_search_index():
        logger.error("Failed to create search index")
        return
    
    logger.info("\n📤 Step 2: Uploading policy documents...")
    if not upload_documents():
        logger.error("Failed to upload documents")
        return
    
    logger.info("\n✅ Azure AI Search setup completed successfully!")
    logger.info(f"🔍 Index '{AZURE_SEARCH_INDEX_NAME}' is ready with policy documents")

if __name__ == "__main__":
    main()

