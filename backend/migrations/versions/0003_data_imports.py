"""Track one-time demo initialization; preserve existing edited datasets."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table('data_imports',
        sa.Column('key', sa.String(64), primary_key=True),
        mysql_engine='InnoDB', mysql_charset='utf8mb4')
    # 已有安装即使删空地点也不重新灌入示例；管理员表保留其初始化历史。
    connection = op.get_bind()
    initialized = any(connection.execute(sa.text(f'SELECT COUNT(*) FROM {name}')).scalar()
                      for name in ('attractions', 'roads', 'admin_users'))
    if initialized:
        connection.execute(table.insert().values(key='course_demo_v1'))


def downgrade():
    op.drop_table('data_imports')
