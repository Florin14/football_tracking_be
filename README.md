<div align="center">

# ⚽ FC BaseCamp — Backend API

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&pause=1000&color=2E9BFF&center=true&vCenter=true&width=500&lines=Football+Tracking+Platform;FastAPI+%2B+PostgreSQL;Real-time+Match+Management" alt="Typing SVG" />

<br/>

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

<br/>

**Modular REST API for managing football teams, matches, and player statistics.**

[Features](#-features) · [Architecture](#-architecture) · [Getting Started](#-getting-started) · [API](#-api-modules) · [Deployment](#-deployment)

---

</div>

## ✨ Features

<table>
<tr>
<td width="50%">

### 🏟️ Core
- Player management with computed stats
- Team rosters & assignments
- Match scheduling, live scores, goals & cards
- Tournament system (groups + knockout)
- Attendance tracking & training sessions
- League rankings

</td>
<td width="50%">

### 🔧 Platform
- Custom JWT auth (cookie-based, role-based)
- Background jobs (match reminders via APScheduler)
- AI chat agent integration
- Email notifications (SMTP)
- PDF & Excel data export
- Auto-migrations with Alembic

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
src/
├── modules/                 # 16 feature modules
│   ├── auth/                #   Login, logout, refresh tokens
│   ├── player/              #   Player CRUD & stats
│   ├── team/                #   Team management
│   ├── match/               #   Matches, goals, cards
│   ├── attendance/          #   Match & training attendance
│   ├── ranking/             #   League standings
│   ├── tournament/          #   Brackets & formats
│   ├── notifications/       #   Alerts & reminders
│   ├── dashboard/           #   Analytics
│   ├── agent/               #   AI chat assistant
│   └── ...                  #   admin, user, email, reports, training
│
├── extensions/
│   ├── auth_jwt/            # Custom JWT implementation
│   ├── sqlalchemy/          # DB engine & sessions
│   └── migrations/          # Alembic configs
│
├── project_helpers/         # Dependencies, exceptions, responses, schemas
├── services/                # App entrypoint, background jobs
└── constants/               # Enums (roles, positions, match states)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL (or [Neon](https://neon.tech))

### Local Development

```bash
git clone https://github.com/Florin14/football_tracking_be.git
cd football_tracking_be

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Configure .env.local with your DATABASE_URL and AUTHJWT_SECRET_KEY

cd src
uvicorn services.run_api:api --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
cd deploy
docker compose up -d --build
docker compose exec -T -w /app/src api alembic upgrade head
```

> API docs available at `http://localhost:8000/docs`

---

## ⚙️ Environment Variables

```env
# Required
DATABASE_URL=postgresql://user:pass@host:5432/dbname
AUTHJWT_SECRET_KEY=your-secret-key
APP_ENV=production                  # production | local
ALLOWED_ORIGINS=https://your-frontend.com,http://localhost:3000

# Optional — Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
GMAIL_SENDER=your-email@gmail.com

# Optional — Features
OPENAI_API_KEY=sk-...               # AI agent
FRONTEND_URL=https://your-frontend.com
```

---

## 📡 API Modules

| Module | Endpoint | Description |
|:-------|:---------|:------------|
| **Auth** | `/auth/login`, `/auth/refresh-token` | JWT login, refresh, logout |
| **Players** | `/players` | CRUD + computed stats (goals, cards, appearances) |
| **Teams** | `/teams` | Team management & roster assignment |
| **Matches** | `/matches` | Scheduling, scores, goals & cards |
| **Attendance** | `/attendance` | Match & training attendance |
| **Rankings** | `/rankings` | League standings |
| **Notifications** | `/notifications` | Alerts & match reminders |
| **Dashboard** | `/dashboard` | Analytics endpoints |
| **Agent** | `/agent` | AI chat conversations |
| **Admin** | `/admin` | Admin user management |

---

## 🗃️ Database Models

```
Users ◄── Players ──► Teams
              │            │
           Goals      Matches
           Cards     (team1, team2)
              │            │
              └── Attendance ──┘

+ Notifications, ChatConversations, Rankings, Tournaments, TrainingSessions
```

**Migrations:**
```bash
cd src
alembic -c extensions/migrations/alembic.ini upgrade head
```

---

## 🔐 Authentication

Custom JWT-in-cookies system (not `fastapi-jwt-auth`):

- **HS256** signing with access + refresh tokens (8h TTL)
- Cookies: `HttpOnly`, `Secure`, `SameSite=None` (cross-origin)
- Role-based access: **Admin** > **Player**
- Auto token refresh on expiry

---

## 🚢 Deployment

```
Internet ──► Caddy (HTTPS) ──► FastAPI :8000 ──► PostgreSQL (Neon)
```

- **VPS** at `footballtracking.duckdns.org`
- **CI/CD**: GitHub Actions → SSH → `docker compose up`
- **Caddy** handles SSL certificate provisioning

---

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)

</div>
