
"""API tests using an isolated SQLite database."""

import os

# Set this before importing the application.
os.environ["DATABASE_URL"] = "sqlite:///./ci_test.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    """Provide a test-only database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    """Create a client with a fresh database for each test."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def register_user(client, username="testuser", email="test@example.com"):
    """Register a test user and return the response."""
    return client.post(
        "/api/register/",
        json={
            "username": username,
            "email": email,
            "password": "TestPassword123!",
        },
    )


def login_user(client, email="test@example.com"):
    """Log in and return the token response."""
    return client.post(
        "/api/token/",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )


def auth_headers(client):
    """Register and authenticate a user for protected requests."""
    register_response = register_user(client)
    assert register_response.status_code == 201

    login_response = login_user(client)
    assert login_response.status_code == 200

    access_token = login_response.json()["access"]
    return {"Authorization": f"Bearer {access_token}"}


def test_health_endpoint(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint(client):
    response = client.get("/readiness/")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_register_user(client):
    response = register_user(client)

    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
    assert response.json()["email"] == "test@example.com"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_register_duplicate_email(client):
    assert register_user(client).status_code == 201

    response = register_user(
        client,
        username="anotheruser",
        email="test@example.com",
    )
    assert response.status_code == 409


def test_register_duplicate_username(client):
    assert register_user(client).status_code == 201

    response = register_user(
        client,
        username="testuser",
        email="another@example.com",
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/register/",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


def test_login_success(client):
    register_user(client)

    response = login_user(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access"]
    assert response.json()["refresh"]


def test_login_rejects_wrong_password(client):
    register_user(client)

    response = client.post(
        "/api/token/",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401


def test_refresh_token(client):
    register_user(client)
    tokens = login_user(client).json()

    response = client.post(
        "/api/token/refresh/",
        json={"refresh": tokens["refresh"]},
    )

    assert response.status_code == 200
    assert response.json()["access"]
    assert response.json()["refresh"]


def test_refresh_rejects_access_token(client):
    register_user(client)
    tokens = login_user(client).json()

    response = client.post(
        "/api/token/refresh/",
        json={"refresh": tokens["access"]},
    )

    assert response.status_code == 401


def test_list_posts_without_login(client):
    response = client.get("/posts/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_post_requires_login(client):
    response = client.post(
        "/posts/",
        json={"title": "My first post", "content": "Hello world"},
    )

    assert response.status_code == 401


def test_create_and_list_post(client):
    headers = auth_headers(client)

    create_response = client.post(
        "/posts/",
        headers=headers,
        json={"title": "My first post", "content": "Hello world"},
    )

    assert create_response.status_code == 201
    assert create_response.json()["title"] == "My first post"
    assert create_response.json()["author_username"] == "testuser"

    list_response = client.get("/posts/")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_comment_and_list_comments(client):
    headers = auth_headers(client)

    post_response = client.post(
        "/posts/",
        headers=headers,
        json={"title": "Test post", "content": "Post content"},
    )
    assert post_response.status_code == 201
    post_id = post_response.json()["id"]

    comment_response = client.post(
        f"/posts/{post_id}/comments/",
        headers=headers,
        json={"content": "Great post!"},
    )

    assert comment_response.status_code == 201
    assert comment_response.json()["content"] == "Great post!"

    list_response = client.get(f"/posts/{post_id}/comments/")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_comment_requires_login(client):
    register_user(client)
    headers = login_user(client).json()
    access_token = headers["access"]

    post_response = client.post(
        "/posts/",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": "Test post", "content": "Post content"},
    )
    post_id = post_response.json()["id"]

    response = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Anonymous comment"},
    )

    assert response.status_code == 401


def test_comment_for_missing_post(client):
    headers = auth_headers(client)

    response = client.post(
        "/posts/9999/comments/",
        headers=headers,
        json={"content": "This post does not exist"},
    )

    assert response.status_code == 404