# Sprout Greenhouse Agent

![Sprout Greenhouse Demo](demo.gif)

A conversational AI assistant designed for houseplant parents, urban gardeners, and greenhouse managers. Built with Google's **Agent Development Kit (ADK)** and deployed on **Google Cloud Agent Platform (Agent Engine)**, Sprout provides plant care recommendations, inventory browsing, personalized watering calculations, botanical taxonomy lookups, local nursery searches, and AI-generated plant photography—rendering interactive UI components directly into the conversation via **A2UI**.

---

## What the Agent Does

Sprout acts as a personal plant specialist and greenhouse assistant, providing:

- **Houseplant Inventory & Adoption**: Browse greenhouse stock stored in Firestore, filter by pet toxicity, and check pricing and availability.
- **Cross-Session Long-Term Memory**: Remembers user preferences, home environment (lighting, temperature, humidity), pet ownership, and critically all user allergies and sensitivities across conversations.
- **Code Execution & Watering Calculations**: Calculates customized watering intervals, water volumes, and soil dry-down guidelines using Python code executed in an isolated sandbox.
- **Botanical Taxonomy & Species Information**: Looks up taxonomic classifications, family ranks, and common names from the Global Biodiversity Information Facility (GBIF).
- **Nearby Plant Nurseries & Garden Centers**: Finds local nurseries and florists using Google Maps Geocoding and Places APIs.
- **Visual Plant Generation**: Generates high-resolution images of houseplants in home settings using Imagen / Gemini Flash Lite Image and hosts them on Cloud Storage.
- **Rich Interactive UI (A2UI)**: Returns structured visual cards, columns, rows, images, and text rather than plain text responses.

---

## Google Cloud Services & Architecture

The agent is built with the following Google Cloud and external integrations directly wired in `app/agent.py`:

| Service / Tool | Implementation Details |
|---|---|
| **Vertex AI Agent Engine** | Hosts the ADK reasoning engine, managing sessions and runtime execution via the A2A protocol. |
| **Vertex AI Memory Bank** | Implements long-term memory via `VertexAiMemoryBankService`, `PreloadMemoryTool`, and `generate_memories_callback` to persist user facts, plant care history, and allergy warnings across sessions. |
| **Agent Engine Python Sandbox** | Provides safe, isolated Python execution using `AgentEngineSandboxCodeExecutor` for mathematical modeling and watering schedule calculations. |
| **Cloud Firestore** | NoSQL database storing plant documents (name, species, light, water, difficulty, price, pet safety, in-stock count, and care history logs). |
| **Cloud Storage** | Public bucket hosting generated plant imagery with signed or public HTTP URLs. |
| **Vertex AI Image Generation** | Uses `gemini-3.1-flash-lite-image` to create photorealistic imagery based on plant care prompts. |
| **A2UI (Agent-to-User Interface)** | Configured with `A2uiSchemaManager` (version 0.8 Basic Catalog) and `a2ui_callback` to emit structured cards, lists, and images to the frontend. |
| **Google Maps Platform** | Geocoding API and Places API (New) for location searches and nearby plant nursery discovery. |
| **GBIF Botanical Species API** | Open botanical taxonomy query endpoint for scientific family, genus, and vernacular names. |

### Status of Planned Features (from Project Brief)

- **Implemented**: Memory Bank (cross-session memory), Firestore database, Cloud Storage image hosting, Imagen image generation, Agent Engine Python code sandbox, A2UI rich cards, Google Maps Places & Geocoding, GBIF botanical records.
- **Planned, not yet implemented**: Cloud Trace distributed tracing integration; Perenual Botanical API (evaluated during planning, superseded by GBIF API).

---

## Project Structure

```
greenhouse-agent/
├── app/
│   ├── agent.py               # Main ADK agent definition, tools, and callbacks
│   ├── a2ui_utils.py          # A2UI after_model_callback and payload parser
│   ├── fast_api_app.py        # ADK FastAPI backend server
│   └── app_utils/             # Core ADK runtime helpers
├── frontend/                  # Lightweight chat frontend and A2A proxy
│   ├── main.py                # FastAPI A2A client proxy to Agent Engine
│   ├── Dockerfile             # Container definition for Cloud Run
│   └── static/
│       └── index.html         # Custom branded chat UI with built-in A2UI renderer
├── demo.gif                   # Looping recording of the agent in action
├── agents-cli-manifest.yaml   # Project manifest and deployment target configuration
├── pyproject.toml             # Python dependencies managed with uv
└── seed_firestore.py          # Seed script for greenhouse plant database
```

---

## Local Setup & Development

### Prerequisites

- Python 3.12+
- `uv` package manager
- Google Cloud SDK (`gcloud`)
- An authenticated GCP project with Vertex AI and Firestore APIs enabled

### 1. Clone & Install Dependencies

```bash
cd greenhouse-agent
uv sync
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
PROJECT_ID="<your-gcp-project-id>"
GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
GOOGLE_MAPS_API_KEY="<your-google-maps-api-key>"
```

### 3. Seed Firestore Database

Initialize the `plants` collection in Firestore with sample greenhouse inventory:

```bash
uv run python seed_firestore.py
```

### 4. Run the Agent Playground

Start the local ADK Web playground with hot-reloading and Memory Bank integration:

```bash
uv run adk web . --port 8000 --reload_agents --memory_service_uri=agentengine://<YOUR_AGENT_ENGINE_ID>
```

### 5. Run the Custom Frontend

To run the custom branded frontend:

```bash
cd frontend
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/us-east1/reasoningEngines/<AGENT_ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT=8080
python main.py
```

Open a browser to the local port displayed in the console to interact with Sprout.

---

## Deployment

### Deploy Agent to Vertex AI Agent Engine

```bash
agents-cli deploy --update-env-vars GOOGLE_MAPS_API_KEY="<your-api-key>"
```

### Deploy Frontend to Cloud Run

```bash
cd frontend
gcloud run deploy frontend \
  --source . \
  --region us-east1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/us-east1/reasoningEngines/<AGENT_ENGINE_ID>",AGENT_DIRECTORY="app" \
  --allow-unauthenticated
```
