"""One-shot database initialisation script.

Run once (or after a db-reset) to:
  1. Generate the organisation hierarchy XLSX from backend/data/seed/organisations.yaml
  2. Generate an example user-bulk-upload XLSX (backend/data/example_users.xlsx)
  3. Apply all Alembic migrations (alembic upgrade head)
  4. Create a superuser account interactively

Usage (from the repo root via just):
    just init-db
"""
import asyncio
import getpass
import subprocess
import sys
import uuid
from pathlib import Path

import yaml
from openpyxl import Workbook

# ─── Paths ────────────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
SEED_DIR = DATA_DIR / "seed"


def _load_seed(name: str) -> dict:  # type: ignore[type-arg]
    """Load a YAML seed file from backend/data/seed/."""
    with open(SEED_DIR / name) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _autosize_columns(ws: object) -> None:
    """Set column widths based on the longest cell value in each column."""
    for col in ws.columns:  # type: ignore[attr-defined]
        max_len = max(len(str(cell.value or "")) for cell in col) + 2
        ws.column_dimensions[col[0].column_letter].width = max_len  # type: ignore[index]


def generate_hierarchy_xlsx() -> Path:
    """Write organisation_hierarchy.xlsx to backend/data/ and return its path.

    Reads from backend/data/seed/organisations.yaml as the single source of
    truth.  The generated XLSX can also be re-imported at any time via the
    admin hierarchy-upload endpoint.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / "organisation_hierarchy.xlsx"
    hierarchy = _load_seed("organisations.yaml").get("hierarchy", [])
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Hierarchy"
    ws.append(["level", "name", "parent_name"])
    for entry in hierarchy:
        ws.append([entry["level"], entry["name"], entry.get("parent", "")])
    _autosize_columns(ws)
    wb.save(dest)
    print(f"  ✔ Created {dest.relative_to(BACKEND_DIR.parent)}")
    return dest


def generate_example_users_xlsx() -> Path:
    """Write example_users.xlsx to backend/data/ and return its path.

    The file demonstrates the format expected by POST /admin/users/bulk-upload.
    Required columns: email, full_name, password
    Optional column:  organization_id
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / "example_users.xlsx"
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Users"
    ws.append(["email", "full_name", "password", "organization_id"])
    example_rows = [
        ("max.mustermann@example.com", "Max Mustermann", "Passwort123!", ""),
        ("anna.schmidt@example.com", "Anna Schmidt", "Sicher456#", ""),
        ("tom.mueller@example.com", "Tom Müller", "Geheim789$", ""),
        ("lisa.wagner@example.com", "Lisa Wagner", "Hallo2024!", ""),
        ("felix.bauer@example.com", "Felix Bauer", "Test5678@", ""),
    ]
    for row in example_rows:
        ws.append(list(row))
    _autosize_columns(ws)

    # Add a note in an empty row explaining optional column
    ws.append([])
    ws.append(["# Notes:"])
    ws.append(["# - organization_id is optional; leave empty to inherit from uploader's org"])
    ws.append(["# - password must be at least 8 characters"])
    ws.append(["# - email must be unique"])
    wb.save(dest)
    print(f"  ✔ Created {dest.relative_to(BACKEND_DIR.parent)}")
    return dest


def run_migrations() -> None:
    """Run alembic upgrade head from the backend directory."""
    print("\n  Running database migrations…")
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**__import__("os").environ, "UV_PYTHON": "3.13"},
    )
    if result.returncode != 0:
        print("  ✘ Migration failed.")
        sys.exit(result.returncode)
    print("  ✔ Migrations applied.")


async def create_superuser() -> None:
    """Interactively create a superuser account."""
    from app.core.security import get_password_hash
    from app.db.session import AsyncSessionLocal
    from app.models.models import User
    from app.services.user_service import UserService

    print("\n  Creating superuser account…")
    email = input("  Email: ").strip()
    name = input("  Full name: ").strip()
    pw = getpass.getpass("  Password: ")

    async with AsyncSessionLocal() as db:
        service = UserService(db)

        existing = await service.get_by_email(email)
        if existing:
            print(f"  ⚠  User {email} already exists — skipping.")
            return

        await service.ensure_core_groups()
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=name,
            hashed_password=get_password_hash(pw),
            is_superuser=True,
        )
        db.add(user)
        await db.flush()
        await service.assign_groups(user, {"helfende", "admin"})
        await db.commit()
    print(f"  ✔ Superuser {email} created.")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run all initialisation steps."""
    print("=== TicketSystem — Database Initialisation ===\n")

    print("1/3  Generating data files…")
    generate_hierarchy_xlsx()
    generate_example_users_xlsx()

    print("\n2/3  Running migrations…")
    run_migrations()

    print("\n3/3  Superuser setup…")
    asyncio.run(create_superuser())

    print("\n✅  Initialisation complete.")
    print("    Default admin:  superadmin@example.com / superadmin  (force password change on first login)")


if __name__ == "__main__":
    main()
