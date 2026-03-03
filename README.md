# PrayogAI — AI Chatbot Builder Platform

> Build, deploy, and manage AI-powered chatbots trained on your own documents or website content — no ML expertise required.
---
## What is PrayogAI?
PrayogAI lets you turn any business document or website into a smart, conversational chatbot in minutes. Upload your files or point it to a URL, and PrayogAI handles everything — text extraction, vector indexing, and AI-powered question answering. The resulting chatbot can be embedded as a widget on any website.
---
## Core Features
### Chatbot Creation
- **Document Bots** — Upload PDF, DOCX, or TXT files. Each file is processed, chunked, and indexed automatically.
- **Website Bots** — Enter a URL and PrayogAI crawls the entire site, including JavaScript-rendered pages via a Selenium fallback.
- **Instant Responses** — Powered by Google Gemini 2.5 Flash with context pulled from your indexed content (RAG architecture).
### Management
- **Dashboard** — See all your bots, their status, and document count in one view.
- **Document Inspector** — Browse which files and pages are indexed inside each bot.
- **Delete Bots** — Removes both the Supabase record and the Qdrant vector collection cleanly.
### Deployment
- **Embeddable Widget** — Generate a JavaScript snippet after bot creation and paste it into any website. Zero authentication required for end-users.
- **Public Chat API** — The /api/chat endpoint is intentionally open so widgets work on any domain.
### Authentication
- Email/password registration and login via Supabase Auth.
- JWT bearer tokens for all protected API routes.
- Session stored in sessionStorage — cleared on logout or token expiry.
---
## Tech Stack
**Backend**
| | |
|---|---|
| Framework | FastAPI 0.115 (Python 3.11) |
| AI / LLM | Google Gemini API|
| Vectorisation | scikit-learn HashingVectorizer (TF-IDF, 384-dim) — no model downloads |
| Vector Database | Qdrant Cloud |
| Auth and Database | Supabase (PostgreSQL + Auth) |
| Document Parsing | PyPDF2, python-docx, chardet |
| Text Chunking | LangChain RecursiveCharacterTextSplitter |
| Web Crawling | aiohttp + BeautifulSoup (default), Selenium + headless Chrome (JS fallback) |
| Hosting | Render |
**Frontend**
| | |
|---|---|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | TailwindCSS + Framer Motion |
| Routing | React Router v7 |
| HTTP Client | Axios |
| Hosting | Vercel |
---
## How It Works
A document or website is processed, chunked into 1000-character pieces with 200-character overlap, and converted into TF-IDF vectors using scikit-learn's HashingVectorizer. These vectors are stored in a dedicated Qdrant collection for that bot.
When a user sends a message, the query is vectorised the same way, and the top-5 closest chunks are retrieved via cosine similarity. Those chunks are passed as context to Google Gemini 2.5 Flash, which generates a natural-language answer.
No heavy ML model is downloaded. TF-IDF vectors are generated on-the-fly, keeping cold-start times near zero on Render's free tier.
---
## Project Structure

```
prayogai/
├── backend/               FastAPI application (deployed on Render)
│   ├── app/
│   │   ├── api/           Auth + main API routes
│   │   ├── core/          Settings (Pydantic / .env)
│   │   ├── models/        Pydantic request and response models
│   │   ├── services/      AI, auth, bots, chat, vector store, web scraper
│   │   └── utils/         Document processor, JSON encoder, serializers
│   ├── migrations/        Supabase SQL migration files
│   ├── render.yaml        Render deployment config
│   └── requirements.txt
├── frontend/              React + TypeScript SPA (deployed on Vercel)
│   ├── src/
│   │   ├── components/    ChatWidget, Navigation, Modal, AuthForm
│   │   ├── context/       AuthContext (session management)
│   │   ├── lib/           Axios instance, bot API helpers
│   │   └── pages/         Dashboard, CreateBot, BotsList, Login, SignUp
│   ├── public/widget/     Embeddable JS widget
│   └── vercel.json        Vercel SPA rewrite config
└── docker-compose.yml     Local Qdrant instance for development
```


## License
MIT