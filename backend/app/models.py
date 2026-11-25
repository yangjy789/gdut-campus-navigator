"""数据库表结构；地点与双向道路先独立保存。"""
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DataImport(Base):
    """事务内记录一次性数据初始化，避免重启复活用户删除的数据。"""
    __tablename__ = 'data_imports'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)


class CampusPlace(Base):
    """访客与后台共用的校园目录，保留来源与图上位置元数据。"""
    __tablename__ = 'campus_places'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class Attraction(Base):
    __tablename__ = 'attractions'
    __table_args__ = (
        CheckConstraint('id >= 0', name='ck_attraction_id'),
        CheckConstraint('latitude IS NULL OR latitude BETWEEN -90 AND 90', name='ck_latitude'),
        CheckConstraint('longitude IS NULL OR longitude BETWEEN -180 AND 180', name='ck_longitude'),
        CheckConstraint("verification_status = 'demo_only'", name='ck_demo_place'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default='demo_only')


class Road(Base):
    __tablename__ = 'roads'
    __table_args__ = (
        CheckConstraint('start_id < end_id', name='ck_road_order'),
        CheckConstraint('distance_m > 0', name='ck_road_distance'),
        UniqueConstraint('start_id', 'end_id', name='uq_road_endpoints'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    start_id: Mapped[int] = mapped_column(ForeignKey('attractions.id', ondelete='RESTRICT'))
    end_id: Mapped[int] = mapped_column(ForeignKey('attractions.id', ondelete='RESTRICT'))
    distance_m: Mapped[int] = mapped_column(Integer)
    bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_status: Mapped[str] = mapped_column(String(32), default='demo_only')


class AdminUser(Base):
    __tablename__ = 'admin_users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AdminSession(Base):
    __tablename__ = 'admin_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('admin_users.id', ondelete='CASCADE'))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
