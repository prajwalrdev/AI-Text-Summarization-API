"""
Interactive Terminal Client for AI Text Summarizer.
Allows you to enter your own custom text and see the generated summary immediately.
"""

import sys
import requests

API_URL = "http://127.0.0.1:8000/summarize"


def main():
    print("\n" + "=" * 60)
    print("        AI TEXT SUMMARIZER - INTERACTIVE CLIENT")
    print("=" * 60)
    print("Type or paste any text to summarize. (Type 'exit' to quit)\n")

    while True:
        try:
            user_text = input("\n👉 Enter your text:\n> ").strip()

            if not user_text:
                print("⚠️  Input cannot be empty. Please type some text.")
                continue

            if user_text.lower() in ("exit", "quit", "q"):
                print("\nGoodbye!\n")
                break

            print("\n⏳ Sending to Gemini AI & saving to PostgreSQL database...")

            response = requests.post(
                API_URL,
                json={"text": user_text},
                headers={"Content-Type": "application/json"},
                timeout=45,
            )

            if response.status_code == 200:
                result = response.json()
                print("\n" + "-" * 60)
                print("✨ AI GENERATED SUMMARY:")
                print("-" * 60)
                print(result["summary"])
                print("-" * 60)
                print("✅ [Saved to PostgreSQL Database]")
            else:
                error_detail = response.json().get("detail", response.text)
                print(f"\n❌ Error ({response.status_code}): {error_detail}")

        except requests.exceptions.ConnectionError:
            print("\n❌ Error: Could not connect to API server at http://127.0.0.1:8000")
            print("Please make sure your server is running in another terminal using:")
            print("python run.py\n")
            break
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
