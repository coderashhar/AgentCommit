# AGENTS.md

## Stack
- Frontend: Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui
- Backend: FastAPI (Python)
- AI: Google ADK + Gemini 2.5 Pro
- Database: PostgreSQL
- Authentication: GitHub OAuth
- Deployment: Vercel + Google Cloud Run

## Conventions
- Use TypeScript on the frontend and Python 3.12+ on the backend.
- Keep components small, reusable, and well-typed.
- Follow feature-based folder organization.
- Use Conventional Commits.
- Write clear comments only where implementation is non-obvious.

## Hard Rules
- Never commit API keys, tokens, or secrets.
- Never use `any` in TypeScript unless explicitly approved.
- Never duplicate logic; extract reusable utilities.
- Never change unrelated files while implementing a feature.
- Never remove existing functionality unless requested.

## Workflow
1. Understand the task before writing code.
2. Propose a short implementation plan.
3. Implement one feature at a time.
4. Run linting and type checks before finishing.
5. Update documentation if behavior changes.

## Living Rules
- Add a new rule here every time the agent repeats a mistake.

## Project History
- Maintain a `PROJECT_HISTORY.md` file at the project root.
- After completing each feature or milestone, append an entry describing:
  - Date
  - Feature implemented
  - Files added or modified
  - Architectural decisions
  - Known issues or follow-up tasks
- Never overwrite previous history; only append new entries.
- Read `PROJECT_HISTORY.md` before starting a new task to understand the current project state.