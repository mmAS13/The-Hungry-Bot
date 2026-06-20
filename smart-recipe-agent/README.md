# The Hungry Bot 🍳

Welcome to **The Hungry Bot 🍳**! This is a simple, modern, and beautiful web application that lets you input ingredients you currently have in your kitchen, searches the web for real recipes using Google Search grounding, lists what ingredients you are missing, and calculates estimated calories per serving.

This project is designed to be highly readable and beginner-friendly, with complete annotations explaining how each file fits together.

---

## 📂 Codebase File Explanations

Here is a map of the files created in your workspace:

### 1. Backend (`app.py`)
- **What it does**: This is the Python script that runs your web server (using Flask). It hosts the homepage and handles API requests.
- **Key details**: 
  - It handles a `/api/find-recipes` endpoint which receives your ingredients.
  - It initializes the `google-genai` client using your `GEMINI_API_KEY`.
  - It sets up a Pydantic schema (`RecipeResponse`) to enforce that the AI responds in a strict JSON format so our frontend can reliably parse the results.
  - It activates Gemini's **Google Search Grounding** tool to search the web for 2-3 real recipes and include their actual source URLs.

### 2. Dependencies (`requirements.txt`)
- **What it does**: Lists all external Python libraries required by this project.
  - `Flask`: The micro web framework that runs the server.
  - `google-genai`: The official modern SDK for Gemini API calls.
  - `python-dotenv`: A utility that reads environment variables from a `.env` file, keeping your API key safe.

### 3. Frontend Layout (`templates/index.html`)
- **What it does**: Defines the user interface. It provides an input box for ingredients, tags to display added ingredients, a beautiful animated loading spinner representing a frying pan, and a placeholder area where the recipe cards will load.

### 4. Stylesheet (`static/css/style.css`)
- **What it does**: Adds beautiful, responsive styles to the HTML content. 
- **Design highlights**:
  - Employs a custom appetizing color palette centered on fresh HSL Emerald Green and warm Amber.
  - Implements soft shadows and thin glassmorphic container boundaries.
  - Includes custom keyframe animations like a rocking pan with bubbling food for the loading screen.
  - Formats "Owned" ingredients (green) and "Missing" ingredients (red/orange) into separate columns for quick readability.

### 5. Interactive Script (`static/js/app.js`)
- **What it does**: Drives the interactive behaviors.
  - Turns comma-separated typed ingredients into interactive tag elements.
  - Sends a network `fetch` request containing the ingredients list to the Flask API.
  - Toggle-checks cooking instructions on click (line-through decoration).
  - Copies the missing ingredients shopping list to the user's clipboard at the press of a button.

---

## 🚀 Step-by-Step Setup Guide

Follow these steps to run the application on your computer:

### Step 1: Set up your Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/) and click **Get API Key** to generate a key.
2. In the `smart-recipe-agent` project directory, make a copy of `.env.template` and name it `.env`:
   - *On Windows Powershell:* `Copy-Item .env.template .env`
3. Open the `.env` file and replace `your_gemini_api_key_here` with your actual API key:
   ```env
   GEMINI_API_KEY=AIzaSy...yourkey...
   ```

### Step 2: Open Terminal / VS Code
Open your terminal inside the project directory (`C:\Users\mariu\.gemini\antigravity\scratch\smart-recipe-agent`).

### Step 3: Activate the Virtual Environment
We have already created a virtual environment named `.venv` for you. Activate it:
- **Windows PowerShell**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows Command Prompt (cmd)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```

Once activated, your terminal prompt will be prefixed with `(.venv)`.

### Step 4: Start the Flask Server
Run the Flask app:
```bash
python app.py
```

You should see output indicating the server is running, like this:
```text
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### Step 5: Test the Application!
1. Open your web browser and navigate to `http://127.0.0.1:5000`.
2. Type in ingredients like `chicken, garlic, broccoli, soy sauce` and press Enter after each.
3. Click **Find Recipes**!
4. Watch the cooking pan animation, and review the recipes, shopping list, and instructions that load in real-time.
