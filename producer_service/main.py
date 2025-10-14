from fastapi import FastAPI, Request
from pydantic import BaseModel
from kafka import KafkaProducer
import json
import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "etl_events")

app = FastAPI()
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

class UserEvent(BaseModel):
    user_id: int
    data: dict

@app.post("/event")
def send_event(event: UserEvent):
    producer.send(KAFKA_TOPIC, event.dict())
    producer.flush()
    return {"status": "event sent"}
