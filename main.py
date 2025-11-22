from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import shutil
import uuid
import json  # ✅ pydantic 대신 직접 JSON 직렬화용

from hwpx_report.hwp_pydantic import DocheongReport, DynamicReport, DynamicSection
from hwpx_report.docheong_report import process_docheong_report, process_dynamic_report
from hwpx_report.hwpx_compress import create_hwpx_from_folder

# 🔹 LLM 자동 분류 헬퍼 (없어도 서버는 뜨도록 try/except)
try:
    # 줄글(STT 결과) → 섹션 JSON 자동 분류 함수
    from hwpx_report.model_json import generate_docheong_json, generate_dynamic_json
except ImportError:
    generate_docheong_json = None
    generate_dynamic_json = None

app = FastAPI(title="HWPX Report API", version="1.0.0")

# 베이스 디렉토리 (/app)
BASE_DIR = Path(__file__).resolve().parent

# hwpx 결과/중간파일 저장 디렉토리
TEMP_DIR = BASE_DIR / "temp_outputs"
TEMP_DIR.mkdir(exist_ok=True)


# ---------- 요청 / 응답 모델 ----------

class DocheongRequest(BaseModel):
    """섹션이 이미 나뉘어 있는 요청용 JSON"""
    title: str
    overview: list[str]
    test_status: list[str]
    key_issues: list[str]
    followup: list[str]


class DocheongAutoRequest(BaseModel):
    """
    줄글 / STT 결과 그대로 받아서
    LLM이 섹션(개요/현황/이슈/향후계획) 자동 분류하도록 하는 요청 타입
    """
    text: str                 # 전체 줄글 / STT 텍스트
    title: str | None = None  # 제목을 직접 지정하고 싶으면 사용 (없으면 LLM이 정한 제목 사용)


class DynamicSectionRequest(BaseModel):
    """동적 섹션 요청"""
    header: str
    content: list[str]


class DynamicReportRequest(BaseModel):
    """동적 섹션 보고서 요청 - 섹션 구조가 자유로움"""
    title: str
    sections: list[DynamicSectionRequest]


class DynamicAutoRequest(BaseModel):
    """
    줄글 / STT 결과 그대로 받아서
    LLM이 섹션 수/이름을 자유롭게 결정하도록 하는 요청 타입
    """
    text: str
    title: str | None = None


class ReportResponse(BaseModel):
    success: bool
    message: str
    file_id: str
    download_url: str


# ---------- 템플릿 경로 헬퍼 ----------

def _get_template_dir() -> Path:
    """
    컨테이너 안에서 실제 존재하는 도청 템플릿 폴더를 찾는다.
    (이름이 바뀌어도 최대한 자동으로 찾아보도록 후보를 두 개 둠)
    """
    candidates = [
        BASE_DIR / "hwpx_report" / "template" / "도청동향보고서_템플릿",
        BASE_DIR / "hwpx_report" / "template" / "docheong_template",
    ]

    for p in candidates:
        if p.exists():
            return p

    # 아무 것도 없으면 좀 더 친절한 에러를 던짐
    raise FileNotFoundError(
        "도청 보고서 템플릿 폴더를 찾을 수 없습니다. 시도한 경로: "
        + ", ".join(str(p) for p in candidates)
    )


# ---------- 공통 HWPX 생성 로직 ----------

def _create_docheong_hwpx(report: DocheongReport) -> tuple[str, Path]:
    """
    공통 HWPX 생성 로직.
      1) JSON 저장
      2) 템플릿 폴더 복사
      3) XML(section0.xml) 내용 갱신
      4) 폴더 전체를 .hwpx로 압축

    반환:
      (file_id, hwpx_output_path)
    """
    file_id = f"docheong_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # 1) JSON 저장
    json_path = TEMP_DIR / f"{file_id}.json"

    # 🔴 문제였던 부분: model_dump_json(ensure_ascii=...) → pydantic v2에서 에러
    # ✅ 안전하게: dict()로 뽑아서 json.dumps로 직접 저장 (한글도 그대로)
    data = report.model_dump()  # pydantic v2 표준
    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    json_path.write_text(json_text, encoding="utf-8")

    # 2) 템플릿 복사 (도청 동향보고서 원본 템플릿)
    template_src = _get_template_dir()
    work_dir = TEMP_DIR / file_id
    shutil.copytree(template_src, work_dir)

    # 3) XML 변환 (섹션 내용 채워넣기)
    xml_template = work_dir / "Contents/section0.xml"
    xml_output = work_dir / "Contents/section0.xml"
    process_docheong_report(str(json_path), str(xml_template), str(xml_output))

    # 4) HWPX 압축 생성
    hwpx_output = TEMP_DIR / f"{file_id}.hwpx"
    create_hwpx_from_folder(str(work_dir), str(hwpx_output))

    return file_id, hwpx_output


def _create_dynamic_hwpx(report: DynamicReport) -> tuple[str, Path]:
    """
    동적 섹션 HWPX 생성 로직.
      1) JSON 저장
      2) 템플릿 폴더 복사
      3) XML(section0.xml) 내용 갱신
      4) 폴더 전체를 .hwpx로 압축

    반환:
      (file_id, hwpx_output_path)
    """
    file_id = f"dynamic_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # 1) JSON 저장
    json_path = TEMP_DIR / f"{file_id}.json"
    data = report.model_dump()
    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    json_path.write_text(json_text, encoding="utf-8")

    # 2) 템플릿 복사
    template_src = _get_template_dir()
    work_dir = TEMP_DIR / file_id
    shutil.copytree(template_src, work_dir)

    # 3) XML 변환 (동적 섹션 처리)
    xml_template = work_dir / "Contents/section0.xml"
    xml_output = work_dir / "Contents/section0.xml"
    process_dynamic_report(str(json_path), str(xml_template), str(xml_output))

    # 4) HWPX 압축 생성
    hwpx_output = TEMP_DIR / f"{file_id}.hwpx"
    create_hwpx_from_folder(str(work_dir), str(hwpx_output))

    return file_id, hwpx_output


# ---------- 엔드포인트 ----------

@app.get("/")
async def root():
    return {
        "service": "HWPX Report Generator",
        "status": "running",
        "port": 5001,
        "endpoints": {
            "generate": "POST /api/report/generate (원스텝: 텍스트→파일)",
            "docheong": "POST /api/report/docheong",
            "docheong_auto": "POST /api/report/docheong-auto",
            "dynamic": "POST /api/report/dynamic",
            "dynamic_auto": "POST /api/report/dynamic-auto",
            "download": "GET /api/download/{file_id}",
            "cleanup": "DELETE /api/cleanup/{file_id}",
        },
    }


@app.post("/api/report/docheong", response_model=ReportResponse)
async def create_docheong_report(request: DocheongRequest):
    """
    섹션이 이미 나뉜 JSON을 받는 엔드포인트.
    - title / overview / test_status / key_issues / followup 필수.
    """
    try:
        # DocheongReport(pydantic)로 검증
        report = DocheongReport(**request.dict())

        # 공통 HWPX 생성 로직 사용
        file_id, _ = _create_docheong_hwpx(report)

        return ReportResponse(
            success=True,
            message="도청 보고서 생성 완료",
            file_id=file_id,
            download_url=f"/api/download/{file_id}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/report/docheong-auto", response_model=ReportResponse)
async def create_docheong_report_auto(request: DocheongAutoRequest):
    """
    줄글 / STT 결과(text)만 받아서:
      1) generate_docheong_json(text)로 섹션 자동 분류
      2) DocheongReport로 검증
      3) 공통 HWPX 생성 로직 재사용
    """
    # langchain_openai / model_json 이 설치되지 않은 상태라면 안내 메시지 반환
    if generate_docheong_json is None:
        raise HTTPException(
            status_code=500,
            detail="자동 분류 기능이 비활성화되어 있습니다. "
                   "서버에 langchain_openai 및 관련 의존성을 설치해야 합니다."
        )

    try:
        # 1) 줄글 → JSON(섹션 자동 분류)
        report_json = generate_docheong_json(request.text)

        # 2) 제목이 별도로 들어오면 덮어쓰기
        if request.title:
            report_json["title"] = request.title

        # 3) pydantic 검증
        report = DocheongReport(**report_json)

        # 4) 공통 HWPX 생성 로직 사용
        file_id, _ = _create_docheong_hwpx(report)

        return ReportResponse(
            success=True,
            message="도청 보고서(자동 분류) 생성 완료",
            file_id=file_id,
            download_url=f"/api/download/{file_id}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/report/dynamic", response_model=ReportResponse)
async def create_dynamic_report(request: DynamicReportRequest):
    """
    동적 섹션 보고서 생성 - 섹션 수/이름이 자유로움.
    - title: 보고서 제목
    - sections: [{header: "□ 섹션명", content: ["내용1", "내용2", ...]}, ...]
    """
    try:
        # DynamicReport로 변환
        sections = [
            DynamicSection(header=s.header, content=s.content)
            for s in request.sections
        ]
        report = DynamicReport(title=request.title, sections=sections)

        # HWPX 생성
        file_id, _ = _create_dynamic_hwpx(report)

        return ReportResponse(
            success=True,
            message="동적 섹션 보고서 생성 완료",
            file_id=file_id,
            download_url=f"/api/download/{file_id}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/report/dynamic-auto", response_model=ReportResponse)
async def create_dynamic_report_auto(request: DynamicAutoRequest):
    """
    줄글 / STT 결과(text)만 받아서:
      1) LLM이 섹션 수/이름을 자유롭게 결정
      2) DynamicReport로 검증
      3) HWPX 생성
    """
    if generate_dynamic_json is None:
        raise HTTPException(
            status_code=500,
            detail="동적 섹션 자동 분류 기능이 비활성화되어 있습니다. "
                   "서버에 langchain_openai 및 관련 의존성을 설치해야 합니다."
        )

    try:
        # 1) 줄글 → JSON (LLM이 섹션 자유롭게 결정)
        report_json = generate_dynamic_json(request.text)

        # 2) 제목이 별도로 들어오면 덮어쓰기
        if request.title:
            report_json["title"] = request.title

        # 3) pydantic 검증
        report = DynamicReport(**report_json)

        # 4) HWPX 생성
        file_id, _ = _create_dynamic_hwpx(report)

        return ReportResponse(
            success=True,
            message="동적 섹션 보고서(자동 분류) 생성 완료",
            file_id=file_id,
            download_url=f"/api/download/{file_id}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/report/generate")
async def generate_report_direct(request: DynamicAutoRequest):
    """
    원스텝 파이프라인: 텍스트 → LLM 섹션 구성 → HWPX 생성 → 파일 직접 반환
    """
    if generate_dynamic_json is None:
        raise HTTPException(
            status_code=500,
            detail="동적 섹션 자동 분류 기능이 비활성화되어 있습니다."
        )

    try:
        # 1) 줄글 → JSON (LLM이 섹션 자유롭게 결정)
        report_json = generate_dynamic_json(request.text)

        # 2) 제목이 별도로 들어오면 덮어쓰기
        if request.title:
            report_json["title"] = request.title

        # 3) pydantic 검증
        report = DynamicReport(**report_json)

        # 4) HWPX 생성
        file_id, hwpx_path = _create_dynamic_hwpx(report)

        # 5) 파일명 생성 (제목 기반)
        safe_title = report.title.replace(" ", "_").replace("/", "_")[:50]
        filename = f"{safe_title}_{file_id}.hwpx"

        return FileResponse(
            path=hwpx_path,
            media_type="application/vnd.hancom.hwpx",
            filename=filename,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{file_id}")
async def download_report(file_id: str):
    hwpx_file = TEMP_DIR / f"{file_id}.hwpx"

    if not hwpx_file.exists():
        raise HTTPException(status_code=404, detail="파일 없음")

    return FileResponse(
        path=hwpx_file,
        media_type="application/vnd.hancom.hwpx",
        filename=f"{file_id}.hwpx",
    )


@app.delete("/api/cleanup/{file_id}")
async def cleanup_report(file_id: str):
    try:
        (TEMP_DIR / f"{file_id}.hwpx").unlink(missing_ok=True)
        (TEMP_DIR / f"{file_id}.json").unlink(missing_ok=True)
        work_dir = TEMP_DIR / file_id
        if work_dir.exists():
            shutil.rmtree(work_dir)
        return {"success": True, "message": "삭제 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
