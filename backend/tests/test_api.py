from pathlib import Path

from app.config import settings

from .conftest import make_png

GOOD_ENQUIRY = dict(
    name="Ahmed Ali",
    phone="+20 100 123 4567",
    email="a@b.com",
    country="eg",
    service="fitout",
    consent=True,
)


def test_bootstrap_has_seed_data_and_etag(client):
    r = client.get("/api/bootstrap")
    assert r.status_code == 200
    data = r.json()
    assert len(data["projects"]) == 9
    assert {o["country"] for o in data["offices"]} == {"eg", "qa"}
    assert len(data["clients"]) == 12
    r2 = client.get("/api/bootstrap", headers={"If-None-Match": r.headers["etag"]})
    assert r2.status_code == 304


def test_enquiry_validation(client):
    assert client.post("/api/enquiries", json=GOOD_ENQUIRY).status_code == 201
    for bad in (
        {**GOOD_ENQUIRY, "name": "A"},
        {**GOOD_ENQUIRY, "phone": "12"},
        {**GOOD_ENQUIRY, "email": "nope"},
        {**GOOD_ENQUIRY, "country": "xx"},
        {**GOOD_ENQUIRY, "consent": False},
        {**GOOD_ENQUIRY, "area_m2": -4},
    ):
        assert client.post("/api/enquiries", json=bad).status_code == 422


def test_enquiry_honeypot_and_rate_limit(client, auth):
    before = len(client.get("/api/admin/enquiries", headers=auth).json())
    assert client.post("/api/enquiries", json={**GOOD_ENQUIRY, "website": "http://spam"}).status_code == 201
    assert len(client.get("/api/admin/enquiries", headers=auth).json()) == before
    codes = [client.post("/api/enquiries", json=GOOD_ENQUIRY).status_code for _ in range(7)]
    assert codes[:5] == [201] * 5 and codes[5] == 429


def test_admin_requires_auth(client):
    assert client.get("/api/admin/projects").status_code == 401
    assert client.post("/api/admin/login", json={"email": "admin@test.com", "password": "bad"}).status_code == 401


def test_login_rate_limit(client):
    codes = [
        client.post("/api/admin/login", json={"email": "x@y.com", "password": "bad"}).status_code for _ in range(10)
    ]
    assert codes[-1] == 429


def test_project_crud_and_images(client, auth):
    r = client.post(
        "/api/admin/projects",
        headers=auth,
        json=dict(title_en="Villa Test", country="eg", type="residential", year=2025),
    )
    assert r.status_code == 201
    p = r.json()
    assert p["slug"] == "villa-test"
    pid = p["id"]

    files = [("files", ("a.png", make_png(), "image/png")), ("files", ("b.png", make_png(800, 1000), "image/png"))]
    up = client.post(f"/api/admin/projects/{pid}/images", headers=auth, files=files)
    assert up.status_code == 201
    imgs = up.json()
    assert imgs[0]["is_cover"] and not imgs[1]["is_cover"]
    key_dir = Path(settings.upload_dir)
    assert any(key_dir.iterdir())

    # public detail exposes the gallery and responsive variants
    d = client.get("/api/projects/villa-test").json()
    assert d["cover"]["srcset"].count("w") >= 2 and len(d["gallery"]) == 2

    # switching cover keeps exactly one cover
    client.patch(f"/api/admin/project-images/{imgs[1]['id']}", headers=auth, json={"is_cover": True})
    covers = [i["is_cover"] for i in client.get(f"/api/admin/projects/{pid}", headers=auth).json()["images"]]
    assert covers.count(True) == 1

    # unpublished projects are hidden from the public API
    body = {**p, "published": False}
    assert client.put(f"/api/admin/projects/{pid}", headers=auth, json=body).status_code == 200
    assert client.get("/api/projects/villa-test").status_code == 404

    before = {x.name for x in key_dir.iterdir()}
    assert client.delete(f"/api/admin/projects/{pid}", headers=auth).status_code == 204
    after = {x.name for x in key_dir.iterdir()}
    assert len(after) == len(before) - 2  # image files cleaned up


def test_rejects_non_images(client, auth):
    pid = client.post(
        "/api/admin/projects", headers=auth, json=dict(title_en="X", country="qa", type="office")
    ).json()["id"]
    r = client.post(
        f"/api/admin/projects/{pid}/images", headers=auth, files=[("files", ("x.png", b"not an image", "image/png"))]
    )
    assert r.status_code == 400


def test_site_image_slot_and_client_logo(client, auth):
    assert client.put(
        "/api/admin/site-images/nope", headers=auth, files={"file": ("a.png", make_png(), "image/png")}
    ).status_code == 404
    r = client.put(
        "/api/admin/site-images/home-hero", headers=auth, files={"file": ("a.png", make_png(), "image/png")}
    )
    assert r.status_code == 200
    assert "home-hero" in client.get("/api/bootstrap").json()["site_images"]

    c = client.post("/api/admin/clients", headers=auth, json={"name": "ACME"}).json()
    r = client.post(
        f"/api/admin/clients/{c['id']}/logo", headers=auth, files={"file": ("l.png", make_png(600, 200), "image/png")}
    )
    assert r.status_code == 200 and r.json()["logo"]["src"].startswith("/media/")


def test_media_is_cached(client, auth):
    src = client.get("/api/bootstrap").json()["site_images"]["home-hero"]["image"]["src"]
    r = client.get(src)
    assert r.status_code == 200 and "immutable" in r.headers["cache-control"]


def test_unknown_api_path_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["detail"] == "Not found"
