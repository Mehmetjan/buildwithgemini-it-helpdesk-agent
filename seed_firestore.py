import datetime
from google.cloud import firestore
from google.api_core.exceptions import NotFound

# Hardcoded project ID as required for Agent Platform / Firestore compatibility
PROJECT_ID = "qwiklabs-gcp-03-f74bc9bf9c60"


def seed_database():
    print(f"Initializing Firestore client for project: {PROJECT_ID}")
    try:
        db = firestore.Client(project=PROJECT_ID)

        # 1. Seed IT Support Tickets
        tickets = [
            {
                "ticket_id": "TICK-101",
                "title": "VPN connection failing on macOS Sequoia",
                "description": "User cannot connect to corporate GlobalProtect VPN following OS upgrade. Error: Authentication timed out.",
                "category": "Network",
                "priority": "High",
                "status": "Open",
                "assignee": "Sarah Connor",
                "user_id": "emp_402",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            {
                "ticket_id": "TICK-102",
                "title": "Monitor flickering on USB-C Dock",
                "description": "External DisplayPort monitor flickers every 30 seconds when connected via Dell Thunderbolt dock.",
                "category": "Hardware",
                "priority": "Medium",
                "status": "In Progress",
                "assignee": "Alex Rivera",
                "user_id": "emp_105",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            {
                "ticket_id": "TICK-103",
                "title": "Request for Figma Professional License",
                "description": "Product designer needs access to the UX team Figma workspace.",
                "category": "Software",
                "priority": "Low",
                "status": "Resolved",
                "assignee": "IT Admin",
                "user_id": "emp_881",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        ]

        for ticket in tickets:
            doc_ref = db.collection("tickets").document(ticket["ticket_id"])
            doc_ref.set(ticket)
            print(f"Seeded ticket: {ticket['ticket_id']} - {ticket['title']}")

        # 2. Seed Knowledge Base Articles
        articles = [
            {
                "article_id": "KB-201",
                "title": "How to Reset Your Okta Corporate Password",
                "category": "Security",
                "content": "1. Navigate to https://sso.company.com/reset\n2. Enter your employee email.\n3. Verify identity via SMS/Push notification.\n4. Create a new password adhering to complexity requirements (16+ chars, numbers, symbols).",
                "tags": ["password", "okta", "security", "login"],
            },
            {
                "article_id": "KB-202",
                "title": "VPN Troubleshooting Guide",
                "category": "Network",
                "content": "If GlobalProtect VPN fails to connect:\n1. Check if internet connection is stable.\n2. Ensure Portal URL is set to vpn.company.com.\n3. Clear VPN cache: Settings -> Gateway -> Re-authenticate.\n4. Restart GlobalProtect service or reboot device.",
                "tags": ["vpn", "globalprotect", "network", "macOS", "windows"],
            },
            {
                "article_id": "KB-203",
                "title": "Requesting Software Licenses & Access",
                "category": "Software",
                "content": "Software access requests (Slack Pro, Figma, GitHub Enterprise) require manager approval. Submit a ticket under Software Category with manager CC'd.",
                "tags": ["software", "license", "figma", "github"],
            },
        ]

        for article in articles:
            doc_ref = db.collection("knowledge_base").document(article["article_id"])
            doc_ref.set(article)
            print(f"Seeded KB article: {article['article_id']} - {article['title']}")

        print("Firestore database seeded successfully!")
    except NotFound:
        print(
            f"Note: The default Firestore database for project '{PROJECT_ID}' does not exist yet."
        )
        print(
            f"Visit https://console.cloud.google.com/firestore/welcome?project={PROJECT_ID} to create it."
        )


if __name__ == "__main__":
    seed_database()
