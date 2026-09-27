import json
from pathlib import Path
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    check_system_status,
    create_ticket,
    find_nearby_places,
    generate_domain_video,
    generate_hardware_diagram,
    geocode_address,
    list_tickets,
    lookup_ip_address,
    search_knowledge_base,
)

# Read remote Agent Engine ID from deployment_metadata.json
deployment_metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_id = None
if deployment_metadata_path.exists():
    try:
        with open(deployment_metadata_path) as f:
            metadata = json.load(f)
            agent_engine_id = metadata.get("remote_agent_runtime_id")
    except Exception as e:
        print(f"Warning: Could not read deployment_metadata.json: {e}")

code_executor = None
if agent_engine_id:
    code_executor = AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=agent_engine_id
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each turn, send the session to Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


# Build A2UI system instruction
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are an IT Helpdesk Assistant. You help employees resolve technical issues, "
        "remember user preferences, personal information, and health/allergy requirements across sessions, "
        "check real-time IT system status, inspect network IP details, geocode locations, find nearby IT service spots, "
        "generate hardware and network architecture diagrams, generate short videos for IT hardware or troubleshooting, "
        "look up knowledge base articles, manage or create support tickets, and execute Python code in a sandbox when computation or scripting is needed."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property (\'h1\', \'h2\', \'body\') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or \'kind\'/\'data\'/\'metadata\' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        list_tickets,
        create_ticket,
        search_knowledge_base,
        check_system_status,
        lookup_ip_address,
        geocode_address,
        find_nearby_places,
        generate_hardware_diagram,
        generate_domain_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
