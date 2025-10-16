from datetime import datetime, timedelta
# ----------------------------
# Default DAG args
# ----------------------------
default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
from minio import Minio
import csv, json, os, logging, uuid
import io
import pandas as pd

# ----------------------------
# Helper: Save data to Data Lake
# ----------------------------
def save_to_data_lake(data, data_type, context):
    minio_client = Minio(endpoint="minio:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    bucket_name = "data-lake"
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)

    timestamp = context.get('ds_nodash', datetime.now().strftime('%Y%m%d'))

    filename = f"{data_type}_{timestamp}.json"
    file_path = os.path.join("/tmp", filename)
    with open(file_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, ensure_ascii=False, default=str)

    object_name = f"raw/{data_type}/{filename}"
    try:
        minio_client.remove_object(bucket_name, object_name)
    except:
        pass
    minio_client.fput_object(bucket_name, object_name, file_path)
    logging.info(f"Ham veri Data Lake'e yüklendi: {object_name}")

    return object_name


# ----------------------------
# DAG tanımı
# ----------------------------
dag = DAG(
    'crm_erp_etl_pipeline',
    default_args=default_args,
    description='CRM + ERP ETL pipeline with Data Lake, raw tables, analysis, and dbt',
    schedule_interval='0 */6 * * *',  # Her 6 saatte bir (00:00, 06:00, 12:00, 18:00)
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'crm', 'erp', 'dbt']
)

# ----------------------------
# 0️⃣ Ensure RAW schema and tables exist
# ----------------------------
def init_raw_tables(**context):
    pg = PostgresHook(postgres_conn_id='postgres_default')
    ddl = [
        "CREATE SCHEMA IF NOT EXISTS raw;",
        """
        CREATE TABLE IF NOT EXISTS raw.crm_customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT,
            email TEXT,
            phone TEXT,
            city TEXT,
            status TEXT,
            registration_date DATE,
            extracted_at TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raw.erp_orders (
            order_id VARCHAR(128) PRIMARY KEY,
            customer_id INTEGER,
            product_id VARCHAR(128),
            quantity INTEGER,
            unit_price NUMERIC(10,2),
            total_amount NUMERIC(10,2),
            status TEXT,
            order_date TIMESTAMP,
            extracted_at TIMESTAMP
        );
        """
    ]
    for stmt in ddl:
        pg.run(stmt)

init_raw_tables_task = PythonOperator(
    task_id='init_raw_tables',
    python_callable=init_raw_tables,
    dag=dag
)

# ----------------------------
# 1️⃣ Extract CRM data
# ----------------------------
def extract_crm_data(**context):
    logging.info("CRM verisi çekiliyor...")
    mssql_hook = MsSqlHook(mssql_conn_id='mssql_crm')
    sql = """
        SELECT id as customer_id, customer_name, email, phone, city, status, registration_date, created_at
        FROM crm.dbo.customers 
        WHERE status='active' AND created_at >= DATEADD(day,-30,GETDATE())
        ORDER BY id;
    """
    records = mssql_hook.get_records(sql)
    if records:
        save_to_data_lake(records, "crm", context)
    logging.info(f"{len(records)} adet CRM kaydı Data Lake'e kaydedildi.")
    return len(records)

extract_crm_task = PythonOperator(
    task_id='extract_crm_data',
    python_callable=extract_crm_data,
    dag=dag
)

# ----------------------------
# 2️⃣ Load Data Lake → Raw Tables
# ----------------------------
def load_from_data_lake_to_raw(**context):
    logging.info("Data Lake'den raw tablolara yükleme başlatıldı...")
    minio_client = Minio(endpoint="minio:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    bucket_name = "data-lake"
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    timestamp = context.get('ds_nodash', datetime.now().strftime('%Y%m%d'))

    # CRM
    try:
        object_name = f"raw/crm/crm_{timestamp}.json"
        response = minio_client.get_object(bucket_name, object_name)
        crm_df = pd.DataFrame(json.load(io.BytesIO(response.read())))
        for _, row in crm_df.iterrows():
            sql = """
            INSERT INTO raw.crm_customers (
                customer_id, customer_name, email, phone, city, status, registration_date, extracted_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
            ON CONFLICT (customer_id) DO UPDATE SET
                customer_name=EXCLUDED.customer_name,
                email=EXCLUDED.email,
                phone=EXCLUDED.phone,
                city=EXCLUDED.city,
                status=EXCLUDED.status,
                registration_date=EXCLUDED.registration_date,
                extracted_at=EXCLUDED.extracted_at;
            """
            pg_hook.run(sql, parameters=(
                row['customer_id'], row['customer_name'], row['email'], row['phone'],
                row['city'], row['status'], row['registration_date']
            ))
    except Exception as e:
        logging.warning(f"CRM yükleme hatası: {e}")

    # Orders (streaming consumer tarafından yazılan)
    try:
        objects = minio_client.list_objects(bucket_name, prefix="raw/order/", recursive=True)
        for obj in objects:
            resp = minio_client.get_object(bucket_name, obj.object_name)
            order_df = pd.DataFrame(json.load(io.BytesIO(resp.read())))
            for _, r in order_df.iterrows():
                sql="""INSERT INTO raw.erp_orders (order_id, customer_id, product_id, quantity, unit_price, total_amount, status, order_date, extracted_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                ON CONFLICT (order_id) DO UPDATE SET
                customer_id=EXCLUDED.customer_id, product_id=EXCLUDED.product_id, quantity=EXCLUDED.quantity, unit_price=EXCLUDED.unit_price,
                total_amount=EXCLUDED.total_amount, status=EXCLUDED.status, order_date=EXCLUDED.order_date, extracted_at=EXCLUDED.extracted_at;"""
                pg_hook.run(sql, parameters=(
                    r.get('event_id',str(uuid.uuid4())),
                    r['customer_id'],
                    r['product_id'],
                    r['quantity'],
                    r['price'],
                    r['quantity']*r['price'],
                    r.get('status','completed'),
                    r['timestamp']
                ))
    except Exception as e:
        logging.warning(f"Order yükleme hatası: {e}")

    logging.info("✅ Data Lake'den raw tablolara yükleme tamamlandı.")

load_from_datalake_task = PythonOperator(
    task_id='load_from_data_lake_to_raw',
    python_callable=load_from_data_lake_to_raw,
    dag=dag
)

# ----------------------------
# DAG Dependencies
# ----------------------------

[init_raw_tables_task, extract_crm_task] >> load_from_datalake_task

# ----------------------------
# 4️⃣ Run DBT models
# ----------------------------
from airflow.operators.bash import BashOperator

dbt_run_task = BashOperator(
    task_id='run_dbt_models',
    bash_command='cd /opt/dbt && dbt run',
    dag=dag
)

load_from_datalake_task >> dbt_run_task


# Get-Process -Id (Get-NetTCPConnection -LocalPort 5432).OwningProcess

# Stop-Process -Id (Get-NetTCPConnection -LocalPort 5432).OwningProcess -Force

#dbeaver-ce &




