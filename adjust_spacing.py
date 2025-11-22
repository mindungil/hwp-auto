# adjust_spacing.py
from lxml import etree

NS = {'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}

# 템플릿 header.xml 수정
# ⚠️ 기존: ./hwpx_report/template/도청동향보고서_템플릿/Contents/header.xml
# 한글 폴더명(NFC/NFD) 문제를 피하기 위해 영어 폴더명으로 변경
header_path = './hwpx_report/template/docheong_template/Contents/header.xml'

parser = etree.XMLParser(remove_blank_text=False)
tree = etree.parse(header_path, parser)
root = tree.getroot()

print("자간 조정 중...")
print("=" * 60)

# 본문용 charPr의 spacing 수정
# charPr id가 15, 21, 22, 24, 25, 26, 27 등이 본문 스타일
body_char_ids = ['15', '21', '22', '24', '25', '26', '27', '28', '29', '30', '31']

count = 0
for char_id in body_char_ids:
    char_prs = root.xpath(f".//hh:charPr[@id='{char_id}']", namespaces=NS)
    
    for char_pr in char_prs:
        spacings = char_pr.xpath(".//hh:spacing", namespaces=NS)
        
        if spacings:
            spacing = spacings[0]
            # 현재 값 가져오기
            old_val = spacing.get('hangul', '0')
            
            # 자간을 5로 설정 (약간 넓게)
            # 원하면 10, 15 등으로 더 넓힐 수 있음
            new_val = '5'  # ← 여기서 값 조정 (5~20 추천)
            
            spacing.set('hangul', new_val)
            spacing.set('latin', new_val)
            spacing.set('hanja', new_val)
            spacing.set('japanese', new_val)
            spacing.set('other', new_val)
            spacing.set('symbol', new_val)
            spacing.set('user', new_val)
            
            print(f"✓ charPr id={char_id}: {old_val} → {new_val}")
            count += 1

# 저장
tree.write(header_path, encoding='utf-8', xml_declaration=True, pretty_print=False)

print("=" * 60)
print(f"✅ 총 {count}개 스타일 자간 조정 완료")
print(f"   파일: {header_path}")
