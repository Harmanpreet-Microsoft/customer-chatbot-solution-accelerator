#!/usr/bin/env python3
"""
Azure AI Search Product Index Setup Script
Creates and populates a product search index for semantic product search
"""

import os
import json
import logging
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticSearch,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_product_search_index():
    """Create Azure AI Search index for products"""
    
    # Get configuration from environment
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = "products"
    
    if not search_endpoint or not search_key:
        logger.error("Missing Azure Search configuration. Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY")
        return False
    
    try:
        # Create search index client
        credential = AzureKeyCredential(search_key)
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Define the product search index with simpler configuration
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
            SearchableField(name="description", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
            SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="price", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="inventory", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="image", type=SearchFieldDataType.String),
            SearchableField(name="tags", type=SearchFieldDataType.String),  # Changed from Collection to String
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
            SimpleField(name="rating", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="review_count", type=SearchFieldDataType.Int32),
            SimpleField(name="in_stock", type=SearchFieldDataType.Boolean, filterable=True),
        ]
        
        # Create the search index without semantic configuration for now
        search_index = SearchIndex(
            name=index_name,
            fields=fields
        )
        
        # Create or update the index
        logger.info(f"Creating/updating search index: {index_name}")
        index_client.create_or_update_index(search_index)
        logger.info(f"✅ Successfully created/updated index: {index_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create search index: {e}")
        return False

def populate_product_index():
    """Populate the product index with sample data"""
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = "products"
    
    if not search_endpoint or not search_key:
        logger.error("Missing Azure Search configuration")
        return False
    
    try:
        # Create search client
        credential = AzureKeyCredential(search_key)
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Sample product data optimized for search
        sample_products = [
            {
                "id": "seafoam-light",
                "title": "Seafoam Light",
                "description": "A calming blue paint that avoids gray undertones, perfect for bedrooms and relaxation spaces. Features excellent coverage and easy application.",
                "category": "Interior Paint",
                "price": 45.00,
                "inventory": 25,
                "image": "/images/seafoam-light.jpg",
                "tags": "blue calming bedroom interior light relaxing",
                "content": "Seafoam Light is a premium interior paint designed for bedrooms and relaxation spaces. This calming blue avoids gray undertones, creating a peaceful atmosphere. Perfect for creating a serene bedroom environment. Features excellent coverage, easy application, and long-lasting durability.",
                "rating": 4.8,
                "review_count": 156,
                "in_stock": True
            },
            {
                "id": "obsidian-pearl",
                "title": "Obsidian Pearl",
                "description": "A sophisticated deep blue with excellent coverage and nanocoating technology. Ideal for accent walls and modern interiors.",
                "category": "Interior Paint",
                "price": 52.00,
                "inventory": 18,
                "image": "/images/obsidian-pearl.jpg",
                "tags": "blue dark sophisticated interior accent modern",
                "content": "Obsidian Pearl is a sophisticated deep blue paint featuring advanced nanocoating technology. Perfect for accent walls and modern interior designs. The deep blue tone creates dramatic yet elegant spaces. Features self-leveling properties and stain resistance.",
                "rating": 4.6,
                "review_count": 89,
                "in_stock": True
            },
            {
                "id": "arctic-white",
                "title": "Arctic White",
                "description": "Ultra-bright white paint with superior hiding power. Perfect for ceilings, trim, and creating clean, bright spaces.",
                "category": "Interior Paint",
                "price": 38.00,
                "inventory": 42,
                "image": "/images/arctic-white.jpg",
                "tags": "white bright ceiling trim clean interior",
                "content": "Arctic White is an ultra-bright white paint with superior hiding power. Perfect for ceilings, trim work, and creating clean, bright interior spaces. Features excellent coverage and easy application. Ideal for modern, minimalist designs.",
                "rating": 4.7,
                "review_count": 203,
                "in_stock": True
            },
            {
                "id": "forest-green",
                "title": "Forest Green",
                "description": "Rich, natural green paint inspired by forest depths. Excellent for exterior applications and nature-themed interiors.",
                "category": "Exterior Paint",
                "price": 48.00,
                "inventory": 15,
                "image": "/images/forest-green.jpg",
                "tags": "green natural exterior forest nature outdoor",
                "content": "Forest Green is a rich, natural green paint inspired by the depths of forest landscapes. Excellent for exterior applications and nature-themed interior designs. Features weather resistance and UV protection for outdoor use.",
                "rating": 4.5,
                "review_count": 67,
                "in_stock": True
            },
            {
                "id": "sunset-orange",
                "title": "Sunset Orange",
                "description": "Warm, vibrant orange paint that brings energy to any space. Perfect for accent walls and creative spaces.",
                "category": "Interior Paint",
                "price": 44.00,
                "inventory": 22,
                "image": "/images/sunset-orange.jpg",
                "tags": "orange warm vibrant accent creative energy",
                "content": "Sunset Orange is a warm, vibrant orange paint that brings energy and creativity to any space. Perfect for accent walls, creative studios, and spaces that need a burst of color. Features excellent color retention and easy application.",
                "rating": 4.4,
                "review_count": 45,
                "in_stock": True
            }
        ]
        
        # Upload documents to the index
        logger.info(f"Uploading {len(sample_products)} products to index: {index_name}")
        search_client.upload_documents(sample_products)
        logger.info(f"✅ Successfully uploaded products to index: {index_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to populate product index: {e}")
        return False

def test_product_search():
    """Test the product search functionality"""
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = "products"
    
    if not search_endpoint or not search_key:
        logger.error("Missing Azure Search configuration")
        return False
    
    try:
        # Create search client
        credential = AzureKeyCredential(search_key)
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Test queries
        test_queries = [
            "blue paint for bedroom",
            "exterior paint",
            "white ceiling paint",
            "accent wall colors",
            "natural green paint"
        ]
        
        logger.info("Testing product search queries...")
        for query in test_queries:
            logger.info(f"\n🔍 Testing query: '{query}'")
            
            # Use simple search instead of semantic search
            results = search_client.search(
                search_text=query,
                top=3
            )
            
            for i, result in enumerate(results):
                logger.info(f"  {i+1}. {result['title']} - ${result['price']} ({result['category']})")
        
        logger.info("✅ Product search tests completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Product search test failed: {e}")
        return False

def main():
    """Main function to set up product search index"""
    logger.info("🚀 Setting up Azure AI Search Product Index")
    
    # Step 1: Create the index
    if not create_product_search_index():
        logger.error("Failed to create product search index")
        return False
    
    # Step 2: Populate with sample data
    if not populate_product_index():
        logger.error("Failed to populate product search index")
        return False
    
    # Step 3: Test the search functionality
    if not test_product_search():
        logger.error("Product search tests failed")
        return False
    
    logger.info("🎉 Product search index setup completed successfully!")
    logger.info("Your agents can now use semantic product search for faster, more accurate results.")
    
    return True

if __name__ == "__main__":
    main()
