#!/bin/bash

API_URL="http://localhost:8000/api/v1/feedback"

echo "🚀 Mengirim 15 review ke API..."

# ========================
# BAHASA INDONESIA (9 review: 4 negatif, 3 positif, 2 netral)
# ========================

# 1. Positif - Kualitas Produk
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Barangnya sangat bagus dan kualitas materialnya premium, jauh di atas ekspektasi saya.",
  "customer_id": "user_001", "product_id": "PROD_A", "rating": 5, "source": "web", "category": "product_quality"
}' &

# 2. Negatif - Pengiriman
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Paket datang terlambat 4 hari dan kardusnya penyok-penyok. Kurirnya tidak ramah sama sekali.",
  "customer_id": "user_002", "product_id": "PROD_B", "rating": 2, "source": "mobile", "category": "delivery"
}' &

# 3. Netral - Harga
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Harga lumayan bersaing tapi fiturnya standar saja, tidak ada yang spesial.",
  "customer_id": "user_003", "product_id": "PROD_C", "rating": 3, "source": "web", "category": "price"
}' &

# 4. Negatif - Customer Service
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Admin chat sangat lambat membalas, saya tanya status refund tidak dijawab sampai sekarang.",
  "customer_id": "user_004", "product_id": "PROD_A", "rating": 1, "source": "chat", "category": "customer_service"
}' &

# 5. Positif - Pengemasan
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Packing sangat aman pakai bubble wrap tebal dan kayu. Seller sangat teliti dan profesional.",
  "customer_id": "user_005", "product_id": "PROD_D", "rating": 5, "source": "web", "category": "packaging"
}' &

# 6. Negatif - Kualitas Produk
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Baru dipakai dua hari sudah rusak, saklarnya tidak berfungsi dengan baik. Sangat mengecewakan.",
  "customer_id": "user_006", "product_id": "PROD_B", "rating": 1, "source": "mobile", "category": "product_quality"
}' &

# 7. Positif - Harga/Nilai
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Sangat worth it dengan harganya yang murah tapi fungsionalitasnya lengkap dan memuaskan.",
  "customer_id": "user_007", "product_id": "PROD_E", "rating": 5, "source": "survey", "category": "price"
}' &

# 8. Netral - Kualitas Produk
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Barang oke sih tapi warnanya agak beda dikit sama yang di foto produk.",
  "customer_id": "user_008", "product_id": "PROD_C", "rating": 4, "source": "web", "category": "product_quality"
}' &

# 9. Negatif - Customer Service
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Pesanan dibatalkan sepihak karena stok habis, padahal di aplikasi tulisannya ready. Sangat tidak profesional.",
  "customer_id": "user_009", "product_id": "PROD_F", "rating": 1, "source": "web", "category": "customer_service"
}' &

# ========================
# BAHASA INGGRIS (6 review: 2 negatif, 2 positif, 2 netral)
# ========================

# 10. Positif - Product Quality
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Installation was super easy and the instructions were crystal clear. Works perfectly right out of the box!",
  "customer_id": "user_009", "product_id": "PROD_G", "rating": 5, "source": "mobile", "category": "product_quality"
}' &

# 11. Positif - Delivery
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Fastest delivery I have ever experienced. Ordered at night and it arrived the next morning. Highly recommended!",
  "customer_id": "user_011", "product_id": "PROD_A", "rating": 5, "source": "web", "category": "delivery"
}' &

# 12. Netral - Customer Service
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "Customer support was responsive but the answers felt copy-pasted and did not really address my specific issue.",
  "customer_id": "user_011", "product_id": "PROD_B", "rating": 3, "source": "chat", "category": "customer_service"
}' &

# 13. Netral - Price
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "The price is reasonable for what you get, nothing extraordinary but it does the job well enough.",
  "customer_id": "user_014", "product_id": "PROD_E", "rating": 3, "source": "web", "category": "price"
}' &

# 14. Negatif - Delivery
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "The courier threw the package over the fence. The item arrived completely broken. Unacceptable service.",
  "customer_id": "user_015", "product_id": "PROD_D", "rating": 1, "source": "survey", "category": "delivery"
}' &

# 15. Negatif - Product Quality
curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d '{
  "text": "The product stopped working after just three days of normal use. Build quality is very disappointing for this price point.",
  "customer_id": "user_010", "product_id": "PROD_C", "rating": 1, "source": "web", "category": "product_quality"
}' &

wait
echo -e "\n✅ Selesai! 15 review terkirim (9 Indonesia + 6 English)."
echo "   Cek log kontainer untuk melihat hasil analisis Gemini."