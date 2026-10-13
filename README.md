# FitPulse Coach 🏋️‍♂️🥗

FitPulse Coach is an intelligent fitness and nutrition companion agent built with the **Google Agent Development Kit (ADK)** and powered by **Gemini**. It helps users discover tailored workout routines, plan balanced healthy meals, calculate metabolic targets, find nearby fitness facilities, track daily progress, and generate visual demonstration media.

![FitPulse Coach Demo](demo.gif)

---

## 🌟 Capabilities & Features

FitPulse Coach implements the following core features:

- **Long-Term Memory across Sessions**: Uses Vertex AI Memory Bank (`PreloadMemoryTool` and callback extraction) to diligently remember user fitness goals, dietary restrictions, allergies, and personal preferences across conversations.
- **Workout & Recipe Database**: Fetches structured workouts and recipe collections stored in **Google Cloud Firestore**.
- **Global Recipe Search**: Connects to the live global recipe database via Spoonacular API integration to search custom ingredients, cuisines, and preparation instructions.
- **Metabolic & Nutrition Calculator**: Computes Basal Metabolic Rate (BMR), Total Daily Energy Expenditure (TDEE), and macro targets based on age, gender, weight, height, and activity level.
- **Places & Gym Discovery**: Geocodes user locations and queries the Google Places API to find nearby gyms, fitness centers, and parks.
- **Visual Image Generation**: Uses `gemini-3.1-flash-lite-image` via the Google GenAI SDK to generate visuals of plated meals, workout movements, and milestone badges. Images are saved as agent artifacts and uploaded directly to **Google Cloud Storage**.
- **Exercise Video Demos**: Generates short video demonstrations using Google's Omni model (`gemini-omni-flash-preview`), saved as artifacts and hosted on Cloud Storage.
- **Activity & Hydration Logging**: Records completed workout sessions, meals, and water intake directly into Cloud Firestore for ongoing progress tracking.
- **Code Execution Sandbox**: Equipped with `AgentEngineSandboxCodeExecutor` to run calculations (e.g. progressive overload curves, 1-rep max estimations).
- **A2UI Rich Card Rendering**: Emits A2UI schema surfaces (Cards, Columns, Rows, Images, and formatted text) for clean visual layout in compatible frontends.

---

## ☁️ Google Cloud & Vertex AI Services

The agent integrates with the following Google Cloud services:

| Service / Tool | Purpose in FitPulse Coach |
|---|---|
| **Gemini (`gemini-3.8-flash`)** | Core reasoning model for conversational guidance and tool orchestration |
| **Google GenAI Image (`gemini-3.1-flash-lite-image`)** | Generates high-quality photos of meals, badges, and exercises |
| **Google GenAI Omni (`gemini-omni-flash-preview`)** | Generates short demonstration video clips for exercises and recipes |
| **Vertex AI Memory Bank** | Persists user facts, allergies, dietary constraints, and goals across sessions |
| **Google Cloud Firestore** | Stores workout catalog, recipe documents, and user activity/meal logs |
| **Google Cloud Storage** | Hosts generated meal/exercise images and video assets with public URLs |
| **Agent Engine Code Sandbox** | Runs isolated Python computations for training curves and formula math |
| **Google Places & Geocoding APIs** | Discovers nearby fitness studios, gyms, and sports parks |

---

## 🛠️ Project Structure

```text
.
├── app/
│   ├── __init__.py         # App export
│   ├── agent.py            # Root agent, tools, callbacks, and A2UI integration
│   └── a2ui_utils.py       # A2UI response formatting callback
├── frontend/
│   ├── main.py             # FastAPI proxy connecting to deployed Agent Engine
│   └── static/
│       └── index.html      # Responsive chat interface with dialogue bubbles & prompt pills
├── agents-cli-manifest.yaml# Agent runtime deployment manifest
├── demo.gif                # Animated recording of the live agent in action
├── pyproject.toml          # Python project dependencies
└── README.md
```

---

## 🚀 Local Setup & Running

### 1. Prerequisites

- Python `>=3.11, <3.14`
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Google Cloud SDK (`gcloud`) authenticated to your GCP project:
  ```bash
  gcloud auth application-default login
  ```

### 2. Environment Variables

Set your Google Cloud project and optional API keys:

```bash
export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
# Optional: for live external recipe search and places discovery
export SPOONACULAR_API_KEY="<your-spoonacular-key>"
export GOOGLE_MAPS_API_KEY="<your-google-maps-key>"
```

### 3. Run Locally with ADK Web

Launch the interactive ADK playground:

```bash
uv run adk web . --port 8080 --reload_agents
```

Open your browser to the local address output by the CLI to chat with the agent and inspect tool calls, artifacts, and A2UI cards.

### 4. Run the Custom Chat Frontend

To run the standalone FastAPI chat UI against a deployed Reasoning Engine:

```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-id>/locations/<region>/reasoningEngines/<engine-id>"
export AGENT_DIRECTORY="app"
uv run python main.py
```
