-- Data quality checks and validation queries

-- 1. Check for null values in critical fields
SELECT 'CRM Customers - Null customer_id' as check_name, COUNT(*) as null_count
FROM crm.customers 
WHERE customer_id IS NULL

UNION ALL

SELECT 'CRM Sales - Null sale_id' as check_name, COUNT(*) as null_count
FROM crm.sales 
WHERE sale_id IS NULL

UNION ALL

SELECT 'ERP Products - Null product_id' as check_name, COUNT(*) as null_count
FROM erp.products 
WHERE product_id IS NULL;

-- 2. Check for duplicate records
SELECT 'CRM Customers - Duplicate emails' as check_name, 
       COUNT(*) - COUNT(DISTINCT email) as duplicate_count
FROM crm.customers

UNION ALL

SELECT 'ERP Products - Duplicate product_ids' as check_name, 
       COUNT(*) - COUNT(DISTINCT product_id) as duplicate_count
FROM erp.products;

-- 3. Check referential integrity
SELECT 'Sales without matching customers' as check_name, COUNT(*) as orphaned_records
FROM crm.sales s
LEFT JOIN crm.customers c ON s.customer_id = c.customer_id
WHERE c.customer_id IS NULL

UNION ALL

SELECT 'Inventory without matching products' as check_name, COUNT(*) as orphaned_records
FROM erp.inventory i
LEFT JOIN erp.products p ON i.product_id = p.product_id
WHERE p.product_id IS NULL;

-- 4. Data ranges and business rules validation
SELECT 'Sales with negative amounts' as check_name, COUNT(*) as invalid_records
FROM crm.sales
WHERE net_amount < 0

UNION ALL

SELECT 'Products with cost > list price' as check_name, COUNT(*) as invalid_records
FROM erp.products
WHERE cost_price > list_price

UNION ALL

SELECT 'Inventory with negative quantities' as check_name, COUNT(*) as invalid_records
FROM erp.inventory
WHERE quantity_on_hand < 0;

-- 5. Summary statistics
SELECT 'Total customers' as metric, COUNT(*)::text as value FROM crm.customers
UNION ALL
SELECT 'Total sales', COUNT(*)::text FROM crm.sales
UNION ALL
SELECT 'Total products', COUNT(*)::text FROM erp.products
UNION ALL
SELECT 'Total inventory records', COUNT(*)::text FROM erp.inventory
UNION ALL
SELECT 'Total sales amount', ROUND(SUM(net_amount), 2)::text FROM crm.sales
UNION ALL
SELECT 'Average order value', ROUND(AVG(net_amount), 2)::text FROM crm.sales;

--vsegidde null deger var mı kontrol edildi

--İki farklı veri setim var:
--Birincisinde segment id, hız ihlali, araç tipi ve zaman damgası bilgileri bulunuyor.
--İkincisinde ise segment id, zaman damgası, araç tipi ve EDS tarafından tespit edilen tüm araç hızları yer alıyor (yani hem hız ihlali yapanlar hem de yapmayanlar mevcut).

--Bu iki veri setini segment id, zaman damgası ve araç tipi üzerinden birleştirerek, hangi segmentlerde ve hangi araç tiplerinde hız ihlali yapılıp yapılmadığını tespit edebilirim.
--Birleştirme sonucunda, hız ihlali değeri null olan kayıtlar, o segmentte ve zamanda hız ihlali yapılmadığını gösterir.
--Bu analiz sayesinde, hız ihlali oranı yüksek olan segmentler ve araç tipleri belirlenir.



--İş analizi açısından, hız ihlali oranı yüksek çıkan segmentler riskli olarak değerlendirilip, bu segmentlerde denetimlerin artırılması veya altyapı iyileştirme çalışmaları yapılması önerilebilir.
--Ayrıca, araç tipi bazında da hangi türlerin daha fazla hız ihlali yaptığı tespit edilerek, hedefli önlemler alınabilir.
--


--duplike kayıtları tespit etme segment_id, zaman_damgasi, arac_tipi alanlarına göre gruplayarak, bu kombinasyonlarda birden fazla kayıt varsa bunları 


---negatif hız değerleri var mı



--sensörlerden 2 dakikada bir veri gelmiş mi
--hız ihlalı değeri yolda yapılacak max hızın üstünde gelmiş mi



--Dimension Tablolar: - dim_segment: segment_id, segment_adı, yol_tipi, vb.
-- - dim_arac_tipi: arac_tipi_id, arac_tipi_adı
 -- - dim_zaman: zaman_damgası, tarih, saat, gün, hafta, vb.

{{ config(materialized='table') }}

SELECT
    segment_id,
    segment_adi,
    yol_tipi
FROM {{ source('kaynak', 'segmentler') }}

{{ config(materialized='table') }}

SELECT
    arac_tipi_id,
    arac_tipi_adi
FROM {{ source('kaynak', 'arac_tipleri') }}

{{ config(materialized='table') }}

SELECT
    zaman_damgasi,
    CAST(zaman_damgasi AS DATE) AS tarih,
    EXTRACT(HOUR FROM zaman_damgasi) AS saat,
    TO_CHAR(zaman_damgasi, 'Day') AS gun,
    EXTRACT(WEEK FROM zaman_damgasi) AS hafta
FROM {{ source('kaynak', 'zamanlar') }}



--Fact Tablolar: - fact_hiz_ihlali: segment_id, zaman_damgası,
-- arac_tipi_id, hiz_ihlali (veya ihlal_flag), [diğer metrikler]
-- - fact_eds_arac_gecis: segment_id, zaman_damgası, arac_tipi_id,
-- hiz (EDS’nin tespit ettiği tüm araçlar ve hızları)

{{ config(materialized='table') }}

SELECT
    ihlal_id,
    segment_id,
    zaman_damgasi,
    arac_tipi_id,
    hiz_ihlali
FROM {{ source('kaynak', 'hiz_ihlalleri') }}

{{ config(materialized='table') }}

SELECT
    gecis_id,
    segment_id,
    zaman_damgasi,
    arac_tipi_id,
    hiz
FROM {{ source('kaynak', 'eds_arac_gecisleri') }}

 --fact_hiz_ihlali (N) — (1) dim_arac_tipi
--- fact_hiz_ihlali (N) — (1) dim_zaman

{{ config(materialized='view') }}

SELECT
    f.segment_id,
    s.segment_adi,
    f.zaman_damgasi,
    z.gun,
    f.arac_tipi_id,
    a.arac_tipi_adi,
    f.hiz_ihlali
FROM {{ ref('fact_hiz_ihlali') }} f
JOIN {{ ref('dim_segment') }} s ON f.segment_id = s.segment_id
JOIN {{ ref('dim_zaman') }} z ON f.zaman_damgasi = z.zaman_damgasi
JOIN {{ ref('dim_arac_tipi') }} a ON f.arac_tipi_id = a.arac_tipi_id


--Intermediate (ara) katmanda, bu ham veriler üzerinde iş kuralları uygulanır, 
--hesaplamalar (ör. brüt kâr, indirimli tutar) ve zenginleştirmeler yapılır.
--tarihlere saatlere günlere ayırmak iş kuralı 
--Bu katman, özet raporlar ve analizler için veri hazırlar.


--En fazla hız ihlali yapılan segmentler (ilk 5)
--Zaman aralığına göre (gün, saat) hız ihlali dağılımı
--Segment bazında hız ihlali yapan araç sayısı


{{ config(materialized='table') }}

SELECT
    segment_id,
    COUNT(*) AS toplam_hiz_ihlali
FROM {{ ref('fact_hiz_ihlali') }}
GROUP BY segment_id
ORDER BY toplam_hiz_ihlali DESC
LIMIT 5


{{ config(materialized='table') }}

SELECT
    DATE_TRUNC('day', zaman_damgasi) AS gun,
    EXTRACT(HOUR FROM zaman_damgasi) AS saat,
    COUNT(*) AS hiz_ihlali_sayisi
FROM {{ ref('fact_hiz_ihlali') }}
GROUP BY gun, saat
ORDER BY gun, saat



{{ config(materialized='table') }}

SELECT
    segment_id,
    COUNT(DISTINCT arac_tipi_id) AS hiz_ihlali_yapan_arac_turu_sayisi
FROM {{ ref('fact_hiz_ihlali') }}
GROUP BY segment_id
ORDER BY hiz_ihlali_yapan_arac_turu_sayisi DESC


--marts
{{ config(materialized='view') }}

SELECT
    f.segment_id,
    s.segment_adi,
    f.zaman_damgasi,
    z.gun,
    z.saat,
    f.arac_tipi_id,
    a.arac_tipi_adi,
    COUNT(*) AS toplam_hiz_ihlali
FROM {{ ref('fact_hiz_ihlali') }} f
JOIN {{ ref('dim_segment') }} s ON f.segment_id = s.segment_id
JOIN {{ ref('dim_zaman') }} z ON f.zaman_damgasi = z.zaman_damgasi
JOIN {{ ref('dim_arac_tipi') }} a ON f.arac_tipi_id = a.arac_tipi_id
GROUP BY
    f.segment_id,
    s.segment_adi,
    f.zaman_damgasi,
    z.gun,
    z.saat,
    f.arac_tipi_id,
    a.arac_tipi_adi
ORDER BY toplam_hiz_ihlali DESC



NOT
--Foreign key, genellikle fact tablolarda bulunur ve dimension tablolara referans verir.

--stg_crm_sales tablosu bir fact (olay/veri) tablosudur; 
--çünkü satış işlemlerini (transaction) tutar ve product_id, customer_id gibi foreign key’lerle dimension tablolara bağlanır.


--Dimension tablolar ise genellikle açıklayıcı (referans) bilgileri tutar (ör. ürünler, müşteriler, bölgeler).,
--Dimension tablolar, genellikle açıklayıcı bilgileri (ürün adı, kategori, marka, tedarikçi vb.) tutar ve bazen başka dimensionlara referans verebilir.


