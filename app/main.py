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
