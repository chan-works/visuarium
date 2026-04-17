from pythonosc import udp_client


class OSCSender:
    def __init__(self, ip: str = "127.0.0.1", port: int = 9001,
                 chat_port: int = 9002,
                 prompt_address: str = "/agent/prompt",
                 chat_address: str = "/agent/chat"):
        self.ip = ip
        self.port = port
        self.chat_port = chat_port
        self.prompt_address = prompt_address
        self.chat_address = chat_address
        self._prompt_client = None
        self._chat_client = None
        self._build_clients()

    def _build_clients(self):
        try:
            self._prompt_client = udp_client.SimpleUDPClient(self.ip, self.port)
        except Exception as e:
            print(f"[OSC] 프롬프트 클라이언트 생성 실패: {e}")
            self._prompt_client = None
        try:
            self._chat_client = udp_client.SimpleUDPClient(self.ip, self.chat_port)
        except Exception as e:
            print(f"[OSC] 대화 클라이언트 생성 실패: {e}")
            self._chat_client = None

    def update(self, ip: str, port: int, chat_port: int,
               prompt_address: str, chat_address: str):
        self.ip = ip
        self.port = port
        self.chat_port = chat_port
        self.prompt_address = prompt_address
        self.chat_address = chat_address
        self._build_clients()

    def send_prompt(self, prompt: str):
        """최종 이미지 생성 프롬프트 전송"""
        if self._prompt_client is None:
            return
        try:
            self._prompt_client.send_message(self.prompt_address, prompt)
        except Exception as e:
            print(f"[OSC] 프롬프트 전송 실패: {e}")

    def send_chat(self, text: str):
        """사용자 발화 또는 AI 응답 텍스트 전송"""
        if self._chat_client is None:
            return
        try:
            self._chat_client.send_message(self.chat_address, text)
        except Exception as e:
            print(f"[OSC] 대화 전송 실패: {e}")
