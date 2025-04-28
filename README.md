⚽ TeamBalancer - Football Team Generator Based on Player Ratings ⚡
Welcome to TeamBalancer, the web app that takes the hassle out of creating fair football teams! 🏆
With the power of genetic algorithms and live performance ratings, we build two balanced squads every time — so the only thing you’ll have to worry about is your first touch! 🚀

🎯 Project Overview
TeamBalancer dynamically generates two football teams based on players' ratings, which are influenced by their performance in recent matches. No more debates about unfair teams — let data and smart algorithms do the heavy lifting! 💪

Key features:

🧠 Genetic Algorithm optimization for fair team distribution

📝 Dynamic rating system based on 5 latest match performances

⚡ FastAPI + Pydantic backend (Pythonic, modern and FAST)

🛢️ SQLAlchemy for seamless database operations

🎯 Intelligent validation (equal defenders, 1 goalkeeper per team, and balanced top-rated players)

🛠️ Tech Stack

Layer	Tech
Backend	Python, FastAPI, Pydantic
ORM / Database	SQLAlchemy, SQLite / PostgreSQL
AI / Algorithm	DEAP (Distributed Evolutionary Algorithms in Python)
Data Handling	Pandas
🧬 How It Works
Load Player Data ➡️

Read players from an Excel file: Name, Position, Rating (Value), and Recent Grades.

Select Players ➡️

Randomly pick 1414 players (2 goalkeepers + 10/12 others).

Normalize Values ➡️

Prepare players' ratings and form data for fairness.

Apply Genetic Algorithm ➡️

Evolve hundreds of possible combinations to find the most balanced split.

Validate ➡️

Each team must have:

At least one Goalkeeper 🧤

Equal number of Defenders 🛡️

Fair distribution of high-rated players 🌟

The final result: Two balanced teams, ready to battle it out! ⚡⚽

📦 Installation
Clone the repo:

git clone https://github.com/Florin14/football_tracking_be.git
cd git clone https://github.com/Florin14/football_tracking_be.git
Install dependencies:

pip install -r requirements.txt
