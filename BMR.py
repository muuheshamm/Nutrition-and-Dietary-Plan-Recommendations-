import pandas as pd
import random

def calc_bmr(age, gender, weight, height):
    """Calculate BMR using the Mifflin-St Jeor Equation."""
    if gender.lower() == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    elif gender.lower() == "female":
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        raise ValueError("Invalid gender. Choose 'male' or 'female'.")
    return bmr

def calc_total_calories_in_day(bmr, activity_level):
    """Adjust BMR based on activity level."""
    activity_multipliers = {
        "sedentary": 1.2,
        "lightly active": 1.375,
        "moderately active": 1.55,
        "active": 1.725,
        "very active": 1.9
    }
    if activity_level not in activity_multipliers:
        raise ValueError("Invalid activity level")
    return bmr * activity_multipliers[activity_level]

def adjust_macronutrient_ratios(goal):
    """Return macronutrient ratios based on goal."""
    if goal == "lose weight":
        return {"protein": 0.45, "carb": 0.35, "fats": 0.2}
    elif goal == "gain weight":
        return {"protein": 0.35, "carb": 0.45, "fats": 0.2}
    elif goal == "gain muscles":
        return {"protein": 0.5, "carb": 0.3, "fats": 0.2}
    else:
        raise ValueError("Invalid goal. Choose 'lose weight', 'gain weight', or 'gain muscles'.")

def allocate_grams(target_calories, target_ratio, food_df, meal_type, excluded_items):
    """Allocate food items for a meal based on calorie targets."""
    allocated_items = []
    if meal_type.startswith("snack"):
        snack_items = food_df[
            (food_df["meal_category"] == "snack") &
            (~food_df["food_item"].isin(excluded_items))
        ]
        if snack_items.empty:
            raise ValueError("No items available for snack selection.")
        snack_item = snack_items.sample().iloc[0]
        grams = (target_calories / snack_item["calories_per_100_gm"]) * 100
        allocated_items.append({
            "item": snack_item["food_item"],
            "grams": grams,
            "calories": (snack_item["calories_per_100_gm"] * grams) / 100,
            "protein": (snack_item["protein_per_100_gm"] * grams) / 100,
            "carb": (snack_item["carb_per_100_gm"] * grams) / 100,
            "fats": (snack_item["fats_per_100_gm"] * grams) / 100
        })
        return allocated_items

    for macronutrient, ratio in target_ratio.items():
        target_macro_calories = target_calories * ratio
        macro_items = food_df[
            (food_df["type_category"] == macronutrient) &
            (food_df["meal_category"] != "snack") &
            (~food_df["food_item"].isin(excluded_items))
        ]
        if macro_items.empty:
            print(f"Warning: No items available for {macronutrient} selection. Skipping.")
            continue
        item = macro_items.sample().iloc[0]
        grams = (target_macro_calories / item["calories_per_100_gm"]) * 100
        allocated_items.append({
            "item": item["food_item"],
            "grams": grams,
            "calories": (item["calories_per_100_gm"] * grams) / 100,
            "protein": (item["protein_per_100_gm"] * grams) / 100,
            "carb": (item["carb_per_100_gm"] * grams) / 100,
            "fats": (item["fats_per_100_gm"] * grams) / 100
        })
    return allocated_items

def recommend_meals(calories_needed, goal, food_df, num_meals_per_day, excluded_items=[]):
    """Generate meal recommendations based on target calories, number of meals, and exclusions."""
    # Adjust total daily calories based on the goal
    if goal == "lose weight":
        target_calories = calories_needed * 0.8
    elif goal == "gain weight":
        target_calories = calories_needed * 1.2
    elif goal == "gain muscles":
        target_calories = calories_needed * 1.1
    else:
        raise ValueError("Invalid goal. Choose 'lose weight', 'gain weight', or 'gain muscles'.")

    # Adjust macronutrient ratios based on the goal
    macro_ratios = adjust_macronutrient_ratios(goal)

    # Dynamically calculate meal ratios
    meal_ratios = {f"meal_{i+1}": 1 / num_meals_per_day for i in range(num_meals_per_day)}
    recommended_meals = {}

    total_calories_generated = 0

    for meal, ratio in meal_ratios.items():
        meal_calories = target_calories * ratio
        meal_items = allocate_grams(meal_calories, macro_ratios, food_df, meal, excluded_items)

        total_meal_calories = sum(item["calories"] for item in meal_items)
        total_meal_protein = sum(item["protein"] for item in meal_items)
        total_meal_carb = sum(item["carb"] for item in meal_items)
        total_meal_fats = sum(item["fats"] for item in meal_items)

        recommended_meals[meal] = {
            "items": meal_items,
            "total_calories": total_meal_calories,
            "total_protein": total_meal_protein,
            "total_carb": total_meal_carb,
            "total_fats": total_meal_fats
        }

        total_calories_generated += total_meal_calories

    print(f"Total Generated Calories: {total_calories_generated:.2f} vs Target Calories: {target_calories:.2f}")
    return recommended_meals
