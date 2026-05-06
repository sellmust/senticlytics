# 🐳 Docker — Setup & Configuration

Documentation for Docker usage in the Customer Feedback Intelligence Platform. All components run as containers connected within a single Docker network.

---

## 🖼️ Running Containers

| Container | Image | Tag | Port |
|-----------|-------|-----|------|
| FastAPI App | `customer_feedback_` | `latest` | `8000` |
| PostgreSQL | `postgres` | `15-alpine` | `5432` |
| Qdrant | `qdrant/qdrant` | `latest` | `6333` |
| n8n | `n8nio/n8n` | `latest` | `5678` |
| Redis | `redis` | `7-alpine` | `6379` |

---

## 📁 Configuration Files

```
project/
├── docker-compose.yml
├── Dockerfile
└── .env
```

---

## 🔧 Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## 🗂️ docker-compose.yml

```yaml
version: '3.8'

services:

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://feedbackuser:feedbackpass@postgres:5432/feedback_db
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GEMINI_MODEL=gemini-2.5-flash
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_started
    networks:
      - feedback_network
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=feedbackuser
      - POSTGRES_PASSWORD=feedbackpass
      - POSTGRES_DB=feedback_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U feedbackuser -d feedback_db"]
      interval: 5s
      retries: 5
    networks:
      - feedback_network

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - feedback_network

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=password
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - feedback_network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - feedback_network

volumes:
  postgres_data:
  qdrant_data:
  n8n_data:
  redis_data:

networks:
  feedback_network:
    driver: bridge
```

---

## 🔗 Inter-Container Communication

All containers share `feedback_network` and communicate via **service names**:

| From | To | Hostname |
|------|----|---------|
| FastAPI | PostgreSQL | `postgres:5432` |
| FastAPI | Qdrant | `qdrant:6333` |
| n8n | FastAPI | `backend:8000` |

---

## 🚀 How to Run

### Via VSCode
Right-click `docker-compose.yml` → **Compose Up**

### Via Terminal
```bash
docker-compose up --build        # build and start
docker-compose up -d --build     # background
docker-compose logs -f backend   # follow FastAPI logs
docker-compose down              # stop (keep data)
docker-compose down -v           # stop + delete volumes
```

---

## 📦 .env

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.3
DATABASE_URL=postgresql://feedbackuser:feedbackpass@postgres:5432/feedback_db
QDRANT_HOST=qdrant
QDRANT_PORT=6333
VECTOR_COLLECTION_NAME=feedback_embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TOP_K=5
FASTAPI_PORT=8000
FASTAPI_WORKERS=2
LOG_LEVEL=INFO
```

---

## 🔁 Startup Order

```
1. PostgreSQL → health check (pg_isready)
2. Qdrant
3. Redis
4. FastAPI (after Postgres healthy)
   ├── init_db()       — create tables
   └── RAGPipeline()   — connect Qdrant + load embedding model
5. n8n
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend can't reach postgres | `docker-compose restart backend` |
| RAG init fails | `curl http://localhost:6333/health` |
| Port conflict | Change port in `docker-compose.yml` |
| `GEMINI_API_KEY not set` | Check `.env` exists in project root |