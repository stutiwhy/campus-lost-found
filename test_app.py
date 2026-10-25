import pytest  # pyright: ignore[reportMissingImports]
import app as application


@pytest.fixture
def client(tmp_path, monkeypatch):
    database = tmp_path / "test.db"
    monkeypatch.setattr(application, "DATABASE", database)
    application.app.config["TESTING"] = True

    application.init_db()

    with application.app.test_client() as test_client:
        yield test_client


def report_data(**overrides):
    data = {
        "name": "Black Earphones",
        "report_type": "Found",
        "category": "Electronics",
        "description": "Black wireless earphones in a case",
        "location": "College library"
    }
    data.update(overrides)
    return data


def test_homepage_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Campus Lost & Found" in response.data


def test_report_is_saved(client):
    response = client.post("/report", data=report_data())

    assert response.status_code == 302

    page = client.get("/")
    assert b"Black Earphones" in page.data
    assert b"College library" in page.data


def test_empty_report_is_rejected(client):
    response = client.post("/report", data={
        "name": "",
        "report_type": "Found",
        "category": "Electronics",
        "description": "Earphones",
        "location": "Library"
    })

    assert response.status_code == 400
    assert b"All fields are required" in response.data


def test_invalid_category_is_rejected(client):
    response = client.post(
        "/report",
        data=report_data(category="Invalid Category")
    )

    assert response.status_code == 400
    assert b"valid category" in response.data


def test_search_finds_matching_item(client):
    client.post("/report", data=report_data())

    response = client.get("/?q=Earphones")
    assert response.status_code == 200
    assert b"Black Earphones" in response.data

    response = client.get("/?q=Textbook")
    assert b"Black Earphones" not in response.data


def test_resolve_item(client):
    client.post("/report", data=report_data())

    with application.get_db() as db:
        item_id = db.execute(
            "SELECT id FROM items"
        ).fetchone()["id"]

    response = client.post(f"/resolve/{item_id}")
    assert response.status_code == 302

    page = client.get("/?status=Resolved")
    assert b"Black Earphones" in page.data
    assert b"Resolved" in page.data


def test_unknown_item_returns_404(client):
    response = client.get("/item/99999")
    assert response.status_code == 404


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["database"] == "connected"

def test_invalid_report_type_is_rejected(client):
    response = client.post("/report", data=report_data(report_type="Stolen"))

    assert response.status_code == 400
    assert b"Lost or Found" in response.data


def test_overlong_field_is_rejected(client):
    response = client.post("/report", data=report_data(name="x" * 101))

    assert response.status_code == 400
    assert b"exceed the allowed length" in response.data


def test_item_detail_page(client):
    client.post("/report", data=report_data())

    response = client.get("/item/1")

    assert response.status_code == 200
    assert b"Black Earphones" in response.data


def test_type_and_category_filters(client):
    client.post("/report", data=report_data())
    client.post("/report", data=report_data(
        name="Blue Backpack", report_type="Lost", category="Bags"
    ))

    page = client.get("/?type=Lost")
    assert b"Blue Backpack" in page.data
    assert b"Black Earphones" not in page.data

    page = client.get("/?category=Electronics")
    assert b"Black Earphones" in page.data
    assert b"Blue Backpack" not in page.data


def test_resolved_items_hidden_from_default_view(client):
    client.post("/report", data=report_data())
    client.post("/resolve/1")

    assert b"Black Earphones" not in client.get("/").data
    assert b"Black Earphones" in client.get("/?status=All").data


def test_resolving_twice_shows_error(client):
    client.post("/report", data=report_data())
    client.post("/resolve/1")

    response = client.post("/resolve/1", follow_redirects=True)

    assert b"already resolved" in response.data


def test_html_in_report_is_escaped(client):
    client.post("/report", data=report_data(name="<script>alert(1)</script>"))

    page = client.get("/?status=All")

    assert b"<script>alert(1)</script>" not in page.data
    assert b"&lt;script&gt;" in page.data
