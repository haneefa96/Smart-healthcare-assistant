#include "web_server.h"
#include "config.h"
#include "motor_driver.h"
#include "vitals_dsp.h"
#include "audio_i2s.h"
#include <ArduinoJson.h>

// Global server instances
AsyncWebServer   g_httpServer(80);
AsyncWebSocket   g_wsControl("/ws/control");
WebSocketsClient g_gatewayClient;

// Broadcast live sensor telemetry to connected web dashboards
void broadcastTelemetry() {
    VitalsData vd;
    xSemaphoreTake(g_vitalsMutex, portMAX_DELAY);
    vd = g_vitals;
    xSemaphoreGive(g_vitalsMutex);

    int aud = (int)audioGetState();
    char json[128];
    if (vd.fingerDetected && vd.isValid) {
        snprintf(json, sizeof(json),
                 "{\"hr\":%.1f,\"spo2\":%.1f,\"finger\":true,\"audio\":%d}",
                 vd.heartRate, vd.spo2, aud);
    } else {
        snprintf(json, sizeof(json),
                 "{\"finger\":%s,\"audio\":%d}",
                 vd.fingerDetected ? "true" : "false", aud);
    }
    g_wsControl.textAll(json);
}

// WebSocket Event Handler for Web Dashboard
static void onControlWSEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
                             AwsEventType type, void *arg, uint8_t *data, size_t len) {
    (void)server;
    if (type != WS_EVT_DATA) return;
    AwsFrameInfo *info = (AwsFrameInfo*)arg;
    if (!info->final || info->opcode != WS_TEXT) return;
    data[len] = '\0';

    // Handle Ping
    if (strcmp((char*)data, "ping") == 0) {
        client->text("{\"pong\":true}");
        return;
    }

    JsonDocument doc;
    if (deserializeJson(doc, (char*)data) != DeserializationError::Ok) return;

    // Motor commands from D-pad
    if (doc["dir"].is<const char*>()) {
        const char *d = doc["dir"].as<const char*>();
        uint8_t sp = doc["speed"] | 170;
        MotorCmd cmd;
        cmd.speedL = sp;
        cmd.speedR = sp;
        cmd.timestamp = millis();

        if      (!strcmp(d, "F")) cmd.dir = MotorDir::FORWARD;
        else if (!strcmp(d, "B")) cmd.dir = MotorDir::BACKWARD;
        else if (!strcmp(d, "L")) cmd.dir = MotorDir::LEFT;
        else if (!strcmp(d, "R")) cmd.dir = MotorDir::RIGHT;
        else                      cmd.dir = MotorDir::STOP;

        xQueueSend(g_motorQueue, &cmd, 0);
    }

    // Voice Toggle from UI
    if (doc["voice"].is<bool>()) {
        if (doc["voice"].as<bool>()) audioStartRecording();
        else                         audioStopRecording();
    }
}

// Gateway WebSocket Event Handler (Connects to Python Backend)
static void onGatewayEvent(WStype_t type, uint8_t *payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            Serial.println("[AI-GW] Connected to Python AI Voice Gateway");
            break;
        case WStype_BIN:
            // Stream synthesized PCM TTS speech chunk to speaker
            audioQueuePlaybackChunk(payload, length);
            break;
        case WStype_TEXT:
            // Forward AI transcript to web dashboard clients
            g_wsControl.textAll((char*)payload);
            break;
        case WStype_DISCONNECTED:
            Serial.println("[AI-GW] Disconnected from Gateway — will auto-reconnect");
            break;
        default: break;
    }
}

// Lightweight landing page served directly by ESP32 HTTP Server
static const char STATUS_PAGE_HTML[] PROGMEM = R"rawhtml(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HealthBot ESP32-S3</title>
  <style>
    body{margin:0;min-height:100vh;background:#060911;color:#f8fafc;font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:rgba(22,28,48,0.85);border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:36px;max-width:440px;text-align:center;box-shadow:0 12px 40px rgba(0,0,0,0.5)}
    .icon{font-size:3rem;margin-bottom:12px}
    h1{font-size:1.4rem;margin:0 0 8px;color:#a78bfa}
    p{font-size:0.88rem;color:#94a3b8;line-height:1.5;margin:0 0 20px}
    .badge{display:inline-block;padding:4px 14px;border-radius:99px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#34d399;font-weight:600;font-size:0.75rem;margin-bottom:20px}
    .btn{display:inline-block;background:#7c6df0;color:#fff;text-decoration:none;padding:12px 28px;border-radius:99px;font-weight:600;font-size:0.9rem;box-shadow:0 0 20px rgba(124,109,240,0.4);transition:transform 0.2s}
    .btn:hover{transform:scale(1.04)}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🏥</div>
    <h1>HealthBot OS</h1>
    <div class="badge">ESP32-S3 Online & Running</div>
    <p>Tele-monitoring & AI Voice Gateway active.<br>Open the modern web dashboard to view live vitals and control the robot.</p>
    <a class="btn" href=")rawhtml" DASHBOARD_URL R"rawhtml(">Open HealthBot Dashboard &rarr;</a>
  </div>
</body>
</html>
)rawhtml";

void webserverInit() {
    g_wsControl.onEvent(onControlWSEvent);
    g_httpServer.addHandler(&g_wsControl);

    g_httpServer.on("/", HTTP_GET, [](AsyncWebServerRequest *req) {
        req->send_P(200, "text/html", STATUS_PAGE_HTML);
    });

    g_httpServer.on("/ping", HTTP_GET, [](AsyncWebServerRequest *req) {
        req->send(200, "text/plain", "pong");
    });

    g_httpServer.begin();
    Serial.println("[WEB] Server listening on port 80");
}

void TaskGateway(void *pvParameters) {
    (void)pvParameters;
    // Parse ws://<host>:<port><path>
    String uri = AI_GATEWAY_WS;
    int schemeEnd = uri.indexOf("://") + 3;
    int portIndex = uri.indexOf(':', schemeEnd);
    int pathIndex = uri.indexOf('/', schemeEnd);

    String host = uri.substring(schemeEnd, (portIndex > 0 && portIndex < pathIndex) ? portIndex : pathIndex);
    uint16_t port = (portIndex > 0 && portIndex < pathIndex) ? uri.substring(portIndex + 1, pathIndex).toInt() : 80;
    String path = uri.substring(pathIndex);

    g_gatewayClient.begin(host.c_str(), port, path.c_str());
    g_gatewayClient.onEvent(onGatewayEvent);
    g_gatewayClient.setReconnectInterval(3000);
    Serial.printf("[AI-GW] Target: %s:%d%s\n", host.c_str(), port, path.c_str());

    const size_t chunkSize = I2S_DMA_FRAME * (I2S_BITS / 8);

    for (;;) {
        g_gatewayClient.loop();

        if (audioGetState() == AudioState::LISTENING) {
            size_t rxLen = 0;
            void *micChunk = xRingbufferReceiveUpTo(g_micTxRingBuf, &rxLen, pdMS_TO_TICKS(20), chunkSize);
            if (micChunk && rxLen > 0) {
                g_gatewayClient.sendBIN((uint8_t*)micChunk, rxLen);
                vRingbufferReturnItem(g_micTxRingBuf, micChunk);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

void TaskTelemetry(void *pvParameters) {
    (void)pvParameters;
    const TickType_t period = pdMS_TO_TICKS(1000); // 1 Hz
    TickType_t lastWakeTime = xTaskGetTickCount();
    Serial.println("[TASK] Web Telemetry pinned to Core " + String(xPortGetCoreID()));

    for (;;) {
        g_wsControl.cleanupClients();
        broadcastTelemetry();
        vTaskDelayUntil(&lastWakeTime, period);
    }
}
