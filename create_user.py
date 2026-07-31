import sys
import argparse
from app.database.session import SessionLocal
from app.database.repositories.user_repository import UserRepository

def main():
    parser = argparse.ArgumentParser(description="Create a new Guardrail AI user")
    parser.add_argument("--username", required=True, help="Username for the new user")
    parser.add_argument("--email", required=True, help="Email address for the new user")
    parser.add_argument("--password", required=True, help="Password for the new user")
    parser.add_argument(
        "--role",
        default="viewer",
        choices=["viewer", "operator", "auditor", "security_analyst", "admin"],
        help="Role of the new user (default: viewer)",
    )

    args = parser.parse_args()

    session = SessionLocal()
    try:
        repo = UserRepository(session)
        if repo.find_by_username(args.username):
            print(f"Error: User with username '{args.username}' already exists.", file=sys.stderr)
            sys.exit(1)
        if repo.find_by_email(args.email):
            print(f"Error: User with email '{args.email}' already exists.", file=sys.stderr)
            sys.exit(1)

        user = repo.create_user(
            username=args.username,
            email=args.email,
            password=args.password,
            role=args.role,
        )
        session.commit()
        print(f"Success: Created user '{user.username}' with role '{user.role}'.")
    except Exception as e:
        session.rollback()
        print(f"Error: Failed to create user: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()
