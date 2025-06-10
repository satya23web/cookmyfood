import streamlit as st
import requests
import json

# --- Configuration ---
API_KEY = st.secrets["SPOONACULAR_API_KEY"]
BASE_URL = "https://api.spoonacular.com/"
RESULTS_PER_PAGE = 10 # Define how many recipes to fetch per "Load More" click

# --- Spoonacular API Functions ---

def search_recipes(query, number=RESULTS_PER_PAGE, offset=0):
    """Searches for recipes by name with pagination."""
    endpoint = "recipes/complexSearch"
    params = {
        "query": query,
        "number": number,
        "offset": offset, # Add offset for pagination
        "apiKey": API_KEY
    }
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error searching for recipes: {e}")
        return []

def get_recipe_details(recipe_id):
    """Fetches detailed information for a specific recipe."""
    endpoint = f"recipes/{recipe_id}/information"
    params = {
        "includeNutrition": True, # Get nutrition data for calories
        "apiKey": API_KEY
    }
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching recipe details: {e}")
        return None

def get_similar_recipes(recipe_id, number=5):
    """Fetches similar recipes for a given recipe ID."""
    endpoint = f"recipes/{recipe_id}/similar"
    params = {
        "number": number, # Number of similar recipes to return
        "apiKey": API_KEY
    }
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching similar recipes: {e}")
        return []

# --- Streamlit UI Layout ---

st.set_page_config(page_title="Python Recipe Finder", layout="centered")

st.title("🍜 Python Recipe Finder")

# --- Session State Initialization ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = "search_input"
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'selected_recipe_id' not in st.session_state:
    st.session_state.selected_recipe_id = None
if 'list_type' not in st.session_state:
    st.session_state.list_type = "search" # Can be "search" or "similar"
if 'last_viewed_recipe_id' not in st.session_state:
    st.session_state.last_viewed_recipe_id = None
if 'current_offset' not in st.session_state: # For pagination in main search
    st.session_state.current_offset = 0
if 'all_search_results' not in st.session_state: # To store all loaded recipes for current search
    st.session_state.all_search_results = []


# --- Navigation and Display Logic ---

# Handle user input and initial search
if st.session_state.current_page == "search_input":
    recipe_name_input = st.text_input(
        "Enter a recipe name (e.g., pasta, chicken soup)",
        value=st.session_state.search_query,
        key="recipe_name_input"
    )

    if st.button("Search Recipes"):
        if recipe_name_input:
            st.session_state.search_query = recipe_name_input
            st.session_state.list_type = "search"
            st.session_state.current_offset = 0 # Reset offset for new search
            st.session_state.all_search_results = [] # Clear previous results
            st.session_state.current_page = "search_results"
            st.rerun()
        else:
            st.warning("Please enter a recipe name to search.")
    st.info("Enter a recipe name above and click 'Search Recipes' to find recipes.")

# Display search results (either original search or similar recipes)
elif st.session_state.current_page == "search_results":
    if st.session_state.list_type == "search":
        st.subheader(f"Search Results for '{st.session_state.search_query}'")
        # Fetch initial or next batch of results
        if not st.session_state.all_search_results or st.session_state.current_offset > len(st.session_state.all_search_results):
            # Fetch only if no results yet or if offset exceeds current stored results (e.g. from a rerun)
            new_recipes = search_recipes(st.session_state.search_query, offset=st.session_state.current_offset)
            # Append new results to the overall list if they are not already there
            # This logic prevents duplicates if reruns happen without button clicks
            if new_recipes and not any(r['id'] == nr['id'] for r in st.session_state.all_search_results for nr in new_recipes):
                 st.session_state.all_search_results.extend(new_recipes)
            elif not new_recipes and st.session_state.current_offset > 0:
                 st.info("No more recipes found for this search.")

        recipes_to_display = st.session_state.all_search_results

    elif st.session_state.list_type == "similar":
        original_recipe_details = get_recipe_details(st.session_state.last_viewed_recipe_id)
        original_title = original_recipe_details.get('title', 'a recipe') if original_recipe_details else 'a recipe'
        st.subheader(f"Similar Recipes to '{original_title}'")
        recipes_to_display = get_similar_recipes(st.session_state.last_viewed_recipe_id)
        # Similar recipes don't have pagination, so we don't store them in all_search_results
        # and no load/previous buttons for them.

    if recipes_to_display:
        for recipe in recipes_to_display:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{recipe['title']}**")
                if 'readyInMinutes' in recipe:
                    st.write(f"*{recipe['readyInMinutes']} minutes*")
            with col2:
                if st.button("View Details", key=f"view_{recipe['id']}_{st.session_state.list_type}"):
                    st.session_state.selected_recipe_id = recipe['id']
                    st.session_state.current_page = "recipe_details"
                    st.rerun()
        st.markdown("---")

        # Pagination and Navigation Buttons
        col_back, col_middle, col_load_more = st.columns(3)

        with col_back:
            if st.session_state.list_type == "search":
                if st.button("Start New Search", key="start_new_search_from_results"):
                    st.session_state.current_page = "search_input"
                    st.session_state.search_query = ""
                    st.session_state.current_offset = 0
                    st.session_state.all_search_results = []
                    st.session_state.last_viewed_recipe_id = None
                    st.rerun()
            elif st.session_state.list_type == "similar":
                if st.button("Back to Recipe Details", key="back_to_details_from_similar"):
                    st.session_state.current_page = "recipe_details"
                    st.session_state.list_type = "search" # Reset list type
                    st.rerun()
        
        # "Previous" and "Load More" only for initial search results
        if st.session_state.list_type == "search":
            with col_middle:
                if st.session_state.current_offset > 0:
                    if st.button("Previous Recipes", key="previous_recipes"):
                        st.session_state.current_offset = max(0, st.session_state.current_offset - RESULTS_PER_PAGE)
                        # Remove the last batch of results if we go back
                        if len(st.session_state.all_search_results) > st.session_state.current_offset + RESULTS_PER_PAGE:
                           st.session_state.all_search_results = st.session_state.all_search_results[:st.session_state.current_offset + RESULTS_PER_PAGE]
                        st.rerun()
            with col_load_more:
                # Only show load more if there are enough results to suggest more
                if len(recipes_to_display) >= RESULTS_PER_PAGE + st.session_state.current_offset: # This might be inaccurate, better to check totalResults from API response if possible
                    if st.button("Load More Recipes", key="load_more_recipes"):
                        st.session_state.current_offset += RESULTS_PER_PAGE
                        st.rerun()
        
    else: # No recipes found in current display (either search or similar)
        st.info(f"No {st.session_state.list_type} recipes found for your query/selection. Try a different one.")
        if st.session_state.list_type == "search":
            if st.button("Start New Search", key="start_new_search_no_results"):
                st.session_state.current_page = "search_input"
                st.session_state.search_query = ""
                st.session_state.current_offset = 0
                st.session_state.all_search_results = []
                st.session_state.last_viewed_recipe_id = None
                st.rerun()
        elif st.session_state.list_type == "similar":
            if st.button("Back to Recipe Details", key="back_to_details_no_similar"):
                st.session_state.current_page = "recipe_details"
                st.session_state.list_type = "search"
                st.rerun()

# Display detailed recipe information
elif st.session_state.current_page == "recipe_details":
    if st.session_state.selected_recipe_id:
        st.subheader("Recipe Details")
        details = get_recipe_details(st.session_state.selected_recipe_id)

        if details:
            st.markdown(f"## {details.get('title', 'N/A')}")
            st.session_state.last_viewed_recipe_id = st.session_state.selected_recipe_id

            st.write(f"**Preparation Time:** {details.get('readyInMinutes', 'N/A')} minutes")
            st.write(f"**Servings:** {details.get('servings', 'N/A')}")

            calories = "N/A"
            if details.get('nutrition') and details['nutrition'].get('nutrients'):
                for nutrient in details['nutrition']['nutrients']:
                    if nutrient.get('title') == 'Calories':
                        calories = f"{nutrient.get('amount', 'N/A')} {nutrient.get('unit', '')}"
                        break
            st.write(f"**Calories:** {calories}")

            if details.get('sourceUrl'):
                st.markdown(f"**Source:** [Link to Recipe]({details['sourceUrl']})")

            st.markdown("### Ingredients:")
            if details.get('extendedIngredients'):
                ingredients_list = "\n".join([f"- {ing['original']}" for ing in details['extendedIngredients']])
                st.markdown(ingredients_list)
            else:
                st.info("No detailed ingredients available.")

            st.markdown("### Instructions:")
            if details.get('analyzedInstructions'):
                for instruction_set in details['analyzedInstructions']:
                    steps_md = ""
                    for step in instruction_set.get('steps', []):
                        steps_md += f"{step.get('number')}. {step.get('step')}\n"
                    st.markdown(steps_md)
            elif details.get('instructions'):
                st.markdown(details['instructions'], unsafe_allow_html=True)
            else:
                st.info("No detailed instructions available.")

            st.markdown("---")
            col_back, col_similar = st.columns(2)
            with col_back:
                if st.button("Back to Search Results", key="back_from_details"):
                    st.session_state.current_page = "search_results"
                    st.session_state.selected_recipe_id = None
                    # No change to list_type or offset here, it will default to previous search context
                    st.rerun()
            with col_similar:
                if st.button("Find Similar Recipes", key="find_similar_from_details"):
                    st.session_state.current_page = "search_results"
                    st.session_state.list_type = "similar"
                    st.rerun()
        else:
            st.warning("Could not load recipe details.")
            st.session_state.current_page = "search_results"
            st.rerun()
    else:
        st.session_state.current_page = "search_results"
        st.rerun()
