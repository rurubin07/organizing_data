import io
import re
from pathlib import Path

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="필기 정리 사이트", layout="wide")

BASE_DIR = Path("notes")
BASE_DIR.mkdir(exist_ok=True)

DEFAULT_SUBJECTS = ["인간학", "자료구조", "운영체제"]

if "subjects" not in st.session_state:
    st.session_state.subjects = DEFAULT_SUBJECTS.copy()

if "selected_subject" not in st.session_state:
    st.session_state.selected_subject = st.session_state.subjects[0]

if "selected_file" not in st.session_state:
    st.session_state.selected_file = None


# -----------------------------
# 유틸
# -----------------------------
def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name


def ensure_subject_dir(subject: str) -> Path:
    subject_dir = BASE_DIR / subject
    subject_dir.mkdir(parents=True, exist_ok=True)
    return subject_dir


def get_txt_files(subject: str):
    subject_dir = ensure_subject_dir(subject)
    return sorted(subject_dir.glob("*.txt"), key=lambda p: p.name.lower())


def save_text_file(subject: str, filename: str, content: str):
    subject_dir = ensure_subject_dir(subject)
    file_path = subject_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def markdown_to_plain_text(md: str) -> str:
    lines = md.splitlines()
    cleaned = []

    for line in lines:
        line = re.sub(r"^#{1,6}\s*", "", line)   # 제목 제거
        line = re.sub(r"^\-\s*", "• ", line)     # bullet 변환
        line = re.sub(r"^\d+\.\s*", "- ", line)  # 숫자목록 변환
        cleaned.append(line)

    return "\n".join(cleaned)


def create_pdf_bytes(title: str, content: str) -> bytes:
    """
    한글 PDF 생성을 위해 ReportLab CID 폰트 사용.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 한글 폰트 등록
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

    margin_x = 50
    y = height - 50

    # 제목
    c.setFont("HYSMyeongJo-Medium", 16)
    c.drawString(margin_x, y, title)
    y -= 30

    # 본문
    c.setFont("HYSMyeongJo-Medium", 11)
    plain_text = markdown_to_plain_text(content)

    max_chars = 55  # 대충 줄바꿈 기준
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

        c.drawString(margin_x, y, line)
        y -= 18

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.title("과목 관리")

new_subject = st.sidebar.text_input("새 과목 이름")
if st.sidebar.button("과목 추가"):
    subject_name = new_subject.strip()
    if not subject_name:
        st.sidebar.warning("과목명을 입력하세요.")
    elif subject_name in st.session_state.subjects:
        st.sidebar.warning("이미 있는 과목입니다.")
    else:
        st.session_state.subjects.append(subject_name)
        ensure_subject_dir(subject_name)
        st.session_state.selected_subject = subject_name
        st.sidebar.success(f"'{subject_name}' 과목이 추가되었습니다.")
        st.rerun()

selected_subject = st.sidebar.selectbox(
    "과목 선택",
    st.session_state.subjects,
    index=st.session_state.subjects.index(st.session_state.selected_subject)
)
st.session_state.selected_subject = selected_subject


# -----------------------------
# 메인 헤더
# -----------------------------
st.title("필기 정리 사이트")
st.caption(f"현재 과목: {selected_subject}")

subject_dir = ensure_subject_dir(selected_subject)
files = get_txt_files(selected_subject)

left, right = st.columns([1, 2], gap="large")


# -----------------------------
# 왼쪽: 파일 리스트
# -----------------------------
with left:
    st.subheader("파일 리스트")

    if not files:
        st.info("이 과목에는 아직 파일이 없습니다.")
    else:
        for file_path in files:
            if st.button(file_path.name, key=f"file_{selected_subject}_{file_path.name}"):
                st.session_state.selected_file = file_path.name
                st.rerun()


# -----------------------------
# 오른쪽: 탭
# -----------------------------
with right:
    tab1, tab2, tab3 = st.tabs(["새 파일 만들기", "파일 업로드", "파일 보기"])

    # 새 파일 만들기
    with tab1:
        st.subheader("새 TXT 파일 만들기")

        with st.form("create_note_form"):
            title = st.text_input("파일 제목")
            content = st.text_area(
                "내용 입력",
                height=350,
                placeholder="# 제목\n\n## 핵심 개념\n- 내용 1\n- 내용 2"
            )
            submitted = st.form_submit_button("저장")

        if submitted:
            clean_title = sanitize_filename(title)
            if not clean_title:
                st.warning("파일 제목을 입력하세요.")
            elif not content.strip():
                st.warning("내용을 입력하세요.")
            else:
                filename = f"{clean_title}.txt"
                save_text_file(selected_subject, filename, content)
                st.session_state.selected_file = filename
                st.success(f"{filename} 저장 완료")
                st.rerun()

    # 파일 업로드
    with tab2:
        st.subheader("정리된 TXT 업로드")

        uploaded_file = st.file_uploader("TXT 파일 업로드", type=["txt"])

        if uploaded_file is not None:
            uploaded_content = uploaded_file.read().decode("utf-8")
            default_name = Path(uploaded_file.name).stem
            custom_name = st.text_input("저장할 파일 이름", value=default_name, key="upload_name")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 미리보기")
                st.markdown(uploaded_content)

            with col2:
                st.markdown("### 원본")
                st.text(uploaded_content)

            if st.button("이 과목에 저장", key="save_uploaded"):
                clean_name = sanitize_filename(custom_name)
                if not clean_name:
                    st.warning("파일 이름을 입력하세요.")
                else:
                    filename = f"{clean_name}.txt"
                    save_text_file(selected_subject, filename, uploaded_content)
                    st.session_state.selected_file = filename
                    st.success(f"{filename} 저장 완료")
                    st.rerun()

    # 파일 보기
    with tab3:
        st.subheader("파일 보기")

        if not st.session_state.selected_file:
            st.info("왼쪽 파일 리스트에서 파일을 선택하세요.")
        else:
            current_path = subject_dir / st.session_state.selected_file

            if not current_path.exists():
                st.warning("선택한 파일이 존재하지 않습니다.")
            else:
                file_content = read_text_file(current_path)

                top1, top2, top3 = st.columns([1, 1, 4])

                with top1:
                    st.download_button(
                        label="TXT 다운로드",
                        data=file_content,
                        file_name=current_path.name,
                        mime="text/plain"
                    )

                with top2:
                    pdf_bytes = create_pdf_bytes(current_path.stem, file_content)
                    st.download_button(
                        label="PDF 다운로드",
                        data=pdf_bytes,
                        file_name=f"{current_path.stem}.pdf",
                        mime="application/pdf"
                    )

                st.markdown("---")
                st.markdown(file_content)
                st.markdown("---")
                with st.expander("원본 텍스트 보기"):
                    st.text(file_content)
