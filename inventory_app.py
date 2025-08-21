import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------------------------
# Initialize Session State
# ---------------------------
if "inventory" not in st.session_state:
    if os.path.exists("inventory.xlsx"):
        try:
            st.session_state.inventory = pd.read_excel("inventory.xlsx")
        except Exception as e:
            st.error(f"Error loading inventory.xlsx: {e}")
            st.stop()
    else:
        st.session_state.inventory = pd.DataFrame(columns=["Item", "Location", "Initial_Stock", "Current_Stock"])

if "logs" not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=["Time", "Action", "Item", "Quantity", "From_Location", "To_Location", "Previous_Count", "Final_Count"])

# ---------------------------
# Sidebar Navigation
# ---------------------------
st.sidebar.title("📦 Inventory System")
page = st.sidebar.radio("Navigation", ["🏠 Home", "📊 Dashboard", "📋 Item List", "🗓️ Movement Logs"])

# ---------------------------
# Home Page with Buttons
# ---------------------------
if page == "🏠 Home":
    st.title("📦 Inventory Management System")
    st.markdown("Select an action below:")

    col1, col2, col3 = st.columns(3)
    add_btn = col1.button("➕ Add New Item")
    move_btn = col2.button("🔄 Move Items")
    purchase_btn = col3.button("💰 Purchase Items")

    df = st.session_state.inventory

    # ---------- Add New Item ----------
    if add_btn:
        st.subheader("Add New Item")
        item_name = st.text_input("Item Name")
        location = st.selectbox("Location", ["Basement", "Shop"])
        qty = st.number_input("Initial Quantity", min_value=1, value=1)
        if st.button("Add Item", key="add_submit"):
            if item_name.strip() == "":
                st.error("Item name cannot be empty.")
            else:
                new_row = {
                    "Item": item_name.strip(),
                    "Location": location,
                    "Initial_Stock": qty,
                    "Current_Stock": qty
                }
                st.session_state.inventory = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                # Log
                new_log = {
                    "Time": datetime.now(),
                    "Action": "Add Item",
                    "Item": item_name.strip(),
                    "Quantity": qty,
                    "From_Location": None,
                    "To_Location": location,
                    "Previous_Count": 0,
                    "Final_Count": qty
                }
                st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore_index=True)
                st.success(f"Item '{item_name}' added to {location} with quantity {qty}.")
                st.session_state.inventory.to_excel("inventory.xlsx", index=False)

    # ---------- Move Items ----------
    if move_btn:
        st.subheader("Move Items Between Locations")
        if df.empty:
            st.info("No items in inventory. Add new items first.")
        else:
            from_location = st.selectbox("From Location", ["Basement", "Shop"], key="from_loc")
            to_location = st.selectbox("To Location", ["Basement", "Shop"], key="to_loc")
            if from_location == to_location:
                st.warning("Source and destination cannot be the same.")
            else:
                items_in_from = df[df["Location"] == from_location]["Item"].tolist()
                selected_items = st.multiselect("Select Items to Move", items_in_from)
                quantities = {}
                for item in selected_items:
                    max_qty = int(df.loc[(df["Item"] == item) & (df["Location"] == from_location), "Current_Stock"].values[0])
                    quantities[item] = st.number_input(f"Quantity for {item} (max {max_qty})", min_value=1, max_value=max_qty, value=1, key=f"move_{item}")
                if st.button("Confirm Move", key="move_submit"):
                    for item, qty in quantities.items():
                        prev_count = int(df.loc[(df["Item"] == item) & (df["Location"] == from_location), "Current_Stock"].values[0])
                        df.loc[(df["Item"] == item) & (df["Location"] == from_location), "Current_Stock"] -= qty
                        if ((df["Item"] == item) & (df["Location"] == to_location)).any():
                            df.loc[(df["Item"] == item) & (df["Location"] == to_location), "Current_Stock"] += qty
                        else:
                            new_row = {"Item": item, "Location": to_location, "Initial_Stock": 0, "Current_Stock": qty}
                            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            st.session_state.inventory = df
                        final_count = int(df.loc[(df["Item"] == item) & (df["Location"] == from_location), "Current_Stock"].values[0])
                        new_log = {
                            "Time": datetime.now(),
                            "Action": "Move",
                            "Item": item,
                            "Quantity": qty,
                            "From_Location": from_location,
                            "To_Location": to_location,
                            "Previous_Count": prev_count,
                            "Final_Count": final_count
                        }
                        st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore_index=True)
                    st.success("Items moved successfully!")
                    st.session_state.inventory.to_excel("inventory.xlsx", index=False)

    # ---------- Purchase Items ----------
    if purchase_btn:
        st.subheader("Purchase Existing Items")
        if df.empty:
            st.info("No items in inventory. Add new items first.")
        else:
            locations = df["Location"].unique().tolist()
            selected_location = st.selectbox("Select Location", locations, key="purchase_loc")
            items_in_location = df[df["Location"] == selected_location]["Item"].tolist()
            selected_items = st.multiselect("Select Items to Purchase", items_in_location)
            quantities = {}
            for item in selected_items:
                quantities[item] = st.number_input(f"Quantity for {item}", min_value=1, value=1, key=f"purchase_{item}")
            if st.button("Confirm Purchase", key="purchase_submit"):
                for item, qty in quantities.items():
                    prev_count = int(df.loc[(df["Item"] == item) & (df["Location"] == selected_location), "Current_Stock"].values[0])
                    df.loc[(df["Item"] == item) & (df["Location"] == selected_location), "Current_Stock"] += qty
                    final_count = int(df.loc[(df["Item"] == item) & (df["Location"] == selected_location), "Current_Stock"].values[0])
                    new_log = {
                        "Time": datetime.now(),
                        "Action": "Purchase",
                        "Item": item,
                        "Quantity": qty,
                        "From_Location": None,
                        "To_Location": selected_location,
                        "Previous_Count": prev_count,
                        "Final_Count": final_count
                    }
                    st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore_index=True)
                st.success("Purchase completed!")
                st.session_state.inventory.to_excel("inventory.xlsx", index=False)

# ---------------------------
# Dashboard
# ---------------------------
elif page == "📊 Dashboard":
    st.title("📊 Dashboard")
    logs = st.session_state.logs.copy()
    if logs.empty:
        st.info("No item movements recorded yet.")
    else:
        logs["Date"] = pd.to_datetime(logs["Time"]).dt.date
        st.subheader("Daily Movement Summary")
        daily_summary = logs.groupby("Date")["Quantity"].sum().reset_index()
        st.bar_chart(daily_summary.set_index("Date"))

        st.subheader("Item-wise Movement")
        item_summary = logs.groupby("Item")["Quantity"].sum().reset_index()
        st.dataframe(item_summary)

# ---------------------------
# Item List
# ---------------------------
elif page == "📋 Item List":
    st.title("📋 Item List")
    search = st.text_input("Search Item")
    df = st.session_state.inventory
    if search:
        df = df[df["Item"].str.contains(search, case=False, na=False)]
    st.dataframe(df)

# ---------------------------
# Movement Logs
# ---------------------------
elif page == "🗓️ Movement Logs":
    st.title("🗓️ Movement Logs")
    if st.session_state.logs.empty:
        st.info("No movements yet.")
    else:
        st.dataframe(st.session_state.logs)
