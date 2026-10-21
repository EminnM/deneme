# Prompt for local Claude Code (Windows)

Paste the block below into Claude Code opened in an empty working folder, not inside the deck folder.

```
I am a contractor reviewing a slide deck. I have a small tool, deckqa, that checks a .pptx against 8 QA criteria
(Alignment, Spacing, Text fit, Lines and arrows, Titles, Readability, Leftover graphics, Consistency).
It runs entirely locally. Please set it up and run it on one deck. Rules first:

RULES
- The deck is confidential. Do not upload it, email it, or send it to any online service. Only run local commands.
- NEVER modify, move, rename or overwrite the original deck. Treat it as read-only. Never run the tool with --fix on it.
- Put all outputs in a new folder next to the deck called "qa-output" (create it). Do not commit anything to git.

STEPS
1. Check Python: run `py -3 --version` (or `python --version`). Need 3.10+. If missing, tell me and stop.
2. Get the tool: `git clone -b claude/new-session-3xlp3i https://github.com/EminnM/deneme.git deckqa`
   then `cd deckqa` and `py -m pip install python-pptx pillow`.
3. Self-test: `py -m unittest discover -s tests`. Tell me whether it passes. If tests fail only because of fonts
   or missing LibreOffice, say so and continue; if something is truly broken, explain and stop.
4. Run the tool on my deck (keep the quotes, the path has spaces):
   py -m deckqa "C:\Users\TKA\Desktop\perpetual-labs\to do\AB1-08478_polished.pptx" --verify "C:\Users\TKA\Desktop\perpetual-labs\to do\qa-output\board.html" --report "C:\Users\TKA\Desktop\perpetual-labs\to do\qa-output\report.md" --notes "C:\Users\TKA\Desktop\perpetual-labs\to do\qa-output\notes.txt" --json "C:\Users\TKA\Desktop\perpetual-labs\to do\qa-output\issues.json"
   The exit code is 1 when issues are found; that is normal, not an error.
   If it says slide images were skipped, that is fine (LibreOffice/poppler not installed). The board still works.
5. Open the board for me in the browser: `start "" "C:\Users\TKA\Desktop\perpetual-labs\to do\qa-output\board.html"`.

THEN REPORT BACK, WITHOUT HIDING ANYTHING
- Per criterion: how many slides pass, how many are flagged, how many do not apply.
- For each flagged item: slide number, criterion, what is wrong, where on the slide, how serious (high/medium/low).
- The fonts / font sizes / colours the deck uses and anything used only once.
- Any font the tool had to approximate (it prints a note) and what that means for trust in the Text fit results.
- Be honest about limits: this checks layout geometry only. It does not check wording, facts, chart data or images.
  Say which flagged items you think could be false alarms (e.g. deliberate design) and why.
- If the tool crashed or looked wrong, show the error and propose the smallest fix to the tool (not to my deck).

I will look at the deck myself and make the final accept / fix / reject call. Do not make that call for me.
```
