from sqlalchemy import Column, Date, Integer, Numeric, String
from .Base import Base

class ElecPrice(Base):

    __tablename__ = 'prices'

    id = Column(Integer, primary_key=True)
    interval = Column(String)
    price = Column(Numeric, nullable=False)
    date = Column(Date)

    def __repr__(self):
        return f"<Price(interval='{self.interval}', amount='{self.price}')>"