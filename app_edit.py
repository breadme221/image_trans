import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 설정 및 API 키 ---
GOOGLE_API_KEY = "AIzaSyCEzcvhvEin06LYS9BPF5gBUUiH6giy-sI"
genai.configure(api_key=GOOGLE_API_KEY)
MODEL_NAME = 'gemini-3-pro-image-preview'

# --- 2. 언어별 기본 프롬프트 정의 ---
PROMPTS = {
    "인도네시아어": "Translate all visible text to Indonesian. Preserve layout.",
    "힌디어": "Translate all visible text to Hindi. Preserve layout.",
    "중국어 간체": "Translate all visible text to Simplified Chinese. Preserve layout.",
    "중국어 번체": "Translate all visible text to Traditional Chinese. Preserve layout.",
    "독일어": "Translate all visible text to German. Condense to fit.",
    "프랑스어": "Translate all visible text to French. Condense to fit.",
    "스페인어": "Translate all visible text to Spanish. Condense to fit.",
    "이탈리아어": "Translate all visible text to Italian. Condense to fit.",
    "포르투갈어": "Translate all visible text to Portuguese. Condense to fit.",
    "베트남어": "Translate all visible text to Vietnamese. Preserve layout.",
    "태국어": "Translate all visible text to Thai. Preserve layout.",
    "말레이어": "Translate all visible text to Malay. Preserve layout."
}

# --- 3. 최신 웹 트렌드 스타일 시트 ---
st.set_page_config(page_title="Gemini Translation Studio", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 텍스트 설정 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F9FAFB !important;
        font-family: 'Inter', -apple-system, sans-serif;
        color: #1F2937 !important;
    }

    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
        min-width: 360px !important;
    }

    /* 텍스트 가시성 강제 고정 */
    h1, h2, h3, h4, p, span, label {
        color: #111827 !important;
    }

    /* 버튼 스타일 (Modern Indigo) */
    .stButton>button {
        width: 100%;
        height: 52px; /* 버튼 높이 증가 */
        background-color: #2563EB !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    .stButton>button:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        transform: translateY(-1px);
    }

    /* 삭제/보조 버튼 스타일 */
    [data-testid="stHeader"] + div .stButton>button {
        height: 44px;
        background-color: #FFFFFF !important;
        color: #374151 !important;
        border: 1px solid #D1D5DB !important;
    }
    [data-testid="stHeader"] + div .stButton>button:hover {
        background-color: #F9FAFB !important;
        border-color: #9CA3AF !important;
    }

    /* 카드 UI (300*300) */
    .img-card {
        background: #FFFFFF;
        padding: 16px;
        border-radius: 16px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-bottom: 24px;
    }

    /* 커스텀 프롬프트 박스 스타일 */
    [data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 10px !important;
        color: #111827 !important;
    }

    /* 체크박스 정렬 */
    .stCheckbox label {
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    
    /* 구분선 */
    hr {
        margin: 2rem 0 !important;
        border-top: 1px solid #E5E7EB !important;
    }
    
    /* 파일 업로더 라벨 양끝 정렬 */
    [data-testid="stFileUploader"] label > div[class*="st-emotion-cache-7e7wz2"],
    [data-testid="stFileUploader"] label > div {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        width: 100% !important;
        gap: 8px !important;
    }
    
    [data-testid="stFileUploader"] label > div > p {
        margin: 0 !important;
        flex: 1 !important;
        min-width: 0 !important;
    }
    
    [data-testid="stFileUploader"] label > div > .stTooltipIcon {
        flex-shrink: 0 !important;
        margin-left: auto !important;
    }
    
    /* 파일 업로더 DOM 순서 조정 - 라벨을 두 번째 자식으로 이동 */
    [data-testid="stFileUploader"] {
        display: flex !important;
        flex-direction: column !important;
    }
    
    [data-testid="stFileUploader"] > div[data-testid="stMarkdownContainer"] {
        order: 1 !important;
    }
    
    [data-testid="stFileUploader"] > label[data-testid="stWidgetLabel"] {
        order: 2 !important;
    }
    
    [data-testid="stFileUploader"] > section {
        order: 3 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. 세션 상태 관리 ---
if 'files' not in st.session_state:
    st.session_state.files = []
if 'results' not in st.session_state:
    st.session_state.results = []
if 'file_selections' not in st.session_state:
    st.session_state.file_selections = {}  # 파일명을 키로 하는 선택 상태

# --- 5. 사이드바 구성 ---
with st.sidebar:
    st.markdown("## 🌐 번역 설정")
    
    # 언어 선택 영역 (리스트 형태)
    with st.container():
        st.markdown("#### 언어 선택")
        all_langs = list(PROMPTS.keys())
        select_all = st.checkbox("전체 언어 선택")
        
        selected_langs = []
        # 그리드 형태로 배치하여 공간 절약
        lang_cols = st.columns(2)
        for i, lang in enumerate(all_langs):
            with lang_cols[i % 2]:
                val = select_all if select_all else False
                if st.checkbox(lang, value=val, key=f"lang_{lang}"):
                    selected_langs.append(lang)

    st.markdown("---")
    
    # 커스텀 프롬프트 영역
    st.markdown("#### ✍️ 추가 지침 (Optional)")
    custom_instruction = st.text_area(
        "AI에게 내릴 특별한 명령",
        placeholder="예: Do not Translate number & Time / Use formal tone",
        height=100
    )

    # 하단 배치: 이미지 업로드
    st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 📁 이미지 업로드")
    new_uploads = st.file_uploader(
        "이미지 업로드", 
        type=['png', 'jpg', 'jpeg'], 
        accept_multiple_files=True, 
        label_visibility="collapsed"
    )
    
    if new_uploads:
        for f in new_uploads:
            if f.name not in [exist.name for exist in st.session_state.files]:
                st.session_state.files.append(f)
                # 새로 추가된 파일의 선택 상태 초기화
                st.session_state.file_selections[f.name] = False

# --- 6. 메인 콘텐츠 영역 ---
st.title("🖼️ Gemini Translation Studio")

# 상단 액션 바 (선택 삭제 / 전체 삭제)
col_title, col_actions = st.columns([2, 1])
with col_actions:
    action_cols = st.columns(2)
    with action_cols[0]:
        # 선택된 파일 개수 확인
        selected_count = sum(1 for f in st.session_state.files if st.session_state.file_selections.get(f.name, False))
        if st.button("🗑️ 선택한 이미지 삭제", disabled=selected_count == 0, type="secondary"):
            # 선택된 파일들만 제외하고 나머지 유지
            files_to_keep = [f for f in st.session_state.files if not st.session_state.file_selections.get(f.name, False)]
            st.session_state.files = files_to_keep
            # 삭제된 파일들의 선택 상태도 제거
            for f in list(st.session_state.file_selections.keys()):
                if f not in [file.name for file in st.session_state.files]:
                    del st.session_state.file_selections[f]
            st.rerun()
    with action_cols[1]:
        if st.button("🗑️ 전체 삭제"):
            st.session_state.files = []
            st.session_state.results = []
            st.session_state.file_selections = {}
            st.rerun()

# 업로드 이미지 확인 (300*300 카드 UI)
if st.session_state.files:
    st.markdown("### 1. 업로드된 이미지")
    grid = st.columns(4)
    for idx, f in enumerate(st.session_state.files):
        with grid[idx % 4]:
            st.markdown('<div class="img-card">', unsafe_allow_html=True)
            img = Image.open(f)
            # 300x300 비율을 유지하며 다운사이징
            img.thumbnail((300, 300))
            st.image(img, use_container_width=True)
            # 파일명을 키로 사용하여 체크박스 상태 관리
            file_key = f"img_check_{f.name}"
            checked = st.checkbox("선택", value=st.session_state.file_selections.get(f.name, False), key=file_key)
            st.session_state.file_selections[f.name] = checked
            st.markdown('</div>', unsafe_allow_html=True)

# --- 7. 프롬프트 입력 및 번역 실행 ---
col_input, col_btn = st.columns([3, 1])
with col_input:
    user_custom_prompt = st.text_input(
        "프롬프트 추가하기 (선택)",
        placeholder="원하는 프롬프트를 추가하세요. (예: The phrase '기존 문장' must be translated exactly as '원하는 문장')",
        help="여기에 입력한 내용은 모든 이미지와 언어 번역 작업에 공통으로 적용됩니다."
    )
    st.caption("이미지를 삭제하려면 왼쪽 사이드바 파일 목록에서 'X'를 누르세요.")

with col_btn:
    st.write("")  # 버튼을 아래쪽으로 정렬하기 위한 공백
    st.write("")
    start_btn = st.button(
        "🚀 일괄 번역 시작", 
        type="primary", 
        use_container_width=True,
        disabled=not (st.session_state.files and selected_langs)
    )

if start_btn:
    st.session_state.results = []
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        total = len(st.session_state.files) * len(selected_langs)
        bar = st.progress(0)
        cnt = 0
        
        for f in st.session_state.files:
            orig_img = Image.open(f)
            for lang in selected_langs:
                cnt += 1
                bar.progress(cnt/total)
                
                final_prompt = PROMPTS[lang]
                if custom_instruction:
                    final_prompt += f" Additional instruction: {custom_instruction}"
                if user_custom_prompt:
                    final_prompt += f" Additional instruction: {user_custom_prompt}"
                final_prompt += " Return only the image result."
                
                res = model.generate_content([final_prompt, orig_img])
                
                if res.candidates[0].content.parts[0].inline_data:
                    st.session_state.results.append({
                        "name": f"{f.name.split('.')[0]}_{lang}.png",
                        "data": res.candidates[0].content.parts[0].inline_data.data
                    })
        st.success("✅ 번역이 성공적으로 완료되었습니다!")
    except Exception as e:
        st.error(f"오류: {e}")

# --- 8. 결과 다운로드 영역 ---
if st.session_state.results:
    st.markdown("### 2. 번역 결과물")
    res_grid = st.columns(4)
    for idx, res in enumerate(st.session_state.results):
        with res_grid[idx % 4]:
            st.markdown('<div class="img-card">', unsafe_allow_html=True)
            res_img = Image.open(io.BytesIO(res['data']))
            disp_img = res_img.copy()
            disp_img.thumbnail((300, 300))
            st.image(disp_img, caption=res['name'], use_container_width=True)
            st.download_button(
                "📥 다운로드", 
                data=res['data'], 
                file_name=res['name'], 
                key=f"dl_{idx}"
            )
            st.markdown('</div>', unsafe_allow_html=True)