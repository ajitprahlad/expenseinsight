import streamlit as st
from PyPDF2 import PdfReader
import re
import pandas as pd
import matplotlib.pyplot as plt
import time

st.set_page_config(
        page_title="ExpenseInsight")

# Function to process the PDF and extract transactions from all pages
def process_pdf(file):
    # Read the PDF
    reader = PdfReader(file)
    all_data_rows = []
    previous_balance = None  # Track the balance across pages

    # Iterate over each page
    for page in reader.pages:
        # Extract text from the page
        raw_text = page.extract_text()

        # Normalize the text
        normalized_text = re.sub(r"\n(?!\d{2}-[A-Za-z]{3}-\d{4})", " ", raw_text)  # Merge multiline transactions
        normalized_text = re.sub(r"\s{2,}", " ", normalized_text)  # Remove extra spaces
        lines = normalized_text.split('\n')

        # Skip the first and last rows (header/footer)
        lines = lines[1:-1]

        # Extract relevant data rows
        for line in lines:
            # Check if the line starts with a date
            if re.match(r"^\d{2}-[A-Za-z]{3}-\d{4}", line):
                parts = line.split(' ')
                # First part is the Date
                date = parts[0]
                # Balance is always the last part
                balance = float(parts[-1].replace(',', ''))
                # Transaction amount is the second-to-last part
                transaction_amount = float(parts[-2].replace(',', ''))
                # Extract particulars
                particulars = ' '.join(parts[1:-2])

                # Determine transaction type (DR or CR)
                if "DR/" in line:  # Withdrawal
                    withdrawal = transaction_amount
                    deposit = 0.0
                elif "CR/" in line:  # Deposit
                    withdrawal = 0.0
                    deposit = transaction_amount
                else:
                    # Fallback to comparing balances (used if markers are absent)
                    if previous_balance is not None:
                        if balance < previous_balance:  # Balance decreased -> Withdrawal
                            withdrawal = transaction_amount
                            deposit = 0.0
                        else:  # Balance increased -> Deposit
                            withdrawal = 0.0
                            deposit = transaction_amount
                    else:
                        withdrawal, deposit = 0.0, 0.0

                # Update the previous balance
                previous_balance = balance

                # Append row to the data list
                all_data_rows.append([date, particulars, deposit, withdrawal, balance])

    # Create DataFrame
    columns = ['Date', 'Particulars', 'Deposits', 'Withdrawals', 'Balance']
    df = pd.DataFrame(all_data_rows, columns=columns)
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')    
    return df

# Function to categorize expenses
def categorize_expenses(df):
    # Define categories with relevant keywords
    categories = {
        "Food & Dining": ["SWIG", "ZOMA", "MCD", "REST", "FOOD", "DINING"],
        "Travel": ["IRCT", "UBER", "OLA", "TRAVEL", "FLIGHT", "TRAIN", "TICKET"],
        "Shopping": ["AMAZ", "FLIP", "SHOP", "PURCHASE", "STORE", "ONLINE"],
        "Utilities": ["JIO", "AIRT", "BILL", "ELECTRIC", "WATER", "UTILITY"],
        "Salary": ["SALARY", "PAYROLL", "CREDIT"],
        "Entertainment": ["MOVIE", "NETFLIX", "SPOTIFY", "ENTERTAIN"],
        "Others": []  # Default category
    }

    # Initialize the Category column with 'Others'
    df['Category'] = 'Others'

    # Iterate over each category and its keywords
    for category, keywords in categories.items():
        if keywords:  # Skip empty categories like "Others"
            # Create a regex pattern to match any keyword in the category
            pattern = '|'.join(keywords)
            # Use regex to categorize the transactions
            df.loc[df['Particulars'].str.contains(pattern, case=False, na=False), 'Category'] = category

    return df


# Streamlit App UI
st.title(":money_with_wings: ExpenseInsight :bar_chart:")

# File upload
uploaded_file = st.file_uploader("Please upload your bank statement in PDF format", type="pdf")

if uploaded_file is None:
    st.markdown("""
        <div style="background-color: #333333; padding: 10px; border-radius: 5px; font-size: 14px; color: #f1f1f1;">
            <strong>Note:</strong> Currently this app can only process IndusInd Bank Statement.
        </div>
    """, unsafe_allow_html=True)

if uploaded_file is not None:
    try:
        # Process the uploaded file
        st.markdown(":hourglass_flowing_sand: **Processing...**")
    
        with st.spinner("Processing your bank statement..."):
            time.sleep(2)  # Simulating processing time
            st.success("Processing Complete!")
            df = process_pdf(uploaded_file)
            df = categorize_expenses(df)

        # Display the DataFrame
        st.subheader("Extracted Transactions :page_with_curl:")
        df_reset = df.reset_index(drop=True)
        df_reset.index = df_reset.index + 1  # Adjust index to start from 1

        # Display the DataFrame in Streamlit
        st.dataframe(df_reset)

        # Insight 1: Expense Categorization
        st.subheader("Expense Categorization :card_index_dividers:")
        # Filter out salary-related entries if you don't want them in the expense category
        df_filtered = df[df['Category'] != 'Salary']
        # Calculate the total withdrawals
        total_withdrawals = df_filtered['Withdrawals'].sum()
        # Group by category and calculate the sum of withdrawals for each category
        category_summary = df_filtered.groupby('Category')['Withdrawals'].sum().reset_index()
        # Calculate the percentage for each category
        category_summary['Percentage'] = (category_summary['Withdrawals'] / total_withdrawals) * 100
         # Round the percentages to 2 decimal places
        category_summary['Percentage'] = category_summary['Percentage'].round(2)
        # Display the bar chart with percentages
        st.bar_chart(data=category_summary, x='Category', y='Percentage')

       # Insight 2: Weekly Spending Trends
        st.subheader("Weekly Spending Trends :chart_with_upwards_trend:")
        # Ensure 'Date' is a datetime object
        if df['Date'].dtype == 'object':  
            df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
        # Extract the month and calculate the week number within that month (1-4)
        df['Week_of_Month'] = df['Date'].dt.day // 7 + 1  # Divide day by 7 and add 1 to get week number (1-4)
        # Group by the week of the month to calculate total withdrawals
        weekly_summary = df.groupby('Week_of_Month')['Withdrawals'].sum().reset_index()
        # Rename the column for better readability
        weekly_summary.rename(columns={'Week_of_Month': 'Week'}, inplace=True)
        # Plot the chart
        st.line_chart(data=weekly_summary, x='Week', y='Withdrawals')

        # Insight 3: Top Vendors
        st.subheader("Top 5 Expenses")
        # Group by 'Particulars' and sum withdrawals, then get the top 5
        expense_summary = df.groupby('Particulars')['Withdrawals'].sum().nlargest(5).reset_index()
        # Adjust the index to start from 1
        expense_summary.index = expense_summary.index + 1
        # Display the DataFrame
        st.dataframe(expense_summary)
    
       # Insight 4: Cash Flow Summary
        st.subheader("💰 Cash Flow Summary")

        # Calculate totals for deposits, withdrawals, and net cash flow
        total_deposits = df['Deposits'].sum()
        total_withdrawals = df['Withdrawals'].sum()
        net_cash_flow = total_deposits - total_withdrawals

        # Calculate percentage of savings
        if total_deposits > 0:
            savings_percentage = (net_cash_flow / total_deposits) * 100
        else:
            savings_percentage = 0  # Avoid division by zero if deposits are 0

        # Display metrics
        st.metric("Total Deposits", f"₹{total_deposits:,.2f}")
        st.metric("Total Withdrawals", f"₹{total_withdrawals:,.2f}")
        st.metric("Remaining Balance", f"₹{net_cash_flow:,.2f}")

        # Provide feedback based on savings percentage
        if savings_percentage > 50:
            st.success(f"Great job! You've saved {savings_percentage:.2f}% of your deposits!")
        elif savings_percentage < 0:
            st.error(f"Uh-oh! You're in a negative balance. You've spent more than your deposits by {abs(savings_percentage):.2f}%.")
        else:
            st.warning(f"You're doing well! You've saved {savings_percentage:.2f}% of your deposits.")

        # Option to download the DataFrame as CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Processed Data as CSV",
            data=csv,
            file_name="processed_transactions.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"An error occurred: {e}")