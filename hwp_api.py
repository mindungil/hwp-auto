from flask import Flask, request, jsonify, send_file
from pathlib import Path
import uuid
import shutil
import os

from hwpx_report.hwp_pydantic import DocheongReport
from hwpx_report.docheong_report import process_docheong_report
from hwpx_report.jbnu_report import copy_folder, zip_as_hwpx

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

# ⚠️ 기존: "도청동향보고서_템플릿"
# 한글 폴더명 대신 영어 폴더명 사용
HWP_TEMPLATE = BASE_DIR / "hwpx_report" / "template" / "docheong_template"

HWP_WORK_BASE = BASE_DIR / "hwpx_report" / "hwpx_file"
JSON_TMP_DIR = HWP_WORK_BASE / "json_tmp"

JSON_TMP_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "docheong-hwp-generator"})


@app.route("/generate-docheong", methods=["POST"])
def generate_docheong():
    """
    Body(JSON)는 DocheongReport 구조.
    {
      "title": "...",
      "overview": { "bullets": ["...","..."] },
      "test_status": { "bullets": [...] },
      "key_issues": { "bullets": [...] },
      "followup": { "bullets": [...] }
    }
    """

    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    try:
        report = DocheongReport(**data)
    except Exception as e:
        return jsonify({"error": f"Invalid payload: {str(e)}"}), 400

    uid = uuid.uuid4().hex
    work_dir = HWP_WORK_BASE / f"도청동향보고서_복사본_{uid}"
    json_path = JSON_TMP_DIR / f"docheong_{uid}.json"
    xml_template = HWP_TEMPLATE / "Contents" / "section0.xml"
    xml_output = work_dir / "Contents" / "section0.xml"
    output_hwpx = HWP_WORK_BASE / f"docheong_{uid}.hwpx"

    try:
        # 1) 템플릿 폴더 복사
        copy_folder(str(HWP_TEMPLATE), str(work_dir))

        # 2) JSON 저장
        json_path.write_text(
            report.model_dump_json(ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 3) XML 변환 (템플릿 XML → 작업 디렉터리 XML)
        process_docheong_report(str(json_path), str(xml_template), str(xml_output))

        # 4) hwpx 압축 생성
        zip_as_hwpx(str(work_dir), str(output_hwpx))

        # 5) 파일 응답
        return send_file(
            output_hwpx,
            as_attachment=True,
            download_name="도청동향보고서.hwpx",
            mimetype="application/octet-stream"
        )

    except Exception as e:
        return jsonify({"error": f"Failed to generate HWP: {str(e)}"}), 500

    finally:
        # 작업 디렉토리 정리(선택)
        try:
            if work_dir.exists():
                shutil.rmtree(work_dir)
        except:
            pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010)
