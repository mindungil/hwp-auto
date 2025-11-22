# LLM 기반 통계 분석 및 보고서 생성 서비스

2025년 1학기 산학협력프로젝트

## 개요

LLM을 활용하여 통계 데이터를 분석하고, 분석 결과를 한글(HWPX) 보고서로 자동 생성하는 서비스입니다. 전북대학교 산학협력 프로젝트로 개발되었습니다.

## 주요 기능

- 통합 데이터 DB 기반 SQL 쿼리 생성 및 데이터 검색
- 사용자 데이터 파일(Excel, CSV) 업로드 및 자동 전처리
- 데이터 파일 미리보기 및 시각화
- LLM 기반 데이터 분석 및 챗봇 기능
- 분석 결과 기반 HWPX 한글보고서 자동 생성
- 그래프 자동 생성 및 보고서 삽입

## 시스템 아키텍처

### 전체 구조

```
┌─────────────────┐
│   User Input    │ (질문, 파일 업로드, STT 텍스트)
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌─────────────────┐
│  Streamlit App  │ <-> │  Flask Server   │
│  (Frontend UI)  │     │  (Backend API)  │
│  Port: 8501     │     │  Port: 5000     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         v                       v
┌─────────────────┐     ┌─────────────────┐
│  FastAPI Server │     │   LLM Agent     │
│  (HWPX 생성)    │     │ - Qwen3-14B     │
│  Port: 5001     │     │ - GPT-4o-mini   │
└────────┬────────┘     │ - KURE-v1       │
         │              └─────────────────┘
         v
┌─────────────────┐
│  HWPX 파일 생성  │
└─────────────────┘
```

### 기술 스택

- **Frontend**: Streamlit
- **Backend**: Flask, FastAPI
- **LLM**: Qwen3-14B (로컬), GPT-4o-mini (OpenAI)
- **Embedding**: KURE-v1
- **Database**: SQLite
- **Container**: Docker

## HWPX 생성 로직

### HWPX 파일 구조

HWPX는 한컴오피스의 XML 기반 문서 포맷으로, ZIP 압축 파일입니다:

```
hwpx_file/
├── mimetype              # 파일 타입 정의
├── META-INF/
│   ├── container.xml
│   └── manifest.xml
├── Contents/
│   ├── content.hpf       # 컨텐츠 매니페스트
│   ├── header.xml        # 헤더 정보
│   └── section0.xml      # 본문 내용
├── BinData/              # 이미지/그래프
├── settings.xml
└── version.xml
```

### 생성 프로세스

1. **입력 데이터 검증**: 사용자 입력을 Pydantic 모델(`DocheongReport`, `JBNUReport`)로 검증
2. **템플릿 복사**: `hwpx_report/template/`에서 템플릿 폴더를 임시 위치로 복사
3. **XML 조작**: `lxml`을 사용해 `section0.xml`의 섹션별 내용 교체
   - 개요, 테스트현황, 주요이슈, 향후계획 등
4. **이미지 등록**: 그래프를 `BinData/`에 복사하고 `content.hpf` 매니페스트 업데이트
5. **ZIP 압축**: mimetype은 STORED, 나머지는 DEFLATED로 압축

### 핵심 XML 조작

- **네임스페이스**: `http://www.hancom.co.kr/hwpml/2011/paragraph`
- **`replace_section()`**: 섹션 헤더를 찾아 기존 내용 제거 후 새 텍스트 삽입
- **`update_header_date()`**: 헤더의 날짜를 오늘 날짜로 업데이트
- **`register_images_to_content_hpf()`**: 이미지 파일을 매니페스트에 등록

## API 엔드포인트

### FastAPI (Port 5001)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/report/docheong` | 구조화된 JSON으로 보고서 생성 |
| POST | `/api/report/docheong-auto` | 원시 텍스트로 자동 분류 후 생성 |
| GET | `/api/download/{file_id}` | 생성된 HWPX 파일 다운로드 |
| DELETE | `/api/cleanup/{file_id}` | 임시 파일 정리 |

### Flask (Port 5000)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/chat` | SSE 기반 채팅 및 SQL 분석 |
| POST | `/upload` | 파일 업로드 및 전처리 |

## 데이터 모델

### DocheongReport (도청동향보고서)

```python
class DocheongReport(BaseModel):
    title: str              # 보고서 제목
    overview: List[str]     # 개요
    test_status: List[str]  # 테스트 현황
    key_issues: List[str]   # 주요이슈
    followup: List[str]     # 향후계획
```

각 리스트는 개조식 형태의 bullet point를 포함:
- `○ (항목명) 내용`
- `    - 세부사항`
- `    ※ 비고`

## 파일 구조

```
app/
├── streamlit_app.py      # Frontend Streamlit UI
├── server.py             # Backend Flask 서버
├── main.py               # FastAPI HWPX 생성 서버
├── data/
│   ├── csv_data/         # 전처리된 데이터
│   ├── xlsx_data/        # 원본 데이터
│   ├── faiss/            # FAISS 인덱스
│   ├── graph/            # 생성된 그래프
│   └── database.db       # SQLite DB
├── hwpx_report/
│   ├── template/         # HWPX 템플릿
│   ├── hwp_file/         # 생성된 파일
│   ├── json_file/        # JSON 출력
│   ├── hwp_pydantic.py   # Pydantic 모델
│   ├── docheong_report.py # 도청보고서 XML 처리
│   ├── hwp_xml.py        # XML 유틸리티
│   ├── hwpx_compress.py  # ZIP 압축
│   ├── jbnu_report.py    # JBNU 보고서 처리
│   └── model_json.py     # GPT-4o-mini 텍스트 분류
├── llm_agent/
│   ├── sql_report.py     # SQL 쿼리 생성 및 분석
│   ├── search.py         # FAISS 문서 검색
│   ├── embedding.py      # KURE-v1 임베딩
│   ├── graph.py          # 그래프 생성
│   ├── preprocess.py     # Excel/CSV 전처리
│   └── csv_2_db.py       # CSV to SQLite
├── Dockerfile
└── requirements.txt
```

## 데이터 흐름

1. **사용자 입력**: Streamlit UI를 통해 질문 또는 파일 업로드
2. **데이터 분석**: Flask 서버가 Qwen3-14B를 사용해 SQL 생성 및 실행
3. **응답 생성**: LLM이 분석 결과를 자연어로 정리
4. **보고서 변환**: GPT-4o-mini가 자유 텍스트를 구조화된 JSON으로 변환
5. **HWPX 생성**: FastAPI가 템플릿 기반으로 XML 조작 후 HWPX 파일 생성
6. **다운로드**: 생성된 HWPX 파일을 사용자에게 제공

## Web UI

<img src="https://github.com/user-attachments/assets/73d8f93e-1d40-4c30-b4b8-91594b37fc29" width="900"/>

## 시스템 아키텍처 다이어그램

<img src="https://github.com/user-attachments/assets/64406086-f9aa-4d5a-8716-6f6e5fc1d9b6" width="650"/>
<img src="https://github.com/user-attachments/assets/2857e364-731e-4d01-976b-df635220b8f0" width="650"/>

## 개발환경

- **Language**: Python
- **Framework**: Streamlit, Flask, FastAPI
- **Server**: Docker
- **Model**: KURE-v1 (Embedding), Qwen3-14B (LLM), GPT-4o-mini (텍스트 분류)
