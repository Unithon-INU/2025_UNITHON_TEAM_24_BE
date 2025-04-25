# Unithon 2025 - Team 24 백엔드 프로젝트

여행 경로 추천 및 커뮤니티 서비스를 위한 백엔드 API 서버입니다.

## 기술 스택

- Python 3.10+
- FastAPI
- PostgreSQL
- SQLAlchemy ORM
- Firebase Authentication
- Google Places API
- Docker (선택사항)

## 설치 및 환경설정

### 1. 저장소 클론

```bash
git clone https://github.com/Unithon-INU/2025_UNITHON_TEAM_24_BE.git
cd 2025_UNITHON_TEAM_24_BE
```

### 2. 가상환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate
```

### 3. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 필요한 환경변수를 설정합니다.
`.env.example` 파일을 참고하여 작성해주세요.

```bash
# .env 파일 예시
cp .env.example .env

# 편집기로 .env 파일 열기
# 필요한 값들을 실제 값으로 수정
```

### 5. Firebase 설정

Firebase Admin SDK를 사용하기 위해 서비스 계정 키 파일이 필요합니다:

1. [Firebase 콘솔](https://console.firebase.google.com/)에서 프로젝트 생성 또는 선택
2. 프로젝트 설정 > 서비스 계정 > Firebase Admin SDK > 새 비공개 키 생성
3. 다운로드 받은 JSON 파일을 프로젝트 루트에 `serviceAccountKey.json` 이름으로 저장
4. `.env` 파일의 `GOOGLE_APPLICATION_CREDENTIALS` 값에 경로 설정

### 6. 데이터베이스 설정

#### 방법 1: 로컬 PostgreSQL 설치

PostgreSQL 데이터베이스를 설정하고, `.env` 파일의 `DATABASE_URL`을 업데이트합니다.

```bash
# PostgreSQL 예시
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
```

#### 방법 2: Docker를 이용한 PostgreSQL 설정 (추천)

Docker를 사용하여 간편하게 PostgreSQL 데이터베이스를 실행할 수 있습니다.

```bash
# PostgreSQL 컨테이너 실행
docker run --name uni-postgres-db \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_USER=your_username \
  -e POSTGRES_DB=your_database \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  -d postgres
```

위 명령어에서 사용된 옵션들:
- `--name`: 컨테이너 이름 설정
- `-e`: 환경변수 설정 (데이터베이스 사용자명, 비밀번호, DB 이름)
- `-p`: 포트 포워딩 (호스트:컨테이너)
- `-v`: 데이터 볼륨 마운트 (데이터 영속성 보장)
- `-d`: 백그라운드 모드로 실행

그런 다음 `.env` 파일의 `DATABASE_URL`을 다음과 같이 설정합니다:

```bash
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/your_database
```

Docker 컨테이너 관리 명령어:
```bash
# 컨테이너 상태 확인
docker ps -a

# 컨테이너 중지
docker stop uni-postgres-db

# 컨테이너 시작
docker start uni-postgres-db

# 컨테이너 삭제 (데이터는 볼륨에 보존됨)
docker rm uni-postgres-db
```

### 7. 마이그레이션 실행

```bash
# 데이터베이스 마이그레이션 실행
alembic upgrade head
```

## 서버 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

서버가 성공적으로 실행되면 `http://127.0.0.1:8000`에서 API 서버에 접근할 수 있습니다.

## API 문서

FastAPI의 자동 생성 API 문서는 다음 URL에서 확인할 수 있습니다:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 테스트

```bash
# 테스트 실행
pytest
```

## 라이센스

이 프로젝트는 MIT 라이센스로 배포됩니다.