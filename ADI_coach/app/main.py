"""
ADI Coach FastAPI Application
입력: HTTP 요청 (POST /chat, GET /stats 등)
출력: JSON 응답 (ADI 점수, 응답, 통계 등)
목표: 간단한 REST API로 ADI Coach 기능 제공

TODO: 향후 개선사항들
- [ ] 인증/인가 시스템 (JWT 토큰)
- [ ] API 레이트 리미팅
- [ ] 요청/응답 로깅 및 모니터링
- [ ] API 버전 관리
- [ ] Swagger 문서 자동화
- [ ] 헬스체크 엔드포인트
- [ ] 메트릭 수집 (Prometheus)
- [ ] 에러 추적 (Sentry)
"""

from __future__ import annotations

import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, status, Request, Depends
from pydantic import BaseModel, Field

from app.core import get_core
from app.store_sqlite import get_store
from app.auth import (
    auth_manager, 
    UserCreate, 
    UserLogin, 
    User, 
    Token, 
    get_current_active_user,
    create_token_response
)
from app.rate_limiter import rate_limit, get_rate_limit_status

class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="사용자 메시지")
    msg_count: int = Field(0, ge=0, le=1000, description="최근 24시간 메시지 수 (자동 계산됨)")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="대화 기록")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="사용자 컨텍스트")


class ChatResponse(BaseModel):
    F: float = Field(..., description="빈도 특성 점수")
    E: float = Field(..., description="감정 점수")
    D: float = Field(..., description="의존성 점수")
    ADI: float = Field(..., description="ADI 점수 (0-10)")
    delay: float = Field(..., description="응답 지연 시간 (초)")
    mode: str = Field(..., description="모드 (support/coaching/mirror)")
    reply: str = Field(..., description="AI 응답")
    quality_score: float = Field(..., description="응답 품질 점수 (0-1)")
    crisis_detected: bool = Field(..., description="위기 상황 감지 여부")
    learning_intent: bool = Field(..., description="학습 의도 여부")
    debug: Dict[str, Any] = Field(..., description="디버그 정보")


app = FastAPI(
    title="ADI Coach API", 
    version="1.0.0",
    description="한국어 대화 기반 ADI 계산 및 AI 코칭 API"
)


@app.get("/")
def root():
    """API 루트 엔드포인트"""
    return {
        "ok": True, 
        "message": "ADI Coach API", 
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/chat", response_model=ChatResponse)
@rate_limit("chat")
async def chat(
    request: ChatRequest,
    http_request: Request
    # current_user: Dict[str, Any] = Depends(get_current_active_user)  # 임시 비활성화
):
    """
    메인 채팅 엔드포인트 (인증 필요)
    사용자 메시지를 분석하고 ADI 기반 응답을 생성합니다.
    """
    try:
        core = get_core()
        store = get_store()
        
        # 사용자 ID 결정 (user_context에서 가져오거나 기본값 사용)
        user_id = request.user_context.get("user_id", "test")
        
        # 최근 12시간 '부정적' 메시지 수 자동 계산 (ADI 산출에 사용)
        neg_msg_count_12h = 0
        try:
            if hasattr(store, 'get_negative_message_count_last_12h'):
                neg_msg_count_12h = store.get_negative_message_count_last_12h(user_id)
            elif hasattr(store, 'get_message_count_last_12h'):
                # 폴백: 부정 메시지 수 API가 없으면 전체 메시지 수를 근사값으로 사용
                neg_msg_count_12h = store.get_message_count_last_12h(user_id)
            else:
                # 최후 폴백: 24시간 값을 절반 가중치로 근사
                _approx_24h = store.get_message_count_last_24h(user_id)
                neg_msg_count_12h = max(0, int(round(_approx_24h * 0.5)))
        except Exception:
            neg_msg_count_12h = 0
        
        # 메시지 처리 (자동 계산된 msg_count 사용)
        result = core.process_message(
            text=request.text,
            msg_count=neg_msg_count_12h,
            conversation_history=request.conversation_history,
            user_context={
                **(request.user_context or {}),
                "user_id": user_id,
                "neg_msg_count_12h": neg_msg_count_12h,
                "msg_count_12h": neg_msg_count_12h  # 하위 호환용
            }
        )
        
        # 위기 상황 감지 시 특별 처리
        if result.get("crisis_detected", False):
            # 위기 상황 응답으로 교체
            result["reply"] = (
                "지금 정말 힘든 시간을 보내고 계시는군요. "
                "혼자 견디려고 하지 마세요. "
                "전문가의 도움을 받는 것이 중요합니다. "
                "생명의전화 1588-9191, 청소년전화 1388로 연락해보세요. "
                "당신은 혼자가 아닙니다."
            )
            result["mode"] = "crisis"
            result["delay"] = 0.5  # 위기 상황 시 빠른 응답
        
        # 데이터베이스 저장
        store.save_message({
            "user_id": user_id,
            "timestamp": time.time(),
            "text": request.text,
            "F": result["F"],
            "E": result["E"],
            "D": result["D"],
            "ADI": result["ADI"],
            "mode": result["mode"],
            "reply": result["reply"],
            "debug": result["debug"]
        })
        
        return ChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")


@app.get("/stats/me")
@rate_limit("stats")
async def get_my_stats(http_request: Request, user_id: str = "test"):
    """내 통계 조회 (임시로 인증 비활성화)"""
    try:
        store = get_store()
        # user_id = current_user["username"]  # 임시 비활성화
        stats = store.get_user_stats(user_id)
        return {"user_id": user_id, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 오류: {str(e)}")


@app.get("/trend/me")
def get_my_adi_trend(
    days: int = 7, 
    user_id: str = "test"
):
    """내 ADI 변화 추이 조회 (임시로 인증 비활성화)"""
    try:
        store = get_store()
        # user_id = current_user["username"]  # 임시 비활성화
        trend = store.get_adi_trend(user_id, days)
        return {"user_id": user_id, "days": days, "trend": trend}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추이 조회 오류: {str(e)}")


@app.post("/auth/register", response_model=User)
def register(user_data: UserCreate):
    """사용자 회원가입"""
    try:
        user = auth_manager.create_user(user_data)
        # 비밀번호 제거 후 반환
        user.pop("hashed_password", None)
        return User(**user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")


@app.post("/auth/login", response_model=Token)
@rate_limit("auth")
async def login(http_request: Request, login_data: UserLogin):
    """사용자 로그인"""
    user = auth_manager.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return create_token_response(user["username"])


@app.get("/auth/me", response_model=User)
def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """현재 사용자 정보 조회"""
    # 비밀번호 제거 후 반환
    user_info = current_user.copy()
    user_info.pop("hashed_password", None)
    return User(**user_info)


@app.post("/auth/refresh", response_model=Token)
def refresh_token(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """토큰 갱신"""
    return create_token_response(current_user["username"])


@app.get("/rate-limit/status")
def get_rate_limit_status_endpoint(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """레이트 리미트 상태 조회"""
    from app.rate_limiter import get_client_identifier
    
    identifier = get_client_identifier(request, current_user["username"])
    
    return {
        "identifier": identifier,
        "chat": get_rate_limit_status(identifier, "chat"),
        "stats": get_rate_limit_status(identifier, "stats"),
        "auth": get_rate_limit_status(identifier, "auth")
    }


@app.get("/health")
def health_check():
    """헬스체크 엔드포인트"""
    try:
        core = get_core()
        store = get_store()
        
        # 기본 기능 테스트
        test_result = core.process_message("테스트", 0)
        
        return {
            "status": "healthy",
            "core_available": True,
            "store_available": True,
            "mistral_available": test_result["debug"].get("mistral_available", False)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


