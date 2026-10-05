# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from google import genai
from google.cloud import firestore, storage

load_dotenv()

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from .a2ui_utils import a2ui_callback


MODEL = "gemini-3.6-flash"

# Hardcoded project and bucket names for Agent Platform compatibility
PROJECT_ID = "qwiklabs-gcp-01-8fd0a7df8d09"
BUCKET_NAME = "greenhouse-plants-qwiklabs-gcp-01-8fd0a7df8d09"

db = firestore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
image_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")


def list_plants(pet_safe_only: bool = False, in_stock_only: bool = True) -> list[dict]:
    """Lists plants from the greenhouse inventory in Firestore.

    Args:
        pet_safe_only: If True, only returns plants that are safe and non-toxic for pets.
        in_stock_only: If True, only returns plants currently in stock.

    Returns:
        A list of plant dictionaries containing name, species, light, water, difficulty, price, and in_stock.
    """
    plants_ref = db.collection("plants")
    results = []
    for doc in plants_ref.stream():
        data = doc.to_dict()
        if in_stock_only and data.get("in_stock", 0) <= 0:
            continue
        if pet_safe_only and not data.get("pet_safe", False):
            continue
        results.append({
            "id": doc.id,
            "name": data.get("name"),
            "species": data.get("species"),
            "light": data.get("light"),
            "water": data.get("water"),
            "difficulty": data.get("difficulty"),
            "price": data.get("price"),
            "pet_safe": data.get("pet_safe"),
            "in_stock": data.get("in_stock"),
            "care_tips": data.get("care_tips"),
            "last_cared_at": data.get("last_cared_at")
        })
    return results


def get_plant_details(plant_name: str) -> dict:
    """Retrieves detailed information and care tips for a specific plant from Firestore.

    Args:
        plant_name: The common name, species name, or id of the plant (e.g. 'Monstera', 'Snake Plant', 'Fern').

    Returns:
        A dictionary with the plant's full details, or an error dictionary if not found.
    """
    search_term = plant_name.lower().strip()
    plants_ref = db.collection("plants")

    # Direct document ID lookup first
    doc = plants_ref.document(search_term.replace(" ", "-")).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}

    # Search by matching name or species
    for doc in plants_ref.stream():
        data = doc.to_dict()
        name = data.get("name", "").lower()
        species = data.get("species", "").lower()
        doc_id = doc.id.lower()
        if search_term in name or search_term in species or search_term in doc_id:
            return {"id": doc.id, **data}

    return {"error": f"No plant found matching '{plant_name}' in the greenhouse catalog."}


def record_plant_care(plant_name: str, care_action: str, notes: str = "") -> str:
    """Records care given to a plant (e.g. watered, fertilized, misted, pruned) and updates Firestore.

    Args:
        plant_name: The name or id of the plant that was cared for.
        care_action: The action taken (e.g., 'watered', 'fertilized', 'repotted', 'pruned').
        notes: Optional observations or condition notes.

    Returns:
        A confirmation message with timestamp of recorded care.
    """
    details = get_plant_details(plant_name)
    if "error" in details:
        return details["error"]

    doc_id = details["id"]
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    plants_ref = db.collection("plants")
    plants_ref.document(doc_id).update({
        "last_cared_at": today,
        "last_care_action": care_action,
        "last_care_notes": notes
    })

    return f"Successfully recorded '{care_action}' for {details['name']} at {today}. Notes: {notes or 'None'}"


def update_plant_inventory(plant_name: str, quantity_change: int) -> str:
    """Updates the in-stock inventory count for a plant in Firestore.

    Args:
        plant_name: The name of the plant.
        quantity_change: Positive integer to add stock, or negative integer to reduce stock (e.g., -1 when adopted).

    Returns:
        A confirmation message with the updated in-stock count.
    """
    details = get_plant_details(plant_name)
    if "error" in details:
        return details["error"]

    doc_id = details["id"]
    current_stock = details.get("in_stock", 0)
    new_stock = max(0, current_stock + quantity_change)

    plants_ref = db.collection("plants")
    plants_ref.document(doc_id).update({"in_stock": new_stock})

    return f"Updated inventory for {details['name']}: {current_stock} -> {new_stock} in stock."


def get_weather(query: str) -> str:
    """Simulates a web search for local weather information.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with simulated weather information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def calculate_watering_schedule(
    plant_name: str,
    pot_diameter_inches: float = 6.0,
    room_temp_f: float = 72.0,
    humidity: str = "average",
) -> dict:
    """Calculates a customized watering interval and recommended water volume for a plant.

    Args:
        plant_name: Common name or species of the plant (e.g. 'Monstera', 'Snake Plant', 'Fern', 'Pothos').
        pot_diameter_inches: The diameter of the plant's container/pot in inches (e.g. 4.0, 6.0, 8.0, 10.0, 12.0).
        room_temp_f: Current ambient indoor temperature in degrees Fahrenheit (e.g. 68.0, 72.0, 78.0).
        humidity: Indoor air humidity level ('low', 'average', or 'high').

    Returns:
        A dictionary with recommended interval in days, water volume, and soil moisture guidelines.
    """
    plant_lower = plant_name.lower()

    # Base watering interval by botanical category (in days)
    if any(s in plant_lower for s in ["snake", "succulent", "cactus", "zz"]):
        base_days = 18.0
        depth_guide = "Allow soil to completely dry out throughout the entire pot."
    elif any(s in plant_lower for s in ["fern", "calathea", "peace lily", "fittonia"]):
        base_days = 4.0
        depth_guide = "Keep soil consistently lightly damp, never soggy."
    elif any(s in plant_lower for s in ["fig", "ficus", "fiddle"]):
        base_days = 9.0
        depth_guide = "Allow top 2-3 inches of soil to dry out before watering."
    else:  # Default tropicals (Monstera, Pothos, Philodendron, etc.)
        base_days = 8.0
        depth_guide = "Allow top 1-2 inches of soil to dry out before watering."

    # Pot size adjustment: larger pots hold moisture longer (square-root scaling)
    size_factor = (pot_diameter_inches / 6.0) ** 0.5
    interval = base_days * size_factor

    # Temperature adjustment: warmer rooms speed up evaporation
    if room_temp_f > 76.0:
        interval *= 0.85
    elif room_temp_f < 68.0:
        interval *= 1.15

    # Humidity adjustment: dry air speeds up soil drying
    if humidity.lower() == "low":
        interval *= 0.85
    elif humidity.lower() == "high":
        interval *= 1.20

    interval_days = max(2, round(interval))

    # Water volume rule of thumb: ~25% of pot volume
    pot_volume_cu_in = 0.785 * (pot_diameter_inches ** 3)
    water_oz = round(pot_volume_cu_in * 0.554 * 0.25, 1)
    water_ml = round(water_oz * 29.5735)

    return {
        "plant": plant_name,
        "pot_diameter_inches": pot_diameter_inches,
        "recommended_interval_days": interval_days,
        "water_frequency": f"Water approximately every {interval_days} days",
        "recommended_water_oz": water_oz,
        "recommended_water_ml": water_ml,
        "soil_moisture_guide": depth_guide,
        "tip": f"In a {room_temp_f}°F room with {humidity} humidity, expect soil to dry in about {interval_days} days."
    }


def lookup_botanical_species(query: str) -> dict:
    """Searches the Global Biodiversity Information Facility (GBIF) public API for live botanical taxonomy and scientific records.

    Args:
        query: Common or scientific plant name to look up (e.g. 'snake plant', 'monstera deliciosa', 'boston fern').

    Returns:
        A dictionary with scientific classification (family, genus, scientific name), natural descriptions, and botanical status.
    """
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.gbif.org/v1/species/search?q={encoded}&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "GreenhouseAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            results = data.get("results", [])
            if not results:
                return {"message": f"No botanical records found in GBIF for '{query}'."}
            top = results[0]
            descriptions = [d.get("description") for d in top.get("descriptions", []) if d.get("description")]
            return {
                "query": query,
                "canonical_name": top.get("canonicalName") or top.get("scientificName"),
                "scientific_name": top.get("scientificName"),
                "family": top.get("family"),
                "genus": top.get("genus"),
                "kingdom": top.get("kingdom"),
                "taxonomic_status": top.get("taxonomicStatus"),
                "botanical_description": descriptions[0] if descriptions else "No formal description provided in primary record.",
                "source": "Global Biodiversity Information Facility (GBIF)"
            }
    except Exception as e:
        return {"error": f"Failed to retrieve data from GBIF: {str(e)}"}


def geocode_address(address: str) -> dict:
    """Uses Google Maps Geocoding API to convert an address or place into geographic coordinates.

    Args:
        address: The street address, city, or place name (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary containing name, address, and location (latitude and longitude).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    try:
        encoded_address = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "GreenhouseAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "OK" or not data.get("results"):
                return {"error": f"Geocoding failed: {data.get('status', 'ZERO_RESULTS')}"}
            result = data["results"][0]
            loc = result.get("geometry", {}).get("location", {})
            return {
                "name": address,
                "address": result.get("formatted_address"),
                "location": {
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng"),
                },
            }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "florist",
    radius_meters: float = 5000.0,
    max_results: int = 5,
) -> list[dict]:
    """Uses Google Maps Places API (New) to search for nearby places around coordinates.

    Args:
        latitude: Latitude of the center location.
        longitude: Longitude of the center location.
        place_type: Place type to find (e.g. 'florist', 'park', 'store', 'hardware_store').
        radius_meters: Search radius in meters (default 5000.0).
        max_results: Max number of places to return (default 5, max 20).

    Returns:
        A list of place dictionaries with name, address, and location.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        payload = {
            "includedTypes": [place_type],
            "maxResultCount": min(max_results, 20),
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius_meters,
                }
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            places = data.get("places", [])
            results = []
            for p in places:
                display_name = p.get("displayName", {}).get("text", "Unknown")
                formatted_address = p.get("formattedAddress", "")
                loc = p.get("location", {})
                results.append({
                    "name": display_name,
                    "address": formatted_address,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                    },
                })
            return results
    except Exception as e:
        return [{"error": f"Places search failed: {str(e)}"}]


async def generate_plant_image(
    plant_name: str,
    setting: str = "in a stylish modern pot in a bright sunlit room",
    tool_context: ToolContext = None,
) -> dict:
    """Generates a realistic photograph of a plant using the gemini-3.1-flash-lite-image model, saves it as an artifact, and uploads it to public Cloud Storage.

    Args:
        plant_name: The name or species of the plant to generate an image for (e.g. 'Monstera Deliciosa', 'Snake Plant', 'Boston Fern').
        setting: Description of the surrounding room or pot setting.

    Returns:
        A dictionary with the plant name, public HTTPS image URL, artifact filename, and status.
    """
    try:
        prompt = f"A beautiful, high quality, realistic photograph of a healthy {plant_name} houseplant {setting}."
        response = image_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        mime_type = "image/jpeg"
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break
            if image_bytes:
                break

        if not image_bytes:
            return {"error": f"Failed to generate image bytes for {plant_name}."}

        # Format clean filename
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", plant_name.lower().strip())
        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"{slug}_{timestamp}.jpg"

        # 1. Save artifact for Playground Artifacts panel
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload to public Cloud Storage bucket
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "plant_name": plant_name,
            "public_url": public_url,
            "artifact_name": filename,
            "status": "success",
            "message": f"Successfully generated visual for {plant_name}. Viewable at: {public_url}"
        }
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}


# Agent Engine Sandbox Environment for Python Code Execution
SANDBOX_RESOURCE_NAME = "projects/1064544961832/locations/us-east1/reasoningEngines/1692949939123912704/sandboxEnvironments/5250009692956000256"
sandbox_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
)

# Vertex AI Memory Bank Configuration (reusing deployed Agent Engine)
MEMORY_BANK_ID = "1692949939123912704"


def memory_bank_service_builder():
    """Builds a VertexAiMemoryBankService instance for deployed runs."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION", "us-east1"),
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends session conversation turns to Memory Bank for cross-session long-term memory extraction."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

role_description = """You are Sprout, a friendly and expert greenhouse assistant and houseplant care specialist.
You remember the user's stated preferences, plant collection, environment details, and facts from previous conversations and use them to personalize your advice across sessions.
IMPORTANT - ALLERGIES & SAFETY: Pay critical attention to and always remember all user allergies, sensitivities, intolerances, and adverse health reactions (including plant allergies, pollen, latex/sap sensitivity, mold, pet allergies, or skin irritants). When recommending or discussing plants, always cross-reference the user's remembered allergies and warn them if a plant could trigger an allergic reaction or sensitivity.
You help plant parents browse available plants, check care requirements, check pet safety, update inventory, calculate personalized watering schedules, look up live botanical taxonomy and species records from GBIF, find nearby plant nurseries, florists, or garden centers using Google Maps, and generate visual images of plants.
You also have an Agent Engine Python sandbox available. You can write and execute Python code in the sandbox to perform custom calculations, simulations, mathematical modeling, and complex data analysis.
Always use your tools (`list_plants`, `get_plant_details`, `calculate_watering_schedule`, `lookup_botanical_species`, `geocode_address`, `find_nearby_places`, `generate_plant_image`, `record_plant_care`, `update_plant_inventory`) or run sandbox Python code to provide accurate, real-world data and visuals."""

ui_description = (
    "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
    "Never nest a Card inside a Card. "
    "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
    "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
    "nothing in adk web). "
    "You may include one Image component, but only when you have a public https "
    "URL for the image (for example the URL an image tool returns after uploading "
    "to a public bucket). Set the Image url to that exact https link, for example "
    "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
    "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
    "not have a public URL, add a short Text line noting the image instead. "
    "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
    "headings and emphasis. "
    "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
    "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
)

instruction = schema_manager.generate_system_prompt(
    role_description=role_description,
    workflow_description="Analyze the request, call relevant tools, and return structured A2UI UI when presenting plant details, care guides, inventory, or search results.",
    ui_description=ui_description,
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
        client_kwargs={"location": "global"},
    ),
    code_executor=sandbox_executor,
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_plants,
        get_plant_details,
        calculate_watering_schedule,
        lookup_botanical_species,
        geocode_address,
        find_nearby_places,
        generate_plant_image,
        record_plant_care,
        update_plant_inventory,
        get_weather,
        get_current_time,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
