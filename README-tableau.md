# 📊 Tableau — Customer Feedback Dashboard

Documentation for the Customer Feedback Intelligence Platform data visualization in **Tableau Desktop**, connected to PostgreSQL and based on 15 feedbacks submitted via `test.sh`.

---

## 🔗 Data Source Connection

| Parameter | Value |
|-----------|-------|
| Host | `localhost` |
| Port | `5432` |
| Database | `feedback_db` |
| Username | `feedbackuser` |
| Table | `feedback` |

Alternative: import CSV from `GET /api/v1/feedback/report/export` for offline analysis.

---

## 📋 Fields Used from PostgreSQL

| Tableau Field | DB Column | Description |
|--------------|-----------|-------------|
| `Id` | `id` | Unique identifier |
| `Sentiment` | `sentiment` | positive / neutral / negative |
| `Sentiment Respon` | `sentiment_respon` | AI-generated response text |
| `Category` | `category` | Aspect provided by user |
| `Rating` | `rating` | 1–5 stars |
| `Sentiment Score` | *Calculated* | 1 / 0 / -1 for plotting |
| `CSAT Score` | *Calculated* | % positive of total |
| `Created At` | `created_at` | Timestamp |

---

## 📐 Dashboard: Customer Feedback Overview

<img width="1366" height="768" alt="Dashboard - Customer Feedback Overview" src="https://github.com/user-attachments/assets/0140fb86-a49b-4037-b126-bb19bb37d388" />

### 1. KPI — Total Feedback
**Metric:** `COUNT([Id])` → **15**

Total responses collected: 11 on May 1, 4 on May 2.

---

### 2. KPI — CSAT Score

**Calculated Field:**
```
COUNTD(IF [Sentiment] = 'positive' THEN [Id] END) /
COUNTD([Id]) * 100
```

Result: **40.0%** — below the 60% target, shown in red with a down arrow.

---

### 3. KPI — AVG Rating

**Formula:** `AVG([Rating])` → **3.0 / 5.0**

---

### 4. Bar Chart — Category Distribution

**Dimension:** `[Category]`
**Measure:** `COUNTD([Id])` as percentage
**Color:** `[Sentiment]`

```
product_quality      pos 18.18% | neu 9.09% | neg 18.18%
price                pos 9.09%  | neg 9.09%
packaging            pos 9.09%
delivery             neg 9.09%
customer_service     neg 18.18%
```

Key insights:
- `product_quality` and `customer_service` have the highest negative rates
- `customer_service` has zero positive feedback
- `packaging` is entirely positive

---

### 5. Scatter Plot — Rating vs Sentiment Score

**X-axis:** `[Rating]` (1–5)
**Y-axis:** `[Sentiment Score]` — Calculated Field:
```
IF [Sentiment] = 'positive' THEN 1
ELSEIF [Sentiment] = 'neutral' THEN 0
ELSE -1
END
```
**Size:** `COUNT([Id])` — larger bubble = more feedbacks at that point
**Color:** `[Sentiment]`

Reading the chart:
- Large red bubbles at rating 1–3 = concentration of dissatisfaction at low ratings
- Large teal bubble at rating 5 = highly satisfied customers giving max rating
- Neutral gray dots cluster near rating 3–4

---

## 🎨 Color Guide

| Color | Hex | Used For |
|-------|-----|----------|
| Teal | `#5FADA0` | Positive |
| Gray | `#A0A0A0` | Neutral |
| Pink/Red | `#E87F7F` | Negative |
| Red | `#DC2626` | CSAT below target |
| Background | `#F5F0EB` | Dashboard |

---

## 🔍 Available Filters

| Filter | Type |
|--------|------|
| Date Range | Date picker (`created_at`) |
| Sentiment | Multi-select |
| Category | Multi-select |
| Rating | Slider |

---

## 📈 Key Insights (15 Feedbacks)

1. CSAT 40% is far below the e-commerce benchmark of 60–80%
2. `customer_service` is the most critical category — zero positive feedback
3. `packaging` is the strongest area — all positive
4. Rating 3.0 and CSAT 40% are consistent — moderate satisfaction
5. Scatter plot shows a clear correlation: high rating → positive sentiment
