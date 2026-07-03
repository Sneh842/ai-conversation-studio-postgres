"""Run once to populate demo data: python seed_data.py"""
from database import db, init_db

KNOWLEDGE_SOURCES = [
    ("Refund Policy", "Policy",
     "Customers can request a refund within 30 days of purchase. Refunds are processed within 5 to 7 business days. "
     "Digital products are non-refundable once downloaded. Refund requests must include the original order number."),
    ("Password Reset Guide", "Support",
     "To reset your password, go to account settings and click forgot password. A reset link is sent to your registered email. "
     "The reset link expires after 24 hours. Contact support if you do not receive the email within 10 minutes."),
    ("Enterprise Pricing Tiers", "Sales",
     "The Starter plan costs 29 dollars per month and supports up to 5 users. The Growth plan costs 99 dollars per month for up to 25 users. "
     "The Enterprise plan is custom priced and includes dedicated support and SSO."),
    ("Data Retention Policy", "Compliance",
     "User data is retained for 90 days after account deletion before permanent removal. Backups are retained for an additional 30 days. "
     "Enterprise customers can request immediate data purge via a signed data deletion request."),
    ("API Rate Limits", "Technical",
     "The standard API tier allows 100 requests per minute. The Enterprise tier allows 1000 requests per minute. "
     "Exceeding the rate limit returns a 429 status code with a retry-after header."),
]

ASSISTANTS = [
    ("Support Bot", "Helpful customer support assistant for a SaaS company", 0.10),
    ("Sales Assistant", "Assistant that answers pricing and plan questions", 0.30),
]


def main():
    init_db()
    with db() as conn:
        existing = conn.execute("SELECT COUNT(*) c FROM knowledge_sources").fetchone()["c"]
        if existing == 0:
            for title, category, content in KNOWLEDGE_SOURCES:
                conn.execute(
                    "INSERT INTO knowledge_sources (title, category, content) VALUES (?, ?, ?)",
                    (title, category, content),
                )
        existing_a = conn.execute("SELECT COUNT(*) c FROM assistants").fetchone()["c"]
        if existing_a == 0:
            for name, persona, bias in ASSISTANTS:
                conn.execute(
                    "INSERT INTO assistants (name, persona, hallucination_bias) VALUES (?, ?, ?)",
                    (name, persona, bias),
                )
    print("Seed data inserted.")


if __name__ == "__main__":
    main()
