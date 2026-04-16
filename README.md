# 멀티턴 대화형 에이전트

멀티턴 AI 대화로 관객의 짧은 입력을 풍부한 이미지 생성 프롬프트로 확장하는 AI 미디어아트 설치 작품용 프로그램.

## 실행 방법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 실행
```bash
python main.py
```

### 3. 설정
- 우측 [설정] 탭에서 Claude API Key 입력
- 마이크, OSC, Whisper 모델 설정 가능

## Windows EXE 빌드
Windows 환경에서:
```
build_windows.bat
```
→ `dist/Visuarium/Visuarium.exe` 생성

## 구조
```
visuarium/
├── main.py                  # 진입점
├── config.json              # 설정 파일 (자동 저장)
├── data.db                  # SQLite DB (자동 생성)
├── requirements.txt
├── build.spec               # PyInstaller 스펙
└── src/
    ├── core/
    │   ├── agent.py         # Claude API 멀티턴 에이전트
    │   ├── stt.py           # Whisper STT + VAD
    │   ├── database.py      # SQLite CRUD
    │   ├── websocket_server.py  # WS 서버 (port 9000)
    │   └── osc_sender.py    # OSC 전송
    ├── gui/
    │   ├── main_window.py   # 메인 윈도우 + 탭 전환
    │   ├── session_panel.py # 세션 진행 화면
    │   ├── settings_panel.py # 설정 화면
    │   └── data_panel.py    # 데이터 관리 + 엑셀 내보내기
    └── utils/
        └── excel_export.py  # Excel 내보내기

## TouchDesigner 연동
- WebSocket: `ws://localhost:9000` 수신 → JSON `{"type":"prompt","data":"..."}`
- OSC: 기본 `127.0.0.1:9001` → address `/visuarium/prompt`
```
