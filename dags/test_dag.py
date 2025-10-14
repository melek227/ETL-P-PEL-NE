from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
import csv
import os
import json
import pickle
from minio import Minio

def save_to_data_lake(data, data_type, context):
    """Veriyi otomatik format detection ile Data Lake'e kaydet"""
    
    minio_client = Minio(
        endpoint="localhost:9000",
        access_key="minioadmin", 
        secret_key="minioadmin",
        secure=False
    )
    bucket_name = "data-lake"
    
    # Bucket yoksa oluştur
    found = minio_client.bucket_exists(bucket_name)
    if not found:
        minio_client.make_bucket(bucket_name)
    
    timestamp = context.get('ds_nodash', datetime.now().strftime('%Y%m%d'))
    
    # Veri formatını otomatik belirle ve kaydet
    if isinstance(data[0], (list, tuple)):  # Structured data
        # CSV formatında kaydet
        filename = f"{data_type}_{timestamp}.csv"
        file_path = os.path.join("/tmp", filename)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            for row in data:
                writer.writerow(row)
        
    elif isinstance(data[0], dict):  # Dictionary data
        # JSON formatında kaydet
        filename = f"{data_type}_{timestamp}.json"
        file_path = os.path.join("/tmp", filename)
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False, default=str)
    
    else:  # Other formats - pickle as fallback
        filename = f"{data_type}_{timestamp}.pkl"
        file_path = os.path.join("/tmp", filename)
        
        with open(file_path, 'wb') as pklfile:
            pickle.dump(data, pklfile)
    
    # MinIO'ya yükle
    object_name = f"raw/{data_type}/{filename}"
    minio_client.fput_object(bucket_name, object_name, file_path)
    logging.info(f"Ham veri Data Lake'e yüklendi: {object_name} (Format: {filename.split('.')[-1]})")
    
    return object_name, filename.split('.')[-1]

# Default arguments
default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # Retry'yi kapat
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'crm_erp_etl_pipeline',
    default_args=default_args,
    description='Complete ETL pipeline for CRM and ERP data with dbt transformations',
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'crm', 'erp', 'dbt', 'postgresql']
)

def extract_crm_data(**context):
    """CRM sisteminden gerçek verileri çeker ve data warehouse'a yükler"""
    logging.info("Starting CRM data extraction from crm_system.customers...")
    
    try:
        # PostgreSQL bağlantısı (kaynak ve hedef aynı DB)
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        # CRM kaynak sisteminden verileri çek
        crm_extract_sql = """
            SELECT 
                id as customer_id,
                customer_name,
                email,
                phone,
                city,
                status,
                registration_date,
                created_at
            FROM crm_system.customers 
            WHERE status = 'active' 
            AND created_at >= NOW() - INTERVAL '30 days'
            ORDER BY id;
        """
        
        crm_records = pg_hook.get_records(crm_extract_sql)
        logging.info(f"Extracted {len(crm_records)} records from CRM system")

        # Ham verileri Data Lake'e kaydet
        if crm_records:
            save_to_data_lake(crm_records, "crm", context)
        
        logging.info(f"✅ CRM ETL Connector: Extracted {len(crm_records)} customer records and saved to Data Lake")
        return len(crm_records)
        
    except Exception as e:
        logging.error(f"❌ CRM ETL Connector failed: {str(e)}")
        raise

def extract_erp_data(**context):
    """ERP sisteminden gerçek siparişleri çeker ve data warehouse'a yükler"""
    logging.info("Starting ERP data extraction from erp_system.orders...")
    
    try:
        # PostgreSQL bağlantısı (kaynak ve hedef aynı DB)
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        # ERP kaynak sisteminden siparişleri çek - CRM müşteri bilgileriyle join
        erp_extract_sql = """
            SELECT 
                o.id as order_id,
                c.id as customer_id,
                o.product_name,
                o.quantity,
                o.unit_price,
                o.total_amount,
                o.order_date,
                o.order_status,
                c.customer_name,
                o.created_at
            FROM erp_system.orders o
            LEFT JOIN crm_system.customers c ON o.customer_email = c.email
            WHERE o.created_at >= NOW() - INTERVAL '30 days'
            ORDER BY o.id;
        """
        
        erp_records = pg_hook.get_records(erp_extract_sql)
        logging.info(f"Extracted {len(erp_records)} order records from ERP system")

        # Ham ERP verilerini Data Lake'e yükle (raw tabloya yükleme load_from_data_lake_to_raw task'ında yapılacak)
        if erp_records:
            save_to_data_lake(erp_records, "erp", context)
            logging.info(f"ERP verisi Data Lake'e kaydedildi")
        
        logging.info(f"✅ ERP ETL Connector: Extracted {len(erp_records)} order records and saved to Data Lake")
        return len(erp_records)
        
    except Exception as e:
        logging.error(f"❌ ERP ETL Connector failed: {str(e)}")
        raise



def load_from_data_lake_to_raw(**context):
    """MinIO'dan veriyi okuyup raw tablolara yükler - Genel format destekli"""
    logging.info("Loading data from Data Lake to Raw tables...")
    
    try:
        
        # MinIO client
        minio_client = Minio(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        bucket_name = "data-lake"
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        timestamp = context.get('ds_nodash', datetime.now().strftime('%Y%m%d'))
        
        # CRM verilerini yükle
        try:
            # Önce hangi formatta olduğunu kontrol et
            for ext in ['csv', 'json', 'pkl']:
                object_name = f"raw/crm/crm_{timestamp}.{ext}"
                try:
                    response = minio_client.get_object(bucket_name, object_name)
                    file_path = f"/tmp/crm_temp.{ext}"
                    
                    with open(file_path, 'wb') as f:
                        for data in response.stream(32*1024):
                            f.write(data)
                    
                    # Format'a göre veriyi oku ve raw tabloya yükle
                    if ext == 'csv':
                        with open(file_path, 'r', encoding='utf-8') as csvfile:
                            reader = csv.reader(csvfile)
                            for row in reader:
                                if len(row) >= 5:  # Minimum alan sayısı kontrolü
                                    insert_sql = """
                                        INSERT INTO raw.crm_customers (customer_id, customer_name, email, phone, city, extracted_at) 
                                        VALUES (%s, %s, %s, %s, %s, NOW())
                                        ON CONFLICT (customer_id) DO UPDATE SET 
                                            customer_name = EXCLUDED.customer_name,
                                            email = EXCLUDED.email,
                                            phone = EXCLUDED.phone,
                                            city = EXCLUDED.city,
                                            extracted_at = EXCLUDED.extracted_at;
                                    """
                                    pg_hook.run(insert_sql, parameters=row[:5])
                    
                    elif ext == 'json':
                        with open(file_path, 'r', encoding='utf-8') as jsonfile:
                            data = json.load(jsonfile)
                            for record in data:
                                if isinstance(record, dict):
                                    # Dict'ten veriyi çıkar
                                    params = [
                                        record.get('customer_id'),
                                        record.get('customer_name'),
                                        record.get('email'),
                                        record.get('phone'),
                                        record.get('city')
                                    ]
                                else:
                                    # Liste/tuple formatı
                                    params = record[:5]
                                
                                if params[0] is not None:  # customer_id kontrolü
                                    insert_sql = """
                                        INSERT INTO raw.crm_customers (customer_id, customer_name, email, phone, city, extracted_at) 
                                        VALUES (%s, %s, %s, %s, %s, NOW())
                                        ON CONFLICT (customer_id) DO UPDATE SET 
                                            customer_name = EXCLUDED.customer_name,
                                            email = EXCLUDED.email,
                                            phone = EXCLUDED.phone,
                                            city = EXCLUDED.city,
                                            extracted_at = EXCLUDED.extracted_at;
                                    """
                                    pg_hook.run(insert_sql, parameters=params)
                    
                    elif ext == 'pkl':
                        with open(file_path, 'rb') as pklfile:
                            data = pickle.load(pklfile)
                            for record in data:
                                if len(record) >= 5:
                                    insert_sql = """
                                        INSERT INTO raw.crm_customers (customer_id, customer_name, email, phone, city, extracted_at) 
                                        VALUES (%s, %s, %s, %s, %s, NOW())
                                        ON CONFLICT (customer_id) DO UPDATE SET 
                                            customer_name = EXCLUDED.customer_name,
                                            email = EXCLUDED.email,
                                            phone = EXCLUDED.phone,
                                            city = EXCLUDED.city,
                                            extracted_at = EXCLUDED.extracted_at;
                                    """
                                    pg_hook.run(insert_sql, parameters=record[:5])
                    
                    logging.info(f"✅ CRM verisi Data Lake'den raw tabloya yüklendi: {object_name}")
                    break
                    
                except Exception as e:
                    continue  # Bu format yoksa diğerini dene
                    
        except Exception as e:
            logging.warning(f"CRM verisi Data Lake'den yüklenemedi: {str(e)}")
        
        # ERP verilerini yükle
        try:
            # Önce hangi formatta olduğunu kontrol et
            for ext in ['csv', 'json', 'pkl']:
                object_name = f"raw/erp/erp_{timestamp}.{ext}"
                try:
                    response = minio_client.get_object(bucket_name, object_name)
                    file_path = f"/tmp/erp_temp.{ext}"
                    
                    with open(file_path, 'wb') as f:
                        for data in response.stream(32*1024):
                            f.write(data)
                    
                    # Format'a göre veriyi oku ve raw tabloya yükle
                    if ext == 'csv':
                        with open(file_path, 'r', encoding='utf-8') as csvfile:
                            reader = csv.reader(csvfile)
                            for row in reader:
                                if len(row) >= 6:  # Minimum alan sayısı kontrolü
                                    insert_sql = """
                                        INSERT INTO raw.erp_orders (order_id, customer_id, product_name, quantity, unit_price, order_date, extracted_at) 
                                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                        ON CONFLICT (order_id) DO UPDATE SET 
                                            customer_id = EXCLUDED.customer_id,
                                            product_name = EXCLUDED.product_name,
                                            quantity = EXCLUDED.quantity,
                                            unit_price = EXCLUDED.unit_price,
                                            order_date = EXCLUDED.order_date,
                                            extracted_at = EXCLUDED.extracted_at;
                                    """
                                    # order_id, customer_id, product_name, quantity, unit_price, order_date
                                    params = (row[0], row[1], row[2], row[3], row[4], row[6])
                                    pg_hook.run(insert_sql, parameters=params)
                    
                    elif ext == 'json':
                        with open(file_path, 'r', encoding='utf-8') as jsonfile:
                            data = json.load(jsonfile)
                            for record in data:
                                if isinstance(record, dict):
                                    # Dict'ten veriyi çıkar
                                    params = [
                                        record.get('order_id'),
                                        record.get('customer_id'),
                                        record.get('product_name'),
                                        record.get('quantity'),
                                        record.get('unit_price'),
                                        record.get('order_date')
                                    ]
                                else:
                                    # Liste/tuple formatı
                                    params = (record[0], record[1], record[2], record[3], record[4], record[6])
                                
                                if params[0] is not None:  # order_id kontrolü
                                    insert_sql = """
                                        INSERT INTO raw.erp_orders (order_id, customer_id, product_name, quantity, unit_price, order_date, extracted_at) 
                                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                        ON CONFLICT (order_id) DO UPDATE SET 
                                            customer_id = EXCLUDED.customer_id,
                                            product_name = EXCLUDED.product_name,
                                            quantity = EXCLUDED.quantity,
                                            unit_price = EXCLUDED.unit_price,
                                            order_date = EXCLUDED.order_date,
                                            extracted_at = EXCLUDED.extracted_at;
                                    """
                                    pg_hook.run(insert_sql, parameters=params)
                    
                    elif ext == 'pkl':
                        with open(file_path, 'rb') as pklfile:
                            data = pickle.load(pklfile)
                            for record in data:
                                if len(record) >= 6:
                                    insert_sql = """
                                        INSERT INTO raw.erp_orders (order_id, customer_id, product_name, quantity, unit_price, order_date, extracted_at) 
                                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                        ON CONFLICT (order_id) DO UPDATE SET 
                                            customer_id = EXCLUDED.customer_id,
                                            product_name = EXCLUDED.product_name,
                                            quantity = EXCLUDED.quantity,
                                            unit_price = EXCLUDED.unit_price,
                                            order_date = EXCLUDED.order_date,
                                            extracted_at = EXCLUDED.extracted_at;
                                    """
                                    # order_id, customer_id, product_name, quantity, unit_price, order_date
                                    params = (record[0], record[1], record[2], record[3], record[4], record[6])
                                    pg_hook.run(insert_sql, parameters=params)
                    
                    logging.info(f"✅ ERP verisi Data Lake'den raw tabloya yüklendi: {object_name}")
                    break
                    
                except Exception as e:
                    continue  # Bu format yoksa diğerini dene
                    
        except Exception as e:
            logging.warning(f"ERP verisi Data Lake'den yüklenemedi: {str(e)}")
        
        logging.info("✅ Data Lake'den Raw tablolara yükleme tamamlandı")
        
    except Exception as e:
        logging.error(f"❌ Data Lake'den yükleme hatası: {str(e)}")
        raise



# PostgreSQL bağlantı kontrolü
postgres_sensor = BashOperator(
    task_id='check_postgres_connection',
    bash_command='echo "PostgreSQL connection successful!"',
    dag=dag
)

# Raw veri çekme taskları
extract_crm_task = PythonOperator(
    task_id='extract_crm_data',
    python_callable=extract_crm_data,
    dag=dag
)

extract_erp_task = PythonOperator(
    task_id='extract_erp_data',
    python_callable=extract_erp_data,
    dag=dag
)


# Data Lake'den Raw tablolara yükleme
load_from_datalake_task = PythonOperator(
    task_id='load_from_data_lake_to_raw',
    python_callable=load_from_data_lake_to_raw,
    dag=dag
)

# Streaming order eventlerini MinIO'dan okuyup customer ile birleştirip hız ihlali/sipariş analizi yapan task
def analyze_orders_with_customers(**context):
    """MinIO'dan order eventlerini ve customer verisini okuyup hız ihlali/sipariş analizi yapar"""
    from minio import Minio
    import pandas as pd
    import glob
    import tempfile
    import io
    logging.info("Order ve customer verisi ile analiz başlatılıyor...")
    minio_client = Minio(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )
    bucket_name = "etl-raw"
    # 1. Customer verisini MinIO'dan oku (ör: raw/crm/crm_*.json)
    customer_df = None
    try:
        # Son customer dosyasını bul
        objects = minio_client.list_objects("data-lake", prefix="raw/crm/", recursive=True)
        customer_files = [obj.object_name for obj in objects if obj.object_name.endswith('.json')]
        if customer_files:
            latest_customer = sorted(customer_files)[-1]
            response = minio_client.get_object("data-lake", latest_customer)
            customer_data = json.load(io.BytesIO(response.read()))
            customer_df = pd.DataFrame(customer_data)
    except Exception as e:
        logging.warning(f"Customer verisi okunamadı: {e}")
        return
    # 2. Order eventlerini MinIO'dan oku (raw/order/ altındaki tüm .json dosyaları)
    order_events = []
    try:
        objects = minio_client.list_objects(bucket_name, prefix="raw/order/", recursive=True)
        for obj in objects:
            if obj.object_name.endswith('.json'):
                response = minio_client.get_object(bucket_name, obj.object_name)
                event = json.load(io.BytesIO(response.read()))
                order_events.append(event)
    except Exception as e:
        logging.warning(f"Order eventleri okunamadı: {e}")
        return
    if not order_events or customer_df is None or customer_df.empty:
        logging.warning("Analiz için yeterli veri yok.")
        return
    order_df = pd.DataFrame(order_events)
    # 3. Join işlemi (ör: customer_id üzerinden)
    if 'customer_id' in order_df.columns and 'customer_id' in customer_df.columns:
        merged = order_df.merge(customer_df, on='customer_id', how='left', suffixes=('_order', '_customer'))
    else:
        logging.warning("customer_id alanı bulunamadı, join yapılamadı.")
        return
    # 4. Hız ihlali/sipariş analizi örneği (ör: hız_ihlali_flag veya benzeri bir alan varsa)
    if 'hiz_ihlali_flag' in merged.columns:
        ihlal_olanlar = merged[merged['hiz_ihlali_flag'] == True]
        oran = len(ihlal_olanlar) / len(merged)
        logging.info(f"Hız ihlali oranı: {oran:.2%}")
    else:
        logging.info(f"Birleştirilmiş sipariş/müşteri kaydı: {len(merged)}")
    # 5. Sonuçları logla veya başka bir yere kaydet
    logging.info("Analiz tamamlandı.")
    return merged.to_dict(orient='records')

analyze_orders_task = PythonOperator(
    task_id='analyze_orders_with_customers',
    python_callable=analyze_orders_with_customers,
    dag=dag
)




# dbt işlemlerini PythonOperator ile çalıştıran fonksiyonlar
import subprocess

def run_dbt_staging(**context):
    """dbt staging modellerini çalıştırır ve PostgreSQL bağlantısını kontrol eder"""
    try:
        # PostgreSQL bağlantı kontrolü
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        pg_hook.get_conn()  # Bağlantı başarılıysa hata vermez
        logging.info("PostgreSQL bağlantısı başarılı!")
        # dbt staging çalıştır
        result = subprocess.run(['dbt', 'run', '--select', 'staging'], cwd='/opt/dbt', capture_output=True, text=True)
        logging.info(result.stdout)
        if result.returncode != 0:
            logging.error(result.stderr)
            raise Exception("dbt staging çalıştırılamadı!")
    except Exception as e:
        logging.error(f"dbt staging hatası: {str(e)}")
        raise

def run_dbt_intermediate(**context):
    try:
        result = subprocess.run(['dbt', 'run', '--select', 'intermediate'], cwd='/opt/dbt', capture_output=True, text=True)
        logging.info(result.stdout)
        if result.returncode != 0:
            logging.error(result.stderr)
            raise Exception("dbt intermediate çalıştırılamadı!")
    except Exception as e:
        logging.error(f"dbt intermediate hatası: {str(e)}")
        raise

def run_dbt_marts(**context):
    try:
        result = subprocess.run(['dbt', 'run', '--select', 'marts'], cwd='/opt/dbt', capture_output=True, text=True)
        logging.info(result.stdout)
        if result.returncode != 0:
            logging.error(result.stderr)
            raise Exception("dbt marts çalıştırılamadı!")
    except Exception as e:
        logging.error(f"dbt marts hatası: {str(e)}")
        raise

dbt_staging_task = PythonOperator(
    task_id='dbt_run_staging',
    python_callable=run_dbt_staging,
    dag=dag
)

dbt_intermediate_task = PythonOperator(
    task_id='dbt_run_intermediate',
    python_callable=run_dbt_intermediate,
    dag=dag
)

dbt_marts_task = PythonOperator(
    task_id='dbt_run_marts',
    python_callable=run_dbt_marts,
    dag=dag
)




def run_dbt_tests(**context):
    import subprocess
    result = subprocess.run(['dbt', 'test'], cwd='/opt/dbt', capture_output=True, text=True)
    logging.info(result.stdout)
    if result.returncode != 0:
        logging.error(result.stderr)
        raise Exception("dbt test çalıştırılamadı!")

dbt_test_task = PythonOperator(
    task_id='dbt_run_tests',
    python_callable=run_dbt_tests,
    dag=dag
)


# Task dependencies - ETL pipeline akışı
# Kaynak sistem → MinIO → Raw Tables → dbt akışı + streaming order analizi
postgres_sensor >> [extract_crm_task, extract_erp_task]
[extract_crm_task, extract_erp_task] >> load_from_datalake_task
load_from_datalake_task >> dbt_staging_task
dbt_staging_task >> dbt_intermediate_task
dbt_intermediate_task >> dbt_marts_task
dbt_marts_task >> dbt_test_task

# Streaming order analizi, batch yükleme ve dbt işlemlerinden bağımsız tetiklenebilir
analyze_orders_task



# Get-Process -Id (Get-NetTCPConnection -LocalPort 5432).OwningProcess

# Stop-Process -Id (Get-NetTCPConnection -LocalPort 5432).OwningProcess -Force

#dbeaver-ce &

# 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


