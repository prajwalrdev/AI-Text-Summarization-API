#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "gemini.h"
#include "db.h"

#pragma comment(lib, "ws2_32.lib")

#define PORT 8000
#define BUFFER_SIZE 65536
#define SUMMARY_BUFFER_SIZE 8192

// Helper function to read .env file in C
static void load_env_file(const char *path, char *gemini_key, size_t key_size, char *db_url, size_t url_size) {
    FILE *fp = fopen(path, "r");
    if (!fp) return;

    char line[512];
    while (fgets(line, sizeof(line), fp)) {
        // Remove trailing newline
        line[strcspn(line, "\r\n")] = '\0';

        if (strncmp(line, "GEMINI_API_KEY=", 15) == 0) {
            strncpy(gemini_key, line + 15, key_size - 1);
            gemini_key[key_size - 1] = '\0';
        } else if (strncmp(line, "DATABASE_URL=", 13) == 0) {
            strncpy(db_url, line + 13, url_size - 1);
            db_url[url_size - 1] = '\0';
        }
    }
    fclose(fp);
}

// Check if string contains only whitespace
static int is_whitespace_only(const char *str) {
    while (*str) {
        if (!isspace((unsigned char)*str)) return 0;
        str++;
    }
    return 1;
}

// Extract JSON field "text" value from body
static int extract_json_text(const char *json_body, char *output, size_t max_size) {
    const char *key = "\"text\":";
    const char *pos = strstr(json_body, key);
    if (!pos) return -1;

    pos += strlen(key);
    while (*pos && (*pos == ' ' || *pos == '\t')) pos++;

    if (*pos != '"') return -1;
    pos++; // Skip opening quote

    size_t i = 0;
    while (*pos && i < max_size - 1) {
        if (*pos == '\\' && *(pos + 1) == '"') {
            output[i++] = '"';
            pos += 2;
        } else if (*pos == '\\' && *(pos + 1) == 'n') {
            output[i++] = '\n';
            pos += 2;
        } else if (*pos == '"') {
            break; // Closing quote
        } else {
            output[i++] = *pos++;
        }
    }
    output[i] = '\0';
    return 0;
}

// Send HTTP JSON response
static void send_http_response(SOCKET client_socket, int status_code, const char *status_text, const char *json_body) {
    char header_buffer[1024];
    int body_len = (int)strlen(json_body);

    snprintf(header_buffer, sizeof(header_buffer),
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "\r\n",
        status_code, status_text, body_len
    );

    send(client_socket, header_buffer, (int)strlen(header_buffer), 0);
    send(client_socket, json_body, body_len, 0);
}

int main(void) {
    char gemini_api_key[256] = {0};
    char database_url[512] = {0};

    // Load credentials from .env (check local or parent folder)
    load_env_file(".env", gemini_api_key, sizeof(gemini_api_key), database_url, sizeof(database_url));
    if (strlen(gemini_api_key) == 0) {
        load_env_file("../.env", gemini_api_key, sizeof(gemini_api_key), database_url, sizeof(database_url));
    }

    printf("==============================================================\n");
    printf("    AI TEXT SUMMARIZATION REST API - C LANGUAGE BACKEND\n");
    printf("==============================================================\n");
    printf("GEMINI_API_KEY: %s\n", strlen(gemini_api_key) > 0 ? "LOADED" : "NOT FOUND (Set in .env)");
    printf("DATABASE_URL:   %s\n", strlen(database_url) > 0 ? database_url : "DEFAULT");
    printf("Listening on:   http://127.0.0.1:%d\n", PORT);
    printf("==============================================================\n\n");

    // Initialize Database
    db_init(database_url);

    // Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        fprintf(stderr, "Failed to initialize Winsock.\n");
        return 1;
    }

    SOCKET server_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server_socket == INVALID_SOCKET) {
        fprintf(stderr, "Failed to create socket.\n");
        WSACleanup();
        return 1;
    }

    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    server_addr.sin_port = htons(PORT);

    if (bind(server_socket, (struct sockaddr *)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        fprintf(stderr, "Bind failed on port %d. (Is another process using it?)\n", PORT);
        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    if (listen(server_socket, SOMAXCONN) == SOCKET_ERROR) {
        fprintf(stderr, "Listen failed.\n");
        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    printf("Server successfully started! Waiting for HTTP requests...\n\n");

    char *recv_buffer = (char *)malloc(BUFFER_SIZE);
    char extracted_text[32768];
    char summary_output[SUMMARY_BUFFER_SIZE];

    while (1) {
        struct sockaddr_in client_addr;
        int client_len = sizeof(client_addr);
        SOCKET client_socket = accept(server_socket, (struct sockaddr *)&client_addr, &client_len);

        if (client_socket == INVALID_SOCKET) {
            continue;
        }

        int bytes_received = recv(client_socket, recv_buffer, BUFFER_SIZE - 1, 0);
        if (bytes_received <= 0) {
            closesocket(client_socket);
            continue;
        }
        recv_buffer[bytes_received] = '\0';

        // 1. Health Endpoint: GET /health
        if (strncmp(recv_buffer, "GET /health", 11) == 0) {
            const char *res_json = "{\"status\":\"healthy\",\"version\":\"1.0.0\",\"language\":\"C\"}";
            send_http_response(client_socket, 200, "OK", res_json);
            closesocket(client_socket);
            continue;
        }

        // 2. Main Summarization Endpoint: POST /summarize
        if (strncmp(recv_buffer, "POST /summarize", 15) == 0) {
            char *body_start = strstr(recv_buffer, "\r\n\r\n");
            if (!body_start) {
                send_http_response(client_socket, 400, "Bad Request", "{\"detail\":\"Malformed HTTP request\"}");
                closesocket(client_socket);
                continue;
            }
            body_start += 4; // Skip \r\n\r\n

            // Extract "text" field
            if (extract_json_text(body_start, extracted_text, sizeof(extracted_text)) != 0 ||
                strlen(extracted_text) == 0 ||
                is_whitespace_only(extracted_text)) {
                send_http_response(client_socket, 422, "Unprocessable Entity",
                    "{\"detail\":\"The 'text' field cannot be empty or contain only whitespace.\"}");
                closesocket(client_socket);
                continue;
            }

            printf("[POST /summarize] Received text (%d chars). Calling Google Gemini API...\n", (int)strlen(extracted_text));

            // Call Google Gemini Cloud API
            int gemini_res = gemini_summarize(gemini_api_key, extracted_text, summary_output, sizeof(summary_output));
            if (gemini_res != 0) {
                printf("[Error] Gemini API call failed with code: %d\n", gemini_res);
                send_http_response(client_socket, 502, "Bad Gateway",
                    "{\"detail\":\"Failed to receive valid summary from Google Gemini API.\"}");
                closesocket(client_socket);
                continue;
            }

            // Save to PostgreSQL
            db_save_summary(database_url, extracted_text, summary_output);

            // Construct JSON Response
            char response_json[SUMMARY_BUFFER_SIZE + 256];
            snprintf(response_json, sizeof(response_json), "{\"summary\":\"%s\"}", summary_output);
            send_http_response(client_socket, 200, "OK", response_json);

            printf("[Success] Summary generated and persisted to database successfully!\n\n");
            closesocket(client_socket);
            continue;
        }

        // Root or other paths: 404
        send_http_response(client_socket, 404, "Not Found", "{\"detail\":\"Endpoint not found. Use POST /summarize or GET /health\"}");
        closesocket(client_socket);
    }

    free(recv_buffer);
    closesocket(server_socket);
    WSACleanup();
    return 0;
}
