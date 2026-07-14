# RTZR STT Pipeline & Benchmark CLI

리턴제로(ReturnZero)의 일반 STT OpenAPI를 사용하여 Sommers 모델과 Whisper 모델의 전사 특성을 비교하고, 모델별 제약 조건을 처리하기 위해 구현한 CLI 벤치마크 파이프라인입니다.

## 주요 기능 및 구현 특징

1. **모델별 설정 제어 (build_safe_config)**
   - Sommers 모델: 영문 키워드 입력 시 부스팅이 작동하지 않는 제약을 처리하기 위해 영어 알파벳을 필터링하고 한글 발음 표기만 입력값으로 변환하여 주입합니다.
   - Whisper 모델: 키워드 부스팅에 필수적인 언어 설정(language: "ko")이 누락되지 않도록 자동으로 강제합니다.
2. **세션 및 예외 처리**
   - 6시간의 JWT 토큰 만료 정책에 대응하여, 만료 30분 전 호출 시 자동으로 토큰을 갱신하는 프로퍼티 캐싱 흐름을 설계했습니다.
   - API 요청 제한(429)을 방지하기 위해 가이드라인 권장 사항인 5초 Polling 루프를 적용하고 이에 따른 예외 처리를 연동했습니다.
3. **화자 분리 타임라인 파싱**
   - API 응답 JSON 데이터를 가공하여 밀리초(ms) 데이터를 분/초 시계 포맷([MM:SS])으로 변환한 뒤 화자별 타임라인을 콘솔에 출력합니다.

---

## 실행 방법 (Getting Started)

### 1. 사전 준비 사항
- Python 3.8 이상
- ReturnZero OpenAPI 자격증명 (CLIENT_ID, CLIENT_SECRET)

### 2. 가상환경 구성 및 패키지 설치
```bash
# 1. 저장소 클론 및 이동
git clone [https://github.com/BIGDannyK/rtzr-stt-pipeline.git](https://github.com/BIGDannyK/rtzr-stt-pipeline.git)
cd rtzr-stt-pipeline

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 필수 의존성 패키지 설치
pip install -r requirements.txt
