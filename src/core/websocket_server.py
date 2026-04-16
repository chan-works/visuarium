import asyncio
import threading
import websockets
import json
from typing import Set


class WebSocketServer:
    def __init__(self, port: int = 9000):
        self.port = port
        self._clients: Set = set()
        self._loop = None
        self._thread = None
        self._server = None
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def send_prompt(self, prompt: str):
        if not self._loop or not self._running:
            return
        message = json.dumps({"type": "prompt", "data": prompt})
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)

    async def _broadcast(self, message: str):
        if not self._clients:
            return
        dead = set()
        for ws in self._clients.copy():
            try:
                await ws.send(message)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    async def _handler(self, websocket):
        self._clients.add(websocket)
        try:
            async for _ in websocket:
                pass
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def serve():
            async with websockets.serve(self._handler, "0.0.0.0", self.port):
                await asyncio.Future()  # run forever

        self._loop.run_until_complete(serve())
