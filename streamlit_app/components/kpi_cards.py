import streamlit as st

def display(metrics: dict):
    cols = st.columns(len(metrics))
    for i, (label, value) in enumerate(metrics.items()):
        with cols[i]:
            st.metric(label, value)