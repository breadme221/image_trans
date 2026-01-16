import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import zipfile
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --- 1. 설정 및 API 키 ---
if "GOOGLE_API_KEY" in st.secrets:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    GOOGLE_API_KEY = "여기에_API_키를_입력하세요"

genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. 모델 설정 ---
GENERATION_MODEL_NAME = 'gemini-3-pro-image-preview'
AUDIT_MODEL_NAME = 'gemini-2.5-flash'

# --- 3. 내장 용어집 ---
GLOSSARY_DB = {
    "걸음 포인트": {"en": "Step points", "ja": "歩数ポイント", "zh": "步数积分", "hi": "कदम अंक", "fr": "Pts marche", "es": "Pts pasos", "id": "Poin langkah", "pt": "Pts passos", "it": "Punti passi", "de": "Schrittpunkte", "vi": "Điểm bước", "th": "คะแนนก้าว", "ms": "Mata langkah", "tw": "步數點數"},
    "걸음 포인트 받기": {"en": "Claim step points", "ja": "歩数ポイントを獲得", "zh": "获取步数积分", "hi": "कदम अंक कमाएं", "fr": "Gagnez pts marches", "es": "Gana pts pasos", "id": "Dapatkan poin langkah", "pt": "Ganhe pts passos", "it": "Ottieni punti passi", "de": "Schrittpunkte erhalten", "vi": "Nhận điểm bước", "th": "รับคะแนนก้าว", "ms": "Dapatkan mata langkah", "tw": "領取步數點數"},
    "수면 포인트": {"en": "Sleep points", "ja": "睡眠ポイント", "zh": "睡眠积分", "hi": "नींद अंक", "fr": "Pts Sommeil", "es": "Pts Sueño", "id": "Poin Tidur", "pt": "Pts Sono", "it": "Punti Sonno", "de": "Schlafpunkte", "vi": "Điểm Ngủ", "th": "คะแนนนอน", "ms": "Mata tidur", "tw": "睡眠點數"},
    "랜덤 포인트": {"en": "Random Points", "ja": "ランダムポイント", "zh": "随机积分", "hi": "बोनस पॉइंट्स", "fr": "Pts bonus", "es": "Pts random", "id": "Poin Acak", "pt": "Pts aleat", "it": "Pts casuali", "de": "Zufallspunkt", "vi": "Điểm Ngẫu nhiên", "th": "คะแนนสุ่ม", "ms": "Mata rawak", "tw": "隨機點數"},
    "랜덤 받기": {"en": "Claim", "ja": "受け取る", "zh": "获取随机", "hi": "पाएं", "fr": "Obtenir", "es": "Obtener", "id": "Ambil", "pt": "Obter", "it": "Ottieni", "de": "Holen", "vi": "Nhận", "th": "รับ", "ms": "Claim", "tw": "隨機獲取"},
    "받을 수 있는 걸음 포인트": {"en": "Claimable Step Points", "ja": "獲得可能ステップポイント", "zh": "可得步数积分", "hi": "प्राप्त कदम अंक", "fr": "Pts marche gagnables", "es": "Pts pasos obtenibles", "id": "Poin langkah diperoleh", "pt": "Pts de passos possíveis", "it": "Punti passi ottenibili", "de": "Schrittpunkte erzielbar", "vi": "Điểm bước có thể nhận", "th": "คะแนนก้าวที่รับได้", "ms": "Mata langkah diperoleh", "tw": "可獲得步數點數"},
    "머니팜": {"en": "Money Farm", "ja": "マネーファーム", "zh": "金币农场", "hi": "머니팜", "fr": "MoneyFarm", "es": "MoneyFarm", "id": "MoneyFarm", "pt": "MoneyFarm", "it": "MoneyFarm", "de": "MoneyFarm", "vi": "MoneyFarm", "th": "มันนี่ฟาร์ม", "ms": "MoneyFarm", "tw": "金幣農場"},
    "리딤 계산기": {"en": "Redeem Calculator", "ja": "交換計算機", "zh": "兑换计算器", "hi": "리딤 계산기", "fr": "Calculateur Réduction", "es": "Calculadora Redimir", "id": "Kalkulator Tukar", "pt": "Calculadora Troca", "it": "Calcolatore Riscatta", "de": "Einlöse-Rechner", "vi": "Máy Tính Quy Đổi", "th": "เครื่องคำนวณการแลกเปลี่ยน", "ms": "Kalkulator Tebus", "tw": "兌換計算機"},
    "출석체크": {"en": "Check-in", "ja": "出席チェック", "zh": "签到", "hi": "चेक-इन", "fr": "Check-in", "es": "Check-in", "id": "Check-in Harian", "pt": "Check-in", "it": "Check-in", "de": "Check-in", "vi": "Điểm danh", "th": "เช็คชื่อ", "ms": "Check-in", "tw": "簽到"},
    "오늘의 걸음수": {"en": "Today's Steps", "ja": "今日の歩数", "zh": "今日步数", "hi": "आज के कदम", "fr": "Pas du jour", "es": "Pasos de hoy", "id": "Langkah hari ini", "pt": "Passos de hoje", "it": "Passi di oggi", "de": "Heutige Schritte", "vi": "Số bước hôm nay", "th": "ก้าววันนี้", "ms": "Langkah hari ini", "tw": "今日步數"}
}

LANG_CODE_MAP = {
    "영어": "en", "일본어": "ja", "중국어 간체": "zh", "힌디어": "hi",
    "프랑스어": "fr", "스페인어": "es", "인도네시아어": "id", "포르투갈어": "pt",
    "이탈리아어": "it", "독일어": "de", "베트남어": "vi", "태국어": "th",
    "말레이어": "ms", "중국어 번체": "tw"
}

# --- 4. [핵심] JSON Mode가 적용된 자동 검수 로직 ---
def run_auto_audit(image_bytes, target_lang):
    """
    JSON Mode를 사용하여 파싱 에러를 방지하고 오타 검수 성능을 극대화합니다.
    """
    model = genai.GenerativeModel(AUDIT_MODEL_NAME)
    
    # 이미지를 API가 직접 읽을 수 있는 딕셔너리 형태로 변환
    img_data = {'mime_type': 'image/png', 'data': image_bytes}
    
    prompt = f"""
    Analyze this translated UI image for 'Moneywalk' (Pedometer App).
    Target Language: {target_lang}
    이미지에 적힌 모든 외국어 텍스트를 한국어로 번역하여 나열하세요.
    - 절대 "이 화면은 ~입니다" 혹은 "의미는 ~입니다" 같은 설명을 덧붙이지 마세요.
    - 화면에 실제 존재하는 텍스트만 1:1로 대응하여 단어 혹은 문장 단위로 나열하세요.

    **STRICT DOMAIN RULES:**
    - Keyword 'Step' MUST be 'Step'. Errors like 'Stem', 'Stop', 'Steep' are CRITICAL.
    - Keyword 'Point' MUST be 'Point'. Errors like 'Pont', 'Piont' are CRITICAL.
    - Ignore design/clipping. Focus ONLY on text characters.

    **OUTPUT JSON STRUCTURE:**
    {{
        "meaning_kr": "추출된 한국어 텍스트들만 나열",
        "critical_errors": ["pont❌ -> point⭕️", "stem❌ -> step⭕️"]
    }}
    """
    
    try:
        # generation_config에 response_mime_type을 설정하여 JSON 강제
        response = model.generate_content(
            [prompt, img_data],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        # 실패 시 로그를 남기고 기본값 반환
        print(f"Audit Error: {e}")
        return {"meaning_kr": "의미를 분석 중입니다...", "critical_errors": []}

# --- 5. 헬퍼 및 UI 로직 (이전과 동일하지만 루프 내 시간 측정 강화) ---
def get_glossary_prompt(lang_name):
    lang_code = LANG_CODE_MAP.get(lang_name)
    if not lang_code: return ""
    rules = [f"   - '{k}' MUST become '{v[lang_code]}'" for k, v in GLOSSARY_DB.items() if lang_code in v]
    return f"\n\n*** MANDATORY GLOSSARY ***\n" + "\n".join(rules) + "\n*************************\n" if rules else ""

def restore_transparency(original_img, generated_img_bytes):
    is_trans = (original_img.mode == 'RGBA') or (original_img.format in ['PNG', 'WEBP'])
    gen_img = Image.open(io.BytesIO(generated_img_bytes)).convert("RGBA")
    if is_trans:
        gen_img = gen_img.resize(original_img.size, Image.Resampling.LANCZOS)
        r, g, b, a = original_img.split()
        gr, gg, gb, _ = gen_img.split()
        final_img = Image.merge("RGBA", (gr, gg, gb, a))
    else:
        final_img = gen_img.resize(original_img.size, Image.Resampling.LANCZOS).convert("RGB")
    buf = io.BytesIO()
    final_img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()

def toggle_langs():
    for lang in LANG_CODE_MAP.keys():
        st.session_state[f"lang_{lang}"] = st.session_state.select_all_key

def translate_single_image(f, lang, file_name, gen_model, user_prompt):
    """단일 이미지 번역 함수"""
    try:
        # 이미지 준비
        f.seek(0)
        orig = Image.open(f).convert("RGBA")
        orig.format = file_name.split('.')[-1].upper()

        t_start = time.time()

        # 1. Gemini 번역
        p_gen = f"{get_glossary_prompt(lang)}\nTranslate all text to {lang}. {user_prompt}\nOutput result as image. Preserve layout."
        resp = gen_model.generate_content([p_gen, orig])

        if resp.candidates and resp.candidates[0].content.parts[0].inline_data:
            data = restore_transparency(orig, resp.candidates[0].content.parts[0].inline_data.data)

            # 2. 자동 검수
            audit = run_auto_audit(data, lang)

            duration = time.time() - t_start

            return {
                "lang": lang,
                "data": data,
                "name": file_name,
                "audit": audit,
                "time": duration,
                "success": True
            }
        else:
            return {
                "lang": lang,
                "name": file_name,
                "error": "No response from Gemini",
                "success": False
            }
    except Exception as e:
        return {
            "lang": lang,
            "name": file_name,
            "error": str(e),
            "success": False
        }

# UI 구성
st.set_page_config(page_title="Moneywalk 번역기 (JSON Mode)", layout="wide")
st.title("글로벌 이미지 번역기")

if 'results' not in st.session_state: st.session_state.results = []

with st.sidebar:
    st.header("🛠️ 설정")
    uploaded_files = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)
    st.divider()
    st.checkbox("전체 선택", key="select_all_key", on_change=toggle_langs)
    selected_langs = [l for l in LANG_CODE_MAP.keys() if st.checkbox(l, key=f"lang_{l}", value=st.session_state.get(f"lang_{l}", l==""))]

if not uploaded_files:
    st.info("⬅️ 사이드바에서 이미지를 업로드해주세요.")
else:
    st.header("1️⃣ 업로드한 이미지")
    t_cols = st.columns(4)
    for i, f in enumerate(uploaded_files):
        with t_cols[i % 4]: st.image(Image.open(f), caption=f.name, use_container_width=True)
    st.divider()

    col_in, col_btn = st.columns([3, 1])
    with col_in: user_prompt = st.text_input("✋잠깐! 추가로 입력할 프롬프트가 있나요?", placeholder="예: (원하는 단어)는 (원하는 번역)로 유지해줘")
    with col_btn:
        st.write(""); st.write("")
        start_btn = st.button("🚀 번역 시작", type="primary", use_container_width=True)

    if start_btn:
        st.divider(); st.header("2️⃣ 번역된 이미지")
        st.session_state.results = []
        gen_model = genai.GenerativeModel(GENERATION_MODEL_NAME)
        progress = st.progress(0); status = st.empty()
        
        total = len(uploaded_files) * len(selected_langs)
        done = [0]  # 리스트로 감싸서 mutable하게
        start_all = time.time()
        res_cols = st.columns(4)
        lock = threading.Lock()  # Thread-safe 업데이트용

        # 각 이미지마다 병렬 처리
        for f in uploaded_files:
            st.info(f"🖼️ **{f.name}** 처리 중...")

            # ThreadPoolExecutor로 14개 언어 동시 처리
            with ThreadPoolExecutor(max_workers=14) as executor:
                # 모든 언어에 대한 Future 생성
                futures = {
                    executor.submit(translate_single_image, f, lang, f.name, gen_model, user_prompt): lang
                    for lang in selected_langs
                }

                # 완료되는 순서대로 처리
                for future in as_completed(futures):
                    result = future.result()

                    # Progress 업데이트 (thread-safe)
                    with lock:
                        done[0] += 1
                        progress.progress(done[0] / total)
                        status.markdown(f"**✅ 완료 ({done[0]}/{total}):** {result['name']} → {result['lang']}")

                    if result['success']:
                        st.session_state.results.append(result)

                        # 결과 표시
                        col_idx = (done[0] - 1) % 4
                        with res_cols[col_idx]:
                            st.markdown(f"**{result['lang']}** ({result['time']:.1f}초)")
                            st.image(result['data'], use_container_width=True)

                            if result['audit']:
                                st.info(f"**의미**: {result['audit'].get('meaning_kr', '-')}")
                                errs = result['audit'].get('critical_errors', [])
                                if errs:
                                    st.error(f"**오타**: " + "\n".join([f"- {e}" for e in errs]))
                            st.divider()

                        # 4개마다 새 컬럼
                        if done[0] % 4 == 0:
                            res_cols = st.columns(4)
                    else:
                        st.error(f"에러 ({result['lang']}): {result.get('error', 'Unknown error')}")
        
        st.success(f"✅ 전체 완료! (총 {time.time()-start_all:.1f}초)")
        progress.empty()

if st.session_state.results:
        st.divider()
        st.header("📦 결과 다운로드")
        
        try:
            zip_io = io.BytesIO()
            with zipfile.ZipFile(zip_io, 'w') as zf:
                for r in st.session_state.results:
                    # 166번 줄에서 'data'라는 키로 저장했으므로 r['data']가 맞습니다.
                    clean_name = r['name'].split('.')[0]
                    safe_file_name = f"{clean_name}_{r['lang']}.png"
                    zf.writestr(safe_file_name, r['data'])
            
            st.download_button(
                label="📂 번역된 이미지 전체 다운로드 (ZIP)",
                data=zip_io.getvalue(),
                file_name="moneywalk_translated.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"다운로드 파일 생성 중 오류가 발생했습니다: {e}")