import streamlit as st 
from calculate_seats import calculate_seats_interface

def main():
    st.set_page_config(layout="wide")
    calculate_seats_interface()

if __name__ == "__main__":
    main()
