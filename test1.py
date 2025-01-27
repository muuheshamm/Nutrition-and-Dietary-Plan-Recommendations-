import subprocess
import json
import math
import re

DATA_FILE = 'venv/datausers.json'
MODEL_NAME = "deepseek-r1:1.5b"
OUTPUT_FILE = 'nutrition_plan.json'

def calculate_health_metrics(user_data):
    """Calculate all required health metrics from user data"""
    profile = user_data['user_profile']
    
    # Basic calculations
    height_m = profile['height'] / 100
    bmi = round(profile['weight'] / (height_m ** 2), 2)
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile['activity_level'])
    calorie_goal = calculate_calorie_goal(tdee, profile['goal'])
    water_intake = calculate_water_intake(profile)
    
    return {
        'bmi': bmi,
        'calorie_goal': calorie_goal,
        'water_intake': water_intake,
        'meals_per_day': profile['meals_per_day'],
        'preferences': profile['food_preferences']
    }

def calculate_bmr(profile):
    """Calculate Basal Metabolic Rate"""
    if profile['gender'].lower() == 'male':
        return 88.362 + (13.397 * profile['weight']) + (4.799 * profile['height']) - (5.677 * profile['age'])
    else:
        return 447.593 + (9.247 * profile['weight']) + (3.098 * profile['height']) - (4.330 * profile['age'])

def calculate_tdee(bmr, activity_level):
    """Calculate Total Daily Energy Expenditure"""
    multipliers = {
        'sedentary': 1.2,
        'lightly active': 1.375,
        'moderately active': 1.55,
        'very active': 1.725,
        'extra active': 1.9
    }
    return bmr * multipliers.get(activity_level.lower(), 1.2)

def calculate_calorie_goal(tdee, goal):
    """Adjust calories based on weight goal"""
    if goal == 'lose weight': return tdee - 500
    if goal == 'gain weight': return tdee + 500
    return tdee

def calculate_water_intake(profile):
    """Calculate daily water intake recommendation"""
    base = profile['weight'] * 0.035
    activity_add = {
        'sedentary': 0.2,
        'lightly active': 0.3,
        'moderately active': 0.5,
        'very active': 0.7,
        'extra active': 0.9
    }.get(profile['activity_level'].lower(), 0.0)
    return round(base + activity_add, 1)

def generate_prompt_template(metrics, user_name):
    """Create the strict JSON generation prompt"""
    return f"""Generate a 7-day nutrition plan in VALID JSON format for {user_name} following EXACTLY this structure:
{{
  "target_calories_per_day": {metrics['calorie_goal']},
  "target_water_intake_liters": {metrics['water_intake']},
  "BMI": {metrics['bmi']},
  "days": [
    {{
      "day": "Monday",
      "meals": [
        {{
          "meal_name": "Breakfast",
          "items": [
            {{
              "name": "Food Name",
              "calories": 300,
              "protein_grams": 20,
              "carbs_grams": 35,
              "fats_grams": 10
            }}
          ]
        }}
      ]
    }}
  ]
}}

Requirements:
- 7 days (Monday-Sunday)
- {metrics['meals_per_day']} meals per day
- Avoid: {", ".join(metrics['preferences']['allergies'])}
- Include: {", ".join(metrics['preferences']['liked_foods'])}
- Daily calories: {metrics['calorie_goal']} ±50
- Water target: {metrics['water_intake']}L

Rules for JSON:
1. Use double quotes ONLY
2. No trailing commas
3. No markdown formatting
4. No additional text outside JSON
5. Maintain exact structure
6. All numbers must be integers
7. Meal names must be breakfast, lunch, dinner, or snack variations

Return ONLY the JSON object with no commentary.
"""

def clean_json_response(raw_response):
    """Extract and fix common JSON formatting issues"""
    # Remove non-JSON content
    json_str = re.sub(r'^[^{]*', '', raw_response, flags=re.DOTALL)
    json_str = re.sub(r'[^}]*$', '', json_str, flags=re.DOTALL)
    
    # Fix common syntax errors
    json_str = json_str.replace("'", '"')  # Replace single quotes
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # Trailing commas
    json_str = re.sub(r'(\w+)(\s*:\s*)', r'"\1"\2', json_str)  # Unquoted keys
    
    # Ensure number formatting
    json_str = re.sub(r'(:\s*)(\d+\.\d+)(\s*[,}])', lambda m: f'{m.group(1)}{round(float(m.group(2)), 1)}{m.group(3)}', json_str)
    
    return json_str

def validate_nutrition_plan(plan):
    """Ensure the generated plan meets requirements"""
    required_keys = ['target_calories_per_day', 'target_water_intake_liters', 'BMI', 'days']
    if not all(key in plan for key in required_keys):
        raise ValueError("Missing required top-level keys")
    
    if len(plan['days']) != 7:
        raise ValueError("Incorrect number of days - expected 7")
        
    total_calories = sum(
        item['calories']
        for day in plan['days']
        for meal in day['meals']
        for item in meal['items']
    )
    
    avg_daily = total_calories / 7
    if not (plan['target_calories_per_day'] - 50 <= avg_daily <= plan['target_calories_per_day'] + 50):
        raise ValueError("Calorie target deviation too large")

def generate_nutrition_plan():
    """Main generation workflow"""
    try:
        # Load user data
        with open(DATA_FILE, 'r') as f:
            user_data = json.load(f)
            
        # Calculate metrics
        metrics = calculate_health_metrics(user_data)
        user_name = user_data['user_profile']['name']
        
        # Generate prompt
        prompt = generate_prompt_template(metrics, user_name)
        
        # Run LLM
        result = subprocess.run(
            ["ollama", "run", MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        
        # Process output
        raw_json = result.stdout.strip()
        cleaned_json = clean_json_response(raw_json)
        
        # Parse and validate
        plan = json.loads(cleaned_json)
        validate_nutrition_plan(plan)
        
        # Save output
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(plan, f, indent=2)
            
        print(f"Successfully generated nutrition plan at {OUTPUT_FILE}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"JSON Error: {str(e)}")
        print("Raw model output:")
        print(raw_json)
        return False
    except subprocess.CalledProcessError as e:
        print(f"Model Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if generate_nutrition_plan():
        print("Operation completed successfully!")
    else:
        print("Failed to generate plan. Check error messages.")