# 🏇 RacePredict-AI

RacePredict-AI is an advanced, machine-learning-powered Django application designed for forecasting horse race outcomes. By utilizing historical race data (1990-2020) and a trained XGBoost model, this system delivers predictive analytics and high-performance metrics through a sleek, professional web interface.

![RacePredict-AI Demo](video/RacePredict-AI.webm)

## ✨ Features

- **Machine Learning Engine**: Employs an XGBoost model (`xgboost_model.pkl`) alongside specialized categorical encoders (`encoders.pkl`) to predict race outcomes and probabilities accurately based on historical metrics.
- **Automated Data ETL Pipeline**: Features an automated Kaggle data ingestion script (`import_kaggle.py`) to systematically populate thousands of horses, jockeys, trainers, and historical races directly into the database.
- **Premium User Interface**: Sports a clean, premium Dark Mode aesthetic with a fully mobile responsive layout.
- **Advanced Race Center**: Features a dynamic, searchable dropdown for race selection using *Choices.js*.
- **Interactive Visualizations**: Implements rich data visualizations seamlessly through *Chart.js*.
- **Comprehensive Data Exploration**: Allows users to delve deeply into race metadata, viewing comprehensive stats like jockey performance, weight carried, official ratings, and racing class in a smooth, scrollable modal layout.

## 🛠️ Technology Stack

- **Backend**: Python (>=3.14), Django (>=5.1)
- **Machine Learning**: XGBoost, Scikit-Learn, Pandas, Numpy, Joblib
- **Database**: PostgreSQL (via `psycopg2-binary`) or SQLite
- **Package Management**: Astral's `uv` tool
- **Frontend**: HTML5, Vanilla JS, CSS3, Chart.js, Choices.js

## 🚀 Getting Started

### Prerequisites
Before setting up the project locally, guarantee you have:
- Python 3.14 or higher
- The `uv` package manager installed
- PostgreSQL (or alternative backend) installed

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mayurkmmt/RacePredict-AI.git
   cd RacePredict-AI
   ```

2. **Configure Environment variables:**
   Copy the `.env.example` template to quickly configure `.env`:
   ```bash
   cp .env.example .env
   ```
   Fill in your local connection details (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `SECRET_KEY`, etc.).

3. **Install Dependencies:**
   The project uses `uv` for highly-optimized dependency management. Install the necessary packages via the lockfile or pyproject definitions:
   ```bash
   uv sync
   ```

4. **Initialize Database Schema:**
   Apply Django's ORM operations to construct necessary tables:
   ```bash
   uv run python manage.py migrate
   ```

5. **Import Historical Reference Data:**
   Deploy the pre-written custom management command to process and ingest Kaggle CSV datasets.
   *(Note: This ETL pipeline parses 30+ years of historical data row-by-row and may take a significant amount of time [approx. 1 hr+])*
   ```bash
   uv run python manage.py import_kaggle
   ```

6. **Ignite the Server:**
   Deploy the fast development web server locally:
   ```bash
   uv run python manage.py runserver
   ```
   The application dashboard will be successfully listening at `http://127.0.0.1:8000/`.

## 🧠 Machine Learning Flow

The prediction core relies on curated historical datasets evaluating variables such as horse pedigree, handicap weight distributions, recent jockey success ratios, and variations in track terrain condition. The resulting weights (`xgboost_model.pkl`) and necessary data transformers (`encoders.pkl`) are pre-packaged at the root architectural level for real-time application inference upon startup.
