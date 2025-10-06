# 🧠 Text2SQL Analytics System

A Django-based **Text-to-SQL Analytics System** that converts natural language (English) questions into SQL queries using **Google Gemini API** and executes them against a PostgreSQL database.

The system returns accurate, safe, and optimized SQL results while enforcing SQL sanitization and validation.

---

## 🏗️ Project Overview

**Goal:** Enable users to interact with databases using natural language instead of manual SQL writing.

**Core Features:**
- Natural Language → SQL conversion (Gemini API)
- Secure SQL execution (sanitized & validated)
- Django REST API endpoint for execution
- Configurable database connection

---

## 🧩 Architecture Diagram

```
User → Django REST API (/api/text2sql/) → Gemini API → SQL Generator
         ↓                                                      ↑
   PostgreSQL ← Query Executor ← SQL Sanitizer ←──────────────┘
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/text2sql.git
cd text2sql
```

### 2️⃣ Create a virtual environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Create a `.env` file in the `config/` folder

```ini
DJANGO_SECRET_KEY='your-secret-key-here'
DEBUG=True
DATABASE_NAME='your-database_name-here'
DATABASE_USER='database_user'
DATABASE_PASSWORD='your-password-here'
DATABASE_HOST='localhost'
GEMINI_API_KEY='your-gemini-api-key-here'
```



---

## 🗄️ Database Initialization Guide

1. **Make sure PostgreSQL is installed and running**

2. **Create a new database and add it to the .env:**

3. **Run Django migrations:**

```bash
python manage.py makemigrations
python manage.py migrate
```

4. **(Optional) Create a superuser:**

```bash
python manage.py createsuperuser
```

---

## 🔑 API Key Configuration

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a Gemini API key
3. Add it to your `.env` file:

```ini
GEMINI_API_KEY='your_actual_api_key_here'
```

---

## 🚀 Run the Server

```bash
python manage.py runserver
```

The app will be live at **http://127.0.0.1:8000/**

---

## 💬 API Endpoint

### `POST /api/text2sql/`

**Description:** Converts a natural language query into an SQL query and executes it on your PostgreSQL database.

#### Request Example:

```json
{
  "nl_query": "give me the employees who are sales representative"
}
```

#### Response Example:

```json
{
    "sql": "SELECT \"employeeName\" FROM \"employees\" WHERE \"title\" = 'Sales Representative' LIMIT 1000",
    "rows": [
        {
            "employeeName": "Nancy Davolio"
        },
        {
            "employeeName": "Janet Leverling"
        },
        {
            "employeeName": "Margaret Peacock"
        },
        {
            "employeeName": "Michael Suyama"
        },
        {
            "employeeName": "Robert King"
        },
        {
            "employeeName": "Anne Dodsworth"
        }
    ],
    "meta": {
        "runtime_s": 1.1754207611083984,
        "row_count": 6
    }
}
```

#### Error Response Example:

```json
{
  "error": "Invalid SQL query generated"
}
```


## ⚠️ Known Limitations

- Free Gemini API may have rate limits
- SQL generation accuracy may vary with complex joins
- Currently supports PostgreSQL only
- No query result caching implemented yet

---

## 🚀 Future Improvements

- [ ] Add multi-database support (MySQL, SQLite)
- [ ] Implement model fine-tuning for specific schema awareness
- [ ] Add caching layer for frequently asked queries
- [ ] Integrate with Streamlit for interactive dashboards
- [ ] Add query history and analytics
- [ ] Implement role-based access control
- [ ] Add support for data visualization

---