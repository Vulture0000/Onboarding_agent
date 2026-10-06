# 6. Tools and Technologies Used

## 6.1 Technology Selection Rationale

Each choice below was made against a specific requirement, and the alternatives considered are recorded because the *rejections* are as informative as the selections. The governing constraint was R5: **the system must behave identically when the same request is submitted twice.** That single requirement eliminated most of the obvious technology choices.

| Requirement | Technology | Decision basis |
|---|---|---|
| Deterministic, inspectable workflows with real suspension points | **LangGraph** | Required genuine pause-and-resume across HTTP requests and process restarts. A queue-plus-worker design could do this but adds an infrastructure dependency; LangGraph persists the interrupt as graph state. |
| Durable interrupt state | **langgraph-checkpoint-sqlite** | The approval flow must survive a server restart mid-decision. In-memory state would lose pending approvals on deploy. |
| Policy retrieval | **FAISS** (via LangChain) | Runs in-process. No vector database service, so the prototype starts with one command. |
| Embeddings + generation | **Gemini** (`langchain-google-genai`) | Free tier available, and a hard requirement: the system must run without it. |
| Structured API + dependency injection | **FastAPI** | Pydantic validation is used as a security boundary, not just for typing — it rejects malformed and over-long input before any handler runs. |
| Auth tokens | **PyJWT** | HS256, small, no native build step. |
| Password hashing | **hashlib.pbkdf2_hmac** (stdlib) | **No bcrypt/passlib.** Selected specifically to avoid a native build dependency, so `pip install` never requires a compiler. Cost: 260,000 iterations of pure-Python-adjacent PBKDF2, measured at 21 ms per login in Section 11. |
| Persistence | **SQLAlchemy 2.0 + SQLite** | SQLite keeps the prototype single-process. The ORM layer is deliberately kept portable so Postgres is a URL change. |
| Frontend | **React 18 + Vite + Tailwind** | Fast dev loop; no backend-for-frontend required. |
| Client state | **React Context** for auth only | A full state library was rejected as unnecessary: only the auth token has genuinely global lifetime. |

## 6.2 Backend Stack

| Component | Version | Role |
|---|---|---|
| Python | 3.12.14 | Runtime |
| FastAPI | 0.141.1 | HTTP API, DI, OpenAPI |
| Uvicorn | ≥0.30 | ASGI server |
| LangGraph | ≥0.2.60 | Agent orchestration, interrupts, checkpointing |
| LangChain / langchain-core | ≥0.3 | LLM + retriever abstraction |
| langchain-google-genai | ≥2.0 | Gemini client |
| FAISS | faiss-cpu ≥1.8 | Vector similarity search |
| SQLAlchemy | 2.1.1 | ORM |
| Pydantic | 2.13.5 | Request/response validation |
| PyJWT | 2.15.1 | Token issuing/verification |
| pypdf | ≥4.2 | PDF text extraction |

## 6.3 Frontend Stack

| Component | Version | Role |
|---|---|---|
| React | ^18.3.1 | UI |
| Vite | ^5.4.8 | Build/dev server (1649 modules, ~750 ms build) |
| Tailwind CSS | ^3.4.13 | Styling |
| react-router-dom | ^6.26.0 | Routing + role guards |
| axios | ^1.7.0 | HTTP client with bearer-token interceptor |
| lucide-react | ^0.446.0 | Icons |

## 6.4 Deployment and Tooling

- **Docker Compose** with separate `backend` (uvicorn) and `frontend` (nginx serving the built assets and proxying `/api`) services.
- **Git** — public repository at `github.com/Vulture0000/Onboarding_agent`.
- **`.gitignore`** excludes `.env`, `.venv/`, `*.db`, `node_modules/`, and `dist/`, so no secret or build artifact can be committed by accident. Verified before pushing.

## 6.5 Codebase Size

| Layer | Lines |
|---|---|
| Backend Python (`app/`) | ~4,375 |
| Frontend JS/JSX (`src/`) | ~3,017 |
| **Total** | **~7,400** |

Distribution: 5 agents, 5 tool modules, 1 graph module (state + workflow), 2 RAG modules, 9 API routers, and 18 frontend pages.
