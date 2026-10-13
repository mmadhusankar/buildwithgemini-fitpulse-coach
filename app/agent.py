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
from typing import Any, Dict, List, Optional
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google import genai
from google.cloud import firestore, storage
from google.genai import types

MODEL = "gemini-3.8-flash"
FIRESTORE_PROJECT = "qwiklabs-gcp-04-b7765e8a6bc2"

# Lazy-initialized Firestore client
_db: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """Returns a singleton Firestore client explicitly pinned to the GCP project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT)
    return _db


def list_workouts(category: Optional[str] = None, difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
    """Look up available workout routines from the catalog.

    Args:
        category: Optional category filter ('cardio', 'strength', 'recovery').
        difficulty: Optional difficulty filter ('beginner', 'intermediate', 'advanced').

    Returns:
        List of matching workout routines with their exercises, duration, and estimated calories burned.
    """
    db = get_firestore_client()
    query = db.collection("workouts")
    if category:
        query = query.where("category", "==", category.lower())
    if difficulty:
        query = query.where("difficulty", "==", difficulty.lower())

    results = []
    for doc in query.stream():
        results.append(doc.to_dict())
    return results


def search_recipes(meal_type: Optional[str] = None, diet_tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for healthy meal recipes from the nutrition catalog.

    Args:
        meal_type: Optional meal filter ('breakfast', 'lunch', 'dinner', 'snack').
        diet_tag: Optional dietary tag filter (e.g. 'high-protein', 'vegetarian', 'keto', 'gluten-free').

    Returns:
        List of matching recipes with ingredients, preparation instructions, and macronutrient breakdowns.
    """
    db = get_firestore_client()
    query = db.collection("recipes")
    if meal_type:
        query = query.where("meal_type", "==", meal_type.lower())
    if diet_tag:
        query = query.where("diet_tags", "array_contains", diet_tag.lower())

    results = []
    for doc in query.stream():
        results.append(doc.to_dict())
    return results


def log_activity_or_meal(
    entry_type: str,
    title: str,
    details: str,
    calories: Optional[int] = None,
    user_id: str = "default_user",
) -> str:
    """Log a user's completed workout, meal, or hydration entry to their activity log.

    Args:
        entry_type: Type of entry ('workout', 'meal', 'hydration').
        title: Short title describing the entry (e.g., 'Completed HIIT session', 'Grilled Salmon dinner').
        details: Additional details (e.g., exercises completed, meal notes, water in ounces).
        calories: Estimated calories burned (if workout) or consumed (if meal).
        user_id: The ID of the user. Defaults to 'default_user'.

    Returns:
        A confirmation message with the logged entry ID.
    """
    db = get_firestore_client()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc_data = {
        "user_id": user_id,
        "entry_type": entry_type.lower(),
        "title": title,
        "details": details,
        "calories": calories,
        "timestamp": timestamp,
    }
    doc_ref = db.collection("user_logs").document()
    doc_ref.set(doc_data)
    return f"Successfully logged {entry_type} entry '{title}' with ID: {doc_ref.id}."


def get_user_activity_logs(user_id: str = "default_user", limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve recent activity logs for a user.

    Args:
        user_id: The user ID to retrieve logs for. Defaults to 'default_user'.
        limit: Maximum number of recent entries to return (default 5).

    Returns:
        A list of recent log entries ordered from newest to oldest.
    """
    db = get_firestore_client()
    query = (
        db.collection("user_logs")
        .where("user_id", "==", user_id)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def calculate_metabolic_targets(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str = "moderate",
    goal: str = "maintenance",
) -> Dict[str, Any]:
    """Calculate Basal Metabolic Rate (BMR), Total Daily Energy Expenditure (TDEE),
    and target macronutrient grams based on user metrics and fitness goal.

    Args:
        weight_kg: Weight in kilograms.
        height_cm: Height in centimeters.
        age: Age in years.
        gender: 'male' or 'female'.
        activity_level: 'sedentary', 'light', 'moderate', 'active', or 'very_active'.
        goal: 'weight_loss', 'maintenance', or 'muscle_gain'.

    Returns:
        A dictionary containing BMR, TDEE, daily target calories, and recommended macros (protein, carbs, fat in grams).
    """
    # Mifflin-St Jeor Equation
    if gender.lower().startswith("m"):
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    multiplier = multipliers.get(activity_level.lower(), 1.55)
    tdee = bmr * multiplier

    # Adjust calorie target based on goal
    if goal.lower() in ["weight_loss", "fat_loss", "cut"]:
        target_calories = tdee - 500
        # 35% protein, 35% carbs, 30% fat
        protein_pct, carbs_pct, fat_pct = 0.35, 0.35, 0.30
    elif goal.lower() in ["muscle_gain", "hypertrophy", "bulk"]:
        target_calories = tdee + 350
        # 30% protein, 45% carbs, 25% fat
        protein_pct, carbs_pct, fat_pct = 0.30, 0.45, 0.25
    else:  # maintenance
        target_calories = tdee
        # 25% protein, 50% carbs, 25% fat
        protein_pct, carbs_pct, fat_pct = 0.25, 0.50, 0.25

    # Calories per gram: Protein=4, Carbs=4, Fat=9
    protein_g = round((target_calories * protein_pct) / 4)
    carbs_g = round((target_calories * carbs_pct) / 4)
    fat_g = round((target_calories * fat_pct) / 9)

    return {
        "bmr_kcal": round(bmr),
        "tdee_kcal": round(tdee),
        "daily_target_calories": round(target_calories),
        "goal": goal.lower(),
        "activity_level": activity_level.lower(),
        "macronutrients": {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
        },
    }


def search_global_recipes(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Search a free global public recipe database for cooking ideas, preparation times,
    servings, calories, and step-by-step instructions.

    Args:
        query: Ingredient or recipe name to search for (e.g., 'chicken', 'salad', 'smoothie', 'salmon').
        limit: Maximum number of recipe ideas to return (default 3).

    Returns:
        A list of matching recipe objects with calories, ingredients, and instructions.
    """
    import json
    import urllib.parse
    import urllib.request

    encoded_query = urllib.parse.quote(query)
    url = f"https://dummyjson.com/recipes/search?q={encoded_query}&limit={limit}"
    headers = {"User-Agent": "FitPulseCoach/1.0"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        recipes = []
        for r in data.get("recipes", []):
            recipes.append({
                "name": r.get("name"),
                "prep_time_minutes": r.get("prepTimeMinutes"),
                "cook_time_minutes": r.get("cookTimeMinutes"),
                "difficulty": r.get("difficulty"),
                "calories_per_serving": r.get("caloriesPerServing"),
                "ingredients": r.get("ingredients", []),
                "instructions": r.get("instructions", []),
            })
        return recipes if recipes else [{"message": f"No global recipes found matching '{query}'."}]
    except Exception as e:
        return [{"error": f"Failed to query global recipe database: {str(e)}"}]


def geocode_address(address: str) -> Dict[str, Any]:
    """Convert a street address or location name into geographic latitude and longitude coordinates
    using the Google Maps Geocoding API.

    Args:
        address: The address, city, or landmark (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary with formatted address and latitude/longitude coordinates.
    """
    import os
    import json
    import urllib.parse
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in the environment."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed: {data.get('status', 'No results')}"}

        first = data["results"][0]
        location = first["geometry"]["location"]
        return {
            "name": first.get("formatted_address", address),
            "address": first.get("formatted_address"),
            "location": {
                "latitude": location["lat"],
                "longitude": location["lng"],
            },
        }
    except Exception as e:
        return {"error": f"Failed to geocode address: {str(e)}"}


def find_nearby_places(
    place_type: str,
    latitude: float,
    longitude: float,
    radius_meters: float = 3000.0,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Find nearby places (e.g., 'gym', 'fitness_center', 'park', 'grocery_store', 'health')
    around a latitude/longitude coordinate using the Google Places API (New).

    Args:
        place_type: Place type to find (e.g., 'gym', 'fitness_center', 'park', 'grocery_store').
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        radius_meters: Search radius in meters (default 3000m / 3km).
        max_results: Maximum places to return (default 5).

    Returns:
        List of matching places with name, address, and location coordinates.
    """
    import os
    import json
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured in the environment."}]

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

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []
        for p in data.get("places", []):
            loc = p.get("location", {})
            results.append({
                "name": p.get("displayName", {}).get("text", "Unknown"),
                "address": p.get("formattedAddress", "Unknown Address"),
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                },
            })
        return results if results else [{"message": f"No nearby {place_type} found."}]
    except Exception as e:
        return [{"error": f"Failed to search nearby places: {str(e)}"}]


GCS_BUCKET_NAME = "fitpulse-assets-xej2ck"
_storage_client: Optional[storage.Client] = None
_genai_client: Optional[genai.Client] = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=FIRESTORE_PROJECT)
    return _storage_client


def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    return _genai_client


def generate_fitness_visual(
    prompt: str,
    title: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a photo or visual for a meal, exercise, or motivational achievement badge
    using the gemini-3.1-flash-lite-image model, save it as an artifact for the Playground,
    and upload it to Cloud Storage to return a public URL.

    Args:
        prompt: Detailed description of the image to generate (e.g. 'a delicious high-protein grilled salmon bowl with fresh greens and lemon').
        title: Short title or filename slug for the image (e.g. 'grilled_salmon_bowl').
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing the public image URL, filename, and title.
    """
    import re
    import uuid

    clean_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", title.lower().strip())
    unique_id = uuid.uuid4().hex[:6]
    filename = f"{clean_slug}_{unique_id}.jpg"

    try:
        client = get_genai_client()
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate a vibrant, high quality photo of: {prompt}",
        )

        image_bytes: Optional[bytes] = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return {"error": "Image model did not return image bytes."}

        # 1. Save artifact to ToolContext for the Playground's Artifacts panel
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=part)

        # 2. Upload image bytes directly to the public Cloud Storage bucket
        storage_client = get_storage_client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "title": title,
            "filename": filename,
            "public_url": public_url,
            "message": f"Successfully generated visual and uploaded to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload visual: {str(e)}"}


def generate_fitness_video(
    prompt: str,
    title: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a short video for an exercise, workout demo, or healthy recipe preparation
    using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video as an artifact for the Playground, uploads it to Cloud Storage,
    and returns its public HTTPS URL.

    Args:
        prompt: Detailed description of the video to generate (e.g. 'A fitness athlete performing clean form bodyweight squats in a sunny gym, smooth continuous motion').
        title: Short title or filename slug for the video (e.g. 'bodyweight_squats_demo').
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing the public video URL, filename, title, and status message.
    """
    import base64
    import re
    import uuid

    clean_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", title.lower().strip())
    unique_id = uuid.uuid4().hex[:6]
    filename = f"{clean_slug}_{unique_id}.mp4"
    mime_type = "video/mp4"

    try:
        client = get_genai_client()
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=f"Generate a clear, high quality fitness video: {prompt}",
        )

        video_bytes: Optional[bytes] = None
        if hasattr(interaction, "output_video") and interaction.output_video:
            raw_data = getattr(interaction.output_video, "data", None)
            if raw_data:
                video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
            if getattr(interaction.output_video, "mime_type", None):
                mime_type = interaction.output_video.mime_type

        if not video_bytes:
            return {"error": "Omni model did not return video bytes."}

        # 1. Save artifact to ToolContext for the Playground's Artifacts panel
        part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=part)

        # 2. Upload video bytes directly to the public Cloud Storage bucket
        storage_client = get_storage_client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "title": title,
            "filename": filename,
            "public_url": public_url,
            "message": f"Successfully generated video and uploaded to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload video: {str(e)}"}


AGENT_ENGINE_ID = "projects/494577185714/locations/us-east1/reasoningEngines/8709448207404367872"
SANDBOX_RESOURCE_NAME = "projects/494577185714/locations/us-east1/reasoningEngines/8709448207404367872/sandboxEnvironments/7674881432946212864"

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    agent_engine_resource_name=AGENT_ENGINE_ID,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each turn, send the session to Vertex AI Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

role_description = """You are FitPulse Coach, an expert fitness and nutrition AI companion.
You guide users to reach their fitness and health goals.
You diligently remember and respect ALL user allergies (e.g. nuts, shellfish, dairy, gluten, penicillin), intolerances, dietary restrictions, fitness goals, and personal preferences across all conversations to personalize recommendations and ensure user safety. Never recommend recipes, meals, or ingredients that conflict with a remembered allergy.
You can:
- Look up customized workout routines from our Firestore catalog via `list_workouts`.
- Suggest healthy meals and macros from our curated Firestore recipes via `search_recipes`.
- Search the live global public recipe database for culinary ideas and steps via `search_global_recipes`.
- Calculate custom BMR, TDEE, calorie targets, and macro splits via `calculate_metabolic_targets`.
- Safely run Python code in the sandbox to calculate complex training progressions, 1-rep max curves, or custom math.
- Geocode addresses and find nearby gyms, fitness centers, or parks via `geocode_address` and `find_nearby_places`.
- Generate visuals of meals, exercises, or milestone badges via `generate_fitness_visual`.
- Generate short demo videos of exercises, workout routines, or recipe preps via `generate_fitness_video`.
- Log completed workouts, meals, and hydration via `log_activity_or_meal`.
- Check the user's recent activity history via `get_user_activity_logs`.
Always be encouraging, actionable, and structured in your guidance."""

instruction = schema_manager.generate_system_prompt(
    role_description=role_description,
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
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        list_workouts,
        search_recipes,
        search_global_recipes,
        calculate_metabolic_targets,
        geocode_address,
        find_nearby_places,
        generate_fitness_visual,
        generate_fitness_video,
        log_activity_or_meal,
        get_user_activity_logs,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
