(function () {
  const puzzleDate = window.DAILY_PUZZLE_DATE;
  const sessionSpec = window.DAILY_SESSION;
  const totalPuzzles = sessionSpec.puzzle_count;
  const board = document.getElementById("daily-board");
  const keyboard = document.getElementById("daily-keyboard");
  const message = document.getElementById("daily-message");
  const shareButton = document.getElementById("share-result");
  const hintButton = document.getElementById("hint-button");
  const hintsLeft = document.getElementById("hints-left");
  const hintPanel = document.getElementById("daily-hint");
  const inputHelp = document.querySelector(".daily-input-help");
  const practiceButton = document.getElementById("practice-run");
  const scoreCount = document.getElementById("score-count");
  const streakCount = document.getElementById("streak-count");
  const puzzleCount = document.getElementById("puzzle-count");
  const puzzleDots = document.getElementById("puzzle-dots");
  const clueLabel = document.getElementById("clue-label");
  const clueText = document.getElementById("clue-text");
  const query = new URLSearchParams(location.search);
  const practiceMode = query.get("practice") === "1";
  const storageKey = `mak3deals-dailydrop-${puzzleDate}-${practiceMode ? "practice" : "official"}`;
  const statsKey = "mak3deals-dailydrop-stats";
  const hintCosts = [150, 300];
  const rows = [];
  const keys = {};
  let currentGuess = "";
  let rowIndex = 0;
  let busy = false;

  if (query.get("reset") === "1") {
    localStorage.removeItem(storageKey);
    query.delete("reset");
    history.replaceState({}, "", `${location.pathname}${query.toString() ? `?${query}` : ""}`);
  }

  function emptyPuzzle() {
    return { guesses: [], hintsUsed: 0, hints: [], complete: false, won: false, answer: null, points: 0 };
  }

  function newSession() {
    return { puzzleIndex: 0, completed: false, puzzles: Array.from({ length: totalPuzzles }, emptyPuzzle) };
  }

  function loadSession() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
      if (!saved || !Array.isArray(saved.puzzles) || saved.puzzles.length !== totalPuzzles) return newSession();
      saved.puzzles = saved.puzzles.map((puzzle) => ({ ...emptyPuzzle(), ...puzzle }));
      saved.puzzleIndex = Math.max(0, Math.min(totalPuzzles - 1, Number(saved.puzzleIndex) || 0));
      return saved;
    } catch (_) {
      return newSession();
    }
  }

  let session = loadSession();

  function persist() {
    localStorage.setItem(storageKey, JSON.stringify(session));
  }

  function currentPuzzle() {
    return session.puzzles[session.puzzleIndex];
  }

  function totalScore() {
    return session.puzzles.reduce((total, puzzle) => total + (puzzle.points || 0), 0);
  }

  function setMessage(text, error) {
    message.textContent = text;
    message.classList.toggle("error", Boolean(error));
  }

  function makeBoard() {
    for (let row = 0; row < 6; row += 1) {
      const cells = [];
      for (let column = 0; column < 5; column += 1) {
        const cell = document.createElement("div");
        cell.className = "daily-cell";
        cell.setAttribute("aria-label", `Row ${row + 1}, letter ${column + 1}`);
        board.appendChild(cell);
        cells.push(cell);
      }
      rows.push(cells);
    }
  }

  function addKey(label, wide) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `key${wide ? " wide" : ""}`;
    button.dataset.baseClass = button.className;
    button.textContent = label;
    button.setAttribute("aria-label", label === "⌫" ? "Backspace" : label);
    button.addEventListener("click", () => handleKey(label));
    keyboard.appendChild(button);
    if (!wide) keys[label] = button;
  }

  function makeKeyboard() {
    ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"].forEach((line, index) => {
      [...line].forEach((letter) => addKey(letter));
      if (index === 1) addKey("SUBMIT", true);
      if (index === 2) addKey("⌫", true);
    });
  }

  function clearBoard() {
    rows.flat().forEach((cell) => { cell.className = "daily-cell"; cell.textContent = ""; });
    keyboard.querySelectorAll("button").forEach((button) => { button.className = button.dataset.baseClass; button.disabled = false; button.dataset.rank = ""; });
  }

  function paintDraft() {
    if (rowIndex > 5) return;
    rows[rowIndex].forEach((cell, index) => {
      cell.textContent = currentGuess[index] || "";
      cell.classList.toggle("filled", Boolean(currentGuess[index]));
    });
    if (currentGuess.length === 5) setMessage("Ready — press Submit to check your guess.");
  }

  function updateKeyColors(guess, pattern) {
    [...guess].forEach((letter, index) => {
      const button = keys[letter];
      if (!button) return;
      const priority = { absent: 1, present: 2, correct: 3 };
      const previous = Number(button.dataset.rank || 0);
      if (priority[pattern[index]] > previous) {
        button.dataset.rank = priority[pattern[index]];
        button.className = `key ${pattern[index]}`;
      }
    });
  }

  function paintResult(guess, pattern, row) {
    [...guess].forEach((letter, index) => {
      const cell = rows[row][index];
      cell.textContent = letter;
      cell.className = `daily-cell ${pattern[index]}`;
    });
    updateKeyColors(guess, pattern);
  }

  function updateProgress() {
    puzzleCount.textContent = session.completed ? "Six puzzles complete" : `Puzzle ${session.puzzleIndex + 1} of ${totalPuzzles}`;
    puzzleDots.replaceChildren(...session.puzzles.map((puzzle, index) => {
      const dot = document.createElement("span");
      dot.className = `puzzle-dot${puzzle.complete ? (puzzle.won ? " won" : " missed") : ""}${!session.completed && index === session.puzzleIndex ? " current" : ""}`;
      dot.textContent = index + 1;
      return dot;
    }));
  }

  function updateScore() {
    scoreCount.textContent = totalScore();
  }

  function updateHintButton() {
    const puzzle = currentPuzzle();
    const remaining = Math.max(0, 2 - puzzle.hintsUsed);
    const nextCost = hintCosts[puzzle.hintsUsed];
    hintsLeft.textContent = nextCost ? `(${remaining} left · −${nextCost} pts)` : "(0 left)";
    hintButton.disabled = session.completed || puzzle.complete || remaining === 0;
  }

  function renderPuzzle() {
    const puzzle = currentPuzzle();
    currentGuess = "";
    rowIndex = puzzle.guesses.length;
    clearBoard();
    updateProgress();
    updateScore();
    const clue = sessionSpec.clues[session.puzzleIndex];
    clueLabel.textContent = `PUZZLE ${session.puzzleIndex + 1} CLUE · ${clue.category}`;
    clueText.textContent = clue.clue;
    puzzle.guesses.forEach((guess, index) => paintResult(guess.guess, guess.pattern, index));
    hintPanel.hidden = !puzzle.hints.length;
    hintPanel.textContent = puzzle.hints.map((hint, index) => `Hint ${index + 1}: ${hint}`).join(" • ");
    updateHintButton();
    inputHelp.textContent = "Build your guess by tapping the letters below or typing on your keyboard. Press Submit or Enter to check it.";
    setMessage(rowIndex ? "Keep going. This puzzle still has guesses available." : "Guess a five-letter word to begin.");
  }

  function updateStreak() {
    const stats = JSON.parse(localStorage.getItem(statsKey) || "{}");
    if (stats.lastDate !== puzzleDate) {
      const then = stats.lastDate ? new Date(`${stats.lastDate}T00:00:00`) : null;
      const now = new Date(`${puzzleDate}T00:00:00`);
      stats.streak = then && Math.round((now - then) / 86400000) === 1 ? (stats.streak || 0) + 1 : 1;
      stats.lastDate = puzzleDate;
      localStorage.setItem(statsKey, JSON.stringify(stats));
    }
    streakCount.textContent = stats.streak || 1;
  }

  function completeSession() {
    session.completed = true;
    persist();
    updateProgress();
    updateScore();
    updateStreak();
    keyboard.querySelectorAll("button").forEach((button) => { button.disabled = true; });
    hintButton.disabled = true;
    shareButton.disabled = false;
    practiceButton.hidden = false;
    practiceButton.textContent = practiceMode ? "Start another practice session" : "Start a practice session";
    inputHelp.textContent = "Six-puzzle session complete. Your final score is ready to share.";
    const solved = session.puzzles.filter((puzzle) => puzzle.won).length;
    setMessage(`Session complete: ${solved} of ${totalPuzzles} solved · ${totalScore()} points.`);
  }

  function advancePuzzle(result) {
    const puzzle = currentPuzzle();
    puzzle.complete = true;
    puzzle.won = result.won;
    puzzle.answer = result.answer;
    puzzle.points = result.points || 0;
    if (session.puzzleIndex === totalPuzzles - 1) {
      completeSession();
      return;
    }
    const completedNumber = session.puzzleIndex + 1;
    session.puzzleIndex += 1;
    persist();
    renderPuzzle();
    setMessage(result.won ? `Puzzle ${completedNumber} solved for ${puzzle.points} points. Puzzle ${session.puzzleIndex + 1} is live.` : `Puzzle ${completedNumber} answer: ${puzzle.answer}. Puzzle ${session.puzzleIndex + 1} is live.`);
  }

  async function submitGuess() {
    if (busy || session.completed || currentGuess.length !== 5) {
      if (currentGuess.length !== 5) setMessage("Use five letters before submitting.", true);
      return;
    }
    busy = true;
    const puzzle = currentPuzzle();
    try {
      const response = await fetch("/api/daily/guess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guess: currentGuess, attempts: rowIndex + 1, puzzle_index: session.puzzleIndex, hints_used: puzzle.hintsUsed })
      });
      const result = await response.json();
      if (!response.ok || !result.ok) { setMessage(result.error || "That guess could not be checked. Please try again.", true); return; }
      paintResult(result.guess, result.pattern, rowIndex);
      puzzle.guesses.push({ guess: result.guess, pattern: result.pattern });
      currentGuess = "";
      if (result.finished) advancePuzzle(result);
      else {
        rowIndex += 1;
        persist();
        setMessage("Keep going. The board is giving you clues.");
      }
    } catch (_) {
      setMessage("We could not check that guess. Your letters are still on the board—press Submit to try again.", true);
    } finally {
      busy = false;
    }
  }

  async function revealHint() {
    const puzzle = currentPuzzle();
    if (session.completed || puzzle.complete || puzzle.hintsUsed >= 2) return;
    try {
      const response = await fetch("/api/daily/hint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hint_index: puzzle.hintsUsed, puzzle_index: session.puzzleIndex })
      });
      const result = await response.json();
      if (!response.ok || !result.ok) { setMessage(result.error || "That hint is unavailable right now.", true); return; }
      puzzle.hintsUsed += 1;
      puzzle.hints.push(result.hint);
      persist();
      hintPanel.hidden = false;
      hintPanel.textContent = puzzle.hints.map((hint, index) => `Hint ${index + 1}: ${hint}`).join(" • ");
      updateHintButton();
    } catch (_) {
      setMessage("We could not load that hint. Please try again.", true);
    }
  }

  function handleKey(key) {
    if (session.completed || busy) return;
    if (key === "ENTER" || key === "SUBMIT") return submitGuess();
    if (key === "⌫") currentGuess = currentGuess.slice(0, -1);
    else if (/^[A-Z]$/.test(key) && currentGuess.length < 5) currentGuess += key;
    paintDraft();
  }

  shareButton.addEventListener("click", async () => {
    const lines = session.puzzles.map((puzzle, index) => `Puzzle ${index + 1}: ${puzzle.won ? `${puzzle.points} pts` : "missed"}`);
    const text = `DealDrop Daily ${puzzleDate} · ${totalScore()} points\n${lines.join("\n")}\nPlay: ${location.origin}/daily`;
    try { await navigator.clipboard.writeText(text); setMessage("Result copied. Send it to somebody who thinks they can beat you."); }
    catch (_) { setMessage(text); }
  });

  hintButton.addEventListener("click", revealHint);
  practiceButton.addEventListener("click", () => { location.href = "/daily?practice=1&reset=1"; });
  document.getElementById("show-how").addEventListener("click", () => {
    const panel = document.getElementById("how-to-play");
    panel.hidden = !panel.hidden;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      if (!event.repeat) handleKey("ENTER");
    }
    else if (event.key === "Backspace") {
      event.preventDefault();
      handleKey("⌫");
    }
    else if (/^[a-zA-Z]$/.test(event.key)) handleKey(event.key.toUpperCase());
  });

  makeBoard();
  makeKeyboard();
  if (session.completed) {
    renderPuzzle();
    completeSession();
  } else {
    const stats = JSON.parse(localStorage.getItem(statsKey) || "{}");
    streakCount.textContent = stats.streak || 0;
    renderPuzzle();
  }
})();
