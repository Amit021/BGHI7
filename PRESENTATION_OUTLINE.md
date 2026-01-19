# CI/CD Pipeline Presentation Outline
## BGHI7 - University Community Platform
### Prof. Dr. Mouzhi Ge, WS 25/26 | Duration: 10 minutes

---

## 1. Project Introduction (2-3 minutes)

### Project Name
**BGHI7** - University Community Platform

### Project Description
A web-based community platform exclusively for university students and alumni to connect, share knowledge, and network.

### Technology Stack
| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.10+, Django 5.2 |
| **Frontend** | Django Templates, HTML/CSS/JS |
| **Database** | SQLite (dev), SQLite (demo production) |
| **API** | Django REST Framework |
| **Web Server** | Gunicorn (WSGI) + Nginx (reverse proxy) |
| **Hosting** | AWS EC2 (Free Tier) |
| **CI/CD** | Jenkins LTS |

### Purpose & Key Features
- **Access Control**: Students register with university email (@th-deg.de, @stud.th-deg.de, @thi.de, @stud.thi.de)
- **Alumni Network**: Alumni can join using invitation codes
- **Discussion Rooms**: Topic-based discussion forums
- **Voting System**: Upvote/downvote on posts and comments
- **Premium Features**: "Jobs & Referrals" section (demo paid feature)
- **REST API**: Full API for mobile/external integrations

### Why This Project?
- Demonstrates real-world web application with authentication
- Shows environment-based configuration (dev vs production)
- Includes user roles and access control logic
- Good candidate for CI/CD due to multiple moving parts

---

## 2. CI/CD Pipeline Demonstration (5-6 minutes)

### Pipeline Overview Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   GitHub    │────▶│   Jenkins   │────▶│   AWS EC2       │
│  (Source)   │     │  (CI/CD)    │     │  (Production)   │
└─────────────┘     └─────────────┘     └─────────────────┘
      │                    │                     │
   Push/PR          Automated               Live App
   Webhook          Pipeline              http://IP:80
```

### Trigger Mechanism
- **GitHub Webhook**: Automatically triggers Jenkins on every push to `main`
- **Fallback Polling**: Jenkins polls Git every 2 minutes (H/2 * * * *)

### Pipeline Stages

#### Stage 1: Checkout
```groovy
stage('Checkout') {
  steps {
    checkout scm
  }
}
```
- Clones the latest code from GitHub repository
- Uses Jenkins SCM integration

#### Stage 2: Setup Virtual Environment
```groovy
stage('Setup venv') {
  steps {
    sh '''
      python3 -m venv "$VENV_DIR"
      "$PIP" install -r requirements.txt
      "$PIP" install -r requirements-dev.txt
    '''
  }
}
```
- Creates isolated Python environment
- Installs production dependencies (Django, DRF, Pillow, etc.)
- Installs dev dependencies (coverage, testing tools)

#### Stage 3: Django Checks (Code Quality)
```groovy
stage('Django checks') {
  steps {
    sh '''
      "$PYTHON" manage.py check
      "$PYTHON" manage.py migrate --noinput
    '''
  }
}
```
- Runs Django system checks (validates models, settings, URLs)
- Applies database migrations
- **Fails fast** if configuration is broken

#### Stage 4: Tests + Coverage (Continuous Integration)
```groovy
stage('Tests + Coverage') {
  steps {
    sh '''
      "$PYTHON" -m coverage run manage.py test
      "$PYTHON" -m coverage xml -o coverage.xml
      "$PYTHON" -m coverage report -m
    '''
  }
}
```
- Runs **17 automated tests** covering:
  - Form validation (student/alumni registration)
  - View access control (login required, paid features)
  - API authentication
- Generates coverage report (~50% code coverage)
- Archives coverage artifacts in Jenkins

#### Stage 5: Deploy App (Continuous Deployment)
```groovy
stage('Deploy App') {
  steps {
    sh '''
      # Sync files to /opt/bghi7
      sudo rsync -av --delete . "$APP_DIR/"
      
      # Setup Python environment
      sudo -u "$APP_USER" venv/bin/pip install -r requirements.txt
      
      # Run migrations & collect static
      sudo -u "$APP_USER" venv/bin/python manage.py migrate --noinput
      sudo -u "$APP_USER" venv/bin/python manage.py collectstatic --noinput
      
      # Restart services
      sudo systemctl restart bghi7
      sudo systemctl restart nginx
    '''
  }
}
```
- **Automatic deployment** - no manual intervention
- Syncs code to production directory
- Sets up production Python environment
- Runs database migrations
- Collects static files (CSS, JS, images)
- Restarts Gunicorn (app server) and Nginx (web server)

### Error Handling & Feedback

| Scenario | What Happens |
|----------|--------------|
| **Test Failure** | Pipeline stops, build marked FAILED, no deployment |
| **Django Check Fails** | Pipeline stops at Stage 3, notifies developer |
| **Deployment Fails** | Previous version stays running (systemd auto-restart) |
| **Build Success** | ✅ Green checkmark in Jenkins, app live immediately |

### Live Demo Points (if showing live)
1. Show Jenkins Dashboard at `http://100.53.1.235:8080`
2. Make a small code change locally
3. Push to GitHub: `git push origin main`
4. Watch Jenkins auto-trigger and run pipeline
5. Show the live app at `http://100.53.1.235`

---

## 3. Toolset Used (1-2 minutes)

### CI/CD Orchestration

| Tool | Role | Why Chosen |
|------|------|------------|
| **Jenkins LTS** | CI/CD orchestration | Industry standard, self-hosted (free), powerful pipeline DSL, extensive plugin ecosystem |
| **GitHub** | Source control + webhooks | Free, integrated with Jenkins, automatic trigger on push |

### Testing Tools

| Tool | Role | Why Chosen |
|------|------|------------|
| **Django Test Framework** | Unit/integration tests | Built into Django, no extra setup |
| **Coverage.py** | Code coverage measurement | Standard Python coverage tool, generates HTML/XML reports |

### Deployment Tools

| Tool | Role | Why Chosen |
|------|------|------------|
| **Gunicorn** | WSGI application server | Production-grade, simple config, works well with Django |
| **Nginx** | Reverse proxy & static files | High performance, industry standard, handles SSL/load balancing |
| **systemd** | Process management | Built into Ubuntu, auto-restart on failure |
| **rsync** | File synchronization | Fast incremental sync, excludes unnecessary files |

### Infrastructure

| Tool | Role | Why Chosen |
|------|------|------------|
| **AWS EC2 (t3.micro)** | Hosting | Free Tier eligible (750 hrs/month), easy to set up |
| **Ubuntu 22.04 LTS** | Server OS | Long-term support, well-documented, works with Jenkins |
| **Boto3 (Python)** | Infrastructure as Code | Automated EC2 provisioning script in `infra/create_jenkins_ec2.py` |

### Tool Categories Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD PIPELINE TOOLS                     │
├─────────────────────────────────────────────────────────────┤
│  ORCHESTRATION      │  TESTING           │  DEPLOYMENT      │
│  ─────────────      │  ───────           │  ──────────      │
│  • Jenkins LTS      │  • Django Tests    │  • Gunicorn      │
│  • GitHub Webhooks  │  • Coverage.py     │  • Nginx         │
│                     │                    │  • systemd       │
├─────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                             │
│  ──────────────                                             │
│  • AWS EC2 (Free Tier)  • Ubuntu 22.04  • Boto3 (IaC)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **Fully Automated**: Push to GitHub → Tests run → Deploy to production (zero manual steps)
2. **Fast Feedback**: Pipeline runs in ~2-3 minutes, immediate notification on failure
3. **Cost-Effective**: Entire setup runs on AWS Free Tier ($0/month)
4. **Production-Ready**: Uses industry-standard tools (Jenkins, Nginx, Gunicorn, systemd)
5. **Scalable Design**: Same pipeline can scale to larger infrastructure with minimal changes

---

## Potential Q&A Questions

1. **Why Jenkins instead of GitHub Actions?**
   - Self-hosted = full control, no usage limits
   - Industry experience (widely used in enterprises)
   - Runs on same server as app (cost-effective for demo)

2. **Why not use Docker?**
   - Kept simple for demo; Docker adds complexity
   - t3.micro has limited resources (1GB RAM)
   - Direct deployment is faster for small apps

3. **What happens if deployment fails mid-way?**
   - systemd keeps the old process running
   - Database migrations are transactional (rollback on failure)
   - Can manually rollback via `git revert` + push

4. **How do you handle secrets?**
   - Environment variables in systemd service file
   - Not committed to Git
   - Could use Jenkins Credentials or AWS Secrets Manager

5. **How would you add staging environment?**
   - Add branch condition in Jenkinsfile
   - Deploy `develop` branch to staging server
   - Deploy `main` branch to production
