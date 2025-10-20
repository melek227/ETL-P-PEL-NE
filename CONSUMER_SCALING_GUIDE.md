# 🚀 Kafka Consumer Scaling (Paralellik) Rehberi

## 🎯 Problem: Neden 3 Consumer?

### **Şu Anki Durum (1 Consumer):**

```
Topic: etl_events (3 partition)

┌─────────────────────────────────────┐
│  Consumer 1 (TEK!)                  │
│  ├─ Partition 0 → sırayla okuyor   │
│  ├─ Partition 1 → sırayla okuyor   │
│  └─ Partition 2 → sırayla okuyor   │
│                                      │
│  ⏱️  Mesaj işleme: 1000 msg/sn     │
└─────────────────────────────────────┘
```

### **İdeal Durum (3 Consumer - Paralel):**

```
Topic: etl_events (3 partition)

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Consumer 1   │  │ Consumer 2   │  │ Consumer 3   │
│ Partition 0  │  │ Partition 1  │  │ Partition 2  │
│              │  │              │  │              │
│ 333 msg/sn   │  │ 333 msg/sn   │  │ 333 msg/sn   │
└──────────────┘  └──────────────┘  └──────────────┘
       ↓                  ↓                  ↓
   AYNI ANDA         AYNI ANDA         AYNI ANDA

⚡ Toplam: 1000 msg/sn (3x daha hızlı işlem!)
```

---

## 📐 Consumer Group Kavramı

### **Aynı Group'taki Consumer'lar:**

```
Consumer Group: "etl_group"

┌─────────────────────────────────────────────────┐
│  Kafka otomatik partition dağıtır:             │
│                                                  │
│  Consumer 1 → Partition 0                       │
│  Consumer 2 → Partition 1                       │
│  Consumer 3 → Partition 2                       │
│                                                  │
│  ✅ Her partition sadece 1 consumer'a atanır   │
│  ✅ Mesaj tekrarı olmaz                         │
│  ✅ Load balancing otomatik                     │
└─────────────────────────────────────────────────┘
```

### **Farklı Group'taki Consumer'lar:**

```
Consumer Group 1: "etl_group"
├─ Consumer A → Tüm partition'ları okur

Consumer Group 2: "analytics_group"  
├─ Consumer B → Tüm partition'ları okur (bağımsız!)

✅ Her group kendi offset'ini tutar
✅ Aynı mesajlar her group tarafından okunur
```

---

## 🛠️ Docker Compose ile 3 Consumer Çalıştırma

### **Yöntem 1: Docker Compose Scale (Basit)**

```powershell
# Container'ları yeniden başlat
docker-compose down

# Consumer service'i 3 instance olarak başlat
docker-compose up -d --scale consumer_service=3

# Durumu kontrol et
docker-compose ps

# Çıktı:
# etl-pipeline_consumer_service_1  running
# etl-pipeline_consumer_service_2  running
# etl-pipeline_consumer_service_3  running
```

### **Yöntem 2: Docker Compose v3 (Deploy - Önerilen)**

docker-compose.yml'de zaten ayarlandı:

```yaml
consumer_service:
  build:
    context: ./consumer_service
  environment:
    - KAFKA_CONSUMER_GROUP=etl_group  # AYNI GROUP!
  deploy:
    replicas: 3  # 3 instance
```

Çalıştırmak için:

```powershell
# Compose V2 (docker-compose)
docker-compose up -d

# Compose V3 (docker compose - yeni)
docker compose up -d
```

---

## 🧪 Test ve Doğrulama

### **1️⃣ Consumer'ları Kontrol Et**

```powershell
# Çalışan consumer'ları listele
docker ps | findstr consumer

# Her consumer'ın logunu izle
docker-compose logs -f consumer_service
```

**Beklenen Çıktı:**
```
consumer_1    | ✅ Kafka consumer başlatıldı
consumer_1    | 👥 Consumer group: etl_group
consumer_1    | 📨 Partition 0, Offset 5: {...}

consumer_2    | ✅ Kafka consumer başlatıldı
consumer_2    | 👥 Consumer group: etl_group
consumer_2    | 📨 Partition 1, Offset 3: {...}

consumer_3    | ✅ Kafka consumer başlatıldı
consumer_3    | 👥 Consumer group: etl_group
consumer_3    | 📨 Partition 2, Offset 7: {...}
```

**Dikkat:** Her consumer **farklı partition** okuyor! ✅

---

### **2️⃣ Consumer Group Durumunu Kontrol Et**

```powershell
docker exec kafka-1 kafka-consumer-groups `
  --describe `
  --group etl_group `
  --bootstrap-server kafka-1:9092,kafka-2:9092,kafka-3:9092
```

**Beklenen Çıktı:**
```
GROUP      TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG  CONSUMER-ID                    HOST
etl_group  etl_events   0          45              45              0    consumer-1-xxx                 /172.18.0.5
etl_group  etl_events   1          38              38              0    consumer-2-xxx                 /172.18.0.6
etl_group  etl_events   2          42              42              0    consumer-3-xxx                 /172.18.0.7
```

**Gördüğün gibi:**
- ✅ 3 farklı consumer
- ✅ Her biri farklı partition'dan okuyor
- ✅ LAG = 0 (tüm mesajlar işlendi)

---

### **3️⃣ Mesaj Gönder ve Dağılımı İzle**

```powershell
# 10 mesaj gönder
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
}

# Consumer loglarını izle
docker-compose logs -f consumer_service
```

**Göreceksin:**
```
consumer_1 | 📨 Partition 0, Offset 10: {'customer_id': 1, ...}
consumer_2 | 📨 Partition 1, Offset 8: {'customer_id': 2, ...}
consumer_3 | 📨 Partition 2, Offset 12: {'customer_id': 3, ...}
consumer_1 | 📨 Partition 0, Offset 11: {'customer_id': 4, ...}
...
```

**Her consumer farklı partition'dan okuyor = PARALEL!** ⚡

---

## ⚖️ Consumer Sayısı vs Partition Sayısı

### **Kurallar:**

| Consumer Sayısı | Partition Sayısı | Sonuç |
|----------------|------------------|-------|
| **1** | 3 | Consumer tüm partition'ları sırayla okur (yavaş) |
| **3** | 3 | ✅ **İdeal!** Her consumer 1 partition (maksimum paralel) |
| **5** | 3 | 2 consumer boşta kalır (gereksiz kaynak) |
| **2** | 3 | 1 consumer 2 partition okur, diğeri 1 partition |

### **En İyi Pratik:**

```
Consumer Sayısı = Partition Sayısı
        ↓
Maksimum paralellik!
```

---

## 🔥 Performans Karşılaştırması

### **Test Senaryosu: 10,000 mesaj**

| Yapılandırma | Süre | Throughput |
|--------------|------|------------|
| 1 Consumer + 3 Partition | 100 sn | 100 msg/sn |
| 3 Consumer + 3 Partition | **35 sn** | **285 msg/sn** ⚡ |

**Sonuç:** ~3x hız artışı! 🚀

---

## 🎓 Mülakat İçin Özet

> **"Consumer sayısı = Partition sayısı olmalıdır, çünkü:**
>
> **1. Maksimum Paralellik:**
> - 3 partition + 3 consumer = Her consumer 1 partition'dan okur
> - Aynı anda 3 partition işlenir (3x hız)
>
> **2. Consumer Group Mekanizması:**
> - Aynı group'taki consumer'lar partition'ları paylaşır
> - Kafka otomatik load balancing yapar
> - Her partition sadece 1 consumer'a atanır
>
> **3. Scalability:**
> - Daha fazla yük → Partition artır + Consumer artır
> - Örnek: 10 partition + 10 consumer = 10x paralellik
>
> **4. Docker Compose ile:**
> - `deploy.replicas: 3` veya `--scale consumer_service=3`
> - Aynı consumer group kullanarak otomatik dağıtım
>
> **Not:** Consumer sayısı > Partition sayısı ise, fazla consumer'lar boşta kalır."

---

## 🛠️ Hızlı Komutlar

```powershell
# Container'ları başlat (3 consumer)
docker-compose up -d --scale consumer_service=3

# Consumer durumunu kontrol et
docker-compose ps | findstr consumer

# Consumer group bilgisi
docker exec kafka-1 kafka-consumer-groups --describe --group etl_group --bootstrap-server kafka-1:9092

# Logları izle
docker-compose logs -f consumer_service

# Partition başına mesaj sayısı
docker exec kafka-1 kafka-run-class kafka.tools.GetOffsetShell --broker-list kafka-1:9092 --topic etl_events

# Consumer'ı durdur
docker-compose stop consumer_service

# Tek bir consumer başlat
docker-compose up -d --scale consumer_service=1
```

---

## 📊 Görselleştirme

```
PARTITION VE CONSUMER EŞLEŞMESİ:

Senaryo 1: 3 Partition + 1 Consumer
┌─────────────────────────────────┐
│  Consumer 1                     │
│  ├─ P0 ─┐                      │
│  ├─ P1 ─┤ Sırayla okuyor       │
│  └─ P2 ─┘                      │
└─────────────────────────────────┘
Hız: 1x


Senaryo 2: 3 Partition + 3 Consumer ✅
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Cons. 1 │  │ Cons. 2 │  │ Cons. 3 │
│   P0    │  │   P1    │  │   P2    │
└─────────┘  └─────────┘  └─────────┘
     ↓            ↓            ↓
 Paralel      Paralel      Paralel
Hız: 3x ⚡


Senaryo 3: 3 Partition + 5 Consumer ⚠️
┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
│ C1  │  │ C2  │  │ C3  │  │ C4  │  │ C5  │
│ P0  │  │ P1  │  │ P2  │  │ BOŞ │  │ BOŞ │
└─────┘  └─────┘  └─────┘  └─────┘  └─────┘
                              ↑        ↑
                         Gereksiz kaynak
Hız: 3x (ama 5 container çalışıyor!)
```

---

## ✅ Sonuç

**3 Partition + 3 Consumer = Mükemmel Denge!** 🎯

- ✅ Maksimum paralellik
- ✅ Optimal kaynak kullanımı
- ✅ 3x hız artışı
- ✅ Kafka'nın load balancing mekanizması

Başarılar! 🚀
