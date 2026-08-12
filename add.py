from datetime import datetime
import requests
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="Stock & SEC Filing Quick View", page_icon="📈", layout="centered"
)


@st.cache_data(ttl=86400)
def get_sec_tickers():
    """Fetches official SEC ticker-to-CIK mapping."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
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


def get_quarter_from_date(date_str):
    """Converts a report date string into Year and Quarter format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.month
        year = dt.year
        if month <= 3:
            q = "Q1"
        elif month <= 6:
            q = "Q2"
        elif month <= 9:
            q = "Q3"
        else:
            q = "Q4"
        return f"{year} {q} (Period ended {date_str})"
    except Exception:
        return date_str


# App Interface
st.title("US Stock & SEC Quick Lookup")
st.write(
    "Enter a US stock ticker to view its exchange price, stock site links, latest reported year/quarter, and SEC filings portal."
)

ticker_input = st.text_input(
    "Stock Ticker Symbol", value="RXT", max_chars=10
).strip()

if st.button("Fetch Data", type="primary"):
    if not ticker_input:
        st.warning("Please enter a valid stock ticker.")
    else:
        with st.spinner(f"Fetching data for {ticker_input.upper()}..."):
            ticker_upper = ticker_input.upper()
            stock = yf.Ticker(ticker_upper)

            # 1. Fetch Live Stock Price via history
            current_price = None
            try:
                hist = stock.history(period="5d")
                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])
            except Exception:
                pass

            # 2. Match Company Name & CIK from SEC Tickers List
            sec_tickers_map = get_sec_tickers()
            company_name = ticker_upper
            cik = None

            if sec_tickers_map:
                for _, info in sec_tickers_map.items():
                    if info["ticker"].upper() == ticker_upper:
                        company_name = info["title"]
                        raw_cik = str(info["cik_str"])
                        cik = raw_cik.zfill(10)
                        break

            # 3. Fetch SEC Filing Data for latest Year & Quarter
            latest_form = None
            filed_date = None
            report_period_display = "N/A"
            filings_list_url = (
                f"https://www.sec.gov/edgar/browse/?CIK={cik}" if cik else ""
            )

            if cik:
                submissions = get_sec_submissions(cik)
                if submissions and "filings" in submissions:
                    recent = submissions["filings"]["recent"]
                    forms = recent["form"]
                    filing_dates = recent["filingDate"]
                    report_dates = recent["reportDate"]

                    for i in range(len(forms)):
                        if forms[i] in ["10-Q", "10-K"]:
                            latest_form = forms[i]
                            filed_date = (
                                filing_dates[i] if i < len(filing_dates) else "N/A"
                            )
                            raw_rep = (
                                report_dates[i] if i < len(report_dates) else ""
                            )
                            report_period_display = get_quarter_from_date(raw_rep)
                            break

            # External Stock Site Links
            yahoo_finance_url = f"https://finance.yahoo.com/quote/{ticker_upper}"
            google_finance_url = f"https://www.google.com/finance/quote/{ticker_upper}:NASDAQ"

            # --- DISPLAY RESULTS ---
            st.markdown("---")
            st.subheader(f"{company_name} ({ticker_upper})")

            # Metrics Row
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Latest Exchange Price",
                    f"${current_price:,.2f}"
                    if current_price
                    else "Unavailable",
                )
            with col2:
                st.metric("Latest Reported Period", report_period_display)

            st.markdown("")
            st.markdown(
                f"**SEC Filing Info:** Form `{latest_form or 'N/A'}` filed on `{filed_date or 'N/A'}`"
            )

            # Links Section
            st.markdown("")
            st.markdown("### Quick Links")
            st.markdown(
                f"🔗 **[View on Yahoo Finance]({yahoo_finance_url})**"
            )
            st.markdown(
                f"🔗 **[View on Google Finance]({google_finance_url})**"
            )
            if filings_list_url:
                st.markdown(
                    f"📂 **[View All SEC Filings on EDGAR]({filings_list_url})**"
                )
            else:
                st.info("SEC filings link unavailable for this ticker.")
