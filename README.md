# RTZR STT Pipeline & Benchmark CLI

리턴제로(ReturnZero)의 일반 STT OpenAPI를 사용하여 `Sommers` 모델과 `Whisper` 모델의 전사 특성을 비교하고, 모델별 제약 조건을 처리하기 위해 구현한 CLI 벤치마크 파이프라인입니다.

## 주요 기능 및 구현 특징

1. **모델별 설정 제어 (`build_safe_config`)**
   - `Sommers`: 영문 bias 주입 시 동작이 제한되는 현상을 방어하기 위해 영어 알파벳을 필터링하고 사용자가 사전에 정의한 한글 발음 표기 컨텍스트만 선별하여 주입하는 구조로 설계했습니다.
   - `Whisper`: 키워드 부스팅 활성화에 필수적인 언어 설정(`language: "ko"`)요건이 누락되지 않도록 자동으로 강제합니다.
2. **세션 및 예외 처리**
   - 6시간의 `JWT` 토큰 만료 정책에 대응하여, 만료 30분 전 호출 시 자동으로 토큰을 갱신하는 프로퍼티 캐싱 흐름을 설계했습니다.
   - API 요청 제한(429)을 방지하기 위해 가이드라인 권장 사항인 5초 Polling 루프를 적용하고 이에 따른 예외 처리를 연동했습니다.
3. **화자 분리 타임라인 파싱 및 .srt 자막 자동 추출**
   - API 응답 JSON 데이터를 가공하여 밀리초(ms) 데이터를 분/초 시계 포맷(`[MM:SS]`)으로 변환한 뒤 화자별 타임라인을 콘솔에 출력합니다.
   - 전사가 정상적으로 완료되면 해당 타임라인 데이터를 바탕으로 표준 자막 규격에 맞는 자막 파일(`.srt`)을 `tests/` 폴더 내에 모델별로 자동 저장합니다.

---

## 실행 방법 (Getting Started)

### 1. 사전 준비 사항
- Python 3.8 이상
- ReturnZero OpenAPI 자격증명 (`RTZR_CLIENT_ID`, `RTZR_CLIENT_SECRET`)

### 2. 가상환경 구성 및 패키지 설치
```bash
# 1. 저장소 클론 및 이동
git clone https://github.com/BIGDannyK/rtzr-stt-pipeline.git
cd rtzr-stt-pipeline

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 필수 의존성 패키지 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정
프로젝트 루트 폴더에 `.env` 파일을 생성하고 발급받은 자격증명을 입력합니다. (`.env.example` 파일 참고)
기본 테스트용 샘플 음성 파일(`tests/sample.wav`)이 저장소에 기본 내장되어 있어 자격증명 입력 후 즉시 실행이 가능합니다.

```env
RTZR_CLIENT_ID=your_client_id_here
RTZR_CLIENT_SECRET=your_client_secret_here
AUDIO_PATH=tests/sample.wav
```

### 4. 파이프라인 실행
저장소에 내장된 기본 테스트 음성 파일(`tests/sample.wav`)을 사용하거나, 변경을 원할 경우 다른 음성 파일을 준비하고 `.env` 내 `AUDIO_PATH`를 수정한 뒤 아래 명령어로 벤치마크 파이프라인을 실행합니다.

```bash
python src/app.py
```

**참고**: 실행이 완료되면 콘솔창에 전사 타임라인이 출력됨과 동시에, `tests/` 디렉토리 내에 모델별 전사 결과가 반영된 `sample_whisper.srt` 및 `sample_sommers.srt` 자막 파일이 자동으로 생성되어 저장됩니다.

### 교차 모델 벤치마크 실험 결과
- **대상 데이터**: 영문 기술 약어(`stt`, `api`)가 포함된 10초 분량의 한국어 음성 (`tests/sample.wav`)
- **부스팅 키워드**: `['리턴제로', 'stt', '에이피아이']`
- **오인식 방어**: 무음 구간의 잡음으로 인한 `Whisper` 모델의 오인식(환각 현상)을 제어하기 위해, 단일 화자 전사 조건(`spk_count: 1`)을 명시하여 통제 변인으로 삼았습니다.

전사 로그 비교
```
--- [실험 1] 모델: whisper / 설정 화자수: 1인 ---
전사 완료 타임라인 (WHISPER)
[00:00]: 이번 과제는 리턴제로의 stt 기술을 활용합니다. 가이드 문서의 api.
[00:04]: 제약 요건을 파악해 파이프라인을 구축해냈습니다.

--- [실험 2] 모델: sommers / 설정 화자수: 1인 ---
전사 완료 타임라인 (SOMMERS)
[00:00]: 이번 과제는 리턴제로의 STT 기술을 활용합니다.
[00:03]: 가이드 문서에 API 제약 요건을 파악해 파이프라인을 구축해냈습니다.
```

### 결과 비교 분석

- **`Whisper`**: 주입된 바이어스 키워드를 텍스트 음절 흐름에 맞춰 소문자 알파벳(`stt`, `api`) 형태로 직관적으로 인식하여 전사합니다.
- **`Sommers`**: 한글 발음 표기(`'에이피아이'`)로 주입된 컨텍스트 바이어스를 수용하면서도, 최종 텍스트 출력 단계에서는 ITN(텍스트 정규화) 모듈을 통해 고유명사 표준 대문자 약어(`'STT'`, `'API'`)로 치환 및 매핑하여 변환 전사하는 텍스트 정제 특성을 보입니다.
