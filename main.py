import streamlit as st 
st.set_page_config(page_title="Dairy Farm Management ", layout="wide")
expense

st.sidebar.header("Navigation")
page=st.sidebar.radio("Go to", ["Milking&Feeding", "Milk Distribution", "Expense", "Payments", "Investments"])

if page=="Milking&Feeding":
    st.write("Hello1")
elif page=="Milk Distribution":
    st.write("Hello2") 
elif page=="Expense":
    st.write("Hello3")
elif page=="Payments":
    st.write("Hello4")
elif page=="Investments":
    st.write("Hello5")