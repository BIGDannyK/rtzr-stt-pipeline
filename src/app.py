import os
import sys
from dotenv import load_dotenv
from client import RTZRClient

load_dotenv()

def format_srt_time(ms: int) -> str:
    """밀리초(ms) 데이터를 SRT 자막 표준 포맷(HH:MM:SS,mmm)으로 변환합니다."""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def save_as_srt(utterances: list, output_path: str, use_diarization: bool):
    """전사 결과를 자막 파일(.srt)로 저장합니다."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for i, utt in enumerate(utterances, 1):
                start_ms = utt['start_at']
                # duration 누락 시 기본값 2초(2000ms) 부여
                duration = utt.get('duration', 2000)
                end_ms = start_ms + duration
                
                start_time = format_srt_time(start_ms)
                end_time = format_srt_time(end_ms)
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                
                # 화자 분리 활성화 여부에 따라 화자 정보 추가
                speaker_info = f"[화자 {utt['spk']}] " if use_diarization and 'spk' in utt else ""
                f.write(f"{speaker_info}{utt['msg']}\n\n")
        print(f"[INFO] 자막 파일 저장 완료: {output_path}")
    except Exception as e:
        print(f"[WARNING] 자막 파일 저장 실패: {e}")

def format_time(ms: int) -> str:
    """밀리초(ms) 데이터를 [MM:SS] 포맷의 문자열로 정확히 변환합니다."""
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"[{minutes:02d}:{seconds:02d}]"

def build_safe_config(model_name: str, spk_count: int, raw_keywords: list) -> dict:
    """모델별/화자별 제약 조건을 고려하여 안전한 OpenAPI 설정을 빌드합니다."""
    config = {
        "model_name": model_name,
        "use_paragraph_splitter": True,
        "use_disfluency_filter": True
    }
    
    # 화자 분리 설정 제어 (spk_count가 1보다 크면 화자 분리 활성화)
    if spk_count > 1:
        config["use_diarization"] = True
        config["diarization"] = {"spk_count": spk_count}
    else:
        config["use_diarization"] = False
        
    # 키워드 부스팅 제약 조건 처리 (한국어 전사 기준) 
    if raw_keywords:
        if model_name == "sommers":
            # 영문 표기는 필터링하고 한글 발음만 통과 
            safe_keywords = [k for k in raw_keywords if not k.encode().isalpha()]
            config["keywords"] = safe_keywords
        elif model_name == "whisper":
            config["language"] = "ko"  # 필수 제약 요건 
            config["keywords"] = raw_keywords
            
    return config

def run_stt_pipeline(client: RTZRClient, audio_path: str, model: str, spk_count: int, keywords: list):
    print(f"\n--- [실험 시작] 모델: {model} / 설정 화자수: {spk_count}인 ---")
    
    config = build_safe_config(model_name=model, spk_count=spk_count, raw_keywords=keywords)
    
    try:
        transcribe_id = client.request_transcription(audio_path, config)
        final_result = client.wait_for_completion(transcribe_id)
        
        print(f"\n✨ 전사 완료 타임라인 ({model.upper()})")
        utterances = final_result.get("results", {}).get("utterances", [])
        
        if not utterances:
            print("발화 데이터가 없습니다.")
            return

        for utt in utterances:
            time_stamp = format_time(utt['start_at'])
            # 화자 분리가 켜진 경우에만 화자 번호 출력
            speaker_info = f" (화자 {utt['spk']})" if config.get("use_diarization") else ""
            print(f"{time_stamp}{speaker_info}: {utt['msg']}")
            
        # -------------------------------------------------------------
        # [추가] SRT 자막 파일 자동 추출 및 저장 로직
        # -------------------------------------------------------------
        # 결과 파일명을 모델명에 맞게 동적 설정 (예: tests/sample.wav -> tests/sample_whisper.srt)
        srt_output_path = audio_path.replace(".wav", f"_{model.lower()}.srt")
        save_as_srt(utterances, srt_output_path, config.get("use_diarization", False))
        # -------------------------------------------------------------

    except Exception as e:
        print(f"[ERROR] {model} 파이프ライン 구동 실패: {e}")

def main():
    audio_path = os.getenv("AUDIO_PATH", "tests/sample.wav")
    keywords = ["리턴제로", "stt", "에이피아이"]
    
    print(f"==================================================")
    print(f"🚀 리턴제로 OpenAI 교차 모델 성능 비교 벤치마크 CLI")
    print(f"[*] 대상 파일: {audio_path}")
    print(f"[*] 부스팅 키워드: {keywords}")
    print(f"==================================================")
    
    try:
        client = RTZRClient()
        
        # [실험 1] Whisper 모델 + 화자 1명 강제 고정 (환각 현상 방어 테스트)
        run_stt_pipeline(client, audio_path, model="whisper", spk_count=1, keywords=keywords)
        
        # [실험 2] 리턴제로 Sommers 모델 (자체 E2E 엔진 처리 효율 테스트) [cite: 16]
        run_stt_pipeline(client, audio_path, model="sommers", spk_count=1, keywords=keywords)
        
    except Exception as e:
        print(f"[FATAL] 초기화 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()