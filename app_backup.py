import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 설정 및 API 키 ---
# ★★★ 여기에 구글 AI Studio API 키를 입력하세요 ★★★
GOOGLE_API_KEY = "AIzaSyCEzcvhvEin06LYS9BPF5gBUUiH6giy-sI"
genai.configure(api_key=GOOGLE_API_KEY)

# 사용할 모델 설정 (이미지 생성 능력이 있는 최신 모델)
MODEL_NAME = 'gemini-3-pro-image-preview' # 또는 'gemini-1.5-pro' 등

# --- 2. 언어별 프롬프트 정의 ---
PROMPTS = {
    "인도네시아어": "Translate all visible text to Indonesian (Bahasa Indonesia). Preserve exact layout and text box size. If text overflows, drop articles or condense phrasing. Do not alter non-text elements.",
    "힌디어": "Translate all visible text to Hindi (Devanagari script). Preserve exact layout and text box size. Ensure proper character rendering. Do not alter non-text elements.",
    "중국어 간체": "Translate all visible text to Simplified Chinese (简体中文). Preserve exact layout and text box size. Do not alter non-text elements.",
    "중국어 번체": "Translate all visible text to Traditional Chinese (繁體中文). Preserve exact layout and text box size. Do not alter non-text elements.",
    "독일어": "Translate all visible text to German. Text expands ~40%: drop articles (der/die/das), use abbreviations, or condense compound words to fit original text box exactly. Do not alter non-text elements.",
    "프랑스어": "Translate all visible text to French. Text expands ~30%: drop articles (le/la/les), use shorter synonyms to fit original text box exactly. Do not alter non-text elements.",
    "스페인어": "Translate all visible text to Spanish. Text expands ~25%: drop articles (el/la/los), use shorter words to fit original text box exactly. Do not alter non-text elements.",
    "이탈리아어": "Translate all visible text to Italian. Text expands ~25%: drop articles (il/la/i/le), condense phrasing to fit original text box exactly. Do not alter non-text elements.",
    "포르투갈어": "Translate all visible text to Brazilian Portuguese. Text expands ~30%: drop articles (o/a/os/as), use abbreviations to fit original text box exactly. Do not alter non-text elements.",
    "베트남어": "Translate all visible text to Vietnamese with correct diacritics (ă, ơ, ư). Condense phrasing to fit original text box exactly. Do not alter non-text elements.",
    "태국어": "Translate all visible text to Thai with correct tone marks and vowel positioning. Preserve exact layout and text box size. Thai is typically compact; if text overflows, use shorter synonyms or drop particles (ครับ/ค่ะ). Do not alter non-text elements.",
    "말레이어": "Translate all visible text to Malay (Bahasa Melayu). Preserve exact layout and text box size. If text overflows, drop articles or condense phrasing. Do not alter non-text elements."
}

# --- 3. 헬퍼 함수 ---
def create_thumbnail(image_file, size=(500, 500)):
    """화면 표시용 썸네일 이미지를 생성합니다."""
    img = Image.open(image_file)
    img.thumbnail(size)
    return img

# --- 4. Streamlit UI 구성 ---
st.set_page_config(page_title="Gemini 배치 이미지 번역기", layout="wide")
st.title("🖼️ Gemini 멀티 이미지/언어 번역기")

# 세션 상태 초기화 (업로드된 이미지와 결과물 관리를 위해)
if 'uploaded_files_list' not in st.session_state:
    st.session_state.uploaded_files_list = []
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = []

# --- 사이드바: 설정 ---
with st.sidebar:
    st.header("🛠️ 설정")
    
    # 4-1. 언어 다중 선택
    selected_languages = st.multiselect(
        "번역할 언어 선택 (다중 선택 가능)",
        options=list(PROMPTS.keys()),
        default=["프랑스어"], # 기본값 설정
        help="여러 언어를 선택하면 한 번에 모두 번역합니다."
    )

    # 4-2. 다중 이미지 업로드
    uploaded_files = st.file_uploader(
        "이미지 업로드 (다중 선택 가능)",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="여러 이미지를 드래그 앤 드롭하거나 선택하세요."
    )
    
    # 업로드된 파일 세션 상태에 추가 (중복 방지)
    if uploaded_files:
        for file in uploaded_files:
            if file not in st.session_state.uploaded_files_list:
                st.session_state.uploaded_files_list.append(file)

    st.divider()
    st.info(f"현재 선택된 언어: {len(selected_languages)}개\n대기 중인 이미지: {len(st.session_state.uploaded_files_list)}장")


# --- 메인 영역: 입력 이미지 관리 ---
st.header("1️⃣ 입력 이미지 확인 및 관리")

if not st.session_state.uploaded_files_list:
    st.info("사이드바에서 이미지를 업로드해주세요.")
else:
    # 썸네일 박스 UI로 보여주기
    cols = st.columns(4) # 한 줄에 4개씩 표시
    for i, file in enumerate(st.session_state.uploaded_files_list):
        col = cols[i % 4]
        with col:
            # 500px 썸네일 생성 및 표시
            thumb = create_thumbnail(file)
            st.image(thumb, caption=file.name, use_container_width=True)
            # 삭제 버튼 (고유 키 필요)
            if st.button(f"🗑️ 삭제", key=f"del_{i}"):
                st.session_state.uploaded_files_list.pop(i)
                st.rerun() # 상태 변경 후 즉시 화면 갱신

st.divider()

# --- 메인 영역: 번역 실행 및 결과 ---
st.header("2️⃣ 번역 실행 및 결과 다운로드")

# 번역 시작 버튼
if st.button("🚀 일괄 번역 시작", type="primary", disabled=not (st.session_state.uploaded_files_list and selected_languages)):
    
    # 결과 초기화 (새로운 작업 시작 시)
    st.session_state.processing_results = []
    
    total_tasks = len(st.session_state.uploaded_files_list) * len(selected_languages)
    progress_bar = st.progress(0)
    status_text = st.empty()
    task_count = 0

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        # [중요] 이중 반복문으로 배치 처리 (이미지 X 언어)
        for file in st.session_state.uploaded_files_list:
            original_image = Image.open(file)
            for lang in selected_languages:
                task_count += 1
                status_text.text(f"진행 중... ({task_count}/{total_tasks}): '{file.name}' → {lang}")
                progress_bar.progress(task_count / total_tasks)
                
                try:
                    # API 호출 (캐싱 없음, 매번 새로 호출)
                    prompt = PROMPTS[lang] + " Output the result as an image exactly."
                    response = model.generate_content([prompt, original_image])
                    
                    # 이미지 데이터 추출
                    if response.candidates[0].content.parts[0].inline_data:
                        img_bytes = response.candidates[0].content.parts[0].inline_data.data
                        # 결과 저장 (원본 파일명, 언어, 이미지 바이너리 데이터)
                        st.session_state.processing_results.append({
                            "origin_name": file.name,
                            "lang": lang,
                            "data": img_bytes
                        })
                    else:
                        st.error(f"오류 ({file.name} - {lang}): 모델이 이미지를 반환하지 않았습니다. 텍스트 응답: {response.text}")
                        
                except Exception as e:
                    st.error(f"처리 실패 ({file.name} - {lang}): {e}")

        status_text.success("✅ 모든 작업이 완료되었습니다! 아래에서 결과를 확인하세요.")
        progress_bar.empty()

    except Exception as e:
        st.error(f"모델 초기화 오류: {e}")

# --- 결과 표시 영역 ---
if st.session_state.processing_results:
    st.subheader(f"총 {len(st.session_state.processing_results)}개의 번역 결과")
    
    # 결과 그리드로 표시
    res_cols = st.columns(3) # 한 줄에 3개씩
    for i, res in enumerate(st.session_state.processing_results):
        col = res_cols[i % 3]
        with col:
            # 바이너리 데이터에서 이미지 열기 (화면 표시용)
            result_img = Image.open(io.BytesIO(res['data']))
            st.image(result_img, caption=f"{res['lang']} - {res['origin_name']}", use_container_width=True)
            
            # 다운로드 버튼 생성 (파일명 지정, 원본 해상도 유지)
            file_name_only = res['origin_name'].split('.')[0]
            download_name = f"{file_name_only}_{res['lang']}.png"
            
            st.download_button(
                label=f"📥 {download_name} 다운로드",
                data=res['data'], # API가 준 원본 바이너리 데이터를 그대로 사용
                file_name=download_name,
                mime="image/png",
                key=f"down_{i}"
            )