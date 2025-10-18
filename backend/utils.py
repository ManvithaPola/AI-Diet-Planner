# backend/utils.py

import os
import json
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import random

# --- Load OpenAI API key ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Dataset path ---
dataset_path = r"C:\Users\polam\Downloads\AI Diet Planner\data\diet_dataset.csv"
df = pd.read_csv(dataset_path)

meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Snack']


# ---------------- Helper Functions ---------------- #

def filter_foods(category, health_conditions, used_foods=[]):
    """
    Filter foods by category, health suitability, and avoid already used foods.
    """
    query = "|".join(health_conditions)
    foods = df[
        (df['Category'] == category) &
        (df['Health Suitability'].str.contains(query, case=False, na=False)) &
        (~df['Food Item'].isin(used_foods))
    ]
    if len(foods) == 0:
        # fallback to all foods in category not used
        foods = df[
            (df['Category'] == category) &
            (~df['Food Item'].isin(used_foods))
        ]
    if len(foods) == 0:
        # fallback to all foods in category including repeats
        foods = df[df['Category'] == category]
    return foods


def generate_explanation(food_item, category, age, gender, health_conditions):
    """
    Generate AI explanation for a food item using OpenAI.
    """
    prompt = f"""
    You are a professional Indian dietitian.
    Explain in 2-3 sentences why including {food_item} for {category} 
    is beneficial for someone of age {age}, gender {gender}, 
    with these health conditions: {', '.join(health_conditions)}.
    Keep it simple, friendly, and personalized.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Explanation not available ({e})"


def generate_meal(category, age, gender, health_conditions, used_foods=[]):
    """
    Generate a single meal with its nutritional info and AI explanation.
    """
    foods = filter_foods(category, health_conditions, used_foods)
    meal_item = foods.sample(n=1).iloc[0]
    explanation = generate_explanation(meal_item['Food Item'], category, age, gender, health_conditions)

    return {
        'Food Item': str(meal_item['Food Item']),
        'Carbs': float(meal_item['Carbs']),
        'Protein': float(meal_item['Protein']),
        'Fat': float(meal_item['Fats']),
        'Calories': float(meal_item['Calories']),
        'Explanation': explanation
    }


def load_json_file(file_path):
    """
    Load JSON file safely. Return empty list if file not found or invalid.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_json_file(file_path, data):
    """
    Save data to JSON file.
    """
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
