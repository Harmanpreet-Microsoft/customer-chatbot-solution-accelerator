"""
Comprehensive tests for cosmos_service.py using mocking, fixtures,
and negative testing.
These tests achieve high coverage without requiring live Azure infrastructure.
"""
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the src/api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api'))

from app.cosmos_service import (CosmosDatabaseService,  # noqa: E402
                                _prepare_query_parameters)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_cosmos_client():
    """Mock CosmosClient for all tests"""
    with patch('app.cosmos_service.CosmosClient') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock database and containers
        mock_db = MagicMock()
        mock_instance.get_database_client.return_value = mock_db
        mock_instance.create_database_if_not_exists.return_value = mock_db
        
        # Mock containers
        mock_products = MagicMock()
        mock_users = MagicMock()
        mock_chat = MagicMock()
        mock_cart = MagicMock()
        mock_transactions = MagicMock()
        
        mock_db.create_container_if_not_exists.side_effect = [
            mock_products, mock_users, mock_chat, mock_cart, mock_transactions
        ]
        
        yield {
            'client': mock_instance,
            'database': mock_db,
            'products': mock_products,
            'users': mock_users,
            'chat': mock_chat,
            'cart': mock_cart,
            'transactions': mock_transactions
        }


@pytest.fixture
def mock_settings():
    """Mock settings for Cosmos DB configuration"""
    with patch('app.cosmos_service.settings') as mock_settings:
        mock_settings.cosmos_db_endpoint = "https://test-cosmos.documents.azure.com:443/"
        mock_settings.cosmos_db_database_name = "test-db"
        mock_settings.cosmos_db_containers = {
            "products": "products",
            "users": "users",
            "chat_sessions": "chat_sessions",
            "carts": "carts",
            "transactions": "transactions"
        }
        mock_settings.azure_client_id = "test-client-id"
        mock_settings.azure_client_secret = "test-secret"
        mock_settings.azure_tenant_id = "test-tenant-id"
        yield mock_settings


@pytest.fixture
def sample_product_dict():
    """Sample product data as dictionary"""
    return {
        "id": "prod-123",
        "title": "Test Product",
        "price": 99.99,
        "original_price": 129.99,
        "rating": 4.5,
        "review_count": 100,
        "image": "https://example.com/image.jpg",
        "category": "Electronics",
        "in_stock": True,
        "description": "A great test product",
        "tags": ["test", "electronics"],
        "specifications": {"color": "blue"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z"
    }


@pytest.fixture
def cosmos_service(mock_cosmos_client, mock_settings):
    """Initialized CosmosDatabaseService with mocked dependencies"""
    with patch('app.cosmos_service.ClientSecretCredential') as mock_cred:
        mock_cred.return_value = MagicMock()
        service = CosmosDatabaseService()
        service.products_container = mock_cosmos_client['products']
        service.users_container = mock_cosmos_client['users']
        service.chat_container = mock_cosmos_client['chat']
        service.cart_container = mock_cosmos_client['cart']
        service.transactions_container = mock_cosmos_client['transactions']
        return service



# ============================================================================
# Test Helper Functions
# ============================================================================

def test_prepare_query_parameters():
    """Test query parameter preparation helper function"""
    params = [
        {"name": "@category", "value": "electronics"},
        {"name": "@min_price", "value": 10.0},
        {"name": "@max_price", "value": 100.0}
    ]
    
    result = _prepare_query_parameters(params)
    
    assert len(result) == 3
    assert result[0] == {"name": "@category", "value": "electronics"}
    assert result[1] == {"name": "@min_price", "value": 10.0}
    assert result[2] == {"name": "@max_price", "value": 100.0}


def test_prepare_query_parameters_empty():
    """Test query parameter preparation with empty list"""
    result = _prepare_query_parameters([])
    assert result == []


def test_prepare_query_parameters_none():
    """Test query parameter preparation with None value"""
    params = [{"name": "@value", "value": None}]
    result = _prepare_query_parameters(params)
    assert result[0]["value"] is None


# ============================================================================
# Test Initialization and Authentication
# ============================================================================

def test_cosmos_init_with_client_secret(mock_cosmos_client, mock_settings):
    """Test initialization with ClientSecretCredential"""
    with patch('app.cosmos_service.ClientSecretCredential') as mock_cred:
        mock_cred.return_value = MagicMock()
        service = CosmosDatabaseService()
        
        assert service.client is not None
        mock_cred.assert_called_once_with(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret"
        )


def test_cosmos_init_with_default_credential(mock_cosmos_client, mock_settings):
    """Test initialization with DefaultAzureCredential"""
    # Remove client credentials to trigger DefaultAzureCredential
    mock_settings.azure_client_id = None
    mock_settings.azure_client_secret = None
    mock_settings.azure_tenant_id = None
    
    with patch('app.cosmos_service.DefaultAzureCredential') as mock_default_cred:
        mock_default_cred.return_value = MagicMock()
        service = CosmosDatabaseService()
        
        assert service.client is not None
        mock_default_cred.assert_called_once()


def test_cosmos_init_missing_endpoint(mock_cosmos_client, mock_settings):
    """Negative test: Missing Cosmos DB endpoint"""
    mock_settings.cosmos_db_endpoint = None
    
    with pytest.raises(Exception, match="Cosmos DB endpoint is required"):
        CosmosDatabaseService()


def test_cosmos_init_rbac_permission_error(mock_cosmos_client, mock_settings):
    """Negative test: RBAC permission error"""
    with patch('app.cosmos_service.ClientSecretCredential') as mock_cred:
        mock_cred.side_effect = Exception("RBAC permissions denied")
        
        with pytest.raises(Exception, match="RBAC Permission Error"):
            CosmosDatabaseService()


def test_cosmos_init_local_auth_disabled_error(mock_settings):
    """Negative test: Local authorization disabled"""
    with patch('app.cosmos_service.ClientSecretCredential') as mock_cred:
        mock_cred.side_effect = Exception("Local Authorization is disabled")
        
        with pytest.raises(Exception, match="Authentication Error"):
            CosmosDatabaseService()


def test_cosmos_init_generic_auth_error(mock_settings):
    """Negative test: Generic authentication error"""
    with patch('app.cosmos_service.ClientSecretCredential') as mock_cred:
        mock_cred.side_effect = Exception("Unknown authentication error")
        
        with pytest.raises(Exception, match="Cannot authenticate to Cosmos DB"):
            CosmosDatabaseService()


# ============================================================================
# Test Serialization/Deserialization
# ============================================================================

class TestCosmosDatabaseServiceMethods:
    """Test individual methods of CosmosDatabaseService"""

    def test_serialize_datetime_fields(self):
        """Test datetime serialization for Cosmos DB"""
        # Mock the service without initialization
        service = Mock(spec=CosmosDatabaseService)
        method = CosmosDatabaseService._serialize_datetime_fields
        service._serialize_datetime_fields = method.__get__(service)
        
        # Test data with datetime
        test_datetime = datetime(2023, 12, 17, 10, 30, 45)
        data = {
            "id": "test-123",
            "name": "Test Product",
            "created_at": test_datetime,
            "updated_at": test_datetime,
            "price": 99.99
        }
        
        result = service._serialize_datetime_fields(data)
        
        assert result["id"] == "test-123"
        assert result["name"] == "Test Product" 
        assert result["price"] == 99.99
        assert result["created_at"] == "2023-12-17T10:30:45Z"
        assert result["updated_at"] == "2023-12-17T10:30:45Z"

    def test_serialize_datetime_fields_with_timezone(self):
        """Test datetime serialization with timezone info"""
        service = Mock(spec=CosmosDatabaseService)
        service._serialize_datetime_fields = CosmosDatabaseService._serialize_datetime_fields.__get__(service)
        
        # Test with timezone-aware datetime
        test_datetime = datetime(2023, 12, 17, 10, 30, 45, tzinfo=timezone.utc)
        data = {"created_at": test_datetime}
        
        result = service._serialize_datetime_fields(data)
        
        assert result["created_at"] == "2023-12-17T10:30:45+00:00"

    def test_deserialize_datetime_fields(self):
        """Test datetime deserialization from Cosmos DB"""
        service = Mock(spec=CosmosDatabaseService)
        service._deserialize_datetime_fields = CosmosDatabaseService._deserialize_datetime_fields.__get__(service)
        
        # Test data with ISO string datetimes
        data = {
            "id": "test-123",
            "name": "Test Product",
            "created_at": "2023-12-17T10:30:45Z",
            "updated_at": "2023-12-17T10:30:45+00:00",
            "price": 99.99,
            "last_login": "2023-12-17T15:20:10Z"
        }
        
        result = service._deserialize_datetime_fields(data)
        
        assert result["id"] == "test-123"
        assert result["name"] == "Test Product"
        assert result["price"] == 99.99
        assert isinstance(result["created_at"], datetime)
        assert isinstance(result["updated_at"], datetime)
        assert isinstance(result["last_login"], datetime)

    def test_deserialize_datetime_fields_no_datetime(self):
        """Test deserialization with no datetime fields"""
        service = Mock(spec=CosmosDatabaseService)
        service._deserialize_datetime_fields = CosmosDatabaseService._deserialize_datetime_fields.__get__(service)
        
        data = {"id": "test-123", "name": "Test Product", "price": 99.99}
        
        result = service._deserialize_datetime_fields(data)
        
        assert result == data

    def test_deserialize_datetime_fields_invalid_format(self):
        """Test deserialization with invalid datetime format"""
        service = Mock(spec=CosmosDatabaseService)
        service._deserialize_datetime_fields = CosmosDatabaseService._deserialize_datetime_fields.__get__(service)
        
        data = {"created_at": "invalid-date-format"}
        
        # This should raise ValueError for invalid format
        with pytest.raises(ValueError):
            service._deserialize_datetime_fields(data)


@patch('app.cosmos_service.settings')
@patch('app.cosmos_service.CosmosClient')
@patch('app.cosmos_service.DefaultAzureCredential')
def test_cosmos_service_initialization_success(mock_credential, mock_client, mock_settings):
    """Test successful Cosmos DB service initialization"""
    # Mock settings
    mock_settings.cosmos_db_endpoint = "https://test-cosmos.documents.azure.com:443/"
    mock_settings.cosmos_db_database_name = "test-db"
    mock_settings.cosmos_db_containers = {
        "products": "products",
        "users": "users", 
        "chat_sessions": "chat_sessions",
        "carts": "carts",
        "transactions": "transactions"
    }
    mock_settings.azure_client_id = None
    mock_settings.azure_client_secret = None
    mock_settings.azure_tenant_id = None
    
    # Mock credential and client
    mock_cred_instance = Mock()
    mock_credential.return_value = mock_cred_instance
    
    mock_client_instance = Mock()
    mock_client.return_value = mock_client_instance
    
    mock_database = Mock()
    mock_client_instance.get_database_client.return_value = mock_database
    
    # Mock container creation
    mock_container = Mock()
    mock_database.create_container_if_not_exists.return_value = mock_container
    
    # Mock create_database_if_not_exists to return the same mock_database
    mock_client_instance.create_database_if_not_exists.return_value = mock_database
    
    # Initialize service
    service = CosmosDatabaseService()
    
    # Verify initialization
    assert service.client == mock_client_instance
    # The database is set by create_database_if_not_exists in _initialize_containers
    assert service.database == mock_database
    mock_client.assert_called_once_with(
        "https://test-cosmos.documents.azure.com:443/", 
        credential=mock_cred_instance
    )


@patch('app.cosmos_service.settings')
def test_cosmos_service_initialization_no_endpoint(mock_settings):
    """Test Cosmos DB service initialization with missing endpoint"""
    mock_settings.cosmos_db_endpoint = None
    
    with pytest.raises(Exception) as exc_info:
        CosmosDatabaseService()
    
    assert "Cosmos DB endpoint is required" in str(exc_info.value)


@patch('app.cosmos_service.settings')
@patch('app.cosmos_service.CosmosClient')
@patch('app.cosmos_service.DefaultAzureCredential')
def test_cosmos_service_initialization_auth_failure(mock_credential, mock_client, mock_settings):
    """Test Cosmos DB service initialization with authentication failure"""
    # Mock settings
    mock_settings.cosmos_db_endpoint = "https://test-cosmos.documents.azure.com:443/"
    mock_settings.azure_client_id = None
    mock_settings.azure_client_secret = None
    mock_settings.azure_tenant_id = None
    
    # Mock authentication failure
    mock_client.side_effect = Exception("Authentication failed")
    
    with pytest.raises(Exception) as exc_info:
        CosmosDatabaseService()
    
    assert "Cannot authenticate to Cosmos DB" in str(exc_info.value)


def test_cosmos_service_datetime_serialization_edge_cases():
    """Test edge cases in datetime serialization"""
    service = Mock(spec=CosmosDatabaseService)
    method = CosmosDatabaseService._serialize_datetime_fields
    service._serialize_datetime_fields = method.__get__(service)
    
    # Test with None values
    data = {"created_at": None, "name": "Test"}
    result = service._serialize_datetime_fields(data)
    assert result["created_at"] is None
    assert result["name"] == "Test"
    
    # Test with nested dict (should not affect nested values)
    nested_data = {
        "created_at": datetime(2023, 12, 17),
        "metadata": {"updated_at": datetime(2023, 12, 18)}
    }
    result = service._serialize_datetime_fields(nested_data)
    assert "Z" in result["created_at"]
    # Nested datetime should remain unchanged
    assert isinstance(result["metadata"]["updated_at"], datetime)


# ============================================================================
# Test Product Operations with Mocking
# ============================================================================

@pytest.mark.asyncio
async def test_get_products_no_filters(cosmos_service, sample_product_dict):
    """Test get_products without filters"""
    cosmos_service.products_container.query_items.return_value = [
        sample_product_dict
    ]
    
    products = await cosmos_service.get_products()
    
    assert len(products) == 1
    assert products[0].id == "prod-123"
    assert products[0].title == "Test Product"


@pytest.mark.asyncio
async def test_get_products_with_category_filter(cosmos_service,
                                                  sample_product_dict):
    """Test get_products with category filter"""
    cosmos_service.products_container.query_items.return_value = [
        sample_product_dict
    ]
    
    products = await cosmos_service.get_products({"category": "Electronics"})
    
    assert len(products) == 1
    cosmos_service.products_container.query_items.assert_called_once()


@pytest.mark.asyncio
async def test_get_products_with_all_filters(cosmos_service,
                                              sample_product_dict):
    """Test get_products with multiple filters combined"""
    cosmos_service.products_container.query_items.return_value = [
        sample_product_dict
    ]
    
    products = await cosmos_service.get_products({
        "category": "Electronics",
        "min_price": 50.0,
        "max_price": 150.0,
        "min_rating": 4.0,
        "in_stock_only": True,
        "query": "test",
        "sort_by": "price",
        "sort_order": "desc"
    })
    
    assert len(products) == 1


@pytest.mark.asyncio
async def test_get_products_error_handling(cosmos_service):
    """Negative test: get_products error handling"""
    error_msg = "Database connection error"
    cosmos_service.products_container.query_items.side_effect = Exception(
        error_msg
    )
    
    with pytest.raises(Exception, match=error_msg):
        await cosmos_service.get_products()


@pytest.mark.asyncio
async def test_get_product_found(cosmos_service, sample_product_dict):
    """Test get_product successfully finds a product"""
    cosmos_service.products_container.query_items.return_value = [
        sample_product_dict
    ]
    
    product = await cosmos_service.get_product("prod-123")
    
    assert product is not None
    assert product.id == "prod-123"
    assert product.title == "Test Product"


@pytest.mark.asyncio
async def test_get_product_not_found(cosmos_service):
    """Negative test: get_product returns None when not found"""
    cosmos_service.products_container.query_items.return_value = []
    
    product = await cosmos_service.get_product("non-existent")
    
    assert product is None


@pytest.mark.asyncio
async def test_get_product_by_sku_found(cosmos_service, sample_product_dict):
    """Test get_product_by_sku successfully finds product"""
    cosmos_service.products_container.query_items.return_value = [
        sample_product_dict
    ]
    
    product = await cosmos_service.get_product_by_sku("SKU-123")
    
    assert product is not None
    assert product.id == "prod-123"


@pytest.mark.asyncio
async def test_get_product_by_sku_error(cosmos_service):
    """Negative test: get_product_by_sku handles errors gracefully"""
    cosmos_service.products_container.query_items.side_effect = Exception(
        "Query error"
    )
    
    product = await cosmos_service.get_product_by_sku("SKU-123")
    
    assert product is None  # Should return None on error


@pytest.mark.asyncio
async def test_search_products_basic(cosmos_service, sample_product_dict):
    """Test basic search_products"""
    cosmos_service.products_container.query_items.return_value = [
        sample_product_dict
    ] * 5
    
    products = await cosmos_service.search_products("test", limit=3)
    
    assert len(products) == 3


@pytest.mark.asyncio
async def test_search_products_hybrid_fallback(cosmos_service,
                                                sample_product_dict):
    """Test search_products_hybrid falls back to enhanced search"""
    # Mock AI Search to fail
    with patch.dict('sys.modules', {
        'services.search': MagicMock(side_effect=ImportError())
    }):
        cosmos_service.products_container.query_items.return_value = [
            sample_product_dict
        ]
        
        products = await cosmos_service.search_products_hybrid("test query")
        
        # Should fall back and still return results
        assert isinstance(products, list)


@pytest.mark.asyncio
async def test_search_products_ai_search_error(cosmos_service):
    """Negative test: search_products_ai_search error handling"""
    with patch.dict('sys.modules', {
        'services.search': MagicMock(side_effect=Exception("AI error"))
    }):
        products = await cosmos_service.search_products_ai_search("test")
        
        assert products == []  # Should return empty list on error


@pytest.mark.asyncio
async def test_get_products_by_category(cosmos_service, sample_product_dict):
    """Test get_products_by_category"""
    cosmos_service.products_container.query_items.return_value = [
        sample_product_dict
    ] * 15
    
    products = await cosmos_service.get_products_by_category(
        "Electronics", limit=10
    )
    
    assert len(products) == 10


# ============================================================================
# Test Order Operations with Mocking
# ============================================================================

@pytest.mark.asyncio
async def test_get_order_by_id_found(cosmos_service):
    """Test get_order_by_id successfully finds order"""
    order_dict = {
        "id": "order-123",
        "user_id": "user-1",
        "items": [],
        "total": 100.0
    }
    cosmos_service.transactions_container.query_items.return_value = [
        order_dict
    ]
    
    order = await cosmos_service.get_order_by_id("order-123")
    
    assert order is not None
    assert order["id"] == "order-123"


@pytest.mark.asyncio
async def test_get_order_by_id_not_found(cosmos_service):
    """Negative test: get_order_by_id returns None when not found"""
    cosmos_service.transactions_container.query_items.return_value = []
    
    order = await cosmos_service.get_order_by_id("non-existent")
    
    assert order is None


@pytest.mark.asyncio
async def test_get_order_by_id_error(cosmos_service):
    """Negative test: get_order_by_id error handling"""
    cosmos_service.transactions_container.query_items.side_effect = Exception(
        "Query failed"
    )
    
    order = await cosmos_service.get_order_by_id("order-123")
    
    assert order is None  # Should return None on error


@pytest.mark.asyncio
async def test_get_orders_by_customer(cosmos_service):
    """Test get_orders_by_customer"""
    orders = [{"id": f"order-{i}", "user_id": "user-1"} for i in range(5)]
    cosmos_service.transactions_container.query_items.return_value = orders
    
    result = await cosmos_service.get_orders_by_customer("user-1", limit=3)
    
    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_orders_by_customer_error(cosmos_service):
    """Negative test: get_orders_by_customer error handling"""
    cosmos_service.transactions_container.query_items.side_effect = Exception(
        "Query error"
    )
    
    result = await cosmos_service.get_orders_by_customer("user-1")
    
    assert result == []  # Should return empty list on error