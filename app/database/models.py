from datetime import datetime
from sqlalchemy import String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TradeLog(Base):
    __tablename__ = 'trade_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pair: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(8))
    strategy: Mapped[str] = mapped_column(String(64))
    regime: Mapped[str] = mapped_column(String(64))
    entry: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    tp1: Mapped[float] = mapped_column(Float)
    tp2: Mapped[float] = mapped_column(Float)
    tp3: Mapped[float] = mapped_column(Float)
    risk_usd: Mapped[float] = mapped_column(Float)
    position_size: Mapped[float] = mapped_column(Float)
    leverage: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    consensus: Mapped[float] = mapped_column(Float)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default='created')
    notes: Mapped[str] = mapped_column(Text, default='')

class BotState(Base):
    __tablename__ = 'bot_state'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)

class PaperTrade(Base):
    __tablename__ = 'paper_trades'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    exchange: Mapped[str] = mapped_column(String(32), default='bitget')
    pair: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(8))
    strategy: Mapped[str] = mapped_column(String(64))
    regime: Mapped[str] = mapped_column(String(64))

    entry: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    tp1: Mapped[float] = mapped_column(Float)
    tp2: Mapped[float] = mapped_column(Float)
    tp3: Mapped[float] = mapped_column(Float)

    amount: Mapped[float] = mapped_column(Float)
    risk_usd: Mapped[float] = mapped_column(Float)
    pnl_usd: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)

    confidence: Mapped[float] = mapped_column(Float)
    consensus: Mapped[float] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(32), default='open')
    close_reason: Mapped[str] = mapped_column(String(32), default='')
    notes: Mapped[str] = mapped_column(Text, default='')
