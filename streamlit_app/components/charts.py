import streamlit as st
import altair as alt
import pandas as pd

def line_chart(df: pd.DataFrame, x: str, y: str, title: str):
    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(x=x, y=y)
        .properties(title=title)
    )
    st.altair_chart(chart, use_container_width=True)

def bar_chart(df: pd.DataFrame, x: str, y: str, title: str):
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(x=x, y=y)
        .properties(title=title)
    )
    st.altair_chart(chart, use_container_width=True)

