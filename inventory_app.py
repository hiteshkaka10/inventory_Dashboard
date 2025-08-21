import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------------------------
# Initialize Session State
# ---------------------------
if "inventory" not in st.session_state:
    # Check if the Excel file exists
    if os.path.exists("inventory.xlsx"):
        try:
            # Read the inventory data from the Excel file
            st.session_state.inventory = pd.read_excel("inventory.xlsx")
            
            # Initialize a "Current_Stock" column if it doesn't exist
            if "Current_Stock" not in st.session_state.inventory.columns:
                 st.session_state.inventory["Current_Stock"] = st.session_state.inventory["Initial_Stock"]
        except Exception as e:
            st.error(f"Error loading inventory.xlsx: {e}")
            st.stop()
    else:
        # Fallback to a default DataFrame if the file is not found
        st.warning("inventory.xlsx not found. Using a default inventory.")
        st.session_state.inventory = pd.DataFrame({
            "Item": ["Water Tank", "Plastic Bucket", "Storage Box", "Chair Model 220"],
            "Initial_Stock": [20, 75, 150, 40],
            "Current_Stock": [20, 75, 150, 40]
        })

if "logs" not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=["Time", "Action", "Item", "Quantity", "Final Count"])

# ---------------------------
# Sidebar Navigation
# ---------------------------
st.sidebar.title("📦 Inventory System")
page = st.sidebar.radio("Navigation", ["🏠 Home", "📊 Dashboard", "📋 List of Items", "🔄 Move / Purchase Item", "🗓️ Daily Log"])

# ---------------------------
# Home Page
# ---------------------------
if page == "🏠 Home":
    st.title("Inventory Management System")
    st.markdown("Welcome! Please select a section from the left sidebar.")

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

        st.subheader("Monthly Movement Summary")
        logs["Month"] = pd.to_datetime(logs["Time"]).dt.to_period("M")
        monthly_summary = logs.groupby("Month")["Quantity"].sum().reset_index()
        st.bar_chart(monthly_summary.set_index("Month"))

        st.subheader("Item-wise Movement")
        item_summary = logs.groupby("Item")["Quantity"].sum().reset_index()
        st.dataframe(item_summary)

# ---------------------------
# List of Items
# ---------------------------
elif page == "📋 List of Items":
    st.title("📋 Item List")
    search = st.text_input("Search Item")
    df = st.session_state.inventory
    if search:
        df = df[df["Item"].str.contains(search, case=False, na=False)]
    st.dataframe(df)

# ---------------------------
# Move / Purchase Items
# ---------------------------
elif page == "🔄 Move / Purchase Item":
    st.title("🔄 Move or Purchase Items")
    action = st.radio("Select Action", ["Move Item", "Purchase Item"])

    df = st.session_state.inventory
    selected_items = st.multiselect("Select Items", df["Item"].tolist())

    quantities = {}
    for item in selected_items:
        quantities[item] = st.number_input(f"Quantity for {item}", min_value=1, value=1)

    if st.button("Confirm Transaction"):
        for item, qty in quantities.items():
            if action == "Move Item":
                if qty > df.loc[df["Item"] == item, "Current_Stock"].values[0]:
                    st.error(f"Not enough stock for {item}")
                    continue
                df.loc[df["Item"] == item, "Current_Stock"] -= qty
                final_count = df.loc[df["Item"] == item, "Current_Stock"].values[0]
                new_log = {"Time": datetime.now(), "Action": "Move", "Item": item, "Quantity": qty, "Final Count": final_count}
            else:  # Purchase Item
                df.loc[df["Item"] == item, "Current_Stock"] += qty
                final_count = df.loc[df["Item"] == item, "Current_Stock"].values[0]
                new_log = {"Time": datetime.now(), "Action": "Purchase", "Item": item, "Quantity": qty, "Final Count": final_count}

            st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([new_log])], ignore