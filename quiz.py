"""Quiz Engine + Result Analyzer

Modes:
  1) Ek category
  2) Apni chuni hui multiple categories (random mix ya category-wise)
  3) Saari categories
  4) Random categories (computer choose karta hai)
Har category me 5 questions (2 easy, 2 medium, 1 hard).
Result ke baad donut/pie chart banta hai.
Run:  python quiz.py
"""
import csv
import json
import math
import os
import random
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

QUESTIONS_FILE = "questions.json"
RESULTS_FILE = "results.csv"
CHART_FILE = "result_chart.png"
DIFFICULTIES = ["easy", "medium", "hard"]

# chart colours
CORRECT_COLOR = "#2A9D8F"
WRONG_COLOR = "#E76F51"
BG_COLOR = "#FAFAF7"
TEXT_COLOR = "#264653"
MUTED_COLOR = "#6B7A80"


# ---------------- Question classes ----------------
class Question:
    def __init__(self, category, difficulty, text, answer):
        self.category = category
        self.difficulty = difficulty
        self.text = text
        self.answer = answer

    def display(self):
        raise NotImplementedError

    def is_valid(self, response):
        raise NotImplementedError

    def check_answer(self, response):
        raise NotImplementedError


class MCQ(Question):
    LETTERS = "abcd"

    def __init__(self, category, difficulty, text, answer, options):
        super().__init__(category, difficulty, text, answer)
        self.options = options[:]
        random.shuffle(self.options)  # option shuffling

    def display(self):
        print(f"\n[{self.category} | {self.difficulty}] {self.text}")
        for letter, opt in zip(self.LETTERS, self.options):
            print(f"  {letter}) {opt}")

    def is_valid(self, response):
        return response in self.LETTERS[: len(self.options)]

    def check_answer(self, response):
        return self.options[self.LETTERS.index(response)] == self.answer


class TrueFalse(Question):
    def display(self):
        print(f"\n[{self.category} | {self.difficulty}] {self.text}")
        print("  (t = True, f = False)")

    def is_valid(self, response):
        return response in ("t", "f")

    def check_answer(self, response):
        return (response == "t") == self.answer


# ---------------- Loading ----------------
def load_bank(path=QUESTIONS_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_questions(bank, category):
    questions = []
    for difficulty in DIFFICULTIES:
        for q in bank[category][difficulty]:
            if q["type"] == "mcq":
                questions.append(MCQ(category, difficulty, q["question"], q["answer"], q["options"]))
            else:
                questions.append(TrueFalse(category, difficulty, q["question"], q["answer"]))
    random.shuffle(questions)  # question shuffling
    return questions


# ---------------- Menu ----------------
def ask_int(prompt, low, high):
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and low <= int(raw) <= high:
            return int(raw)
        print(f"{low} se {high} ke beech ka number likho.")


def ask_numbers(prompt, count, minimum):
    while True:
        raw = input(prompt).strip()
        try:
            picks = sorted({int(x) for x in raw.split(",") if x.strip()})
        except ValueError:
            picks = []
        if len(picks) >= minimum and all(1 <= p <= count for p in picks):
            return picks
        print(f"Kam se kam {minimum} valid number likho (1 se {count}), comma se alag karke.")


def choose_setup(categories):
    """Returns (chosen_categories, mixed)."""
    n = len(categories)
    print("\nCategories:")
    for i, c in enumerate(categories, 1):
        print(f"  {i}) {c}")

    print("\nKya chahiye?")
    print("  1) Ek category")
    print("  2) Meri choose ki hui multiple categories")
    print("  3) Saari categories")
    print("  4) Random categories (computer choose karega)")
    mode = ask_int("Option: ", 1, 4)

    if mode == 1:
        pick = ask_int("Category number: ", 1, n)
        return [categories[pick - 1]], False

    if mode == 2:
        picks = ask_numbers("Category numbers (jaise 1,3,4): ", n, 2)
        chosen = [categories[p - 1] for p in picks]
    elif mode == 3:
        chosen = categories[:]
    else:
        how_many = ask_int(f"Kitni random categories? (2-{n}): ", 2, n)
        chosen = random.sample(categories, how_many)
        print("Selected: " + ", ".join(chosen))

    print("\nQuestions ka order?")
    print("  1) Sab categories ke questions random mix")
    print("  2) Category-wise, ek ek karke")
    order = ask_int("Option: ", 1, 2)
    return chosen, order == 1


# ---------------- Quiz ----------------
def ask(question):
    while True:
        response = input("Answer: ").strip().lower()
        if question.is_valid(response):
            return question.check_answer(response)
        print("Invalid input, dobara try karo.")


def run_quiz(bank, chosen, mixed):
    # results[category][difficulty] = [correct, total]
    results = {c: {d: [0, 0] for d in DIFFICULTIES} for c in chosen}
    log = []

    if mixed:
        questions = [q for c in chosen for q in build_questions(bank, c)]
        random.shuffle(questions)
        print(f"\n{'=' * 10} MIXED QUIZ ({len(questions)} questions) {'=' * 10}")
        groups = [questions]
    else:
        groups = [build_questions(bank, c) for c in chosen]

    for group in groups:
        if not mixed:
            print(f"\n{'=' * 10} {group[0].category} {'=' * 10}")
        for q in group:
            q.display()
            correct = ask(q)
            print("Correct!" if correct else f"Wrong. Answer: {q.answer}")
            results[q.category][q.difficulty][1] += 1
            if correct:
                results[q.category][q.difficulty][0] += 1
            log.append((q.category, q.difficulty, q.text, int(correct)))
    return results, log


# ---------------- Saving ----------------
def save_to_csv(player, log, path=RESULTS_FILE):
    new_file = not os.path.exists(path)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp", "player", "category", "difficulty", "question", "correct"])
        for category, difficulty, text, correct in log:
            writer.writerow([stamp, player, category, difficulty, text, correct])


# ---------------- Results ----------------
def category_score(levels):
    correct = sum(v[0] for v in levels.values())
    total = sum(v[1] for v in levels.values())
    return correct, total


def combine_levels(results):
    combined = {d: [0, 0] for d in DIFFICULTIES}
    for levels in results.values():
        for d in DIFFICULTIES:
            combined[d][0] += levels[d][0]
            combined[d][1] += levels[d][1]
    return combined


def print_results(results):
    print(f"\n{'=' * 10} RESULT {'=' * 10}")
    for category, levels in results.items():
        correct, total = category_score(levels)
        print(f"\n{category}: {correct}/{total}")
        for d in DIFFICULTIES:
            c, t = levels[d]
            print(f"   {d:<7}: {c}/{t}")
    if len(results) > 1:
        correct, total = category_score(combine_levels(results))
        print(f"\nOverall: {correct}/{total}")


# ---------------- Chart ----------------
def draw_donut(ax, title, levels):
    correct, total = category_score(levels)
    wrong = total - correct
    pct = round(correct / total * 100) if total else 0

    ax.pie(
        [correct, wrong],
        colors=[CORRECT_COLOR, WRONG_COLOR],
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.36, "edgecolor": BG_COLOR, "linewidth": 3},
    )
    ax.text(0, 0.1, f"{correct}/{total}", ha="center", va="center",
            fontsize=26, fontweight="bold", color=TEXT_COLOR)
    ax.text(0, -0.2, f"{pct}%", ha="center", va="center", fontsize=13, color=MUTED_COLOR)
    ax.set_title(title, fontsize=14, fontweight="bold", color=TEXT_COLOR, pad=10)

    parts = [f"{d.capitalize()} {levels[d][0]}/{levels[d][1]}" for d in DIFFICULTIES]
    ax.text(0, -1.38, "  ·  ".join(parts), ha="center", va="center", fontsize=9, color=MUTED_COLOR)
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.6, 1.25)


def plot_results(results, player):
    panels = []
    if len(results) > 1:
        panels.append(("Overall", combine_levels(results)))
    panels += list(results.items())

    n = len(panels)
    cols = min(n, 3)
    rows = math.ceil(n / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 4.9 * rows), squeeze=False)
    fig.patch.set_facecolor(BG_COLOR)
    flat = axes.flatten()

    for ax, (title, levels) in zip(flat, panels):
        ax.set_facecolor(BG_COLOR)
        draw_donut(ax, title, levels)
    for ax in flat[n:]:
        ax.axis("off")

    fig.suptitle(f"Quiz Result  -  {player}", fontsize=18, fontweight="bold", color=TEXT_COLOR)
    fig.legend(
        handles=[Patch(color=CORRECT_COLOR, label="Correct"), Patch(color=WRONG_COLOR, label="Wrong")],
        loc="lower center", ncol=2, frameon=False, fontsize=11,
    )
    plt.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(CHART_FILE, dpi=200, facecolor=BG_COLOR)
    print(f"\nChart saved: {CHART_FILE}")
    plt.show()


def main():
    player = input("Tumhara naam: ").strip() or "anonymous"
    bank = load_bank()
    chosen, mixed = choose_setup(list(bank.keys()))
    results, log = run_quiz(bank, chosen, mixed)
    save_to_csv(player, log)
    print_results(results)
    plot_results(results, player)


if __name__ == "__main__":
    main()