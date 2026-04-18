import streamlit as st
from pathlib import Path

st.set_page_config(page_title="필기 정리 사이트", layout="wide")

BASE_DIR = Path("notes")
BASE_DIR.mkdir(exist_ok=True)

st.title("필기 정리 사이트")

menu = st.sidebar.radio(
    "메뉴 선택",
    ["새 파일 만들기", "파일 업로드", "저장된 파일 보기"]
)

subjects = ["인간학", "자료구조", "운영체제", "데이터베이스"]

if menu == "새 파일 만들기":
    st.header("새 txt 파일 만들기")

    subject = st.selectbox("과목 선택", subjects)
    title = st.text_input("파일 제목")
    content = st.text_area("내용 입력", height=400, placeholder="여기에 필기 내용을 입력하세요")

    if st.button("txt 파일 저장"):
        if not title.strip():
            st.warning("파일 제목을 입력하세요.")
        elif not content.strip():
            st.warning("내용을 입력하세요.")
        else:
            subject_dir = BASE_DIR / subject
            subject_dir.mkdir(exist_ok=True)

            filename = f"{title.strip()}.txt"
            file_path = subject_dir / filename

            file_path.write_text(content, encoding="utf-8")
            st.success(f"저장 완료: {subject}/{filename}")

            st.download_button(
                label="txt 다운로드",
                data=content,
                file_name=filename,
                mime="text/plain"
            )

elif menu == "파일 업로드":
    st.header("txt 파일 업로드")

    uploaded_file = st.file_uploader("정리된 txt 파일 업로드", type=["txt"])

    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8")

        st.subheader("렌더링 화면")
        st.markdown(content)

        st.subheader("원본 내용")
        st.text(content)

elif menu == "저장된 파일 보기":
    st.header("저장된 파일 보기")

    subject = st.selectbox("과목 선택", subjects)
    subject_dir = BASE_DIR / subject
    subject_dir.mkdir(exist_ok=True)

    txt_files = list(subject_dir.glob("*.txt"))

    if not txt_files:
        st.info("저장된 파일이 없습니다.")
    else:
        file_names = [file.name for file in txt_files]
        selected_file = st.selectbox("파일 선택", file_names)

        file_path = subject_dir / selected_file
        content = file_path.read_text(encoding="utf-8")

        st.subheader("렌더링 화면")
        st.markdown(content)

        st.subheader("원본 내용")
        st.text(content)

        st.download_button(
            label="txt 다운로드",
            data=content,
            file_name=selected_file,
            mime="text/plain"
        )
