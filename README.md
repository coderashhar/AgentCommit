# 🚀 AgentCommit — AI Open Source Mentor

> Your AI mentor for open source contributions — from finding the perfect issue to getting your pull request merged.

[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-Gemini%202.5%20Pro-4285F4?logo=google)](https://google.github.io/adk-docs/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What is AgentCommit?

AgentCommit is a **multi-agent AI platform** that helps developers contribute to open source with confidence. Instead of simply recommending repositories, AgentCommit acts like an experienced mentor that:

- 👤 **Analyzes** your GitHub profile to understand your skills
- 📦 **Recommends** repositories matching your tech stack
- 🔍 **Discovers** beginner-friendly issues you can tackle
- 📖 **Explains** complex issues in plain English
- 🎯 **Plans** step-by-step implementation guides
- ✅ **Reviews** your code and pull requests
- 💬 **Generates** professional commit messages
- 📊 **Tracks** your contribution progress

---

## Architecture

```
                User
                  │
                  ▼
          Coordinator Agent
                  │
  ────────────────────────────────
  │       │       │      │      │
  ▼       ▼       ▼      ▼      ▼
Profile  Repo   Issue  Mentor   PR
Agent    Agent  Agent  Agent   Review
  │       │       │      │      │
  └───────────┬─────────────────┘
              │
              ▼
        Dashboard / UI
```

Powered by **Google Agent Development Kit (ADK)** with **Gemini 2.5 Pro**.

---

## Tech Stack

| Layer          | Technology                                    |
|----------------|-----------------------------------------------|
| Frontend       | Next.js 15 · TypeScript · Tailwind CSS · shadcn/ui |
| Backend        | FastAPI · Python 3.12+                        |
| AI Framework   | Google ADK · Gemini 2.5 Pro                   |
| Database       | PostgreSQL · Redis                            |
| Auth           | GitHub OAuth                                  |
| MCP            | GitHub MCP Server                             |
| Deployment     | Vercel (frontend) · Google Cloud Run (backend)|

---

## Getting Started

### Prerequisites

- **Node.js** 18+
- **Python** 3.12+
- **Docker & Docker Compose** (for PostgreSQL & Redis)
- **GitHub OAuth App** ([Create one here](https://github.com/settings/developers))
- **Google API Key** (for Gemini via ADK)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AgentCommit.git
cd AgentCommit
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Start Database Services

```bash
docker compose up -d
```

### 4. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the app.

---

## Project Structure

```
AgentCommit/
├── frontend/                 # Next.js 15 App Router
│   ├── src/
│   │   ├── app/              # Pages & layouts
│   │   ├── components/       # UI components
│   │   ├── lib/              # Utilities & API client
│   │   └── types/            # TypeScript interfaces
│   └── package.json
│
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── agents/           # Google ADK agents
│   │   ├── api/              # REST endpoints
│   │   ├── database/         # SQLAlchemy models
│   │   ├── mcp/              # MCP server integrations
│   │   ├── models/           # Pydantic schemas
│   │   └── tools/            # GitHub API tools
│   └── requirements.txt
│
├── docker-compose.yml        # PostgreSQL + Redis
├── AGENTS.md                 # AI agent guidelines
├── ROADMAP.md                # Full project roadmap
└── PROJECT_HISTORY.md        # Development timeline
```

---

## Contributing

We welcome contributions! Please read our contributing guidelines before submitting a PR.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit using Conventional Commits (`git commit -m "feat: add amazing feature"`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## License

This project is open source under the [MIT License](LICENSE).

---

## Acknowledgments

- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) — Multi-agent framework
- [Gemini 2.5 Pro](https://deepmind.google/technologies/gemini/) — LLM powering the agents
- [shadcn/ui](https://ui.shadcn.com/) — Beautiful component library
- [Framer Motion](https://www.framer.com/motion/) — Animation library