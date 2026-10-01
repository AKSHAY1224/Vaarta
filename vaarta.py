"""
The brain of Vaarta, shared by the terminal (main.py) and the web UI (server.py).

Three things live here: which model to use, a cheap check that Ollama is
running and has that model, and the one call that sends the conversation to
the model. Keeping that in one place means Phase 3 (switching models) is a
one-word change for both faces of Vaarta.
"""

import ollama

# Phase 3 result on a Ryzen 5 5600H with 16 GB RAM, CPU only: llama3.2 (3B)
# ran at about 18 tokens/s and followed the prompt's rules; mistral (7B) ran at
# about 8 tokens/s, answered at three times the length, and ignored "code only".
# So the small model stays the default. Try "mistral" or "qwen2.5:7b" here
# after "ollama pull <name>" to see the difference yourself.
MODEL = "mistral"


def check_model():
    """Return None if Ollama is running and MODEL is pulled, otherwise a
    readable message. ollama.show() only reads the model's details, it does
    not load the model, so this is cheap."""
    try:
        ollama.show(MODEL)
    except (ConnectionError, ollama.ResponseError) as e:
        return f"{e}\nIs Ollama running? Did you run: ollama pull {MODEL}"
    return None


def stream_reply(messages):
    """Send the WHOLE conversation to the model and yield the reply piece by
    piece (one token at a time: a word or part of a word).

    `messages` is the full history, system prompt first. The model remembers
    nothing between calls; it only knows what is inside this list right now.
    Under the hood this is one HTTP POST to http://localhost:11434/api/chat.
    (By default Ollama feeds the model only the last ~4096 tokens of the list,
    so in a very long chat the oldest turns are silently dropped.)
    """
    for chunk in ollama.chat(model=MODEL, messages=messages, stream=True):
        yield chunk["message"]["content"]
