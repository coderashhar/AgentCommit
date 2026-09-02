"""initial_schema

Revision ID: b28573c7b38c
Revises: 
Create Date: 2026-09-02 10:35:09.181886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b28573c7b38c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables: users, profile_analyses, saved_issues."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("avatar_url", sa.Text(), nullable=True, server_default=""),
        sa.Column("bio", sa.Text(), nullable=True, server_default=""),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "profile_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=True),
        sa.Column("frameworks", sa.JSON(), nullable=True),
        sa.Column("experience_level", sa.String(length=50), nullable=True, server_default="beginner"),
        sa.Column("domains", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True, server_default=""),
        sa.Column("analyzed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_analyses_username", "profile_analyses", ["username"])

    op.create_table(
        "saved_issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("repo_full_name", sa.String(length=500), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True, server_default=""),
        sa.Column("html_url", sa.Text(), nullable=True, server_default=""),
        sa.Column("saved_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_issues_username", "saved_issues", ["username"])


def downgrade() -> None:
    """Drop all initial tables."""
    op.drop_index("ix_saved_issues_username", table_name="saved_issues")
    op.drop_table("saved_issues")
    op.drop_index("ix_profile_analyses_username", table_name="profile_analyses")
    op.drop_table("profile_analyses")
    op.drop_table("users")
