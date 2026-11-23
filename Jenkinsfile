pipeline {
    agent any
    environment {
        DOCKERHUB_USER = 'shaulicohenr'
        REPO_URL       = 'https://github.com/shaulicohenr/hello-world.git'
        REPO_BRANCH    = 'main'
        IMAGE_NAME     = "${DOCKERHUB_USER}/hello-world"
        IMAGE_TAG      = "v${BUILD_NUMBER}"
        K8S_NAMESPACE  = 'hello-world'
    }
    options {
        timestamps()
        disableConcurrentBuilds()
    }
    stages {
        stage('Clone Repository') {
            steps {
                git branch: "${REPO_BRANCH}", url: "${REPO_URL}"
            }
        }
        stage('Build Application') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --no-cache-dir -r app/requirements-dev.txt
                    python -m py_compile app/app.py
                    cd app && python -m pytest -q
                '''
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .'
            }
        }
        stage('Security Scan (Trivy)') {
            steps {
                // Fails the build on CRITICAL vulnerabilities. Requires the trivy binary on the agent.
                sh 'trivy image --exit-code 1 --severity CRITICAL --no-progress ${IMAGE_NAME}:${IMAGE_TAG}'
            }
        }
        stage('Tag Image') {
            steps {
                sh 'docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest'
            }
        }
        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push ${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${IMAGE_NAME}:latest
                        docker logout
                    '''
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        # Point the manifest at the image that was just pushed
                        sed -i "s|image: .*|image: ${IMAGE_NAME}:${IMAGE_TAG}|" k8s/deployment.yaml

                        kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                        kubectl apply -n ${K8S_NAMESPACE} -f k8s/deployment.yaml
                        kubectl apply -n ${K8S_NAMESPACE} -f k8s/service.yaml
                        kubectl rollout status deployment/hello-world -n ${K8S_NAMESPACE} --timeout=120s
                    '''
                }
            }
        }
    }
    post {
        success {
            echo "Deployed ${IMAGE_NAME}:${IMAGE_TAG} to namespace ${K8S_NAMESPACE}"
        }
        failure {
            echo 'Pipeline failed - check the stage logs above.'
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}
