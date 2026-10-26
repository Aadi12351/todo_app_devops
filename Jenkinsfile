pipeline {
    agent {
        label 'todo-agent'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout()
    }

    parameters {
        string(
            name: 'MANIFEST_DIR',
            defaultValue: 'k8s',
            description: 'Repository folder containing Kubernetes YAML files'
        )
        string(
            name: 'DEPLOYMENT_NAME',
            defaultValue: 'todo-app',
            description: 'Kubernetes Deployment name'
        )
        string(
            name: 'CONTAINER_NAME',
            defaultValue: 'todo-app',
            description: 'Container name inside the Deployment'
        )
        string(
            name: 'K8S_NAMESPACE',
            defaultValue: 'default',
            description: 'Existing Kubernetes namespace'
        )
    }

    environment {
        IMAGE_NAME = 'aaditya4512/todo-app'
        CONTROLLER_HOST = '172.31.9.27'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Python Tests') {
            steps {
                sh '''
                    set -eu
                    python3 -m venv .venv
                    .venv/bin/python -m pip install -r requirements.txt
                    .venv/bin/python -m pytest -v
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    set -eu
                    docker build -t "$IMAGE_NAME:$BUILD_NUMBER" .
                '''
            }
        }

        stage('Docker Hub Push') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_TOKEN'
                    )
                ]) {
                    sh '''
                        set -eu
                        set +x
                        export DOCKER_CONFIG="$(mktemp -d)"
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT

                        printf '%s' "$DOCKER_TOKEN" |
                            docker login \
                                --username "$DOCKER_USER" \
                                --password-stdin

                        docker push "$IMAGE_NAME:$BUILD_NUMBER"
                    '''
                }
            }
        }

        stage('Deploy to KIND') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    sshagent(credentials: ['controller-ssh']) {
                        sh '''
                            set -eu

                            for value in "$DEPLOYMENT_NAME" "$CONTAINER_NAME" "$K8S_NAMESPACE"; do
                                case "$value" in
                                    ""|*[!a-z0-9.-]*)
                                        echo "Invalid Kubernetes name: $value"
                                        exit 1
                                        ;;
                                esac
                            done

                            test -d "$MANIFEST_DIR"

                            REMOTE_DIR=$(ssh \
                                -o BatchMode=yes \
                                -o ConnectTimeout=15 \
                                -o StrictHostKeyChecking=yes \
                                "ubuntu@$CONTROLLER_HOST" \
                                'mktemp -d /tmp/todo-deploy.XXXXXXXX')

                            trap 'ssh -o BatchMode=yes -o ConnectTimeout=15 \
                                -o StrictHostKeyChecking=yes \
                                "ubuntu@$CONTROLLER_HOST" \
                                "rm -rf -- $REMOTE_DIR"' EXIT

                            scp \
                                -o BatchMode=yes \
                                -o ConnectTimeout=15 \
                                -o StrictHostKeyChecking=yes \
                                -r "$MANIFEST_DIR/." \
                                "ubuntu@$CONTROLLER_HOST:$REMOTE_DIR/"

                            ssh \
                                -o BatchMode=yes \
                                -o ConnectTimeout=15 \
                                -o StrictHostKeyChecking=yes \
                                "ubuntu@$CONTROLLER_HOST" \
                                bash -s -- \
                                "$REMOTE_DIR" "$K8S_NAMESPACE" \
                                "$DEPLOYMENT_NAME" "$CONTAINER_NAME" \
                                "$IMAGE_NAME:$BUILD_NUMBER" <<'REMOTE'
set -eu

manifest_dir="$1"
namespace="$2"
deployment="$3"
container="$4"
image="$5"

export KUBECONFIG="$HOME/kind-kubeconfig"

kube() {
    kubectl --context kind-todo-cluster -n "$namespace" "$@"
}

test -r "$KUBECONFIG"

# Apply both deployment.yaml and service.yaml.
kube apply -f "$manifest_dir"

# Update the container image only in the Deployment.
kube set image "deployment/$deployment" "$container=$image"

# Wait until the new application Pods are ready.
if ! kube rollout status "deployment/$deployment" --timeout=180s; then
    echo "Deployment did not become ready. Diagnostic output:"
    kube get pods -o wide || true
    kube describe "deployment/$deployment" || true
    kube get events --sort-by=.metadata.creationTimestamp || true
    exit 1
fi

kube get "deployment/$deployment" -o wide
kube get pods,services
REMOTE
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Tests, Docker Hub push and KIND deployment successful!'
        }

        failure {
            echo 'Pipeline failed. Check the failed stage in console output.'
        }
    }
}
