import requests
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="Stock & SEC Filing Quick View", page_icon="📈", layout="centered"
)

# Custom Styling for Minimalist Card View
st.markdown(
    """
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-top: 20px;
        border: 1px solid #e9ecef;
    }
    .metric-title {
        font-size: 14px;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 600;
        color: #212529;
    }
    .card-header {
        font-size: 20px;
        font-weight: 700;
        color: #212529;
        margin-bottom: 15px;
        border-bottom: 2px solid #f1f3f5;
        padding-bottom: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=86400)
def get_sec_tickers():
    """Fetches official SEC ticker-to-CIK mapping map."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def get_cik_by_ticker(ticker_symbol, tickers_data):
    """Finds the padded 10-digit CIK for a given stock ticker."""
    ticker_upper = ticker_symbol.upper()
    if not tickers_data:
        return None
    for _, info in tickers_data.items():
        if info["ticker"].upper() == ticker_upper:
            raw_cik = str(info["cik_str"])
            return raw_cik.zfill(10)
    return None


def get_sec_submissions(cik):
    """Fetches filing history JSON from SEC EDGAR."""
    headers = {"User-Agent": "PersonalResearchApp user@example.com"}
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


# App Interface
st.title("US Stock & SEC Quick Lookup")
st.write(
    "Enter a US stock ticker to view its exchange price, latest quarterly report period, and direct SEC filing links."
)

ticker_input = st.text_input(
    "Stock Ticker Symbol", value="AAPL", max_chars=10
).strip()

if st.button("Fetch Data", type="primary"):
    if not ticker_input:
        st.warning("Please enter a valid stock ticker.")
    else:
        with st.spinner(f"Fetching data for {ticker_input.upper()}..."):
            # 1. Fetch Live Stock Data via yfinance
            stock = yf.Ticker(ticker_input)
            try:
                hist = stock.history(period="1d")
                if not hist.empty:
                    current_price = hist["Close"].iloc[-1]
                else:
                    current_price = stock.info.get(
                        "regularMarketPrice",
                        stock.info.get("currentPrice", None),
                    )
            except Exception:
                current_price = None

            company_name = stock.info.get(
                "longName", ticker_input.upper()
            )

            # 2. Fetch SEC Data
            sec_tickers_map = get_sec_tickers()
            cik = get_cik_by_ticker(ticker_input, sec_tickers_map)

            latest_form = None
            filed_date = None
            report_period = None
            sec_link = None
            filings_list_url = f"https://www.sec.gov/edgar/browse/?CIK={cik}" if cik else "#"

            if cik:
                submissions = get_sec_submissions(cik)
                if submissions and "filings" in submissions:
                    recent = submissions["filings"]["recent"]
                    forms = recent["form"]
                    filing_dates = recent["filingDate"]
                    report_dates = recent["reportDate"]
                    accession_numbers = recent["accessionNumber"]
                    primary_documents = recent["primaryDocument"]

                    # Look for the latest 10-Q (Quarterly Report)
                    for i, form in enumerate(forms):
                        if form == "10-Q":
                            latest_form = "10-Q"
                            filed_date = filing_dates[i]
                            report_period = report_dates[i] if i < len(report_dates) else "N/A"
                            acc_no_raw = accession_numbers[i]
                            acc_no_clean = acc_no_raw.replace("-", "")
                            doc_name = primary_documents[i]
                            sec_link = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_clean}/{doc_name}"
                            break

            # --- RENDER MINIMALIST CARD VIEW ---
            st.markdown(
                f"""
            <div class="card">
                <div class="card-header">{company_name} ({ticker_input.upper()})</div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                    <div>
                        <div class="metric-title">Latest Exchange Price</div>
                        <div class="metric-value">{"$" + f"{current_price:,.2f}" if current_price else "Unavailable"}</div>
                    </div>
                    <div>
                        <div class="metric-title">Latest Reported Period</div>
                        <div class="metric-value" style="font-size: 20px; margin-top: 4px;">{report_period if report_period else "N/A"}</div>
                    </div>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #e9ecef; margin: 15px 0;">
                
                <div style="margin-bottom: 12px;">
                    <div class="metric-title">SEC Filing Status</div>
                    <div style="font-size: 15px; color: #495057;">
                        <b>Form:</b> {latest_form if latest_form else "10-Q data not found"} &nbsp;|&nbsp; 
                        <b>Filed Date:</b> {filed_date if filed_date else "N/A"}
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Action Buttons / Links outside HTML card for native Streamlit interactions
            st.write("")
            col1, col2 = st.columns(2)
            with col1:
                if sec_link:
                    st.markdown(
                        f"""<a href="{sec_link}" target="_blank" style="display:block; text-align:center; background-color:#212529; color:white; padding:10px 15px; border-radius:6px; text-decoration:none; font-weight:500;">📥 Download Latest 10-Q File</a>""",
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("Direct 10-Q download link unavailable.")
            with col2:
                st.markdown(
                    f"""<a href="{filings_list_url}" target="_blank" style="display:block; text-align:center; background-color:#6c757d; color:white; padding:10px 15px; border-radius:6px; text-decoration:none; font-weight:500;">📂 View All SEC Filings</a>""",
                    unsafe_allow_html=True,
                )
