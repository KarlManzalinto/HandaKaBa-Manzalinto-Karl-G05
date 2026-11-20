# Handa Ka Ba
A home emergency preparedness system that helps Filipino households keep their emergency kits (go-bags) complete and up to date.
**CSIT327 - Information Management 2 | Section G05**
Developed by Karl Augustus V. Manzalinto
---
## About the Project
Many households pack an emergency kit once and then forget about it, so food, water, and medicine expire or run low before a typhoon or earthquake. Handa Ka Ba lets each household track what is inside their go-bag, how much they have, and when each item expires.
---
## Core Feature: Go-Bag Inventory
Project Development 2 - a full vertical slice from the database to the user interface.
| Feature | Description |
|---|---|
| Add items | Log each item with category, name, quantity, unit, expiry date, and notes |
| View, search, and filter | Search items and filter by category or expiry status |
| Edit items | Update quantities or expiry dates |
| Delete items | Remove items after a confirmation page |
| Expiry tracking | Each item shows Good, Expiring in 30 days, Expired, or No expiry |
| Readiness dashboard | Readiness score, items expiring soon, a needs-attention list, and a household-size checklist |
| Admin overview | Admins can view all households' items, delete inappropriate entries, and see overall totals |
### Validation Rules
- Category, item name, quantity, and unit are required
- Quantity must be between 1 and 9,999
- Expiry dates cannot be in the past for new items
- No duplicate items in the same category
- Each item is linked to its owner, and users can only see and edit their own items
### Starter Categories
Water, Food, Medicine, Light / Power, and Documents. These are added automatically when you run the migrations.
---
## User Roles
| Role | Access |
|---|---|
| Household User | Add, view, search, edit, and delete their own items, and track readiness on their dashboard |
| Administrator | View all households' inventory, delete inappropriate items, and see totals on the admin dashboard |
---
## Standard Features (Project Development 1)
- Account Registration
- Login / Logout
- Role-Based User Dashboard
- User Profile (view and edit)
---
## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Django 5.2 (Python) |
| Database | PostgreSQL (Supabase) |
| Frontend | Django Templates and CSS |
---
## Setup
1. Clone the repository
```bash
git clone https://github.com/KarlManzalinto/HandaKaBa-Manzalinto-Karl-G05.git
cd HandaKaBa-Manzalinto-Karl-G05
```
2. Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```
On Mac/Linux, use `source venv/bin/activate`.
3. Install dependencies
```bash
pip install -r requirements.txt
```
4. Set up environment variables
```bash
copy .env.example .env
```
Open `.env` and add your Supabase `DATABASE_URL`.
5. Create the database tables
```bash
python manage.py migrate
```
6. Create an admin account (superusers automatically get the Administrator role)
```bash
python manage.py createsuperuser
```
7. Run the server
```bash
python manage.py runserver
```
Open http://127.0.0.1:8000/. Register an account to become a Household User, then click **My inventory** in the sidebar.
---
## Running Tests
```bash
python manage.py test inventory
```
Your database user must be allowed to create a test database.
---
## Project Structure
```
HandaKaBa-Manzalinto-Karl-G05/
├── accounts/      Registration, login, profiles, dashboards
├── inventory/     Go-bag inventory core feature
├── templates/     Base layout and dashboards
├── handakaba/     Settings, URLs, static files
├── docs/          Project reports
├── requirements.txt
└── manage.py
```
