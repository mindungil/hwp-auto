# check_all_styles.py
from lxml import etree

NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hh': 'http://www.hancom.co.kr/hwpml/2011/head'
}

# section0.xml에서 사용되는 모든 charPr 찾기
section_path = './hwpx_report/hwpx_file/도청동향보고서_복사본/Contents/section0.xml'
parser = etree.XMLParser(remove_blank_text=False)
tree = etree.parse(section_path, parser)
root = tree.getroot()

# 모든 run에서 사용된 charPrIDRef 수집
char_pr_ids = set()
runs = root.xpath(".//hp:run", namespaces=NS)
for run in runs:
    char_id = run.get('charPrIDRef')
    if char_id:
        char_pr_ids.add(char_id)

print("=" * 60)
print("section0.xml에서 사용 중인 charPr ID 목록:")
print("=" * 60)
print(sorted(char_pr_ids, key=int))

# header.xml에서 각 charPr의 spacing 확인
# ⚠️ 기존: ./hwpx_report/template/도청동향보고서_템플릿/Contents/header.xml
# → 한글 폴더명 대신 영어 폴더명 사용
header_path = './hwpx_report/template/docheong_template/Contents/header.xml'
tree2 = etree.parse(header_path, parser)
root2 = tree2.getroot()

print("\n" + "=" * 60)
print("각 charPr의 현재 spacing 값:")
print("=" * 60)

for char_id in sorted(char_pr_ids, key=int):
    char_prs = root2.xpath(f".//hh:charPr[@id='{char_id}']", namespaces=NS)
    if char_prs:
        char_pr = char_prs[0]
        spacings = char_pr.xpath(".//hh:spacing", namespaces=NS)
        if spacings:
            spacing_val = spacings[0].get('hangul', '0')
            print(f"  charPr id={char_id:>2} : spacing={spacing_val:>3}")
