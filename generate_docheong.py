#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import secrets

from hwpx_report.hwp_pydantic import DocheongReport
from hwpx_report.docheong_report import process_docheong_report
from hwpx_report.jbnu_report import copy_folder, zip_as_hwpx


def main():
    print("🔥 도청 동향보고서 자동 생성 테스트 시작")
    
    # 타임스탬프와 랜덤 ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_id = secrets.token_hex(3)
    
    # 1) 테스트용 JSON 데이터 (상세 버전)
    report_data = {
        "title": "생성형 AI 시스템 사전테스트 동향보고",
        "overview": [
            " ○ (운영기간) '25. 11. 3.(월) ~ 11. 5.(수), 3일간",
            "    ※ 당초 기조실 대상으로 사전 테스트를 실시했으나, 설문응답이 20건(행정정보과 9건)에 불과하여 신뢰성 확보를 위해 범위를 확대하여 사전테스트 재실시",
            " ○ (홍보방법) 전 직원 메일발송 + 행정포탈 공지사항 게시",
            "    - (메일) 6,497명 발송 → 3,186명 확인",
            "    - (포탈) 공지사항 게시 → 790회 열람",
            " ○ (목    표) 대량 동시접속 시 부하테스트(안정성) 및 API 사용량 확인"
        ],
        "test_status": [
            " ○ (접속자수) 총 607명(11. 3. ~ 11. 5.)",
            " ○ (사용토큰) 16,713,736토큰(어절)   ※ 1인당 27,535토큰",
            " ○ (질문횟수) 8,413건  ※ 1인당 13.9회",
            " ○ (동시접속자) 11. 4. 오전100명 → 11. 4. 오후50명 → 11. 5. 20~30명",
            " ○ (부하측정) 최적화를 통해 동시 250명 질문까지 답변 가능하나, 현재 최대 분당 20건 질문 중으로 정식 서비스 시에도 쾌적한 운영 가능",
            " ○ (API 사용량) ChatGPT $4.43, 퍼플렉시티 $1.3 사용",
            "     - 향후 활성화 시 하루 $20씩 사용하더라도 연간 10,438천원 소요"
        ],
        "key_issues": [
            " ○ (교육) 사전 설명이 없어 직원들이 사용법을 잘 모르는 상황",
            " ○ (로그인) @mail.go.kr 대신 @korea.kr 등 다른 메일 입력 후 가입신청(33명)",
            "    - 11. 4. 국과장급 AI 교육시에도 로그인이 어렵다는 의견",
            " ○ (웹검색) 웹검색 기능을 켜지 않고 사용하여, 예전 자료만 확인",
            " ○ (PDF) PDF 변환기능 필요 의견  ※현재 Chandra OCR 포팅 중"
        ],
        "followup": [
            " ○ 이용자 대상 설문조사 실시                        : 11. 6. ~ 7."
        ]
    }
    
    # 2) JSON 저장
    json_dir = Path("hwpx_report/json_file")
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / f"docheong_{timestamp}.json"
    json_path.write_text(
        DocheongReport(**report_data).model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"✅ JSON 저장됨: {json_path}")
    
    # 3) 템플릿 복사
    # ⚠️ 기존: "hwpx_report/template/도청동향보고서_템플릿"
    template_src = "hwpx_report/template/docheong_template"
    work_folder = f"hwpx_report/hwpx_file/도청동향보고서_복사본_{timestamp}_{random_id}"
    copy_folder(template_src, work_folder)
    print(f"✅ 폴더 복제 완료: {template_src} → {work_folder}")
    
    # 4) XML 생성
    xml_path = f"{work_folder}/Contents/section0.xml"
    process_docheong_report(str(json_path), xml_path, xml_path)
    
    # 5) HWPX 압축
    output_hwpx = f"도청동향보고서_{timestamp}_{random_id}.hwpx"
    zip_as_hwpx(work_folder, output_hwpx)
    
    print(f"🎉 HWPX 생성 완료: {output_hwpx}")


if __name__ == "__main__":
    main()
