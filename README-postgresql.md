# 🗄️ PostgreSQL — Database Workflow

Documentation for the database layer, focused on the `feedback` table — the primary store for all feedback entries and AI-generated results.

---

## 🔗 Connection Config

| Parameter | Value |
|-----------|-------|
| Host (Docker internal) | `postgres` |
| Host (from host machine) | `localhost` |
| Port | `5432` |
| Database | `feedback_db` |
| Username | `feedbackuser` |
| Password | `feedbackpass` |

The backend uses an **async engine** (`postgresql+asyncpg://`) for all FastAPI endpoints.

---

## 📊 The `feedback` Table

```sql
CREATE TABLE feedback (
    id               SERIAL PRIMARY KEY,

    -- Content
    text             TEXT NOT NULL,

    -- Input Metadata (from user/test.sh)
    customer_id      VARCHAR(100),
    product_id       VARCHAR(100),
    source           VARCHAR(50)  DEFAULT 'web',
    category         VARCHAR(100),          -- provided by user on submit
    rating           INTEGER CHECK (rating BETWEEN 1 AND 5),

    -- AI Results (auto-filled by Gemini)
    sentiment        sentiment_type NOT NULL,  -- positive / neutral / negative
    sentiment_respon TEXT,                     -- personalized response from Gemini

    -- Flags
    is_verified      BOOLEAN DEFAULT FALSE,
    is_spam          BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at       TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sentiment_created ON feedback (sentiment, created_at);
CREATE INDEX idx_customer_date     ON feedback (customer_id, created_at);
CREATE INDEX idx_product_sentiment ON feedback (product_id, sentiment);
```

---

## 🔄 Data Flow: Request → Database

```
[1] POST /api/v1/feedback
    body: { text, customer_id, product_id, source, rating, category }
        │
        ▼
[2] RAGPipeline.similarity_search(text)
    └── Retrieve similar past feedbacks from Qdrant as context
        │
        ▼
[3] GeminiService.analyze_feedback(text, rag_context)
    └── Returns: { sentiment, sentiment_respon }
        │
        ▼
[4] Build Feedback object
    ├── text, customer_id, product_id, source, rating, category  ← from user
    ├── sentiment                                                  ← from Gemini
    └── sentiment_respon                                          ← from Gemini
        │
        ▼
[5] db.add() + await db.flush()
    └── Row inserted → feedback.id available
        │
        ▼
[6] RAGPipeline.index_feedback(id, text, metadata)
    └── Vector upserted to Qdrant
        │
        ▼
[7] await db.commit()
    └── Transaction finalized
```

If any step fails → `await db.rollback()` → row never saved.

---

## 📝 Sample Data (from test.sh)

| id | sentiment | sentiment_respon (excerpt) | category | rating | created_at |
|----|-----------|---------------------------|----------|--------|-----------|
| 1 | negative | "Kami sangat menyesal atas keterlambatan..." | delivery | 2 | 2025-05-01 |
| 2 | positive | "Terima kasih banyak atas ulasan positif..." | product_quality | 5 | 2025-05-01 |
| 3 | negative | "Kami mohon maaf atas pengalaman buruk..." | customer_service | 1 | 2025-05-01 |
| ... | ... | ... | ... | ... | ... |
| 15 | negative | "Kami memahami kekhawatiran Anda..." | price | 3 | 2025-05-02 |

**Sentiment distribution (15 feedbacks):**
- Positive: 6 records
- Neutral: 3 records
- Negative: 6 records

---

## 🔍 Key Queries

### Sentiment distribution (used by Tableau)
```sql
SELECT
    DATE(created_at) AS date,
    sentiment,
    COUNT(*)         AS total
FROM feedback
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), sentiment
ORDER BY date, sentiment;
```

### CSAT score per day (used by Tableau)
```sql
SELECT
    DATE(created_at) AS date,
    ROUND(
        COUNT(CASE WHEN sentiment = 'positive' THEN 1 END)::numeric
        / COUNT(*)::numeric * 100, 2
    ) AS csat_score
FROM feedback
GROUP BY DATE(created_at)
ORDER BY date;
```

### Category distribution (used by Tableau)
```sql
SELECT
    category,
    COUNT(*)                                                   AS total,
    COUNT(CASE WHEN sentiment = 'positive' THEN 1 END)         AS positive,
    COUNT(CASE WHEN sentiment = 'neutral'  THEN 1 END)         AS neutral,
    COUNT(CASE WHEN sentiment = 'negative' THEN 1 END)         AS negative
FROM feedback
GROUP BY category
ORDER BY total DESC;
```

### All feedbacks for n8n daily export
```sql
SELECT id, customer_id, product_id, rating, text,
       sentiment, sentiment_respon, category, source, created_at
FROM feedback
WHERE created_at >= NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
```

---

## 🗃️ Session Management

```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

Every endpoint gets a fresh session via `Depends(get_db)`.

---

## 💾 Persistence

Data is stored in Docker volume `postgres_data` and survives container restarts. Lost only if `docker-compose down -v` is run.