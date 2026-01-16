pipeline {
  agent any

  options {
    timestamps()
  }

  triggers {
    pollSCM('H/2 * * * *')
  }

  environment {
    VENV_DIR = '.venv'
    PYTHON = "${VENV_DIR}/bin/python"
    PIP = "${VENV_DIR}/bin/pip"
    
    // App deployment settings
    APP_DIR = '/opt/bghi7'
    APP_USER = 'ubuntu'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup venv') {
      steps {
        sh '''
          set -e
          python3 -m venv "$VENV_DIR"
          "$PIP" install --upgrade pip
          "$PIP" install -r requirements.txt
          if [ -f requirements-dev.txt ]; then
            "$PIP" install -r requirements-dev.txt
          fi
        '''
      }
    }

    stage('Django checks') {
      steps {
        sh '''
          set -e
          "$PYTHON" manage.py check
          "$PYTHON" manage.py migrate --noinput
        '''
      }
    }

    stage('Tests + Coverage') {
      steps {
        sh '''
          set -e
          "$PYTHON" -m coverage run manage.py test
          "$PYTHON" -m coverage xml -o coverage.xml
          "$PYTHON" -m coverage html -d coverage_html
          "$PYTHON" -m coverage report -m
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'coverage.xml,coverage_html/**', fingerprint: true, onlyIfSuccessful: false
        }
      }
    }

    stage('Deploy App') {
      when {
        branch 'main'
      }
      steps {
        sh '''
          set -e
          
          # Create app directory if it doesn't exist
          sudo mkdir -p "$APP_DIR"
          sudo chown "$APP_USER:$APP_USER" "$APP_DIR"
          
          # Sync app files (excluding .git, __pycache__, .venv, db.sqlite3)
          rsync -av --delete \
            --exclude '.git' \
            --exclude '__pycache__' \
            --exclude '.venv' \
            --exclude 'coverage_html' \
            --exclude 'coverage.xml' \
            --exclude '*.pyc' \
            . "$APP_DIR/"
          
          # Setup venv in app directory
          cd "$APP_DIR"
          python3 -m venv venv
          venv/bin/pip install --upgrade pip
          venv/bin/pip install -r requirements.txt
          venv/bin/pip install gunicorn
          
          # Run migrations
          venv/bin/python manage.py migrate --noinput
          
          # Collect static files
          venv/bin/python manage.py collectstatic --noinput
          
          # Setup systemd service for gunicorn
          sudo tee /etc/systemd/system/bghi7.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=BGHI7 Django App (Gunicorn)
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/bghi7
Environment="DJANGO_SECRET_KEY=jenkins-prod-secret-change-me-12345"
Environment="DJANGO_DEBUG=False"
Environment="DJANGO_ALLOWED_HOSTS=*"
ExecStart=/opt/bghi7/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 webappname.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICEEOF
          
          # Setup nginx
          sudo tee /etc/nginx/sites-available/bghi7 > /dev/null << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /opt/bghi7/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF
          
          # Enable site and restart services
          sudo ln -sf /etc/nginx/sites-available/bghi7 /etc/nginx/sites-enabled/bghi7
          sudo rm -f /etc/nginx/sites-enabled/default
          sudo nginx -t
          sudo systemctl daemon-reload
          sudo systemctl enable bghi7
          sudo systemctl restart bghi7
          sudo systemctl restart nginx
          
          echo "✅ App deployed successfully!"
          echo "🌐 Visit: http://$(curl -s ifconfig.me)"
        '''
      }
    }
  }
}
