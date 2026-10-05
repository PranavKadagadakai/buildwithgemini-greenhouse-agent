"""Seed Firestore with initial greenhouse plant inventory."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-8fd0a7df8d09"

SEED_PLANTS = [
    {
        "id": "monstera-deliciosa",
        "name": "Monstera Deliciosa",
        "species": "Monstera deliciosa",
        "light": "Bright indirect light",
        "water": "Water every 1-2 weeks, allow soil to dry out between waterings",
        "difficulty": "Easy to Moderate",
        "pet_safe": False,
        "price": 34.99,
        "in_stock": 8,
        "care_tips": "Wipe leaves to keep them dust-free; provide a moss pole for climbing.",
        "last_cared_at": "2026-10-01"
    },
    {
        "id": "snake-plant",
        "name": "Snake Plant (Sansevieria)",
        "species": "Dracaena trifasciata",
        "light": "Low to bright indirect light; very adaptable",
        "water": "Water every 2-3 weeks; highly drought-tolerant, do not overwater",
        "difficulty": "Beginner / Indestructible",
        "pet_safe": False,
        "price": 24.50,
        "in_stock": 15,
        "care_tips": "Excellent air purifier; thrives on neglect in well-draining soil.",
        "last_cared_at": "2026-09-28"
    },
    {
        "id": "golden-pothos",
        "name": "Golden Pothos",
        "species": "Epipremnum aureum",
        "light": "Low to medium indirect light",
        "water": "Water every 1-2 weeks when top 2 inches of soil feel dry",
        "difficulty": "Beginner",
        "pet_safe": False,
        "price": 18.00,
        "in_stock": 20,
        "care_tips": "Fast growing trailing vine; great for hanging planters or shelves.",
        "last_cared_at": "2026-10-03"
    },
    {
        "id": "boston-fern",
        "name": "Boston Fern",
        "species": "Nephrolepis exaltata",
        "light": "Medium to bright indirect light",
        "water": "Keep soil consistently moist; prefers high humidity",
        "difficulty": "Moderate",
        "pet_safe": True,
        "price": 22.00,
        "in_stock": 6,
        "care_tips": "Pet-friendly! Mist frequently or keep in a bathroom with indirect light.",
        "last_cared_at": "2026-10-04"
    },
    {
        "id": "spider-plant",
        "name": "Spider Plant",
        "species": "Chlorophytum comosum",
        "light": "Bright indirect light; tolerates moderate shade",
        "water": "Water when top half of soil is dry, roughly once a week",
        "difficulty": "Beginner",
        "pet_safe": True,
        "price": 16.50,
        "in_stock": 12,
        "care_tips": "Completely pet-safe and non-toxic. Produces cute 'spiderettes' that can be propagated.",
        "last_cared_at": "2026-10-02"
    },
    {
        "id": "fiddle-leaf-fig",
        "name": "Fiddle Leaf Fig",
        "species": "Ficus lyrata",
        "light": "Consistent bright, filtered indirect sunlight",
        "water": "Water when top 2-3 inches feel dry; sensitive to overwatering and drafts",
        "difficulty": "Intermediate",
        "pet_safe": False,
        "price": 49.99,
        "in_stock": 4,
        "care_tips": "Keep away from heating vents and AC drafts. Rotate pot weekly for even growth.",
        "last_cared_at": "2026-09-30"
    }
]


def seed():
    print(f"Connecting to Firestore with hardcoded project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)
    plants_ref = db.collection("plants")

    for plant in SEED_PLANTS:
        doc_id = plant["id"]
        plants_ref.document(doc_id).set(plant)
        print(f"Seeded: {plant['name']} ({doc_id})")

    print(f"Successfully seeded {len(SEED_PLANTS)} plants into Firestore collection 'plants'.")


if __name__ == "__main__":
    seed()
