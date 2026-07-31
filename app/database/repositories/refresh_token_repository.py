from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models.refresh_token import RefreshTokenModel
from app.database.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshTokenModel]):
    def __init__(self, session: Session):
        super().__init__(session, RefreshTokenModel)

    def find_by_hash(self, token_hash: str) -> Optional[RefreshTokenModel]:
        return (
            self.session.query(RefreshTokenModel)
            .filter(RefreshTokenModel.token_hash == token_hash)
            .first()
        )

    def create_token(
        self, token_hash: str, user_id: int, expires_at: datetime
    ) -> RefreshTokenModel:
        model = RefreshTokenModel(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
        )
        return self.add(model)

    def revoke_token(self, token_hash: str) -> Optional[RefreshTokenModel]:
        model = self.find_by_hash(token_hash)
        if model:
            model.revoked = True
            self.session.flush()
        return model

    def revoke_all_for_user(self, user_id: int) -> None:
        self.session.query(RefreshTokenModel).filter(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.revoked.is_(False),
        ).update({"revoked": True})
        self.session.flush()
