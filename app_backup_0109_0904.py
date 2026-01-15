import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import zipfile
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 1. 설정 및 API 키 ---
GOOGLE_API_KEY = "AIzaSyCEzcvhvEin06LYS9BPF5gBUUiH6giy-sI"
genai.configure(api_key=GOOGLE_API_KEY)

# 모델 설정: Nano Banana Pro (Gemini 3 Pro Image Preview)
MODEL_NAME = 'gemini-3-pro-image-preview'

# --- 2. 언어별 프롬프트 정의 ---
COMMON_INSTRUCTION = (
    "Output the result as a high-quality image. Preserve the exact original colors and layout. "
    "Replace only the text. Do not render any checkerboard patterns for transparent areas."
)

PROMPTS = {
    "인도네시아어": "Translate all visible text to Indonesian (Bahasa Indonesia).",
    "힌디어": "Translate all visible text to Hindi (Devanagari script).",
    "중국어 간체": "Translate all visible text to Simplified Chinese (简体中文).",
    "중국어 번체": "Translate all visible text to Traditional Chinese (繁體中文).",
    "독일어": "Translate all visible text to German.",
    "프랑스어": "Translate all visible text to French.",
    "스페인어": "Translate all visible text to Spanish.",
    "이탈리아어": "Translate all visible text to Italian.",
    "포르투갈어": "Translate all visible text to Brazilian Portuguese.",
    "베트남어": "Translate all visible text to Vietnamese.",
    "태국어": "Translate all visible text to Thai.",
    "말레이어": "Translate all visible text to Malay (Bahasa Melayu)."
}

# --- 3. 헬퍼 함수 ---
def create_thumbnail(image_file, size=(500, 500)):
    img = Image.open(image_file)
    img.thumbnail(size)
    return img

def restore_transparency(original_img, generated_img_bytes):
    """
    원본 이미지의 투명도(Alpha)를 생성된 이미지에 다시 적용하여 
    AI가 생성한 체크무늬 배경을 제거합니다.
    """
    gen_img = Image.open(io.BytesIO(generated_img_bytes)).convert("RGBA")
    
    # 생성된 이미지를 원본 크기에 맞게 조정 (AI가 크기를 미세하게 바꿀 수 있음)
    gen_img = gen_img.resize(original_img.size, Image.Resampling.LANCZOS)
    
    if original_img.mode == 'RGBA':
        # 원본에서 알파 채널(투명도)만 추출
        r, g, b, a = original_img.split()
        # 생성된 이미지의 RGB와 원본의 Alpha를 결합
        gen_r, gen_g, gen_b, _ = gen_img.split()
        final_img = Image.merge("RGBA", (gen_r, gen_g, gen_b, a))
    else:
        final_img = gen_img

    # 결과 저장
    png_buffer = io.BytesIO()
    final_img.save(png_buffer, format='PNG', optimize=True)
    return png_buffer.getvalue()

def toggle_all_languages():
    new_state = st.session_state.select_all_key
    for lang in PROMPTS.keys():
        st.session_state[f"lang_{lang}"] = new_state

# --- 4. Streamlit UI 구성 ---
st.set_page_config(page_title="Gemini 배치 이미지 번역기", layout="wide")

# CSS 스타일 추가
st.markdown("""
    <style>
    /* 텍스트 입력 필드 라벨 크기 키우기 */
    [data-testid="stTextInput"] label p {
        font-size: 18px !important;
        font-weight: 600 !important;
    }
    
    /* 번역 버튼 너비 고정 */
    [data-testid="stBaseButton-primary"] {
        width: 136px !important;
        min-width: 136px !important;
        max-width: 136px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("글로벌 이미지 번역기")

if 'processing_results' not in st.session_state:
    st.session_state.processing_results = []

with st.sidebar:
    st.header("🛠️ 설정")
    st.checkbox("전체 선택", key="select_all_key", on_change=toggle_all_languages)
    
    selected_languages = []
    for lang in PROMPTS.keys():
        if f"lang_{lang}" not in st.session_state:
            st.session_state[f"lang_{lang}"] = (lang == "프랑스어")
        if st.checkbox(lang, key=f"lang_{lang}"):
            selected_languages.append(lang)

    st.divider()
    uploaded_files = st.file_uploader(
        "이미지 업로드", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True
    )

st.header("1️⃣ 번역할 이미지")

if not uploaded_files:
    st.info("사이드바에서 이미지를 업로드해주세요.")
else:
    cols = st.columns(4)
    for i, file in enumerate(uploaded_files):
        with cols[i % 4]:
            st.image(create_thumbnail(file), caption=file.name, use_container_width=True)
            
    st.divider()
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        user_custom_prompt = st.text_input("프롬프트 추가하기", placeholder="예: Do not translate numbers.")
    with col_btn:
        st.write("")  # 버튼을 아래쪽으로 정렬하기 위한 공백
        st.write("")
        start_btn = st.button("🚀 일괄 번역 시작", type="primary", use_container_width=True)

    if start_btn:
        st.session_state.processing_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        try:
            model = genai.GenerativeModel(MODEL_NAME)
            total_tasks = len(uploaded_files) * len(selected_languages)
            task_count = 0

            for file in uploaded_files:
                file.seek(0)
                original_img = Image.open(file).convert("RGBA")
                
                for lang in selected_languages:
                    task_count += 1
                    status_text.text(f"진행 중... ({task_count}/{total_tasks}): {file.name}")
                    progress_bar.progress(task_count / total_tasks)
                    
                    full_prompt = f"{PROMPTS[lang]} {COMMON_INSTRUCTION} {user_custom_prompt}"
                    
                    try:
                        response = model.generate_content([full_prompt, original_img], safety_settings=safety_settings)
                        part = response.candidates[0].content.parts[0]
                        
                        if part.inline_data:
                            # 핵심: 원본의 투명도를 결과물에 다시 씌움
                            final_bytes = restore_transparency(original_img, part.inline_data.data)
                            st.session_state.processing_results.append({
                                "origin_name": file.name, "lang": lang, "data": final_bytes
                            })
                    except Exception as e:
                        st.error(f"실패: {file.name} - {e}")

            status_text.success("✅ 번역 및 투명도 복원 완료!")
        except Exception as e:
            st.error(f"오류: {e}")

st.divider()
st.header("2️⃣ 번역된 이미지 다운로드")

if st.session_state.processing_results:
    # ZIP 다운로드 및 그리드 표시 로직 (기존과 동일)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for res in st.session_state.processing_results:
            zf.writestr(f"{res['origin_name']}_{res['lang']}.png", res['data'])
    
    st.download_button("📦 전체 다운로드 (ZIP)", zip_buffer.getvalue(), "results.zip", "application/zip")
    
    res_cols = st.columns(3)
    for i, res in enumerate(st.session_state.processing_results):
        with res_cols[i % 3]:
            st.image(Image.open(io.BytesIO(res['data'])), caption=f"{res['lang']} - {res['origin_name']}", use_container_width=True)
            st.download_button("📥 다운로드", res['data'], f"{res['lang']}_{res['origin_name']}.png", "image/png", key=f"dl_{i}")