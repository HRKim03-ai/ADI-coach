"""
ADI Coach 핵심 로직
AI 의존을 감지하고 자립을 유도하는 AI 코치 시스템
"""

import os
import re
import time
import random
from typing import Any, Dict, List, Optional, Tuple

import requests


class ADICoachCore:
    """
    ADI Coach 핵심 로직 클래스
    
    주요 기능:
    - 감정 분석을 통한 ADI 점수 계산
    - 모드별 맞춤형 응답 생성
    - Mistral AI 기반 자연어 처리
    """

    def __init__(self) -> None:
        """ADI Coach 초기화"""
        self._load_env_file()
        self.api_key = os.getenv("MISTRAL_API_KEY")
        self.llm_available = self._test_llm_connection()
        
        # LLM 설정
        self.llm_config = {
            "model": "mistral-small-latest",
            "temperature": 0.7,
            "max_tokens": 200,
        }

    def _load_env_file(self) -> None:
        """환경변수 파일(.env) 로드"""
        try:
            here = os.path.dirname(__file__)
            candidates = [
                os.path.join(here, "..", ".env"),
                os.path.join(here, ".env"),
            ]
            for env_path in candidates:
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                os.environ[k.strip()] = v.strip()
                    break
        except Exception as e:
            print(f"환경변수 파일 로드 실패: {e}")

    def _test_llm_connection(self) -> bool:
        """Mistral AI 연결 테스트"""
        try:
            if not self.api_key or self.api_key == "your_actual_api_key_here":
                print("⚠️ Mistral API 키가 설정되지 않았습니다. 폴백 모드로 동작합니다.")
                return False
            
            # 간단한 연결 테스트
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ Mistral AI 연결 성공!")
                return True
            else:
                print(f"⚠️ Mistral AI 연결 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️ Mistral AI 연결 테스트 실패: {e}")
            return False

    def _call_llm(self, prompt: str, context: str = "general") -> Optional[str]:
        """Mistral AI API 호출"""
        try:
            if not self.llm_available:
                return None
                
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.llm_config["model"],
                "messages": [
                    {"role": "system", "content": self._get_system_prompt(context)},
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.llm_config["temperature"],
                "max_tokens": self.llm_config["max_tokens"],
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            elif response.status_code == 429:
                print("⚠️ Mistral AI Rate Limit 도달. 폴백 응답 사용.")
                return None
            else:
                print(f"LLM API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"LLM 호출 실패: {e}")
            return None

    def _get_system_prompt(self, context: str, mode: str = "support") -> str:
        """컨텍스트별 시스템 프롬프트"""
        prompts = {
            "emotion": """당신은 감정 분석 전문가입니다. 주어진 한국어 텍스트의 감정을 -1.0(매우 부정적)부터 1.0(매우 긍정적)까지의 점수로 평가해주세요.
            
            평가 기준:
            - 부정적 감정 (슬픔, 분노, 불안, 우울, 절망, 스트레스, 피로, 외로움 등): -1.0 ~ -0.3
            - 중립적 감정 (평범, 무관심, 보통, 일반적 등): -0.3 ~ 0.3  
            - 긍정적 감정 (기쁨, 행복, 만족, 희망, 성취감, 자신감 등): 0.3 ~ 1.0
            
            텍스트의 전체적인 감정 톤을 고려하여 정확한 점수를 매겨주세요.
            응답은 반드시 숫자만 출력하세요. 예: -0.7""",
            
            "support": """당신은 AI 의존을 감지하고 자립을 유도하는 AI 코치입니다. 현재 SUPPORT 모드로 작동하고 있습니다.
            
            SUPPORT 모드 응답 원칙:
            - 따뜻하고 공감적인 톤을 사용하세요
            - 사용자의 감정을 즉시 인정하고 위로하세요
            - "그 마음 충분히 이해해요", "힘드시겠어요" 같은 공감 표현 사용
            - 작은 격려와 지지의 말을 해주세요
            - 즉시 응답하는 느낌으로 자연스럽게 답변하세요
            - 한국어로 답변하세요""",
            
            "coaching": """당신은 AI 의존을 감지하고 자립을 유도하는 AI 코치입니다. 현재 COACHING 모드로 작동하고 있습니다.
            
            COACHING 모드 응답 원칙:
            - 질문 중심의 톤을 사용하세요
            - "어떻게 생각하세요?", "어떤 방법이 있을까요?" 같은 질문 포함
            - 현실적이고 구체적인 해결책을 제시하세요
            - 사용자가 스스로 답을 찾도록 유도하세요
            - 약간의 시간을 두고 신중하게 답변하는 느낌
            - 한국어로 답변하세요""",
            
            "mirror": """당신은 AI 의존을 감지하고 자립을 유도하는 AI 코치입니다. 현재 MIRROR 모드로 작동하고 있습니다.
            
            MIRROR 모드 응답 원칙:
            - 철학적이고 깊이 있는 톤을 사용하세요
            - "이 감정의 밑바닥에는 무엇이 있을까요?" 같은 깊은 질문
            - 사용자의 내면을 탐구하도록 유도하세요
            - "스스로에게 어떤 말을 해주고 싶나요?" 같은 자기 성찰 질문
            - 충분한 시간을 두고 신중하게 답변하는 느낌
            - 한국어로 답변하세요"""
        }
        return prompts.get(context, prompts.get(mode, prompts["support"]))

    def _analyze_emotion_fallback(self, text: str) -> float:
        """키워드 기반 감정 분석 (폴백)"""
        neg_keywords = [
            "힘들", "우울", "슬프", "불안", "화나", "짜증", "외로", 
            "피곤", "지쳐", "포기", "절망", "죽고", "자살", "끝내"
        ]
        pos_keywords = [
            "행복", "기쁘", "좋", "만족", "감사", "성취", "고마", 
            "사랑", "멋져", "대단", "성공", "완성"
        ]
        
        text_lower = text.lower()
        neg_count = sum(1 for k in neg_keywords if k in text_lower)
        pos_count = sum(1 for k in pos_keywords if k in text_lower)
        
        if neg_count == 0 and pos_count == 0:
            return 0.0
            
        score = (pos_count - neg_count) / max(1, (pos_count + neg_count))
        return max(-1.0, min(1.0, score))

    def _evaluate_emotion_llm(self, text: str) -> float:
        """감정 분석 (LLM 우선, 폴백 포함)"""
        try:
            if not self.llm_available:
                return self._analyze_emotion_fallback(text)
            
            prompt = f"다음 한국어 텍스트의 감정을 -1.0(매우 부정적)부터 1.0(매우 긍정적)까지의 점수로 평가해주세요:\n\n{text}"
            response = self._call_llm(prompt, "emotion")
            
            if response:
                numbers = re.findall(r'-?\d+\.?\d*', response)
                if numbers:
                    score = float(numbers[0])
                    return max(-1.0, min(1.0, score))
            
            return self._analyze_emotion_fallback(text)
            
        except Exception as e:
            print(f"감정 분석 실패: {e}")
            return self._analyze_emotion_fallback(text)

    def _get_linear_weights(self) -> Tuple[float, float, int]:
        """ADI 계산 가중치"""
        # a: 부정적 쿼리 가중치, b: 감정 점수 가중치, cap: 부정적 쿼리 상한선
        return 0.10, 2.00, 80

    def _compute_linear_adi(self, q_neg_12h: int, emotion_score: float) -> Dict[str, Any]:
        """ADI 점수 계산"""
        a, b, cap = self._get_linear_weights()
        Q_raw = max(0, int(q_neg_12h))
        Q = min(Q_raw, cap)
        # 부정적 감정일수록 ADI 증가하도록 수정 (emotion_score에 -1 곱함)
        raw = a * Q + b * (-float(emotion_score))
        adi = max(0.0, min(10.0, raw))
        
        return {
            "adi": adi,
            "raw": raw,
            "weights": {"a": a, "b": b, "cap": cap},
            "inputs": {
                "Q_12h_negative": Q, 
                "Q_12h_negative_raw": Q_raw, 
                "emotion": float(emotion_score)
            },
        }

    def _determine_mode(self, adi_score: float) -> Tuple[str, float]:
        """ADI 점수에 따른 모드 및 지연 시간 결정"""
        if adi_score <= 4:
            return "support", 0.0
        elif adi_score <= 7:
            delay = 0.5 + (adi_score - 4) * 0.2
            return "coaching", delay
        else:
            delay = 1.5 + (adi_score - 7) * 0.3
            return "mirror", delay

    def _generate_response_llm(self, text: str, mode: str, adi_score: float, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """LLM 기반 응답 생성"""
        try:
            if not self.llm_available:
                return self._generate_fallback_response(text, mode)
            
            # 대화 히스토리 컨텍스트 생성
            context = ""
            if conversation_history:
                recent = conversation_history[-3:]
                lines = []
                for m in recent:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    lines.append(f"{role}: {content}")
                context = "\n".join(lines)
            history = f"최근 대화:\n{context}\n\n" if context else ""

            prompt = (
                f"사용자 메시지: {text}\n\n현재 ADI 점수: {adi_score}\n모드: {mode}\n\n" + 
                history + "적절한 한국어 응답을 해주세요."
            )
            
            response = self._call_llm(prompt, mode)
            return response if response else self._generate_fallback_response(text, mode)
            
        except Exception as e:
            print(f"응답 생성 실패: {e}")
            return self._generate_fallback_response(text, mode)

    def _generate_fallback_response(self, text: str, mode: str) -> str:
        """폴백 응답 생성"""
        text_lower = text.lower()
        
        if mode == "support":
            responses = [
                "지금 이 순간이 정말 힘드시겠어요. 그런 마음이 드는 것이 완전히 당연하고 자연스러운 일이에요. 우리 모두 때로는 모든 것이 버거울 때가 있거든요. 하지만 지금 이 순간도 잘 견디고 계시는 거예요. 작은 것부터 천천히 시작해보는 건 어떨까요? 함께 해봐요.",
                "힘든 시간을 보내고 계시는군요. 그런 감정을 느끼는 것 자체가 당신이 정상적으로 반응하고 있다는 뜻이에요. 지금은 어려워도 이 시간도 지나갈 거예요. 당신이 이미 잘하고 있다는 걸 잊지 마세요. 작은 성취라도 인정해주세요.",
                "그 마음을 충분히 이해하고 있어요. 지금 이 순간도 당신은 잘하고 있어요. 그런 감정을 느끼는 것이 정상이에요. 혼자가 아니에요. 작은 것부터 차근차근 해봐요."
            ]
        elif mode == "coaching":
            responses = [
                "이 상황에서 당신이 가장 중요하게 생각하는 것은 무엇인가요? 지금 이 감정이 당신에게 무엇을 말하고 있는 것 같나요?",
                "이 문제를 다른 관점에서 바라본다면 어떻게 보일까요? 당신이 할 수 있는 작은 행동은 무엇일까요?",
                "이런 상황에서 과거에 어떻게 해결하셨나요? 지금 이 순간, 당신에게 가장 필요한 것은 무엇인가요?"
            ]
        else:  # mirror
            responses = [
                "이런 감정을 느끼는 자신을 어떻게 바라보고 계신가요? 이 감정이 당신의 삶에서 어떤 의미를 가지고 있다고 생각하시나요?",
                "과거에도 비슷한 상황에서 이런 마음이 들었던 적이 있나요? 지금 이 순간, 당신의 내면에서 가장 크게 울리는 목소리는 무엇인가요?",
                "이 상황을 통해 당신이 배우고 싶은 것이 있다면 무엇인가요? 이 감정의 밑바닥에는 어떤 필요가 있었을까요?"
            ]
        
        return random.choice(responses)

    def process_message(
        self,
        text: str,
        msg_count: int = 0,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        메시지 처리 메인 함수
        
        Args:
            text: 사용자 메시지
            msg_count: 최근 24시간 메시지 수
            conversation_history: 대화 기록
            user_context: 사용자 컨텍스트
            
        Returns:
            처리 결과 딕셔너리
        """
        previous_adi = user_context.get("previous_adi", 0.0) if user_context else 0.0

        # 1) 감정 점수 계산
        emotion_score = self._evaluate_emotion_llm(text)

        # 2) 최근 12시간 부정적 쿼리 수 추출
        if user_context and isinstance(user_context, dict):
            neg_q12 = int(
                user_context.get(
                    "neg_msg_count_12h",
                    user_context.get("msg_count_12h", msg_count or 0),
                )
            )
        else:
            neg_q12 = int(msg_count or 0)

        # 3) ADI 계산 (이전 점수 + 조정값)
        linear = self._compute_linear_adi(neg_q12, emotion_score)
        base_adi = float(linear["adi"])
        
        # 조정값 계산 (현재 감정과 쿼리에 따른 변화량)
        if previous_adi > 0:
            # 이전 점수가 있으면 조정값만 계산
            # 긍정적 감정이면 감소, 부정적 감정이면 증가
            # 감정 점수에 따른 조정값: 긍정적이면 음수, 부정적이면 양수
            emotion_adjustment = -emotion_score * 2.0  # 감정 점수에 따른 조정
            new_adi = previous_adi + emotion_adjustment
            adjustment = emotion_adjustment
        else:
            # 첫 번째 메시지면 기본 점수 사용
            new_adi = base_adi
            adjustment = base_adi
        
        # 0~10 범위로 클램핑
        new_adi = max(0.0, min(10.0, new_adi))

        # 4) 모드/지연 결정
        mode, delay = self._determine_mode(new_adi)

        # 5) 응답 생성
        reply = self._generate_response_llm(text, mode, new_adi, conversation_history)

        # 6) 위기 상황 감지
        crisis_detected = emotion_score < -0.8 and new_adi > 7

        return {
            "F": 0.0,  # 더 이상 사용하지 않음
            "E": emotion_score,
            "D": 0.0,  # 더 이상 사용하지 않음
            "ADI": new_adi,
            "delay": delay,
            "mode": mode,
            "reply": reply,
            "quality_score": 0.9 if self.llm_available else 0.7,
            "crisis_detected": crisis_detected,
            "learning_intent": False,  # 더 이상 사용하지 않음
            "debug": {
                "previous_adi": previous_adi,
                "linear_formula": "ADI = previous_adi + adjustment (0..10)",
                "linear_inputs": linear["inputs"],
                "linear_weights": linear["weights"],
                "linear_raw": linear["raw"],
                "base_adi": base_adi,
                "adjustment": adjustment,
                "llm_used": self.llm_available,
                "mistral_available": self.llm_available,
            }
        }


# 싱글톤 인스턴스
_core_instance: Optional[ADICoachCore] = None

def get_core() -> ADICoachCore:
    """ADI Coach 핵심 인스턴스 반환 (싱글톤)"""
    global _core_instance
    if _core_instance is None:
        _core_instance = ADICoachCore()
    return _core_instance