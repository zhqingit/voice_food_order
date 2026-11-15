"""cost tracking: phone calls, Stripe fees, fixed platform costs

Revision ID: 0031_cost_tracking
Revises: 0030_channel_commission
Create Date: 2026-11-14

Phone calls get their own row with the AI and Twilio cost (only logged
before). Card charges record the Stripe processing fee; existing ones are
backfilled with the standard 2.9% + 30¢ estimate. Admins enter fixed monthly
costs in platform_costs.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0031_cost_tracking"
down_revision = "0030_channel_commission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phone_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_sid", sa.String(64), nullable=False, unique=True),
        sa.Column("caller", sa.String(32), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("end_reason", sa.String(32), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_cost", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("telephony_cost", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index("ix_phone_calls_store_id", "phone_calls", ["store_id"])
    op.create_index("ix_phone_calls_started_at", "phone_calls", ["started_at"])

    op.create_table(
        "platform_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_platform_costs_month", "platform_costs", ["month"])

    op.add_column("payments", sa.Column("stripe_fee", sa.Numeric(10, 2), nullable=True))
    op.execute(
        "UPDATE payments SET stripe_fee = ROUND(amount * 0.029 + 0.30, 2) "
        "WHERE kind = 'charge' AND method = 'card' AND status = 'succeeded'"
    )


def downgrade() -> None:
    op.drop_column("payments", "stripe_fee")
    op.drop_index("ix_platform_costs_month", table_name="platform_costs")
    op.drop_table("platform_costs")
    op.drop_index("ix_phone_calls_started_at", table_name="phone_calls")
    op.drop_index("ix_phone_calls_store_id", table_name="phone_calls")
    op.drop_table("phone_calls")
