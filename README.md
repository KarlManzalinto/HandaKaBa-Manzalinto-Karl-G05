# Handa Ka Ba (IM2) - Account Feature

Django + PostgreSQL/Supabase. Roles: Administrator, Household User.

## Setup
```
python -m venv venv
venv\Scripts\activate          # Windows (source venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
copy .env.example .env          # then edit DB settings
python manage.py migrate
python manage.py createsuperuser   # superusers automatically get the Administrator role
python manage.py runserver
```
Open http://127.0.0.1:8000/ - register creates Household Users. 
