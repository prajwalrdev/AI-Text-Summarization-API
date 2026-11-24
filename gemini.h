#ifndef GEMINI_H
#define GEMINI_H

/**
 * Call Google Gemini hosted API over HTTPS using native Windows WinHTTP.
 *
 * @param api_key The Google Gemini API key.
 * @param input_text The user-provided text to summarize.
 * @param output_summary Buffer to store the generated summary.
 * @param max_output_size Maximum size of the output buffer.
 * @return 0 on success, non-zero on failure.
 */
int gemini_summarize(const char *api_key, const char *input_text, char *output_summary, int max_output_size);

#endif // GEMINI_H
