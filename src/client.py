import os
import json
import time
import requests
from typing import Any, Dict, Optional

class RTZRClient:
    def __init__(self, base_url: str = "https://openapi.vito.ai") -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = os.getenv("RTZR_CLIENT_ID")
        self.client_secret = os.getenv("RTZR_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("환경변수(RTZR_CLIENT_ID, RTZR_CLIENT_SECRET)를 설정해주세요.")
            
        self._sess = requests.Session()
        self._token_info: Optional[Dict[str, Any]] = None

    @property
    def token(self) -> str:
        """JWT 토큰 만료 30분 전 자동 갱신"""
        if self._token_info is None or self._token_info.get("expire_at", 0) < time.time() - 1800:
            url = f"{self.base_url}/v1/authenticate"
            resp = self._sess.post(
                url,
                data={"client_id": self.client_id, "client_secret": self.client_secret}
            )
            resp.raise_for_status()
            self._token_info = resp.json()
        return self._token_info["access_token"]

    def _get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "accept": "application/json"}

    def request_transcription(self, file_path: str, config: Dict[str, Any]) -> str:
        """음성 파일 전사 요청 후 TRANSCRIBE_ID 반환"""
        url = f"{self.base_url}/v1/transcribe"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"오디오 파일이 없습니다: {file_path}")
            
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {"config": json.dumps(config)}
            resp = self._sess.post(url, headers=self._get_headers(), files=files, data=data)
            resp.raise_for_status()
            return resp.json()["id"]

    def get_result(self, transcribe_id: str) -> Dict[str, Any]:
        """진행 상태 조회"""
        url = f"{self.base_url}/v1/transcribe/{transcribe_id}"
        resp = self._sess.get(url, headers=self._get_headers())
        resp.raise_for_status()
        return resp.json()

    def wait_for_completion(self, transcribe_id: str, poll_interval: int = 5) -> Dict[str, Any]:
        """5초 주기 Polling 및 에러 핸들링"""
        print(f"[INFO] 전사 작업 대기 중... (ID: {transcribe_id})")
        while True:
            result = self.get_result(transcribe_id)
            status = result.get("status")
            
            if status == "completed":
                return result
            elif status == "failed":
                raise RuntimeError(f"전사 실패 원인: {result.get('error')}")
                
            print(".", end="", flush=True)
            time.sleep(poll_interval)