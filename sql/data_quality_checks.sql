-- Data quality checks and validation queries

-- 1. Check for null values in critical fields
SELECT 'CRM Customers - Null customer_id' as check_name, COUNT(*) as null_count
FROM crm.customers 
WHERE customer_id IS NULL

UNION ALL

SELECT 'CRM Sales - Null sale_id' as check_name, COUNT(*) as null_count
FROM crm.sales 
WHERE sale_id IS NULL

UNION ALL

SELECT 'ERP Products - Null product_id' as check_name, COUNT(*) as null_count
FROM erp.products 
WHERE product_id IS NULL;

-- 2. Check for duplicate records
SELECT 'CRM Customers - Duplicate emails' as check_name, 
       COUNT(*) - COUNT(DISTINCT email) as duplicate_count
FROM crm.customers

UNION ALL

SELECT 'ERP Products - Duplicate product_ids' as check_name, 
       COUNT(*) - COUNT(DISTINCT product_id) as duplicate_count
FROM erp.products;

-- 3. Check referential integrity
SELECT 'Sales without matching customers' as check_name, COUNT(*) as orphaned_records
FROM crm.sales s
LEFT JOIN crm.customers c ON s.customer_id = c.customer_id
WHERE c.customer_id IS NULL

UNION ALL

SELECT 'Inventory without matching products' as check_name, COUNT(*) as orphaned_records
FROM erp.inventory i
LEFT JOIN erp.products p ON i.product_id = p.product_id
WHERE p.product_id IS NULL;

-- 4. Data ranges and business rules validation
SELECT 'Sales with negative amounts' as check_name, COUNT(*) as invalid_records
FROM crm.sales
WHERE net_amount < 0

UNION ALL

SELECT 'Products with cost > list price' as check_name, COUNT(*) as invalid_records
FROM erp.products
WHERE cost_price > list_price

UNION ALL

SELECT 'Inventory with negative quantities' as check_name, COUNT(*) as invalid_records
FROM erp.inventory
WHERE quantity_on_hand < 0;

-- 5. Summary statistics
SELECT 'Total customers' as metric, COUNT(*)::text as value FROM crm.customers
UNION ALL
SELECT 'Total sales', COUNT(*)::text FROM crm.sales
UNION ALL
SELECT 'Total products', COUNT(*)::text FROM erp.products
UNION ALL
SELECT 'Total inventory records', COUNT(*)::text FROM erp.inventory
UNION ALL
SELECT 'Total sales amount', ROUND(SUM(net_amount), 2)::text FROM crm.sales
UNION ALL
SELECT 'Average order value', ROUND(AVG(net_amount), 2)::text FROM crm.sales;