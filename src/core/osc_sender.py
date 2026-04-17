from pythonosc import udp_client


class OSCSender:
    def __init__(self, ip: str = "127.0.0.1", port: int = 9001,
                 prompt_address: str = "/agent/prompt",
                 chat_address: str = "/agent/chat"):
        self.ip = ip
        self.port = port
        self.prompt_address = prompt_address   # 최종 이미지 생성 프롬프트
        self.chat_address = chat_address        # 사용자 발화 / AI 대화 텍스트
        self._client = None
        self._build_client()

    def _build_client(self):
        try:
            self._client = udp_client.SimpleUDPClient(self.ip, self.port)
        except Exception as e:
            print(f"[OSC] 클라이언트 생성 실패: {e}")
            self._client = None

    def update(self, ip: str, port: int,
               prompt_address: str, chat_address: str):
        self.ip = ip
        self.port = port
        self.prompt_address = prompt_address
        self.chat_address = chat_address
        self._build_client()

    def send_prompt(self, prompt: str):
        """최종 이미지 생성 프롬프트 전송"""
        if self._client is None:
            return
        try:
            self._client.send_message(self.prompt_address, prompt)
        except Exception as e:
            print(f"[OSC] 프롬프트 전송 실패: {e}")

    def send_chat(self, text: str):
        """사용자 발화 또는 AI 응답 텍스트 전송"""
        if self._client is None:
            return
        try:
            self._client.send_message(self.chat_address, text)
        except Exception as e:
            print(f"[OSC] 대화 전송 실패: {e}")
