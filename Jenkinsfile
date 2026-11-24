pipeline {
    agent any
    environment {
        DOCKERHUB_USER = 'shaulicohenr'
        REPO_URL       = 'https://github.com/shaulicohenr/hello-world.git'
        REPO_BRANCH    = 'main'
        IMAGE_NAME     = "${DOCKERHUB_USER}/hello-world"
        IMAGE_TAG      = "v${BUILD_NUMBER}"
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
        stage('Docker Build') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .'
            }
        }
        stage('Tag Image') {
            steps {
                sh 'docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest'
            }
        }
        stage('Trivy Scan') {
            steps {
                // Fails the build on CRITICAL vulnerabilities. Requires the trivy binary on the agent.
                sh 'trivy image --exit-code 1 --severity CRITICAL --no-progress ${IMAGE_NAME}:${IMAGE_TAG}'
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
    }
    post {
        success { echo "Pushed ${IMAGE_NAME}:${IMAGE_TAG}" }
        failure { echo 'Pipeline failed - check the stage logs above.' }
        always  { sh 'docker image prune -f || true' }
    }
}
