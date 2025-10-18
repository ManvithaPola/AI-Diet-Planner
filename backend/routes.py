# backend/routes.py

from flask import Blueprint, render_template, request, jsonify
import os
import json
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import random

# --- Load OpenAI API key ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
dataset_path = os.path.join(DATA_DIR, "diet_dataset.csv")
previous_1day_path = os.path.join(DATA_DIR, "previous_1day_plans.json")
previous_7day_path = os.path.join(DATA_DIR, "previous_7day_plans.json")

# --- Load dataset ---
df = pd.read_csv(dataset_path)
meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Snack']

# --- Blueprint ---
main_routes = Blueprint('main_routes', __name__)

# --- Helper functions ---

def filter_foods(category, health_conditions, used_foods=[]):
    """Filter foods by category and health suitability, avoiding repeats if needed"""
    query = "|".join(health_conditions)
    foods = df[
        (df['Category'] == category) &
        (df['Health Suitability'].str.contains(query, case=False, na=False)) &
        (~df['Food Item'].isin(used_foods))
    ]
    if len(foods) == 0:
        foods = df[(df['Category'] == category) & (~df['Food Item'].isin(used_foods))]
    if len(foods) == 0:
        foods = df[df['Category'] == category]
    return foods

def generate_explanation(food_item, category, age, gender, health_conditions):
    """Generate AI explanation for a meal using OpenAI"""
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
    """Generate a single meal with explanation"""
    foods = filter_foods(category, health_conditions, used_foods)
    meal_item = foods.sample(n=1).iloc[0]
    explanation = generate_explanation(
        str(meal_item['Food Item']), category, age, gender, health_conditions
    )
    return {
        'Food Item': str(meal_item['Food Item']),
        'Carbs': float(meal_item['Carbs']),
        'Protein': float(meal_item['Protein']),
        'Fat': float(meal_item['Fats']),
        'Calories': float(meal_item['Calories']),
        'Explanation': explanation
    }

# --- Routes ---

@main_routes.route("/")
def home():
    return render_template("index.html")

@main_routes.route("/about")
def about():
    return render_template("about.html")

@main_routes.route("/contact")
def contact():
    return render_template("contact.html")

@main_routes.route("/plan/1day", methods=["GET", "POST"])
def plan_1day():
    if request.method == "POST":
        try:
            age = int(request.form.get("age"))
        except:
            return jsonify({"error": "Invalid age"}), 400

        gender = request.form.get("gender")
        health_conditions_input = request.form.get("health_conditions", "")
        health_conditions = [h.strip() for h in health_conditions_input.split(",") if h.strip()]
        if not health_conditions:
            return jsonify({"error": "Provide at least one health condition"}), 400

        daily_plan = {'Meals': {}, 'Total Calories': 0, 'Explanations': []}
        total_calories = 0
        day_explanations = []
        used_foods_1day = []

        for meal in meal_types:
            meal_info = generate_meal(meal, age, gender, health_conditions, used_foods_1day)
            used_foods_1day.append(meal_info['Food Item'])
            daily_plan['Meals'][meal] = f"{meal_info['Food Item']} (Carbs: {meal_info['Carbs']}g, Protein: {meal_info['Protein']}g, Fat: {meal_info['Fat']}g, {meal_info['Calories']} kcal)"
            total_calories += meal_info['Calories']
            day_explanations.append(meal_info['Explanation'])

        daily_plan['Total Calories'] = total_calories
        daily_plan['Explanations'] = day_explanations

        # Save to JSON
        if os.path.exists(previous_1day_path):
            try:
                with open(previous_1day_path, "r") as f:
                    previous_plans = json.load(f)
            except json.JSONDecodeError:
                previous_plans = []
        else:
            previous_plans = []

        previous_plans.append(daily_plan)
        with open(previous_1day_path, "w") as f:
            json.dump(previous_plans, f, indent=4)

        return jsonify(daily_plan)

    return render_template("1day.html")

@main_routes.route("/plan/7day", methods=["GET", "POST"])
def plan_7day():
    if request.method == "POST":
        try:
            age = int(request.form.get("age"))
        except:
            return jsonify({"error": "Invalid age"}), 400

        gender = request.form.get("gender")
        health_conditions_input = request.form.get("health_conditions", "")
        health_conditions = [h.strip() for h in health_conditions_input.split(",") if h.strip()]
        if not health_conditions:
            return jsonify({"error": "Provide at least one health condition"}), 400

        weekly_plan = []
        used_foods = []

        for day in range(1, 8):
            daily_plan = {'Day': f'Day {day}', 'Meals': {}, 'Total Calories': 0, 'Explanations': []}
            total_calories = 0
            day_explanations = []

            for meal in meal_types:
                meal_info = generate_meal(meal, age, gender, health_conditions, used_foods)
                used_foods.append(meal_info['Food Item'])
                daily_plan['Meals'][meal] = f"{meal_info['Food Item']} (Carbs: {meal_info['Carbs']}g, Protein: {meal_info['Protein']}g, Fat: {meal_info['Fat']}g, {meal_info['Calories']} kcal)"
                total_calories += meal_info['Calories']
                day_explanations.append(meal_info['Explanation'])

            daily_plan['Total Calories'] = total_calories
            daily_plan['Explanations'] = day_explanations
            weekly_plan.append(daily_plan)

        # Save weekly plan
        if os.path.exists(previous_7day_path):
            try:
                with open(previous_7day_path, "r") as f:
                    previous_weekly = json.load(f)
            except json.JSONDecodeError:
                previous_weekly = []
        else:
            previous_weekly = []

        previous_weekly.append(weekly_plan)
        with open(previous_7day_path, "w") as f:
            json.dump(previous_weekly, f, indent=4)

        return jsonify(weekly_plan)

    return render_template("7day.html")

@main_routes.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if request.method == "POST":
        user_prompt = request.form.get("prompt")
        if not user_prompt:
            return jsonify({"error": "Prompt cannot be empty"}), 400

        # In-memory chatbot history (limit to last 15 messages)
        if not hasattr(chatbot, "history"):
            chatbot.history = []

        if len(chatbot.history) > 15:
            chatbot.history = chatbot.history[-15:]

        messages = [{"role": "system", "content": "You are a professional Indian dietitian chatbot. Give healthy diet suggestions based on user input."}]
        for chat in chatbot.history:
            messages.append({"role": "user", "content": chat['user']})
            messages.append({"role": "assistant", "content": chat['ai']})
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            answer = f"Error: {e}"

        chatbot.history.append({"user": user_prompt, "ai": answer})
        return jsonify({"response": answer})

    return render_template("chatbot.html")
