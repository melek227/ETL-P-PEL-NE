-- Sample ERP data population script

-- Insert sample products
INSERT INTO erp.products (product_id, product_name, product_category, product_subcategory, brand, supplier_id, cost_price, list_price, weight, dimensions, product_status, created_date, updated_date) VALUES
(101, 'Laptop Pro X1', 'Electronics', 'Computers', 'TechBrand', 'SUPP001', 800.00, 999.99, 2.5, '35x25x2 cm', 'Active', '2023-01-01', '2024-01-01'),
(102, 'Smartphone Y2', 'Electronics', 'Mobile', 'PhoneCorp', 'SUPP002', 600.00, 799.99, 0.2, '15x7x1 cm', 'Active', '2023-02-01', '2024-01-01'),
(103, 'Headphones Z3', 'Electronics', 'Audio', 'SoundTech', 'SUPP003', 50.00, 79.99, 0.3, '20x18x8 cm', 'Active', '2023-03-01', '2024-01-01'),
(104, 'Tablet Mini', 'Electronics', 'Tablets', 'TechBrand', 'SUPP001', 300.00, 399.99, 0.5, '25x18x1 cm', 'Active', '2023-04-01', '2024-01-01'),
(105, 'Smart Watch', 'Electronics', 'Wearables', 'WearTech', 'SUPP004', 150.00, 249.99, 0.1, '4x4x1 cm', 'Active', '2023-05-01', '2024-01-01');

-- Insert sample inventory data
INSERT INTO erp.inventory (inventory_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, reorder_point, max_stock_level, last_updated) VALUES
(1, 101, 'WH001', 50, 5, 20, 100, CURRENT_TIMESTAMP),
(2, 102, 'WH001', 75, 10, 25, 150, CURRENT_TIMESTAMP),
(3, 103, 'WH001', 100, 0, 30, 200, CURRENT_TIMESTAMP),
(4, 104, 'WH001', 25, 3, 15, 75, CURRENT_TIMESTAMP),
(5, 105, 'WH001', 40, 2, 20, 100, CURRENT_TIMESTAMP),
(6, 101, 'WH002', 30, 2, 15, 75, CURRENT_TIMESTAMP),
(7, 102, 'WH002', 45, 5, 20, 100, CURRENT_TIMESTAMP),
(8, 103, 'WH002', 60, 0, 25, 150, CURRENT_TIMESTAMP);

COMMIT;