import logging
from app.database.session import SessionLocal, engine, Base
from app.database.repositories.user_repository import UserRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_db")

def seed():
    # Make sure tables are created
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")
    
    session = SessionLocal()
    try:
        repo = UserRepository(session)
        default_users = [
            ("admin", "admin", "admin@example.com"),
            ("security_analyst", "security_analyst", "analyst@example.com"),
            ("auditor", "auditor", "auditor@example.com"),
            ("operator", "operator", "operator@example.com"),
            ("viewer", "viewer", "viewer@example.com"),
        ]
        
        for username, role, email in default_users:
            existing = repo.find_by_username(username)
            if not existing:
                password = username
                repo.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=role
                )
                logger.info(f"Created user: {username} with role {role} and password {password}")
            else:
                logger.info(f"User {username} already exists")
        session.commit()
        logger.info("Database seeding completed successfully.")
    except Exception as e:
        session.rollback()
        logger.error(f"Seeding failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed()
