package cam.door.backend.socket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class WebRTCSignalingHandler extends TextWebSocketHandler {

    private static final Logger logger = LoggerFactory.getLogger(WebRTCSignalingHandler.class);
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        sessions.put(session.getId(), session);
        logger.info("Connection established with session ID: {}", session.getId());
    }

    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        logger.info("Message received from session {}: {}", session.getId(), payload);

        JsonNode jsonNode = objectMapper.readTree(payload);
        String type = jsonNode.get("type").asText();

        if ("offer".equals(type) || "answer".equals(type) || "ice".equals(type)) {
            logger.info("Broadcasting {} message to peers", type);
            broadcastToPeers(session, message);
        }
    }

    private void broadcastToPeers(WebSocketSession sender, TextMessage message) throws Exception {
        for (WebSocketSession peer : sessions.values()) {
            if (!peer.getId().equals(sender.getId())) {
                logger.info("Relaying message to peer with session ID: {}", peer.getId());
                peer.sendMessage(message);
            }
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        sessions.remove(session.getId());
        logger.info("Connection closed with session ID: {}", session.getId());
    }
}
