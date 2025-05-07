"""create lesson progress table

Revision ID: 001
Revises: 
Create Date: 2024-03-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create progress status enum type
    progress_status = postgresql.ENUM('not_started', 'in_progress', 'completed', name='progressstatus')
    progress_status.create(op.get_bind())

    # Create lesson progress table
    op.create_table(
        'lesson_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('lesson_id', sa.String(36), nullable=False),
        sa.Column('status', sa.Enum('not_started', 'in_progress', 'completed', name='progressstatus'), nullable=False),
        sa.Column('progress_percentage', sa.Float, nullable=False, default=0.0),
        sa.Column('last_position_seconds', sa.Integer, nullable=False, default=0),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('last_activity_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['lesson_id'], ['course_lessons.id'], ondelete='CASCADE'),
        sa.Index('ix_lesson_progress_user_id', 'user_id'),
        sa.Index('ix_lesson_progress_lesson_id', 'lesson_id')
    )

def downgrade():
    op.drop_table('lesson_progress')
    op.execute('DROP TYPE progressstatus') 