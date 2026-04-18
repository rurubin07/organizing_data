import io
import re
from pathlib import Path

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


st.set_page_config(page_title="필기 정리 사이트", layout="wide")

BASE_DIR = Path("notes")
BASE_DIR.mkdir(exist_ok=True)

DEFAULT_SUBJECTS = ["인간학", "자료구조", "운영체제"]

if "subjects" not in st.session_state:
    existing = [p.name for p in BASE_DIR.iterdir() if p.is_dir()]
    st.session_state.subjects = sorted(list(set(DEFAULT_SUBJECTS + existing)))

if not st.session_state.subjects:
    st.session_state.subjects = DEFAULT_SUBJECTS.copy()

if "selected_subject" not in st.session_state:
    st.session_state.selected_subject = st.session_state.subjects[0]

if "selected_file" not in st.session_state:
    st.session_state.selected_file = None

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False


def sanitize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name


def ensure_subject_dir(subject: str) -> Path:
    subject_dir = BASE_DIR / subject
    subject_dir.mkdir(parents=True, exist_ok=True)
    return subject_dir


def get_subject_files(subject: str):
    subject_dir = ensure_subject_dir(subject)
    return sorted(subject_dir.glob("*.txt"), key=lambda x: x.name.lower())


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def delete_file(path: Path):
    if path.exists():
        path.unlink()


def delete_subject(subject: str):
    subject_dir = BASE_DIR / subject
    if subject_dir.exists() and subject_dir.is_dir():
        for file in subject_dir.glob("*"):
            if file.is_file():
                file.unlink()
        subject_dir.rmdir()


def markdown_to_plain_text(md: str) -> str:
    lines = md.splitlines()
    result = []

    for line in lines:
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^\-\s*", "• ", line)
        line = re.sub(r"^\d+\.\s*", "- ", line)
        result.append(line)

    return "\n".join(result)


def create_pdf_bytes(title: str, content: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

    x = 50
    y = height - 50

    c.setFont("HYSMyeongJo-Medium", 16)
    c.drawString(x, y, title)
    y -= 30

    c.setFont("HYSMyeongJo-Medium", 11)

    plain_text = markdown_to_plain_text(content)
    max_chars = 55

    lines = []
    for paragraph in plain_text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue

        while len(paragraph) > max_chars:
            lines.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        lines.append(paragraph)

    for line in lines:
        if y < 50:
            c.showPage()
            c.setFont("HYSMyeongJo-Medium", 11)
            y = height - 50

        c.drawString(x, y, line)
        y -= 18

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ------------------- 사이드바 -------------------
st.sidebar.title("과목 관리")

new_subject = st.sidebar.text_input("새 과목 이름")

if st.sidebar.button("과목 추가"):
    subject_name = sanitize_name(new_subject)
    if not subject_name:
        st.sidebar.warning("과목명을 입력하세요.")
    elif subject_name in st.session_state.subjects:
        st.sidebar.warning("이미 존재하는 과목입니다.")
    else:
        st.session_state.subjects.append(subject_name)
        st.session_state.subjects.sort()
        ensure_subject_dir(subject_name)
        st.session_state.selected_subject = subject_name
        st.session_state.selected_file = None
        st.sidebar.success(f"{subject_name} 과목이 추가되었습니다.")
        st.rerun()

selected_subject = st.sidebar.selectbox(
    "과목 선택",
    st.session_state.subjects,
    index=st.session_state.subjects.index(st.session_state.selected_subject)
)
st.session_state.selected_subject = selected_subject

if st.sidebar.button("현재 과목 삭제"):
    if len(st.session_state.subjects) == 1:
        st.sidebar.error("마지막 과목은 삭제할 수 없습니다.")
    else:
        delete_subject(selected_subject)
        st.session_state.subjects.remove(selected_subject)
        st.session_state.selected_subject = st.session_state.subjects[0]
        st.session_state.selected_file = None
        st.session_state.edit_mode = False
        st.sidebar.success(f"{selected_subject} 과목이 삭제되었습니다.")
        st.rerun()


# ------------------- 메인 -------------------
st.title("필기 정리 사이트")
st.caption(f"현재 과목: {selected_subject}")

subject_dir = ensure_subject_dir(selected_subject)
files = get_subject_files(selected_subject)

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("파일 리스트")

    if not files:
        st.info("이 과목에는 아직 파일이 없습니다.")
    else:
        for file_path in files:
            if st.button(file_path.name, key=f"{selected_subject}_{file_path.name}"):
                st.session_state.selected_file = file_path.name
                st.session_state.edit_mode = False
                st.rerun()

with right:
    tab1, tab2 = st.tabs(["파일 업로드", "파일 보기/수정"])

    with tab1:
        st.subheader("정리된 TXT 파일 업로드")

        uploaded_file = st.file_uploader("TXT 업로드", type=["txt"])

        if uploaded_file is not None:
            uploaded_content = uploaded_file.read().decode("utf-8")
            default_name = Path(uploaded_file.name).stem
            custom_name = st.text_input("저장할 파일 이름", value=default_name)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 미리보기")
                st.markdown(uploaded_content)

            with col2:
                st.markdown("### 원본")
                st.text(uploaded_content)

            if st.button("이 과목에 저장"):
                clean_name = sanitize_name(custom_name)
                if not clean_name:
                    st.warning("파일 이름을 입력하세요.")
                else:
                    filename = f"{clean_name}.txt"
                    file_path = subject_dir / filename
                    write_file(file_path, uploaded_content)
                    st.session_state.selected_file = filename
                    st.success(f"{filename} 저장 완료")
                    st.rerun()

    with tab2:
        st.subheader("파일 보기 / 수정")

        if not st.session_state.selected_file:
            st.info("왼쪽에서 파일을 선택하세요.")
        else:
            current_path = subject_dir / st.session_state.selected_file

            if not current_path.exists():
                st.warning("선택한 파일이 존재하지 않습니다.")
            else:
                current_content = read_file(current_path)

                top1, top2, top3, top4 = st.columns([1, 1, 1, 1])

                with top1:
                    st.download_button(
                        "TXT 다운로드",
                        data=current_content,
                        file_name=current_path.name,
                        mime="text/plain"
                    )

                with top2:
                    pdf_bytes = create_pdf_bytes(current_path.stem, current_content)
                    st.download_button(
                        "PDF 다운로드",
                        data=pdf_bytes,
                        file_name=f"{current_path.stem}.pdf",
                        mime="application/pdf"
                    )

                with top3:
                    if st.button("파일 수정"):
                        st.session_state.edit_mode = True
                        st.rerun()

                with top4:
                    if st.button("파일 삭제"):
                        delete_file(current_path)
                        st.session_state.selected_file = None
                        st.session_state.edit_mode = False
                        st.success("파일이 삭제되었습니다.")
                        st.rerun()

                st.markdown("---")

                if st.session_state.edit_mode:
                    st.markdown("### 파일 수정 중")

                    with st.form("edit_form"):
                        new_title = st.text_input("파일 제목", value=current_path.stem)
                        new_content = st.text_area("내용 수정", value=current_content, height=400)
                        save_edit = st.form_submit_button("수정 저장")

                    if save_edit:
                        clean_title = sanitize_name(new_title)
                        if not clean_title:
                            st.warning("파일 제목을 입력하세요.")
                        elif not new_content.strip():
                            st.warning("내용을 입력하세요.")
                        else:
                            new_filename = f"{clean_title}.txt"
                            new_path = subject_dir / new_filename

                            if new_path != current_path and current_path.exists():
                                current_path.unlink()

                            write_file(new_path, new_content)
                            st.session_state.selected_file = new_filename
                            st.session_state.edit_mode = False
                            st.success("파일이 수정되었습니다.")
                            st.rerun()

                else:
                    st.markdown(current_content)
                    st.markdown("---")
                    with st.expander("원본 텍스트 보기"):
                        st.text(current_content)
