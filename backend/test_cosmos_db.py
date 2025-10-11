#!/usr/bin/env python3
"""
Test script to check what's in Cosmos DB
"""
import asyncio
from app.cosmos_service import get_cosmos_service

async def test_cosmos_db():
    """Test what's in the Cosmos DB"""
    print("🧪 Testing Cosmos DB...")
    
    try:
        service = get_cosmos_service()
        products = await service.get_products()
        
        print(f"📦 Found {len(products)} products in Cosmos DB")
        
        if products:
            print("\n📋 First 5 products:")
            for i, product in enumerate(products[:5], 1):
                print(f"{i}. {product.title} - ${product.price}")
                print(f"   ID: {product.id}")
                print(f"   Category: {product.category}")
                print(f"   In Stock: {product.in_stock}")
                print(f"   Description: {product.description[:50] if product.description else 'None'}...")
                print()
        else:
            print("❌ No products found in Cosmos DB")
            
    except Exception as e:
        print(f"❌ Error accessing Cosmos DB: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cosmos_db())
