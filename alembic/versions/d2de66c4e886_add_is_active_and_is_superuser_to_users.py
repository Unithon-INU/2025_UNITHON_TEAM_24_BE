# alembic/versions/d2de66c4e886_add_is_active_and_is_superuser_to_users.py
"""add is_active and is_superuser to users

Revision ID: d2de66c4e886
Revises: f07cb107d277
Create Date: 2025-04-21 04:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2de66c4e886'
down_revision = 'f07cb107d277'
branch_labels = None
depends_on = None


def upgrade():
    # 1) server_default 로 기존 레코드 채우기
    op.add_column(
        'users',
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('TRUE')
        )
    )
    op.add_column(
        'users',
        sa.Column(
            'is_superuser',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('FALSE')
        )
    )

    # 2) 이제 기본값(default)은 제거(옵션)
    op.alter_column('users', 'is_active', server_default=None)
    op.alter_column('users', 'is_superuser', server_default=None)


def downgrade():
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'is_active')