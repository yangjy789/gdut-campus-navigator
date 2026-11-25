"""Add the unified campus catalog without modifying existing algorithm fixtures."""
from alembic import op
import sqlalchemy as sa
import json
from pathlib import Path

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table('campus_places',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        mysql_engine='InnoDB', mysql_charset='utf8mb4')
    source = Path(__file__).resolve().parents[3] / 'data/public_campus/campus.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    op.bulk_insert(table, [{'id':p['id'],'payload':p} for p in data['places']])
    op.get_bind().execute(sa.text("INSERT INTO data_imports (`key`) VALUES ('public_campus_2026_v1')"))


def downgrade():
    op.get_bind().execute(sa.text("DELETE FROM data_imports WHERE `key` = 'public_campus_2026_v1'"))
    op.drop_table('campus_places')
