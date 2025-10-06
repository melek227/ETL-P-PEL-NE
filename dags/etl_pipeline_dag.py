from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.http.sensors.http import HttpSensor
import logging
import random
from decimal import Decimal

# Default arguments
default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'comprehensive_etl_pipeline',
    default_args=default_args,
    description='Comprehensive ETL Pipeline for CRM/ERP Data with dbt Transformations',
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'crm', 'erp', 'dbt', 'warehouse']
)

def setup_database_schemas(**context):
    """Database schema'larını oluşturur"""
    logging.info("Setting up database schemas...")
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Schema'ları oluştur
    schemas = ['raw', 'staging', 'intermediate', 'marts']
    for schema in schemas:
        pg_hook.run(f"CREATE SCHEMA IF NOT EXISTS {schema};")
        logging.info(f"Schema '{schema}' created/verified")
    
    # Raw tablolarını oluştur
    pg_hook.run("""
        CREATE TABLE IF NOT EXISTS raw.crm_customers (
            customer_id SERIAL PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            phone VARCHAR(50),
            registration_date DATE,
            status VARCHAR(50),
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS raw.erp_orders (
            order_id SERIAL PRIMARY KEY,
            customer_id INTEGER,
            product_name VARCHAR(255),
            product_category VARCHAR(100),
            quantity INTEGER,
            unit_price DECIMAL(10,2),
            order_date DATE,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS raw.erp_products (
            product_id SERIAL PRIMARY KEY,
            product_name VARCHAR(255),
            category VARCHAR(100),
            supplier VARCHAR(255),
            cost_price DECIMAL(10,2),
            stock_quantity INTEGER,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    logging.info("Database schemas and tables created successfully")
    return "schemas_created"

def extract_crm_customers(**context):
    """CRM müşteri verilerini çeker"""
    logging.info("Extracting CRM customer data...")
    
    # Simulated CRM API data
    customers = [
        {'customer_name': 'Acme Corporation', 'email': 'contact@acme.com', 'phone': '+90-212-555-0001', 'registration_date': '2024-01-15', 'status': 'active'},
        {'customer_name': 'Tech Solutions Ltd', 'email': 'info@techsol.com', 'phone': '+90-212-555-0002', 'registration_date': '2024-02-20', 'status': 'active'},
        {'customer_name': 'Global Dynamics', 'email': 'sales@globaldyn.com', 'phone': '+90-212-555-0003', 'registration_date': '2024-03-10', 'status': 'inactive'},
        {'customer_name': 'Innovation Hub', 'email': 'hello@innohub.com', 'phone': '+90-212-555-0004', 'registration_date': '2024-04-05', 'status': 'active'},
        {'customer_name': 'Future Systems', 'email': 'contact@futuresys.com', 'phone': '+90-212-555-0005', 'registration_date': '2024-05-12', 'status': 'active'},
    ]
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Truncate and insert fresh data
    pg_hook.run("TRUNCATE TABLE raw.crm_customers RESTART IDENTITY;")
    
    for customer in customers:
        pg_hook.run("""
            INSERT INTO raw.crm_customers (customer_name, email, phone, registration_date, status, extracted_at) 
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, parameters=[customer['customer_name'], customer['email'], customer['phone'], 
                        customer['registration_date'], customer['status']])
    
    logging.info(f"Extracted {len(customers)} CRM customer records")
    return len(customers)

def extract_erp_orders(**context):
    """ERP sipariş verilerini çeker"""
    logging.info("Extracting ERP order data...")
    
    # Simulated ERP data
    orders = [
        {'customer_id': 1, 'product_name': 'Laptop Pro 15', 'product_category': 'Electronics', 'quantity': 2, 'unit_price': 25000, 'order_date': '2024-06-01'},
        {'customer_id': 2, 'product_name': 'Wireless Mouse', 'product_category': 'Accessories', 'quantity': 10, 'unit_price': 450, 'order_date': '2024-06-02'},
        {'customer_id': 1, 'product_name': 'External Monitor', 'product_category': 'Electronics', 'quantity': 1, 'unit_price': 8500, 'order_date': '2024-06-03'},
        {'customer_id': 3, 'product_name': 'Office Chair', 'product_category': 'Furniture', 'quantity': 5, 'unit_price': 1200, 'order_date': '2024-06-04'},
        {'customer_id': 4, 'product_name': 'Mechanical Keyboard', 'product_category': 'Accessories', 'quantity': 3, 'unit_price': 850, 'order_date': '2024-06-05'},
        {'customer_id': 2, 'product_name': 'Tablet 10"', 'product_category': 'Electronics', 'quantity': 1, 'unit_price': 12000, 'order_date': '2024-06-06'},
        {'customer_id': 5, 'product_name': 'Desk Lamp', 'product_category': 'Office', 'quantity': 4, 'unit_price': 320, 'order_date': '2024-06-07'},
    ]
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Truncate and insert fresh data
    pg_hook.run("TRUNCATE TABLE raw.erp_orders RESTART IDENTITY;")
    
    for order in orders:
        pg_hook.run("""
            INSERT INTO raw.erp_orders (customer_id, product_name, product_category, quantity, unit_price, order_date, extracted_at) 
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, parameters=[order['customer_id'], order['product_name'], order['product_category'],
                        order['quantity'], order['unit_price'], order['order_date']])
    
    logging.info(f"Extracted {len(orders)} ERP order records")
    return len(orders)

def extract_erp_products(**context):
    """ERP ürün verilerini çeker"""
    logging.info("Extracting ERP product data...")
    
    products = [
        {'product_name': 'Laptop Pro 15', 'category': 'Electronics', 'supplier': 'TechCorp', 'cost_price': 20000, 'stock_quantity': 50},
        {'product_name': 'Wireless Mouse', 'category': 'Accessories', 'supplier': 'AccessoryPlus', 'cost_price': 300, 'stock_quantity': 200},
        {'product_name': 'External Monitor', 'category': 'Electronics', 'supplier': 'DisplayTech', 'cost_price': 6500, 'stock_quantity': 75},
        {'product_name': 'Office Chair', 'category': 'Furniture', 'supplier': 'ComfortSeating', 'cost_price': 800, 'stock_quantity': 30},
        {'product_name': 'Mechanical Keyboard', 'category': 'Accessories', 'supplier': 'KeyboardMaster', 'cost_price': 600, 'stock_quantity': 120},
        {'product_name': 'Tablet 10"', 'category': 'Electronics', 'supplier': 'TabletCorp', 'cost_price': 9500, 'stock_quantity': 40},
        {'product_name': 'Desk Lamp', 'category': 'Office', 'supplier': 'LightingSolutions', 'cost_price': 200, 'stock_quantity': 80},
    ]
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Truncate and insert fresh data
    pg_hook.run("TRUNCATE TABLE raw.erp_products RESTART IDENTITY;")
    
    for product in products:
        pg_hook.run("""
            INSERT INTO raw.erp_products (product_name, category, supplier, cost_price, stock_quantity, extracted_at) 
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, parameters=[product['product_name'], product['category'], product['supplier'],
                        product['cost_price'], product['stock_quantity']])
    
    logging.info(f"Extracted {len(products)} ERP product records")
    return len(products)

def validate_extracted_data(**context):
    """Çekilen verilerin kalitesini ve bütünlüğünü kontrol eder"""
    logging.info("Starting comprehensive data validation...")
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    validation_results = {}
    
    # CRM veri kontrolü
    crm_count = pg_hook.get_first("SELECT COUNT(*) FROM raw.crm_customers")[0]
    validation_results['crm_customers'] = crm_count
    logging.info(f"CRM Customers: {crm_count} records")
    
    # ERP veri kontrolleri
    orders_count = pg_hook.get_first("SELECT COUNT(*) FROM raw.erp_orders")[0]
    products_count = pg_hook.get_first("SELECT COUNT(*) FROM raw.erp_products")[0]
    validation_results['erp_orders'] = orders_count
    validation_results['erp_products'] = products_count
    logging.info(f"ERP Orders: {orders_count} records")
    logging.info(f"ERP Products: {products_count} records")
    
    # Veri kalite kontrolleri
    invalid_emails = pg_hook.get_first("SELECT COUNT(*) FROM raw.crm_customers WHERE email NOT LIKE '%@%' OR email IS NULL")[0]
    if invalid_emails > 0:
        logging.warning(f"Found {invalid_emails} invalid email addresses")
        validation_results['invalid_emails'] = invalid_emails
    
    negative_prices = pg_hook.get_first("SELECT COUNT(*) FROM raw.erp_orders WHERE unit_price <= 0")[0]
    if negative_prices > 0:
        logging.warning(f"Found {negative_prices} negative or zero prices")
        validation_results['negative_prices'] = negative_prices
    
    orphan_orders = pg_hook.get_first("""
        SELECT COUNT(*) FROM raw.erp_orders o 
        WHERE NOT EXISTS (SELECT 1 FROM raw.crm_customers c WHERE c.customer_id = o.customer_id)
    """)[0]
    if orphan_orders > 0:
        logging.warning(f"Found {orphan_orders} orders without matching customers")
        validation_results['orphan_orders'] = orphan_orders
    
    # Minimum veri gereksinimlerini kontrol et
    if crm_count < 1 or orders_count < 1 or products_count < 1:
        raise ValueError("Insufficient data extracted - pipeline requires minimum data volumes")
    
    logging.info("Data validation completed successfully")
    context['task_instance'].xcom_push(key='validation_results', value=validation_results)
    return validation_results

def generate_pipeline_report(**context):
    """Pipeline sonuçlarını raporlar"""
    logging.info("Generating ETL pipeline report...")
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Validation sonuçlarını al
    validation_results = context['task_instance'].xcom_pull(task_ids='validate_extracted_data', key='validation_results')
    
    # Final data warehouse istatistikleri
    try:
        staging_stats = pg_hook.get_records("""
            SELECT 'customers' as table_name, COUNT(*) as record_count FROM staging.stg_crm_customers
            UNION ALL
            SELECT 'orders', COUNT(*) FROM staging.stg_erp_orders
            UNION ALL  
            SELECT 'products', COUNT(*) FROM staging.stg_erp_products
        """)
        
        marts_stats = pg_hook.get_records("""
            SELECT 'customer_metrics' as table_name, COUNT(*) as record_count FROM marts.customer_metrics
        """)
    except Exception as e:
        logging.warning(f"Could not retrieve warehouse stats (dbt tables may not exist yet): {e}")
        staging_stats = []
        marts_stats = []
    
    # Report oluştur
    report = {
        'pipeline_date': context['ds'],
        'execution_time': context['task_instance'].start_date,
        'validation_results': validation_results,
        'staging_stats': staging_stats,
        'marts_stats': marts_stats,
        'status': 'SUCCESS'
    }
    
    logging.info("=== ETL PIPELINE REPORT ===")
    logging.info(f"Pipeline Date: {report['pipeline_date']}")
    logging.info(f"Execution Time: {report['execution_time']}")
    logging.info(f"Extracted Records: CRM={validation_results.get('crm_customers', 0)}, Orders={validation_results.get('erp_orders', 0)}, Products={validation_results.get('erp_products', 0)}")
    
    if staging_stats:
        logging.info("Staging Layer:")
        for stat in staging_stats:
            logging.info(f"  {stat[0]}: {stat[1]} records")
    
    if marts_stats:
        logging.info("Marts Layer:")
        for stat in marts_stats:
            logging.info(f"  {stat[0]}: {stat[1]} records")
    
    logging.info("ETL Pipeline completed successfully!")
    return report

# Task definitions
setup_db_task = PythonOperator(
    task_id='setup_database_schemas',
    python_callable=setup_database_schemas,
    dag=dag
)

postgres_health_check = PostgresOperator(
    task_id='postgres_health_check',
    postgres_conn_id='postgres_default',
    sql='SELECT 1 as health_check;',
    dag=dag
)

extract_crm_task = PythonOperator(
    task_id='extract_crm_customers',
    python_callable=extract_crm_customers,
    dag=dag
)

extract_orders_task = PythonOperator(
    task_id='extract_erp_orders',
    python_callable=extract_erp_orders,
    dag=dag
)

extract_products_task = PythonOperator(
    task_id='extract_erp_products',
    python_callable=extract_erp_products,
    dag=dag
)

validate_data_task = PythonOperator(
    task_id='validate_extracted_data',
    python_callable=validate_extracted_data,
    dag=dag
)

# dbt transformation tasks
dbt_staging_task = BashOperator(
    task_id='dbt_staging_models',
    bash_command='cd /opt/airflow/dbt_project && dbt run --profiles-dir /opt/airflow/dbt_project --select staging',
    dag=dag
)

dbt_intermediate_task = BashOperator(
    task_id='dbt_intermediate_models',
    bash_command='cd /opt/airflow/dbt_project && dbt run --profiles-dir /opt/airflow/dbt_project --select intermediate',
    dag=dag
)

dbt_marts_task = BashOperator(
    task_id='dbt_marts_models',
    bash_command='cd /opt/airflow/dbt_project && dbt run --profiles-dir /opt/airflow/dbt_project --select marts',
    dag=dag
)

dbt_tests_task = BashOperator(
    task_id='dbt_data_quality_tests',
    bash_command='cd /opt/airflow/dbt_project && dbt test --profiles-dir /opt/airflow/dbt_project',
    dag=dag
)

generate_report_task = PythonOperator(
    task_id='generate_pipeline_report',
    python_callable=generate_pipeline_report,
    dag=dag
)

# Define comprehensive task dependencies
postgres_health_check >> setup_db_task
setup_db_task >> [extract_crm_task, extract_orders_task, extract_products_task]
[extract_crm_task, extract_orders_task, extract_products_task] >> validate_data_task
validate_data_task >> dbt_staging_task
dbt_staging_task >> dbt_intermediate_task
dbt_intermediate_task >> dbt_marts_task
dbt_marts_task >> dbt_tests_task
dbt_tests_task >> generate_report_task