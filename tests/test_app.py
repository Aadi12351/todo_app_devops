
import importlib


def test_home_page(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_PATH",
        str(tmp_path / "test.db")
    )

    import app
    importlib.reload(app)

    client = app.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"My DevOps To-Do App" in response.data


def test_add_task(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_PATH",
        str(tmp_path / "test.db")
    )

    import app
    importlib.reload(app)

    client = app.app.test_client()

    response = client.post(
        "/add",
        data={"title": "Learn Jenkins"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Learn Jenkins" in response.data


def test_complete_and_delete_task(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_PATH",
        str(tmp_path / "test.db")
    )

    import app
    importlib.reload(app)

    client = app.app.test_client()

    client.post(
        "/add",
        data={"title": "Learn Kubernetes"}
    )

    response = client.post(
        "/complete/1",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.get_db() as connection:
        task = connection.execute(
            "SELECT completed FROM tasks WHERE id = 1"
        ).fetchone()

    assert task["completed"] == 1

    response = client.post(
        "/delete/1",
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Learn Kubernetes" not in response.data
