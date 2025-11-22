from lxml import etree
from pathlib import Path
from typing import List
from copy import deepcopy
from datetime import datetime
import re

from hwpx_report.hwp_pydantic import DocheongReport, DynamicReport

NS = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}


def get_all_paras(root):
    return root.xpath(".//hp:p", namespaces=NS)


def get_para_text(p):
    texts = p.xpath(".//hp:t/text()", namespaces=NS)
    return "".join(texts)


def update_text_only(root, para_pr_id: str, new_text: str):
    """특정 paraPrIDRef의 텍스트만 업데이트"""
    paras = root.xpath(f".//hp:p[@paraPrIDRef='{para_pr_id}']", namespaces=NS)

    for p in paras:
        t_elements = p.xpath(".//hp:t", namespaces=NS)
        if t_elements:
            t_elements[0].text = new_text
            print(f"✅ paraPrIDRef={para_pr_id} 텍스트 업데이트 완료.")
            break


def update_header_date(root):
    """헤더 날짜를 오늘 날짜로 변경"""

    today = datetime.now()

    # U+2019 문자를 직접 유니코드로 생성
    right_single_quote = chr(0x2019)  # '''

    date_str = today.strftime(f"{right_single_quote}%y. %m. %d.(")
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    weekday_kor = weekdays[today.weekday()]
    new_date = f"{date_str}{weekday_kor})"

    print(f"📅 헤더 날짜를 {new_date} 로 변경합니다.")

    # 두 종류의 작은따옴표 모두 찾기
    date_pattern = re.compile(
        r"[\u0027\u2019]\d{2}\.\s*\d{1,2}\.\s*\d{1,2}\.\([월화수목금토일]\)"
    )

    # 모든 텍스트 노드 검색
    t_nodes = root.xpath(".//hp:t", namespaces=NS)

    for t in t_nodes:
        if t.text:
            match = date_pattern.search(t.text)
            if match:
                old_date = t.text
                t.text = new_date
                print(f"   🔄 날짜 교체: {old_date} → {new_date}")
                return True

    print("⚠️ 헤더 날짜를 찾지 못했습니다.")
    return False


def remove_approval_table_by_id(root):
    """ID가 1739249837인 승인 테이블만 정확히 제거"""

    print("🔍 승인 테이블 검색 중...")

    # 특정 ID로 테이블 찾기
    tables = root.xpath(".//hp:tbl[@id='1739249837']", namespaces=NS)

    if tables:
        table = tables[0]
        parent = table.getparent()

        if parent is not None:
            parent.remove(table)
            print("✅ 승인 테이블(ID: 1739249837) 제거 완료")
            return True

    # ID로 못 찾으면 "행정정보과장" 텍스트로 찾기
    print("   ID로 찾지 못함, 텍스트로 재검색...")
    all_tables = root.xpath(".//hp:tbl", namespaces=NS)

    for table in all_tables:
        texts = table.xpath(".//hp:t/text()", namespaces=NS)
        if any("행정정보과장" in text for text in texts):
            parent = table.getparent()
            if parent is not None:
                parent.remove(table)
                print("✅ 승인 테이블(텍스트 검색) 제거 완료")
                return True

    print("⚠️ 승인 테이블을 찾을 수 없음")
    return False


def normalize_followup_colon_spacing(root):
    """
    '□ 향후계획' 섹션 안에서
    - 콜론 앞 공백은 모두 제거
    - 콜론 뒤에는 공백 1칸만 유지
      예) '향후계획2    :   두팀이' → '향후계획2: 두팀이'
    """

    print("🔧 '향후계획' 섹션 콜론 주변 공백 정리 중...")

    paras = get_all_paras(root)
    in_followup = False
    changed_nodes = 0

    for p in paras:
        text = get_para_text(p) or ""

        # '□ 향후계획' 제목을 만나면 이후가 대상
        if "□ 향후계획" in text:
            in_followup = True
            continue

        # 혹시 이후에 다른 섹션이 있다면 종료
        if in_followup and text.strip().startswith("□") and "향후계획" not in text:
            in_followup = False

        if not in_followup:
            continue

        if ":" not in text and "：" not in text:
            continue

        for t_node in p.xpath(".//hp:t", namespaces=NS):
            if not t_node.text:
                continue

            original = t_node.text
            new_text = original

            # 1) 콜론 앞 공백 제거
            new_text = re.sub(r"\s+(:)", r"\1", new_text)
            # 2) 콜론 뒤 공백 1칸
            new_text = re.sub(r":\s*(\S)", r": \1", new_text)

            if new_text != original:
                t_node.text = new_text
                changed_nodes += 1

    print(f"   ✓ 콜론 주변 공백 정리된 텍스트 노드: {changed_nodes}개\n")


def replace_section(root, header_text: str, next_headers: List[str], content_lines: List[str]):
    """
    특정 섹션의 내용을 content_lines로 교체.

    - header_text 로 시작하는 소제목(예: '□ 개', '□ 테스트 현황') 아래 내용을 전부 지우고
    - 템플릿 문단 하나를 골라 골격만 복사한 뒤,
      그 안의 텍스트(<hp:t>) / linesegarray는 모두 삭제하고
      새 텍스트(<hp:t>) 하나만 넣음.
    """

    paras = get_all_paras(root)

    start_idx = None
    header_para = None

    for i, p in enumerate(paras):
        text = get_para_text(p)
        if header_text in text:
            start_idx = i
            header_para = p
            print(f"  ✓ 섹션 시작: '{header_text}' (index {i})")
            break

    if start_idx is None:
        print(f"  ⚠️ 헤더를 찾을 수 없음: '{header_text}'")
        return

    end_idx = len(paras)
    for i in range(start_idx + 1, len(paras)):
        text = get_para_text(paras[i])
        for next_h in next_headers:
            if next_h in text:
                end_idx = i
                print(f"  ✓ 섹션 종료: '{next_h}' (index {i})")
                break
        if end_idx < len(paras):
            break

    # 템플릿 문단(해당 섹션에서 첫 번째 본문 문단)을 기준으로 복제
    template_para = None
    for i in range(start_idx + 1, min(start_idx + 10, len(paras))):
        if i >= end_idx:
            break
        candidate = paras[i]
        text = get_para_text(candidate)
        if text and not any(h in text for h in next_headers):
            template_para = candidate
            break

    if template_para is None:
        print("  ⚠️ 템플릿 문단 없음")
        return

    # 기존 본문 제거
    removed_count = 0
    for p in list(paras[start_idx + 1:end_idx]):
        try:
            p.getparent().remove(p)
            removed_count += 1
        except Exception:
            pass

    print(f"  ✓ 제거: {removed_count}개 문단")

    # 새 본문 추가
    added_count = 0
    current_position = header_para

    for line in content_lines:
        new_para = deepcopy(template_para)

        # 1) 기존 텍스트 노드(<hp:t>) 전부 삭제
        for t_node in new_para.xpath(".//hp:t", namespaces=NS):
            parent = t_node.getparent()
            if parent is not None:
                parent.remove(t_node)

        # 2) 기존 linesegarray 전부 삭제 → HWP가 자동으로 줄나눔/줄간격 다시 계산
        for lsa in new_para.xpath(".//hp:linesegarray", namespaces=NS):
            parent = lsa.getparent()
            if parent is not None:
                parent.remove(lsa)

        # 3) run 하나 잡고, 없으면 새로 만든 뒤 그 안에 t 하나만 생성
        runs = new_para.xpath(".//hp:run", namespaces=NS)
        if runs:
            run = runs[0]
        else:
            run = etree.SubElement(new_para, f"{{{NS['hp']}}}run")

        t = etree.SubElement(run, f"{{{NS['hp']}}}t")
        # JSON에 '○ ...' 전체 문장을 넣어주면 그대로 출력됨
        t.text = line

        current_position.addnext(new_para)
        current_position = new_para
        added_count += 1

    print(f"  ✓ 추가: {added_count}개 문단\n")


def process_docheong_report(json_path: str, xml_template: str, xml_output: str):
    """JSON → XML 변환 (도청 동향보고서)"""
    print("\n" + "=" * 60)
    print("도청 동향보고서 XML 생성")
    print("=" * 60)

    report = DocheongReport.model_validate_json(
        Path(json_path).read_text(encoding="utf-8")
    )
    print(f"✓ JSON 로드: {Path(json_path).name}")

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(xml_template, parser)
    root = tree.getroot()
    print(f"✓ 템플릿 로드: {Path(xml_template).name}\n")

    # 날짜와 승인 테이블 수정
    print("📝 헤더 수정 중...")
    date_updated = update_header_date(root)
    table_removed = remove_approval_table_by_id(root)

    if not date_updated:
        print("❌ 날짜 업데이트 실패")
    if not table_removed:
        print("❌ 테이블 제거 실패")

    print()

    # 제목 업데이트 (머리글/표지용 제목들)
    update_text_only(root, "43", report.title)
    update_text_only(root, "31", report.title)
    print(f"✓ 제목: '{report.title}'\n")

    # 섹션별 내용 교체
    print("섹션 업데이트:")
    print("-" * 60)

    replace_section(root, "□ 개", ["□ 테스트 현황"], report.overview)
    replace_section(root, "□ 테스트 현황", ["□ 주요이슈"], report.test_status)
    replace_section(root, "□ 주요이슈", ["□ 향후계획"], report.key_issues)
    replace_section(root, "□ 향후계획", [], report.followup)

    # 🔹 줄 간격(spacing)은 더 이상 강제로 건드리지 않음
    #    → HWP가 자동 줄바꿈/줄간격을 다시 계산하게 둠

    # 🔹 향후계획 섹션의 ":" 앞/뒤 공백 정리 (앞 0칸, 뒤 1칸)
    normalize_followup_colon_spacing(root)

    # 저장
    Path(xml_output).parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(xml_output),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=False,
    )

    print("=" * 60)
    print(f"✅ 완료: {xml_output}")
    print("=" * 60 + "\n")


def find_content_start_para(root):
    """
    본문 시작 위치를 찾음 (첫 번째 □ 섹션 헤더)
    """
    paras = get_all_paras(root)
    for i, p in enumerate(paras):
        text = get_para_text(p)
        if text and text.strip().startswith("□"):
            return i, p
    return None, None


def remove_all_content_sections(root):
    """
    모든 □ 섹션과 그 내용을 제거하고, 첫 번째 섹션 헤더의 위치와 템플릿 문단을 반환
    """
    paras = get_all_paras(root)

    # 첫 번째 섹션 헤더 찾기
    start_idx = None
    first_section_para = None
    template_para = None

    for i, p in enumerate(paras):
        text = get_para_text(p)
        if text and text.strip().startswith("□"):
            if start_idx is None:
                start_idx = i
                first_section_para = p
                # 템플릿 문단 찾기 (섹션 헤더 바로 다음 문단)
                if i + 1 < len(paras):
                    template_para = paras[i + 1]
            break

    if start_idx is None:
        print("⚠️ 섹션 헤더를 찾을 수 없음")
        return None, None, None

    # 첫 번째 섹션 헤더 이후의 모든 문단 제거
    removed_count = 0
    for p in list(paras[start_idx:]):
        try:
            parent = p.getparent()
            if parent is not None:
                parent.remove(p)
                removed_count += 1
        except Exception:
            pass

    print(f"✓ 기존 섹션 제거: {removed_count}개 문단")

    return start_idx, first_section_para, template_para


def create_section_header_para(template_para, header_text: str):
    """
    섹션 헤더 문단 생성 (□ 로 시작하는 제목)
    """
    new_para = deepcopy(template_para)

    # 기존 텍스트 노드 제거
    for t_node in new_para.xpath(".//hp:t", namespaces=NS):
        parent = t_node.getparent()
        if parent is not None:
            parent.remove(t_node)

    # linesegarray 제거
    for lsa in new_para.xpath(".//hp:linesegarray", namespaces=NS):
        parent = lsa.getparent()
        if parent is not None:
            parent.remove(lsa)

    # 새 텍스트 추가
    runs = new_para.xpath(".//hp:run", namespaces=NS)
    if runs:
        run = runs[0]
    else:
        run = etree.SubElement(new_para, f"{{{NS['hp']}}}run")

    t = etree.SubElement(run, f"{{{NS['hp']}}}t")
    t.text = header_text

    return new_para


def create_content_para(template_para, content_text: str):
    """
    내용 문단 생성
    """
    new_para = deepcopy(template_para)

    # 기존 텍스트 노드 제거
    for t_node in new_para.xpath(".//hp:t", namespaces=NS):
        parent = t_node.getparent()
        if parent is not None:
            parent.remove(t_node)

    # linesegarray 제거
    for lsa in new_para.xpath(".//hp:linesegarray", namespaces=NS):
        parent = lsa.getparent()
        if parent is not None:
            parent.remove(lsa)

    # 새 텍스트 추가
    runs = new_para.xpath(".//hp:run", namespaces=NS)
    if runs:
        run = runs[0]
    else:
        run = etree.SubElement(new_para, f"{{{NS['hp']}}}run")

    t = etree.SubElement(run, f"{{{NS['hp']}}}t")
    t.text = content_text

    return new_para


def process_dynamic_report(json_path: str, xml_template: str, xml_output: str):
    """JSON → XML 변환 (동적 섹션 보고서)"""
    print("\n" + "=" * 60)
    print("동적 섹션 보고서 XML 생성")
    print("=" * 60)

    report = DynamicReport.model_validate_json(
        Path(json_path).read_text(encoding="utf-8")
    )
    print(f"✓ JSON 로드: {Path(json_path).name}")
    print(f"✓ 섹션 수: {len(report.sections)}개")

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(xml_template, parser)
    root = tree.getroot()
    print(f"✓ 템플릿 로드: {Path(xml_template).name}\n")

    # 날짜와 승인 테이블 수정
    print("📝 헤더 수정 중...")
    date_updated = update_header_date(root)
    table_removed = remove_approval_table_by_id(root)

    if not date_updated:
        print("❌ 날짜 업데이트 실패")
    if not table_removed:
        print("❌ 테이블 제거 실패")

    print()

    # 제목 업데이트
    update_text_only(root, "43", report.title)
    update_text_only(root, "31", report.title)
    print(f"✓ 제목: '{report.title}'\n")

    # 기존 모든 섹션 내용 가져오기 (템플릿 문단 확보용)
    paras = get_all_paras(root)

    # 첫 번째 섹션 헤더와 템플릿 문단 찾기
    first_section_idx = None
    first_section_para = None
    template_para = None

    for i, p in enumerate(paras):
        text = get_para_text(p)
        if text and text.strip().startswith("□"):
            first_section_idx = i
            first_section_para = p
            # 템플릿 문단 찾기 (섹션 헤더 다음의 본문 문단)
            for j in range(i + 1, min(i + 10, len(paras))):
                candidate = paras[j]
                cand_text = get_para_text(candidate)
                if cand_text and not cand_text.strip().startswith("□"):
                    template_para = candidate
                    break
            break

    if first_section_idx is None or template_para is None:
        print("⚠️ 템플릿 섹션을 찾을 수 없음")
        return

    # 섹션 헤더용 템플릿도 저장
    header_template = first_section_para

    # 첫 번째 섹션 헤더 이후 모든 문단 제거
    removed_count = 0
    for p in list(paras[first_section_idx:]):
        try:
            parent = p.getparent()
            if parent is not None:
                parent.remove(p)
                removed_count += 1
        except Exception:
            pass

    print(f"✓ 기존 섹션 제거: {removed_count}개 문단")

    # 삽입 위치 찾기 (제거된 첫 번째 섹션 이전 위치)
    paras = get_all_paras(root)
    if paras:
        insert_after = paras[-1]
    else:
        print("⚠️ 삽입 위치를 찾을 수 없음")
        return

    # 동적 섹션 생성
    print("\n섹션 생성:")
    print("-" * 60)

    current_position = insert_after
    total_added = 0

    for section in report.sections:
        # 섹션 헤더 생성
        header_para = create_section_header_para(header_template, section.header)
        current_position.addnext(header_para)
        current_position = header_para
        total_added += 1

        print(f"  ✓ 섹션: '{section.header}' ({len(section.content)}개 항목)")

        # 섹션 내용 생성
        for line in section.content:
            content_para = create_content_para(template_para, line)
            current_position.addnext(content_para)
            current_position = content_para
            total_added += 1

    print(f"\n✓ 총 {total_added}개 문단 추가")

    # 저장
    Path(xml_output).parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(xml_output),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=False,
    )

    print("=" * 60)
    print(f"✅ 완료: {xml_output}")
    print("=" * 60 + "\n")
