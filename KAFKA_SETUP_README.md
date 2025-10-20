# 🚀 Kafka 3-Broker Partition Setup

## 📋 Yapılan Değişiklikler

### ✅ 1. Docker Compose Güncellemeleri

#### **3 Kafka Broker Eklendi:**
- `kafka-1` (Port: 9092) - Broker ID: 1
- `kafka-2` (Port: 9093) - Broker ID: 2  
- `kafka-3` (Port: 9094) - Broker ID: 3

#### **Önemli Konfigürasyonlar:**
```yaml
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3  # 3 replica
KAFKA_DEFAULT_REPLICATION_FACTOR: 3        # Varsayılan 3 replica
KAFKA_MIN_INSYNC_REPLICAS: 2               # En az 2 broker'a yazılsın
```

#### **Topic Otomasyonu:**
`kafka-init` servisi ile otomatik topic oluşturma:

| Topic | Partitions | Replication Factor |
|-------|------------|-------------------|
| `etl_events` | 3 | 3 |
| `crm_data` | 5 | 3 |
| `erp_data` | 5 | 3 |

### ✅ 2. Producer Service Güncellemeleri

- **Multiple broker desteği** eklendi
- `KAFKA_BROKER` artık 3 broker'ı kabul eder: `kafka-1:9092,kafka-2:9092,kafka-3:9092`
- Health check endpoint'i broker bilgilerini gösterir

### ✅ 3. Consumer Service Güncellemeleri

- **3 broker'dan okuma** desteği eklendi
- **Partition bilgisi** loglarda gösteriliyor
- Tüm partition'lardan paralel okuma yapılıyor

---

## 🏃 Çalıştırma

### 1️⃣ Mevcut Container'ları Durdur ve Temizle

```powershell
docker-compose down -v
```

### 2️⃣ Yeni Yapılandırmayla Başlat

```powershell
docker-compose up -d
```

### 3️⃣ Logları İzle

```powershell
# Tüm servisleri izle
docker-compose logs -f

# Sadece Kafka broker'ları
docker-compose logs -f kafka-1 kafka-2 kafka-3

# Kafka init (topic oluşturma)
docker-compose logs kafka-init

# Producer ve Consumer
docker-compose logs -f producer_service consumer_service
```

---

## 🧪 Test Komutları

### ✅ 1. Broker'ların Durumunu Kontrol Et

```powershell
# Broker 1'e gir
docker exec -it kafka-1 bash

# Broker listesini gör
kafka-broker-api-versions --bootstrap-server kafka-1:9092,kafka-2:9092,kafka-3:9092

# Çık
exit
```

### ✅ 2. Topic'leri Kontrol Et

```powershell
# Topic listesi
docker exec kafka-1 kafka-topics --list --bootstrap-server kafka-1:9092,kafka-2:9092,kafka-3:9092

# Topic detayları (partition ve replica bilgileri)
docker exec kafka-1 kafka-topics --describe --topic etl_events --bootstrap-server kafka-1:9092,kafka-2:9092,kafka-3:9092
```

**Beklenen Çıktı:**
```
Topic: etl_events       TopicId: xxx        PartitionCount: 3       ReplicationFactor: 3
        Topic: etl_events       Partition: 0    Leader: 1       Replicas: 1,2,3 Isr: 1,2,3
        Topic: etl_events       Partition: 1    Leader: 2       Replicas: 2,3,1 Isr: 2,3,1
        Topic: etl_events       Partition: 2    Leader: 3       Replicas: 3,1,2 Isr: 3,1,2
```

### ✅ 3. Producer Service'i Test Et

```powershell
# Health check (broker bilgilerini gösterir)
curl http://localhost:8000/health

# Test mesajı gönder
curl -X POST http://localhost:8000/order `
  -H "Content-Type: application/json" `
  -d '{
    "customer_id": 123,
    "product_id": "PROD-456",
    "quantity": 2,
    "price": 199.99
  }'
```

### ✅ 4. Consumer Service'i Test Et

```powershell
# Consumer'ı başlat
curl -X POST http://localhost:8001/consumer/start

# Consumer durumunu kontrol et
curl http://localhost:8001/consumer/status

# Son event'leri gör
curl http://localhost:8001/events/recent
```

### ✅ 5. Partition Dağılımını Gözlemle

```powershell
# Consumer loglarında partition bilgisi
docker-compose logs -f consumer_service

# Göreceğin: "📨 Partition 0, Offset 5: {...}"
# Her mesaj farklı partition'a gidebilir
```

### ✅ 6. Mesaj Üretip İzle (10 mesaj)

```powershell
# PowerShell ile döngü
for ($i=1; $i -le 10; $i++) {
    curl -X POST http://localhost:8000/order `
      -H "Content-Type: application/json" `
      -d "{
        `"customer_id`": $i,
        `"product_id`": `"PROD-$i`",
        `"quantity`": $i,
        `"price`": $(100 * $i)
      }"
    Write-Host "Mesaj $i gönderildi"
    Start-Sleep -Milliseconds 500
}
```

---

## 🔍 Hata Toleransı Testi

### Test: 1 Broker'ı Kapat

```powershell
# Broker 2'yi durdur
docker stop kafka-2

# Mesaj göndermeye devam et (çalışmalı!)
curl -X POST http://localhost:8000/order `
  -H "Content-Type: application/json" `
  -d '{
    "customer_id": 999,
    "product_id": "TEST-FAILOVER",
    "quantity": 1,
    "price": 99.99
  }'

# Topic durumunu kontrol et
docker exec kafka-1 kafka-topics --describe --topic etl_events --bootstrap-server kafka-1:9092,kafka-3:9092

# Broker 2'yi tekrar başlat
docker start kafka-2
```

**Beklenen:** Sistem çalışmaya devam etmeli! 2/3 quorum sağlanıyor.

---

## 📊 Monitoring Komutları

### Consumer Group Durumu

```powershell
docker exec kafka-1 kafka-consumer-groups --describe --group etl_group --bootstrap-server kafka-1:9092,kafka-2:9092,kafka-3:9092
```

**Çıktı:**
```
GROUP           TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
etl_group       etl_events      0          45              45              0
etl_group       etl_events      1          38              38              0
etl_group       etl_events      2          42              42              0
```

### Partition Leader'ları Göster

```powershell
docker exec kafka-1 kafka-topics --describe --topic etl_events --bootstrap-server kafka-1:9092
```

---

## 🎯 Beklenen Sonuçlar

### ✅ 3 Broker Çalışıyor
```
kafka-1     ✅ Running (Port 9092)
kafka-2     ✅ Running (Port 9093)
kafka-3     ✅ Running (Port 9094)
```

### ✅ Topic'ler Oluşturuldu
```
etl_events  → 3 partitions, 3 replicas
crm_data    → 5 partitions, 3 replicas
erp_data    → 5 partitions, 3 replicas
```

### ✅ Mesajlar Dağıtıldı
```
Partition 0: [msg1, msg4, msg7, ...]
Partition 1: [msg2, msg5, msg8, ...]
Partition 2: [msg3, msg6, msg9, ...]
```

### ✅ Replica'lar Dağıtıldı
```
Partition 0: Leader=Broker1, Replicas=[Broker1, Broker2, Broker3]
Partition 1: Leader=Broker2, Replicas=[Broker2, Broker3, Broker1]
Partition 2: Leader=Broker3, Replicas=[Broker3, Broker1, Broker2]
```

---

## 🐛 Troubleshooting

### Problem: Broker'lar başlamıyor

```powershell
# ZooKeeper durumunu kontrol et
docker-compose logs zookeeper

# Broker loglarını incele
docker-compose logs kafka-1 kafka-2 kafka-3

# Port çakışması kontrolü
netstat -an | Select-String "9092|9093|9094"
```

### Problem: Topic oluşturulmadı

```powershell
# Init service logunu kontrol et
docker-compose logs kafka-init

# Manuel topic oluştur
docker exec kafka-1 kafka-topics --create \
  --topic test_topic \
  --partitions 3 \
  --replication-factor 3 \
  --bootstrap-server kafka-1:9092,kafka-2:9092,kafka-3:9092
```

### Problem: Consumer mesaj okumuyor

```powershell
# Consumer group'u sıfırla
docker exec kafka-1 kafka-consumer-groups --group etl_group --reset-offsets --to-earliest --topic etl_events --execute --bootstrap-server kafka-1:9092
```

---

## 📚 Referanslar

- **Kafka Documentation:** https://kafka.apache.org/documentation/
- **Confluent Platform:** https://docs.confluent.io/
- **kafka-python:** https://kafka-python.readthedocs.io/

---

## 🎓 Mülakat Noktaları

1. **3 broker neden?** → Quorum (2/3), hata toleransı, maliyet dengesi
2. **Replication factor 3 neden?** → Her partition 3 kopyada, veri güvenliği
3. **Min in-sync replicas 2 neden?** → En az 2 broker'a yazılmadan commit olmaz
4. **Partition sayısı nasıl belirlenir?** → Throughput ihtiyacı, consumer sayısı, parallellik
5. **Leader election nasıl olur?** → ZooKeeper/KRaft ile otomatik, ISR (In-Sync Replicas) arasından

---

✅ **Setup tamamlandı! Başarılar!** 🚀
