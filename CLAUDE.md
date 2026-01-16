# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an image translation application for the "Moneywalk" pedometer app, built with Streamlit and Google's Gemini AI models. The app translates UI screenshots into 14 languages while preserving transparency, layout, and applying domain-specific terminology validation.

## Commands

### Running the Application
```bash
streamlit run app.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

**Main Application: [app.py](app.py)**
- Primary production version with JSON Mode auto-audit system
- Uses two Gemini models in sequence:
  1. `gemini-3-pro-image-preview` (GENERATION_MODEL_NAME) - for image translation
  2. `gemini-2.5-flash` (AUDIT_MODEL_NAME) - for automated quality control with JSON mode

**Backup Versions**
- [app_final.py](app_final.py) - Basic version without audit system
- Multiple timestamped backups (app_backup*.py) - Historical versions
- [app_openrouter.py](app_openrouter.py) - Alternative API implementation

### Key Architecture Patterns

**1. Two-Stage Translation Pipeline**
- Stage 1: Generate translated image using Gemini 3 Pro with glossary-enforced prompts
- Stage 2: Auto-audit the result using Gemini 2.5 Flash with JSON Mode to detect typos and validate translations
- The audit phase uses `response_mime_type: "application/json"` to prevent parsing errors

**2. Transparency Preservation (`restore_transparency` function)**
- Critical function that prevents AI-generated checkerboard backgrounds on transparent images
- Splits original alpha channel and merges with generated RGB channels
- Located in [app.py:91-103](app.py#L91-L103)

**3. Domain-Specific Glossary System**
- `GLOSSARY_DB` (line 23-34) contains mandatory translations for Moneywalk-specific terms
- Terms like "걸음 포인트" (Step Points), "수면 포인트" (Sleep Points) must translate consistently
- `get_glossary_prompt()` function injects these rules into generation prompts

**4. JSON Mode Audit Logic (`run_auto_audit` function)**
- Located at [app.py:44-82](app.py#L44-L82)
- Forces structured JSON output with `response_mime_type: "application/json"`
- Returns two fields:
  - `meaning_kr`: Korean interpretation of translated text for validation
  - `critical_errors`: List of detected typos (e.g., "pont❌ -> point⭕️")
- Special focus on detecting "Step"/"Point" misspellings which are critical business terms

### Configuration

**API Key Management**
- Reads from `st.secrets["GOOGLE_API_KEY"]` if available (for Streamlit Cloud deployment)
- Falls back to hardcoded placeholder (requires manual update for local development)
- Note: `.streamlit/` folder is gitignored (see [.gitignore](.gitignore))

**Language Support**
- 14 languages defined in `LANG_CODE_MAP` (line 36-41)
- Each language has corresponding glossary translations in `GLOSSARY_DB`

### State Management

**Session State Keys**
- `results`: List of translation results with audit data
- `lang_{language_name}`: Checkbox states for each language
- `select_all_key`: Master toggle for language selection

### Data Flow

1. User uploads multiple images via sidebar
2. Selects target languages (with select-all option)
3. Optional custom prompt for additional translation rules
4. For each image × language combination:
   - Generate translated image with glossary enforcement
   - Run auto-audit with JSON Mode to detect errors
   - Display result with audit feedback (meaning + critical errors)
   - Store result in session state
5. Package all results into downloadable ZIP file

### Important Behavioral Notes

**Glossary Enforcement**
- The glossary prompt is prepended to every generation request
- Format: "MANDATORY GLOSSARY" section with strict "MUST become" rules
- Example: "'걸음 포인트' MUST become 'Step points'" for English

**Critical Error Detection**
- Audit prompt explicitly flags "Step" vs "Stem"/"Stop"/"Steep" errors as CRITICAL
- Same for "Point" vs "Pont"/"Piont"
- This addresses a recurring issue where Gemini models occasionally misread generated text

**Real-time Progress Display**
- Grid layout updates incrementally (4 columns per row)
- Each result shows: language name, processing time, image preview, audit results
- Error messages displayed inline with specific translations

## Development Context

This application was specifically built for translating the Moneywalk app's Korean UI into multiple languages for international release. The glossary system and audit logic exist because:
1. Moneywalk has proprietary terms that must be consistent across languages
2. Generic AI translations sometimes introduce subtle typos in common words
3. The two-stage pipeline catches these issues before manual review

When modifying translation logic, always test with actual Moneywalk screenshots to ensure glossary terms are preserved correctly.
