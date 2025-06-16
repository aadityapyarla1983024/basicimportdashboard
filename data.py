import streamlit as st
import pandas as pd
import io
import datetime
import numpy as np

# --- Configuration for Streamlit Page ---
st.set_page_config(
    layout="wide",
    page_title="Import Data Filter & Download",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Styling ---
st.markdown("""
    <style>
    /* General adjustments for padding and width */
    .reportview-container .main .block-container {
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    /* Specific adjustments for multiselect dropdowns to prevent excessive height */
    .stMultiSelect div[data-baseweb="select"] {
        max-height: 150px;
        overflow-y: auto;
    }
    /* Text area height adjustment */
    .stTextArea [data-baseweb="textarea"] {
        min-height: 100px;
    }
    .stDownloadButton {
        margin-top: 15px;
    }
    .stSubheader {
        color: #2F80ED; /* A slightly softer blue for subheaders */
    }
    h1, h2, h3, h4, h5, h6 {
        color: #1A1A1A; /* Darker text for headers */
    }
    .sidebar .sidebar-content {
        background-color: #f0f2f6; /* Lighter sidebar background */
    }
    </style>
""", unsafe_allow_html=True)

# --- Global Data Variable ---
if 'df_original' not in st.session_state:
    st.session_state.df_original = None

# --- Custom AWP Product Description Keywords ---
AWP_KEYWORDS = [
    "TELESCOPIC BOOMLIFT", "ARTICULATING BOOMLIFT", "SCISSOR LIFT",
    "AERIAL WORK PLATFORM", "AWP", "PERSONNEL LIFT", "BOOM LIFT", "JLG",
    "GENIE", "SKYJACK", "HAULOTTE", "DINGLI", "MAN LIFT", "PLATFORM LIFT",
    "FORKLIFT", "TELEHANDLER", "STACKER", "PALLET TRUCK", "CRANE", "HOIST"
]

# --- Data Loading and Caching ---
@st.cache_data(show_spinner="Loading data, please wait...")
def load_data(uploaded_file):
    if uploaded_file.name.endswith('.csv') or uploaded_file.name.endswith('.txt'):
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        df = pd.read_csv(stringio, sep=r'\s{2,}', engine='python', skipinitialspace=True)
    elif uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file, engine='calamine')

    df.columns = df.columns.str.strip()

    col_mapping = {
        'INDIAN IMPORTER NAME': 'INDIAN IMPORTER NAME',
        'FOREIGN EXPORTER NAME': 'FOREIGN EXPORTER NAME',
        'FOREIGN COUNTRY': 'FOREIGN COUNTRY',
        'FOREIGN EXPORTER CITY': 'FOREIGN EXPORTER CITY',
        'INDIAN PORT': 'INDIAN PORT',
        'CHA NAME': 'CHA NAME',
        'MODE': 'MODE',
        'CITY': 'CITY',
        'PRODUCT DESCRIPTION': 'PRODUCT DESCRIPTION',
        'DATE': 'DATE',
        'QUANTITY': 'QUANTITY',
        'UNIT': 'UNIT',
        'TOTAL ASS VALUE INR': 'TOTAL ASS VALUE INR',
        'DUTY IN INR': 'DUTY IN INR',
        'TOTAL ASS VALUE IN FOREIGN CURRENCY': 'TOTAL ASS VALUE IN FOREIGN CURRENCY',
        'FOREIGN CURRENCY': 'FOREIGN CURRENCY',
        'FOREIGN PORT': 'FOREIGN PORT'
    }
    df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns}, inplace=True)
    
    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce', dayfirst=True)
        df.dropna(subset=['DATE'], inplace=True)
    
    numeric_cols = [
        'QUANTITY', 'TOTAL ASS VALUE INR', 'UNIT INR', 
        'TOTAL ASS VALUE IN FOREIGN CURRENCY', 'UNIT RATE IN FOREIGN CURRENCY', 
        'DUTY IN INR'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col].fillna(0, inplace=True)

    string_cols_to_categorize = [
        'INDIAN IMPORTER NAME', 'FOREIGN EXPORTER NAME', 'INDIAN PORT', 
        'FOREIGN COUNTRY', 'CHA NAME', 'FOREIGN EXPORTER CITY', 'MODE', 'CITY',
        'FOREIGN PORT', 'UNIT', 'FOREIGN CURRENCY'
    ]
    for col in string_cols_to_categorize:
        if col in df.columns and df[col].dtype == 'object':
            if df[col].nunique() / len(df[col]) < 0.5:
                df[col] = df[col].astype('category')

    return df

# --- Filtering Function ---
def apply_filters(df, filters):
    filtered_df = df.copy()

    for column, criterion in filters.items():
        if criterion is None or (isinstance(criterion, (str, list, tuple)) and not criterion):
            continue
        if column not in filtered_df.columns and column not in ['DATE_RANGE', 'AWP_MACHINES']:
            continue

        if column == 'DATE_RANGE':
            if 'DATE' in filtered_df.columns and criterion[0] is not None and criterion[1] is not None:
                start_date = pd.to_datetime(criterion[0])
                end_date = pd.to_datetime(criterion[1])
                filtered_df = filtered_df[
                    (filtered_df['DATE'] >= start_date) & 
                    (filtered_df['DATE'] <= end_date)
                ]
        elif column == 'AWP_MACHINES':
            if 'PRODUCT DESCRIPTION' in filtered_df.columns and criterion:
                awp_pattern = "|".join([k.lower() for k in criterion])
                filtered_df = filtered_df[
                    filtered_df['PRODUCT DESCRIPTION'].astype(str).str.contains(awp_pattern, case=False, na=False)
                ]
        elif isinstance(criterion, str):
            filtered_df = filtered_df[
                filtered_df[column].astype(str).str.contains(criterion, case=False, na=False)
            ]
        elif isinstance(criterion, (list, tuple)):
            if column in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[column].isin(criterion)]
    return filtered_df

# --- Main App Logic ---

st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader("Choose an Import Data File", type=["csv", "txt", "xlsx"])

if uploaded_file is not None:
    st.session_state.df_original = load_data(uploaded_file)
    st.sidebar.success("Data Loaded Successfully!")
else:
    st.info("Please upload a data file (CSV, TXT, or XLSX) to begin filtering and analysis.")
    st.session_state.df_original = None

if st.session_state.df_original is not None:
    df_full = st.session_state.df_original.copy()

    # --- Filter Options ---
    st.sidebar.header("Filter Options")

    # Date Range Filter
    min_date_val = None
    max_date_val = None

    if 'DATE' in df_full.columns and not df_full['DATE'].empty and pd.notna(df_full['DATE'].min()):
        min_date_val = df_full['DATE'].min().date()
        max_date_val = df_full['DATE'].max().date()
        
        default_start_date = min_date_val
        default_end_date = max_date_val
    else:
        today = datetime.date.today()
        min_date_val = datetime.date(today.year - 1, 1, 1)
        max_date_val = today
        default_start_date = min_date_val
        default_end_date = max_date_val
        st.sidebar.warning("No valid 'DATE' column found or all dates are missing. Date filter might not work as expected.")


    selected_date_range = st.sidebar.slider(
        "Select Date Range",
        min_value=min_date_val,
        max_value=max_date_val,
        value=(default_start_date, default_end_date),
        format="YYYY-MM-DD",
        help="Drag the sliders to select a range of dates."
    )

    # Partial Match Text Filters
    st.sidebar.subheader("Partial Match Filters")
    indian_importer_name_filter = st.sidebar.text_input("Indian Importer Name", "",
                                                      help="Search for partial Indian Importer names (case-insensitive).")
    address_filter = st.sidebar.text_input("Address (Indian Importer)", "",
                                         help="Search for partial Indian Importer addresses (case-insensitive).")
    foreign_exporter_name_filter = st.sidebar.text_input("Foreign Exporter Name", "",
                                                        help="Search for partial Foreign Exporter names (case-insensitive).")
    cha_name_filter = st.sidebar.text_input("CHA Name", "",
                                            help="Search for partial CHA names (Customs House Agent, case-insensitive).")
    general_product_desc_filter = st.sidebar.text_input("Product Description (General Keywords)", "",
                                                         help="Search for any keywords in the product description (case-insensitive).")


    # Multi-Select Filters (Dynamically populated)
    st.sidebar.subheader("Multi-Select Filters")
    
    all_indian_ports = sorted(df_full['INDIAN PORT'].dropna().unique().tolist()) if 'INDIAN PORT' in df_full.columns else []
    selected_indian_ports = st.sidebar.multiselect("Indian Port", all_indian_ports,
                                                    help="Select one or more Indian ports.")

    all_foreign_countries = sorted(df_full['FOREIGN COUNTRY'].dropna().unique().tolist()) if 'FOREIGN COUNTRY' in df_full.columns else []
    selected_foreign_countries = st.sidebar.multiselect("Foreign Country", all_foreign_countries,
                                                         help="Select one or more foreign countries.")
    
    all_foreign_exporter_cities = sorted(df_full['FOREIGN EXPORTER CITY'].dropna().unique().tolist()) if 'FOREIGN EXPORTER CITY' in df_full.columns else []
    selected_foreign_exporter_cities = st.sidebar.multiselect("Foreign Exporter City", all_foreign_exporter_cities,
                                                                help="Select one or more foreign exporter cities.")
    
    all_foreign_ports = sorted(df_full['FOREIGN PORT'].dropna().unique().tolist()) if 'FOREIGN PORT' in df_full.columns else []
    selected_foreign_ports = st.sidebar.multiselect("Foreign Port", all_foreign_ports,
                                                     help="Select one or more foreign ports.")


    all_modes = sorted(df_full['MODE'].dropna().unique().tolist()) if 'MODE' in df_full.columns else []
    selected_modes = st.sidebar.multiselect("Import Mode", all_modes,
                                            help="Select one or more modes of transport (e.g., SEA, AIR).")

    all_indian_cities = sorted(df_full['CITY'].dropna().unique().tolist()) if 'CITY' in df_full.columns else []
    selected_indian_cities = st.sidebar.multiselect("Indian Importer City", all_indian_cities,
                                                     help="Select one or more Indian importer cities.")

    # AWP Machines Filter
    st.sidebar.subheader("Special Product Filters")
    selected_awp_keywords = st.sidebar.multiselect(
        "AWP Machines/Related Products Keywords",
        options=AWP_KEYWORDS,
        help="Select keywords to filter 'PRODUCT DESCRIPTION' for Aerial Work Platform machines and related equipment."
    )

    # Build the filter dictionary
    filters = {
        'DATE_RANGE': selected_date_range,
        'INDIAN IMPORTER NAME': indian_importer_name_filter,
        'ADDRESS': address_filter,
        'FOREIGN EXPORTER NAME': foreign_exporter_name_filter,
        'INDIAN PORT': selected_indian_ports,
        'FOREIGN COUNTRY': selected_foreign_countries,
        'CHA NAME': cha_name_filter,
        'FOREIGN EXPORTER CITY': selected_foreign_exporter_cities,
        'FOREIGN PORT': selected_foreign_ports,
        'MODE': selected_modes,
        'CITY': selected_indian_cities,
        'AWP_MACHINES': selected_awp_keywords,
        'PRODUCT DESCRIPTION': general_product_desc_filter,
    }

    # Apply filters to get the filtered_df
    filtered_df = apply_filters(df_full, filters)

    # --- Display Filtered Data ---
    st.header("Filtered Data Results")
    if not filtered_df.empty:
        # Display ALL results at once
        st.dataframe(filtered_df, use_container_width=True)

        # --- Download buttons for filtered data ---
        st.subheader("Download Filtered Data")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Filtered Data as CSV",
                data=csv,
                file_name="filtered_import_data.csv",
                mime="text/csv",
            )
        with col_dl2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Filtered Data')
            excel_buffer.seek(0)
            st.download_button(
                label="Download Filtered Data as Excel",
                data=excel_buffer,
                file_name="filtered_import_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No data found matching the selected filters. Please adjust your filters or upload a different file.")