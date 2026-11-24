#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <winhttp.h>
#include "gemini.h"

#pragma comment(lib, "winhttp.lib")

// Helper to escape JSON characters in C
static char *json_escape_string(const char *input) {
    size_t len = strlen(input);
    char *escaped = (char *)malloc(len * 2 + 1);
    if (!escaped) return NULL;

    size_t j = 0;
    for (size_t i = 0; i < len; i++) {
        switch (input[i]) {
            case '"':  escaped[j++] = '\\'; escaped[j++] = '"'; break;
            case '\\': escaped[j++] = '\\'; escaped[j++] = '\\'; break;
            case '\b': escaped[j++] = '\\'; escaped[j++] = 'b'; break;
            case '\f': escaped[j++] = '\\'; escaped[j++] = 'f'; break;
            case '\n': escaped[j++] = '\\'; escaped[j++] = 'n'; break;
            case '\r': escaped[j++] = '\\'; escaped[j++] = 'r'; break;
            case '\t': escaped[j++] = '\\'; escaped[j++] = 't'; break;
            default:   escaped[j++] = input[i]; break;
        }
    }
    escaped[j] = '\0';
    return escaped;
}

// Simple JSON response parser to extract text from {"candidates":[{"content":{"parts":[{"text":"..."}]}}]}
static int extract_summary_from_json(const char *json_str, char *output, int max_size) {
    const char *text_key = "\"text\": \"";
    const char *pos = strstr(json_str, text_key);
    if (!pos) {
        // Fallback check for unspaced key
        text_key = "\"text\":\"";
        pos = strstr(json_str, text_key);
        if (!pos) return -1;
    }

    pos += strlen(text_key);
    int idx = 0;
    while (*pos && idx < max_size - 1) {
        if (*pos == '\\' && *(pos + 1) == '"') {
            output[idx++] = '"';
            pos += 2;
        } else if (*pos == '\\' && *(pos + 1) == 'n') {
            output[idx++] = '\n';
            pos += 2;
        } else if (*pos == '"') {
            break; // End of string
        } else {
            output[idx++] = *pos++;
        }
    }
    output[idx] = '\0';
    return 0;
}

int gemini_summarize(const char *api_key, const char *input_text, char *output_summary, int max_output_size) {
    if (!api_key || !input_text || !output_summary || max_output_size <= 0) {
        return -1;
    }

    // 1. Prepare JSON Payload
    char *escaped_input = json_escape_string(input_text);
    if (!escaped_input) return -1;

    size_t payload_size = strlen(escaped_input) + 512;
    char *payload = (char *)malloc(payload_size);
    if (!payload) {
        free(escaped_input);
        return -1;
    }

    snprintf(payload, payload_size,
        "{\"contents\":[{\"parts\":[{\"text\":\"Please summarize concisely: %s\"}]}],\"generationConfig\":{\"temperature\":0.2,\"maxOutputTokens\":1024}}",
        escaped_input
    );
    free(escaped_input);

    // 2. Initialize WinHTTP
    HINTERNET hSession = WinHttpOpen(
        L"AI-Text-Summarizer-C/1.0",
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS,
        0
    );
    if (!hSession) {
        free(payload);
        return -2;
    }

    HINTERNET hConnect = WinHttpConnect(
        hSession,
        L"generativelanguage.googleapis.com",
        INTERNET_DEFAULT_HTTPS_PORT,
        0
    );
    if (!hConnect) {
        WinHttpCloseHandle(hSession);
        free(payload);
        return -3;
    }

    // Construct path: /v1beta/models/gemini-3.1-flash-lite:generateContent
    HINTERNET hRequest = WinHttpOpenRequest(
        hConnect,
        L"POST",
        L"/v1beta/models/gemini-3.1-flash-lite:generateContent",
        NULL,
        WINHTTP_NO_REFERRER,
        WINHTTP_DEFAULT_ACCEPT_TYPES,
        WINHTTP_FLAG_SECURE
    );
    if (!hRequest) {
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        free(payload);
        return -4;
    }

    // 3. Set Headers (Content-Type and x-goog-api-key)
    wchar_t w_headers[512];
    wchar_t w_api_key[256];
    MultiByteToWideChar(CP_UTF8, 0, api_key, -1, w_api_key, 256);
    swprintf(w_headers, 512, L"Content-Type: application/json\r\nx-goog-api-key: %s\r\n", w_api_key);

    BOOL bResults = WinHttpSendRequest(
        hRequest,
        w_headers,
        (DWORD)-1L,
        payload,
        (DWORD)strlen(payload),
        (DWORD)strlen(payload),
        0
    );
    free(payload);

    if (bResults) {
        bResults = WinHttpReceiveResponse(hRequest, NULL);
    }

    if (!bResults) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return -5;
    }

    // 4. Read Response Body
    DWORD dwSize = 0;
    DWORD dwDownloaded = 0;
    size_t response_capacity = 8192;
    size_t response_len = 0;
    char *response_body = (char *)malloc(response_capacity);
    if (!response_body) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return -6;
    }
    response_body[0] = '\0';

    do {
        dwSize = 0;
        if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
        if (dwSize == 0) break;

        if (response_len + dwSize + 1 > response_capacity) {
            response_capacity = (response_len + dwSize + 1) * 2;
            char *new_buf = (char *)realloc(response_body, response_capacity);
            if (!new_buf) break;
            response_body = new_buf;
        }

        if (WinHttpReadData(hRequest, response_body + response_len, dwSize, &dwDownloaded)) {
            response_len += dwDownloaded;
            response_body[response_len] = '\0';
        }
    } while (dwSize > 0);

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);

    // 5. Extract Summary from JSON
    int parse_res = extract_summary_from_json(response_body, output_summary, max_output_size);
    free(response_body);

    return parse_res;
}
