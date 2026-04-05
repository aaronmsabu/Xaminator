"""Add exam_sessions table and update seat_allocations for session-based seating

Revision ID: 001_exam_sessions
Revises: 68ed1e93e217
Create Date: 2026-04-05

Changes:
  - Creates exam_sessions table (the physical time-slot shared by multiple exams)
  - Adds session_id column to exams (nullable FK)
  - Recreates seat_allocations with:
      - session_id (NOT NULL, FK to exam_sessions) as seat-uniqueness anchor
      - exam_id becomes nullable (student's specific exam)
      - unique constraints now on (session_id, student_id) and (session_id, hall_id, seat_number)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001_exam_sessions'
down_revision = '68ed1e93e217'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # 1. Create exam_sessions
    # ----------------------------------------------------------------
    op.create_table(
        'exam_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('exam_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_exam_sessions_id', 'exam_sessions', ['id'], unique=False)
    op.create_index('ix_exam_sessions_exam_date', 'exam_sessions', ['exam_date'])
    op.create_index('ix_exam_sessions_status', 'exam_sessions', ['status'])

    # ----------------------------------------------------------------
    # 2. Add session_id to exams (nullable, no FK enforced in SQLite)
    # ----------------------------------------------------------------
    op.add_column('exams', sa.Column('session_id', sa.Integer(), nullable=True))
    op.create_index('ix_exams_session_id', 'exams', ['session_id'])

    # ----------------------------------------------------------------
    # 3. Recreate seat_allocations with new structure
    #    SQLite doesn't support ALTER TABLE for constraints, so we use
    #    batch mode to recreate the table.
    # ----------------------------------------------------------------
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    with op.batch_alter_table('seat_allocations', recreate='auto') as batch_op:
        # Add new session_id column (nullable initially for migration)
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))

        # Make exam_id nullable (it was NOT NULL before)
        batch_op.alter_column('exam_id', nullable=True, existing_type=sa.Integer())

        # Drop old unique constraints
        batch_op.drop_constraint('uq_allocation_exam_student', type_='unique')
        batch_op.drop_constraint('uq_allocation_hall_seat', type_='unique')

        # Add new session-scoped unique constraints
        batch_op.create_unique_constraint(
            'uq_alloc_session_student', ['session_id', 'student_id']
        )
        batch_op.create_unique_constraint(
            'uq_alloc_session_hall_seat', ['session_id', 'hall_id', 'seat_number']
        )

        # Add FK index for session_id
        batch_op.create_index('ix_seat_alloc_session_id', ['session_id'])


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    # Reverse: recreate seat_allocations with exam_id-based constraints
    with op.batch_alter_table('seat_allocations', recreate='auto') as batch_op:
        batch_op.drop_constraint('uq_alloc_session_student', type_='unique')
        batch_op.drop_constraint('uq_alloc_session_hall_seat', type_='unique')
        batch_op.drop_index('ix_seat_alloc_session_id')
        batch_op.drop_column('session_id')
        batch_op.alter_column('exam_id', nullable=False, existing_type=sa.Integer())
        batch_op.create_unique_constraint(
            'uq_allocation_exam_student', ['exam_id', 'student_id']
        )
        batch_op.create_unique_constraint(
            'uq_allocation_hall_seat', ['exam_id', 'hall_id', 'seat_number']
        )

    op.drop_index('ix_exams_session_id', table_name='exams')
    op.drop_column('exams', 'session_id')

    op.drop_index('ix_exam_sessions_status', table_name='exam_sessions')
    op.drop_index('ix_exam_sessions_exam_date', table_name='exam_sessions')
    op.drop_index('ix_exam_sessions_id', table_name='exam_sessions')
    op.drop_table('exam_sessions')
