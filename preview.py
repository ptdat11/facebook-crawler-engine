import PIL.Image
import streamlit as st
import pandas as pd
from pathlib import Path
import numpy as np
import glob
import sys
import PIL

data_dir = "kltn"
page_ids = glob.glob("*", root_dir=f"{data_dir}/")

def on_select():
    st.session_state.index = 0

page_dropdown = st.selectbox(
    "Page ID:",
    options=page_ids,
    index=None,
    placeholder="Select a page ID",
    on_change=on_select
)

if not page_dropdown:
    sys.exit()

root_dir = Path(data_dir) / page_dropdown
df = pd.read_csv(
    root_dir / f"{page_dropdown}.csv"
)
# img_paths = glob.glob(root_dir / "imgs" / "*.jpg")

def handle_prev():
    st.session_state.index = np.clip(
        st.session_state.index-1, 
        a_min=0, a_max=df.shape[0]-1
    )

def handle_next():
    st.session_state.index = np.clip(
        st.session_state.index+1, 
        a_min=0, a_max=df.shape[0]-1
    )

_, leftcol, centercol, rightcol = st.columns([1/3-.137, .137, 1/3, 1/3])

with leftcol:
    st.button("Previous", on_click=handle_prev)
with centercol:
    st.number_input(
        label="Index:",
        label_visibility="collapsed",
        min_value=0,
        max_value=df.shape[0]-1,
        key="index"
    )
with rightcol:
    st.button("Next", on_click=handle_next)

i = st.session_state.index
st.link_button("Go to post", df.post_url[i], type="primary")
st.write(df.text[i])

imgs = [
    str(root_dir / "imgs" / image)
    for image in df.images[i].split()
]
st.image(imgs)