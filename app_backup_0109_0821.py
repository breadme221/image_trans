import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import zipfile
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 1. 설정 및 API 키 ---
# ★★★ 여기에 구글 AI Studio API 키를 입력하세요 ★★★
GOOGLE_API_KEY = "AIzaSyCEzcvhvEin06LYS9BPF5gBUUiH6giy-sI"
genai.configure(api_key=GOOGLE_API_KEY)

# 모델 설정: Nano Banana Pro (Gemini 3 Pro Image Preview)
MODEL_NAME = 'gemini-3-pro-image-preview'

# --- 2. 언어별 프롬프트 정의 ---
# 공통 지시사항: 배경 유지 및 고품질 출력 강조
COMMON_INSTRUCTION = "Output the result as a high-quality image. Preserve the exact original background, colors, and layout. Only replace the text."

PROMPTS = {
    "인도네시아어": "Translate all visible text to Indonesian (Bahasa Indonesia).",
    "힌디어": "Translate all visible text to Hindi (Devanagari script). Ensure proper character rendering.",
    "중국어 간체": "Translate all visible text to Simplified Chinese (简体中文).",
    "중국어 번체": "Translate all visible text to Traditional Chinese (繁體中文).",
    "독일어": "Translate all visible text to German. Text expands ~40%: drop articles or condense words.",
    "프랑스어": "Translate all visible text to French. Text expands ~30%: drop articles or use synonyms.",
    "스페인어": "Translate all visible text to Spanish. Text expands ~25%: drop articles.",
    "이탈리아어": "Translate all visible text to Italian. Text expands ~25%: condense phrasing.",
    "포르투갈어": "Translate all visible text to Brazilian Portuguese. Text expands ~30%: use abbreviations.",
    "베트남어": "Translate all visible text to Vietnamese with correct diacritics.",
    "태국어": "Translate all visible text to Thai. Preserve exact layout.",
    "말레이어": "Translate all visible text to Malay (Bahasa Melayu)."
}

# --- 3. 헬퍼 함수 ---
def create_thumbnail(image_file, size=(500, 500)):
    """화면 표시용 썸네일 이미지를 생성합니다."""
    img = Image.open(image_file)
    img.thumbnail(size)
    return img

def process_image_bytes(img_bytes):
    """이미지 바이트를 받아 PNG 형식으로 정리하여 반환합니다."""
    img = Image.open(io.BytesIO(img_bytes))
    png_buffer = io.BytesIO()
    img.save(png_buffer, format='PNG', optimize=True)
    return png_buffer.getvalue()

def toggle_all_languages():
    """전체 선택 체크박스 상태에 따라 개별 언어 체크박스를 동기화합니다."""
    new_state = st.session_state.select_all_key
    for lang in PROMPTS.keys():
        st.session_state[f"lang_{lang}"] = new_state

# --- 4. Streamlit UI 구성 ---
st.set_page_config(page_title="Gemini 배치 이미지 번역기 (Nano Banana Pro)", layout="wide")
st.title("글로벌 이미지 번역기")

if 'processing_results' not in st.session_state:
    st.session_state.processing_results = []

# --- 사이드바: 설정 ---
with st.sidebar:
    st.header("🛠️ 설정")
    
    # 4-1. 언어 다중 선택
    st.subheader("번역할 언어 선택")
    st.checkbox("전체 선택", key="select_all_key", on_change=toggle_all_languages)
    st.divider()
    
    selected_languages = []
    for lang in PROMPTS.keys():
        if f"lang_{lang}" not in st.session_state:
            st.session_state[f"lang_{lang}"] = (lang == "프랑스어")
        if st.checkbox(lang, key=f"lang_{lang}"):
            selected_languages.append(lang)

    st.divider()

    # 4-2. 다중 이미지 업로드
    uploaded_files = st.file_uploader(
        "이미지 업로드 (다중 선택 가능)",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="이미지를 추가하거나 삭제하려면 위 리스트의 x 버튼을 누르세요."
    )

    st.info(f"현재 선택된 언어: {len(selected_languages)}개\n대기 중인 이미지: {len(uploaded_files) if uploaded_files else 0}장")


# --- 메인 영역 ---
st.header("1️⃣ 번역할 이미지 올리기")

if not uploaded_files:
    st.info("사이드바에서 이미지를 업로드해주세요.")
else:
    # 썸네일 그리드 표시
    cols = st.columns(4)
    for i, file in enumerate(uploaded_files):
        col = cols[i % 4]
        with col:
            thumb = create_thumbnail(file)
            st.image(thumb, caption=file.name, use_container_width=True)
            
    st.divider()

    # [추가됨] 사용자 커스텀 프롬프트 입력창 및 컨트롤 영역
    col_input, col_btn = st.columns([3, 1])
    
    with col_input:
        user_custom_prompt = st.text_input(
            "프롬프트 추가하기 (선택)",
            placeholder="원하는 프롬프트를 추가하세요. (예: The phrase '기존 문장' must be translated exactly as '원하는 문장’)",
            help="여기에 입력한 내용은 모든 이미지와 언어 번역 작업에 공통으로 적용됩니다."
        )
        st.caption("이미지를 삭제하려면 왼쪽 사이드바 파일 목록에서 'X'를 누르세요.")
        
    with col_btn:
        # 버튼을 아래쪽으로 정렬하기 위한 공백
        st.write("") 
        st.write("")
        start_btn = st.button("🚀 일괄 번역 시작", type="primary", use_container_width=True, disabled=not (uploaded_files and selected_languages))

    # --- 번역 실행 로직 ---
    if start_btn:
        st.session_state.processing_results = []
        
        total_tasks = len(uploaded_files) * len(selected_languages)
        progress_bar = st.progress(0)
        status_text = st.empty()
        task_count = 0

        # 안전 설정: 필터 해제
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        try:
            model = genai.GenerativeModel(MODEL_NAME)
            
            for file in uploaded_files:
                file.seek(0)
                original_image = Image.open(file)
                
                for lang in selected_languages:
                    task_count += 1
                    status_text.text(f"진행 중... ({task_count}/{total_tasks}): '{file.name}' → {lang}")
                    progress_bar.progress(task_count / total_tasks)
                    
                    try:
                        # [핵심 수정] 프롬프트 조합: 언어별 프롬프트 + 공통 지시 + 사용자 입력
                        full_prompt = f"{PROMPTS[lang]} {COMMON_INSTRUCTION}"
                        
                        if user_custom_prompt:
                            full_prompt += f" {user_custom_prompt}"
                        
                        response = model.generate_content(
                            [full_prompt, original_image],
                            safety_settings=safety_settings
                        )
                        
                        if not response.candidates:
                            st.warning(f"⚠️ ({file.name} - {lang}): AI 응답 없음 (필터링됨)")
                            continue
                            
                        part = response.candidates[0].content.parts[0]
                        
                        if part.inline_data:
                            img_bytes = part.inline_data.data
                            final_bytes = process_image_bytes(img_bytes)
                            
                            st.session_state.processing_results.append({
                                "origin_name": file.name,
                                "lang": lang,
                                "data": final_bytes
                            })
                        elif part.text:
                            st.warning(f"⚠️ ({file.name} - {lang}): 이미지가 생성되지 않았습니다.")
                        else:
                            st.error(f"❌ ({file.name} - {lang}): 알 수 없는 응답 형식")

                    except Exception as e:
                        st.error(f"❌ 처리 실패 ({file.name} - {lang}): {str(e)}")

            status_text.success("✅ Nano Banana Pro 작업 완료!")
            progress_bar.empty()

        except Exception as e:
            st.error(f"모델 초기화 오류: {e}")

st.divider()

# --- 메인 영역: 결과 확인 ---
st.header("2️⃣ 번역된 이미지 다운로드 ")

if st.session_state.processing_results:
    st.subheader(f"총 {len(st.session_state.processing_results)}개의 번역 결과")
    
    col1, col2 = st.columns([5, 1])
    with col2:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for res in st.session_state.processing_results:
                file_name_only = res['origin_name'].split('.')[0]
                download_name = f"{file_name_only}_{res['lang']}.png"
                zip_file.writestr(download_name, res['data'])
        
        zip_buffer.seek(0)
        st.download_button(
            label="📦 전체 다운로드 (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="translated_images.zip",
            mime="application/zip",
            key="download_all"
        )
    
    res_cols = st.columns(3)
    for i, res in enumerate(st.session_state.processing_results):
        col = res_cols[i % 3]
        with col:
            result_img = Image.open(io.BytesIO(res['data']))
            st.image(result_img, caption=f"{res['lang']} - {res['origin_name']}", use_container_width=True)
            
            file_name_only = res['origin_name'].split('.')[0]
            download_name = f"{file_name_only}_{res['lang']}.png"
            
            st.download_button(
                label="📥 다운로드",
                data=res['data'],
                file_name=download_name,
                mime="image/png",
                key=f"down_{i}"
            )
else:
    st.info("아직 생성된 결과물이 없습니다.")