# Noi Tro AI

## Overview

"Noi Tro AI" - Smart Vietnamese home cooking assistant powered by Django and Gemini AI.

## Stack

- **Backend**: Django 5.2 (Python 3.11)
- **Frontend**: HTML, CSS (Bootstrap 5), JavaScript
- **Database**: SQLite (development), PostgreSQL (production via DATABASE_URL)
- **AI**: Google Gemini via Replit AI Integrations
- **Static files**: WhiteNoise

## Project Structure

```
/
├── manage.py
├── seed_data.py
├── noi_tro_ai/          # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── app/                 # Main Django app
    ├── models.py        # UserProfile, Food, MealPlan, NutritionLog, ChatMessage
    ├── views.py         # Page views + API endpoints
    ├── urls.py          # URL routing
    ├── templatetags/
    │   └── custom_filters.py
    ├── templates/app/   # HTML templates (Bootstrap 5)
    │   ├── base.html
    │   ├── dashboard.html
    │   ├── chat.html
    │   ├── meal_plans.html
    │   ├── nutrition.html
    │   ├── foods.html
    │   └── profile.html
    └── static/          # Static CSS/JS files
```

## Key Commands

- `python3 manage.py runserver 0.0.0.0:8000` — run dev server
- `python3 manage.py makemigrations` — create migrations
- `python3 manage.py migrate` — apply migrations
- `python3 seed_data.py` — seed food database

## Features

- Dashboard with nutrition overview
- AI chat assistant (Gemini) for meal suggestions
- Meal planning calendar
- Nutrition tracking with charts
- Food database with search/filter
- Health profile management

## URL Routes

- `/` — Dashboard
- `/chat/` — AI chat
- `/thuc-don/` — Meal plans
- `/theo-doi/` — Nutrition tracking
- `/mon-an/` — Food database
- `/ho-so/` — Health profile
