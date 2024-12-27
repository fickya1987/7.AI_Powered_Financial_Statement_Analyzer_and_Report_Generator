import streamlit as st
import yfinance as yf
import pandas as pd
from openai import OpenAI
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
)

# Check if the API key was loaded
if not client.api_key:
    st.error("OpenAI API key not found. Please set it in the .env file or Streamlit secrets.")
    st.stop()

# Define the FinancialAnalyzer class
class FinancialAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker
        self.stock = yf.Ticker(ticker)
        self.income_stmt = None
        self.balance_sheet = None
        self.cash_flow = None
        self.financial_ratios = {}

    def fetch_financial_statements(self):
        try:
            self.income_stmt = self.stock.financials
            self.balance_sheet = self.stock.balance_sheet
            self.cash_flow = self.stock.cashflow
            return True
        except Exception as e:
            st.error(f"Error fetching financial statements: {e}")
            return False

    def calculate_financial_ratios(self):
        try:
            # Initialize an empty list for missing data
            missing_data = []

            # Gross Margin = Gross Profit / Total Revenue
            try:
                gross_profit = self.income_stmt.loc['Gross Profit'].iloc[0]
                total_revenue = self.income_stmt.loc['Total Revenue'].iloc[0]
                self.financial_ratios['Gross Margin'] = gross_profit / total_revenue
            except KeyError:
                missing_data.append('Gross Margin')

            # Current Ratio = Total Current Assets / Total Current Liabilities
            try:
                total_current_assets = self.balance_sheet.loc['Total Current Assets'].iloc[0]
                total_current_liabilities = self.balance_sheet.loc['Total Current Liabilities'].iloc[0]
                self.financial_ratios['Current Ratio'] = total_current_assets / total_current_liabilities
            except KeyError:
                missing_data.append('Current Ratio')

            # Debt-to-Equity Ratio = Total Liabilities / Total Stockholder Equity
            try:
                total_liabilities = self.balance_sheet.loc['Total Liab'].iloc[0]
                shareholder_equity = self.balance_sheet.loc['Total Stockholder Equity'].iloc[0]
                self.financial_ratios['Debt-to-Equity Ratio'] = total_liabilities / shareholder_equity
            except KeyError:
                missing_data.append('Debt-to-Equity Ratio')

            if missing_data:
                st.warning(f"Unable to calculate the following ratios due to missing data: {', '.join(missing_data)}")

        except Exception as e:
            st.error(f"Error calculating financial ratios: {e}")

    def generate_financial_report(self):
        try:
            if not self.financial_ratios:
                st.error("No financial ratios available to generate the report.")
                return None

            # Build the prompt based on available ratios
            ratios_text = ""
            for ratio_name, ratio_value in self.financial_ratios.items():
                ratios_text += f"{ratio_name}: {ratio_value:.2f}\n"

            prompt = f"""
            Provide a detailed analysis of {self.ticker}'s financial health based on the following financial ratios:

            {ratios_text}

            Discuss what each available ratio means for the company's financial stability and performance.
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7,
            )
            report = response.choices[0].message.content.strip()
            return report
        except Exception as e:
            st.error(f"Error generating financial report: {e}")
            return None

# Function to create a download link for the report
def get_text_download_link(text, filename):
    b64 = base64.b64encode(text.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">Download Report</a>'
    return href

def generate_report_with_available_data(analyzer):
    try:
        # Build the prompt using whatever data is available
        prompt = f"""
        Provide a detailed analysis of {analyzer.ticker}'s financial health based on the available financial statements.

        Discuss the company's performance, financial stability, and any notable trends or observations.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=1.0,
        )
        report = response.choices[0].message.content.strip()
        return report
    except Exception as e:
        st.error(f"Error generating financial report: {e}")
        return None

# Main function to run the Streamlit app
def main():
    st.title("AI-Powered Financial Statement Analyzer and Report Generator")

    # Sidebar for user input
    st.sidebar.header("User Input")
    ticker = st.sidebar.text_input("Stock Ticker Symbol", value='AAPL').upper()

    if ticker:
        st.sidebar.write(f"Analyzing: {ticker}")
        with st.spinner('Fetching data...'):
            analyzer = FinancialAnalyzer(ticker)
            if analyzer.fetch_financial_statements():
                analyzer.calculate_financial_ratios()

                if analyzer.financial_ratios:
                    st.success("Data fetched and ratios calculated.")

                    # Option to display raw financial statements
                    if st.sidebar.checkbox("Show Raw Financial Statements"):
                        st.subheader("Income Statement")
                        st.write(analyzer.income_stmt)
                        st.subheader("Balance Sheet")
                        st.write(analyzer.balance_sheet)
                        st.subheader("Cash Flow Statement")
                        st.write(analyzer.cash_flow)

                    # Display financial ratios
                    st.subheader("Key Financial Ratios")
                    st.write(pd.DataFrame.from_dict(analyzer.financial_ratios, orient='index', columns=['Value']))

                    with st.spinner('Generating AI report...'):
                        report = analyzer.generate_financial_report()
                    if report:
                        st.subheader("AI-Generated Financial Report")
                        st.write(report)
                        st.markdown(get_text_download_link(report, f"{ticker}_financial_report.txt"), unsafe_allow_html=True)
                    else:
                        st.error("Failed to generate financial report.")
                else:
                    st.error("Financial ratios could not be calculated.")
                    st.info("Generating report based on available financial data.")

                    # Attempt to generate report based on available financial statements
                    report = generate_report_with_available_data(analyzer)
                    if report:
                        st.subheader("AI-Generated Financial Report")
                        st.write(report)
                    else:
                        st.error("Unable to generate report due to insufficient data.")
            else:
                st.error("Failed to fetch data. Please check the ticker symbol and try again.")

if __name__ == "__main__":
    main()
