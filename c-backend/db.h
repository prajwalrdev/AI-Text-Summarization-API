#ifndef DB_H
#define DB_H

/**
 * Initialize database table 'summaries' in PostgreSQL if it doesn't already exist.
 *
 * @param conninfo PostgreSQL connection string.
 * @return 0 on success, non-zero on failure.
 */
int db_init(const char *conninfo);

/**
 * Save original text and generated summary to the 'summaries' table in PostgreSQL.
 *
 * @param conninfo PostgreSQL connection string.
 * @param original_text The source text submitted by user.
 * @param generated_summary The AI-generated summary.
 * @return 0 on success, non-zero on failure.
 */
int db_save_summary(const char *conninfo, const char *original_text, const char *generated_summary);

#endif // DB_H
