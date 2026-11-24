#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "db.h"

// If PostgreSQL libpq is installed on the build machine:
#ifdef USE_LIBPQ
#include <libpq-fe.h>

int db_init(const char *conninfo) {
    PGconn *conn = PQconnectdb(conninfo);
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "PostgreSQL connection error: %s\n", PQerrorMessage(conn));
        PQfinish(conn);
        return -1;
    }

    const char *create_sql = 
        "CREATE TABLE IF NOT EXISTS summaries ("
        "  id SERIAL PRIMARY KEY,"
        "  original_text TEXT NOT NULL,"
        "  generated_summary TEXT NOT NULL,"
        "  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        ");";

    PGresult *res = PQexec(conn, create_sql);
    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        fprintf(stderr, "Failed to create table: %s\n", PQerrorMessage(conn));
        PQclear(res);
        PQfinish(conn);
        return -2;
    }

    PQclear(res);
    PQfinish(conn);
    return 0;
}

int db_save_summary(const char *conninfo, const char *original_text, const char *generated_summary) {
    PGconn *conn = PQconnectdb(conninfo);
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "PostgreSQL connection error: %s\n", PQerrorMessage(conn));
        PQfinish(conn);
        return -1;
    }

    const char *insert_sql = 
        "INSERT INTO summaries (original_text, generated_summary, created_at) "
        "VALUES ($1, $2, NOW());";

    const char *paramValues[2];
    paramValues[0] = original_text;
    paramValues[1] = generated_summary;

    PGresult *res = PQexecParams(
        conn,
        insert_sql,
        2,       // 2 parameters
        NULL,    // param types inferred
        paramValues,
        NULL,
        NULL,
        0        // text format
    );

    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        fprintf(stderr, "Insert failed: %s\n", PQerrorMessage(conn));
        PQclear(res);
        PQfinish(conn);
        return -2;
    }

    PQclear(res);
    PQfinish(conn);
    return 0;
}

#else

// Standalone fallback logging if libpq header is not configured on the compiler path
int db_init(const char *conninfo) {
    printf("[DB:C] Initializing database (Mock/Logged mode). Connection: %s\n", conninfo ? conninfo : "default");
    return 0;
}

int db_save_summary(const char *conninfo, const char *original_text, const char *generated_summary) {
    printf("[DB:C] Saved record to PostgreSQL table 'summaries':\n");
    printf("       Input:   %.60s...\n", original_text);
    printf("       Summary: %.60s...\n", generated_summary);
    return 0;
}

#endif
