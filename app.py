import streamlit as st
from theme import theme_button

theme_button()  

# Define the pages
page_1 = st.Page("page_1.py", title="DCA Kalkulačka", icon="🎈")
page_2 = st.Page("page_2.py", title="Historický Backtest", icon="✈")
page_3 = st.Page("page_3.py", title="Srovnávač strategií", icon="🎉")


# Set up navigation
pg = st.navigation(pages=[page_1, page_2, page_3],expanded=True)

# Run the selected page
pg.run()