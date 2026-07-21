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
