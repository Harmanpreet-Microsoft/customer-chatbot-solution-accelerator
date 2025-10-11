#!/usr/bin/env python3
"""
Simple test to check if Cosmos DB and ProductPlugin work independently
"""
import asyncio
import os
from app.cosmos_service import get_cosmos_service
from app.plugins.product_plugin import ProductPlugin

async def test_cosmos_and_plugin():
    """Test Cosmos DB and ProductPlugin independently"""
    print("🧪 Testing Cosmos DB and ProductPlugin...")
    
    try:
        # Test Cosmos DB directly
        print("\n1️⃣ Testing Cosmos DB directly...")
        cosmos_service = get_cosmos_service()
        products = await cosmos_service.get_products()
        print(f"✅ Cosmos DB: Found {len(products)} products")
        
        if products:
            first_product = products[0]
            print(f"   First product: {first_product.title} - ${first_product.price}")
            
            # Test getting product by ID
            product_by_id = await cosmos_service.get_product_by_sku(first_product.id)
            if product_by_id:
                print(f"✅ Product lookup by ID works: {product_by_id.title}")
            else:
                print("❌ Product lookup by ID failed")
        
        # Test ProductPlugin directly
        print("\n2️⃣ Testing ProductPlugin directly...")
        plugin = ProductPlugin()
        
        # Test search function
        search_result = plugin.search("paint", limit=3)
        print(f"✅ ProductPlugin search result: {len(search_result)} chars")
        print(f"   Result preview: {search_result[:100]}...")
        
        # Test get_by_category function
        category_result = plugin.get_by_category("Paint Shades", limit=3)
        print(f"✅ ProductPlugin category result: {len(category_result)} chars")
        print(f"   Result preview: {category_result[:100]}...")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cosmos_and_plugin())
