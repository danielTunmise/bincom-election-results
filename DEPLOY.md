# Deploying to PythonAnywhere (free plan)

Replace `YOURUSERNAME` with your PythonAnywhere username everywhere below.
Your site will be at `https://YOURUSERNAME.pythonanywhere.com`.

## 1. Get the code onto PythonAnywhere
1. Sign up / log in at <https://www.pythonanywhere.com> (free "Beginner" account).
2. Open the **Consoles** tab and start a **Bash** console.
3. Run:
   ```bash
   git clone https://github.com/danielTunmise/bincom-election-results.git
   cd bincom-election-results
   ```

## 2. Create a virtualenv and install Django
Pick a Python version that is available on your account (3.10+ is required by Django 5.2). Example with 3.12:
```bash
mkvirtualenv --python=/usr/bin/python3.12 bincom-venv
pip install -r requirements.txt
```
(`mkvirtualenv` leaves the env active. Later, use `workon bincom-venv` to re-activate it.)

## 3. Build the database and collect static files
```bash
python import_mysql_dump.py
python manage.py collectstatic --noinput
```
You should see the row counts (e.g. `polling_unit 272 rows`) and "Created ...db.sqlite3".

## 4. Create the web app
1. Go to the **Web** tab -> **Add a new web app** -> Next.
2. Choose **Manual configuration** (NOT the "Django" option) and the same Python version as the virtualenv.
3. On the web app page set:
   * **Source code:** `/home/YOURUSERNAME/bincom-election-results`
   * **Virtualenv:** `/home/YOURUSERNAME/.virtualenvs/bincom-venv`
4. In the **Static files** section add:
   * URL: `/static/`  ->  Directory: `/home/YOURUSERNAME/bincom-election-results/staticfiles`

## 5. Edit the WSGI file
On the Web tab click the link to the WSGI configuration file (`/var/www/YOURUSERNAME_pythonanywhere_com_wsgi.py`),
delete everything in it and paste:

```python
import os
import sys

path = "/home/YOURUSERNAME/bincom-election-results"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_SECRET_KEY"] = "put-a-long-random-string-here"   # any long random text
os.environ["DJANGO_DEBUG"] = "0"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
Save it.

## 6. Reload and test
1. On the Web tab click the big green **Reload** button.
2. Open `https://YOURUSERNAME.pythonanywhere.com` and check:
   * Page 1: choose **Uvwie -> Effurun Ii -> effurun 2** -> Show result -> 9 parties, total 3859.
   * Page 2: choose **Uvwie** -> calculated column 3047 / 2673 / 2061 ... total 20420.
   * Page 3: add a test unit and confirm the success message and result page.
   * The page is styled (green nav bar). If it looks unstyled, re-check the static files mapping in step 4.

## Troubleshooting
* **"Something went wrong" page:** Web tab -> *Error log*.
* **DisallowedHost error:** the app already allows `.pythonanywhere.com`; for a custom domain set `DJANGO_ALLOWED_HOSTS` in the WSGI file.
* **No styling:** run `python manage.py collectstatic --noinput` again and check the static mapping path.
* **Reset the data:** in a Bash console run `cd ~/bincom-election-results && python import_mysql_dump.py`, then Reload.
* **Updating after code changes:** `cd ~/bincom-election-results && git pull`, then Reload. (`db.sqlite3` is not in git, so your data is kept.)
* Free accounts must press "Run until 3 months from today" on the Web tab now and then to keep the site up.
