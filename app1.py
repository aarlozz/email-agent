from flask import Flask, request, jsonify, send_from_directory
from agent import run_agent

app = Flask(__name__, static_folder="static")
history = []   # one in-memory conversation (fine for local, single-user use)

@app.get("/")
def index():
    return send_from_directory("static", "index1.html")

@app.post("/chat")
def chat():
    global history
    message = request.json.get("message", "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400
    answer, history = run_agent(message, history)
    return jsonify({"answer": answer})

@app.post("/reset")
def reset():
    global history
    history = []
    return jsonify({"ok": True})

if __name__ == "__main__":
    # 127.0.0.1 = only your own machine can connect. This server can read your mailbox.
    app.run(host="127.0.0.1", port=5000, threaded=False)