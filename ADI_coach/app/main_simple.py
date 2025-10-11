"""
ADI Coach FastAPI Application - 간소화 버전
인증 없이 핵심 기능만 제공
"""

from __future__ import annotations

import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.core import get_core
from app.store_sqlite import get_store

# Pydantic 모델 정의
class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    text: str = Field(..., description="사용자 메시지")
    msg_count: int = Field(0, description="최근 24시간 메시지 수")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="대화 기록")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="사용자 컨텍스트")

class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    F: float = Field(..., description="Frequency 점수")
    E: float = Field(..., description="Emotion 점수")
    D: float = Field(..., description="Dependency 점수")
    ADI: float = Field(..., description="ADI 점수")
    delay: float = Field(..., description="응답 지연 시간")
    mode: str = Field(..., description="응답 모드")
    reply: str = Field(..., description="AI 응답")
    quality_score: float = Field(..., description="응답 품질 점수")
    crisis_detected: bool = Field(..., description="위기 상황 감지 여부")
    learning_intent: bool = Field(..., description="학습 의도 여부")
    debug: Dict[str, Any] = Field(..., description="디버그 정보")

class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    timestamp: float
    core_available: bool
    store_available: bool
    mistral_available: bool

# FastAPI 앱 생성
app = FastAPI(
    title="ADI Coach API",
    description="AI 의존을 감지하고 자립을 유도하는 AI 코치",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 핵심 컴포넌트 초기화
core = get_core()
store = get_store()

@app.get("/", response_model=Dict[str, str])
async def root():
    """루트 엔드포인트"""
    return {
        "message": "ADI Coach API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        core_available=core is not None,
        store_available=store is not None,
        mistral_available=core.llm_available if core else False
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    채팅 엔드포인트
    
    사용자 메시지를 받아서 ADI 분석 및 응답을 생성합니다.
    """
    try:
        # 메시지 처리
        result = core.process_message(
            text=request.text,
            msg_count=request.msg_count,
            conversation_history=request.conversation_history,
            user_context=request.user_context
        )
        
        # 데이터베이스에 저장
        if store:
            try:
                store.save_message(
                    user_id=request.user_context.get("user_id", "anonymous"),
                    text=request.text,
                    reply=result["reply"],
                    adi_score=result["ADI"],
                    mode=result["mode"],
                    emotion_score=result["E"]
                )
            except Exception as e:
                print(f"데이터베이스 저장 실패: {e}")
        
        return ChatResponse(**result)
        
    except Exception as e:
        print(f"채팅 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/stats/{user_id}")
async def get_stats(user_id: str):
    """사용자 통계 조회"""
    try:
        if not store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="데이터베이스 서비스를 사용할 수 없습니다"
            )
        
        stats = store.get_user_stats(user_id)
        return stats
        
    except Exception as e:
        print(f"통계 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/trend/{user_id}")
async def get_trend(user_id: str, days: int = 7):
    """사용자 ADI 트렌드 조회"""
    try:
        if not store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="데이터베이스 서비스를 사용할 수 없습니다"
            )
        
        trend = store.get_adi_trend(user_id, days)
        return trend
        
    except Exception as e:
        print(f"트렌드 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"트렌드 조회 중 오류가 발생했습니다: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)