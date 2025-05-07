"""create progress tables

Revision ID: 001
Revises: 
Create Date: 2024-03-19 10:00:00.000000

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
    # Create lesson_progress table
    op.create_table(
        'lesson_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('lesson_id', sa.String(36), sa.ForeignKey('course_lessons.id'), nullable=False, index=True),
        sa.Column('status', postgresql.ENUM('not_started', 'in_progress', 'completed', name='progress_status'), nullable=False, default='not_started'),
        sa.Column('progress_percentage', sa.Float, nullable=False, default=0.0),
        sa.Column('last_position_seconds', sa.Integer, nullable=False, default=0),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('last_activity_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.Index('idx_lesson_progress_user_lesson', 'user_id', 'lesson_id', unique=True)
    )
    
    # Add indexes
    op.create_index('idx_lesson_progress_status', 'lesson_progress', ['status'])
    op.create_index('idx_lesson_progress_last_activity', 'lesson_progress', ['last_activity_at'])

def downgrade():
    # Drop lesson_progress table
    op.drop_table('lesson_progress')
    
    # Drop enum type
    op.execute('DROP TYPE progress_status') 