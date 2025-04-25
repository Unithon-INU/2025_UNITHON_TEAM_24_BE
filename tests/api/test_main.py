# tests/api/test_main.py
from fastapi.testclient import TestClient
from app.main import app # FastAPI 앱 인스턴스 가져오기
from app.core.config import settings # settings 사용 위해 import

# TestClient 인스턴스 생성
client = TestClient(app)

def test_read_root():
    """루트 경로 GET 요청 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome to {settings.PROJECT_NAME}!"}