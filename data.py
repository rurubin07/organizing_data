import io
import re
import sqlite3
from datetime import datetime

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="필기 정리 사이트", layout="wide")
DB_PATH = "notes.db"


# -----------------------------
# DB 연결 / 초기화
# -----------------------------
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)

    conn.commit()

    # 기본 과목
    default_subjects = ["인간학", "자료구조", "운영체제"]
    for subject in default_subjects:
        try:
            cur.execute("INSERT INTO subjects (name) VALUES (?)", (subject,))
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# 세션 상태
# -----------------------------
if "selected_subject_id" not in st.session_state:
    st.session_state.selected_subject_id = None

if "selected_note_id" not in st.session_state:
    st.session_state.selected_note_id = None

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False


# -----------------------------
# 유틸 함수
# -----------------------------
def sanitize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name


def remove_emoji(text: str) -> str:
    return re.sub(r"[^\u0000-\uFFFF]", "", text)


def markdown_to_plain_text(md: str) -> str:
    md = remove_emoji(md)
    lines = md.splitlines()
    result = []

    for line in lines:
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^\-\s*", "• ", line)
        line = re.sub(r"^\d+\.\s*", "- ", line)
        result.append(line)

    return "\n".join(result)


def split_long_line(text: str, max_chars: int = 55):
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    lines.append(text)
    return lines


def create_pdf_bytes(title: str, content: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

    x = 50
    y = height - 50

    safe_title = remove_emoji(title)
    safe_content = markdown_to_plain_text(content)

    c.setFont("HYSMyeongJo-Medium", 16)
    c.drawString(x, y, safe_title)
    y -= 30

    c.setFont("HYSMyeongJo-Medium", 11)

    lines = []
    for paragraph in safe_content.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(split_long_line(paragraph, max_chars=55))

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


# -----------------------------
# DB 함수
# -----------------------------
def get_subjects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM subjects ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_subject(name: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def delete_subject(subject_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE subject_id = ?", (subject_id,))
    cur.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()


def get_notes_by_subject(subject_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, updated_at
        FROM notes
        WHERE subject_id = ?
        ORDER BY updated_at DESC
    """, (subject_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_note(note_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, subject_id, title, content, created_at, updated_at
        FROM notes
        WHERE id = ?
    """, (note_id,))
    row = cur.fetchone()
    conn.close()
    return row


def add_note(subject_id: int, title: str, content: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notes (subject_id, title, content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (subject_id, title, content, now, now))
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return note_id


def update_note(note_id: int, new_title: str, new_content: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE notes
        SET title = ?, content = ?, updated_at = ?
        WHERE id = ?
    """, (new_title, new_content, now, note_id))
    conn.commit()
    conn.close()


def delete_note(note_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()


# -----------------------------
# 초기 선택값 보정
# -----------------------------
subjects = get_subjects()

if subjects and st.session_state.selected_subject_id is None:
    st.session_state.selected_subject_id = subjects[0][0]


# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.title("과목 관리")

new_subject = st.sidebar.text_input("새 과목 이름")

if st.sidebar.button("과목 추가"):
    subject_name = sanitize_name(new_subject)
    if not subject_name:
        st.sidebar.warning("과목명을 입력하세요.")
    else:
        add_subject(subject_name)
        subjects = get_subjects()
        matched = [s for s in subjects if s[1] == subject_name]
        if matched:
            st.session_state.selected_subject_id = matched[0][0]
        st.session_state.selected_note_id = None
        st.sidebar.success(f"{subject_name} 과목이 추가되었습니다.")
        st.rerun()

subjects = get_subjects()

if not subjects:
    st.error("과목이 없습니다.")
    st.stop()

subject_names = [s[1] for s in subjects]
subject_ids = [s[0] for s in subjects]

current_index = 0
if st.session_state.selected_subject_id in subject_ids:
    current_index = subject_ids.index(st.session_state.selected_subject_id)

selected_subject_name = st.sidebar.selectbox(
    "과목 선택",
    subject_names,
    index=current_index
)

selected_subject_id = subjects[subject_names.index(selected_subject_name)][0]
st.session_state.selected_subject_id = selected_subject_id

if st.sidebar.button("현재 과목 삭제"):
    if len(subjects) == 1:
        st.sidebar.error("마지막 과목은 삭제할 수 없습니다.")
    else:
        delete_subject(selected_subject_id)
        subjects = get_subjects()
        st.session_state.selected_subject_id = subjects[0][0]
        st.session_state.selected_note_id = None
        st.session_state.edit_mode = False
        st.sidebar.success(f"{selected_subject_name} 과목이 삭제되었습니다.")
        st.rerun()


# -----------------------------
# 메인 화면
# -----------------------------
st.title("필기 정리 사이트")
st.caption(f"현재 과목: {selected_subject_name}")

notes = get_notes_by_subject(selected_subject_id)

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("파일 리스트")

    if not notes:
        st.info("이 과목에는 아직 저장된 파일이 없습니다.")
    else:
        for note_id, note_title, updated_at in notes:
            label = f"{note_title}\n({updated_at})"
            if st.button(label, key=f"note_{note_id}"):
                st.session_state.selected_note_id = note_id
                st.session_state.edit_mode = False
                st.rerun()

with right:
    tab1, tab2 = st.tabs(["파일 업로드", "파일 보기/수정"])

    with tab1:
        st.subheader("정리된 TXT 파일 업로드")

        uploaded_file = st.file_uploader("TXT 업로드", type=["txt"])

        if uploaded_file is not None:
            uploaded_content = uploaded_file.read().decode("utf-8")
            default_name = sanitize_name(uploaded_file.name.rsplit(".", 1)[0])
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
                    note_id = add_note(selected_subject_id, clean_name, uploaded_content)
                    st.session_state.selected_note_id = note_id
                    st.success(f"{clean_name} 저장 완료")
                    st.rerun()

    with tab2:
        st.subheader("파일 보기 / 수정")

        if not st.session_state.selected_note_id:
            st.info("왼쪽에서 파일을 선택하세요.")
        else:
            note = get_note(st.session_state.selected_note_id)

            if note is None:
                st.warning("선택한 파일이 존재하지 않습니다.")
            else:
                note_id, subject_id, title, content, created_at, updated_at = note

                st.caption(f"생성: {created_at} | 수정: {updated_at}")

                top1, top2, top3, top4 = st.columns([1, 1, 1, 1])

                with top1:
                    st.download_button(
                        "TXT 다운로드",
                        data=content,
                        file_name=f"{title}.txt",
                        mime="text/plain"
                    )

                with top2:
                    pdf_bytes = create_pdf_bytes(title, content)
                    st.download_button(
                        "PDF 다운로드",
                        data=pdf_bytes,
                        file_name=f"{remove_emoji(title)}.pdf",
                        mime="application/pdf"
                    )

                with top3:
                    if st.button("파일 수정"):
                        st.session_state.edit_mode = True
                        st.rerun()

                with top4:
                    if st.button("파일 삭제"):
                        delete_note(note_id)
                        st.session_state.selected_note_id = None
                        st.session_state.edit_mode = False
                        st.success("파일이 삭제되었습니다.")
                        st.rerun()

                st.markdown("---")

                if st.session_state.edit_mode:
                    st.markdown("### 파일 수정 중")

                    with st.form("edit_form"):
                        new_title = st.text_input("파일 제목", value=title)
                        new_content = st.text_area("내용 수정", value=content, height=400)
                        save_edit = st.form_submit_button("수정 저장")

                    if save_edit:
                        clean_title = sanitize_name(new_title)
                        if not clean_title:
                            st.warning("파일 제목을 입력하세요.")
                        elif not new_content.strip():
                            st.warning("내용을 입력하세요.")
                        else:
                            update_note(note_id, clean_title, new_content)
                            st.session_state.edit_mode = False
                            st.success("파일이 수정되었습니다.")
                            st.rerun()

                else:
                    st.markdown(content)
                    st.markdown("---")
                    with st.expander("원본 텍스트 보기"):
                        st.text(content)
