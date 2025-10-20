from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
import os
from minio import Minio
from minio.error import S3Error
import io
import uuid
from datetime import datetime
from typing import List, Dict, Any
import threading
import queue

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-1:9092,kafka-2:9092,kafka-3:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "etl_events")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "etl_group")

# MinIO bağlantı ayarları
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "etl-raw")

# FastAPI app
app = FastAPI(
    title="Consumer Service API",
    description="Kafka'dan event okuyup MinIO'ya yazan mikroservis. Event'leri izleme ve yönetme endpoint'leri.",
    version="1.0.0"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Bucket yoksa oluştur
try:
    found = minio_client.bucket_exists(MINIO_BUCKET)
    if not found:
        minio_client.make_bucket(MINIO_BUCKET)
except Exception as e:
    print(f"MinIO bucket oluşturma hatası: {e}")




# Event'leri saklamak için in-memory queue (son 100 event)
recent_events = queue.Queue(maxsize=100)
consumer_running = False
consumer_threads = []

def process_event(event):
    """Event'i MinIO'ya yaz ve queue'ya ekle"""
    print(f"Received event: {event}")
    
    # Recent events'e ekle
    try:
        if recent_events.full():
            recent_events.get()  # En eskiyi çıkar
        recent_events.put(event)
    except:
        pass
    
    # Event'i JSON olarak MinIO'ya yaz
    try:
        now = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        event_type = event.get("event_type", "unknown")
        
        # Event tipine göre klasörleme
        if event_type == "order_event":
            object_name = f"raw/order/order_{now}_{uuid.uuid4()}.json"
        elif event_type == "crm_data":
            object_name = f"raw/crm/crm_{now}_{uuid.uuid4()}.json"
        elif event_type == "erp_data":
            object_name = f"raw/erp/erp_{now}_{uuid.uuid4()}.json"
        else:
            object_name = f"raw/events/event_{now}_{uuid.uuid4()}.json"
        
        data = json.dumps(event).encode("utf-8")
        minio_client.put_object(
            MINIO_BUCKET,
            object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type="application/json"
        )
        print(f"Event MinIO'ya yazıldı: {object_name}")
        return True
    except S3Error as err:
        print(f"MinIO yazma hatası: {err}")
        return False
    except Exception as e:
        print(f"Bilinmeyen hata: {e}")
        return False

def consume_partition(partition):
    """Belirli bir partition için Kafka'dan mesaj oku (thread)"""
    global consumer_running
    brokers = KAFKA_BROKER.split(',')
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=brokers,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id=KAFKA_CONSUMER_GROUP,
        max_poll_records=500,
        session_timeout_ms=30000,
        heartbeat_interval_ms=10000
    )
    consumer.assign([partition])
    print(f"✅ Partition {partition.partition} için consumer başlatıldı.")
    try:
        for message in consumer:
            if not consumer_running:
                break
            print(f"📨 Partition {message.partition}, Offset {message.offset}: {message.value}")
            process_event(message.value)
    finally:
        consumer.close()

# Root endpoint
@app.get("/")
def root():
    return {
        "service": "Consumer Service",
        "status": "running",
        "consumer_status": "active" if consumer_running else "stopped",
        "description": "Kafka'dan veri okuyup MinIO'ya yazan servis",
        "endpoints": {
            "health": "/health",
            "start_consumer": "/consumer/start",
            "stop_consumer": "/consumer/stop",
            "consumer_status": "/consumer/status",
            "recent_events": "/events/recent",
            "minio_objects": "/minio/objects",
            "docs": "/docs"
        }
    }

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "kafka_broker": KAFKA_BROKER,
        "kafka_topic": KAFKA_TOPIC,
        "minio_endpoint": MINIO_ENDPOINT,
        "minio_bucket": MINIO_BUCKET,
        "consumer_running": consumer_running,
        "timestamp": datetime.utcnow().isoformat()
    }

# Consumer yönetimi
@app.post("/consumer/start")
def start_consumer(background_tasks: BackgroundTasks):
    """Her partition için ayrı consumer başlat"""
    global consumer_running, consumer_threads
    if consumer_running:
        return {"status": "already_running", "message": "Consumer zaten çalışıyor"}
    brokers = KAFKA_BROKER.split(',')
    # Partition bilgilerini almak için geçici consumer
    temp_consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=brokers,
        group_id=KAFKA_CONSUMER_GROUP
    )
    partitions = temp_consumer.partitions_for_topic(KAFKA_TOPIC)
    temp_consumer.close()
    consumer_threads = []
    consumer_running = True
    for p in partitions:
        partition = kafka.TopicPartition(KAFKA_TOPIC, p)
        t = threading.Thread(target=consume_partition, args=(partition,), daemon=True)
        consumer_threads.append(t)
        t.start()
    return {
        "status": "started",
        "message": f"{len(partitions)} partition için consumer başlatıldı",
        "kafka_topic": KAFKA_TOPIC
    }

@app.post("/consumer/stop")
def stop_consumer():
    """Tüm consumer thread'lerini durdur"""
    global consumer_running, consumer_threads
    if not consumer_running:
        return {"status": "already_stopped", "message": "Consumer zaten durmuş"}
    consumer_running = False
    for t in consumer_threads:
        t.join(timeout=2)
    consumer_threads = []
    return {
        "status": "stopped",
        "message": "Tüm consumer thread'leri durduruldu"
    }

@app.get("/consumer/status")
def consumer_status():
    """Consumer durumunu kontrol et"""
    return {
        "consumer_running": consumer_running,
        "kafka_broker": KAFKA_BROKER,
        "kafka_topic": KAFKA_TOPIC,
        "timestamp": datetime.utcnow().isoformat()
    }

# Event izleme
@app.get("/events/recent")
def get_recent_events(limit: int = 10):
    """Son işlenen event'leri getir"""
    events = list(recent_events.queue)
    return {
        "total": len(events),
        "events": events[-limit:] if limit > 0 else events
    }

# MinIO işlemleri
@app.get("/minio/objects")
def list_minio_objects(prefix: str = "raw/", max_items: int = 50):
    """MinIO'daki objeleri listele"""
    try:
        objects = minio_client.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True)
        object_list = []
        
        for i, obj in enumerate(objects):
            if i >= max_items:
                break
            object_list.append({
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
            })
        
        return {
            "bucket": MINIO_BUCKET,
            "prefix": prefix,
            "count": len(object_list),
            "objects": object_list
        }
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")

@app.get("/minio/object/{path:path}")
def get_minio_object(path: str):
    """MinIO'dan belirli bir objeyi oku"""
    try:
        response = minio_client.get_object(MINIO_BUCKET, path)
        data = json.loads(response.read().decode('utf-8'))
        response.close()
        response.release_conn()
        
        return {
            "object_name": path,
            "data": data
        }
    except S3Error as e:
        raise HTTPException(status_code=404, detail=f"Object not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Startup event
@app.on_event("startup")
def startup_event():
    """Uygulama başlarken her partition için consumer başlat"""
    start_consumer(BackgroundTasks())

# Shutdown event
@app.on_event("shutdown")
def shutdown_event():
    """Uygulama kapanırken consumer'ı durdur"""
    global consumer_running
    consumer_running = False
