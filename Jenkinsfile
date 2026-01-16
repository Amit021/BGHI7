pipeline {
  agent any

  options {
    timestamps()
  }

  triggers {
    // Jenkins running on a laptop is usually not reachable by GitHub webhooks.
    // Polling still gives fully automatic builds shortly after a push.
    pollSCM('H/2 * * * *')
  }

  environment {
    VENV_DIR = '.venv'
    PYTHON = "${VENV_DIR}/bin/python"
    PIP = "${VENV_DIR}/bin/pip"

    // PythonAnywhere SSH deploy settings
    PA_HOST = 'ssh.pythonanywhere.com'
    // Set this in Jenkins job config (e.g. "amit21")
    PA_USER = "${env.PA_USER}"
    // Script to run on PythonAnywhere (create it once in your PythonAnywhere home dir)
    PA_DEPLOY_SCRIPT = "${env.PA_DEPLOY_SCRIPT ?: '~/deploy_bghi7.sh'}"
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

    stage('Deploy to PythonAnywhere') {
      when {
        allOf {
          branch 'main'
          expression { return env.PA_USER?.trim() }
        }
      }
      steps {
        // Requires Jenkins plugin: "SSH Agent"
        sshagent(credentials: ['pythonanywhere-ssh']) {
          sh '''
            set -e
            mkdir -p ~/.ssh
            chmod 700 ~/.ssh

            # Avoid interactive host key prompt on first connection
            ssh-keyscan -H "$PA_HOST" >> ~/.ssh/known_hosts 2>/dev/null

            # -tt forces a PTY (some restricted hosts require it)
            ssh -tt "$PA_USER@$PA_HOST" "bash -lc $PA_DEPLOY_SCRIPT"
          '''
        }
      }
    }
  }
}
