

from sqlalchemy import Column, Integer, String
from .Base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)

    def __repr__(self):
        return f"<User(username='{self.username}', password='{self.password}'>)"