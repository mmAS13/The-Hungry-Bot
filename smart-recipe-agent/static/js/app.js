// app.js
// This file handles the interactive frontend behavior for our Smart Recipe Agent.
// It manages the list of ingredients, sends requests to the Flask server,
// and dynamically creates recipe cards on the webpage.

// State management
let ingredientsList = [];

// DOM Elements
const ingredientInput = document.getElementById('ingredient-input');
const addBtn = document.getElementById('add-btn');
const tagsContainer = document.getElementById('tags-container');
const findRecipesBtn = document.getElementById('find-recipes-btn');
const clearAllBtn = document.getElementById('clear-all-btn');
const recipeLoader = document.getElementById('recipe-loader');
const errorBanner = document.getElementById('error-banner');
const errorMessage = document.getElementById('error-message');
const closeErrorBtn = document.getElementById('close-error-btn');
const resultsSection = document.getElementById('results-section');
const recipesGrid = document.getElementById('recipes-grid');
const loaderMessage = document.getElementById('loader-message');

const DEFAULT_LOADER_MESSAGE = loaderMessage.textContent;
const SLOW_LOADER_MESSAGE = "Still searching... the AI is reading multiple recipe sites to find the best matches.";
let loaderMessageTimeout = null;

// ==========================================
// INGREDIENTS LIST MANAGEMENT
// ==========================================

// Add ingredient on clicking the "Add" button
addBtn.addEventListener('click', addIngredientFromInput);

// Add ingredient on pressing "Enter" key in the input field
ingredientInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault(); // Prevent default form submission behavior
        addIngredientFromInput();
    }
});

// Close error banner on close button click
closeErrorBtn.addEventListener('click', hideError);

// Clear all ingredients
clearAllBtn.addEventListener('click', () => {
    ingredientsList = [];
    renderTags();
    updateActionButtons();
    hideResults();
});

// Find recipes on button click
findRecipesBtn.addEventListener('click', fetchRecipes);

/**
 * Reads the text value from the input field, sanitizes it,
 * adds it to our state list, and updates the tags display.
 */
function addIngredientFromInput() {
    const value = ingredientInput.value.trim().toLowerCase();
    
    if (value === "") return;
    
    // Check if ingredient already exists in our list
    if (ingredientsList.includes(value)) {
        showError(`"${value}" is already in your list!`);
        ingredientInput.value = "";
        return;
    }
    
    // Add to list and reset input field
    ingredientsList.push(value);
    ingredientInput.value = "";
    
    // Clear any active errors and render updated tags
    hideError();
    renderTags();
    updateActionButtons();
}

/**
 * Removes an ingredient from the list and refreshes the tag elements.
 */
function removeIngredient(ingredient) {
    ingredientsList = ingredientsList.filter(item => item !== ingredient);
    renderTags();
    updateActionButtons();
    
    // If no ingredients are left, hide any old results
    if (ingredientsList.length === 0) {
        hideResults();
    }
}

/**
 * Creates HTML tags for each ingredient in the list and mounts them to the DOM.
 */
function renderTags() {
    tagsContainer.innerHTML = '';
    
    ingredientsList.forEach(ingredient => {
        // Create tag container
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.textContent = ingredient;
        
        // Create remove button ("x")
        const removeBtn = document.createElement('span');
        removeBtn.className = 'tag-remove';
        removeBtn.innerHTML = '&times;';
        removeBtn.title = `Remove ${ingredient}`;
        removeBtn.addEventListener('click', () => removeIngredient(ingredient));
        
        // Assemble and append
        tag.appendChild(removeBtn);
        tagsContainer.appendChild(tag);
    });
}

/**
 * Enables or disables submission buttons depending on ingredient state.
 */
function updateActionButtons() {
    if (ingredientsList.length > 0) {
        findRecipesBtn.disabled = false;
        clearAllBtn.style.display = 'inline-flex';
    } else {
        findRecipesBtn.disabled = true;
        clearAllBtn.style.display = 'none';
    }
}

// ==========================================
// ERROR AND RESULTS UI TOGGLES
// ==========================================

function showError(msg) {
    errorMessage.textContent = msg;
    errorBanner.style.display = 'flex';
    // Scroll to the error so the user sees it
    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
    errorBanner.style.display = 'none';
}

function hideResults() {
    resultsSection.style.display = 'none';
    recipesGrid.innerHTML = '';
}

// ==========================================
// API COMMUNICATION AND RECIPE RENDERING
// ==========================================

/**
 * Performs a network POST request to our Flask backend to fetch recipes.
 * Handles loading screens and error handling.
 */
async function fetchRecipes() {
    if (ingredientsList.length === 0) return;
    
    // Setup UI states for active search
    hideError();
    hideResults();
    recipeLoader.style.display = 'flex';
    findRecipesBtn.disabled = true;
    clearAllBtn.disabled = true;
    loaderMessage.textContent = DEFAULT_LOADER_MESSAGE;

    // Swap to a "still working" message after 20s so a long wait doesn't feel stuck
    loaderMessageTimeout = setTimeout(() => {
        loaderMessage.textContent = SLOW_LOADER_MESSAGE;
    }, 20000);

    // Scroll to the loader to focus user attention
    recipeLoader.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    try {
        const response = await fetch('/api/find-recipes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ingredients: ingredientsList })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // Server returned an error code (400 or 500)
            throw new Error(data.error || 'Failed to fetch recipes. Please try again.');
        }
        
        if (!data.recipes || data.recipes.length === 0) {
            throw new Error('No recipes found. Try adding more general ingredients (like chicken, onions, or rice).');
        }
        
        // Render recipes list on success
        renderRecipes(data.recipes);
        
    } catch (err) {
        showError(err.message);
    } finally {
        // Restore buttons and hide loading screen
        clearTimeout(loaderMessageTimeout);
        recipeLoader.style.display = 'none';
        findRecipesBtn.disabled = false;
        clearAllBtn.disabled = false;
    }
}

/**
 * Builds HTML elements representing the returned recipes list and updates the DOM.
 */
function renderRecipes(recipes) {
    recipesGrid.innerHTML = '';
    
    recipes.forEach((recipe, index) => {
        // Create recipe card main container
        const card = document.createElement('article');
        card.className = 'recipe-card';
        card.style.animationDelay = `${index * 0.15}s`; // Stagger animation for nice flow
        
        // Separate Owned ingredients and Missing ingredients
        const ownedIngredients = recipe.ingredients.filter(ing => ing.owned);
        const missingIngredients = recipe.ingredients.filter(ing => !ing.owned);
        
        // Build card inner HTML structure
        if (index === 0) {
            card.classList.add('best-match');
        }

        let cardHTML = `
            <div class="recipe-card-header">
                <div class="recipe-title-wrapper">
                    <h3>${escapeHtml(recipe.name)}</h3>
                    <div class="recipe-meta">
                        <span class="meta-badge badge-calories">🔥 ${recipe.calories} kcal / serving</span>
                        <a href="${recipe.url}" target="_blank" rel="noopener noreferrer" class="meta-badge badge-source">🌐 View Recipe Source</a>
                    </div>
                </div>
                <div class="match-score-wrapper" title="${escapeHtml(recipe.match_reason || '')}">
                    <div class="match-score-ring ${matchBadgeClass(recipe.match_score)}">
                        <span class="match-score-value">${recipe.match_score}%</span>
                    </div>
                    <span class="match-score-label">Match</span>
                </div>
            </div>
            ${recipe.match_reason ? `<p class="match-reason">${escapeHtml(recipe.match_reason)}</p>` : ''}

            <div class="ingredients-columns">
                <!-- Columns for ingredients user HAS -->
                <div class="ingredients-col kitchen-col">
                    <div class="col-header">
                        <h4><span class="icon-circle icon-have">✓</span> In Your Kitchen</h4>
                        <span class="count-badge">${ownedIngredients.length}</span>
                    </div>
                    <ul class="ingredient-list">
                        ${ownedIngredients.map(ing => `
                            <li class="ingredient-item">
                                <span class="item-check">✓</span>
                                <span>${escapeHtml(ing.name)}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>

                <!-- Columns for ingredients user NEEDS (Shopping List) -->
                <div class="ingredients-col shopping-col">
                    <div class="col-header">
                        <h4><span class="icon-circle icon-need">+</span> Shopping List</h4>
                        ${missingIngredients.length > 0 ? `<button class="btn-copy" onclick="copyShoppingList(this, ${index})">Copy List</button>` : ''}
                    </div>
                    <ul class="ingredient-list" id="shopping-list-${index}">
                        ${missingIngredients.length > 0 ?
                            missingIngredients.map(ing => `
                                <li class="ingredient-item">
                                    <span class="item-cross">＋</span>
                                    <span>${escapeHtml(ing.name)}</span>
                                </li>
                            `).join('') :
                            `<li class="ingredient-item text-muted"><em>You have everything! 🎉</em></li>`
                        }
                    </ul>
                </div>
            </div>

            <div class="instructions-wrapper">
                <h4>Instructions <span class="instructions-hint">(click a step to check it off)</span></h4>
                <ol class="instructions-list">
                    ${recipe.instructions.map(step => `
                        <li class="instruction-step" onclick="toggleStep(this)">
                            ${escapeHtml(step)}
                        </li>
                    `).join('')}
                </ol>
            </div>
        `;
        
        card.innerHTML = cardHTML;
        recipesGrid.appendChild(card);
    });
    
    // Show results section
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Toggles line-through text decoration when instruction step is clicked.
 */
window.toggleStep = function(element) {
    element.classList.toggle('completed');
};

/**
 * Extracts and copies missing ingredients list to clipboard for user convenience.
 */
window.copyShoppingList = function(button, recipeIndex) {
    const listItems = document.querySelectorAll(`#shopping-list-${recipeIndex} .ingredient-item span:last-child`);
    if (listItems.length === 0) return;
    
    // Compile ingredients into a newline-separated string
    const itemsText = Array.from(listItems).map(item => `- ${item.textContent}`).join('\n');
    
    navigator.clipboard.writeText(itemsText).then(() => {
        // Provide copy success UX feedback
        const originalText = button.textContent;
        button.textContent = "Copied! ✓";
        button.style.backgroundColor = "var(--primary-bg)";
        button.style.color = "var(--primary)";
        button.style.borderColor = "hsl(150, 40%, 85%)";
        
        // Revert copy button back to original state after 2 seconds
        setTimeout(() => {
            button.textContent = originalText;
            button.style.backgroundColor = "";
            button.style.color = "";
            button.style.borderColor = "";
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
};

/**
 * Picks a badge color tier for the match score: high/medium/low.
 */
function matchBadgeClass(score) {
    if (score >= 75) return 'score-high';
    if (score >= 40) return 'score-medium';
    return 'score-low';
}

/**
 * Helper utility to prevent HTML injection by escaping characters.
 */
function escapeHtml(string) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(string).replace(/[&<>"']/g, function(m) { return map[m]; });
}
