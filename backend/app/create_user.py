import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from app.database import engine, initialize_database, session_factory
from app.models import User
from app.security import password_hash


async def create_user(username: str, role: str, password: str) -> None:
    await initialize_database()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"User {username!r} already exists")
        session.add(
            User(
                username=username,
                hashed_password=password_hash.hash(password),
                role=role,
            )
        )
        await session.commit()
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a GridOps API user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", default="viewer")
    args = parser.parse_args()
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")
    if len(password) < 12:
        parser.error("Password must be at least 12 characters long")
    asyncio.run(create_user(args.username, args.role, password))
    print(f"Created user {args.username!r} with role {args.role!r}.")


if __name__ == "__main__":
    main()
