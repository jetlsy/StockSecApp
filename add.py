from datetime import datetime
import requests
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="Stock & SEC Filing Quick View", page_icon="📈", layout="centered"
)


@st.cache_data(ttl=86400)
def get_sec_mapping(ticker_symbol):
    """Dynamically searches the full SEC database for any ticker."""
    upper_t = ticker_symbol.upper()
    headers = {"User-Agent": "ResearchApp user@example.com"}
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for _, info in data.items():
                if info.get("ticker", "").upper() == upper_t:
                    return info.get("title", upper_t), str(info.get("cik_str")).zfill(10)
    except Exception:
        pass
    return upper_t, None


def get_latest_quarter(cik):
    """Fetches recent filings and extracts the latest 10-Q or 10-K period."""
    headers = {"User-Agent": "ResearchApp user@example.com"}
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            sub = response.json()
            recent = sub.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            report_dates = recent.get("reportDate", [])
            filing_dates = recent.get("filingDate", [])

            for i, form in enumerate(forms):
                if form in ["10-Q", "10-K"]:
                    rep_date = report_dates[i] if i < len(report_dates) else ""
                    file_date = filing_dates[i] if i < len(filing_dates) else ""
                    if rep_date:
                        try:
                            dt = datetime.strptime(rep_date, "%Y-%m-%d")
                            m = dt.month
                            y = dt.year
                            q = "Q1" if m <= 3 else ("Q2" if m <= 6 else ("Q3" if m <= 9 else "Q4"))
                            return f"{y} {q}", form, file_date
                        except Exception:
                            pass
    except Exception:
        pass
    return "N/A", "N/A", "N/A"


# App Interface
st.title("US Stock & SEC Quick Lookup")
st.write("Enter any US stock ticker to view its exchange price, official company website, latest reported year/quarter, and SEC filings portal.")

ticker_input = st.text_input("Stock Ticker Symbol", value="RXT", max_chars=10).strip()

if st.button("Fetch Data", type="primary"):
    if not ticker_input:
        st.warning("Please enter a valid stock ticker.")
    else:
        with st.spinner(f"Fetching data for {ticker_input.upper()}..."):
            ticker_upper = ticker_input.upper()
            stock = yf.Ticker(ticker_upper)

            # 1. Fetch Live Stock Price
            price_str = "Unavailable"
            try:
                hist = stock.history(period="5d")
                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])
                    price_str = f"${current_price:,.2f}"
            except Exception:
                pass

            # 2. Dynamically Get CIK and Company Name
            company_name, cik = get_sec_mapping(ticker_upper)

            # 3. Get Company Website URL
            company_website = None
            try:
                info = stock.info
                company_website = info.get("website")
            except Exception:
                pass
            if not company_website:
                company_website = f"https://www.google.com/search?q={ticker_upper}+official+website"

            # 4. Get Latest Quarter & Filing Info
            report_period_display, latest_form, filed_date = get_latest_quarter(cik) if cik else ("N/A", "N/A", "N/A")
            filings_list_url = f"https://www.sec.gov/edgar/browse/?CIK={cik}" if cik else ""

            # --- DISPLAY RESULTS ---
            st.markdown("---")
            st.subheader(f"{company_name} ({ticker_upper})")

            # Metrics Row
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Latest Exchange Price", price_str)
            with col2:
                st.metric("Latest Reported Period", report_period_display)

            st.markdown(f"**SEC Filing Info:** Form `{latest_form}` filed on `{filed_date}`")

            # Links Section
            st.markdown("### Quick Links")
            st.markdown(f"🔗 **[Official Company Website]({company_website})**")
            if filings_list_url:
                st.markdown(f"📂 **[View All SEC Filings on EDGAR]({filings_list_url})**")
            else:
                st.warning("SEC filings link unavailable for this ticker.")
