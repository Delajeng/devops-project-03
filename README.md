# Project 3 — Full CI/CD Pipeline with Automated Testing

## What was buildt

A production-grade CI/CD pipeline around a Python Flask task API — a small but real app with multiple endpoints. The pipeline runs tests, lints the code, scans the Docker image for vulnerabilities, and pushes to AWS ECR. A failing test stops the build before an image is ever created.

## What was learnt

- Writing a testable Python Flask API from scratch
- Multi-job GitHub Actions pipelines with dependency gates
- Unit testing with pytest and coverage enforcement
- Docker image vulnerability scanning with Trivy
- Pushing Docker images to AWS ECR
- PR vs. main branch pipeline behaviour

## The app: Task API

A simple REST API that manages tasks in memory.

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

