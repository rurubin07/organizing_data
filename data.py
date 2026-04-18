import streamlit as st

st.set_page_config(page_title="필기 정리 사이트", layout="wide")

st.title("필기 정리 사이트")

uploaded_file = st.file_uploader("정리된 txt 파일 업로드", type=["txt"])

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8")

    st.subheader("렌더링 화면")
    st.markdown(content)

    st.subheader("원본 내용")
    st.text(content)
