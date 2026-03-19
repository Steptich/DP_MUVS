import streamlit as st
from theme import theme_button

theme_button()  

# Define the pages
main_page = st.Page("main_page.py", title="Úvodní stránka", icon="🎈")
page_2 = st.Page("page_2.py", title="DCA", icon="✈")
page_3 = st.Page("page_3.py", title="Dynamic DCA", icon="🎉")


# Set up navigation
pg = st.navigation([main_page, page_2, page_3])

# Run the selected page
pg.run()