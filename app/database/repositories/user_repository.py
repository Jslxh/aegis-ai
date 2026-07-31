from typing import Optional

from sqlalchemy.orm import Session

from app.database.models.user import UserModel
from app.database.repositories.base import BaseRepository
from app.auth.security import hash_password


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, session: Session):
        super().__init__(session, UserModel)

    def find_by_username(self, username: str) -> Optional[UserModel]:
        return (
            self.session.query(UserModel)
            .filter(UserModel.username == username)
            .first()
        )

    def find_by_email(self, email: str) -> Optional[UserModel]:
        return (
            self.session.query(UserModel)
            .filter(UserModel.email == email)
            .first()
        )

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "viewer",
    ) -> UserModel:
        model = UserModel(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
        return self.add(model)
