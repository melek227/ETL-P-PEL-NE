# 🎯 Kafka 3-Broker Partition Mimarisi

## 📐 Mimari Diyagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     KAFKA CLUSTER (3 BROKER)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │  BROKER 1      │  │  BROKER 2      │  │  BROKER 3      │    │
│  │  ID: 1         │  │  ID: 2         │  │  ID: 3         │    │
│  │  Port: 9092    │  │  Port: 9093    │  │  Port: 9094    │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│         │                   │                   │                │
│         │                   │                   │                │
│  Topic: etl_events (3 partitions, replication-factor=3)         │
│                                                                   │
│  Partition 0:                                                    │
│  ├─ Leader:   Broker 1  ✅                                      │
│  ├─ Replica:  Broker 2                                          │
│  └─ Replica:  Broker 3                                          │
│                                                                   │
│  Partition 1:                                                    │
│  ├─ Leader:   Broker 2  ✅                                      │
│  ├─ Replica:  Broker 3                                          │
│  └─ Replica:  Broker 1                                          │
│                                                                   │
│  Partition 2:                                                    │
│  ├─ Leader:   Broker 3  ✅                                      │
│  ├─ Replica:  Broker 1                                          │
│  └─ Replica:  Broker 2                                          │
└─────────────────────────────────────────────────────────────────┘

                            ▲                ▼
                            │                │
                ┌───────────┴────────────────┴────────────┐
                │                                          │
        ┌───────▼────────┐                    ┌──────────▼─────────┐
        │   PRODUCER     │                    │    CONSUMER        │
        │   SERVICE      │                    │    SERVICE         │
        │                │                    │                    │
        │  Port: 8000    │                    │   Port: 8001       │
        │                │                    │                    │
        │  Connects to:  │                    │  Connects to:      │
        │  3 brokers     │                    │  3 brokers         │
        └────────────────┘                    └────────────────────┘
                │                                         │
                │                                         │
                └─────────── Messages ───────────────────┘
```

---

## 🔄 Mesaj Akışı

```
1. Producer mesaj gönderir
   │
   ├─ Mesaj 1 → Hash/Round-robin → Partition 0 (Broker 1)
   │                                    ├─ Replica → Broker 2
   │                                    └─ Replica → Broker 3
   │
   ├─ Mesaj 2 → Hash/Round-robin → Partition 1 (Broker 2)
   │                                    ├─ Replica → Broker 3
   │                                    └─ Replica → Broker 1
   │
   └─ Mesaj 3 → Hash/Round-robin → Partition 2 (Broker 3)
                                        ├─ Replica → Broker 1
                                        └─ Replica → Broker 2

2. Consumer tüm partition'lardan okur
   │
   ├─ Partition 0'dan oku
   ├─ Partition 1'den oku
   └─ Partition 2'den oku
```

---

## ⚡ Hata Toleransı Senaryosu

### 🔴 Broker 2 Çöktü!

```
BEFORE:
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Broker 1 │  │ Broker 2 │  │ Broker 3 │
│    ✅    │  │    ✅    │  │    ✅    │
└──────────┘  └──────────┘  └──────────┘

Partition 1: Leader=Broker2, ISR=[B2,B3,B1]
```

```
AFTER (Broker 2 crashed):
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Broker 1 │  │ Broker 2 │  │ Broker 3 │
│    ✅    │  │    ❌    │  │    ✅    │
└──────────┘  └──────────┘  └──────────┘

Partition 1: Leader=Broker3 (otomatik!), ISR=[B3,B1]
                ↑
                Failover!
```

**Sonuç:** 
- ✅ Sistem çalışmaya devam eder
- ✅ Mesajlar kaybolmaz
- ✅ 2/3 quorum hala sağlanıyor
- ✅ Broker 2 geri gelince otomatik sync

---

## 📊 Partition Dağılımı Örneği

**10 mesaj gönderildiğinde:**

```
Producer → etl_events topic

Mesaj 1  → Partition 0 (Broker 1) ┐
Mesaj 4  → Partition 0 (Broker 1) ├─ 3 mesaj
Mesaj 7  → Partition 0 (Broker 1) ┘
Mesaj 10 → Partition 0 (Broker 1)

Mesaj 2  → Partition 1 (Broker 2) ┐
Mesaj 5  → Partition 1 (Broker 2) ├─ 3 mesaj
Mesaj 8  → Partition 1 (Broker 2) ┘

Mesaj 3  → Partition 2 (Broker 3) ┐
Mesaj 6  → Partition 2 (Broker 3) ├─ 4 mesaj
Mesaj 9  → Partition 2 (Broker 3) ┘
```

**Load Balancing:** Mesajlar otomatik dağıtılır!

---

## 🎯 Konfigürasyon Özeti

| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| **Broker Sayısı** | 3 | Minimum production setup |
| **Replication Factor** | 3 | Her partition 3 kopyada |
| **Min In-Sync Replicas** | 2 | En az 2 broker'a yazılsın |
| **Partition (etl_events)** | 3 | Paralel işlem için |
| **Partition (crm_data)** | 5 | Daha yüksek throughput |
| **Producer acks** | all | Tüm replica'lara yazılsın |
| **Consumer Group** | etl_group | Grup halinde consume |

---

## 🔥 Performans Metrikleri

### Tek Broker vs 3 Broker

```
┌─────────────────┬──────────────┬──────────────┐
│     Metrik      │  1 Broker    │  3 Broker    │
├─────────────────┼──────────────┼──────────────┤
│ Throughput      │  1x          │  ~3x         │
│ Hata Toleransı  │  ❌ Yok     │  ✅ 1 broker │
│ Veri Güvenliği  │  ❌ Tek kopya│  ✅ 3 kopya  │
│ Disk Kapasitesi │  1x          │  1x (dağılmış)│
│ Network I/O     │  1x          │  3x          │
│ Quorum          │  ❌ Yok     │  ✅ 2/3      │
└─────────────────┴──────────────┴──────────────┘
```

---

## 🎓 Key Takeaways

### ✅ 3 Broker Seçilme Nedenleri:

1. **Quorum:** (3/2) + 1 = 2 → 1 broker çökse bile çalışır
2. **Maliyet:** 5 broker aynı toleransı sağlar ama %67 daha pahalı
3. **Standart:** Endüstride en yaygın production setup
4. **Load Balancing:** 3 partition = 3 paralel işlem
5. **Veri Güvenliği:** 3 kopya = maksimum güvenlik

### ✅ Partition Sayısı Belirleme:

- **Consumer sayısı = Partition sayısı** → Maksimum paralellik
- **Yüksek throughput** → Daha fazla partition
- **Düşük latency** → Daha az partition
- **Örnek:** 3 consumer → 3 partition ideal

### ✅ Replication Factor:

- **1:** Üretim için riskli ❌
- **2:** Minimum, ama quorum sorunu
- **3:** İdeal (standart) ⭐
- **5+:** Enterprise, yüksek maliyet

---

## 📞 Quick Reference

```bash
# Broker durumu
docker ps | grep kafka

# Topic listesi
docker exec kafka-1 kafka-topics --list --bootstrap-server kafka-1:9092

# Partition detayları
docker exec kafka-1 kafka-topics --describe --topic etl_events --bootstrap-server kafka-1:9092

# Consumer group durumu
docker exec kafka-1 kafka-consumer-groups --describe --group etl_group --bootstrap-server kafka-1:9092

# Mesaj gönder (test)
curl -X POST http://localhost:8000/order -H "Content-Type: application/json" -d '{"customer_id":1,"product_id":"TEST","quantity":1,"price":99.99}'

# Consumer başlat
curl -X POST http://localhost:8001/consumer/start

# Health check
curl http://localhost:8000/health
curl http://localhost:8001/health
```

---

🎉 **Happy Kafka Streaming!** 🚀
