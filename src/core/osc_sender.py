from pythonosc import udp_client


class OSCSender:
    def __init__(self, ip: str = "127.0.0.1", port: int = 9001, address: str = "/visuarium/prompt"):
        self.ip = ip
        self.port = port
        self.address = address
        self._client = None
        self._build_client()

    def _build_client(self):
        try:
            self._client = udp_client.SimpleUDPClient(self.ip, self.port)
        except Exception as e:
            print(f"[OSC] 클라이언트 생성 실패: {e}")
            self._client = None

    def update(self, ip: str, port: int, address: str):
        self.ip = ip
        self.port = port
        self.address = address
        self._build_client()

    def send_prompt(self, prompt: str):
        if self._client is None:
            return
        try:
            self._client.send_message(self.address, prompt)
        except Exception as e:
            print(f"[OSC] 전송 실패: {e}")
