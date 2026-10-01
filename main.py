"""
Vaarta - a local, offline chatbot. This file is the TERMINAL face of Vaarta.

The whole chatbot is ONE loop:
  1. keep a list called `messages`  (this list IS the chatbot's memory)
  2. add what the user typed to the list
  3. send the ENTIRE list to the model
  4. print the reply, and add it to the list too

The call to the model lives in vaarta.py so the web face (server.py) can
share it. Nothing is sent to the internet: Ollama runs the model on this
laptop and listens on http://localhost:11434.
"""

import sys

import vaarta
from prompts import SYSTEM_PROMPT

# In a normal terminal this does nothing. But if the output is sent to a file
# or another program, Windows Python switches to an old encoding (cp1252) and
# a Hindi word or an emoji in a reply would crash print(). Force UTF-8.
sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")


def main():
    # Fail right away with a readable message if Ollama is not running or the
    # model was never pulled, instead of a long traceback mid-reply.
    problem = vaarta.check_model()
    if problem:
        print(f"Could not start Vaarta: {problem}")
        return

    # The conversation history. The first entry is the system prompt:
    # the user never sees it, but the model reads it on every turn.
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"Vaarta is ready (model: {vaarta.MODEL}). Type 'exit' to quit.\n")

    while True:
        user_text = input("You: ").strip()

        if user_text.lower() in ("exit", "quit", "/bye"):
            print("Vaarta: Bye!")
            break
        if not user_text:
            continue  # ignore empty lines

        messages.append({"role": "user", "content": user_text})

        # Send the WHOLE history and print the reply as it streams in.
        print("Vaarta: ", end="", flush=True)
        reply = ""
        for piece in vaarta.stream_reply(messages):
            print(piece, end="", flush=True)
            reply += piece
        print()

        # Store the reply so the model can see its own earlier answers next turn.
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C, or end-of-input (Ctrl+Z then Enter on Windows, Ctrl+D on
        # macOS/Linux), also exit cleanly.
        print("\nVaarta: Bye!")
