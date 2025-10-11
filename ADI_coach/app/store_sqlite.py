"""
SQLite Storage for ADI Coach
입력: 메시지 데이터, 사용자 ID, 조회 파라미터
출력: 저장 성공 여부, 조회된 데이터
목표: 로컬 SQLite에 대화 로그 저장 및 조회

TODO: 향후 개선사항들
- [ ] 데이터베이스 마이그레이션 시스템
- [ ] 사용자별 데이터 암호화
- [ ] 데이터 압축 및 아카이빙
- [ ] 실시간 데이터 동기화 (클라우드 백업)
- [ ] 데이터 분석 및 통계 기능
- [ ] 데이터 내보내기/가져오기 기능
- [ ] 백업 및 복구 시스템
"""

from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class SQLiteStore:
    """SQLite 기반 데이터 저장소"""
    
    def __init__(self, db_path: str = "./adi_coach.db"):
        self.db_path = Path(db_path)
        self._ensure_parent_dir()
        self._init_database()
    
    def _ensure_parent_dir(self):
        """데이터베이스 파일의 부모 디렉토리 생성"""
        if self.db_path.parent and not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            # 메시지 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    text TEXT NOT NULL,
                    F REAL NOT NULL,
                    E REAL NOT NULL,
                    D REAL NOT NULL,
                    ADI REAL NOT NULL,
                    mode TEXT NOT NULL,
                    reply TEXT NOT NULL,
                    debug_info TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 사용자 세션 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_start REAL NOT NULL,
                    session_end REAL,
                    message_count INTEGER DEFAULT 0,
                    avg_adi REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성 (성능 최적화)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_id 
                ON messages(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON user_sessions(user_id)
            """)
            
            conn.commit()
    
    def save_message(self, data: Dict[str, Any]) -> bool:
        """
        메시지 데이터 저장
        TODO: 배치 저장으로 성능 최적화
        TODO: 데이터 검증 및 정제
        TODO: 중복 데이터 방지
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO messages 
                    (user_id, timestamp, text, F, E, D, ADI, mode, reply, debug_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(data.get("user_id", "")),
                    float(data.get("timestamp", 0.0)),
                    str(data.get("text", "")),
                    float(data.get("F", 0.0)),
                    float(data.get("E", 0.0)),
                    float(data.get("D", 0.0)),
                    float(data.get("ADI", 0.0)),
                    str(data.get("mode", "")),
                    str(data.get("reply", "")),
                    json.dumps(data.get("debug", {}))
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"메시지 저장 오류: {e}")
            return False
    
    def get_recent_messages(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 메시지 조회
        TODO: 페이지네이션 구현
        TODO: 필터링 옵션 추가 (날짜, 모드별)
        TODO: 검색 기능 추가
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM messages 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (user_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"메시지 조회 오류: {e}")
            return []
    
    def get_message_count_last_24h(self, user_id: str) -> int:
        """
        최근 24시간 내 메시지 수 조회
        """
        try:
            import time
            cutoff_time = time.time() - (24 * 60 * 60)  # 24시간 전
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM messages 
                    WHERE user_id = ? AND timestamp > ?
                """, (user_id, cutoff_time))
                
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"24시간 메시지 수 조회 오류: {e}")
            return 0

    def get_message_count_last_hours(self, user_id: str, hours: int) -> int:
        """
        최근 N시간 내 메시지 수 조회
        """
        try:
            import time
            cutoff_time = time.time() - (hours * 60 * 60)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM messages
                    WHERE user_id = ? AND timestamp > ?
                    """,
                    (user_id, cutoff_time),
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"최근 {hours}시간 메시지 수 조회 오류: {e}")
            return 0

    def get_message_count_last_12h(self, user_id: str) -> int:
        """
        최근 12시간 내 메시지 수 조회
        """
        return self.get_message_count_last_hours(user_id, 12)

    def get_negative_message_count_last_hours(self, user_id: str, hours: int, threshold: float = -0.3) -> int:
        """
        최근 N시간 내 부정적 메시지 수 조회
        - 기준: 저장된 감정점수 E < threshold 를 부정으로 간주 (기본 -0.3)
        - 현재 요청은 포함하지 않음 (이전 기록만 대상으로 집계)
        """
        try:
            import time
            cutoff_time = time.time() - (hours * 60 * 60)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM messages
                    WHERE user_id = ? AND timestamp > ? AND E < ?
                    """,
                    (user_id, cutoff_time, float(threshold)),
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"최근 {hours}시간 부정적 메시지 수 조회 오류: {e}")
            return 0

    def get_negative_message_count_last_12h(self, user_id: str, threshold: float = -0.3) -> int:
        """
        최근 12시간 내 부정적 메시지 수 조회
        """
        return self.get_negative_message_count_last_hours(user_id, 12, threshold)
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 통계 조회
        TODO: 고급 분석 메트릭 추가
        TODO: 감정 변화 추이 분석
        TODO: 패턴 인식 및 인사이트 제공
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 기본 통계
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as message_count,
                        AVG(ADI) as avg_adi,
                        AVG(F) as avg_f,
                        AVG(E) as avg_e,
                        AVG(D) as avg_d,
                        MIN(timestamp) as first_message,
                        MAX(timestamp) as last_message
                    FROM messages 
                    WHERE user_id = ?
                """, (user_id,))
                
                stats = dict(cursor.fetchone())
                
                # 모드별 통계
                cursor = conn.execute("""
                    SELECT mode, COUNT(*) as count
                    FROM messages 
                    WHERE user_id = ?
                    GROUP BY mode
                """, (user_id,))
                
                mode_stats = {row[0]: row[1] for row in cursor.fetchall()}
                stats["mode_distribution"] = mode_stats
                
                return stats
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}
    
    def get_adi_trend(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        ADI 변화 추이 조회
        TODO: 시계열 분석 기능
        TODO: 이상치 탐지
        TODO: 예측 모델링
        """
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT 
                        DATE(datetime(timestamp, 'unixepoch')) as date,
                        AVG(ADI) as avg_adi,
                        COUNT(*) as message_count
                    FROM messages 
                    WHERE user_id = ? AND timestamp > ?
                    GROUP BY DATE(datetime(timestamp, 'unixepoch'))
                    ORDER BY date
                """, (user_id, cutoff_time))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"ADI 추이 조회 오류: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        오래된 데이터 정리
        TODO: 자동 정리 스케줄링
        TODO: 중요 데이터 보존 정책
        TODO: 아카이빙 시스템
        """
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM messages 
                    WHERE timestamp < ?
                """, (cutoff_time,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
        except Exception as e:
            print(f"데이터 정리 오류: {e}")
            return 0
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 데이터 내보내기 (GDPR 준수)
        TODO: 다양한 형식 지원 (JSON, CSV, PDF)
        TODO: 데이터 익명화 옵션
        TODO: 압축 및 암호화
        """
        try:
            messages = self.get_recent_messages(user_id, limit=1000)
            stats = self.get_user_stats(user_id)
            trend = self.get_adi_trend(user_id)
            
            return {
                "user_id": user_id,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "messages": messages,
                "statistics": stats,
                "trend": trend
            }
        except Exception as e:
            print(f"데이터 내보내기 오류: {e}")
            return {}


# 전역 인스턴스
_store_instance = None

def get_store() -> SQLiteStore:
    """SQLite 저장소 인스턴스 반환"""
    global _store_instance
    if _store_instance is None:
        _store_instance = SQLiteStore()
    return _store_instance
