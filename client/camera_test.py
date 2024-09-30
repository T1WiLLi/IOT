import asyncio
import cv2
import websockets
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from av import VideoFrame

class CameraStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        
    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        
        if not ret:
            return None
        
        video_frame = VideoFrame.from_nbarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

async def start_stream():
    pc = RTCPeerConnection()
    pc.addTrack(CameraStreamTrack())
    
    async with websockets.connect("ws://192.168.2.117:8080/ws") as ws:
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        await ws.send(json.dumps({
            "type": "offer",
            "sdp": pc.localDescription.sdp
        }))
        
        response = await ws.recv()
        answer = json.loads(response)
        if answer["type"] == "answer":
            await pc.setRemoteDescription(RTCSessionDescription(answer["sdp"], "answer"))
        
        async for message in ws:
            ice = json.loads(message)
            if ice["type"] == "ice":
                candidate = ice["candidate"]
                await pc.addIceCandidate(candidate)

asyncio.run(start_stream())
