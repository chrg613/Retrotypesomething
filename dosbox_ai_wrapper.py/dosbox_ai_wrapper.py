import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
import google.generativeai as genai

# === Configure Gemini ===
API = "AIzaSyCg6tcwoRQMJV_KJAlYHeGNMfUc1xykQnE"
genai.configure(api_key=API)
generation_config = {
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain"
}
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
)

# === Ask Gemini ===

def ask_gpt(command):
    prompt = f"In DOSBox, what does this command do: {command}?"
    try:
        response = model.generate_content(prompt)
        explanation = response.text  # Gemini's main text output
        return explanation.strip()
    except Exception as e:
        return f"[AI Error] {e}"

# === GUI App ===
class DOSBoxAIApp:
    def __init__(self, root):
        self.root = root
        root.title("DOSBox-X with AI Assistant")
        root.geometry("1000x600")

        # Left pane: DOS terminal
        self.terminal = ScrolledText(root, width=70, height=30, bg="black", fg="lime", insertbackground="white")
        self.terminal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right pane: GPT response
        self.assistant = ScrolledText(root, width=50, height=30, bg="#6CA49D", fg="black")
        self.assistant.pack(side=tk.RIGHT, fill=tk.BOTH)

        # Bottom input field
        self.entry = tk.Entry(root, bg="black", fg="white", insertbackground="white")
        self.entry.pack(fill=tk.X)
        self.entry.bind("<Return>", self.on_enter)

        # Launch DOSBox-X
        self.process = subprocess.Popen(
            ["dosbox-x", "-nogui"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1
        )

        # Start reading DOSBox output
        threading.Thread(target=self.read_output, daemon=True).start()

    def read_output(self):
        for line in iter(self.process.stdout.readline, b''):
            try:
                text = line.decode('utf-8')
                self.terminal.insert(tk.END, text)
                self.terminal.see(tk.END)
            except:
                continue

    def on_enter(self, event):
        cmd = self.entry.get().strip()
        self.entry.delete(0, tk.END)

        if cmd.lower() in ["exit", "quit"]:
            self.process.stdin.write(b"exit\n")
            self.process.stdin.flush()
            self.root.quit()
            return

        self.process.stdin.write((cmd + "\n").encode('utf-8'))
        self.process.stdin.flush()
        self.terminal.insert(tk.END, f"> {cmd}\n")
        self.terminal.see(tk.END)

        # Call Gemini in thread
        threading.Thread(target=self.get_ai_explanation, args=(cmd,), daemon=True).start()

    def get_ai_explanation(self, cmd):
        explanation = ask_gpt(cmd)
        self.assistant.insert(tk.END, f"> {cmd}\n🤖 {explanation}\n\n")
        self.assistant.see(tk.END)

# === Main ===
if __name__ == "__main__":
    root = tk.Tk()
    app = DOSBoxAIApp(root)
    root.mainloop()
