"""
LIVO Footwear ERP — Database Observability & Safe Performance Instrumentation
Attaches lightweight SQLAlchemy event listeners to measure query durations,
track slow queries, count rollbacks, and monitor pool exhaustion without logging sensitive data.
"""

import time
import logging
import re
from sqlalchemy import event
from app.core.metrics import metrics

logger = logging.getLogger("livo.db")

SLOW_QUERY_THRESHOLD_MS = 500.0

def sanitize_sql(statement: str) -> str:
    """Removes literal parameter values from SQL query strings for safe logging."""
    if not statement:
        return ""
    # Strip quoted strings and inline numbers
    clean = re.sub(r"'[^']*'", "'?'", statement)
    clean = re.sub(r"\b\d+\b", "?", clean)
    # Collapse excess whitespace
    return " ".join(clean.split())[:300]

def attach_db_observability(engine):
    """Instruments a SQLAlchemy engine with safe observability hooks."""

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if context is not None:
            context._query_start_time = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if context is not None and hasattr(context, "_query_start_time"):
            duration_ms = (time.perf_counter() - context._query_start_time) * 1000.0
            metrics.inc("db_queries_total")
            
            if duration_ms > SLOW_QUERY_THRESHOLD_MS:
                metrics.inc("db_slow_queries_total")
                safe_query = sanitize_sql(statement)
                logger.warning(
                    f"Slow Query Detected ({round(duration_ms, 2)}ms): {safe_query}",
                    extra={
                        "duration_ms": duration_ms,
                        "event": "slow_database_query"
                    }
                )

    @event.listens_for(engine, "handle_error")
    def handle_error(context):
        metrics.inc("db_errors_total")
        logger.error(
            f"Database execution error: {type(context.original_exception).__name__}",
            extra={"event": "db_error"}
        )

    # Listen for rollback events on connection
    @event.listens_for(engine, "rollback")
    def receive_rollback(conn):
        metrics.inc("db_rollbacks_total")

    # Pool monitoring (for QueuePool in postgres)
    if hasattr(engine.pool, "size"):
        @event.listens_for(engine.pool, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            checked_out = engine.pool.checkedout()
            pool_size = engine.pool.size()
            if pool_size > 0:
                utilization = checked_out / pool_size
                metrics.set_gauge("db_pool_utilization", round(utilization, 2))
                if utilization >= 0.9:
                    logger.warning(
                        f"Database connection pool approaching exhaustion ({checked_out}/{pool_size})",
                        extra={"event": "db_pool_high_utilization"}
                    )
