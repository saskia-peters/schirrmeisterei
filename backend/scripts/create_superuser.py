import asyncio
import getpass
import uuid

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.models import User
from app.services.user_service import UserService


async def main() -> None:
    """Interactively create a superuser account and commit it to the database."""
    email = input("Email: ")
    name = input("Full name: ")
    pw = getpass.getpass("Password: ")
    async with AsyncSessionLocal() as db:
        service = UserService(db)
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
    print("Superuser created successfully")


asyncio.run(main())
