import os
from flask import Flask, request, jsonify, session, redirect, render_template
import threading, builtins, time, uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-to-a-secret")

# Thread-safe file writing
save_lock = threading.Lock()
def save_progress(team, players, uid, points, stage):
    with save_lock:
        with open("scores.txt", "a", encoding="utf-8") as f:
            f.write(f"ID: {uid}\n")
            f.write(f"Team name: {team}\n")
            f.write(f"Players: {players}\n")
            f.write(f"Stage: {stage}\n")
            f.write(f"Points: {points}\n")
            f.write("-" * 30 + "\n")  # optional separator between entries

# --- UID Generator ---
def make_uid(team, players):
    initials = "".join([p.strip()[0].upper() for p in players.split(",") if p.strip()])
    short_code = str(uuid.uuid4())[:6].upper()
    return f"{team.upper()}-{initials}-{short_code}"

# --- WebIO class ---
class WebIO:
    def __init__(self):
        self.output_lines = []
        self.input_buffer = []
        self.cond = threading.Condition()
    def web_print(self, *args):
        text = " ".join(map(str, args))
        with self.cond:
            self.output_lines.append(text)
            self.cond.notify_all()
    def web_input(self, prompt=""):
        if prompt:
            self.web_print(prompt)
        with self.cond:
            while not self.input_buffer:
                self.cond.wait()
            return self.input_buffer.pop(0)
    def send_input(self, s):
        with self.cond:
            self.input_buffer.append(s)
            self.cond.notify_all()
    def get_output_and_clear(self):
        with self.cond:
            out = "\n".join(self.output_lines)
            self.output_lines = []
            return out

# --- GameRunner ---
class GameRunner:
    def __init__(self, team, players, uid):
        self.webio = WebIO()
        self.finished = False
        self.finished_time = None
        self.start_time = time.time()
        self.thread = threading.Thread(
            target=self._run_main, args=(team, players, uid), daemon=True
        )
        self.thread.start()

    def _run_main(self, team, players, uid):
        orig_input = builtins.input
        orig_print = builtins.print
        builtins.input = self.webio.web_input
        builtins.print = self.webio.web_print
        try:
            main(team, players, uid)
            self.finished = True
            self.finished_time = time.time()
        except Exception as e:
            self.webio.web_print("Exception in game:", e)
            self.finished = True
            self.finished_time = time.time()
        finally:
            builtins.input = orig_input
            builtins.print = orig_print
            with self.webio.cond:
                self.webio.cond.notify_all()

    def send_input(self, text):
        self.webio.send_input(text)
    def get_output(self, wait_seconds=2.0):
        end = time.time() + wait_seconds
        out = self.webio.get_output_and_clear()
        while out.strip() == "" and not self.finished and time.time() < end:
            time.sleep(0.03)
            out = self.webio.get_output_and_clear()
        return out

# --- Cleanup old runners ---
runners = {}
def cleanup_runners(max_age_seconds=300):
    now = time.time()
    for sid, runner in list(runners.items()):
        if getattr(runner, "finished", False):
            ft = getattr(runner, "finished_time", 0) or 0
            if now - ft > max_age_seconds:
                try:
                    del runners[sid]
                except KeyError:
                    pass

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/quest")
def quest():
    return render_template("quest.html")

@app.route("/start_quest", methods=["POST"])
def start_quest():
    team = (request.form.get("team") or "").strip()
    players = (request.form.get("players") or "").strip()
    if not team or not players:
        return "Team and players are required", 400
    if "uid" not in session:
        session["uid"] = make_uid(team, players)
    session["team"] = team
    session["players"] = players
    return redirect("/quest")

@app.route("/play", methods=["POST"])
def play():
    cleanup_runners()
    data = request.get_json() or {}
    action = data.get("action", "")
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    sid = session["sid"]
    if action == "start":
        if sid not in runners or runners[sid].finished:
            team = session.get("team")
            players = session.get("players")
            uid = session.get("uid")
            runners[sid] = GameRunner(team, players, uid)
            out = runners[sid].get_output(wait_seconds=2.0)
            return jsonify({"output": out, "finished": runners[sid].finished})
        else:
            out = runners[sid].get_output(wait_seconds=0.5)
            return jsonify({"output": out, "finished": runners[sid].finished})
    if action == "answer":
        answer = data.get("answer", "")
        if sid not in runners:
            return jsonify({"output": "No game in progress. Click Start first.", "finished": True})
        runner = runners[sid]
        runner.send_input(answer)
        out = runner.get_output(wait_seconds=2.0)
        return jsonify({"output": out, "finished": runner.finished})
    return jsonify({"output": "Unknown action", "finished": False})

# --- Paste your exact game code here (main, qn1, qn2, qn3) unchanged ---
def qn1(team, players, uid): 
    points = 100
    answer = "EETOAIN"
    print("Welcome to SUBQUEST 1! ")
    print("You have 100 points for this question.")
    print("DECODE!! FI FI HD GI FE GC GH")
    print("You can choose to decode from these 5 methods: (Only 2 methods used one after the other can actually solve it HEHEHE)\n"
          "1. Ascii <-> Alphabet/Number\n"
          "2. Ceasar Cipher\n"
          "3. Atbash Cipher\n"
          "4. Letter-to-Number\n"
          "5. PURE INTUITION!!\n")
    while points > 0:
        user_input = input("Enter the word: ").strip().upper()
        if len(user_input) != len(answer):
            print(f"Please ensure the correct number of letters in your answer ({len(answer)} letters).\n")
            print(f"Points remaining: {points}\n")
            continue
        if user_input == answer:
            print(f"Correct! You still have {points} points.\n")
            break
        else:
            points -= 2
            print(f"Incorrect! Points remaining: {points}\n")
            if points <= 80:
                print("Hint: Try using the 'Letter-to-Number' decoding method!\n")
            if points <= 60:
                print("Hint: Try using the 'Ascii <-> Alphabet/Number' decoding method")
    if points == 0:
        print("You have no points left! DISAPPOINTMENT!!\n")

    save_progress(team, players, uid, points, 1)
    return points

def qn2(team, players, uid):
    points = 100
    print("Welcome to the SUBQUEST 2!")
    print("You start with 100 points.")
    print("For every wrong answer (correct length), you lose 2 point (points never go below 0).")
    print("Enter the 7-letter answer, combining the first letters of each clue in order.\n")

    # Clues dictionary (for reference if needed)
    clues = {
        "L": "an abstract data type representing an ordered collection of elements",
        "C": "Set of instructions that a computer follows to perform a task",
        "R": "A hardware component that temporarily stores data and programs the computer is actively using, allowing the CPU to access them quickly",
        "S": "a linear data structure which follows LIFO principle for inserting and deleting elements",
        "P": "reference that stores the address of data, allowing indirect access to its value",
        "E": "A 32 bit micro controller",
        "S2": "a device that detects and responds to changes in its environment by converting the physical change into an electrical signal"
    }

    full_answers = {"L":"LIST","C":"CODE","R":"RAM","S":"STACK","P":"POINTER","E":"ESP32","S2":"SENSOR"}

    # Final order of letters
    order = ["L","C","R","S","P","E","S2"]

    while points > 0:
        print("Clues:")
        print("""        "1.": "an abstract data type representing an ordered collection of elements",
        "2.": "Set of instructions that a computer follows to perform a task",
        "3.": "A hardware component that temporarily stores data and programs the computer is actively using, allowing the CPU to access them quickly",
        "4.": "a linear data structure which follows LIFO principle for inserting and deleting elements",
        "5.": "reference that stores the address of data, allowing indirect access to its value",
        "6.": "A 32 bit micro controller",
        "7.": "a device that detects and responds to changes in its environment by converting the physical change into an electrical signal""")

        user_input = input("Enter the 7-letter word: ").strip().upper()

        if len(user_input) != 7:
            print(f"Please ensure the correct number of letters in your answer (7 letters).\n")
            continue

        expected = "LCRSPES"
        if user_input == expected:
            print(f"Correct! You still have {points} points.\n")
            break
        else:
            points -= 2
            print(f"Incorrect! Points remaining: {points}\n")

    if points == 0:
        print("You have no points left!\n DISAPPOINTMENT")
    
    save_progress(team, players, uid, points, 2)

    return points

def qn3(points, team, players, uid):
    points = int(points)
    answer = "ELECTROSAPIENS"
    print("Welcome to SUBQUEST 3 !!\n")
    print("word1 = ANSWER TO SUBQUEST 1\nword2 = ANSWER TO SUBQUEST 2\nSolve the anagram of both words and enter your answer\n")
    chances = 5
    while chances > 0:
        user_input = input(f"Enter the output word (chances left: {chances}): ").strip().upper()
        if len(user_input) != len(answer):
            print(f"Please ensure the correct number of letters in your answer ({len(answer)} letters).\n")
            continue
        if user_input == answer:
            print(f"Correct! You still have {points} points.\n")
            return points
        else:
            chances -= 1
            points -= 10
            if points < 0: points = 0
            print(f"Incorrect! -10 points. Points remaining: {points}\n")
    points -= 50
    if points < 0: points = 0
    print(f"Out of chances! The correct answer was: {answer}")
    print(f"-50 penalty. Points remaining: {points}\n")

    save_progress(team, players, uid, points, 3)
    return points

def main(team, players, uid):
    round1 = qn1(team, players, uid)
    round2 = qn2(team, players, uid)
    round3 = qn3(round1 + round2, team, players, uid)
    total_points = round1 + round2 + round3
    print("Total points = " + str(total_points))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)       # Bind to all interfaces
