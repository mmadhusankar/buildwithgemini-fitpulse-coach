"""Seed script for FitPulse Coach Firestore collections."""

import sys
from google.cloud import firestore

FIRESTORE_PROJECT = "qwiklabs-gcp-04-b7765e8a6bc2"

WORKOUTS = [
    {
        "id": "full-body-hiit",
        "title": "Full-Body HIIT Blast",
        "category": "cardio",
        "difficulty": "intermediate",
        "duration_minutes": 25,
        "calories_burned_est": 280,
        "exercises": [
            {"name": "Jumping Jacks", "duration_sec": 45, "rest_sec": 15},
            {"name": "Bodyweight Squats", "duration_sec": 45, "rest_sec": 15},
            {"name": "Push-ups", "duration_sec": 45, "rest_sec": 15},
            {"name": "Mountain Climbers", "duration_sec": 45, "rest_sec": 15},
            {"name": "Plank Hold", "duration_sec": 45, "rest_sec": 15},
        ],
        "description": "High-intensity full body circuit designed to burn fat and boost cardiovascular fitness with zero equipment.",
    },
    {
        "id": "upper-body-power",
        "title": "Upper Body Strength Builder",
        "category": "strength",
        "difficulty": "advanced",
        "duration_minutes": 40,
        "calories_burned_est": 320,
        "exercises": [
            {"name": "Dumbbell Overhead Press", "sets": 4, "reps": 10},
            {"name": "Barbell Rows", "sets": 4, "reps": 8},
            {"name": "Incline Push-ups", "sets": 3, "reps": 12},
            {"name": "Bicep Curls to Hammer Press", "sets": 3, "reps": 12},
            {"name": "Dips", "sets": 3, "reps": 10},
        ],
        "description": "Target shoulders, chest, and arms for hypertrophy and foundational strength.",
    },
    {
        "id": "core-mobility-flow",
        "title": "Core Sculpt & Mobility Flow",
        "category": "recovery",
        "difficulty": "beginner",
        "duration_minutes": 20,
        "calories_burned_est": 120,
        "exercises": [
            {"name": "Bird Dogs", "reps": 12, "per_side": True},
            {"name": "Dead Bugs", "reps": 10, "per_side": True},
            {"name": "Cat-Cow Stretch", "duration_sec": 60},
            {"name": "Glute Bridges", "reps": 15},
            {"name": "Child's Pose Breathing", "duration_sec": 90},
        ],
        "description": "Low-impact recovery and core stability routine improving spinal mobility and abdominal engagement.",
    },
]

RECIPES = [
    {
        "id": "mediterranean-quinoa-bowl",
        "title": "Mediterranean Quinoa Power Bowl",
        "meal_type": "lunch",
        "diet_tags": ["vegetarian", "gluten-free", "high-protein"],
        "prep_time_minutes": 15,
        "calories": 480,
        "macros": {"protein_g": 24, "carbs_g": 52, "fat_g": 18},
        "ingredients": ["1 cup cooked quinoa", "1/2 cup chickpeas", "1/2 cup cucumber", "1/4 cup feta cheese", "1 tbsp olive oil", "lemon juice", "parsley"],
        "instructions": "Layer cooked quinoa and chickpeas in a bowl, top with diced cucumber, kalamata olives, and crumbled feta. Whisk olive oil, lemon juice, and herbs, and drizzle over the bowl.",
    },
    {
        "id": "grilled-salmon-asparagus",
        "title": "Grilled Wild Salmon & Garlic Asparagus",
        "meal_type": "dinner",
        "diet_tags": ["keto", "high-protein", "gluten-free", "pescatarian"],
        "prep_time_minutes": 20,
        "calories": 520,
        "macros": {"protein_g": 42, "carbs_g": 8, "fat_g": 34},
        "ingredients": ["6 oz wild salmon fillet", "1 bunch fresh asparagus", "1 tbsp grass-fed butter", "2 cloves minced garlic", "sea salt", "black pepper", "lemon wedges"],
        "instructions": "Season salmon and asparagus with garlic, salt, and black pepper. Pan-sear or grill salmon skin-side down for 5 minutes, flip for 3 minutes. Sauté asparagus in butter until tender-crisp.",
    },
    {
        "id": "high-protein-berry-oats",
        "title": "Overnight High-Protein Berry Oats",
        "meal_type": "breakfast",
        "diet_tags": ["vegetarian", "high-fiber", "high-protein"],
        "prep_time_minutes": 5,
        "calories": 390,
        "macros": {"protein_g": 32, "carbs_g": 48, "fat_g": 8},
        "ingredients": ["1/2 cup rolled oats", "1 scoop vanilla whey/plant protein", "3/4 cup unsweetened almond milk", "1/2 cup mixed berries", "1 tbsp chia seeds"],
        "instructions": "Mix oats, protein powder, chia seeds, and almond milk in a jar. Refrigerate overnight. Top with fresh blueberries and strawberries before serving.",
    },
]

def seed():
    print(f"Connecting to Firestore with project: '{FIRESTORE_PROJECT}'...")
    db = firestore.Client(project=FIRESTORE_PROJECT)
    
    print("Seeding 'workouts' collection...")
    for item in WORKOUTS:
        doc_ref = db.collection("workouts").document(item["id"])
        doc_ref.set(item)
        print(f"  + Added workout: {item['id']} ({item['title']})")

    print("Seeding 'recipes' collection...")
    for item in RECIPES:
        doc_ref = db.collection("recipes").document(item["id"])
        doc_ref.set(item)
        print(f"  + Added recipe: {item['id']} ({item['title']})")

    print("✅ Firestore seed complete!")

if __name__ == "__main__":
    seed()
