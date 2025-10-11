"""
JWT Authentication System
입력: 사용자 인증 정보 (username, password)
출력: JWT 토큰, 사용자 정보
목표: 안전한 API 접근 제어 및 사용자 세션 관리

TODO: 향후 개선사항들
- [ ] OAuth 2.0 통합 (Google, Kakao, Naver)
- [ ] 2FA (Two-Factor Authentication) 지원
- [ ] 역할 기반 접근 제어 (RBAC)
- [ ] 토큰 갱신 (Refresh Token) 시스템
- [ ] 사용자 활동 로깅 및 감사
- [ ] 비밀번호 정책 강화
- [ ] 계정 잠금 정책
- [ ] 이메일 인증 시스템
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "adi_coach_secret_key_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 토큰 스키마
security = HTTPBearer()


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None


class AuthManager:
    """인증 관리자 클래스"""
    
    def __init__(self):
        self.users_db = {}  # 실제 환경에서는 데이터베이스 사용
        self._create_default_users()
    
    def _create_default_users(self):
        """기본 사용자 생성 (개발용)"""
        try:
            # 기본 관리자 계정
            admin_password = self.get_password_hash("admin123")
            self.users_db["admin"] = {
                "username": "admin",
                "email": "admin@adicoach.com",
                "full_name": "Administrator",
                "hashed_password": admin_password,
                "is_active": True,
                "created_at": datetime.utcnow()
            }
            
            # 테스트 사용자 계정
            test_password = self.get_password_hash("test123")
            self.users_db["test"] = {
                "username": "test",
                "email": "test@adicoach.com",
                "full_name": "Test User",
                "hashed_password": test_password,
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        except Exception as e:
            print(f"기본 사용자 생성 중 오류 발생: {e}")
            # bcrypt 오류 시 간단한 해시 사용 (개발용)
            self.users_db["admin"] = {
                "username": "admin",
                "email": "admin@adicoach.com",
                "full_name": "Administrator",
                "hashed_password": "admin123",  # 개발용 임시
                "is_active": True,
                "created_at": datetime.utcnow()
            }
            self.users_db["test"] = {
                "username": "test",
                "email": "test@adicoach.com",
                "full_name": "Test User",
                "hashed_password": "test123",  # 개발용 임시
                "is_active": True,
                "created_at": datetime.utcnow()
            }
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """비밀번호 해싱 (bcrypt는 72바이트 제한)"""
        # bcrypt는 72바이트 제한이 있으므로 초과시 자르기
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """사용자 인증"""
        user = self.users_db.get(username)
        if not user:
            return None
        if not self.verify_password(password, user["hashed_password"]):
            return None
        return user
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """JWT 액세스 토큰 생성"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            token_data = TokenData(username=username)
            return token_data
        except JWTError:
            return None
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """사용자 정보 조회"""
        return self.users_db.get(username)
    
    def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """새 사용자 생성"""
        if user_data.username in self.users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        hashed_password = self.get_password_hash(user_data.password)
        user = {
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        self.users_db[user_data.username] = user
        return user


# 전역 인증 관리자 인스턴스
auth_manager = AuthManager()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """현재 사용자 조회 (의존성 주입)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    token_data = auth_manager.verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    user = auth_manager.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """활성 사용자 조회"""
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_token_response(username: str) -> Token:
    """토큰 응답 생성"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_manager.create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
