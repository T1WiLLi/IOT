import asyncio
import cv2
import websockets
import json
import logging
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription, RTCIceCandidate
from av import VideoFrame

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
            logger.warning("Failed to capture frame")
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
                logger.info(f"Sending ICE candidate: {event.candidate.candidate}")
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

        logger.info("Sending offer")
        await ws.send(json.dumps({
            "type": "offer",
            "sdp": pc.localDescription.sdp
        }))

        logger.info("Waiting for answer")
        response = await ws.recv()
        answer = json.loads(response)
        if answer["type"] == "answer":
            logger.info("Received answer, setting remote description")
            await pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type="answer"))

        logger.info("Listening for ICE candidates")
        async for message in ws:
            try:
                data = json.loads(message)
                if data["type"] == "ice":
                    logger.info("Received ICE candidate")
                    candidate = data["candidate"]
                    logger.debug(f"ICE candidate data: {candidate}")
                    
                    if not candidate or "candidate" not in candidate:
                        logger.warning("Received invalid ICE candidate data")
                        continue

                    try:
                        # Correct way to create the RTCIceCandidate object
                        ice_candidate = RTCIceCandidate(
                            candidate=candidate["candidate"],
                            sdpMid=candidate["sdpMid"],
                            sdpMLineIndex=candidate["sdpMLineIndex"]
                        )
                        await pc.addIceCandidate(ice_candidate)
                        logger.info("ICE candidate added successfully")
                    except Exception as e:
                        logger.error(f"Error adding ICE candidate: {e}", exc_info=True)
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON message", exc_info=True)
            except KeyError:
                logger.error("Missing expected keys in message", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error processing message: {e}", exc_info=True)

        # Keep the connection alive
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(start_stream())
    except Exception as e:
        logger.error(f"An error occurred in main: {e}", exc_info=True)
