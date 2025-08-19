# Baby Milk Tracker

- A lightweight web application to record, visualize, and analyze baby feeding logs.
- Built with FastAPI (backend, SQLite persistence) and a vanilla HTML/CSS/JS frontend.
- The goal is to provide an easy tool for parents to keep track of their baby's milk intake and daily feeding schedule.

## Features

- Daily & weekly charts: stacked bar chart of milk types (breast milk, pre, sct).

- Feeding logs: add, list, and delete individual feedings with time, amount, and type.

- Quick input: prefilled current date & time, with +10/−10/+1/-1 ml buttons for faster entry.

- Aggregates: totals and averages by week, month, and year.

- Interactive navigation: scroll through history, 7 days visible at a time.

- Data management: wipe/reset endpoint for starting fresh.

## Tech Stack

- Backend: FastAPI

- Database: SQLite via SQLAlchemy ORM

- Frontend: Static HTML, CSS, and vanilla JavaScript with Chart.js

## Current Status

- Core API (CRUD for feedings) complete.

- Interactive frontend with chart + feeding list.

- Local persistence in milk.db.

## How to Run Locally

- Clone the repo and install requirements:

+ git clone https://github.com/<your-username>/baby-milk-tracker.git
+ cd baby-milk-tracker/web
+ pip install -r requirements.txt


- Start the backend:
+ uvicorn app:app --reload


- Then open http://127.0.0.1:8000 in your browser.

## Deployment

- This project is ready to deploy on Render or any FastAPI-compatible service.
- Static files are served under /static.

## License

- MIT — feel free to use, modify, and share.