import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------
# Initialize Session State
# ---------------------------
if "inventory" not in st.session_state:
    # Initialize default inventory if no Excel file exists
    st.session_state.inventory = pd.DataFrame({
        "Item": ["Water Tank", "Plastic Bucket", "Storage Box", "Chair Model 220"],
        "Location": ["Basement", "Basement", "Basement", "Basement"],
        "Current_Stock": [20, 75, 150, 40]
    })

if "logs" not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=["Time", "Action", "Item", "Quantity", "From", "To", "Previous Count", "Final Count"])

# ---------------------------
# Home Page Buttons
# ---------------------------
st.title("📦 Inventory Management System")
st.markdown("Welcome! Choose an action below:")

col1, col2, col3 = st.columns(3)
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

with col1:
    if st.button("Add Items"):
        st.session_state.current_page = "add_items"
with col2:
    if st.button("Move Items"):
        st.session_state.current_page = "move_items"
with col3:
    if st.button("Purchase Items"):
        st.session_state.current_page = "purchase_items"

# ---------------------------
# Add Items Page
# ---------------------------
if st.session_state.current_page == "add_items":
    st.subheader("➕ Add New Item")
    item_name = st.text_input("Item Name")
    location = st.selectbox("Location", ["Basement", "Shop"])
    quantity = st.number_input("Quantity", min_value=1, value=1)

    if st.button("Add Item to Inventory"):
        if item_name in st.session_state.inventory["Item"].values:
            st.warning(f"{item_name} already exists! Use Purchase/Move instead.")
        else:
            new_item = pd.DataFrame({
                "Item": [item_name],
                "Location": [location],
                "Current_Stock": [quantity]
            })
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_item], ignore_index=True)
            st.success(f"Item '{item_name}' added successfully!")

# ---------------------------
# Move Items Page
# ---------------------------
elif st.session_state.current_page == "move_items":
    st.subheader("🔄 Move Items (Basement ↔ Shop)")
    df = st.session_state.inventory.copy()
    items = df["Item"].tolist()
    selected_items = st.multiselect("Select Items to Move", items)
    
    if selected_items:
        move_from = st.selectbox("Move From", ["Basement", "Shop"])
        move_to = st.selectbox("Move To", ["Basement", "Shop"])
        quantities = {}
        for item in selected_items:
            quantities[item] = st.number_input(f"Quantity for {item}", min_value=1, value=1)
        if st.button("Confirm Move"):
            for item, qty in quantities.items():
                mask = (st.session_state.inventory["Item"] == item) & (st.session_state.inventory["Location"] == move_from)
                if st.session_state.inventory.loc[mask, "Current_Stock"].sum() < qty:
                    st.error(f"Not enough stock for {item} in {move_from}")
                    continue
                previous_count = st.session_state.inventory.loc[mask, "Current_Stock"].values[0]
                st.session_state.inventory.loc[mask, "Current_Stock"] -= qty
                # Add or update item in destination location
                if ((st.session_state.inventory["Item"] == item) & (st.session_state.inventory["Location"] == move_to)).any():
                    st.session_state.inventory.loc[(st.session_state.inventory["Item"] == item) & (st.session_state.inventory["Location"] == move_to), "Current_Stock"] += qty
                else:
                    new_row = pd.DataFrame({"Item": [item], "Location": [move_to], "Current_Stock": [qty]})
                    st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
                final_count = st.session_state.inventory.loc[(st.session_state.inventory["Item"] == item) & (st.session_state.inventory["Location"] == move_from), "Current_Stock"].values[0]
                new_log = {
                    "Time": datetime.now(),
                    "Action": "Move",
                    "Item": item,
                    "Quantity": qty,
                    "From": move_from,
                    "To": move_to,
                    "Previous Count": previous_count,
                    "Final Count": final_count
                }
                st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore_index=True)
            st.success("Movement completed!")

# ---------------------------
# Purchase Items Page
# ---------------------------
elif st.session_state.current_page == "purchase_items":
    st.subheader("🛒 Purchase Items")
    df = st.session_state.inventory.copy()
    items = df["Item"].tolist()
    selected_items = st.multiselect("Select Items to Purchase", items)
    
    if selected_items:
        quantities = {}
        location = st.selectbox("Purchase Location", ["Basement", "Shop"])
        for item in selected_items:
            quantities[item] = st.number_input(f"Quantity for {item}", min_value=1, value=1)
        if st.button("Confirm Purchase"):
            for item, qty in quantities.items():
                mask = (st.session_state.inventory["Item"] == item) & (st.session_state.inventory["Location"] == location)
                if mask.any():
                    previous_count = st.session_state.inventory.loc[mask, "Current_Stock"].values[0]
                    st.session_state.inventory.loc[mask, "Current_Stock"] += qty
                else:
                    previous_count = 0
                    new_row = pd.DataFrame({"Item": [item], "Location": [location], "Current_Stock": [qty]})
                    st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
                final_count = st.session_state.inventory.loc[(st.session_state.inventory["Item"] == item) & (st.session_state.inventory["Location"] == location), "Current_Stock"].values[0]
                new_log = {
                    "Time": datetime.now(),
                    "Action": "Purchase",
                    "Item": item,
                    "Quantity": qty,
                    "From": "",
                    "To": location,
                    "Previous Count": previous_count,
                    "Final Count": final_count
                }
                st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore_index=True)
            st.success("Purchase completed!")

# ---------------------------
# Logs Page
# ---------------------------
st.sidebar.title("📋 Navigation")
page = st.sidebar.radio("View", ["Inventory List", "Logs"])
if page == "Inventory List":
    st.subheader("📋 Current Inventory")
    st.dataframe(st.session_state.inventory)
else:
    st.subheader("🗓️ Movement Logs")
    st.dataframe(st.session_state.logs)
