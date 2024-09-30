import asyncio
import cv2
import websockets
import json
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription, RTCIceCandidate
from av import VideoFrame

class CameraStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise IOError("Cannot open webcam")
        
    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        
        if not ret:
            print("Failed to capture frame")
            return None
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

async def start_stream():
    pc = RTCPeerConnection()
    pc.addTrack(CameraStreamTrack())
    
    async with websockets.connect("ws://192.168.2.117:8080/ws") as ws:
        @pc.on("icecandidate")
        async def on_icecandidate(event):
            if event.candidate:
                print("Sending ICE candidate")
                await ws.send(json.dumps({
                    "type": "ice",
                    "candidate": {
                        "candidate": event.candidate.candidate,
                        "sdpMid": event.candidate.sdpMid,
                        "sdpMLineIndex": event.candidate.sdpMLineIndex
                    }
                }))

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        print("Sending offer")
        await ws.send(json.dumps({
            "type": "offer",
            "sdp": pc.localDescription.sdp
        }))
        
        print("Waiting for answer")
        response = await ws.recv()
        answer = json.loads(response)
        if answer["type"] == "answer":
            print("Received answer, setting remote description")
            await pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type="answer"))
        
        print("Listening for messages")
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "ice":
                print("Received ICE candidate")
                candidate = data["candidate"]
                await pc.addIceCandidate(RTCIceCandidate(
                    sdpMid=candidate.get("sdpMid"),
                    sdpMLineIndex=candidate.get("sdpMLineIndex"),
                    candidate=candidate["candidate"]
                ))

try:
    asyncio.run(start_stream())
except Exception as e:
    print(f"An error occurred: {e}")