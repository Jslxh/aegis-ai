from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from app.database.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: Session, model_cls: type[ModelType]):
        self.session = session
        self.model_cls = model_cls

    def add(self, model: ModelType) -> ModelType:
        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)
        return model

    def get(self, id: Any) -> ModelType | None:
        return self.session.get(self.model_cls, id)

    def list(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        return (
            self.session.query(self.model_cls)
            .order_by(self.model_cls.id.desc())  # type: ignore[attr-defined]
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete(self, id: Any) -> bool:
        obj = self.get(id)
        if obj:
            self.session.delete(obj)
            self.session.flush()
            return True
        return False

    def count(self) -> int:
        return self.session.query(self.model_cls).count()
