import os
from openai import OpenAI
from dotenv import load_dotenv
from src.chroma_db import query_documents

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
    base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
)

# # type: ignore 를 추가하면 에디터의 노란색 경고줄을 숨길 수 있습니다.
MODEL = os.getenv("OPENAI_MODEL", "google/gemma-3-4b") # type: ignore

def build_context(docs: list[dict]) -> str:
    """검색된 문서 청크를 컨텍스트 문자열로 변환"""
    context_parts = []
    for i, doc in enumerate(docs, 1):
        context_parts.append(f"[출처: {doc['source']}]\n{doc['text']}")
    return "\n\n".join(context_parts)

def rag_answer(messages_history: list) -> dict:
    """
    RAG 파이프라인:
    1. 마지막 질문을 추출하여 ChromaDB에서 관련 문서 검색
    2. 전체 대화 기록(messages_history)과 검색된 컨텍스트를 포함하여 LM Studio 모델에 전달
    3. 응답 반환
    """
    # Streamlit에서 전달받은 전체 기록 중, 가장 마지막 메시지(현재 사용자의 질문)만 뽑아서 문서 검색에 사용합니다.
    current_question = messages_history[-1]["content"]

    # 1. 관련 문서 검색
    docs = query_documents(current_question, n_results=3)

    # 2. LLM에 전달할 최종 메시지 리스트 생성
    messages = []

    if not docs:
        # 관련 문서 없으면 일반 질문용 시스템 프롬프트 추가
        messages.append({"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다. 업로드된 관련 문서가 없으므로 일반적인 지식을 바탕으로 답변하세요."})
        source_info = None
    else:
        # 관련 문서 있으면 컨텍스트를 포함한 시스템 프롬프트 추가
        context = build_context(docs)
        messages.append({
            "role": "system",
            "content": (
                "당신은 똑똑하고 친절한 '스마트 온실 관리 AI 어시스턴트'입니다.\n"
                "상황에 따라 아래의 규칙을 유연하게 적용하여 대답하세요.\n\n"
                "1. 일상 대화 및 일반 지식: 사용자가 인사를 하거나 문서와 관련 없는 일반적인 질문(예: 날씨, 농담, IT, 일상 등)을 하면, 문서를 무시하고 당신의 기본 지식을 활용해 자연스럽고 친절하게 대화하세요.\n"
                "2. 전문 질문: 스마트팜, 토마토 생육, 기상 데이터 등 제공된 문서와 관련된 질문이라면, 반드시 아래 [참고 문서]의 내용을 우선적으로 기반하여 정확하게 답변하세요.\n"
                "3. 문서에 내용이 없을 때: 전문 질문이지만 [참고 문서]에 정답이 없다면, '제공된 문서에는 해당 내용이 없지만...'이라고 안내한 뒤, 당신의 일반 지식을 바탕으로 조언을 덧붙여주세요.\n\n"
                "4. 출력 형식 주의사항: 숫자 범위를 나타낼 때는 마크다운 취소선 오류를 방지하기 위해 물결표(~) 기호를 절대 사용하지 말고, 반드시 하이픈(-)이나 '에서'라는 단어를 사용하세요. (예: 20-25도, 20에서 25도)\n\n"
                f"=== 참고 문서 ===\n{context}\n=== 참고 문서 끝 ==="
            )
        })
        source_info = list(set(d["source"] for d in docs))

    filtered_history = []
    for msg in messages_history:
        # 기본 인사말 제외
        if msg["role"] == "assistant" and any(k in msg["content"] for k in ("스마트 온실 관리", "상태:")):
            continue
        
        # 연속된 동일 역할 메시지 병합 (오류 방지)
        if filtered_history and filtered_history[-1]["role"] == msg["role"]:
            filtered_history[-1] = {
                "role": msg["role"], 
                "content": f"{filtered_history[-1]['content']}\n{msg['content']}"
            }
        else:
            filtered_history.append({"role": msg["role"], "content": msg["content"]})

    # 최근 10개 기록만 유지 및 시작 역할 검증 (System 뒤엔 반드시 User)
    MAX_HISTORY = 10
    recent_history = filtered_history[-MAX_HISTORY:]
    
    if recent_history and recent_history[0]["role"] == "assistant":
        recent_history = recent_history[1:]

    messages.extend(recent_history)

    # 모델 호출
    response = client.chat.completions.create(
        model=MODEL, # type: ignore
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": source_info
    }
