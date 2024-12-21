import asyncio
import json

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedOK

from .singleton_storage import SingletonStorage

session_state = SingletonStorage()

async def handler(websocket):
    print("new connection")
    print("active sessions", session_state.data.keys())

    session_id = websocket.request.path[1:]
    if session_id in session_state.data:
        session_state.data[session_id]["ws"] = websocket

        await websocket.send(json.dumps(session_state.data[session_id]["messages"]))
    else:
        print(f"Session ID {session_id} not found")

    while True:
        try:
            message = await websocket.recv()
            print(f"received message {message} from client")
        except ConnectionClosedOK:
            print(f"Terminated")
            break


async def websocket_server():
    server = await serve(handler, "", 8001)
    print("WebSocket server started on ws://localhost:8001")
    return server.serve_forever()


