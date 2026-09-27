import datetime
import os
import uuid
from typing import Optional
from dotenv import load_dotenv
import requests
from google import genai
from google.genai import types
from google.cloud import firestore, storage
from google.api_core.exceptions import NotFound
from google.adk.tools import ToolContext

load_dotenv()

# Hardcoded project ID as required for Agent Platform / Firestore compatibility
PROJECT_ID = "qwiklabs-gcp-03-f74bc9bf9c60"

# Fallback in-memory store for local testing if Firestore DB instance is not provisioned yet
_LOCAL_TICKETS = {
    "TICK-101": {
        "ticket_id": "TICK-101",
        "title": "VPN connection failing on macOS Sequoia",
        "description": "User cannot connect to corporate GlobalProtect VPN following OS upgrade.",
        "category": "Network",
        "priority": "High",
        "status": "Open",
        "assignee": "Sarah Connor",
        "user_id": "emp_402",
        "created_at": "2026-09-27T16:00:00Z",
    },
    "TICK-102": {
        "ticket_id": "TICK-102",
        "title": "Monitor flickering on USB-C Dock",
        "description": "External DisplayPort monitor flickers every 30 seconds when connected via Dell Thunderbolt dock.",
        "category": "Hardware",
        "priority": "Medium",
        "status": "In Progress",
        "assignee": "Alex Rivera",
        "user_id": "emp_105",
        "created_at": "2026-09-27T15:30:00Z",
    },
}

_LOCAL_KB = {
    "KB-201": {
        "article_id": "KB-201",
        "title": "How to Reset Your Okta Corporate Password",
        "category": "Security",
        "content": "1. Navigate to https://sso.company.com/reset\n2. Enter your employee email.\n3. Verify identity via SMS/Push notification.\n4. Create a new password adhering to complexity requirements (16+ chars).",
        "tags": ["password", "okta", "security", "login"],
    },
    "KB-202": {
        "article_id": "KB-202",
        "title": "VPN Troubleshooting Guide",
        "category": "Network",
        "content": "If GlobalProtect VPN fails to connect:\n1. Check internet connection.\n2. Ensure Portal URL is set to vpn.company.com.\n3. Clear VPN cache in Settings -> Gateway.\n4. Restart GlobalProtect service.",
        "tags": ["vpn", "globalprotect", "network", "macOS", "windows"],
    },
}


def _get_firestore_client() -> Optional[firestore.Client]:
    """Helper to instantiate Firestore client with hardcoded project ID."""
    try:
        return firestore.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"Warning: Unable to initialize Firestore client: {e}")
        return None


def list_tickets(status: str = "", category: str = "") -> str:
    """Lists IT support tickets filtered by status or category.

    Args:
        status: Optional status to filter by (e.g. 'Open', 'In Progress', 'Resolved').
        category: Optional category to filter by (e.g. 'Network', 'Hardware', 'Software').

    Returns:
        A string summarizing the matching tickets.
    """
    db = _get_firestore_client()
    if db:
        try:
            query_ref = db.collection("tickets")
            if status:
                query_ref = query_ref.where("status", "==", status)
            if category:
                query_ref = query_ref.where("category", "==", category)

            docs = list(query_ref.stream())
            if docs:
                tickets = [doc.to_dict() for doc in docs]
                return f"Found {len(tickets)} ticket(s):\n" + "\n".join(
                    [
                        f"[{t.get('ticket_id')}] {t.get('title')} | Category: {t.get('category')} | Status: {t.get('status')} | Priority: {t.get('priority')} | Assignee: {t.get('assignee', 'Unassigned')}"
                        for t in tickets
                    ]
                )
            return "No tickets found matching the specified filters in Firestore."
        except NotFound:
            pass  # Fall back to local store if DB not created yet
        except Exception as e:
            print(f"Firestore query error: {e}")

    # Fallback store search
    results = []
    for t in _LOCAL_TICKETS.values():
        if status and t["status"].lower() != status.lower():
            continue
        if category and t["category"].lower() != category.lower():
            continue
        results.append(t)

    if results:
        return f"Found {len(results)} ticket(s):\n" + "\n".join(
            [
                f"[{t['ticket_id']}] {t['title']} | Category: {t['category']} | Status: {t['status']} | Priority: {t['priority']}"
                for t in results
            ]
        )
    return "No tickets found matching the criteria."


def create_ticket(
    title: str,
    description: str,
    category: str,
    priority: str = "Medium",
    user_id: str = "emp_user",
) -> str:
    """Creates a new IT support ticket.

    Args:
        title: Short title describing the issue.
        description: Detailed description of the problem.
        category: Ticket category ('Network', 'Hardware', 'Software', 'Security', etc.).
        priority: Urgency level ('Low', 'Medium', 'High', 'Critical').
        user_id: ID of the reporting employee.

    Returns:
        A confirmation message with the generated Ticket ID.
    """
    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ticket_data = {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "status": "Open",
        "assignee": "Unassigned",
        "user_id": user_id,
        "created_at": now_iso,
    }

    db = _get_firestore_client()
    if db:
        try:
            doc_ref = db.collection("tickets").document(ticket_id)
            doc_ref.set(ticket_data)
            return f"Successfully created ticket [{ticket_id}] in Firestore:\nTitle: {title}\nCategory: {category}\nPriority: {priority}\nStatus: Open"
        except NotFound:
            pass
        except Exception as e:
            print(f"Firestore error creating ticket: {e}")

    # Local fallback
    _LOCAL_TICKETS[ticket_id] = ticket_data
    return f"Successfully created ticket [{ticket_id}]:\nTitle: {title}\nCategory: {category}\nPriority: {priority}\nStatus: Open"


def search_knowledge_base(query: str) -> str:
    """Searches knowledge base articles for troubleshooting IT issues.

    Args:
        query: Search term or issue keyword (e.g. 'vpn', 'password', 'license').

    Returns:
        Matching knowledge base articles and solutions.
    """
    db = _get_firestore_client()
    if db:
        try:
            docs = list(db.collection("knowledge_base").stream())
            if docs:
                articles = [doc.to_dict() for doc in docs]
                q = query.lower()
                matches = [
                    a
                    for a in articles
                    if q in a.get("title", "").lower()
                    or q in a.get("content", "").lower()
                    or any(q in tag.lower() for tag in a.get("tags", []))
                ]
                if matches:
                    return "\n\n".join(
                        [
                            f"=== [{a.get('article_id')}] {a.get('title')} ===\nCategory: {a.get('category')}\nContent:\n{a.get('content')}"
                            for a in matches
                        ]
                    )
        except NotFound:
            pass
        except Exception as e:
            print(f"Firestore KB search error: {e}")

    # Fallback search
    q = query.lower()
    matches = [
        a
        for a in _LOCAL_KB.values()
        if q in a["title"].lower()
        or q in a["content"].lower()
        or any(q in tag.lower() for tag in a["tags"])
    ]
    if matches:
        return "\n\n".join(
            [
                f"=== [{a['article_id']}] {a['title']} ===\nCategory: {a['category']}\nContent:\n{a['content']}"
                for a in matches
            ]
        )
    return f"No knowledge base articles found matching query '{query}'."


def check_system_status(service_name: str = "") -> str:
    """Checks the real-time operational status of IT services and infrastructure.

    Args:
        service_name: Optional name of the service to check (e.g. 'VPN', 'Okta', 'Slack', 'Email', 'Jira').

    Returns:
        A string summarizing the operational status of the service(s).
    """
    system_status = {
        "VPN": "Degraded Performance (High latency reported on US-East gateway)",
        "Okta": "Operational",
        "Slack": "Operational",
        "Email": "Operational",
        "Jira": "Operational",
        "GitHub": "Operational",
    }

    if service_name:
        for name, status in system_status.items():
            if service_name.lower() in name.lower():
                return f"System Status for [{name}]: {status}"
        return f"Service '{service_name}' not found in monitoring system. Monitored services: {', '.join(system_status.keys())}."

    statuses = [f"• {svc}: {status}" for svc, status in system_status.items()]
    return "Current IT Systems Status:\n" + "\n".join(statuses)


def lookup_ip_address(ip_address: str = "") -> str:
    """Looks up network diagnostic information, ISP, location, and ASN for an IP address or hostname.

    Args:
        ip_address: The IP address or domain name to inspect (e.g. '8.8.8.8', '1.1.1.1').

    Returns:
        A string with network diagnostic details (ISP, Organization, Location, Country, Timezone).
    """
    try:
        url = (
            f"http://ip-api.com/json/{ip_address.strip()}"
            if ip_address
            else "http://ip-api.com/json/"
        )
        response = requests.get(url, timeout=5)
        data = response.json()

        if data.get("status") == "success":
            return (
                f"IP Diagnostic Results for [{data.get('query')}]:\n"
                f"• ISP: {data.get('isp')}\n"
                f"• Organization: {data.get('org')}\n"
                f"• Location: {data.get('city')}, {data.get('regionName')}, {data.get('country')}\n"
                f"• ASN: {data.get('as')}\n"
                f"• Timezone: {data.get('timezone')}"
            )
        return f"Unable to resolve IP or hostname '{ip_address}': {data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error connecting to IP lookup service: {e}"


def geocode_address(address: str) -> str:
    """Converts a street address, city, or location name into geographic coordinates (latitude and longitude).

    Args:
        address: The address or location name to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A string with the latitude, longitude, and formatted address.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set in .env."

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            fmt_address = result.get("formatted_address")
            lat = result["geometry"]["location"]["lat"]
            lng = result["geometry"]["location"]["lng"]
            return f"Geocoding Result for '{address}':\n• Formatted Address: {fmt_address}\n• Latitude: {lat}\n• Longitude: {lng}"
        return f"Geocoding failed for '{address}': {data.get('status')} - {data.get('error_message', 'No details')}"
    except Exception as e:
        return f"Error connecting to Geocoding API: {e}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "electronics_store",
    radius: float = 2000.0,
) -> str:
    """Finds nearby places of a specific type (e.g. electronics_store, store, cafe) around a given coordinate using Places API (New).

    Args:
        latitude: Latitude of the center point.
        longitude: Longitude of the center point.
        place_type: Type of place to search for (e.g. 'electronics_store', 'store', 'cafe', 'bank').
        radius: Radius in meters around the center location (default: 2000.0).

    Returns:
        A list of nearby places including name, address, and location.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set in .env."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    body = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius,
            }
        },
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=5)
        data = response.json()

        if "places" in data and data["places"]:
            places_summary = []
            for p in data["places"]:
                name = p.get("displayName", {}).get("text", "Unknown")
                addr = p.get("formattedAddress", "No address")
                loc = p.get("location", {})
                places_summary.append(
                    f"• {name}\n  Address: {addr}\n  Location: ({loc.get('latitude')}, {loc.get('longitude')})"
                )
            return f"Found {len(places_summary)} nearby '{place_type}' place(s):\n" + "\n".join(places_summary)
        return f"No nearby places found for type '{place_type}' within {radius} meters."
    except Exception as e:
        return f"Error connecting to Places API (New): {e}"


def generate_hardware_diagram(
    prompt: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generates an IT hardware or network architecture diagram image, saves it to Playground artifacts, and uploads it to Cloud Storage.

    Args:
        prompt: Detailed description of the IT diagram, network flowchart, or hardware setup to generate.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    try:
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        image_bytes = None
        mime_type = "image/png"
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return "Failed to generate diagram image: No image data returned by model."

        # 1. Save artifact for Playground panel if tool_context is provided
        if tool_context:
            filename = f"diagram_{uuid.uuid4().hex[:6]}.png"
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes to public Cloud Storage bucket with hardcoded bucket name
        bucket_name = "it-helpdesk-assets-qwiklabs-gcp-03-f74bc9bf9c60"
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        object_name = f"diagrams/diagram_{uuid.uuid4().hex[:8]}.png"
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
        return public_url
    except Exception as e:
        return f"Error generating hardware diagram image: {e}"


def generate_domain_video(
    prompt: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generates a short video for IT helpdesk, network troubleshooting, or server hardware overview using gemini-omni-flash-preview in the global region.
    Saves the video to Playground artifacts and uploads to Cloud Storage, returning the public HTTPS URL.

    Args:
        prompt: Detailed description of the IT support video or hardware walkthrough to generate.

    Returns:
        The public HTTPS URL of the uploaded MP4 video in Cloud Storage.
    """
    try:
        video_bytes = None
        mime_type = "video/mp4"

        # 1. Try Interactions API REST endpoint in global region
        try:
            import base64
            import google.auth
            import google.auth.transport.requests

            credentials, _ = google.auth.default()
            credentials.refresh(google.auth.transport.requests.Request())

            url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/global/interactions"
            headers = {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "gemini-omni-flash-preview",
                "input": [{"type": "text", "text": prompt}],
                "response_format": [{"type": "video", "delivery": "inline"}],
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                steps = data.get("steps", [])
                for step in steps:
                    if step.get("type") == "model_output":
                        for content in step.get("content", []):
                            if content.get("type") == "video":
                                if "data" in content:
                                    video_bytes = base64.b64decode(content["data"])
                                elif "bytes" in content:
                                    video_bytes = base64.b64decode(content["bytes"])
                                if "mime_type" in content:
                                    mime_type = content["mime_type"]
                                break
            else:
                print(f"Interactions API REST status {resp.status_code}: {resp.text}")
        except Exception as rest_err:
            print(f"Interactions API REST exception: {rest_err}")

        # 2. Fallback to genai client generate_content / generate_videos if needed
        if not video_bytes:
            try:
                genai_client = genai.Client(
                    vertexai=True,
                    project=PROJECT_ID,
                    location="global",
                )
                response = genai_client.models.generate_content(
                    model="gemini-omni-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(response_modalities=["VIDEO"]),
                )
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            video_bytes = part.inline_data.data
                            if part.inline_data.mime_type:
                                mime_type = part.inline_data.mime_type
                            break
            except Exception as genai_err:
                print(f"GenAI fallback exception: {genai_err}")

        if not video_bytes:
            return "Failed to generate domain video: No video bytes returned from model."

        # (1) Save artifact for Playground panel if tool_context is provided
        if tool_context:
            filename = f"video_{uuid.uuid4().hex[:6]}.mp4"
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload video bytes to public Cloud Storage bucket with hardcoded bucket name
        bucket_name = "it-helpdesk-assets-qwiklabs-gcp-03-f74bc9bf9c60"
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        object_name = f"videos/video_{uuid.uuid4().hex[:8]}.mp4"
        blob = bucket.blob(object_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
        return public_url
    except Exception as e:
        return f"Error generating domain video: {e}"





