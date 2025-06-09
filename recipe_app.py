import streamlit as st
import requests
import json
st.set_page_config(page_title="Recipe Finder", layout="centered")

st.title("🍜 Recipe Finder")

st.set_page_config(
    page_title="Cook With Me – AI Recipe Finder",
    page_icon="🍲",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Configuration ---
# Get API key from Streamlit secrets
API_KEY = st.secrets["SPOONACULAR_API_KEY"] # This is the correct way to access it
BASE_URL = "https://api.spoonacular.com/"

# --- Spoonacular API Functions ---

def search_recipes(query, number=10):
    """Searches for recipes by name."""
    endpoint = "recipes/complexSearch"
    params = {
        "query": query,
        "number": number,
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

# --- Streamlit UI Layout ---



# Input for recipe name
recipe_name_input = st.text_input(
    "Enter a recipe name (e.g., pasta, chicken soup)",
    key="recipe_name_input"
)

# Search button
if st.button("Search Recipes"):
    if recipe_name_input:
        st.session_state.search_query = recipe_name_input # Store query in session state
        st.session_state.current_page = "search_results" # Navigate to search results
        st.rerun() # Rerun the app to show results
    else:
        st.warning("Please enter a recipe name to search.")

# --- Navigation and Display Logic ---

# Initialize session state for navigation if not already set
if 'current_page' not in st.session_state:
    st.session_state.current_page = "search_input" # Default page
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'selected_recipe_id' not in st.session_state:
    st.session_state.selected_recipe_id = None


# Display logic based on current_page in session state
if st.session_state.current_page == "search_results":
    if st.session_state.search_query:
        st.subheader(f"Search Results for '{st.session_state.search_query}'")
        recipes = search_recipes(st.session_state.search_query)

        if recipes:
            for recipe in recipes:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{recipe['title']}**")
                with col2:
                    # Store selected recipe ID in session state and change page
                    if st.button("View Details", key=f"view_{recipe['id']}"):
                        st.session_state.selected_recipe_id = recipe['id']
                        st.session_state.current_page = "recipe_details"
                        st.rerun() # Rerun to show details
            st.markdown("---") # Separator
            if st.button("Back to Search Input", key="back_to_input_from_results"):
                st.session_state.current_page = "search_input"
                st.session_state.search_query = ""
                st.rerun()
        else:
            st.info("No recipes found for your search. Try a different name.")
            if st.button("Back to Search Input", key="back_to_input_no_results"):
                st.session_state.current_page = "search_input"
                st.session_state.search_query = ""
                st.rerun()
    else: # If search_query is empty, go back to input state
        st.session_state.current_page = "search_input"
        st.rerun()

elif st.session_state.current_page == "recipe_details":
    if st.session_state.selected_recipe_id:
        st.subheader("Recipe Details")
        details = get_recipe_details(st.session_state.selected_recipe_id)

        if details:
            st.markdown(f"## {details.get('title', 'N/A')}")
            st.write(f"**Preparation Time:** {details.get('readyInMinutes', 'N/A')} minutes")
            st.write(f"**Servings:** {details.get('servings', 'N/A')}")

            # Extract Calories
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
                # Handle structured steps
                for instruction_set in details['analyzedInstructions']:
                    steps_md = ""
                    for step in instruction_set.get('steps', []):
                        steps_md += f"{step.get('number')}. {step.get('step')}\n"
                    st.markdown(steps_md)
            elif details.get('instructions'):
                # Handle single string instructions (might be HTML)
                st.markdown(details['instructions'], unsafe_allow_html=True) # Use unsafe_allow_html if instructions can contain HTML
            else:
                st.info("No detailed instructions available.")
        else:
            st.warning("Could not load recipe details.")

        # Back button
        if st.button("Back to Search Results", key="back_to_results_from_details"):
            st.session_state.current_page = "search_results"
            st.session_state.selected_recipe_id = None # Clear selected ID
            st.rerun()
    else: # If no recipe ID selected, go back to search results
        st.session_state.current_page = "search_results"
        st.rerun()

# Default state if nothing is triggered yet
elif st.session_state.current_page == "search_input":
    st.info("Enter a recipe name above and click 'Search Recipes' to find recipes.")
