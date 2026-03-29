import pytest
from httpx import AsyncClient

from app.models.models import User


@pytest.mark.asyncio
class TestTicketsCRUD:
    async def test_create_ticket(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Test Ticket", "description": "This is a test ticket"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Ticket"
        assert data["status"] == "new"
        assert len(data["status_logs"]) == 1
        assert data["status_logs"][0]["to_status"] == "new"
        assert data["status_logs"][0]["note"] == "Ticket created"

    async def test_list_tickets(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post(
            "/api/v1/tickets/",
            json={"title": "Ticket 1", "description": "Desc 1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/tickets/",
            json={"title": "Ticket 2", "description": "Desc 2"},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/tickets/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_get_ticket(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Get Me", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/tickets/{ticket_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == ticket_id

    async def test_get_ticket_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get(
            "/api/v1/tickets/nonexistent-id", headers=auth_headers
        )
        assert response.status_code == 404

    async def test_update_ticket(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Original", "description": "Original desc"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tickets/{ticket_id}",
            json={"title": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    async def test_update_ticket_status_creates_log(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Status Test", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tickets/{ticket_id}/status",
            json={"status": "working", "note": "Starting work"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "working"

        logs = [
            log
            for log in data["status_logs"]
            if log["to_status"] == "working" and log["note"] == "Starting work"
        ]
        assert len(logs) == 1
        assert logs[0]["from_status"] in {"new", None}

    async def test_delete_ticket_by_creator(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Delete Me", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/tickets/{ticket_id}", headers=auth_headers
        )
        assert response.status_code == 204

    async def test_close_ticket_forbidden_for_helfende_only(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Close Test", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tickets/{ticket_id}/status",
            json={"status": "closed", "note": "Attempt close"},
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_waiting_status_requires_waiting_for_note(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Wait Test", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tickets/{ticket_id}/status",
            json={"status": "waiting"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_close_ticket_allowed_for_schirrmeister(
        self, client: AsyncClient, schirrmeister_headers: dict[str, str], auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Close Test", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tickets/{ticket_id}/status",
            json={"status": "closed", "note": "Closing as schirrmeister"},
            headers=schirrmeister_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "closed"

    async def test_close_ticket_allowed_for_admin(
        self, client: AsyncClient, admin_headers: dict[str, str], auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Close Test", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tickets/{ticket_id}/status",
            json={"status": "closed", "note": "Closing as admin"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "closed"

    async def test_unauthenticated_access(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/tickets/")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestKanbanBoard:
    async def test_kanban_board_structure(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post(
            "/api/v1/tickets/",
            json={"title": "New Ticket", "description": "Test"},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/tickets/board", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "new" in data
        assert "working" in data
        assert "waiting" in data
        assert "resolved" in data
        assert "closed" in data
        assert len(data["new"]) >= 1


@pytest.mark.asyncio
class TestComments:
    async def test_add_and_list_comments(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Comment Test", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            json={"content": "This is a comment"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["content"] == "This is a comment"

        ticket_response = await client.get(
            f"/api/v1/tickets/{ticket_id}", headers=auth_headers
        )
        assert len(ticket_response.json()["comments"]) == 1

    async def test_delete_comment(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tickets/",
            json={"title": "Comment Delete Test", "description": "Test"},
            headers=auth_headers,
        )
        ticket_id = create_response.json()["id"]

        comment_response = await client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            json={"content": "To be deleted"},
            headers=auth_headers,
        )
        comment_id = comment_response.json()["id"]

        response = await client.delete(
            f"/api/v1/tickets/{ticket_id}/comments/{comment_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
