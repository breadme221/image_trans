import streamlit as st
from openai import OpenAI
from PIL import Image
import io
import base64

# 1. OpenRouter 설정
# 여기에 본인의 OpenRouter API Key를 입력하세요.
OPENROUTER_API_KEY = "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"
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# 2. 언어별 프롬프트 설정 (기존과 동일)
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

# 이미지를 base64로 인코딩하는 함수
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# 3. UI 구성
st.set_page_config(page_title="Global Image Translator", layout="wide")
st.title("🖼️ OpenRouter-Gemini 이미지 번역")

with st.sidebar:
    st.header("설정")
    target_lang = st.selectbox("번역할 언어 선택", list(PROMPTS.keys()))
    uploaded_file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("원본 이미지")
        st.image(image, use_container_width=True)

    if st.button(f"{target_lang}로 번역 시작"):
        with st.spinner("OpenRouter를 통해 번역 중..."):
            try:
                base64_image = encode_image(uploaded_file)
                
                # OpenRouter에서 Gemini 1.5 Pro 모델 호출
                response = client.chat.completions.create(
                    model="google/gemini-3-pro-image-preview", # 혹은 OpenRouter에서 제공하는 최신 모델명
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": PROMPTS[target_lang]},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                },
                            ],
                        }
                    ],
                )
                
                with col2:
                    st.subheader("번역 결과 (텍스트)")
                    # 모델의 응답이 비어있지 않은지 확인하고 텍스트를 출력합니다.
                    if response.choices[0].message.content:
                        translation_text = response.choices[0].message.content
                        st.info(translation_text) # 파란색 박스 안에 번역 내용을 보여줍니다.
                    else:
                        st.warning("모델이 번역 결과를 텍스트로 반환하지 않았습니다.")
                        
            except Exception as e:
                st.error(f"오류 발생: {e}")