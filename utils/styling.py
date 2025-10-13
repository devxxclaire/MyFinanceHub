import streamlit as st

def set_custom_style():
    """
    Apply a sleek dark-themed custom style for MyFinanceHub
    with modern gradients, white text, and accent highlights.
    """
    st.markdown("""
        <style>
            /* --- GLOBAL BACKGROUND --- */
            .stApp {
                background: linear-gradient(135deg, #0d1117, #1a1f2b);
                color: #FFFFFF;
                font-family: 'Inter', sans-serif;
            }

            /* --- HEADERS --- */
            h1, h2, h3, h4, h5, h6 {
                color: #00D4FF; /* Cyan Accent */
                font-weight: 600;
            }

            /* --- SIDEBAR --- */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #111827, #1f2937);
                color: #E5E7EB;
                border-right: 1px solid #374151;
            }

            [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
                color: #60A5FA;
            }

            [data-testid="stSidebar"] a {
                color: #A5B4FC !important;
                font-weight: 500;
            }

            [data-testid="stSidebar"] a:hover {
                color: #C084FC !important;
                font-weight: 600;
            }

            /* --- BUTTONS --- */
            div.stButton > button:first-child {
                background: linear-gradient(90deg, #2563EB, #06B6D4);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0.6rem 1.2rem;
                font-weight: 600;
                font-size: 1rem;
                transition: all 0.3s ease;
            }

            div.stButton > button:first-child:hover {
                background: linear-gradient(90deg, #0EA5E9, #3B82F6);
                transform: scale(1.05);
            }

            /* --- TEXT INPUTS --- */
            .stTextInput > div > div > input {
                background-color: #111827;
                color: white;
                border: 1px solid #374151;
                border-radius: 8px;
            }

            /* --- SELECT BOXES --- */
            .stSelectbox, .stMultiSelect {
                background-color: #111827 !important;
                color: #FFFFFF !important;
            }

            /* --- DATAFRAMES / TABLES --- */
            .stDataFrame {
                background-color: #1F2937 !important;
                color: #E5E7EB !important;
                border-radius: 8px;
                padding: 1rem;
            }

            /* --- FOOTER HIDE --- */
            footer {
                visibility: hidden;
            }

            /* --- CENTERING ELEMENTS --- */
            .centered {
                display: flex;
                justify-content: center;
                align-items: center;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)