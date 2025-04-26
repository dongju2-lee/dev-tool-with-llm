#!/bin/bash
set -e

# 환경 변수 검증
if [ -z "$ARGOCD_SERVER" ]; then
  echo "Error: ARGOCD_SERVER 환경 변수가 설정되지 않았습니다."
  exit 1
fi

if [ -z "$ARGOCD_TOKEN" ] && [ -z "$ARGOCD_USERNAME" ] && [ -z "$ARGOCD_PASSWORD" ]; then
  echo "Error: ARGOCD_TOKEN, ARGOCD_USERNAME/ARGOCD_PASSWORD 중 하나는 제공되어야 합니다."
  exit 1
fi

# ARGOCD_USERNAME과 ARGOCD_PASSWORD가 제공된 경우 토큰 생성
if [ -n "$ARGOCD_USERNAME" ] && [ -n "$ARGOCD_PASSWORD" ]; then
  echo "사용자 인증 정보로 ArgoCD 토큰 생성 중..."
  
  INSECURE_FLAG=""
  if [ "$ARGOCD_INSECURE" = "true" ]; then
    INSECURE_FLAG="--insecure"
  fi
  
  # argocd CLI 설치 (필요한 경우)
  if ! command -v argocd &> /dev/null; then
    echo "ArgoCD CLI 설치 중..."
    curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    chmod +x /usr/local/bin/argocd
  fi
  
  # 로그인 및 토큰 생성
  export ARGOCD_TOKEN=$(argocd login $ARGOCD_SERVER --username $ARGOCD_USERNAME --password $ARGOCD_PASSWORD $INSECURE_FLAG --plaintext --auth-token)
fi

echo "ArgoCD MCP 서버 시작 중..."
python -u mcp_server.py 