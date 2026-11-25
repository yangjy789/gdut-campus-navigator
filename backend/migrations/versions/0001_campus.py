"""Initial campus tables, schema version 0001."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('attractions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column('code', sa.String(16), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('verification_status', sa.String(32), nullable=False),
        sa.CheckConstraint('id >= 0', name='ck_attraction_id'),
        sa.CheckConstraint('latitude IS NULL OR latitude BETWEEN -90 AND 90', name='ck_latitude'),
        sa.CheckConstraint('longitude IS NULL OR longitude BETWEEN -180 AND 180', name='ck_longitude'),
        sa.CheckConstraint("verification_status = 'demo_only'", name='ck_demo_place'),
        mysql_engine='InnoDB', mysql_charset='utf8mb4')
    op.create_table('roads',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column('start_id', sa.Integer(), sa.ForeignKey('attractions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('end_id', sa.Integer(), sa.ForeignKey('attractions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('distance_m', sa.Integer(), nullable=False),
        sa.Column('bidirectional', sa.Boolean(), nullable=False),
        sa.Column('verification_status', sa.String(32), nullable=False),
        sa.CheckConstraint('start_id < end_id', name='ck_road_order'),
        sa.CheckConstraint('distance_m > 0', name='ck_road_distance'),
        sa.UniqueConstraint('start_id', 'end_id', name='uq_road_endpoints'),
        mysql_engine='InnoDB', mysql_charset='utf8mb4')


def downgrade():
    op.drop_table('roads')
    op.drop_table('attractions')
