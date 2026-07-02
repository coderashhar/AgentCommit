# 🚀 AgentCommit - AI Open Source Mentor

> **Tagline:** Your AI mentor for open source contributions—from finding the perfect issue to getting your pull request merged.

---

# Project Goal

AgentCommit is a multi-agent AI platform that helps developers contribute to open source with confidence.

Instead of simply recommending GitHub repositories, AgentCommit acts like an experienced mentor that:

- analyzes a developer's GitHub profile
- understands their skills
- recommends suitable repositories
- finds beginner-friendly issues
- explains issues in plain English
- creates an implementation plan
- reviews code and pull requests
- generates professional commit messages
- tracks contribution progress

The entire workflow is powered by specialized AI agents collaborating together.

---

# Target Users

- Students
- First-time contributors
- Hacktoberfest participants
- GSSoC contributors
- Developers wanting to enter open source
- Experienced developers looking for relevant projects

---

# Tech Stack

## Frontend

- Next.js 15 (App Router)
- React
- TypeScript
- TailwindCSS
- shadcn/ui
- Framer Motion
- React Flow (Agent visualization)
- Recharts (Analytics)

---

## Backend

- FastAPI

---

## AI Framework

- Google Agent Development Kit (ADK)

---

## LLM

- Gemini 2.5 Pro

---

## APIs

- GitHub REST API
- GitHub GraphQL API

---

## MCP Servers

- GitHub MCP
- Filesystem MCP
- Browser MCP
- Memory MCP

---

## Database

- PostgreSQL
- Redis (Caching)

---

## Authentication

- GitHub OAuth

---

# High-Level Architecture

```text
                User
                  │
                  ▼
          Coordinator Agent
                  │
───────────────────────────────────────────────
│          │          │         │            │
▼          ▼          ▼         ▼            ▼

Profile    Repo       Issue     Mentor      PR
Agent      Agent      Agent     Agent       Review

│          │          │         │            │

└───────────────┬────────────────────────────┘
                │
                ▼
      Planning Agent
                │
                ▼
     Commit Message Agent
                │
                ▼
      Dashboard / UI
```

---

# Multi-Agent Design

## 1. Coordinator Agent

Responsibilities

- Receive user request
- Route tasks
- Manage workflow
- Aggregate responses
- Handle failures

Input

GitHub username or repository

Output

Final structured response

---

## 2. Profile Analyzer Agent

Responsibilities

- Fetch GitHub profile
- Analyze repositories
- Detect languages
- Detect frameworks
- Detect interests
- Calculate experience level

Output

```json
{
  "languages": [],
  "frameworks": [],
  "experience": "",
  "domains": []
}
```

---

## 3. Repository Recommendation Agent

Responsibilities

Recommend repositories based on:

- skills
- stars
- activity
- technologies
- organization quality

Example

React Developer

↓

Recommend

- React
- Next.js
- Chakra UI
- TailwindCSS
- Vite

---

## 4. Issue Discovery Agent

Responsibilities

Search GitHub for

- good first issue
- help wanted
- beginner friendly
- documentation
- bug

Ranking Factors

- Skill match
- Issue age
- Repository activity
- Difficulty
- Popularity

Output

Top recommended issues

---

## 5. Issue Explainer Agent

Responsibilities

Convert complicated GitHub issues into:

- Plain English
- Required knowledge
- Estimated time
- Difficulty
- Concepts to learn
- Helpful resources

Example Output

Issue Summary

Difficulty

⭐⭐☆☆☆

Estimated Time

2 Hours

Concepts

- React Hooks
- Context API
- Accessibility

---

## 6. Implementation Planner Agent

Responsibilities

Generate

- Files to edit
- Functions involved
- Step-by-step implementation
- Risks
- Edge cases
- Testing strategy

Example

Step 1

Locate Sidebar.tsx

↓

Step 2

Modify keyboard handlers

↓

Step 3

Update tests

↓

Step 4

Run lint

↓

Step 5

Submit PR

---

## 7. Mentor Agent

Acts like a senior developer.

Responsibilities

Explain

- best practices
- design decisions
- code architecture
- coding conventions

Never directly solve everything.

Encourage learning.

---

## 8. PR Review Agent

Input

GitHub Pull Request

Responsibilities

Review

- Code quality
- Performance
- Readability
- Documentation
- Tests
- Best practices

Generate review comments.

---

## 9. Commit Message Agent

Generate Conventional Commits

Examples

```
feat(auth): add GitHub OAuth login

fix(ui): improve sidebar responsiveness

docs(readme): update installation guide
```

---

## 10. Progress Tracking Agent

Tracks

- merged PRs
- repositories
- issues solved
- organizations
- contribution streak
- language usage

Displays analytics dashboard.

---

# User Workflow

```text
User enters GitHub username

↓

Profile Analysis

↓

Skill Extraction

↓

Repository Recommendation

↓

Issue Discovery

↓

Issue Explanation

↓

Implementation Plan

↓

Developer completes work

↓

PR Review

↓

Commit Message

↓

Contribution Analytics
```

---

# Pages

## Landing

- Hero
- Features
- Architecture animation
- CTA

---

## Dashboard

Shows

- Profile summary
- Skills
- Recommended repositories
- Recommended issues
- AI insights

---

## Repository Details

Displays

- Repository overview
- Languages
- Contribution guide
- Open issues

---

## Issue Details

Displays

- AI explanation
- Difficulty
- Estimated effort
- Learning resources
- Implementation plan

---

## PR Review

Upload

- PR URL

Returns

- Review summary
- Suggestions
- Improvements

---

## Analytics

Displays

- Contribution graph
- Languages
- Organizations
- PR history
- Learning roadmap

---

# Security

- OAuth authentication
- No API keys exposed
- Environment variables
- Rate limiting
- Input validation
- Prompt injection filtering
- Secure GitHub token storage

---

# MVP (Phase 1)

- Landing page
- GitHub login
- Profile analysis
- Repository recommendation
- Issue recommendation
- Issue explanation

---

# Phase 2

- Implementation planner
- Commit message generator
- Learning roadmap
- Dashboard

---

# Phase 3

- PR Review Agent
- Repository insights
- Contribution analytics
- Memory

---

# Phase 4

- Team collaboration
- Discord integration
- Slack integration
- VS Code Extension
- Browser Extension

---

# Folder Structure

```text
agentcommit/

├── frontend/
│
├── backend/
│
├── agents/
│   ├── coordinator.py
│   ├── profile_agent.py
│   ├── repo_agent.py
│   ├── issue_agent.py
│   ├── explainer_agent.py
│   ├── planner_agent.py
│   ├── mentor_agent.py
│   ├── pr_review_agent.py
│   ├── commit_agent.py
│   └── analytics_agent.py
│
├── tools/
│   ├── github_tool.py
│   ├── search_tool.py
│   ├── parser.py
│   └── utils.py
│
├── workflows/
│   └── mentor_workflow.py
│
├── mcp/
│   ├── github/
│   ├── filesystem/
│   └── browser/
│
├── api/
│
├── database/
│
├── docs/
│
├── tests/
│
├── .env.example
│
└── README.md
```

---

# Stretch Goals

- AI-generated onboarding plans for first-time contributors
- Automatic repository health scoring
- Personalized learning roadmap based on accepted/rejected PRs
- Repository dependency visualization
- AI-generated architecture diagrams
- GitHub notification assistant
- Issue similarity detection
- AI pair programmer mode
- Resume and LinkedIn contribution generator
- Voice-based mentoring
- Multi-language support

---

# Deliverables

- Fully functional multi-agent application
- Responsive web interface
- Google ADK integration
- MCP server integration
- GitHub OAuth authentication
- Public GitHub repository
- Comprehensive README with architecture diagrams
- Deployment (Frontend + Backend)
- 5-minute demo video
- Kaggle submission write-up

---

# Success Criteria

A user should be able to:

1. Sign in with GitHub.
2. Have their skills automatically analyzed.
3. Receive personalized repository recommendations.
4. Discover beginner-friendly issues that match their experience.
5. Understand complex issues through AI explanations.
6. Receive a step-by-step implementation plan.
7. Get AI feedback on their pull request.
8. Generate high-quality conventional commit messages.
9. Track their open-source growth through an analytics dashboard.

The platform should feel like an experienced open-source mentor guiding the user from their very first contribution to becoming a confident contributor.