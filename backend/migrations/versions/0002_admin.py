"""Add administrator accounts and revocable sessions."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('admin_users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(64), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        mysql_engine='InnoDB', mysql_charset='utf8mb4')
    op.create_table('admin_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('admin_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        mysql_engine='InnoDB', mysql_charset='utf8mb4')
    op.create_index('ix_admin_sessions_expires_at', 'admin_sessions', ['expires_at'])


def downgrade():
    op.drop_table('admin_sessions')
    op.drop_table('admin_users')
