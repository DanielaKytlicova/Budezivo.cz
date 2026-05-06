"""add contacts and contact_links tables (Phase 76 — M1)

Revision ID: c93b07e1d8f2
Revises: b58d127e4c91
Create Date: 2026-05-01 12:00:00.000000

Centralised contact directory auto-populated from reservations and event
applications. Mirrors the wireframe approved in Phase 76 — see PRD.md.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c93b07e1d8f2'
down_revision: Union[str, Sequence[str], None] = 'b58d127e4c91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add marketing_consent column to existing intake tables so the new
    #    public opt-in checkbox has somewhere to land.
    op.add_column('reservations',
        sa.Column('marketing_consent', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('event_applications',
        sa.Column('marketing_consent', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # 2) New `contacts` table.
    op.create_table(
        'contacts',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('institution_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_name', sa.Text()),
        sa.Column('last_name', sa.Text()),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('phone', sa.Text()),
        sa.Column('type', sa.Text(), server_default=sa.text("'jine'")),
        sa.Column('primary_source', sa.Text()),
        sa.Column('school_name', sa.Text()),
        sa.Column('school_type', sa.Text()),
        sa.Column('marketing_consent', sa.Boolean()),
        sa.Column('marketing_consent_at', sa.DateTime(timezone=True)),
        sa.Column('note', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_activity_at', sa.DateTime(timezone=True)),
    )
    op.create_index('idx_contacts_institution', 'contacts', ['institution_id'])
    # Per-institution dedup on lower-cased email
    op.create_index('idx_contacts_email_inst', 'contacts', ['institution_id', 'email'], unique=True)
    op.create_index('idx_contacts_type', 'contacts', ['type'])
    op.create_index('idx_contacts_consent', 'contacts', ['marketing_consent'])

    # 3) New `contact_links` table.
    op.create_table(
        'contact_links',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('contact_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('institution_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('program_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('programs.id', ondelete='SET NULL')),
        sa.Column('event_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('events.id', ondelete='SET NULL')),
        sa.Column('reservation_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('reservations.id', ondelete='SET NULL')),
        sa.Column('application_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('event_applications.id', ondelete='SET NULL')),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('role', sa.Text()),
        sa.Column('status', sa.Text()),
        sa.Column('label', sa.Text()),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_contact_links_contact', 'contact_links', ['contact_id'])
    op.create_index('idx_contact_links_institution', 'contact_links', ['institution_id'])
    op.create_index('idx_contact_links_program', 'contact_links', ['program_id'])
    op.create_index('idx_contact_links_event', 'contact_links', ['event_id'])
    op.create_index('idx_contact_links_source', 'contact_links', ['source_type'])


def downgrade() -> None:
    op.drop_index('idx_contact_links_source', table_name='contact_links')
    op.drop_index('idx_contact_links_event', table_name='contact_links')
    op.drop_index('idx_contact_links_program', table_name='contact_links')
    op.drop_index('idx_contact_links_institution', table_name='contact_links')
    op.drop_index('idx_contact_links_contact', table_name='contact_links')
    op.drop_table('contact_links')
    op.drop_index('idx_contacts_consent', table_name='contacts')
    op.drop_index('idx_contacts_type', table_name='contacts')
    op.drop_index('idx_contacts_email_inst', table_name='contacts')
    op.drop_index('idx_contacts_institution', table_name='contacts')
    op.drop_table('contacts')
    op.drop_column('event_applications', 'marketing_consent')
    op.drop_column('reservations', 'marketing_consent')
