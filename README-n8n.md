# ⚙️ n8n — Workflow Automation

Documentation for the two automation workflows connected to the Customer Feedback Intelligence Platform.

n8n communicates with FastAPI using the **internal Docker hostname**:
```
http://backend:8000/api/v1/...
```

---

## 📋 Workflow 1 — Negative Feedback Real-time Alert

<img width="1295" height="325" alt="image" src="https://github.com/user-attachments/assets/59ee4dfd-1822-4373-83fc-93fd3fad7aa3" />


**Tag:** `feedback-alert`

```
[Check Every 1 Day] → [Fetch New Negative Feedback] → [Create Alert Summary] → [Send Alert Email to Ops Team]
```

### Purpose
Detect new negative feedbacks on a schedule and notify the operations team.

---

### Node 1 — Check Every 1 Day
**Type:** Schedule Trigger (⚡)

Runs automatically every day. Can be shortened to hourly depending on business needs.

---

### Node 2 — Fetch New Negative Feedback
**Type:** HTTP Request (🌐)

| Config | Value |
|--------|-------|
| Method | `GET` |
| URL | `http://backend:8000/api/v1/feedback` |
| Query Params | `sentiment=negative&days=1` |

Fetches all negative feedbacks from the last 24 hours. Response includes `sentiment_respon` — the AI-generated response that Gemini already produced for each feedback.

---

### Node 3 — Create Alert Summary
**Type:** Code Node (`{}`)

Assembles the alert content:

```javascript
const feedbacks = items.map(item => item.json);
const total = feedbacks.length;
const categories = [...new Set(feedbacks.map(f => f.category))];

return [{
  json: {
    total_negative: total,
    categories_affected: categories.join(', '),
    summary_list: feedbacks.map(f =>
      `[${f.category}] Rating ${f.rating}/5\n` +
      `Feedback: ${f.text}\n` +
      `AI Response: ${f.sentiment_respon}`
    ).join('\n\n'),
    generated_at: new Date().toISOString()
  }
}];
```

---

### Node 4 — Send Alert Email to Ops Team

**Type:** Gmail — Send Message (M)

Email includes:
- Total negative feedback count
- Affected categories
- Per-feedback: original text + `sentiment_respon` from Gemini

**🚨 [Alert] 6 New Negative Feedbacks - Friday, May 1, 2026**
<img width="866" height="687" alt="image" src="https://github.com/user-attachments/assets/3bf3c062-fe69-4d2c-8ba0-4a6126a73daf" />

**🚨 [Alert] 2 New Negative Feedbacks - Saturday, May 2, 2026**
<img width="777" height="433" alt="image" src="https://github.com/user-attachments/assets/b226397e-fed8-4ea4-adb3-d5e324b889ed" />

---

## 📊 Workflow 2 — Automated Daily Report to Google Sheets & Email

<img width="1101" height="524" alt="image" src="https://github.com/user-attachments/assets/175859a1-ace7-495f-97d7-4f079d21b7aa" />

**Tag:** `daily-report`

```
                    ┌─[Fetch Yesterday's Statistics]─┐
[Check Every 1 Day]─┤                                 ├─[Prepare Data]─[Siapkan Data]─[Split Out]─┬─[Write to Sheet: Daily Summary]
                    └─[Export All Yesterday's Feedback]┘                                           ├─[Write to Sheet: Feedback Detail]
                                                                                                   └─[Send Report via Email]
```

### Purpose
Automatically create a comprehensive daily report — fetch yesterday's data, write to Google Sheets, and email a summary.

---

### Node 1 — Check Every 1 Day
Ideally scheduled in the morning (e.g., 07:00) so reports are ready when the team starts work.

---

### Node 2a — Fetch Yesterday's Statistics
**Type:** HTTP Request (🌐)

```
GET http://backend:8000/api/v1/feedback/stats/summary?days=1
```

Returns aggregated stats: total, sentiment distribution, category distribution, avg rating.

---

### Node 2b — Export All Yesterday's Feedback
**Type:** HTTP Request (🌐)

```
GET http://backend:8000/api/v1/feedback/report/export?days=1
```

Returns a flat list. Each row includes: `id, customer_id, product_id, rating, text, sentiment, sentiment_respon, category, source, created_at`.

---

### Node 3 — Prepare Data for Google Sheets
**Type:** Code Node (`{}`)

Merges stats + flat export, builds structured object for Sheets.

---

### Node 4 — Siapkan Data untuk Google Sheets
**Type:** Set / Transform Node (`{}`)

Final data type normalization before writing to Sheets.

---

### Node 5 — Split Out
**Type:** Split Out (🔀)

Splits `feedbacks_raw` array into individual items — one row per feedback.

---

### Node 6a — Write to Sheet: Daily Summary
**Type:** Google Sheets — Append

Writes **1 summary row** per day:

### Node 6b — Write to Sheet: Feedback Detail
**Type:** Google Sheets — Append

Each feedback as one row including `sentiment_respon` — so the sheet also captures what the AI said in response to each feedback. This can be used for QA reviews or tone analysis.

Link Spreadsheet: [Daily Summary and Feedbaack Detail](https://docs.google.com/spreadsheets/d/1f1tRc3eC615f-y17RyyoZ5y4WSAa_ojdxsM47KKVFbM/edit?usp=sharing)

### Node 6c — Send Report via Email

**Type:** Gmail — Send Message (M)

Daily email includes: total feedbacks, sentiment distribution, avg rating, top categories, link to Google Sheets.

**📊 Daily Feedback Report — Friday, May 1, 2026**
<img width="629" height="404" alt="image" src="https://github.com/user-attachments/assets/eeca0594-742b-4999-ba12-6e941b456b4c" />

**📊 Daily Feedback Report — Saturday, May 2, 2026**
<img width="750" height="478" alt="image" src="https://github.com/user-attachments/assets/4fc0822b-8e69-4674-b6be-9dab590e7b8c" />

---

## 🔄 Workflow Comparison

| Aspect | Workflow 1 (Alert) | Workflow 2 (Daily Report) |
|--------|-------------------|--------------------------|
| Purpose | Early warning for negatives | Comprehensive daily report |
| Data filter | Negative feedbacks only | All feedbacks from yesterday |
| Includes `sentiment_respon` | Yes — per alert item | Yes — in Feedback Detail sheet |
| Output | Alert email to Ops | Google Sheets + summary email |
| Audience | Operations team | Management / all stakeholders |

---

## 🐳 n8n Container

```yaml
n8n:
  image: n8nio/n8n:latest
  ports:
    - "5678:5678"
  volumes:
    - n8n_data:/home/node/.n8n
    - ./n8n_workflows:/workflows
  networks:
    - cfi_network
```

Access at: `http://localhost:5678`
