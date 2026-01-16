#!/bin/bash
# Streamlit 개발 서버 실행 스크립트

cd "$(dirname "$0")"
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.headless false
