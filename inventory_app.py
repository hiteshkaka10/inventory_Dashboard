import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import datetime
from google.oauth2.service_account import Credentials

# --- Configuration & Setup ---
st.set_page_config(page_title="ASHISH SARL INVENTORY", layout="wide")

# Initialize session state for multi-item moves and additions
if 'moves_list' not in st.session_state:
    st.session_state['moves_list'] = []
if 'add_list' not in st.session_state:
    st.session_state['add_list'] = []
if 'purchase_list' not in st.session_state:
    st.session_state['purchase_list'] = []
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Home"

def back_to_home():
    st.session_state['current_page'] = "Home"
    st.rerun()

# Function to get Google Sheets credentials and client
@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Authenticates with Google Sheets using Streamlit secrets."""
    try:
        # Load the credentials from Streamlit secrets
        creds_json = st.secrets["gsheets"]
        creds = Credentials.from_service_account_info(
            creds_json,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(creds)
        # Get the spreadsheet URL from secrets
        spreadsheet_url = st.secrets["sheets"]["spreadsheet_url"]
        spreadsheet = client.open_by_url(spreadsheet_url)
        
        # Get the worksheets, creating them if they don't exist
        try:
            ws = spreadsheet.worksheet("Inventory")
        except gspread.exceptions.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title="Inventory", rows="100", cols="20")
            ws.append_row(['Sr No', 'Item Name', 'Category', 'Location', 'Initial stock', 'Current Stock'])
        
        try:
            log_sheet = spreadsheet.worksheet("Logs")
        except gspread.exceptions.WorksheetNotFound:
            log_sheet = spreadsheet.add_worksheet(title="Logs", rows="100", cols="5")
            log_sheet.append_row(['Timestamp', 'Action', 'Item Name', 'Details'])

        return client, ws, log_sheet

    except Exception as e:
        st.error(f"Failed to authenticate or connect to Google Sheets. Please check your secrets.toml file. Error: {e}")
        st.stop()
        return None, None, None

# Get the client and worksheets
client, ws, log_sheet = get_gspread_client()
if client is None:
    st.stop()

# --- Logging Functionality ---
def log_action(action, item_name, details):
    """Writes a log entry to the 'Logs' worksheet."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data = [timestamp, action, item_name, details]
    try:
        log_sheet.append_row(log_data)
    except Exception as e:
        st.warning(f"Failed to write to log sheet. Error: {e}")

# --- Data Fetching and Caching ---
@st.cache_data(ttl=60) # Cache the inventory data for 60 seconds
def fetch_inventory_data():
    """Fetches inventory data from the 'Inventory' worksheet."""
    try:
        df_fetched = get_as_dataframe(ws, evaluate_formulas=True)
        if not df_fetched.empty:
            # Drop any empty rows from the DataFrame
            df_fetched.dropna(how='all', inplace=True)
            
            # Drop any columns that are unnamed (e.g., empty header cells) and strip whitespace
            df_fetched.columns = df_fetched.columns.astype(str).str.strip()
            df_fetched = df_fetched.loc[:, df_fetched.columns.str.len() > 0]
            
            # Fill empty values and explicitly convert columns to string type for filtering
            df_fetched['Item Name'] = df_fetched['Item Name'].fillna('').astype(str)
            df_fetched['Category'] = df_fetched['Category'].fillna('').astype(str)
            df_fetched['Location'] = df_fetched['Location'].fillna('').astype(str)
            
            # Convert stock and Sr No columns to numeric, filling NaNs with 0
            df_fetched['Sr No'] = pd.to_numeric(df_fetched['Sr No'], errors='coerce').fillna(0).astype(int)
            df_fetched['Initial stock'] = pd.to_numeric(df_fetched['Initial stock'], errors='coerce').fillna(0).astype(int)
            df_fetched['Current Stock'] = pd.to_numeric(df_fetched['Current Stock'], errors='coerce').fillna(0).astype(int)
        return df_fetched
    except Exception as e:
        st.error(f"Failed to fetch inventory data. Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_logs_data():
    """Fetches log data from the 'Logs' worksheet."""
    try:
        data = log_sheet.get_all_records()
        df_logs = pd.DataFrame(data)
        if not df_logs.empty:
            df_logs['Timestamp'] = pd.to_datetime(df_logs['Timestamp'], errors='coerce')
            df_logs = df_logs.dropna(subset=['Timestamp']) # Drop rows with invalid timestamps
            df_logs.sort_values(by="Timestamp", ascending=False, inplace=True)
        return df_logs
    except Exception as e:
        st.error(f"Failed to fetch logs. Error: {e}")
        return pd.DataFrame()

def clear_cache():
    """Clears the cache to fetch fresh data from Google Sheets."""
    st.cache_data.clear()
    st.rerun()

# --- Main App Logic ---
df = fetch_inventory_data()
df_logs = fetch_logs_data()

# Custom CSS for styling and smaller font
st.html("""
<style>
.stDataFrame {
    font-size: 14px;
}
.stButton>button {
    font-size: 12px;
    padding: 2px 5px;
    margin: 2px;
}
</style>
""")

# Header
if st.session_state['current_page'] != "Home":
    if st.button("⬅️ Back to Home"):
        back_to_home()

st.markdown("<h3>WELCOME TO <span style='color:red'>ASHISH SARL</span> INVENTORY</h3>", unsafe_allow_html=True)
st.button("Refresh Inventory Data", on_click=clear_cache, help="Click to reload the latest data from the Google Sheet.")

# Sidebar for navigation
menu = ["Home", "View Items", "Add Item", "Move Item", "Purchase Item", "View Logs"]
choice = st.sidebar.selectbox("Navigation", menu, index=menu.index(st.session_state['current_page']), key="sidebar_menu")

# Sync selection from sidebar to home buttons
if choice != st.session_state['current_page']:
    st.session_state['current_page'] = choice
    st.session_state['add_list'] = []  # Clear add list when switching pages
    st.session_state['moves_list'] = [] # Clear move list when switching pages
    st.session_state['purchase_list'] = [] # Clear purchase list when switching pages


# -----------------------------
# Home Page (Buttons)
# -----------------------------
if st.session_state['current_page'] == "Home":
    st.subheader("Dashboard")
    st.markdown("Use the buttons below or the sidebar to navigate.")
    
    col_buttons = st.columns(3)
    with col_buttons[0]:
        if st.button("📦 View Items"):
            st.session_state['current_page'] = "View Items"
            st.rerun()
    with col_buttons[1]:
        if st.button("➕ Add Item"):
            st.session_state['current_page'] = "Add Item"
            st.rerun()
    with col_buttons[2]:
        if st.button("🚚 Move Item"):
            st.session_state['current_page'] = "Move Item"
            st.rerun()
    
    col_buttons2 = st.columns(3)
    with col_buttons2[0]:
        if st.button("🛒 Purchase Item"):
            st.session_state['current_page'] = "Purchase Item"
            st.rerun()
    with col_buttons2[1]:
        if st.button("📋 View Logs"):
            st.session_state['current_page'] = "View Logs"
            st.rerun()
    
    st.markdown("---")

# -----------------------------
# View Items
# -----------------------------
elif st.session_state['current_page'] == "View Items":
    st.subheader("Inventory List")
    
    # Universal Search Bar
    search_term = st.text_input("Search for any keyword (Item, Category, or Location)", "")
    
    # Check if df is not empty before filtering
    if not df.empty:
        # Universal search logic
        if search_term:
            filtered_df = df[
                df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            ]
        else:
            filtered_df = df.copy()

        # Add a column for deletion at the end
        filtered_df_with_delete = filtered_df.copy()
        filtered_df_with_delete['Delete?'] = False

        # Use st.data_editor for editing
        edited_df = st.data_editor(filtered_df_with_delete, use_container_width=True)

        # Button to save changes
        if st.button('Save Changes'):
            try:
                # Find rows marked for deletion
                deleted_rows = edited_df[edited_df['Delete?']]
                
                if not deleted_rows.empty:
                    st.warning("Are you sure you want to delete the selected items? This action cannot be undone.")
                    if st.button("Confirm Deletion"):
                        # Get original indices to delete from Google Sheet
                        deleted_indices = deleted_rows.index.tolist()
                        
                        for index in sorted(deleted_indices, reverse=True):
                            ws.delete_rows(index + 2)
                            deleted_item_name = filtered_df.loc[index]['Item Name']
                            log_action("Delete", deleted_item_name, f"Deleted item from inventory via data editor.")
                        
                        st.success("Selected items deleted successfully! Refreshing data...")
                        clear_cache()
                else:
                    updated_df = edited_df.drop(columns=['Delete?'])
                    set_with_dataframe(ws, updated_df, include_index=False, resize=True)
                    
                    st.success("Changes saved successfully! Refreshing data...")
                    clear_cache()
            except Exception as e:
                st.error(f"Error saving changes: {e}")

    else:
        st.info("No data available to display or filter. Please add items using the sidebar.")

# -----------------------------
# Add Item
# -----------------------------
elif st.session_state['current_page'] == "Add Item":
    st.subheader("Add New Inventory Items")
    st.markdown("Use the form below to add items to a list. Click 'Execute All Additions' when finished.")

    # Form to add a single item
    with st.form("add_item_form"):
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        with col1:
            name = st.text_input("Item Name", key="add_name_input")
        with col2:
            category = st.text_input("Category", key="add_category_input")
        with col3:
            location = st.selectbox("Location", ["godown", "Shop"], key="add_location_input")
        with col4:
            initial_stock = st.number_input("Initial Stock", min_value=0, value=0, key="add_stock_input")
        with col5:
            st.markdown("<h3 style='margin-bottom: 0px;'>Add</h3>", unsafe_allow_html=True)
            add_to_list_button = st.form_submit_button("➕")

    if add_to_list_button:
        if not name or not category or not location or initial_stock == 0:
            st.error("Please fill out all fields and select a valid initial stock.")
        else:
            st.session_state['add_list'].append({
                'Item Name': name,
                'Category': category,
                'Location': location,
                'Initial stock': initial_stock,
                'Current Stock': initial_stock
            })
            st.success(f"Added {name} to the addition list.")
    
    st.markdown("---")
    st.subheader("Items to Add")
    if st.session_state['add_list']:
        add_df = pd.DataFrame(st.session_state['add_list'])
        st.dataframe(add_df, use_container_width=True)

        col_add_buttons = st.columns(2)
        with col_add_buttons[0]:
            if st.button("Execute All Additions"):
                try:
                    next_sr_no = len(df) + 1 if not df.empty else 1
                    for item in st.session_state['add_list']:
                        item['Sr No'] = next_sr_no
                        next_sr_no += 1
                    
                    new_items_df = pd.DataFrame(st.session_state['add_list'])
                    updated_df = pd.concat([df, new_items_df], ignore_index=True)
                    
                    set_with_dataframe(ws, updated_df, include_index=False, resize=True)
                    
                    for item in st.session_state['add_list']:
                        log_action("Add", item['Item Name'], f"Added new item with initial stock: {item['Initial stock']}.")
                    
                    st.success("All items added successfully! Inventory updated.")
                    st.session_state['add_list'] = []  # Clear the list
                    clear_cache()
                except Exception as e:
                    st.error(f"Error executing additions: {e}")
        with col_add_buttons[1]:
            if st.button("Cancel"):
                st.session_state['add_list'] = []
                st.rerun()
    else:
        st.info("The addition list is empty. Add items using the form above.")

# -----------------------------
# Move Item
# -----------------------------
elif st.session_state['current_page'] == "Move Item":
    st.subheader("Move Inventory Items")
    st.markdown("Use the form below to add items to a list of moves. Click 'Execute All Moves' when finished.")

    # Form to add a single move
    with st.form("move_item_form"):
        item_names = df['Item Name'].tolist() if not df.empty else []
        selected_item = st.selectbox("Select Item to Move", [''] + item_names, key="move_item_select")
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            from_location = st.selectbox("Moving From", ["godown", "Shop"], index=0, key="move_from_location")
        with col2:
            to_location = st.selectbox("Moving To", ["godown", "Shop"], index=1, key="move_to_location")
        with col3:
            move_quantity = st.number_input("Quantity", min_value=0, value=0, key="move_quantity")
        with col4:
            st.markdown("<h3 style='margin-bottom: 0px;'>Add</h3>", unsafe_allow_html=True)
            add_to_list_button = st.form_submit_button("➕")

    if add_to_list_button:
        if not selected_item or not to_location or move_quantity == 0:
            st.error("Please fill out all fields and select a valid quantity.")
        else:
            current_stock = df.loc[df['Item Name'] == selected_item, 'Current Stock'].values[0]
            if move_quantity > current_stock:
                st.error(f"Not enough stock to move! Current stock for {selected_item} is {current_stock}.")
            else:
                st.session_state['moves_list'].append({
                    'Item Name': selected_item,
                    'From Location': from_location,
                    'To Location': to_location,
                    'Quantity': move_quantity
                })
                st.success(f"Added {move_quantity} of {selected_item} to the move list.")

    st.markdown("---")
    st.subheader("Move List")
    if st.session_state['moves_list']:
        moves_df = pd.DataFrame(st.session_state['moves_list'])
        st.dataframe(moves_df, use_container_width=True)
        
        col_move_buttons = st.columns(2)
        with col_move_buttons[0]:
            if st.button("Execute All Moves"):
                try:
                    for move in st.session_state['moves_list']:
                        item_name = move['Item Name']
                        move_quantity = move['Quantity']
                        to_location = move['To Location']
                        
                        df.loc[df['Item Name'] == item_name, 'Current Stock'] -= move_quantity
                        df.loc[df['Item Name'] == item_name, 'Location'] = to_location
                        
                        log_action("Move", item_name, f"Moved {move_quantity} units from {move['From Location']} to {to_location}.")

                    set_with_dataframe(ws, df, include_index=False, resize=True)
                    
                    st.success("All moves executed successfully! Inventory updated.")
                    st.session_state['moves_list'] = []  # Clear the list
                    clear_cache()
                except Exception as e:
                    st.error(f"Error executing moves: {e}")
        with col_move_buttons[1]:
            if st.button("Cancel"):
                st.session_state['moves_list'] = []
                st.rerun()
    else:
        st.info("The move list is empty. Add items using the form above.")

# -----------------------------
# Purchase Item
# -----------------------------
elif st.session_state['current_page'] == "Purchase Item":
    st.subheader("Purchase Inventory Items")
    st.markdown("Use the form below to add items to a list of purchases. Click 'Execute All Purchases' when finished.")
    
    # Form to add a single purchase
    with st.form("purchase_item_form"):
        item_names = df['Item Name'].tolist() if not df.empty else []
        selected_item = st.selectbox("Select Item to Purchase", [''] + item_names, key="purchase_item_select")

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            purchase_quantity = st.number_input("Quantity to Purchase", min_value=0, value=0, key="purchase_quantity")
        with col2:
            st.markdown("<h3 style='margin-bottom: 0px;'>Add</h3>", unsafe_allow_html=True)
            add_to_list_button = st.form_submit_button("➕")

    if add_to_list_button:
        if not selected_item or purchase_quantity == 0:
            st.error("Please fill out all fields and select a valid quantity.")
        else:
            st.session_state['purchase_list'].append({
                'Item Name': selected_item,
                'Quantity': purchase_quantity
            })
            st.success(f"Added {purchase_quantity} of {selected_item} to the purchase list.")
    
    st.markdown("---")
    st.subheader("Purchase List")
    if st.session_state['purchase_list']:
        purchase_df = pd.DataFrame(st.session_state['purchase_list'])
        st.dataframe(purchase_df, use_container_width=True)
        
        col_purchase_buttons = st.columns(2)
        with col_purchase_buttons[0]:
            if st.button("Execute All Purchases"):
                try:
                    for purchase in st.session_state['purchase_list']:
                        item_name = purchase['Item Name']
                        purchase_quantity = purchase['Quantity']
                        
                        df.loc[df['Item Name'] == item_name, 'Current Stock'] += purchase_quantity
                        
                        log_action("Purchase", item_name, f"Purchased {purchase_quantity} units. New stock: {df.loc[df['Item Name'] == item_name, 'Current Stock'].iloc[0]}.")

                    set_with_dataframe(ws, df, include_index=False, resize=True)
                    
                    st.success("All purchases executed successfully! Inventory updated.")
                    st.session_state['purchase_list'] = []  # Clear the list
                    clear_cache()
                except Exception as e:
                    st.error(f"Error executing purchases: {e}")
        with col_purchase_buttons[1]:
            if st.button("Cancel"):
                st.session_state['purchase_list'] = []
                st.rerun()
    else:
        st.info("The purchase list is empty. Add items using the form above.")
                
# -----------------------------
# View Logs
# -----------------------------
elif st.session_state['current_page'] == "View Logs":
    st.subheader("App Activity Logs")
    
    # Date picker for filtering logs
    if not df_logs.empty:
        log_date = st.date_input("Select a date to view logs", datetime.date.today())
        
        filtered_logs_df = df_logs[df_logs['Timestamp'].dt.date == log_date]
        
        if not filtered_logs_df.empty:
            st.dataframe(filtered_logs_df, use_container_width=True)
        else:
            st.info(f"No log data found for {log_date}.")
    else:
        st.info("No log data to display yet.")
