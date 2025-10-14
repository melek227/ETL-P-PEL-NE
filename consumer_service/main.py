from kafka import KafkaConsumer

import json
import os
from minio import Minio
from minio.error import S3Error


KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "etl_events")

# MinIO bağlantı ayarları
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "etl-raw")

# MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Bucket yoksa oluştur
found = minio_client.bucket_exists(MINIO_BUCKET)
if not found:
    minio_client.make_bucket(MINIO_BUCKET)

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='etl_group'
)



def process_event(event):
    print(f"Received event: {event}")
    # Event'i JSON olarak MinIO'ya yaz
    try:
        import uuid
        from datetime import datetime
        # order eventleri için raw/order/ klasörüne kaydet
        now = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        object_name = f"raw/order/order_{now}_{uuid.uuid4()}.json"
        data = json.dumps(event).encode("utf-8")
        minio_client.put_object(
            MINIO_BUCKET,
            object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type="application/json"
        )
        print(f"Order event MinIO'ya yazıldı: {object_name}")
    except S3Error as err:
        print(f"MinIO yazma hatası: {err}")
    except Exception as e:
        print(f"Bilinmeyen hata: {e}")


import io

if __name__ == "__main__":
    print("Kafka consumer başlatıldı...")
    for message in consumer:
        process_event(message.value)
