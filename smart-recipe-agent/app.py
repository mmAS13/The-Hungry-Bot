# app.py
# This is the main backend file for The Hungry Bot 🍳 web application.
# It sets up a Flask web server, defines the pages and API endpoints,
# and connects to the Gemini API to search for recipes and format the results.

import os
import json
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

class RecipeResponse(BaseModel):
    # The final container for all recipes returned.
    recipes: List[Recipe] = Field(description="A list containing 2 to 3 real recipes found on the web")


# ==========================================
# HELPER FUNCTIONS
# ==========================================

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
        "      ]\n"
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
    # We bind to '0.0.0.0' so the server is reachable from outside the container
    app.run(debug=True, host='0.0.0.0', port=port)
