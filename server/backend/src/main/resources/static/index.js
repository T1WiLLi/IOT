const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});

pc.ontrack = function(event) {
    console.log("Received track event:", event);
    console.log("Track kind:", event.track.kind);
    console.log("Track readyState:", event.track.readyState);
    const videoElement = document.getElementById("video");
    if (videoElement.srcObject !== event.streams[0]) {
        console.log("Setting video srcObject");
        videoElement.srcObject = event.streams[0];
    }
};

pc.onicecandidate = function(event) {
    if (event.candidate) {
        console.log("New ICE candidate:", event.candidate);
        const candidateObj = {
            type: "ice",
            candidate: {
                candidate: event.candidate.candidate,
                sdpMid: event.candidate.sdpMid,
                sdpMLineIndex: event.candidate.sdpMLineIndex,
                usernameFragment: event.candidate.usernameFragment
            }
        };
        console.log("Sending ICE candidate:", candidateObj);
        ws.send(JSON.stringify(candidateObj));
    }
};

const ws = new WebSocket("ws://192.168.2.117:8080/ws");

ws.onopen = function() {
    console.log("WebSocket connection opened");
};

ws.onmessage = async function(event) {
    try {
        const message = JSON.parse(event.data);
        console.log("Message received:", message);

        if (message.type === "offer") {
            console.log("Setting remote description (offer)");
            await pc.setRemoteDescription(new RTCSessionDescription(message));

            console.log("Creating answer");
            const answer = await pc.createAnswer();
            console.log("Setting local description (answer)");
            await pc.setLocalDescription(answer);

            console.log("Sending answer");
            ws.send(JSON.stringify({
                type: "answer",
                sdp: pc.localDescription.sdp
            }));
        } else if (message.type === "ice") {
            console.log("Received ICE candidate:", message.candidate);
            try {
                if (message.candidate && message.candidate.candidate) {
                    await pc.addIceCandidate(new RTCIceCandidate(message.candidate));
                    console.log("ICE candidate added successfully");
                } else {
                    console.warn("Received invalid ICE candidate");
                }
            } catch (error) {
                console.error("Error adding ICE candidate:", error);
            }
        }
    } catch (error) {
        console.error("Error in onmessage:", error);
    }
};

ws.onclose = function() {
    console.log("WebSocket connection closed");
};

ws.onerror = function(error) {
    console.error("WebSocket error:", error);
};

// Add error handling for the video element
const videoElement = document.getElementById("video");
videoElement.onerror = function(error) {
    console.error("Video element error:", error);
};