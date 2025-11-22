# jbnu_report.py
from pathlib import Path
import shutil
import zipfile
import time
from datetime import datetime


def copy_folder(src: str, dst: str):
    """
    HWPX 템플릿 폴더 전체를 작업 폴더로 복사하는 유틸.

    - src: 원본 템플릿 폴더 경로 (문자열 또는 Path 가능)
    - dst: 작업용 복사본 폴더 경로
    """
    src_path = Path(src)
    dst_path = Path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"템플릿 폴더가 존재하지 않습니다: {src_path}")

    # 기존 작업 폴더가 있으면 삭제 후 새로 복사
    if dst_path.exists():
        shutil.rmtree(dst_path)

    shutil.copytree(src_path, dst_path)
    print(f"  ✅ 템플릿 복사: {src_path} → {dst_path}")


def zip_as_hwpx(src_folder: str, output_hwpx: str):
    """
    src_folder 안의 구조를 그대로 유지하면서 .hwpx(zip) 파일 생성.

    - mimetype 은 반드시 첫 번째, STORED(무압축)으로 넣고
    - 나머지는 DEFLATED로 압축
    - ZIP 규격상 1980년 이전 타임스탬프는 허용되지 않으므로,
      그런 경우 최소 1980-01-01 00:00:00 으로 보정해서 넣는다.
    """
    src_path = Path(src_folder)
    output_hwpx = Path(output_hwpx)

    if not src_path.exists():
        raise FileNotFoundError(f"압축할 폴더가 존재하지 않습니다: {src_path}")

    print(f"\n  ZIP 생성 중: {output_hwpx}")

    # ZIP 타임스탬프 최소값 (1980-01-01 00:00:00)
    min_ts = datetime(1980, 1, 1, 0, 0, 0).timestamp()

    # 전체 파일 목록
    all_files = [p for p in src_path.rglob("*") if p.is_file()]

    # mimetype 파일은 규격상 맨 앞에, STORED로 넣기 위해 분리
    mimetype_path = src_path / "mimetype"
    other_files = []

    if mimetype_path in all_files:
        all_files.remove(mimetype_path)
        other_files = all_files
    else:
        mimetype_path = None
        other_files = all_files

    with zipfile.ZipFile(output_hwpx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1) mimetype: 첫 번째 + STORED (무압축)
        if mimetype_path and mimetype_path.exists():
            st = mimetype_path.stat()
            # 1980년 이전이면 최소값으로 보정
            mtime = max(st.st_mtime, min_ts)
            date_time = time.localtime(mtime)[:6]

            with mimetype_path.open("rb") as f:
                info = zipfile.ZipInfo("mimetype", date_time=date_time)
                info.compress_type = zipfile.ZIP_STORED  # 무압축
                zf.writestr(info, f.read())

            print("    ✓ mimetype (STORED)")

        # 2) 나머지 파일들: DEFLATED
        for path in other_files:
            arcname = path.relative_to(src_path).as_posix()

            st = path.stat()
            # 1980년 이전 타임스탬프 보정
            mtime = max(st.st_mtime, min_ts)
            date_time = time.localtime(mtime)[:6]

            with path.open("rb") as f:
                info = zipfile.ZipInfo(arcname, date_time=date_time)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, f.read())

            print(f"    ✓ {arcname} (DEFLATED)")

    print(f"  ✅ ZIP 생성 완료: {output_hwpx}")
