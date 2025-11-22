from pydantic import BaseModel
from typing import List

class SectionBullet(BaseModel):
    """섹션의 bullet 항목"""
    bullets: List[str]

class JBNUReport(BaseModel):
    """전북대 보고서"""
    title: str
    overview: SectionBullet
    status: SectionBullet
    issues: SectionBullet
    plans: SectionBullet

class DocheongReport(BaseModel):
    """도청 동향보고서 (단순화 버전)"""
    title: str
    overview: List[str]
    test_status: List[str]
    key_issues: List[str]
    followup: List[str]

# 동적 섹션 모델
class DynamicSection(BaseModel):
    """동적 섹션 구조"""
    header: str          # 섹션 헤더 (예: "□ 개요", "□ 분석결과")
    content: List[str]   # bullet points

class DynamicReport(BaseModel):
    """동적 섹션 보고서 - LLM이 섹션 구조를 자유롭게 결정"""
    title: str
    sections: List[DynamicSection]
