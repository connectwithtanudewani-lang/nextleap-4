"""CLI: python -m scripts.ask "Exit load of Parag Parikh Flexi Cap Fund?" """
import sys

from rag.assistant import Assistant

if __name__ == "__main__":
    a = Assistant()
    questions = sys.argv[1:] or [input("Question: ")]
    for q in questions:
        r = a.ask(q)
        print(f"Q: {q}\n[{r.kind} · {r.mode}]\n{r.as_markdown()}\n")
