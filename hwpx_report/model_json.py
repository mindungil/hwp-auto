import json
import re
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# OpenAI API 키 (환경변수에서 가져오기)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI LLM 초기화
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4o-mini",
    max_tokens=4000,
    temperature=0.3,
)


def generate_response(prompt: str, system_message: str = "") -> str:
    """OpenAI LLM으로 프롬프트 응답 생성"""
    messages = []
    if system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    return response.content


def extract_json_block(text: str) -> str:
    """LLM 응답에서 JSON 블록만 추출"""
    # ```json ... ``` 형태 처리
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    text = text.strip()

    # 첫 번째 {...} 블록만 추출
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("JSON 블록을 찾을 수 없습니다.")
    return match.group()


def generate_docheong_json(content: str) -> dict:
    """
    자유 형식 회의 내용 → 도청 동향보고서 JSON 변환

    ⚠️ 주의: 반환 형식은 반드시 DocheongReport와 맞춰야 함.
      {
        "title": "보고서 제목",
        "overview": [ "...", ... ],
        "test_status": [ "...", ... ],
        "key_issues": [ "...", ... ],
        "followup": [ "...", ... ]
      }
    각 리스트 요소는 문자열 한 줄.
    """
    system_message = """
당신은 전라북도청의 행정·업무 보고서를 작성하는 전문가이다.
사용자가 입력한 회의/상황 설명을 읽고, 다음 JSON 형식으로 **개조식·보고서 문체**로 정리하라.

반드시 아래 **키 이름과 자료형**을 그대로 사용해야 한다.

{
  "title": "보고서 제목(짧게 요약)",
  "overview": [
    "○ (항목명1) 한 줄 요약 문장",
    "    - 필요하면 세부 설명 한 줄",
    "    ※ 비고가 있으면 이렇게 한 줄"
  ],
  "test_status": [
    "○ (현재 현황1) 한 줄 요약",
    "    - 세부 상황"
  ],
  "key_issues": [
    "○ (이슈1) 한 줄 요약",
    "○ (이슈2) 한 줄 요약"
  ],
  "followup": [
    "○ (향후 계획1) 한 줄 요약",
    "○ (향후 계획2) 한 줄 요약"
  ]
}

[섹션 의미]
- overview    : 전체 배경·개괄 설명, 중요한 전반 상황 요약
- test_status : 현재 진행 현황·상태 (서비스면 테스트 현황, 사람 이야기면 현재 활동 패턴 등)
- key_issues  : 문제점, 쟁점, 리스크
- followup    : 향후 계획, 필요한 조치, 액션 아이템

[항목 이름(괄호 안 텍스트) 작성 가이드]
- 서비스/테스트 관련 주제인 경우 예시:
    overview    : "○ (운영기간) ...", "○ (홍보방법) ..."
    test_status : "○ (접속자수) ...", "○ (사용토큰) ..."
- 개인 취미·업무 회의 등 다른 주제인 경우 상황에 맞는 이름으로 작성:
    overview    : "○ (취미 활동 개요) ...", "○ (회의 개요) ..."
    test_status : "○ (현재 취미 현황) ...", "○ (현재 추진 현황) ..."
    key_issues  : "○ (시간 부족 문제) ...", "○ (협업 이슈) ..."
    followup    : "○ (휴식일 설정 계획) ...", "○ (향후 지원 방안) ..."

[문체·형식 규칙 — 개조식·보고서 스타일]
1. 모든 문장은 **개조식 문체**로 작성할 것.
   - 문장 끝은 가급적 "~함", "~임", "~필요", "~계획임" 등 **체언+이다 / 명사형**으로 마무리.
   - 예: "스트레스 해소 수단으로 활용 중임", "시간 관리 보완 필요", "추가 예산 검토 계획임".
2. **문장 끝에 마침표( . )를 붙이지 말 것.**
   - "…중임.", "…필요." 처럼 끝에 점을 찍지 말고
   - "…중임", "…필요" 형태로 끝낼 것.
3. "~합니다", "~했습니다" 등의 서술식 종결어미는 가능한 한 사용하지 말 것.
4. 각 항목은 한 줄짜리 문장으로 간결하게 작성할 것 (불필요한 수식·감정 표현 배제).
5. 주관적·감상적 표현은 피하고, **사실·관찰·계획 중심**으로 정리할 것.

[형식 규칙 — JSON 구조]
1. JSON의 최상위 키는 **반드시** 다음 다섯 개만 존재해야 한다:
   - "title", "overview", "test_status", "key_issues", "followup"
2. 각 섹션 값은 문자열 리스트(list[str])여야 한다.
3. 각 항목은 항상 "○ "로 시작하고, 괄호 안의 항목명은 상황에 맞게 **구체적인 이름**으로 작성한다.
   - 예: "○ (운영기간) ...", "○ (홍보방법) ...",
         "○ (취미 활동 현황) ...", "○ (핵심 이슈) ..."
4. 세부 설명이 필요하면 같은 섹션 안에
   - "    - " 로 시작하는 문자열을 추가한다. (최대 한두 줄 정도로 짧게)
5. 비고가 필요하면
   - "    ※ " 로 시작하는 문자열을 추가한다.
6. 어떤 섹션에 넣을 내용이 없으면, 그 섹션은 빈 리스트 [] 로 둔다.
7. 각 문자열은 **한 줄짜리 문장**으로 작성하고, 줄바꿈 문자("\\n")는 포함하지 않는다.
8. 설명 텍스트는 JSON 바깥에 쓰지 말고, **JSON 전체만** 그대로 반환한다.
"""

    prompt = f"""다음 회의/상황 설명을 읽고 위에서 지정한 형식의 JSON을 생성하세요.

입력 텍스트:
\"\"\"{content}\"\"\""""

    print("🤖 OpenAI GPT로 JSON 생성 중...")
    response = generate_response(prompt, system_message)

    print("\n=== LLM 응답 ===")
    print(response)
    print("=" * 60 + "\n")

    try:
        json_str = extract_json_block(response)
        raw = json.loads(json_str)

        # 혹시 빠진 섹션이 있으면 기본값 채워 넣기
        cleaned = {
            "title": raw.get("title", "무제 보고서"),
            "overview": raw.get("overview", []) or [],
            "test_status": raw.get("test_status", []) or [],
            "key_issues": raw.get("key_issues", []) or [],
            "followup": raw.get("followup", []) or [],
        }

        # 기본적으로 list[str] 형태로 맞추기
        for key in ["overview", "test_status", "key_issues", "followup"]:
            value = cleaned[key]
            if isinstance(value, str):
                cleaned[key] = [value]
            elif isinstance(value, list):
                cleaned[key] = [str(v) for v in value]
            else:
                cleaned[key] = [str(value)]

        # 🔹 2차 후처리: 각 항목 끝의 불필요한 마침표(.) 제거
        def strip_trailing_period(s: str) -> str:
            s = s.rstrip()
            # 맨 끝에 있는 마침표 연속 제거 ("...." 같은 것도 한 번에 제거)
            s = re.sub(r"[.]+$", "", s)
            return s.rstrip()

        for key in ["overview", "test_status", "key_issues", "followup"]:
            cleaned[key] = [strip_trailing_period(v) for v in cleaned[key]]

        return cleaned

    except Exception as e:
        raise RuntimeError(f"❌ JSON 파싱 실패: {e}\n응답:\n{response}")


def generate_dynamic_json(content: str) -> dict:
    """
    자유 형식 회의 내용 → 동적 섹션 JSON 변환
    LLM이 섹션 수와 이름을 자유롭게 결정

    반환 형식:
      {
        "title": "보고서 제목",
        "sections": [
          {"header": "□ 섹션명1", "content": ["내용1", "내용2", ...]},
          {"header": "□ 섹션명2", "content": ["내용1", "내용2", ...]},
          ...
        ]
      }
    """
    system_message = """
당신은 전라북도청의 행정·업무 보고서를 작성하는 전문가이다.
사용자가 입력한 회의/상황 설명을 읽고, **내용에 맞는 섹션을 자유롭게 구성**하여 JSON 형식으로 정리하라.

중요: 섹션의 수와 이름은 **입력 내용에 따라 동적으로 결정**한다.
- 내용이 많으면 5-7개 섹션으로 세분화
- 내용이 간단하면 2-3개 섹션으로 간결하게
- 섹션 이름은 내용을 가장 잘 반영하는 것으로 자유롭게 작성

반드시 아래 JSON 형식을 사용해야 한다:

{
  "title": "보고서 제목(짧게 요약)",
  "sections": [
    {
      "header": "□ 섹션명",
      "content": [
        "○ (항목명) 한 줄 요약 문장",
        "    - 필요하면 세부 설명 한 줄",
        "    ※ 비고가 있으면 이렇게 한 줄"
      ]
    }
  ]
}

[섹션 이름 예시 - 상황에 맞게 자유롭게]
- 서비스/프로젝트: "□ 사업 개요", "□ 추진 현황", "□ 주요 성과", "□ 문제점 및 개선사항", "□ 향후 계획"
- 회의 보고: "□ 회의 개요", "□ 논의 사항", "□ 결정 사항", "□ 후속 조치"
- 분석 보고: "□ 분석 배경", "□ 데이터 현황", "□ 분석 결과", "□ 시사점", "□ 제언"
- 일반 보고: "□ 배경", "□ 현황", "□ 문제점", "□ 대응방안", "□ 기대효과"

[문체·형식 규칙 — 개조식·보고서 스타일]
1. 모든 문장은 **개조식 문체**로 작성할 것.
   - 문장 끝은 가급적 "~함", "~임", "~필요", "~계획임" 등 **체언+이다 / 명사형**으로 마무리.
   - 예: "스트레스 해소 수단으로 활용 중임", "시간 관리 보완 필요", "추가 예산 검토 계획임".
2. **문장 끝에 마침표( . )를 붙이지 말 것.**
3. "~합니다", "~했습니다" 등의 서술식 종결어미는 사용하지 말 것.
4. 각 항목은 한 줄짜리 문장으로 간결하게 작성할 것.
5. 주관적·감상적 표현은 피하고, **사실·관찰·계획 중심**으로 정리할 것.

[형식 규칙 — JSON 구조]
1. 각 섹션의 header는 반드시 "□ "로 시작해야 한다.
2. 각 content 항목은 "○ "로 시작하고, 세부사항은 "    - ", 비고는 "    ※ "로 시작한다.
3. 섹션에 넣을 내용이 없으면 해당 섹션을 생성하지 않는다.
4. 각 문자열은 한 줄짜리 문장으로 작성하고, 줄바꿈 문자("\\n")는 포함하지 않는다.
5. JSON 전체만 반환하고, 설명 텍스트는 포함하지 않는다.
"""

    prompt = f"""다음 회의/상황 설명을 읽고 내용에 맞는 섹션을 자유롭게 구성하여 JSON을 생성하세요.

입력 텍스트:
\"\"\"{content}\"\"\""""

    print("🤖 OpenAI GPT로 동적 섹션 JSON 생성 중...")
    response = generate_response(prompt, system_message)

    print("\n=== LLM 응답 ===")
    print(response)
    print("=" * 60 + "\n")

    try:
        json_str = extract_json_block(response)
        raw = json.loads(json_str)

        # 필수 필드 검증
        cleaned = {
            "title": raw.get("title", "무제 보고서"),
            "sections": []
        }

        # sections 처리
        sections = raw.get("sections", [])
        if not isinstance(sections, list):
            sections = []

        for section in sections:
            if isinstance(section, dict):
                header = section.get("header", "□ 기타")
                content = section.get("content", [])

                # content가 list[str]인지 확인
                if isinstance(content, str):
                    content = [content]
                elif isinstance(content, list):
                    content = [str(v) for v in content]
                else:
                    content = [str(content)]

                # 마침표 제거
                content = [re.sub(r"[.]+$", "", v.rstrip()).rstrip() for v in content]

                cleaned["sections"].append({
                    "header": header,
                    "content": content
                })

        # 섹션이 하나도 없으면 기본 섹션 추가
        if not cleaned["sections"]:
            cleaned["sections"] = [{
                "header": "□ 내용",
                "content": ["○ (내용) 입력된 내용이 없음"]
            }]

        return cleaned

    except Exception as e:
        raise RuntimeError(f"❌ JSON 파싱 실패: {e}\n응답:\n{response}")
