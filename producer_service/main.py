from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json, os
from datetime import datetime
from typing import Optional, Dict, Any

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-1:9092,kafka-2:9092,kafka-3:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "etl_events")

app = FastAPI(
    title="Order Producer Service",
    description="Kafka'ya sipariş eventleri gönderen servis",
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

# Kafka producer lazy load
producer = None
def get_producer():
    global producer
    if producer is None:
        try:
            # Multiple brokers için liste
            brokers = KAFKA_BROKER.split(',')
            producer = KafkaProducer(
                bootstrap_servers=brokers,  # 3 broker listesi
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',  # Tüm replica'lara yazılsın
                retries=3,
                max_block_ms=5000,
                # Partition stratejisi (round-robin veya key-based)
                # partitioner=lambda key, all_parts, available: hash(key) % len(all_parts) if key else 0
            )
            print(f"✅ Kafka Producer connected to brokers: {brokers}")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Kafka unavailable: {e}")
    return producer

# Pydantic model
class OrderEvent(BaseModel):
    order_id: Optional[int] = None
    customer_id: int
    product_id: str
    quantity: int
    price: float
    order_date: Optional[str] = None
    status: Optional[str] = "pending"

# Root & Health
@app.get("/")
def root():
    return {"service": "Order Producer", "status": "running", "endpoint": "/order"}

@app.get("/health")
def health_check():
    try:
        p = get_producer()
        # Broker bilgisini döndür
        brokers = KAFKA_BROKER.split(',')
        kafka_status = "connected"
    except:
        brokers = []
        kafka_status = "disconnected"
    return {
        "status": "healthy" if kafka_status=="connected" else "degraded",
        "kafka_status": kafka_status,
        "kafka_brokers": brokers,
        "kafka_topic": KAFKA_TOPIC,
        "timestamp": datetime.utcnow().isoformat()
    }

# Order gönderme endpoint
@app.post("/order")
def send_order(order: OrderEvent):
    try:
        prod = get_producer()
        order_data = order.dict()
        order_data["timestamp"] = datetime.utcnow().isoformat()
        order_data["event_type"] = "order_event"

        if not order_data.get("order_date"):
            order_data["order_date"] = datetime.utcnow().isoformat()

        prod.send(KAFKA_TOPIC, order_data)
        prod.flush()

        return {
            "status": "success",
            "message": "Order sent to Kafka",
            "customer_id": order.customer_id,
            "order_id": order_data.get("order_id"),
            "timestamp": order_data["timestamp"]
        }
    except KafkaError as e:
        raise HTTPException(status_code=500, detail=f"Kafka error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Cleanup
@app.on_event("shutdown")
def shutdown_event():
    global producer
    if producer:
        producer.close()




