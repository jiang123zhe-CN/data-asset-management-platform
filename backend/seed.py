import asyncio

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User


async def seed():
    """Create default admin user if not exists."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                display_name="系统管理员",
                email="admin@example.com",
            )
            db.add(admin)
            db.commit()
            print("Default admin user created: admin / admin123")

        # Create sample users for each role if they don't exist
        sample_users = [
            ("data_entry", "录入员"),
            ("data_admin", "数据管理员"),
            ("reviewer", "复核员"),
        ]
        for role, display_name in sample_users:
            exists = db.query(User).filter(User.username == role).first()
            if not exists:
                user = User(
                    username=role,
                    hashed_password=hash_password("admin123"),
                    role=role,
                    display_name=display_name,
                )
                db.add(user)
        db.commit()
        print("Sample users seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed())
