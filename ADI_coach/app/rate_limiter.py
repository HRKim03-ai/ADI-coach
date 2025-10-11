"""
API Rate Limiting System
입력: 사용자 요청 (IP, 사용자 ID)
출력: 요청 허용/거부 결정
목표: API 남용 방지 및 서버 보호

TODO: 향후 개선사항들
- [ ] Redis 기반 분산 레이트 리미팅
- [ ] 사용자별 맞춤형 제한 설정
- [ ] 동적 제한 조정 (서버 부하에 따라)
- [ ] IP 화이트리스트/블랙리스트
- [ ] 요청 패턴 분석 및 이상 탐지
- [ ] 레이트 리미팅 메트릭 수집
- [ ] 슬라이딩 윈도우 알고리즘
- [ ] 토큰 버킷 알고리즘
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from fastapi import HTTPException, status, Request
from functools import wraps


class RateLimiter:
    """레이트 리미터 클래스"""
    
    def __init__(self):
        # 메모리 기반 저장소 (실제 환경에서는 Redis 사용)
        self.requests = defaultdict(deque)
        self.blocked_ips = set()
        
        # 기본 제한 설정
        self.limits = {
            "default": {"requests": 100, "window": 3600},  # 1시간에 100회
            "chat": {"requests": 30, "window": 3600},      # 1시간에 30회 채팅
            "auth": {"requests": 10, "window": 3600},      # 1시간에 10회 인증 시도
            "stats": {"requests": 60, "window": 3600},     # 1시간에 60회 통계 조회
        }
    
    def is_allowed(
        self, 
        identifier: str, 
        endpoint: str = "default",
        custom_limit: Optional[Dict[str, int]] = None
    ) -> Tuple[bool, Dict[str, int]]:
        """
        요청 허용 여부 확인
        
        Args:
            identifier: 사용자 식별자 (IP 또는 사용자 ID)
            endpoint: 엔드포인트 타입
            custom_limit: 사용자 정의 제한 설정
            
        Returns:
            (허용여부, 남은 요청 수 정보)
        """
        current_time = time.time()
        
        # 차단된 IP 확인
        if identifier in self.blocked_ips:
            return False, {"blocked": True}
        
        # 제한 설정 가져오기
        limit_config = custom_limit or self.limits.get(endpoint, self.limits["default"])
        max_requests = limit_config["requests"]
        window_seconds = limit_config["window"]
        
        # 요청 기록 가져오기
        request_times = self.requests[identifier]
        
        # 윈도우 밖의 오래된 요청 제거
        cutoff_time = current_time - window_seconds
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
        
        # 현재 요청 수 확인
        current_requests = len(request_times)
        
        if current_requests >= max_requests:
            # 제한 초과 시 차단 (1시간)
            if current_requests >= max_requests * 2:
                self.blocked_ips.add(identifier)
                return False, {"blocked": True, "reason": "excessive_requests"}
            
            return False, {
                "allowed": False,
                "current_requests": current_requests,
                "max_requests": max_requests,
                "reset_time": int(request_times[0] + window_seconds) if request_times else int(current_time + window_seconds)
            }
        
        # 요청 기록 추가
        request_times.append(current_time)
        
        return True, {
            "allowed": True,
            "current_requests": current_requests + 1,
            "max_requests": max_requests,
            "remaining": max_requests - (current_requests + 1)
        }
    
    def get_rate_limit_info(self, identifier: str, endpoint: str = "default") -> Dict[str, int]:
        """레이트 리미트 정보 조회"""
        current_time = time.time()
        limit_config = self.limits.get(endpoint, self.limits["default"])
        request_times = self.requests[identifier]
        
        # 윈도우 밖의 오래된 요청 제거
        cutoff_time = current_time - limit_config["window"]
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
        
        return {
            "current_requests": len(request_times),
            "max_requests": limit_config["requests"],
            "window_seconds": limit_config["window"],
            "remaining": max(0, limit_config["requests"] - len(request_times))
        }
    
    def reset_limits(self, identifier: str):
        """사용자 제한 초기화"""
        if identifier in self.requests:
            del self.requests[identifier]
        if identifier in self.blocked_ips:
            self.blocked_ips.remove(identifier)
    
    def set_custom_limit(self, identifier: str, endpoint: str, limit_config: Dict[str, int]):
        """사용자별 맞춤 제한 설정"""
        # 실제 구현에서는 데이터베이스에 저장
        pass


# 전역 레이트 리미터 인스턴스
rate_limiter = RateLimiter()


def get_client_identifier(request: Request, user_id: Optional[str] = None) -> str:
    """클라이언트 식별자 생성"""
    if user_id:
        return f"user:{user_id}"
    
    # IP 주소 기반 식별
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"ip:{client_ip}"


def rate_limit(endpoint: str = "default", custom_limit: Optional[Dict[str, int]] = None):
    """레이트 리미팅 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Request 객체 찾기
            request = None
            user_id = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            for key, value in kwargs.items():
                if key == "request" and isinstance(value, Request):
                    request = value
                elif key == "current_user" and isinstance(value, dict):
                    user_id = value.get("username")
            
            if not request:
                # Request 객체를 찾을 수 없는 경우 제한 없이 통과
                return await func(*args, **kwargs)
            
            # 클라이언트 식별자 생성
            identifier = get_client_identifier(request, user_id)
            
            # 레이트 리미트 확인
            allowed, info = rate_limiter.is_allowed(identifier, endpoint, custom_limit)
            
            if not allowed:
                if info.get("blocked"):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. IP blocked temporarily.",
                        headers={"Retry-After": "3600"}
                    )
                else:
                    reset_time = info.get("reset_time", int(time.time() + 3600))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Try again after {reset_time}",
                        headers={
                            "X-RateLimit-Limit": str(info.get("max_requests", 100)),
                            "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                            "X-RateLimit-Reset": str(reset_time),
                            "Retry-After": str(reset_time - int(time.time()))
                        }
                    )
            
            # 요청 처리
            response = await func(*args, **kwargs)
            
            # 응답 헤더에 레이트 리미트 정보 추가
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(info.get("max_requests", 100))
                response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            
            return response
        
        return wrapper
    return decorator


def get_rate_limit_status(identifier: str, endpoint: str = "default") -> Dict[str, int]:
    """레이트 리미트 상태 조회"""
    return rate_limiter.get_rate_limit_info(identifier, endpoint)
