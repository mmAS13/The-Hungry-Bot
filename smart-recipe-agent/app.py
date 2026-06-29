# app.py
# This is the main backend file for The Hungry Bot 🍳 web application.
# It sets up a Flask web server, defines the pages and API endpoints,
# and connects to the Gemini API to search for recipes and format the results.

import os
import json
import time
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Import the Google GenAI SDK and its internal types
from google import genai
from google.genai import types

# Import Pydantic tools. We use these to tell Gemini exactly what structure
# we want our JSON response to be in.
from pydantic import BaseModel, Field
from typing import List

# Load environment variables from the .env file if it exists
load_dotenv()

# Initialize the Flask web application
app = Flask(__name__)

# Gemini's Google Search grounding call is genuinely slow (often 30-90s since it
# does live web searches per request). We cache results per unique ingredient set
# for a while so repeated/demo searches come back instantly instead of re-querying.
RECIPE_CACHE = {}
CACHE_TTL_SECONDS = 30 * 60


def get_cache_key(ingredients):
    return tuple(sorted(i.lower() for i in ingredients))


def get_cached_response(ingredients):
    entry = RECIPE_CACHE.get(get_cache_key(ingredients))
    if not entry:
        return None
    cached_at, payload = entry
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        return None
    return payload


def set_cached_response(ingredients, payload):
    RECIPE_CACHE[get_cache_key(ingredients)] = (time.time(), payload)

# ==========================================
# DEFINING THE DATA STRUCTURES (Pydantic Models)
# ==========================================
# We define these models to tell the Gemini API the exact format of the JSON we need.
# This ensures the backend always returns consistent data that the frontend JavaScript can easily display.

class IngredientStatus(BaseModel):
    # This represents a single ingredient in a recipe.
    name: str = Field(description="Name of the ingredient with quantities (e.g., '2 chicken breasts', '1 tbsp soy sauce')")
    owned: bool = Field(description="True if the user already has this ingredient in their input list, False if it is a missing/shopping list item")

class Recipe(BaseModel):
    # This represents a single recipe.
    name: str = Field(description="The name of the recipe")
    url: str = Field(description="The source URL where this recipe was found via Google Search")
    calories: int = Field(description="Estimated calories per serving for this recipe")
    ingredients: List[IngredientStatus] = Field(description="List of all ingredients required, classified as owned or missing")
    instructions: List[str] = Field(description="Step-by-step cooking instructions")
    match_score: int = Field(description="0-100 score for how well this recipe matches the user's available ingredients")
    match_reason: str = Field(description="One short sentence explaining the match score")

class RecipeResponse(BaseModel):
    # The final container for all recipes returned.
    recipes: List[Recipe] = Field(description="A list containing 2 to 3 real recipes found on the web")


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def score_recipe_match(recipe):
    """
    Evaluation layer: recomputes each recipe's match score deterministically
    from the owned/missing ingredient breakdown, instead of trusting the
    model's self-reported number. This keeps the score consistent and
    auditable regardless of what the LLM guessed.
    """
    ingredients = recipe.get('ingredients') or []
    if not ingredients:
        return 0
    owned_count = sum(1 for ing in ingredients if ing.get('owned'))
    return round((owned_count / len(ingredients)) * 100)


def get_gemini_client():
    """
    Retrieves the Gemini API key from the environment and initializes the client.
    Throws a helpful error if the API key is not configured.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please create a file named '.env' "
            "in the project folder and add your key like: GEMINI_API_KEY=your_key_here"
        )
    return genai.Client(api_key=api_key)


# ==========================================
# ROUTES AND ENDPOINTS
# ==========================================

@app.route('/')
def index():
    """
    Serves the main frontend page. 
    Flask looks for index.html inside the 'templates' folder automatically.
    """
    return render_template('index.html')


@app.route('/api/find-recipes', methods=['POST'])
def find_recipes():
    """
    API endpoint that accepts a list of ingredients, searches the web using Gemini 
    and Google Search grounding, formats the recipes, and returns JSON.
    """
    try:
        # 1. Initialize the Gemini Client
        client = get_gemini_client()
    except ValueError as e:
        # Return error if API Key is not set
        return jsonify({'error': str(e)}), 400

    # 2. Get ingredients from the frontend request
    data = request.get_json() or {}
    user_ingredients = data.get('ingredients', [])

    if not user_ingredients or not isinstance(user_ingredients, list):
        return jsonify({'error': 'Please provide a list of ingredients (e.g., chicken, broccoli).'}), 400

    # Reject absurdly large requests before they ever reach the model
    # (keeps prompts small and prevents accidental runaway API costs).
    MAX_INGREDIENTS = 25
    MAX_INGREDIENT_LENGTH = 60

    cleaned_ingredients = []
    for item in user_ingredients:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if item and len(item) <= MAX_INGREDIENT_LENGTH:
            cleaned_ingredients.append(item)

    if not cleaned_ingredients:
        return jsonify({'error': 'Please provide at least one valid ingredient (max 60 characters each).'}), 400

    if len(cleaned_ingredients) > MAX_INGREDIENTS:
        return jsonify({'error': f'Please provide at most {MAX_INGREDIENTS} ingredients at a time.'}), 400

    user_ingredients = cleaned_ingredients

    # Serve from cache if we've already searched this exact ingredient set recently
    cached = get_cached_response(user_ingredients)
    if cached is not None:
        return jsonify(cached)

    # Format the ingredients into a comma-separated string for our prompt
    ingredients_str = ", ".join(user_ingredients)

    # 3. Build a detailed prompt instructing Gemini what to do.
    # We specify the JSON structure directly in the prompt since Gemini cannot combine
    # Google Search grounding tool with the response_mime_type="application/json" setting.
    prompt = (
        f"Find 2-3 real, high-quality recipes from the web that primarily use these ingredients: {ingredients_str}.\n\n"
        "Guidelines:\n"
        "1. You MUST perform a Google Search to search for actual, published recipes from food blogs or websites.\n"
        "2. For each recipe, provide the actual source URL found via search grounding.\n"
        "3. Provide step-by-step cooking instructions.\n"
        "4. Estimate the calories per serving (as a rough estimate).\n"
        "5. Categorize each ingredient in the recipe: set 'owned' to true if the user's input list contains it, or false if it is a missing ingredient that they need to buy.\n\n"
        "You MUST respond ONLY with a valid JSON object matching the following structure (do not include any other text or markdown code blocks):\n"
        "{\n"
        "  \"recipes\": [\n"
        "    {\n"
        "      \"name\": \"Recipe Name\",\n"
        "      \"url\": \"https://example.com/recipe-source\",\n"
        "      \"calories\": 350,\n"
        "      \"ingredients\": [\n"
        "        {\"name\": \"ingredient name with quantity\", \"owned\": true},\n"
        "        {\"name\": \"missing ingredient with quantity\", \"owned\": false}\n"
        "      ],\n"
        "      \"instructions\": [\n"
        "        \"Step 1 explanation\",\n"
        "        \"Step 2 explanation\"\n"
        "      ],\n"
        "      \"match_score\": 80,\n"
        "      \"match_reason\": \"One short sentence on why this recipe fits the user's ingredients\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    try:
        # 4. Call the Gemini API
        # We use 'gemini-2.5-flash' because it's fast, cheap, and supports Google Search.
        # We omitted response_mime_type and response_schema here because the API does not
        # support combining Google Search grounding tools with structured outputs yet.
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                # Enable Google Search grounding (web search tool)
                tools=[types.Tool(google_search=types.GoogleSearch())],
                # Low temperature for focused, factual recipe generation based on the search
                temperature=0.2
            )
        )

        # 5. Parse the JSON text returned by Gemini.
        # Since the model might wrap the JSON response in markdown code blocks,
        # we will clean the response text before loading it.
        response_text = response.text.strip()
        
        # Strip markdown markers if the model included them
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        response_text = response_text.strip()
        
        recipe_json = json.loads(response_text)

        # Evaluation layer: override the model's self-reported match_score with a
        # deterministic one, then rank recipes best-match-first.
        recipes = recipe_json.get('recipes', [])
        for recipe in recipes:
            recipe['match_score'] = score_recipe_match(recipe)
        recipes.sort(key=lambda r: r.get('match_score', 0), reverse=True)
        recipe_json['recipes'] = recipes

        set_cached_response(user_ingredients, recipe_json)
        return jsonify(recipe_json)

    except Exception as e:
        # Print the error details to the server console and report to user
        print(f"Gemini API Error: {str(e)}")
        return jsonify({'error': f"An error occurred while finding recipes: {str(e)}"}), 500


# Run the Flask development server if this file is run directly
if __name__ == '__main__':
    # Cloud Run requires the app to listen on the port defined by the PORT environment variable.
    # We default to 5000 for local development if the variable is not set.
    port = int(os.environ.get("PORT", 5000))
    # Debug mode (interactive debugger/reloader) is opt-in only, since it's a remote
    # code execution risk if ever left on in a deployed environment.
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    # We bind to '0.0.0.0' so the server is reachable from outside the container
    app.run(debug=debug, host='0.0.0.0', port=port)
