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

st.set_page_config(page_title="Recipe Finder", layout="centered")

st.title("🍜 Recipe Finder")

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
if 'last_api_fetch_was_full_page' not in st.session_state: # NEW: To track if last API call returned a full batch
    st.session_state.last_api_fetch_was_full_page = False 


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
            st.session_state.last_api_fetch_was_full_page = False # Reset flag for new search
            st.session_state.current_page = "search_results"
            st.rerun()
        else:
            st.warning("Please enter a recipe name to search.")
    st.info("Enter a recipe name above and click 'Search Recipes' to find recipes.")

# Display search results (either original search or similar recipes)
elif st.session_state.current_page == "search_results":
    if st.session_state.list_type == "search":
        st.subheader(f"Search Results for '{st.session_state.search_query}'")
        
        # Fetch new results if current_offset exceeds already loaded results
        # This ensures we always fetch when the offset points to unseen recipes
        if st.session_state.current_offset >= len(st.session_state.all_search_results):
            new_recipes = search_recipes(st.session_state.search_query, number=RESULTS_PER_PAGE, offset=st.session_state.current_offset)
            
            # Update the flag based on the actual fetch result
            st.session_state.last_api_fetch_was_full_page = (len(new_recipes) == RESULTS_PER_PAGE)

            if new_recipes:
                # Append only unique new recipes to avoid duplicates on reruns
                current_ids = {r['id'] for r in st.session_state.all_search_results}
                unique_new_recipes = [nr for nr in new_recipes if nr['id'] not in current_ids]
                st.session_state.all_search_results.extend(unique_new_recipes)
            elif st.session_state.current_offset > 0:
                # If no new recipes were fetched and we're not at the very beginning,
                # it means we've reached the end of the results.
                st.info("No more recipes found for this search.")

        recipes_to_display = st.session_state.all_search_results

    elif st.session_state.list_type == "similar":
        original_recipe_details = get_recipe_details(st.session_state.last_viewed_recipe_id)
        original_title = original_recipe_details.get('title', 'a recipe') if original_recipe_details else 'a recipe'
        st.subheader(f"Similar Recipes to '{original_title}'")
        recipes_to_display = get_similar_recipes(st.session_state.last_viewed_recipe_id)
        # Similar recipes don't have pagination, so no load/previous buttons for them.

    if recipes_to_display:
        # Display recipes relevant to the current offset
        start_index = st.session_state.current_offset
        end_index = start_index + RESULTS_PER_PAGE
        current_batch_to_show = recipes_to_display[start_index:end_index]

        # Handle case where going previous leaves an empty current_batch_to_show
        if not current_batch_to_show and start_index > 0:
            st.info("You've reached the end of the recipes for this search.")
            st.session_state.current_offset = max(0, len(recipes_to_display) - RESULTS_PER_PAGE)
            current_batch_to_show = recipes_to_display[st.session_state.current_offset:st.session_state.current_offset + RESULTS_PER_PAGE]


        for recipe in current_batch_to_show:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{recipe['title']}**")
                if 'readyInMinutes' in recipe:
                    st.write(f"*{recipe['readyInMinutes']} minutes*") # Corrected the typo here
            with col2:
                if st.button("View Details", key=f"view_{recipe['id']}_{st.session_state.list_type}_{st.session_state.current_offset}"):
                    st.session_state.selected_recipe_id = recipe['id']
                    st.session_state.current_page = "recipe_details"
                    st.rerun()
        st.markdown("---")

        # Pagination and Navigation Buttons for main search results
        if st.session_state.list_type == "search":
            col_prev, col_main_nav, col_next = st.columns(3)

            with col_prev:
                if st.session_state.current_offset > 0:
                    if st.button("Previous Recipes", key="previous_recipes"):
                        st.session_state.current_offset = max(0, st.session_state.current_offset - RESULTS_PER_PAGE)
                        st.rerun()

            with col_main_nav:
                current_page_num = (st.session_state.current_offset // RESULTS_PER_PAGE) + 1
                st.write(f"Page {current_page_num}")

            with col_next:
                # Show "Load More" ONLY if the last API call returned a full page of results
                if st.session_state.last_api_fetch_was_full_page:
                    if st.button("Load More Recipes", key="load_more_recipes"):
                        st.session_state.current_offset += RESULTS_PER_PAGE
                        st.rerun()
            
        # Back to Search Input or Details button (always available regardless of list type)
        if st.session_state.list_type == "search":
            if st.button("Start New Search", key="start_new_search_from_results_bottom"):
                st.session_state.current_page = "search_input"
                st.session_state.search_query = ""
                st.session_state.current_offset = 0
                st.session_state.all_search_results = []
                st.session_state.last_viewed_recipe_id = None
                st.session_state.last_api_fetch_was_full_page = False # Reset flag
                st.rerun()
        elif st.session_state.list_type == "similar":
             if st.button("Back to Recipe Details", key="back_to_details_from_similar_bottom"):
                st.session_state.current_page = "recipe_details"
                st.session_state.list_type = "search"
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
                st.session_state.last_api_fetch_was_full_page = False # Reset flag
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
