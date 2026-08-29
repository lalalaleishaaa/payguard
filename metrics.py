"""
Performance Metrics Tracker

Tracks and reports PayGuard's recovery performance metrics.
"""

from database import Database

db = Database()


def get_recovery_rate():
    """Calculate overall recovery rate."""
    total_failed = db.fetch_one("SELECT COUNT(*) as c FROM transactions WHERE status='failed'")["c"]
    total_recovered = db.fetch_one("SELECT COUNT(*) as c FROM transactions WHERE recovery_status='recovered'")["c"]
    return (total_recovered / total_failed * 100) if total_failed > 0 else 0


def get_recovery_by_segment():
    """Breakdown of recovery rate by customer segment."""
    return db.fetch_all("""
        SELECT c.segment, 
               COUNT(CASE WHEN t.recovery_status='recovered' THEN 1 END) as recovered,
               COUNT(*) as total
        FROM transactions t
        JOIN customers c ON t.customer_id = c.id
        WHERE t.status = 'failed'
        GROUP BY c.segment
    """)


def get_avg_recovery_time():
    """Average time between failure and recovery."""
    result = db.fetch_one("""
        SELECT AVG(
            (julianday(r.timestamp) - julianday(t.timestamp)) * 24 * 60
        ) as avg_minutes
        FROM recovery_actions r
        JOIN transactions t ON r.transaction_id = t.id
        WHERE r.success = 1
    """)
    return result["avg_minutes"] if result else 0


if __name__ == "__main__":
    print(f"Recovery Rate: {get_recovery_rate():.1f}%")
    print(f"Avg Recovery Time: {get_avg_recovery_time():.1f} minutes")
    print("\nBy Segment:")
    for row in get_recovery_by_segment():
        rate = (row["recovered"] / row["total"] * 100) if row["total"] > 0 else 0
        print(f"  {row['segment']}: {rate:.1f}% ({row['recovered']}/{row['total']})")