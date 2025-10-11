"""
ADI Coach Streamlit UI - 최적화된 전체화면 레이아웃
"""

import streamlit as st
import requests
import json
import time
from typing import Dict, Any, List

# 페이지 설정
st.set_page_config(
    page_title="ADI Coach",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 전체 화면 CSS
st.markdown("""
<style>
/* 기본 여백 제거 */
.main .block-container {
    padding: 0;
    max-width: 100%;
}

.stApp {
    padding: 0;
}

.stApp > header {
    visibility: hidden;
}

/* 헤더 */
.header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem 2rem;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.header h1 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: 600;
}

.header p {
    margin: 0.3rem 0 0 0;
    font-size: 0.9rem;
    opacity: 0.9;
}

/* 메인 컨테이너 */
.main-container {
    display: flex;
    height: 100vh;
    margin-top: 80px;
}

/* 채팅 영역 */
.chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
}

/* 채팅 헤더 */
.chat-header {
    background: white;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.chat-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    margin: 0;
}

.new-chat-btn {
    background: #667eea;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-size: 0.9rem;
    cursor: pointer;
}

.new-chat-btn:hover {
    background: #5a67d8;
}

/* 채팅 메시지 영역 */
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    background: #f8fafc;
}

/* 메시지 스타일 */
.message {
    margin-bottom: 1.5rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.message.user {
    flex-direction: row-reverse;
}

.message-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    font-weight: 600;
    flex-shrink: 0;
}

.message.user .message-avatar {
    background: #667eea;
    color: white;
}

.message.assistant .message-avatar {
    background: #10b981;
    color: white;
}

.message-content {
    max-width: 70%;
    padding: 0.75rem 1rem;
    border-radius: 12px;
    font-size: 0.95rem;
    line-height: 1.5;
}

.message.user .message-content {
    background: #667eea;
    color: white;
    border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
    background: white;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}


/* 채팅 입력 영역 */
.chat-input-area {
    background: white;
    padding: 1rem 1.5rem;
    border-top: 1px solid #e2e8f0;
}

.chat-input-container {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
}

.chat-input {
    flex: 1;
    min-height: 44px;
    max-height: 120px;
    padding: 0.75rem 1rem;
    border: 1px solid #d1d5db;
    border-radius: 12px;
    font-size: 0.95rem;
    resize: none;
    outline: none;
}

.chat-input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.send-btn {
    background: #667eea;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    min-width: 80px;
}

.send-btn:hover {
    background: #5a67d8;
}

/* 분석 패널 */
.analysis-panel {
    width: 350px;
    background: white;
    border-left: 1px solid #e2e8f0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

.analysis-header {
    padding: 1.5rem 1.5rem 1rem;
    border-bottom: 1px solid #e2e8f0;
}

.analysis-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 0.5rem 0;
}

.analysis-subtitle {
    font-size: 0.85rem;
    color: #64748b;
    margin: 0;
}

/* 메트릭 카드 */
.metric-card {
    margin: 1rem 1.5rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}

.metric-title {
    font-size: 0.8rem;
    color: #64748b;
    margin: 0 0 0.5rem 0;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.metric-label {
    font-size: 0.8rem;
    color: #64748b;
    margin: 0.25rem 0 0 0;
}

/* 모드별 색상 */
.mode-support { color: #059669; }
.mode-coaching { color: #d97706; }
.mode-mirror { color: #dc2626; }

/* 진행률 바 */
.progress-bar {
    width: 100%;
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    overflow: hidden;
    margin: 0.5rem 0;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #10b981, #059669);
    border-radius: 4px;
    transition: width 0.3s ease;
}

/* 스크롤바 */
.chat-messages::-webkit-scrollbar {
    width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
    background: #f1f5f9;
}

.chat-messages::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

/* 타이핑 애니메이션 */
.typing-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #64748b;
    font-size: 0.9rem;
    font-style: italic;
}

.typing-dots {
    display: flex;
    gap: 2px;
}

.typing-dot {
    width: 4px;
    height: 4px;
    background: #64748b;
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-10px); }
}

/* 반응형 */
@media (max-width: 1024px) {
    .main-container {
        flex-direction: column;
    }
    
    .analysis-panel {
        width: 100%;
        border-left: none;
        border-top: 1px solid #e2e8f0;
    }
    
    .message-content {
        max-width: 85%;
    }
}
</style>
""", unsafe_allow_html=True)

# API 호출 함수
def call_chat_api(text: str, msg_count: int = 0, user_context: Dict = None) -> Dict[str, Any]:
    """채팅 API 호출"""
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "text": text,
                "msg_count": msg_count,
                "conversation_history": st.session_state.get("conversation_history", []),
                "user_context": user_context or {}
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API 호출 오류: {e}")
        return None
    except Exception as e:
        st.error(f"예상치 못한 오류: {e}")
        return None

# 세션 상태 초기화
if "conversation_history" not in st.session_state:
    st.session_state["conversation_history"] = []
if "adi_history" not in st.session_state:
    st.session_state["adi_history"] = []
if "is_typing" not in st.session_state:
    st.session_state["is_typing"] = False

# 헤더
st.markdown("""
<div class="header">
    <h1>🧭 ADI Coach</h1>
    <p>AI 의존을 감지하고, 자립을 유도하는 AI 코치</p>
</div>
""", unsafe_allow_html=True)

# 메인 컨테이너
col1, col2 = st.columns([3, 1])

# 왼쪽: 채팅 영역
with col1:
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)
    
    # 채팅 헤더
    col1_header, col2_header = st.columns([1, 1])
    with col1_header:
        st.markdown('<h3 class="chat-title">💬 대화</h3>', unsafe_allow_html=True)
    with col2_header:
        if st.button("🗑️ 새 대화", key="new_chat", help="대화를 초기화합니다"):
            st.session_state["conversation_history"] = []
            st.session_state["adi_history"] = []
            st.rerun()

    # 채팅 메시지 영역
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)

    # 대화 기록 표시
    for i, message in enumerate(st.session_state["conversation_history"]):
        if message["role"] == "user":
            st.markdown(f"""
            <div class="message user">
                <div class="message-avatar">U</div>
                <div class="message-content">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            
                st.markdown(f"""
                <div class="message assistant">
                    <div class="message-avatar">AI</div>
                    <div class="message-content">
                        {message["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # 타이핑 인디케이터
    if st.session_state.get("is_typing", False):
        st.markdown("""
        <div class="message assistant">
            <div class="message-avatar">AI</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span>AI가 응답을 생성하고 있습니다</span>
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 채팅 입력 영역
    st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)

    # 채팅 입력
    col1_input, col2_input = st.columns([6, 1])
    with col1_input:
        user_input = st.text_area(
            "메시지를 입력하세요...",
            key="chat_input",
            height=44,
            placeholder="여기에 메시지를 입력하세요...",
            label_visibility="collapsed"
        )
    with col2_input:
        send_clicked = st.button("전송", key="send_btn", type="primary", use_container_width=True)

    # 메시지 전송 처리
    if send_clicked and user_input.strip():
        # 사용자 메시지 추가
        st.session_state["conversation_history"].append({"role": "user", "content": user_input})
        
        # 타이핑 상태 시작
        st.session_state["is_typing"] = True
        st.rerun()

    # 타이핑 상태일 때 API 호출
    if st.session_state.get("is_typing", False) and st.session_state["conversation_history"]:
        # 마지막 메시지가 사용자 메시지인지 확인
        last_message = st.session_state["conversation_history"][-1]
        if last_message["role"] == "user":
            # 이전 ADI 정보 가져오기
            previous_adi = 0.0
            previous_mode = "support"
            if st.session_state["adi_history"]:
                last_adi = st.session_state["adi_history"][-1]
                previous_adi = last_adi.get("adi", 0.0)
                previous_mode = last_adi.get("mode", "support")
            
            # API 호출
            result = call_chat_api(
                last_message["content"], 
                msg_count=0,
                user_context={
                    "previous_adi": previous_adi,
                    "previous_mode": previous_mode
                }
            )
            
            if result:
                # AI 응답 추가
                st.session_state["conversation_history"].append({"role": "assistant", "content": result["reply"]})
                
                # ADI 히스토리에 추가
                st.session_state["adi_history"].append({
                    "adi": result["ADI"],
                    "mode": result["mode"],
                    "delay": result["delay"],
                    "emotion_score": result["E"],
                    "score_adjustment": result["debug"]["linear_raw"]
                })
                
                # 타이핑 상태 종료
                st.session_state["is_typing"] = False
                
                # 응답 지연 적용
                if result["delay"] > 0:
                    time.sleep(result["delay"])
                
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # chat-input-area
    st.markdown('</div>', unsafe_allow_html=True)  # chat-area

# 오른쪽: 분석 패널
with col2:
    st.markdown('<div class="analysis-panel">', unsafe_allow_html=True)

    # 분석 헤더
    st.markdown("""
    <div class="analysis-header">
        <h3 class="analysis-title">📊 실시간 분석</h3>
        <p class="analysis-subtitle">ADI 점수와 감정 상태를 모니터링합니다</p>
    </div>
    """, unsafe_allow_html=True)

    # 현재 상태 표시
    if st.session_state["adi_history"]:
        latest = st.session_state["adi_history"][-1]
        
        # ADI 점수
        adi = latest['adi']
        mode = latest['mode']
        mode_emoji = {"support": "🤗", "coaching": "🎯", "mirror": "🪞"}.get(mode, "🤗")
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">ADI 점수</div>
            <div class="metric-value mode-{mode}">
                {adi:.1f} {mode_emoji}
            </div>
            <div class="metric-label">{mode.upper()} 모드</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {adi * 10}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 감정 점수
        emotion_score = latest.get('emotion_score', 0)
        adjustment = latest.get('score_adjustment', 0)
        
        emotion_color = "#ef4444" if emotion_score < 0 else "#10b981" if emotion_score > 0 else "#6b7280"
        adjustment_color = "#ef4444" if adjustment > 0 else "#10b981" if adjustment < 0 else "#6b7280"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">감정 분석</div>
            <div class="metric-value" style="color: {emotion_color}">
                {emotion_score:.2f}
            </div>
            <div class="metric-label">
                {'부정적' if emotion_score < 0 else '긍정적' if emotion_score > 0 else '중립'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 점수 조정
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">점수 조정</div>
            <div class="metric-value" style="color: {adjustment_color}">
                {adjustment:+.1f}
            </div>
            <div class="metric-label">
                {'증가' if adjustment > 0 else '감소' if adjustment < 0 else '변화없음'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 응답 지연
        delay = latest.get('delay', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">응답 지연</div>
            <div class="metric-value">
                {delay:.1f}초
            </div>
            <div class="metric-label">
                {'즉시' if delay == 0 else '점진적' if delay < 1 else '긴 지연'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title">대화를 시작하세요</div>
            <div class="metric-value" style="color: #6b7280; font-size: 1rem;">
                💬
            </div>
            <div class="metric-label">
                메시지를 입력하면 분석이 시작됩니다
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 도움말
    with st.expander("💡 사용법", expanded=False):
        st.markdown("""
        **ADI Coach 사용법**
        
        🤗 **Support 모드** (0-4점)
        - 즉시 응답
        - 따뜻한 위로와 지지
        
        🎯 **Coaching 모드** (4-7점)
        - 점진적 지연 (0.5-1.1초)
        - 성찰 유도 질문
        
        🪞 **Mirror 모드** (7-10점)
        - 긴 지연 (1.5-2.4초)
        - 깊은 자기 성찰 질문
        
        **팁**: 부정적 감정을 표현하면 ADI 점수가 올라가고, 긍정적 감정을 표현하면 점수가 내려갑니다.
        """)

    st.markdown('</div>', unsafe_allow_html=True)  # analysis-panel