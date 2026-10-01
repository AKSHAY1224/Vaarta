"""
Vaarta - the WEB face. A tiny Flask server with three jobs:

  GET  /        send the page (web/index.html, plus style.css and app.js)
  GET  /status  tell the page which model is in use and whether Ollama is up
  POST /chat    receive the conversation, add the system prompt, stream the reply

The browser keeps the conversation history and sends ALL of it with every
request, exactly like the `messages` list in main.py. So this server stores
nothing between requests (it is "stateless"), and refreshing the page starts
a fresh conversation.

It listens only on 127.0.0.1, so nothing else on your network can reach it,
and nothing here touches the internet.
"""

import socket

from flask import Flask, Response, jsonify, request, send_from_directory

import vaarta
from prompts import SYSTEM_PROMPT

# static_url_path="" means web/style.css is served at /style.css, and so on.
# It also means any other GET that matches no route below is looked up as a
# file in web/, so typing /chat in the address bar says "Not Found" (GET)
# rather than "Method Not Allowed". /chat only answers POST.
app = Flask(__name__, static_folder="web", static_url_path="")


@app.get("/")
def page():
    return send_from_directory("web", "index.html")


@app.get("/status")
def status():
    problem = vaarta.check_model()
    return jsonify({"model": vaarta.MODEL, "ok": problem is None, "problem": problem})


@app.post("/chat")
def chat():
    body = request.get_json(silent=True)
    history = body.get("messages") if isinstance(body, dict) else None

    # Accept only the shape main.py uses: a list of user/assistant turns.
    # The system prompt is added here, so the browser can never change it.
    valid = isinstance(history, list) and all(
        isinstance(m, dict)
        and m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
        for m in history
    )
    if not valid:
        return jsonify({"error": "expected {'messages': [{'role': 'user' or 'assistant', 'content': '...'}, ...]}"}), 400

    # Ollama can be closed, or the model removed, while the page is open. The
    # same cheap check as at startup lets the page show the real reason.
    problem = vaarta.check_model()
    if problem:
        return jsonify({"error": problem}), 503

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # Returning a generator makes Flask send each piece the moment the model
    # produces it, so the browser can show the reply as it is being written.
    # (Flask adds "charset=utf-8" to text/plain by itself.)
    return Response(vaarta.stream_reply(messages), mimetype="text/plain")


if __name__ == "__main__":
    problem = vaarta.check_model()

    # On Windows, two copies of this server can share port 5000 without any
    # error, and the browser then keeps talking to the OLD copy. So refuse to
    # start if something already answers on the port.
    with socket.socket() as probe:
        already_running = probe.connect_ex(("127.0.0.1", 5000)) == 0

    if problem:
        print(f"Could not start Vaarta: {problem}")
    elif already_running:
        print("Vaarta is already running at http://127.0.0.1:5000. Press Ctrl+C in that terminal first.")
    else:
        print(f"Vaarta web UI (model: {vaarta.MODEL}). Open http://127.0.0.1:5000 in your browser. Ctrl+C to stop.")
        # Flask prints a red "development server" warning here. That is expected
        # and fine: this is a private tool for one person on 127.0.0.1, not a website.
        app.run(host="127.0.0.1", port=5000, debug=False)
