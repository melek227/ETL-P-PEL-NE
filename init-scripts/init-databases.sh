#!/bin/bash
set -e

# Create additional databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE crm;
    CREATE DATABASE erp;
    CREATE DATABASE warehouse;
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON DATABASE crm TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE erp TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE warehouse TO $POSTGRES_USER;
EOSQL

# Create CRM schema and tables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "crm" <<-EOSQL
    -- Create CRM schema
    CREATE SCHEMA IF NOT EXISTS crm;
    
    -- CRM Customers table
    CREATE TABLE IF NOT EXISTS crm.customers (
        customer_id INTEGER PRIMARY KEY,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(20),
        address TEXT,
        city VARCHAR(100),
        state VARCHAR(50),
        zip_code VARCHAR(20),
        country VARCHAR(100),
        registration_date DATE,
        last_activity_date DATE,
        customer_status VARCHAR(50) DEFAULT 'Active',
        customer_type VARCHAR(50) DEFAULT 'Standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- CRM Sales table
    CREATE TABLE IF NOT EXISTS crm.sales (
        sale_id INTEGER PRIMARY KEY,
        customer_id INTEGER REFERENCES crm.customers(customer_id),
        product_id INTEGER NOT NULL,
        sale_date DATE NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price DECIMAL(10,2) NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        discount_amount DECIMAL(10,2) DEFAULT 0,
        net_amount DECIMAL(10,2) NOT NULL,
        sales_rep_id VARCHAR(50),
        channel VARCHAR(50),
        region VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_customers_email ON crm.customers(email);
    CREATE INDEX IF NOT EXISTS idx_customers_status ON crm.customers(customer_status);
    CREATE INDEX IF NOT EXISTS idx_sales_customer ON crm.sales(customer_id);
    CREATE INDEX IF NOT EXISTS idx_sales_date ON crm.sales(sale_date);
    CREATE INDEX IF NOT EXISTS idx_sales_product ON crm.sales(product_id);
EOSQL

# Create ERP schema and tables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "erp" <<-EOSQL
    -- Create ERP schema
    CREATE SCHEMA IF NOT EXISTS erp;
    
    -- ERP Products table
    CREATE TABLE IF NOT EXISTS erp.products (
        product_id INTEGER PRIMARY KEY,
        product_name VARCHAR(255) NOT NULL,
        product_category VARCHAR(100) NOT NULL,
        product_subcategory VARCHAR(100),
        brand VARCHAR(100),
        supplier_id VARCHAR(50),
        cost_price DECIMAL(10,2),
        list_price DECIMAL(10,2),
        weight DECIMAL(8,3),
        dimensions VARCHAR(100),
        product_status VARCHAR(50) DEFAULT 'Active',
        created_date DATE DEFAULT CURRENT_DATE,
        updated_date DATE DEFAULT CURRENT_DATE
    );
    
    -- ERP Inventory table
    CREATE TABLE IF NOT EXISTS erp.inventory (
        inventory_id INTEGER PRIMARY KEY,
        product_id INTEGER REFERENCES erp.products(product_id),
        warehouse_id VARCHAR(50) NOT NULL,
        quantity_on_hand INTEGER DEFAULT 0,
        quantity_reserved INTEGER DEFAULT 0,
        quantity_available INTEGER GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,
        reorder_point INTEGER DEFAULT 0,
        max_stock_level INTEGER DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_products_category ON erp.products(product_category);
    CREATE INDEX IF NOT EXISTS idx_products_status ON erp.products(product_status);
    CREATE INDEX IF NOT EXISTS idx_inventory_product ON erp.inventory(product_id);
    CREATE INDEX IF NOT EXISTS idx_inventory_warehouse ON erp.inventory(warehouse_id);
EOSQL

# Create Warehouse schema
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "warehouse" <<-EOSQL
    -- Create warehouse schema for transformed data
    CREATE SCHEMA IF NOT EXISTS public;
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE SCHEMA IF NOT EXISTS intermediate;
    CREATE SCHEMA IF NOT EXISTS marts;
    CREATE SCHEMA IF NOT EXISTS snapshots;
    
    -- Grant permissions on schemas
    GRANT ALL ON SCHEMA public TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA staging TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA intermediate TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA marts TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA snapshots TO $POSTGRES_USER;
EOSQL

echo "Database initialization completed successfully!"