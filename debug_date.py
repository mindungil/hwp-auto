# debug_date.py (수정 버전)
from lxml import etree
import os

NS = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}

# 올바른 경로
xml_path = './hwpx_report/template/docheong_template/Contents/section0.xml'

print(f"✅ 파일 경로: {xml_path}\n")

# XML 로드
parser = etree.XMLParser(remove_blank_text=False)
tree = etree.parse(xml_path, parser)
root = tree.getroot()

# 모든 텍스트 노드 검색
all_texts = root.xpath(".//hp:t", namespaces=NS)

print("=" * 60)
print("날짜 형태 텍스트 찾기")
print("=" * 60)

count = 0
for i, t in enumerate(all_texts):
    if t.text and any(x in t.text for x in ["25", "11", "6", "'", "'"]):
        count += 1
        print(f"\n[{i}] 텍스트: {repr(t.text)}")
        
        # UTF-8 바이트 확인
        try:
            bytes_data = t.text.encode('utf-8')
            print(f"    UTF-8 bytes: {bytes_data}")
            
            # 첫 글자 유니코드
            if t.text:
                first_char = t.text[0]
                print(f"    첫 글자: '{first_char}' → U+{ord(first_char):04X}")
        except Exception as e:
            print(f"    인코딩 오류: {e}")
        
        # 테이블 정보
        parent = t.getparent()
        depth = 0
        while parent is not None and depth < 10:
            if 'tbl' in parent.tag:
                tbl_id = parent.get('id', 'no-id')
                print(f"    ✓ 테이블 ID: {tbl_id}")
                break
            parent = parent.getparent()
            depth += 1
        
        if count >= 5:  # 처음 5개만
            break

print(f"\n총 {count}개 발견")