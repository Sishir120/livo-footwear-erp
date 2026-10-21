"""028_register_double_entry_accounting_ledger

Revision ID: 028_register_double_entry_accounting_ledger
Revises: 027_operational_numeric_precision
Create Date: 2026-10-19 12:00:00.000000

Sprint 1B.1 DDL Implementation:
Creates the double-entry accounting schema foundation with strict multi-tenant
isolation, dual-currency precision, and pure append-only voucher lifecycle:
1. Adds unique constraint on branches(company_id, id) for composite foreign key targeting.
2. Creates account_groups table (hierarchical classification with composite self-reference).
3. Creates ledger_accounts table (Chart of Accounts with branch/group composite foreign keys).
4. Creates accounting_periods table (fiscal periods with unique company/FY/period constraint).
5. Creates journal_vouchers table (atomic double-entry header, pure append-only, partial unique reversal index).
6. Creates journal_entries table (debit/credit lines, strict XOR constraint, composite tenant keys).
7. Adds database-level triggers enforcing posted voucher and entry immutability across PostgreSQL and SQLite.

Pure DDL only. Zero seed data. Zero runtime posting hooks.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '028_register_double_entry_accounting_ledger'
down_revision: Union[str, Sequence[str], None] = '027_operational_numeric_precision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # -------------------------------------------------------------------------
    # 1. Prerequisite: Add UniqueConstraint('company_id', 'id') to branches
    # -------------------------------------------------------------------------
    if dialect == "sqlite":
        with op.batch_alter_table("branches") as batch_op:
            batch_op.create_unique_constraint("uq_branches_company_id", ["company_id", "id"])
    else:
        op.create_unique_constraint("uq_branches_company_id", "branches", ["company_id", "id"])

    # -------------------------------------------------------------------------
    # 2. Table: account_groups
    # -------------------------------------------------------------------------
    op.create_table(
        "account_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("group_type", sa.String(length=32), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "id", name="uq_account_groups_company_id"),
        sa.UniqueConstraint("company_id", "code", name="uq_account_group_company_code"),
        sa.ForeignKeyConstraint(
            ["company_id", "parent_id"],
            ["account_groups.company_id", "account_groups.id"],
            name="fk_account_groups_parent",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "group_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')",
            name="chk_account_group_type",
        ),
        sa.CheckConstraint("level >= 1", name="chk_account_group_level"),
    )
    op.create_index("ix_account_groups_company_id", "account_groups", ["company_id"])
    op.create_index("ix_account_groups_parent", "account_groups", ["company_id", "parent_id"])

    # Partial unique indexes for group name hierarchy
    op.execute("""
        CREATE UNIQUE INDEX uq_account_group_root_name 
        ON account_groups(company_id, name) 
        WHERE parent_id IS NULL;
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_account_group_child_name 
        ON account_groups(company_id, parent_id, name) 
        WHERE parent_id IS NOT NULL;
    """)

    # -------------------------------------------------------------------------
    # 3. Table: ledger_accounts
    # -------------------------------------------------------------------------
    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normal_balance", sa.String(length=10), nullable=False),
        sa.Column("is_control_account", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("subledger_type", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "id", name="uq_ledger_accounts_company_id"),
        sa.UniqueConstraint("company_id", "code", name="uq_ledger_account_company_code"),
        sa.ForeignKeyConstraint(
            ["company_id", "group_id"],
            ["account_groups.company_id", "account_groups.id"],
            name="fk_ledger_accounts_group",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_ledger_accounts_branch",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "normal_balance IN ('DEBIT', 'CREDIT')",
            name="chk_ledger_account_normal_balance",
        ),
    )
    op.create_index("ix_ledger_accounts_company_code", "ledger_accounts", ["company_id", "code"])
    op.create_index("ix_ledger_accounts_group", "ledger_accounts", ["company_id", "group_id"])
    op.create_index("ix_ledger_accounts_branch", "ledger_accounts", ["company_id", "branch_id"])
    op.create_index("ix_ledger_accounts_active", "ledger_accounts", ["company_id", "is_active"])

    # -------------------------------------------------------------------------
    # 4. Table: accounting_periods
    # -------------------------------------------------------------------------
    op.create_table(
        "accounting_periods",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fiscal_year", sa.String(length=20), nullable=False),
        sa.Column("period_number", sa.Integer(), nullable=False),
        sa.Column("period_name", sa.String(length=50), nullable=False),
        sa.Column("start_date_ad", sa.Date(), nullable=False),
        sa.Column("end_date_ad", sa.Date(), nullable=False),
        sa.Column("start_date_bs", sa.String(length=10), nullable=False),
        sa.Column("end_date_bs", sa.String(length=10), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "id", name="uq_accounting_periods_company_id"),
        sa.UniqueConstraint("company_id", "fiscal_year", "period_number", name="uq_accounting_period_company_fy_period"),
        sa.CheckConstraint("period_number BETWEEN 1 AND 12", name="chk_accounting_period_number_range"),
        sa.CheckConstraint("start_date_ad <= end_date_ad", name="chk_accounting_period_dates_ad"),
    )
    op.create_index("ix_accounting_periods_lookup", "accounting_periods", ["company_id", "start_date_ad", "end_date_ad"])
    op.create_index("ix_accounting_periods_status", "accounting_periods", ["company_id", "is_closed"])

    # -------------------------------------------------------------------------
    # 5. Table: journal_vouchers (Append-Only Lifecycle)
    # -------------------------------------------------------------------------
    op.create_table(
        "journal_vouchers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("voucher_number", sa.String(length=50), nullable=False),
        sa.Column("voucher_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("date_ad", sa.Date(), nullable=False),
        sa.Column("date_bs", sa.String(length=10), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=True),
        sa.Column("total_debit_base", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("total_credit_base", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="NPR"),
        sa.Column("exchange_rate", sa.Numeric(precision=12, scale=6), nullable=False, server_default="1.000000"),
        sa.Column("total_debit_currency", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("total_credit_currency", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("narration", sa.Text(), nullable=True),
        sa.Column("source_doc_type", sa.String(length=50), nullable=True),
        sa.Column("source_doc_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("is_reversal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reversal_of_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("posted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "id", name="uq_journal_vouchers_company_id"),
        sa.UniqueConstraint("company_id", "voucher_number", name="uq_journal_voucher_company_number"),
        sa.UniqueConstraint("company_id", "idempotency_key", name="uq_journal_voucher_company_idempotency"),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_journal_vouchers_branch",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "period_id"],
            ["accounting_periods.company_id", "accounting_periods.id"],
            name="fk_journal_vouchers_period",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "reversal_of_id"],
            ["journal_vouchers.company_id", "journal_vouchers.id"],
            name="fk_journal_vouchers_reversal",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("status IN ('DRAFT', 'POSTED')", name="chk_journal_voucher_status"),
        sa.CheckConstraint(
            "voucher_type IN ('JOURNAL', 'SALES', 'PURCHASE', 'PAYMENT', 'RECEIPT', 'CONTRA', 'OPENING', 'REVERSAL')",
            name="chk_journal_voucher_type",
        ),
        sa.CheckConstraint(
            "total_debit_base >= 0.00 AND total_credit_base >= 0.00",
            name="chk_journal_voucher_totals_non_negative",
        ),
        sa.CheckConstraint("exchange_rate > 0.000000", name="chk_journal_voucher_exchange_rate"),
        sa.CheckConstraint(
            "(status != 'POSTED') OR (total_debit_base = total_credit_base)",
            name="chk_journal_voucher_posted_balanced",
        ),
    )
    op.create_index("ix_journal_vouchers_company_date", "journal_vouchers", ["company_id", "date_ad"])
    op.create_index("ix_journal_vouchers_status", "journal_vouchers", ["company_id", "status"])
    op.create_index("ix_journal_vouchers_source_doc", "journal_vouchers", ["company_id", "source_doc_type", "source_doc_id"])
    op.create_index("ix_journal_vouchers_branch", "journal_vouchers", ["company_id", "branch_id"])

    # Partial unique index enforcing single reversal per voucher per company
    op.execute("""
        CREATE UNIQUE INDEX uq_jv_reversal_of 
        ON journal_vouchers(company_id, reversal_of_id) 
        WHERE reversal_of_id IS NOT NULL;
    """)

    # -------------------------------------------------------------------------
    # 6. Table: journal_entries
    # -------------------------------------------------------------------------
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("voucher_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("ledger_id", sa.Integer(), nullable=False),
        sa.Column("debit_amount_base", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("credit_amount_base", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("debit_amount_currency", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("credit_amount_currency", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.00"),
        sa.Column("narration", sa.String(length=255), nullable=True),
        sa.Column("party_type", sa.String(length=32), nullable=True),
        sa.Column("party_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("voucher_id", "line_number", name="uq_journal_entry_voucher_line"),
        sa.ForeignKeyConstraint(
            ["company_id", "voucher_id"],
            ["journal_vouchers.company_id", "journal_vouchers.id"],
            name="fk_journal_entries_voucher",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "ledger_id"],
            ["ledger_accounts.company_id", "ledger_accounts.id"],
            name="fk_journal_entries_ledger",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_journal_entries_branch",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "debit_amount_base >= 0.00 AND credit_amount_base >= 0.00",
            name="chk_journal_entry_non_negative_base",
        ),
        sa.CheckConstraint(
            "((debit_amount_base > 0.00 AND credit_amount_base = 0.00) OR (credit_amount_base > 0.00 AND debit_amount_base = 0.00))",
            name="chk_journal_entry_debit_xor_credit_base",
        ),
        sa.CheckConstraint(
            "debit_amount_currency >= 0.00 AND credit_amount_currency >= 0.00",
            name="chk_journal_entry_non_negative_curr",
        ),
    )
    op.create_index("ix_journal_entries_account_lookup", "journal_entries", ["company_id", "ledger_id", "created_at"])
    op.create_index("ix_journal_entries_party", "journal_entries", ["company_id", "party_type", "party_id"])
    op.create_index("ix_journal_entries_voucher", "journal_entries", ["voucher_id"])
    op.create_index("ix_journal_entries_branch", "journal_entries", ["company_id", "branch_id"])

    # -------------------------------------------------------------------------
    # 7. Database Triggers (Posted Immutability Enforcement)
    # -------------------------------------------------------------------------
    if dialect == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION enforce_journal_voucher_initial_draft_status()
            RETURNS TRIGGER AS $$
            BEGIN
                IF (NEW.status != 'DRAFT') THEN
                    RAISE EXCEPTION 'Journal vouchers must be created in DRAFT status. Direct insertion as % is prohibited.', NEW.status;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            DROP TRIGGER IF EXISTS trg_journal_voucher_initial_draft ON journal_vouchers;
            CREATE TRIGGER trg_journal_voucher_initial_draft
            BEFORE INSERT ON journal_vouchers
            FOR EACH ROW EXECUTE FUNCTION enforce_journal_voucher_initial_draft_status();
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION prevent_posted_journal_voucher_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                IF (OLD.status = 'POSTED') THEN
                    RAISE EXCEPTION 'Posted journal vouchers are strictly immutable. Updates and deletes are prohibited. Use a separate reversing voucher instead.';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            DROP TRIGGER IF EXISTS trg_journal_voucher_immutable ON journal_vouchers;
            CREATE TRIGGER trg_journal_voucher_immutable
            BEFORE UPDATE OR DELETE ON journal_vouchers
            FOR EACH ROW EXECUTE FUNCTION prevent_posted_journal_voucher_modification();
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION prevent_posted_journal_entry_modification()
            RETURNS TRIGGER AS $$
            DECLARE
                v_status VARCHAR(20);
            BEGIN
                SELECT status INTO v_status FROM journal_vouchers WHERE id = OLD.voucher_id;
                IF (v_status = 'POSTED') THEN
                    RAISE EXCEPTION 'Journal entry lines belonging to a posted voucher are strictly immutable. Updates and deletes are prohibited.';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            DROP TRIGGER IF EXISTS trg_journal_entry_immutable ON journal_entries;
            CREATE TRIGGER trg_journal_entry_immutable
            BEFORE UPDATE OR DELETE ON journal_entries
            FOR EACH ROW EXECUTE FUNCTION prevent_posted_journal_entry_modification();
        """)
    elif dialect == "sqlite":
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_journal_voucher_initial_draft
            BEFORE INSERT ON journal_vouchers
            WHEN NEW.status != 'DRAFT'
            BEGIN
                SELECT RAISE(ABORT, 'Journal vouchers must be created in DRAFT status. Direct insertion is prohibited.');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_journal_voucher_no_update
            BEFORE UPDATE ON journal_vouchers
            WHEN OLD.status = 'POSTED'
            BEGIN
                SELECT RAISE(ABORT, 'Posted journal vouchers are strictly immutable');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_journal_voucher_no_delete
            BEFORE DELETE ON journal_vouchers
            WHEN OLD.status = 'POSTED'
            BEGIN
                SELECT RAISE(ABORT, 'Posted journal vouchers are strictly immutable');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_journal_entry_no_update
            BEFORE UPDATE ON journal_entries
            WHEN (SELECT status FROM journal_vouchers WHERE id = OLD.voucher_id) = 'POSTED'
            BEGIN
                SELECT RAISE(ABORT, 'Journal entry lines belonging to a posted voucher are strictly immutable');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_journal_entry_no_delete
            BEFORE DELETE ON journal_entries
            WHEN (SELECT status FROM journal_vouchers WHERE id = OLD.voucher_id) = 'POSTED'
            BEGIN
                SELECT RAISE(ABORT, 'Journal entry lines belonging to a posted voucher are strictly immutable');
            END;
        """)


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # 1. Drop Triggers and Functions
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_journal_entry_immutable ON journal_entries;")
        op.execute("DROP FUNCTION IF EXISTS prevent_posted_journal_entry_modification();")
        op.execute("DROP TRIGGER IF EXISTS trg_journal_voucher_immutable ON journal_vouchers;")
        op.execute("DROP FUNCTION IF EXISTS prevent_posted_journal_voucher_modification();")
        op.execute("DROP TRIGGER IF EXISTS trg_journal_voucher_initial_draft ON journal_vouchers;")
        op.execute("DROP FUNCTION IF EXISTS enforce_journal_voucher_initial_draft_status();")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_journal_entry_no_delete;")
        op.execute("DROP TRIGGER IF EXISTS trg_journal_entry_no_update;")
        op.execute("DROP TRIGGER IF EXISTS trg_journal_voucher_no_delete;")
        op.execute("DROP TRIGGER IF EXISTS trg_journal_voucher_no_update;")
        op.execute("DROP TRIGGER IF EXISTS trg_journal_voucher_initial_draft;")

    # 2. Drop Partial Unique Indexes
    op.execute("DROP INDEX IF EXISTS uq_jv_reversal_of;")
    op.execute("DROP INDEX IF EXISTS uq_account_group_child_name;")
    op.execute("DROP INDEX IF EXISTS uq_account_group_root_name;")

    # 3. Drop Accounting Tables in Reverse Topological Dependency Order
    op.drop_table("journal_entries")
    op.drop_table("journal_vouchers")
    op.drop_table("accounting_periods")
    op.drop_table("ledger_accounts")
    op.drop_table("account_groups")

    # 4. Drop Unique Constraint on branches
    if dialect == "sqlite":
        with op.batch_alter_table("branches") as batch_op:
            batch_op.drop_constraint("uq_branches_company_id", type_="unique")
    else:
        op.drop_constraint("uq_branches_company_id", "branches", type_="unique")
