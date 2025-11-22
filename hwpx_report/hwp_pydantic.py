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
