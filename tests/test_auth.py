"""Integration tests for auth and user profile endpoints."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.db import get_session
from app.models import User
from app.auth import hash_password, create_access_token

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="session")
def session_fixture():
    """Provide an in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Provide a TestClient with the in-memory database injected."""

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="registered_user")
def registered_user_fixture(session: Session) -> tuple[User, str]:
    """Create a test user and return (user, token)."""
    user = User(
        email="profile-test@example.com",
        hashed_password=hash_password("testpassword"),
        name="Profile Test User",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(user.id)
    return user, token


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(registered_user: tuple[User, str]) -> dict:
    """Return Bearer auth headers for the test user."""
    _, token = registered_user
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /auth/register and POST /auth/login
# ---------------------------------------------------------------------------


def test_register_user(client: TestClient) -> None:
    """POST /auth/register should create a new user and return its data."""
    payload = {"email": "new@example.com", "password": "securepass", "name": "New User"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["name"] == "New User"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient) -> None:
    """POST /auth/register with a duplicate email should return 409."""
    payload = {"email": "dup@example.com", "password": "securepass"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409


def test_login_success(client: TestClient, registered_user: tuple[User, str]) -> None:
    """POST /auth/login with valid credentials should return an access token."""
    response = client.post(
        "/auth/login",
        json={"email": "profile-test@example.com", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient) -> None:
    """POST /auth/login with wrong password should return 401."""
    response = client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me/profile
# ---------------------------------------------------------------------------


def test_get_profile_authenticated(
    client: TestClient, auth_headers: dict, registered_user: tuple[User, str]
) -> None:
    """GET /auth/me/profile should return the authenticated user's profile."""
    user, _ = registered_user
    response = client.get("/auth/me/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert data["name"] == user.name


def test_get_profile_unauthenticated(client: TestClient) -> None:
    """GET /auth/me/profile without a token should return 401 or 403."""
    response = client.get("/auth/me/profile")
    assert response.status_code in (401, 403)


_EXPECTED_PROFILE_FIELDS = (
    "phone", "bio", "location", "website", "linkedin_url", "github_url", "resume_text"
)


def test_get_profile_returns_profile_fields(
    client: TestClient, auth_headers: dict
) -> None:
    """GET /auth/me/profile response includes all expected profile fields."""
    response = client.get("/auth/me/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    for field in _EXPECTED_PROFILE_FIELDS:
        assert field in data


# ---------------------------------------------------------------------------
# PATCH /auth/me/profile
# ---------------------------------------------------------------------------


def test_update_profile_basic_fields(
    client: TestClient, auth_headers: dict
) -> None:
    """PATCH /auth/me/profile should update basic string fields."""
    payload = {
        "bio": "Software engineer",
        "location": "San Francisco, CA",
        "phone": "+15551234567",
    }
    response = client.patch("/auth/me/profile", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "Software engineer"
    assert data["location"] == "San Francisco, CA"
    assert data["phone"] == "+15551234567"


def test_update_profile_partial(
    client: TestClient, auth_headers: dict
) -> None:
    """PATCH /auth/me/profile should support partial updates without clearing unset fields."""
    # First update: set bio
    client.patch("/auth/me/profile", json={"bio": "First bio"}, headers=auth_headers)
    # Second update: set location only; bio should remain
    response = client.patch(
        "/auth/me/profile", json={"location": "New York"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "First bio"
    assert data["location"] == "New York"


def test_update_profile_no_fields(
    client: TestClient, auth_headers: dict
) -> None:
    """PATCH /auth/me/profile with no fields should return 400."""
    response = client.patch("/auth/me/profile", json={}, headers=auth_headers)
    assert response.status_code == 400


def test_update_profile_unauthenticated(client: TestClient) -> None:
    """PATCH /auth/me/profile without a token should return 401 or 403."""
    response = client.patch("/auth/me/profile", json={"bio": "test"})
    assert response.status_code in (401, 403)


def test_update_profile_sets_updated_at(
    client: TestClient, auth_headers: dict
) -> None:
    """PATCH /auth/me/profile should set updated_at on the user."""
    response = client.patch(
        "/auth/me/profile", json={"bio": "has timestamp"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_at"] is not None


# ---------------------------------------------------------------------------
# Skills encoding / decoding
# ---------------------------------------------------------------------------


def test_update_profile_skills_list(
    client: TestClient, auth_headers: dict
) -> None:
    """PATCH /auth/me/profile with a skills list should persist and return it as a list."""
    skills = ["Python", "FastAPI", "Docker"]
    response = client.patch(
        "/auth/me/profile", json={"skills": skills}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["skills"], list)
    assert data["skills"] == skills


def test_update_profile_skills_empty_list(
    client: TestClient, auth_headers: dict
) -> None:
    """PATCH /auth/me/profile with an empty skills list should store and return an empty list."""
    response = client.patch(
        "/auth/me/profile", json={"skills": []}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["skills"] == []


def test_get_profile_skills_decoding(
    client: TestClient, session: Session, auth_headers: dict, registered_user: tuple[User, str]
) -> None:
    """GET /auth/me/profile should decode skills_json stored as a JSON string into a list."""
    user, _ = registered_user
    # Directly write a JSON-encoded string into the DB to simulate stored data
    user.skills_json = json.dumps(["Go", "Kubernetes", "Terraform"])
    session.add(user)
    session.commit()

    response = client.get("/auth/me/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["skills"], list)
    assert data["skills"] == ["Go", "Kubernetes", "Terraform"]


def test_update_profile_skills_roundtrip(
    client: TestClient, auth_headers: dict
) -> None:
    """Skills set via PATCH should be returned correctly by GET /auth/me/profile."""
    skills = ["React", "TypeScript", "Node.js"]
    client.patch("/auth/me/profile", json={"skills": skills}, headers=auth_headers)
    response = client.get("/auth/me/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["skills"] == skills


# ---------------------------------------------------------------------------
# GET /auth/me/token
# ---------------------------------------------------------------------------


def test_get_me_token(client: TestClient, auth_headers: dict) -> None:
    """GET /auth/me/token should return a new access token."""
    response = client.get("/auth/me/token", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
