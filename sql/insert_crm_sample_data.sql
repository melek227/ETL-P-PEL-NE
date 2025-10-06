-- Sample CRM data population script

-- Insert sample customers
INSERT INTO crm.customers (customer_id, first_name, last_name, email, phone, address, city, state, zip_code, country, registration_date, last_activity_date, customer_status, customer_type) VALUES
(1, 'John', 'Doe', 'john.doe@email.com', '555-1234', '123 Main St', 'New York', 'NY', '10001', 'USA', '2023-01-15', '2024-01-10', 'Active', 'Premium'),
(2, 'Jane', 'Smith', 'jane.smith@email.com', '555-5678', '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'USA', '2023-02-20', '2024-01-09', 'Active', 'Standard'),
(3, 'Bob', 'Johnson', 'bob.johnson@email.com', '555-9012', '789 Pine St', 'Chicago', 'IL', '60601', 'USA', '2023-03-10', '2024-01-08', 'Active', 'Premium'),
(4, 'Alice', 'Brown', 'alice.brown@email.com', '555-3456', '321 Elm St', 'Houston', 'TX', '77001', 'USA', '2023-04-05', '2024-01-07', 'Active', 'Standard'),
(5, 'Charlie', 'Wilson', 'charlie.wilson@email.com', '555-7890', '654 Maple Ave', 'Phoenix', 'AZ', '85001', 'USA', '2023-05-12', '2024-01-06', 'Inactive', 'Premium');

-- Insert sample sales data
INSERT INTO crm.sales (sale_id, customer_id, product_id, sale_date, quantity, unit_price, total_amount, discount_amount, net_amount, sales_rep_id, channel, region) VALUES
(1, 1, 101, '2024-01-01', 2, 99.99, 199.98, 0, 199.98, 'REP001', 'Online', 'North'),
(2, 2, 102, '2024-01-02', 1, 149.99, 149.99, 15.00, 134.99, 'REP002', 'Store', 'West'),
(3, 3, 103, '2024-01-03', 3, 79.99, 239.97, 0, 239.97, 'REP001', 'Online', 'Central'),
(4, 1, 102, '2024-01-04', 1, 149.99, 149.99, 0, 149.99, 'REP003', 'Phone', 'North'),
(5, 4, 101, '2024-01-05', 1, 99.99, 99.99, 10.00, 89.99, 'REP002', 'Store', 'South'),
(6, 2, 103, '2024-01-06', 2, 79.99, 159.98, 0, 159.98, 'REP001', 'Online', 'West'),
(7, 5, 102, '2024-01-07', 1, 149.99, 149.99, 0, 149.99, 'REP003', 'Phone', 'West'),
(8, 3, 101, '2024-01-08', 1, 99.99, 99.99, 5.00, 94.99, 'REP002', 'Store', 'Central');

COMMIT;