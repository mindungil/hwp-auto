import zipfile
from pathlib import Path


def create_hwpx_from_folder(folder_path: str, output_path: str):
    """폴더를 HWPX 파일로 압축"""
    
    folder = Path(folder_path)
    output = Path(output_path)
    
    print(f"\n  ZIP 생성 중: {output}")
    
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # mimetype은 STORED로 (압축 안함)
        mimetype_file = folder / 'mimetype'
        if mimetype_file.exists():
            zipf.write(mimetype_file, 'mimetype', compress_type=zipfile.ZIP_STORED)
            print(f"    ✓ mimetype (STORED)")
        
        # 모든 파일 추가
        for file_path in sorted(folder.rglob('*')):
            if file_path.is_file() and file_path.name != 'mimetype':
                arcname = file_path.relative_to(folder)
                zipf.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)
                
                if file_path.suffix == '.xml':
                    print(f"    ✓ {arcname} (DEFLATED)")
    
    print(f"✅ 압축 완료: {output}\n")