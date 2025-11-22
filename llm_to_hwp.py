#!/usr/bin/env python3
"""
사용자 프롬프트 → OpenAI GPT → JSON → HWPX 생성
"""
import json
from pathlib import Path
from datetime import datetime
import secrets

from hwpx_report.hwp_pydantic import DocheongReport
from hwpx_report.docheong_report import process_docheong_report
from hwpx_report.jbnu_report import copy_folder, zip_as_hwpx
from hwpx_report.model_json import generate_docheong_json


def create_hwpx_from_prompt(user_prompt: str, output_filename: str = None):
    """사용자 프롬프트 → HWPX 파일 생성 (OpenAI 사용)"""
    print("\n" + "=" * 60)
    print("🎃 도청 동향보고서 자동 생성 (OpenAI GPT)")
    print("=" * 60 + "\n")
    
    # 1) LLM으로 JSON 생성
    report_json = generate_docheong_json(user_prompt)
    
    print("✅ JSON 생성 완료!")
    print(json.dumps(report_json, indent=2, ensure_ascii=False))
    print()
    
    # 2) JSON 검증
    report = DocheongReport(**report_json)
    
    # 3) 타임스탬프
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_id = secrets.token_hex(3)
    
    # 4) JSON 저장
    json_dir = Path("hwpx_report/json_file")
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / f"docheong_{timestamp}.json"
    json_path.write_text(
        report.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"✅ JSON 저장: {json_path}\n")
    
    # 5) 템플릿 복사
    #   ⚠️ 기존: "hwpx_report/template/도청동향보고서_템플릿"
    #   → 한글 폴더 이름(NFC/NFD) 문제 피하려고 영어로 변경
    template_src = "hwpx_report/template/docheong_template"
    work_folder = f"hwpx_report/hwpx_file/도청동향보고서_복사본_{timestamp}_{random_id}"
    copy_folder(template_src, work_folder)
    print(f"✅ 템플릿 복사 완료\n")
    
    # 6) XML 생성
    xml_path = f"{work_folder}/Contents/section0.xml"
    process_docheong_report(str(json_path), xml_path, xml_path)
    
    # 7) HWPX 압축
    if output_filename:
        output_hwpx = output_filename
    else:
        output_hwpx = f"도청동향보고서_{timestamp}_{random_id}.hwpx"
    
    zip_as_hwpx(work_folder, output_hwpx)
    
    print("\n" + "=" * 60)
    print(f"🎉 HWPX 생성 완료: {output_hwpx}")
    print("=" * 60 + "\n")
    
    return output_hwpx


def main():
    user_prompt = """
    오늘은 캡스톤 디자인 과목을 위해 김길모임 팀이 모여서 회의했어.
    주제는 뭐먹을지였어. 캡스톤에서 회의비 주어주는데 15만원 가지고 뭘 먹을지 정해야되거든
    꾸석지, 미친고기, 흑심, 신가화로, 쿠우쿠우, 샤브올데이, 오일내,,, 등등의 아이디어가 나왔어.
    
    아래는 별도로 주무관님이랑 얘기한 내용들이야
    - 모델따라 기능들 크로스체크 
    - 자기가 한것들 문서화
    - 피피티에 기능들 한페이지에 몰아넣어서 작성
    - 두팀이 한거 hwp 그대로 재현
    - 모델별로 4명이서 수십개 대화 해뷰면서 테스트 20번 이상
    - 이번주까지 기능완성 후 도청 담주에 가서 ppt 완성
    - 요구사항 체크리스트 작성 후 완료/미완료 나눠서 끝내기
    """
    
    create_hwpx_from_prompt(user_prompt)
    # create_hwpx_from_prompt(user_prompt, output_filename="도청동향보고서_테스트.hwpx")


if __name__ == "__main__":
    main()
