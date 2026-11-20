Handa Ka Ba (IM2)
Handa Ka Ba is a web-based home emergency preparedness system for Filipino households. It helps families keep their go-bag (emergency kit) ready by tracking what is inside it, how much of each item they have, and when items expire.
Built with Django and PostgreSQL/Supabase. Roles: Administrator and Household User.
Core Feature: Go-Bag Inventory (Project Development 2)
Household users record every item in their go-bag and keep it up to date.
Add items with category, name, quantity, unit, expiry date and notes
View, search and filter items by category or expiry status (Expired, Expiring in 30 days)
Edit and delete items, with a confirmation page before deleting
Expiry status on every item: Good, expiring within 30 days, Expired, or No expiry
Household dashboard shows a readiness score, items expiring soon, a needs-attention list and a checklist based on household size
Administrator can view all households' items on the All inventory page, delete inappropriate entries, and see inventory totals on the admin dashboard
Rules enforced: required fields, quantity from 1 to 9,999, no past expiry dates on new items, and no duplicate items in the same category. Each item is linked to the user who created it, and users can only see and change their own items.
Five starter categories are added automatically by the migrations: Water, Food, Medicine, Light/Power and Documents.
Standard Features (Project Development 1)
Account registration
Login / logout
Role-based dashboards (Household User and Administrator)
User profile (view and edit, including photo, barangay and household size)
Setup
git clone https://github.com/KarlManzalinto/HandaKaBa-Manzalinto-Karl-G05.git
cd HandaKaBa-Manzalinto-Karl-G05
python -m venv venv
venv\Scripts\activate          # Windows (source venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
copy .env.example .env          # then edit DB settings (DATABASE_URL for Supabase)
python manage.py migrate        # creates all tables, including the inventory tables and starter categories
python manage.py createsuperuser   # superusers automatically get the Administrator role
python manage.py runserver
Open http://127.0.0.1:8000/. Registering creates a Household User. Log in and click My inventory in the sidebar to start adding go-bag items.
Running the tests
python manage.py test inventory
Your database user must be allowed to create a test database.
Project Structure
accounts/     registration, login, profiles, role-based dashboards
inventory/    go-bag inventory core feature (models, forms, views, templates, tests)
templates/    base layout and dashboards
handakaba/    project settings, URLs and static files
docs/         project reports (PD2 completion report)
