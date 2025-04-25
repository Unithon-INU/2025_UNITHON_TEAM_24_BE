"""add foreign key from travel_routes.owner_id to users.id

Revision ID: 42333becda6f
Revises: abc5700be2a3
Create Date: 2025-04-21 19:04:30.088683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '42333becda6f'
down_revision: Union[str, None] = 'abc5700be2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 0) 만약 이미 생성된 index가 있으면 미리 삭제
    op.execute("DROP INDEX IF EXISTS ix_travel_routes_owner_id;")

    # 1) routes 테이블 (새로 생성하는 경우)
    op.create_table(
        'routes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('moving_info', sa.JSON(), nullable=False),
        sa.Column('estimated_duration', sa.String(), nullable=True),
        sa.Column('total_distance', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_routes_created_at', 'routes', ['created_at'], unique=False)
    op.create_index('ix_routes_owner_id', 'routes', ['owner_id'], unique=False)

    # 2) route_places 테이블 (새로 생성하는 경우)
    op.create_table(
        'route_places',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('route_id', sa.String(), nullable=False),
        sa.Column('place_google_id', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['place_google_id'], ['places.google_place_id'], ),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_route_places_created_at', 'route_places', ['created_at'], unique=False)
    op.create_index('ix_route_places_place_google_id', 'route_places', ['place_google_id'], unique=False)
    op.create_index('ix_route_places_route_id', 'route_places', ['route_id'], unique=False)

    # 3) 기존 travel_routes 테이블 수정
    #    estimated_duration, total_distance NULL 허용
    op.alter_column('travel_routes', 'estimated_duration',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('travel_routes', 'total_distance',
               existing_type=sa.VARCHAR(),
               nullable=True)

    #    created_at → timezone-aware DateTime 로 변경
    op.alter_column('travel_routes', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               nullable=False)

    # 4) travel_routes 테이블에 owner_id FK 재설정
    #    기존 FK 제거
    op.drop_constraint('travel_routes_owner_id_fkey', 'travel_routes', type_='foreignkey')
    #    새 FK 추가 (cascade on delete)
    op.create_foreign_key(
        None,
        'travel_routes', 'users',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )

    # 5) travel_routes.places JSON 컬럼 제거
    op.drop_column('travel_routes', 'places')

    # 6) 다시 owner_id index 생성 (이미 위에서 지웠으니 안전)
    op.create_index('ix_travel_routes_owner_id', 'travel_routes', ['owner_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 1) places 컬럼 복원
    op.add_column('travel_routes', sa.Column(
        'places',
        postgresql.JSON(astext_type=sa.Text()),
        nullable=False
    ))

    # 2) travel_routes FK 롤백
    op.drop_constraint(None, 'travel_routes', type_='foreignkey')
    op.create_foreign_key(
        'travel_routes_owner_id_fkey',
        'travel_routes', 'users',
        ['owner_id'], ['id']
    )

    # 3) travel_routes 인덱스 롤백
    op.drop_index('ix_travel_routes_owner_id', table_name='travel_routes')
    op.create_index('ix_travel_routes_owner_id', 'travel_routes', ['owner_id'], unique=False)

    # 4) created_at, total_distance, estimated_duration 롤백
    op.alter_column('travel_routes', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('travel_routes', 'total_distance',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('travel_routes', 'estimated_duration',
               existing_type=sa.VARCHAR(),
               nullable=False)

    # 5) route_places 테이블 롤백
    op.drop_index('ix_route_places_route_id', table_name='route_places')
    op.drop_index('ix_route_places_place_google_id', table_name='route_places')
    op.drop_index('ix_route_places_created_at', table_name='route_places')
    op.drop_table('route_places')

    # 6) routes 테이블 롤백
    op.drop_index('ix_routes_owner_id', table_name='routes')
    op.drop_index('ix_routes_created_at', table_name='routes')
    op.drop_table('routes')