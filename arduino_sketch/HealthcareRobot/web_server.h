#pragma once
#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include <AsyncTCP.h>
#include <WebSocketsClient.h>

// Global handles
extern AsyncWebServer   g_httpServer;
extern AsyncWebSocket   g_wsControl;
extern WebSocketsClient g_gatewayClient;

// Public Server Functions
void webserverInit();
void broadcastTelemetry();
void TaskGateway(void *pvParameters);
void TaskTelemetry(void *pvParameters);
