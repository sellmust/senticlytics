# 🤖 Gemini LLM & RAG Pipeline

Documentation for the AI layer — covering `gemini_service.py` (Gemini 2.5 Flash) and `rag_pipeline.py` (Qdrant vector store).

---

## Overview

Every feedback goes through two AI components in a specific order:

```
[Feedback Text]
      │
      ▼
[RAGPipeline] ─── similarity_search(text, top_k=5)
      │              └── Retrieve similar past feedbacks from Qdrant
      │              └── Build rag_context string
      ▼
[GeminiService] ─── analyze_feedback(text, rag_context)
      │              └── Classify sentiment
      │              └── Generate personalized sentiment_respon
      ▼
[PostgreSQL]  ─── Save: sentiment + sentiment_respon
      │
      ▼
[RAGPipeline] ─── index_feedback(id, text, metadata)
                   └── Embed + upsert to Qdrant (for future queries)
```

RAG runs **before** Gemini to provide context, then runs **again after** to index the new feedback.

---

## 🔷 Part 1 — Gemini Service

### Configuration

```python
GEMINI_MODEL        = "gemini-2.5-flash"
GEMINI_TEMPERATURE  = 0.3    # low = deterministic, structured JSON output
GEMINI_MAX_TOKENS   = 1024
GEMINI_TOP_P        = 0.95
GEMINI_TOP_K        = 40
transport           = "rest"  # forced REST (not gRPC)
```

Initialized as a **global singleton** via `get_gemini_service()`.

---

### Core Prompts

#### `SENTIMENT_ANALYSIS_PROMPT` — No RAG context
Used when no similar feedbacks are found in Qdrant.

```
You are a customer service response model. Analyze the sentiment of the
following customer feedback. The feedback may be in Indonesian or English.

Based on the sentiment, generate an appropriate, personalized response:
- negative: sincere apology that acknowledges the specific issue + concrete solution
- neutral:  polite thank-you that references the specific feedback content
- positive: warm thank-you that echoes the positive aspects mentioned

The response must feel natural and specific — NOT a generic template.

Return ONLY valid JSON:
{
  "sentiment": "positive" | "neutral" | "negative",
  "sentiment_respon": "<personalized response in same language as feedback>"
}

Feedback: {text}
```

#### `SENTIMENT_WITH_CONTEXT_PROMPT` — With RAG context
Used when similar past feedbacks are found. The `rag_context` block is injected so Gemini generates a response consistent with how similar cases were handled.

```
[same instructions as above, plus:]

Below are similar past feedbacks and how they were handled (for context):
{rag_context}

Based on the sentiment AND the context above, generate a personalized response...
```

---

### `analyze_feedback(text, rag_context)` — Main Method

Called on every `POST /api/v1/feedback`.

```python
async def analyze_feedback(self, text: str, rag_context: Optional[str] = None) -> Dict:
    return await self.analyze_sentiment(text, rag_context=rag_context)
```

**Flow:**
1. Choose prompt based on whether `rag_context` is available
2. Call `_safe_generate(prompt)` → Gemini REST API
3. Strip markdown fences → `_extract_json(raw)` → parse
4. Return `{sentiment, sentiment_respon}`
5. On any failure → `_fallback_sentiment(text)`

**Returns:**
```json
{
  "sentiment": "negative",
  "sentiment_respon": "Kami sangat menyesal mendengar pengalaman buruk Anda. Kami akan segera menghubungi tim logistik untuk menindaklanjuti masalah ini."
}
```

---

### `generate_insights(feedbacks)` — Batch Insights

Called by the n8n pipeline for daily reports. Accepts up to 20 feedbacks.

Input format per feedback:
```
[NEGATIVE | delivery | rating:2] Pengiriman lambat...
```

Returns:
```json
{
  "insights":        [{"title", "description", "impact", "priority"}],
  "recommendations": ["actionable string"],
  "trends":          ["observed pattern"],
  "critical_issues": ["issue needing immediate attention"]
}
```

---

### `_fallback_sentiment(text)` — Fallback

Activated when Gemini is unavailable or returns an error.

```python
def _fallback_sentiment(self, text: str) -> Dict:
    text_lower = text.lower()
    if any(w in text_lower for w in ['bagus', 'good', 'great', 'mantap', 'puas', 'recommended']):
        sentiment = 'positive'
    elif any(w in text_lower for w in ['jelek', 'bad', 'terrible', 'kecewa', 'rusak', 'lambat', 'mahal']):
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    return {
        'sentiment': sentiment,
        'sentiment_respon': 'Terima kasih atas ulasan Anda. Tim kami akan segera menindaklanjuti.'
    }
```

The default `sentiment_respon` is always the same generic template when using fallback — unlike Gemini which generates a unique, personalized response each time.

---

## 🔷 Part 2 — RAG Pipeline

### Configuration

```python
EMBEDDING_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM    = 384
COLLECTION_NAME  = "feedback_embeddings"
CHUNK_SIZE       = 500
CHUNK_OVERLAP    = 100
TOP_K            = 5
MIN_SCORE        = 0.3    # minimum cosine similarity
QDRANT_HOST      = "qdrant"
QDRANT_PORT      = 6333
```

Initialized as a **global singleton** via `get_rag_pipeline()`.

---

### Initialization

```
RAGPipeline.__init__()
    ├── Load SentenceTransformer("all-MiniLM-L6-v2") → dim=384
    ├── Connect QdrantClient(host="qdrant", port=6333, timeout=30)
    └── _initialize_collection()
        └── Create "feedback_embeddings" if not exists
            VectorParams(size=384, distance=COSINE)
```

---

### `similarity_search(query_text, top_k)` — Retrieve Context

Called **before** Gemini on every feedback creation.

```python
def similarity_search(self, query_text: str, top_k: int = 5) -> List[Dict]:
    embedding = self.embedding_model.encode(
        self._preprocess_text(query_text),
        normalize_embeddings=True
    )
    results = self.qdrant_client.search(
        collection_name = COLLECTION_NAME,
        query_vector    = embedding.tolist(),
        limit           = top_k,
        with_payload    = True
    )
    return [r for r in results if r.score >= MIN_SCORE]
```

Each result includes `feedback_id`, `text`, `score`, and metadata payload (sentiment, category, source, customer_id).

---

### `_build_rag_context(similar_feedbacks)` — Format for Gemini

After `similarity_search`, results are formatted into a context string injected into the Gemini prompt:

```python
def _build_rag_context(similar_feedbacks: List[dict]) -> Optional[str]:
    lines = []
    for i, item in enumerate(similar_feedbacks[:5], 1):
        text = item.get('text', '')[:150]
        sentiment = item.get('metadata', {}).get('sentiment', '?')
        lines.append(f"{i}. [{sentiment.upper()}] {text}")
    return "Similar past feedbacks:\n" + "\n".join(lines)
```

Returns `None` if no relevant feedbacks found → Gemini uses `SENTIMENT_ANALYSIS_PROMPT` instead.

---

### `index_feedback(feedback_id, text, metadata)` — Store Vector

Called **after** `db.flush()`, before `db.commit()`.

```python
def index_feedback(self, feedback_id: int, text: str, metadata: Dict) -> str:
    text = self._preprocess_text(text)      # clean + truncate to 512 chars

    embedding = self.embedding_model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True           # L2 normalize for cosine
    )                                       # shape: (384,)

    point = PointStruct(
        id      = int(feedback_id),
        vector  = embedding.tolist(),
        payload = {
            "feedback_id":     feedback_id,
            "text":            text,
            "sentiment":       metadata["sentiment"],
            "category":        metadata["category"],
            "source":          metadata["source"],
            "customer_id":     metadata["customer_id"],
            "indexed_at":      datetime.utcnow().isoformat(),
            "embedding_model": EMBEDDING_MODEL
        }
    )
    self.qdrant_client.upsert(collection_name=COLLECTION_NAME, points=[point])
    return str(feedback_id)
```

---

### Management Methods

| Method | Description |
|--------|-------------|
| `batch_index_feedbacks(list)` | Batch 32 items — used by seed scripts |
| `delete_feedback(id)` | Remove vector from Qdrant |
| `reindex_feedback(id, text, metadata)` | Delete + re-index |
| `get_collection_stats()` | points_count, vectors_count, embedding_dim |
| `health_check()` | Ping Qdrant collection |

---

## 🔗 Full Integration Flow

```
POST /api/v1/feedback
    │
    ├─ RAG: similarity_search(text)          → rag_context (or None)
    │
    ├─ Gemini: analyze_feedback(text, ctx)   → { sentiment, sentiment_respon }
    │
    ├─ db.flush()                            → feedback.id assigned
    │
    ├─ RAG: index_feedback(id, text, meta)   → vector stored in Qdrant
    │
    └─ db.commit()                           → row saved in PostgreSQL
```

The RAG index grows with every new feedback, making future `sentiment_respon` outputs progressively more context-aware and consistent.