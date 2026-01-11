# TeamBalancer - Football Team Generator

TeamBalancer builds fair football teams based on player ratings and recent performance.
It uses a genetic algorithm to create two balanced squads.

## Features
- Genetic algorithm optimization for fair team distribution
- Dynamic rating system based on recent match performance
- FastAPI backend with SQLAlchemy
- Validation rules (goalkeeper count, defender balance, top-rated distribution)

## Tech Stack
- Backend: Python, FastAPI, Pydantic
- ORM / Database: SQLAlchemy, SQLite / PostgreSQL
- AI / Algorithm: DEAP
- Data Handling: Pandas

## Installation
Clone the repo:
```
git clone https://github.com/Florin14/football_tracking_be.git
cd football_tracking_be
```

Install dependencies:
```
pip install -r requirements.txt
```

## Environment
Server (default):
- APP_ENV=production
- DATABASE_URL=postgresql://...

Local (use local DB):
- APP_ENV=local
- DATABASE_URL_LOCAL=postgresql://postgres:postgres@localhost:5432/football_tracking_be

You can also use POSTGRESQL_LOCAL_* vars if you prefer split config.

## Run
```
uvicorn services.run_api:api --host 0.0.0.0 --port 8000 --reload
```
