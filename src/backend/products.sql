CREATE TABLE dbo.Products (
  id INT IDENTITY(1,1) PRIMARY KEY,
  sku NVARCHAR(64) NOT NULL UNIQUE,
  name NVARCHAR(200) NOT NULL,
  description NVARCHAR(MAX) NULL,
  price DECIMAL(10,2) NOT NULL,
  image_url NVARCHAR(500) NULL,
  inventory INT NOT NULL DEFAULT 0
);

INSERT INTO dbo.products (sku, name, description, price, image_url, inventory) VALUES
('SKU-1001','Motion Desk','Height-adjustable desk, oak top',399.00,NULL,12),
('SKU-1002','Ergo Chair','Ergonomic mesh back chair',199.00,NULL,25),
('SKU-2001','LED Strip','5m RGB LED strip with remote',24.99,NULL,100);
