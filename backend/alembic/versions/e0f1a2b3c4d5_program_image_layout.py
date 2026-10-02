"""Add program image layout and focal point metadata."""
from alembic import op

revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE programs
            ADD COLUMN IF NOT EXISTS image_layout TEXT NOT NULL DEFAULT 'hero',
            ADD COLUMN IF NOT EXISTS image_focus_x INTEGER NOT NULL DEFAULT 50,
            ADD COLUMN IF NOT EXISTS image_focus_y INTEGER NOT NULL DEFAULT 50
    """)
    op.execute("""
        ALTER TABLE programs
            ADD CONSTRAINT ck_program_image_layout
                CHECK (image_layout IN ('hero', 'square')),
            ADD CONSTRAINT ck_program_image_focus_x
                CHECK (image_focus_x BETWEEN 0 AND 100),
            ADD CONSTRAINT ck_program_image_focus_y
                CHECK (image_focus_y BETWEEN 0 AND 100)
    """)


def downgrade():
    op.execute("""
        ALTER TABLE programs
            DROP CONSTRAINT IF EXISTS ck_program_image_focus_y,
            DROP CONSTRAINT IF EXISTS ck_program_image_focus_x,
            DROP CONSTRAINT IF EXISTS ck_program_image_layout,
            DROP COLUMN IF EXISTS image_focus_y,
            DROP COLUMN IF EXISTS image_focus_x,
            DROP COLUMN IF EXISTS image_layout
    """)
