#!/bin/bash
# Color definitions
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   AI Research Assistant - Linux Start   ${NC}"
echo -e "${BLUE}========================================${NC}"

# Navigate to script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Start Backend
if [ -d ".venv" ]; then
    echo -e "${GREEN}[OK] 找到 Python 虛擬環境 (.venv)${NC}"
    source .venv/bin/activate
else
    echo -e "${RED}[ERROR] 未找到 .venv 資料夾，請先執行環境安裝！${NC}"
    exit 1
fi

# Create logs directory if not exists
mkdir -p logs

echo -e "${YELLOW}正在啟動後端服務...${NC}"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait a second to check if backend started successfully
sleep 2
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}[SUCCESS] 後端服務已啟動 (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}[ERROR] 後端服務啟動失敗，請檢查 logs/backend.log${NC}"
    exit 1
fi

# 2. Start Frontend
echo -e "${YELLOW}正在啟動前端服務...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
else
    echo -e "${RED}[ERROR] frontend 目錄不存在！${NC}"
    kill $BACKEND_PID
    exit 1
fi

# Wait a second to check if frontend started successfully
sleep 2
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}[SUCCESS] 前端服務已啟動 (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}[ERROR] 前端服務啟動失敗，請檢查 logs/frontend.log${NC}"
    kill $BACKEND_PID
    exit 1
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN} 服務啟動完畢！可用連結：${NC}"
echo -e " - ${BLUE}後端 API${NC}: http://localhost:8000"
echo -e " - ${BLUE}前端介面${NC}: http://localhost:3000 (Vite 設定的 Port)"
echo -e " - ${BLUE}API 文件${NC}: http://localhost:8000/api/docs"
echo -e "${YELLOW} 按 [Ctrl+C] 可同時關閉前端與後端服務${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Function to clean up on exit
cleanup() {
    echo -e "\n${YELLOW}正在關閉服務中...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}服務已關閉！${NC}"
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Keep the script running to keep trapping Ctrl+C
while true; do
    sleep 1
done
