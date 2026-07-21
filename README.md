# Project 3 — Full CI/CD Pipeline with Automated Testing
**Difficulty:** ⭐⭐ Beginner+ | **Time:** 4–5 hrs | **AWS services:** ECR, IAM

---

## What you're building

A production-grade CI/CD pipeline around a Python Flask task API — a small but real app with multiple endpoints. The pipeline runs tests, lints the code, scans the Docker image for vulnerabilities, and pushes to AWS ECR. A failing test stops the build before an image is ever created.

## What you'll learn

- Writing a testable Python Flask API from scratch
- Multi-job GitHub Actions pipelines with dependency gates
- Unit testing with pytest and coverage enforcement
- Docker image vulnerability scanning with Trivy
- Pushing Docker images to AWS ECR
- PR vs. main branch pipeline behaviour

## The app: Task API

A simple REST API that manages tasks in memory. Small enough to understand completely, real enough to have meaningful tests.

```
GET  /           → welcome + version
GET  /health     → {"status": "ok", "version": "1.0.0"}
GET  /tasks      → list all tasks
POST /tasks      → create a task  {"title": "Buy milk"}
GET  /tasks/:id  → get one task
DELETE /tasks/:id → delete a task
```

## Pipeline architecture

```
git push / Pull Request
        │
        ▼
GitHub Actions
        │
        ├─ Job 1: test
        │    ├─ flake8 lint
        │    ├─ pytest with coverage (fail if < 80%)
        │    └─ upload coverage artifact
        │         │ (only if pass)
        │         ▼
        ├─ Job 2: build-and-scan
        │    ├─ docker build
        │    ├─ Trivy scan (fail on HIGH/CRITICAL)
        │    └─ push to AWS ECR (main branch only)
        │         │ (only if pass)
        │         ▼
        └─ Job 3: notify
             └─ post summary comment to PR
```

---

## Prerequisites — complete all of these before starting

### Tools on your laptop

**Python 3.11+**
```bash
python3 --version
# Mac: brew install python@3.12
# Windows: winget install Python.Python.3.12
# Ubuntu: sudo apt install python3.12 python3.12-venv
```

**Docker Desktop** — https://docs.docker.com/get-docker/
```bash
docker --version   # verify it's running
```

**AWS CLI v2**
```bash
# Mac:
brew install awscli
# Windows:
winget install Amazon.AWSCLI
# Linux:
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
unzip /tmp/awscliv2.zip -d /tmp && sudo /tmp/aws/install
# Verify:
aws --version
```

**Git**
```bash
git --version   # install from https://git-scm.com if missing
```

### AWS account setup (one-time)

1. Sign up at https://aws.amazon.com (free tier — this project stays within free limits)
2. **IAM → Users → Create user**
   - Username: `devops-project-03`
   - Permissions: attach policy `AmazonEC2ContainerRegistryFullAccess`
   - Create access key → **Application running outside AWS**
   - Download CSV (shown once only)
3. Configure the CLI:
```bash
aws configure
# AWS Access Key ID:     [paste from CSV]
# AWS Secret Access Key: [paste from CSV]
# Default region:        us-east-1
# Default output format: json

aws sts get-caller-identity   # verify — shows your account ID
```

### GitHub account
- https://github.com — free account, Actions included

---

## Step-by-step

### Step 1 — Create the project repo

```bash
mkdir devops-project-03
cd devops-project-03
git init
git checkout -b main
```

Create `.gitignore` before any code:
```
__pycache__/
*.pyc
.pytest_cache/
venv/
.venv/
.env
coverage.xml
.coverage
trivy-*.sarif
```

### Step 2 — Write the app

```bash
mkdir app tests
touch app/__init__.py tests/__init__.py
```

**`app/tasks.py`** — task store:

```python
from dataclasses import dataclass, field, asdict
from typing import Optional
import time


@dataclass
class Task:
    id: int
    title: str
    done: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class TaskStore:
    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1

    def get_all(self) -> list[dict]:
        return [t.to_dict() for t in self._tasks.values()]

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def create(self, title: str) -> Task:
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        task = Task(id=self._next_id, title=title.strip())
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task

    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
```

**`app/main.py`** — Flask API:

```python
import os
from flask import Flask, jsonify, request, abort
from .tasks import TaskStore

VERSION = os.getenv("APP_VERSION", "1.0.0")
app = Flask(__name__)
store = TaskStore()


@app.route("/")
def index():
    return jsonify({"name": "Task API", "version": VERSION,
                    "endpoints": ["/health", "/tasks"]})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": VERSION})


@app.route("/tasks", methods=["GET"])
def list_tasks():
    tasks = store.get_all()
    return jsonify({"tasks": tasks, "count": len(tasks)})


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True)
    if not data or "title" not in data:
        abort(400, description="Body must be JSON with a 'title' field")
    try:
        task = store.create(data["title"])
    except ValueError as e:
        abort(400, description=str(e))
    return jsonify(task.to_dict()), 201


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id: int):
    task = store.get(task_id)
    if not task:
        abort(404, description=f"Task {task_id} not found")
    return jsonify(task.to_dict())


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int):
    if not store.delete(task_id):
        abort(404, description=f"Task {task_id} not found")
    return "", 204


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request", "detail": str(e.description)}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "detail": str(e.description)}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
```

**`app/requirements.txt`**:
```
flask==3.0.3
gunicorn==22.0.0
```

**`requirements-dev.txt`**:
```
pytest==8.2.0
pytest-cov==5.0.0
flake8==7.0.0
```

### Step 3 — Write the tests

**`tests/test_api.py`**:

```python
import json
import pytest
from app.main import app, store


@pytest.fixture(autouse=True)
def reset_store():
    """Clear store before every test so tests are independent."""
    store._tasks.clear()
    store._next_id = 1
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def post_task(client, title):
    return client.post("/tasks",
                       data=json.dumps({"title": title}),
                       content_type="application/json")


class TestHealth:
    def test_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_returns_ok(self, client):
        assert client.get("/health").get_json()["status"] == "ok"

    def test_has_version(self, client):
        assert "version" in client.get("/health").get_json()


class TestListTasks:
    def test_empty_on_start(self, client):
        res = client.get("/tasks").get_json()
        assert res["tasks"] == [] and res["count"] == 0

    def test_shows_created_tasks(self, client):
        post_task(client, "Buy milk")
        post_task(client, "Walk dog")
        assert client.get("/tasks").get_json()["count"] == 2


class TestCreateTask:
    def test_creates_with_201(self, client):
        res = post_task(client, "Buy milk")
        assert res.status_code == 201

    def test_returns_task_data(self, client):
        data = post_task(client, "Buy milk").get_json()
        assert data["title"] == "Buy milk"
        assert data["done"] is False
        assert "id" in data

    def test_empty_title_400(self, client):
        assert post_task(client, "   ").status_code == 400

    def test_missing_title_400(self, client):
        res = client.post("/tasks",
                          data=json.dumps({}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_no_body_400(self, client):
        assert client.post("/tasks").status_code == 400


class TestGetTask:
    def test_get_existing(self, client):
        post_task(client, "Buy milk")
        res = client.get("/tasks/1")
        assert res.status_code == 200
        assert res.get_json()["title"] == "Buy milk"

    def test_get_missing_404(self, client):
        assert client.get("/tasks/999").status_code == 404


class TestDeleteTask:
    def test_delete_existing(self, client):
        post_task(client, "Buy milk")
        assert client.delete("/tasks/1").status_code == 204
        assert client.get("/tasks/1").status_code == 404

    def test_delete_missing_404(self, client):
        assert client.delete("/tasks/999").status_code == 404
```

### Step 4 — Run everything locally first

```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate          # Windows

pip install -r app/requirements.txt -r requirements-dev.txt

# Lint
flake8 app/ tests/ --max-line-length=100

# Tests
pytest tests/ -v --cov=app --cov-report=term-missing
# All tests should pass before touching Docker or AWS
```

### Step 5 — Write the Dockerfile

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.12-slim
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
COPY --from=builder /install /usr/local
COPY app/ .
USER appuser
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "main:app"]
```

Test it locally:

```bash
docker build -t task-api:local .
docker run -d -p 8080:8080 --name task-test task-api:local

curl http://localhost:8080/health
# {"status": "ok", "version": "1.0.0"}

curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Test task"}'
# {"created_at": ..., "done": false, "id": 1, "title": "Test task"}

docker stop task-test && docker rm task-test
```

### Step 6 — Create AWS ECR repository

```bash
# Create the registry
aws ecr create-repository \
  --repository-name devops-project-03 \
  --region us-east-1 \
  --image-scanning-configuration scanOnPush=true

# Note the repositoryUri from the output:
# 123456789012.dkr.ecr.us-east-1.amazonaws.com/devops-project-03

# Save your account ID for later

```

### Step 7 — Create a dedicated IAM user for GitHub Actions

```bash
# Create user with minimal ECR permissions only
aws iam create-user --user-name github-actions-ecr

aws iam attach-user-policy --user-name github-actions-ecr --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess
  
  

# Create credentials — shown ONCE, copy immediately
aws iam create-access-key --user-name github-actions-ecr
```

### Step 8 — Add secrets to GitHub

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `AWS_ACCESS_KEY_ID` | AccessKeyId from Step 7 |
| `AWS_SECRET_ACCESS_KEY` | SecretAccessKey from Step 7 |
| `AWS_ACCOUNT_ID` | 12-digit account ID from Step 6 |

### Step 9 — Create the pipeline

`.github/workflows/ci-cd.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  IMAGE_URI: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/devops-project-03

jobs:
  test:
    name: Test and Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: |
            app/requirements.txt
            requirements-dev.txt

      - name: Install dependencies
        run: pip install -r app/requirements.txt -r requirements-dev.txt

      - name: Lint
        run: flake8 app/ tests/ --max-line-length=100

      - name: Test with coverage
        run: |
          pytest tests/ -v \
            --cov=app \
            --cov-report=term-missing \
            --cov-report=xml:coverage.xml \
            --cov-fail-under=80

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: coverage.xml

  build-and-scan:
    name: Build, Scan, Push to ECR
    runs-on: ubuntu-latest
    needs: test
    permissions:
      contents: read
      security-events: write

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Log in to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - uses: docker/setup-buildx-action@v3

      - name: Build image for scanning
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          load: true
          tags: ${{ env.IMAGE_URI }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.IMAGE_URI }}:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: HIGH,CRITICAL
          exit-code: "1"

      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif

      - name: Push to ECR (main branch + scan passed)
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ${{ env.IMAGE_URI }}:${{ github.sha }}
            ${{ env.IMAGE_URI }}:latest
          cache-from: type=gha

  notify:
    name: PR Summary
    runs-on: ubuntu-latest
    needs: [test, build-and-scan]
    if: github.event_name == 'pull_request'
    permissions:
      pull-requests: write
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: "✅ Tests passed · Trivy scan clean · Safe to merge."
            })
```

### Step 10 — Push and verify

```bash
git add .
git commit -m "project-03: Task API + CI/CD pipeline → AWS ECR"
git push -u origin main
```

Watch **Actions** tab. After it passes:

```bash
# Verify image is in ECR
aws ecr list-images --repository-name devops-project-03 --region us-east-1

# Pull and run from ECR
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

docker run -p 8080:8080 \
  $ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/devops-project-03:latest

curl http://localhost:8080/health
```

---

## Clean up (prevents ongoing AWS charges)

```bash
# Delete ECR repository and all images
aws ecr delete-repository \
  --repository-name devops-project-03 \
  --force --region us-east-1

# Delete IAM user
aws iam detach-user-policy \
  --user-name github-actions-ecr \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess

aws iam list-access-keys --user-name github-actions-ecr \
  --query 'AccessKeyMetadata[*].AccessKeyId' --output text | \
  tr '\t' '\n' | while read key; do
    aws iam delete-access-key \
      --user-name github-actions-ecr --access-key-id "$key"
  done

aws iam delete-user --user-name github-actions-ecr
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `AuthorizationException` in ECR login | AWS secrets wrong in GitHub — re-check Step 8 |
| `build-and-scan` runs even on test failure | `needs: test` missing from job definition |
| Trivy fails with real CVEs | Update base image: add `RUN apt-get update && apt-get upgrade -y` after FROM |
| `load: true` + `push: true` error | Can't combine — use two separate build steps (scan step uses `load`, push step uses `push`) |
| Coverage below 80% | Add more test cases or lower `--cov-fail-under` temporarily |

---

## Definition of done

- [ ] `curl http://localhost:8080/tasks` returns `{"count": 0, "tasks": []}` locally
- [ ] `pytest tests/ -v` passes with >80% coverage locally
- [ ] Docker image builds and app responds on port 8080
- [ ] ECR repository created in AWS console
- [ ] GitHub Actions secrets configured
- [ ] Pipeline passes all 3 jobs on push to main
- [ ] Deliberately broken test stops pipeline at Job 1 (image never built)
- [ ] Image visible in ECR with `:latest` and SHA tags
- [ ] AWS resources cleaned up

**Next:** [Project 4 — Kubernetes + Helm on EKS](../project-04-kubernetes-helm/README.md)
