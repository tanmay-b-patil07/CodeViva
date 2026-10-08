from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so they are registered in Base.metadata.
from app.db import models  # noqa: E402, F401