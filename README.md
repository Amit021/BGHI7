# BGHI7

University-only community app (students + alumni) built with Django.

## Run in GitHub Codespaces

This project can be run directly in GitHub Codespaces.

- (Optional) Load demo users and sample posts/comments:
  - `python manage.py seed_demo_data --yes`

- Start the Django development server:
  - `python manage.py runserver`

Once running, open the forwarded application URL from the Codespaces **Ports** tab (you can open it in a new browser tab).

## Requirements

- Python 3.10+ (recommended)
- macOS / Linux / Windows

## Setup (first time)

From the project root:

1) Create and activate a virtual environment

- macOS/Linux:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`

- Windows (PowerShell):
  - `py -m venv .venv`
  - `.\.venv\Scripts\Activate.ps1`

2) Install dependencies

- `python -m pip install --upgrade pip`
- `pip install -r requirements.txt`

3) Run migrations

- `python manage.py migrate`

4) (Optional) Seed demo data

- `python manage.py seed_demo_data --yes`

This creates demo users and sample posts/comments.

5) Start the server

- `python manage.py runserver`

Open `http://127.0.0.1:8000/`.

## Demo accounts

If you ran `seed_demo_data`, use:

- Student:
  - `student1@th-deg.de` / `student123`

- Alumni:
  - `alumni1@gmail.com` / `alumni123`

## Admin / Django shell

Create an admin user:

- `python manage.py createsuperuser`

Open admin:

- `http://127.0.0.1:8000/admin/`

## Notes

- Local SQLite DB (`db.sqlite3`) is intentionally not committed. Each developer will create their own via `migrate`.
- Student registration is gated by the configured university email domains (see below).
- The "Jobs & Referrals" topic is demo-gated by `User.is_paid`.

## Student Email Domains

Students can register with emails from the following domains (no invitation code required):

**Default domains:**
- `th-deg.de`
- `stud.th-deg.de`
- `thi.de`
- `stud.thi.de`

**To add more domains**, set the `UNIVERSITY_EMAIL_DOMAINS` environment variable (comma-separated):

```bash
export UNIVERSITY_EMAIL_DOMAINS="th-deg.de,stud.th-deg.de,thi.de,stud.thi.de,newuni.edu"
```

Or in the systemd service file on the server:

```ini
Environment="UNIVERSITY_EMAIL_DOMAINS=th-deg.de,stud.th-deg.de,thi.de,stud.thi.de,newuni.edu"
```

If the env var is not set, the default domains above are used.

Alumni (non-student emails) require a valid invitation code to register.

## API

- API routes are mounted at `/api/` (see `GET /api`).
- Most API endpoints require authentication (`IsAuthenticated`). The simplest way in local dev is to log in via the web UI first, then call the API using the same session/cookies.

## CI/CD (Jenkins + AWS Free Tier)

This repo includes a Jenkins pipeline in [Jenkinsfile](Jenkinsfile) that:

- Polls the Git repo (every ~2 minutes) for new commits (or use GitHub webhooks)
- Runs Django checks, migrations, tests, and coverage
- Deploys to the server automatically

### 0) Avoid surprise charges

- Prefer a single small EC2 instance for demo purposes.
- In AWS Billing, enable alerts/alarms so you get notified if charges occur.

### 1) Create an EC2 instance (Ubuntu)

- Launch **EC2** (Ubuntu 22.04 LTS), instance type **t2.micro** or **t3.micro** (Free Tier eligible).
- Create a keypair and download it.
- Security Group (minimum):
  - SSH `22` from *your IP only*
  - HTTP `80` from anywhere (for the site)
  - Jenkins `8080` from *your IP only* (or use SSH port-forwarding instead)

### 2) Install system dependencies

On the EC2 instance:

- `sudo apt-get update`
- `sudo apt-get install -y python3-venv python3-pip git nginx openjdk-17-jre`

### 3) Install Jenkins

Install Jenkins (LTS) and start it, then open `http://<EC2_PUBLIC_IP>:8080`.
Follow the Jenkins setup wizard and install suggested plugins.

### 4) Create a Jenkins Pipeline job

Create a Pipeline job pointing to this repo and `Jenkinsfile`.
Since Jenkins is running on a server, you can use GitHub webhooks or polling.

### 5) Configure app settings for production

This project supports environment-based settings:

- `DJANGO_DEBUG=false`
- `DJANGO_SECRET_KEY=<random-secret>`
- `DJANGO_ALLOWED_HOSTS=<your-domain-or-ec2-ip>`

Static files can be collected with:

- `python manage.py collectstatic --noinput`

### 6) Serve Django with gunicorn + nginx

For a simple demo:

- Run the app with gunicorn (example): `gunicorn webappname.wsgi:application --bind 127.0.0.1:8000`
- Configure nginx to proxy `/` to `127.0.0.1:8000` and serve `/static/` from `staticfiles/`.
