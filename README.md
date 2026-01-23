# BGHI7

University-only community app (students + alumni) built with Django.

## Quick Start: Run in GitHub Codespaces 

The easiest way to test this application is using GitHub Codespaces - no local setup required!

### Step 1: Open in Codespaces

1. Go to the repository: https://github.com/Amit021/BGHI7
2. Click the green **"Code"** button
3. Select the **"Codespaces"** tab
4. Click **"Create codespace on main"**

### Step 2: Wait for Setup (1-2 minutes)

The Codespace will automatically:
- Install all Python dependencies
- Run database migrations
- Seed demo data (sample users, posts, and comments)
- Start the Django development server

### Step 3: Access the Application

Once setup is complete:
1. A preview window will open automatically, OR
2. Go to the **"Ports"** tab at the bottom of VS Code
3. Click the **globe icon** 🌐 next to port `8000` to open the app in a new browser tab

### Demo Login Credentials

Use these pre-seeded accounts to test the application:

| Role    | Email                | Password     |
|---------|----------------------|--------------|
| Student | `student1@th-deg.de` | `student123` |
| Alumni  | `alumni1@gmail.com`  | `alumni123`  |

### Invitation Codes (For Testing Registration)

To test user registration:

- **Students**: Can register with university emails (`@th-deg.de`, `@stud.th-deg.de`, `@thi.de`, `@stud.thi.de`) - no invitation code required
- **Alumni**: Must use a valid invitation code to register with non-university emails

| Invitation Code  | Status       | Use Case                             |
|------------------|--------------|--------------------------------------|
| `ALUMNI2025`     | Active       | Use this to register as a new alumni |
| `ALUMNI2025USED` | Already Used | Tests "code already used" validation |

### Features to Test

- **Landing Page**: Browse categories (Community, Jobs, Study Materials, Mentorship)
- **User Registration**: Register with a university email (`@th-deg.de`, `@stud.th-deg.de`, etc.)
- **Posts & Comments**: Create posts, add comments with file attachments (Study Materials)
- **Voting System**: Upvote/downvote posts
- **Premium Access**: Enable on your profile to access Jobs & Referrals
- **Mentorship**: Create a mentorship profile to offer/seek mentoring
- **Direct Messages**: Send private messages to other users

### Troubleshooting

If the server isn't running:
1. Open a terminal in Codespaces
2. Run: `python manage.py runserver 0.0.0.0:8000`

To reset demo data:
```bash
python manage.py seed_demo_data --yes
```

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

## CI/CD Pipeline (Jenkins + AWS EC2)

This project includes a fully automated CI/CD pipeline using Jenkins deployed on AWS EC2.

### Pipeline Overview

The pipeline is defined in [Jenkinsfile](Jenkinsfile) and consists of 5 stages:

```
┌─────────────┐    ┌─────────────┐    ┌───────────────┐    ┌─────────────────┐    ┌─────────────┐
│  Checkout   │ -> │ Setup venv  │ -> │ Django checks │ -> │ Tests + Coverage│ -> │   Deploy  │
└─────────────┘    └─────────────┘    └───────────────┘    └─────────────────┘    └─────────────┘
```

### Pipeline Stages Explained

#### 1. Checkout
- Pulls the latest code from the GitHub repository
- Triggered automatically every 2 minutes via SCM polling (or via GitHub webhook)

#### 2. Setup Virtual Environment
- Creates a Python virtual environment
- Installs production dependencies from `requirements.txt`
- Installs dev dependencies from `requirements-dev.txt` (includes pytest, coverage, etc.)

#### 3. Django Checks
- Runs `python manage.py check` to validate Django configuration
- Runs database migrations with `python manage.py migrate --noinput`

#### 4. Tests + Coverage
- Executes the full test suite using `coverage run manage.py test`
- Generates coverage reports in XML and HTML formats
- Archives coverage artifacts for review in Jenkins

#### 5. Deploy App
The deployment stage performs the following:
- **Syncs application files** to `/opt/bghi7` on the server (excluding `.git`, `__pycache__`, `.venv`, `db.sqlite3`)
- **Preserves uploaded files** (attachments, comment attachments) between deployments
- **Sets up Python virtual environment** with Gunicorn WSGI server
- **Runs database migrations** on production database
- **Collects static files** for nginx serving
- **Configures systemd service** (`bghi7.service`) for automatic app startup/restart
- **Configures nginx** as reverse proxy:
  - Serves static files from `/static/`
  - Serves media/uploads from `/images/`
  - Proxies all other requests to Gunicorn (port 8000)
- **Restarts services** to apply changes

### Infrastructure Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           AWS EC2 Instance              │
                    │              (Ubuntu 22.04)             │
┌──────────┐        │  ┌─────────┐      ┌──────────────────┐  │
│  GitHub  │ ──────>│  │ Jenkins │ ──── │ Django App       │  │
│   Repo   │  push/ │  │ :8080   │      │ (Gunicorn :8000) │  │
└──────────┘  poll  │  └─────────┘      └──────────────────┘  │
                    │                           ↑             │
                    │                    ┌──────┴───────┐     │
                    │                    │    nginx     │     │
                    │                    │    :80       │     │
                    │                    └──────────────┘     │
                    └─────────────────────────────────────────┘
                                        ↑
                              HTTP requests from users
```

### Production Environment Variables

The deployed app uses these environment variables (configured in systemd service):

| Variable | Value | Description |
|----------|-------|-------------|
| `DJANGO_DEBUG` | `False` | Disables debug mode for security |
| `DJANGO_SECRET_KEY` | `<secret>` | Django secret key for sessions |
| `DJANGO_ALLOWED_HOSTS` | `*` | Allowed host headers |

### How to Set Up Jenkins (From Scratch)

#### 0) Avoid Surprise AWS Charges
- Use a single **t2.micro** or **t3.micro** instance (Free Tier eligible)
- Enable AWS Billing alerts/alarms to get notified of any charges

#### 1) Create an EC2 Instance (Ubuntu)

- Launch **EC2** (Ubuntu 22.04 LTS), instance type **t2.micro** or **t3.micro** (Free Tier eligible)
- Create a keypair and download it
- Security Group (minimum):
  - SSH `22` from *your IP only*
  - HTTP `80` from anywhere (for the site)
  - Jenkins `8080` from *your IP only* (or use SSH port-forwarding instead)

#### 2) Install System Dependencies

SSH into the EC2 instance and run:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git nginx openjdk-17-jre
```

#### 3) Install Jenkins

```bash
# Add Jenkins repository
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/ | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

# Install and start Jenkins
sudo apt-get update
sudo apt-get install -y jenkins
sudo systemctl enable jenkins
sudo systemctl start jenkins
```

Access Jenkins at `http://<EC2_PUBLIC_IP>:8080` and complete the setup wizard.

#### 4) Create a Jenkins Pipeline Job

1. In Jenkins, click **"New Item"**
2. Enter a name (e.g., `BGHI7`), select **"Pipeline"**, click OK
3. Under **"Pipeline"** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/Amit021/BGHI7.git`
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`
4. Save and click **"Build Now"** to trigger the first build

#### 5) Verify Deployment

After a successful build:
- The app is deployed to `/opt/bghi7`
- Access the app at `http://<EC2_PUBLIC_IP>`
- Jenkins will automatically deploy on every push to the repository
