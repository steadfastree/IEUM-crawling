# 빌드 스테이지
FROM python:3.9-slim as builder

WORKDIR /app

# 필요한 패키지 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc

# 가상 환경 생성 및 활성화
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 실행 스테이지
FROM python:3.9-slim

WORKDIR /app

# 빌드 스테이지에서 생성된 가상 환경 복사
COPY --from=builder /opt/venv /opt/venv

# 환경 변수 설정
ENV PATH="/opt/venv/bin:$PATH"

# 애플리케이션 코드 복사
COPY . .

# 포트 설정
EXPOSE 5001

# 실행 명령
CMD ["python", "app.py"]