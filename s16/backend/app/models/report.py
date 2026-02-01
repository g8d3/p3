from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True)
    trader_address = Column(String, index=True, nullable=False)
    format = Column(String, nullable=False)  # 'html', 'pdf', 'json'
    file_path = Column(String, nullable=True)  # Path to stored file
    file_size = Column(Integer, nullable=True)  # Size in bytes
    content = Column(Text, nullable=True)  # For small reports stored in DB
    metadata = Column(JSON, nullable=True)  # Additional metadata as JSON
    data_period_start = Column(DateTime, nullable=True)
    data_period_end = Column(DateTime, nullable=True)
    total_trades = Column(Integer, nullable=True)
    total_volume = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # trader = relationship("Trader", back_populates="reports")  # Uncomment if Trader model exists

    def __repr__(self):
        return f"<Report(id='{self.id}', trader='{self.trader_address}', format='{self.format}')>"