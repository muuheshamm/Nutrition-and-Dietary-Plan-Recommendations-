from BMR import calc_bmr, calc_total_calories_in_day, allocate_grams, recommend_meals, adjust_macronutrient_ratios
import pandas as pd
import subprocess
import json
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

import test1 as t1

INPUT_FILE = 'user_profile.json'
OUTPUT_FILE = 'nutrition_plan.json'
MODEL_NAME = "deepseek-r1:1.5b"

load_dotenv()
llm = ChatGroq(
    temperature=0.2,
    model_name="llama3-70b-8192",
    api_key='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'
)

def main():
    # Sample food data
    sample_data = {
        "food_item": [
            "Oatmeal", "Eggs", "Chicken Breast", "Salmon", "Almonds",
            "Avocado", "Banana", "Greek Yogurt", "Brown Rice", "Spinach",
            "Quinoa", "Tofu", "Peanut Butter", "Sweet Potato", "Broccoli",
            "Trail Mix", "Protein Bar", "Cheese Stick", "Dark Chocolate", "Rice Cake"
        ],
        "calories_per_100_gm": [68, 155, 165, 208, 576, 160, 89, 59, 110, 23, 120, 76, 588, 86, 34, 500, 350, 300, 546, 380],
        "carb_per_100_gm": [12, 1.1, 0, 0, 21, 8.5, 22.8, 3.6, 23, 3.6, 21.3, 1.9, 20, 20, 7, 50, 40, 1, 50, 80],
        "protein_per_100_gm": [2.4, 13, 31, 20, 21, 2, 1.1, 10, 2.6, 2.9, 4.4, 8, 25, 1.6, 2.8, 10, 20, 25, 6, 7],
        "fats_per_100_gm": [1.4, 11, 3.6, 13, 49, 15, 0.3, 0.4, 0.9, 0.4, 2, 4.8, 50, 0.1, 0.4, 30, 15, 20, 40, 2],
        "type_category": [
            "carb", "protein", "protein", "protein", "fats",
            "fats", "carb", "protein", "carb", "carb",
            "carb", "protein", "fats", "carb", "carb",
            "fats", "carb", "protein", "fats", "carb"
        ],
        "meal_category": [
            "breakfast", "breakfast", "lunch", "lunch", "snack",
            "snack", "snack", "breakfast", "lunch", "dinner",
            "lunch", "lunch", "snack", "lunch", "dinner",
            "snack", "snack", "snack", "snack", "snack"
        ]
    }

    food_df = pd.DataFrame(sample_data)

    


    # User data
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        user_profile = json.load(f)
    age = user_profile['age']
    gender = user_profile['gender']
    weight = user_profile['weight']
    height = user_profile['height']
    activity_level = "active" #user_profile['activity_level']
    goal = user_profile['goal']
    num_meals_per_day = user_profile['meals_per_day'] 

    # Calculate BMR and daily calorie needs
    bmr = calc_bmr(age, gender, weight, height)
    calories_needed = calc_total_calories_in_day(bmr, activity_level)

    # Generate recommended meals
    recommended_meals = recommend_meals(calories_needed, goal, food_df, num_meals_per_day)

    # Format the output
    output = []
    output.append(f"BMR = {bmr:.2f} calories")
    output.append(f"Calories per day = {calories_needed:.2f} calories\n")
    output.append(f"Number of Meals per Day = {num_meals_per_day}\n")

    output.append("Recommended Meals:")
    total_calories = 0
    total_protein = 0
    total_carb = 0
    total_fats = 0

    for meal, details in recommended_meals.items():
        output.append(f"\n{meal.capitalize()}:")
        for item in details["items"]:
            output.append(f"  - {item['item']}: {item['grams']:.2f}g ({item['calories']:.2f} calories, {item['protein']:.2f}g protein, {item['carb']:.2f}g carb, {item['fats']:.2f}g fats)")
        output.append(f"  Total Calories: {details['total_calories']:.2f}")
        output.append(f"  Total Protein: {details['total_protein']:.2f}g")
        output.append(f"  Total Carbs: {details['total_carb']:.2f}g")
        output.append(f"  Total Fats: {details['total_fats']:.2f}g")

        total_calories += details['total_calories']
        total_protein += details['total_protein']
        total_carb += details['total_carb']
        total_fats += details['total_fats']

    output.append("\nTotal for the day:")
    output.append(f"  Total Calories: {total_calories:.2f}")
    output.append(f"  Total Protein: {total_protein:.2f}g")
    output.append(f"  Total Carbs: {total_carb:.2f}g")
    output.append(f"  Total Fats: {total_fats:.2f}g")

    # Save to file
    with open("meal_plan_output.txt", "w") as file:
        file.write("\n".join(output))

    print("Output saved to meal_plan_output.txt")

    # Read the saved file and send it to the LLM
    with open("meal_plan_output.txt", "r") as file:
        meal_plan_content = file.read()

   
    messages = [
        {"role": "system", "content": "You are an expert nutrition assistant."},
        {
            "role": "user",
            "content": (
                f"Based on the following user data:\n"
                f"- Age: {age}\n"
                f"- Gender: {gender}\n"
                f"- Weight: {weight} kg\n"
                f"- Height: {height} cm\n"
                f"- Activity level: {activity_level}\n"
                f"- Goal: {goal}\n"
                f"- Number of meals per day: {num_meals_per_day}\n\n"
                f"Here is the current meal plan:\n\n{meal_plan_content}\n\n"
                "Please adjust the meal plan to better align with the user's data, ensuring it supports their goal of losing weight while maintaining a balanced nutrient profile. "
                "Provide a complete adjusted plan with all meals and their nutritional details."
                f"For Each Meal, Provide:** - Detailed menu items that match preferences - Calories for each item - Total calories for the meal - Macronutrient breakdown (proteins, carbs, fats) - Alternatives for food allergies and dislikes"
                f"Response in json format as this template:"
                f"days->[day1 -> [meals -> [meal1 -> items -> [item1 -> [item name -> '', protin -> '', carbs -> '', fats -> '', caluris -> ''], item2, ..], meal2, ...]], day2, ..]"
                
            ),
        },
    ]

    ai_msg = llm.invoke(messages)
    print(ai_msg.content)

    # Display LLM Adjustments
    # print("\nLLM Adjustments:")
    # print(ai_msg.get("content", "No response content"))

if __name__ == "__main__":
    main()