(function () {
  const puzzleDate = window.DAILY_PUZZLE_DATE;
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
  const query = new URLSearchParams(location.search);
  const practiceMode = query.get("practice") === "1";
  const storageKey = `mak3deals-dailydrop-${puzzleDate}-${practiceMode ? "practice" : "official"}`;
  if (query.get("reset") === "1") localStorage.removeItem(storageKey);
  const statsKey = "mak3deals-dailydrop-stats";
  const rows = [];
  const keys = {};
  let currentGuess = "";
  let rowIndex = 0;
  let finished = false;
  let hintsUsed = 0;
  let solvedAt = 0;
  let currentScore = 1000;
  const hintCosts = [150, 300];

  function potentialScore(attempts) {
    return Math.max(0, 1000 - Math.max(0, attempts - 1) * 100 - hintCosts.slice(0, hintsUsed).reduce((total, cost) => total + cost, 0));
  }

  function updateScore(attempts, won, final) {
    currentScore = won ? potentialScore(attempts) : final ? 0 : potentialScore(attempts);
    scoreCount.textContent = currentScore;
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

  function makeKeyboard() {
    ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"].forEach((line, index) => {
      [...line].forEach((letter) => addKey(letter));
      if (index === 1) addKey("ENTER", true);
      if (index === 2) addKey("⌫", true);
    });
  }

  function addKey(label, wide) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `key${wide ? " wide" : ""}`;
    button.textContent = label;
    button.setAttribute("aria-label", label === "⌫" ? "Backspace" : label);
    button.addEventListener("click", () => handleKey(label));
    keyboard.appendChild(button);
    if (!wide) keys[label] = button;
  }

  function paintDraft() {
    rows[rowIndex].forEach((cell, index) => {
      cell.textContent = currentGuess[index] || "";
      cell.classList.toggle("filled", Boolean(currentGuess[index]));
    });
  }

  function setMessage(text, error) {
    message.textContent = text;
    message.classList.toggle("error", Boolean(error));
  }

  function updateKeyColors(guess, pattern) {
    [...guess].forEach((letter, index) => {
      const button = keys[letter];
      if (!button) return;
      const priority = { absent: 1, present: 2, correct: 3 };
      const previous = button.dataset.rank ? Number(button.dataset.rank) : 0;
      if (priority[pattern[index]] > previous) {
        button.dataset.rank = priority[pattern[index]];
        button.className = `key ${pattern[index]}`;
      }
    });
  }

  function paintResult(guess, pattern) {
    [...guess].forEach((letter, index) => {
      const cell = rows[rowIndex][index];
      cell.textContent = letter;
      cell.className = `daily-cell ${pattern[index]}`;
    });
    updateKeyColors(guess, pattern);
  }

  function saveState(answer, solved) {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    saved.guesses = saved.guesses || [];
    saved.guesses.push({ guess: currentGuess, pattern: rows[rowIndex].map((cell) => [...cell.classList].find((item) => ["correct", "present", "absent"].includes(item))) });
    if (solved && !saved.solvedAt) saved.solvedAt = saved.guesses.length;
    if (answer) saved.answer = answer;
    localStorage.setItem(storageKey, JSON.stringify(saved));
    return saved;
  }

  function finish(won, answer) {
    finished = true;
    shareButton.disabled = false;
    hintButton.disabled = true;
    keyboard.querySelectorAll("button").forEach((button) => { button.disabled = true; });
    practiceButton.hidden = false;
    practiceButton.textContent = practiceMode ? "Start another practice run" : "Practice this puzzle again";
    inputHelp.textContent = practiceMode ? "Practice run complete. Start another practice run whenever you want." : "Today's official run is complete. A new puzzle opens tomorrow, or you can practice this puzzle again.";
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    updateScore(saved.solvedAt || (saved.guesses || []).length, won, true);
    const stats = JSON.parse(localStorage.getItem(statsKey) || "{}");
    if (stats.lastDate !== puzzleDate) {
      stats.streak = stats.lastDate && isYesterday(stats.lastDate) ? (stats.streak || 0) + 1 : 1;
      stats.lastDate = puzzleDate;
      localStorage.setItem(statsKey, JSON.stringify(stats));
    }
    streakCount.textContent = stats.streak || 1;
    setMessage(practiceMode ? `Practice complete: ${won ? `you found ${answer}` : `the word was ${answer}`}. Score: ${currentScore}.` : won ? `You found ${answer} and scored ${currentScore} points. New puzzle tomorrow.` : `The word was ${answer}. Final score: ${currentScore}. New puzzle tomorrow.`);
  }

  function isYesterday(previous) {
    const then = new Date(`${previous}T00:00:00`);
    const now = new Date(`${puzzleDate}T00:00:00`);
    return Math.round((now - then) / 86400000) === 1;
  }

  function updateHintButton() {
    const remaining = Math.max(0, 2 - hintsUsed);
    const nextCost = hintCosts[hintsUsed];
    hintsLeft.textContent = nextCost ? `(${remaining} left · −${nextCost} pts)` : "(0 left)";
    hintButton.disabled = finished || solvedAt || remaining === 0;
  }

  hintButton.addEventListener("click", async () => {
    if (finished || solvedAt || hintsUsed >= 2) return;
    const response = await fetch("/api/daily/hint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hint_index: hintsUsed })
    });
    const result = await response.json();
    if (!result.ok) { setMessage(result.error, true); return; }
    hintsUsed += 1;
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    saved.hintsUsed = hintsUsed;
    saved.hints = saved.hints || [];
    saved.hints.push(result.hint);
    localStorage.setItem(storageKey, JSON.stringify(saved));
    hintPanel.hidden = false;
    hintPanel.textContent = saved.hints.map((hint, index) => `Hint ${index + 1}: ${hint}`).join(" • ");
    updateScore((saved.guesses || []).length, false);
    updateHintButton();
  });

  async function submitGuess() {
    if (finished || currentGuess.length !== 5) {
      if (currentGuess.length !== 5) setMessage("Use five letters before submitting.", true);
      return;
    }
    const guess = currentGuess;
    const response = await fetch("/api/daily/guess", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ guess, attempts: rowIndex + 1 }) });
    const result = await response.json();
    if (!result.ok) { setMessage(result.error, true); return; }
    paintResult(result.guess, result.pattern);
    const saved = saveState(result.answer, result.won);
    solvedAt = saved.solvedAt || 0;
    updateScore(solvedAt || rowIndex + 1, Boolean(solvedAt));
    updateHintButton();
    currentGuess = "";
    if (rowIndex === 5) finish(Boolean(saved.solvedAt), result.answer || "the daily word");
    else {
      rowIndex += 1;
      setMessage(result.won ? `Correct—${currentScore} points locked. Finish all six turns.` : "Keep going. The board is giving you clues.");
    }
  }

  function handleKey(key) {
    if (finished) return;
    if (key === "ENTER") return submitGuess();
    if (key === "⌫") currentGuess = currentGuess.slice(0, -1);
    else if (/^[A-Z]$/.test(key) && currentGuess.length < 5) currentGuess += key;
    paintDraft();
  }

  function restore() {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    const stats = JSON.parse(localStorage.getItem(statsKey) || "{}");
    hintsUsed = saved.hintsUsed || 0;
    solvedAt = saved.solvedAt || 0;
    updateHintButton();
    if (saved.hints && saved.hints.length) {
      hintPanel.hidden = false;
      hintPanel.textContent = saved.hints.map((hint, index) => `Hint ${index + 1}: ${hint}`).join(" • ");
    }
    streakCount.textContent = stats.streak || 0;
    updateScore(saved.solvedAt || (saved.guesses || []).length, Boolean(saved.solvedAt), Boolean(saved.answer));
    (saved.guesses || []).forEach((item) => {
      if (rowIndex > 5) return;
      paintResult(item.guess, item.pattern);
      rowIndex += 1;
    });
    if (saved.answer) finish(Boolean(saved.solvedAt), saved.answer);
    else if (rowIndex) setMessage("Keep going. The board is giving you clues.");
  }

  shareButton.addEventListener("click", async () => {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    const squares = (saved.guesses || []).map((item) => item.pattern.map((state) => state === "correct" ? "🟨" : state === "present" ? "🟩" : "⬜").join("")).join("\n");
    const text = `DealDrop Daily ${puzzleDate} · ${currentScore} points\n${squares}\nPlay: ${location.origin}/daily`;
    try { await navigator.clipboard.writeText(text); setMessage("Result copied. Send it to somebody who thinks they can beat you."); }
    catch (_) { setMessage(text); }
  });

  practiceButton.addEventListener("click", () => {
    if (practiceMode) localStorage.removeItem(storageKey);
    location.href = "/daily?practice=1&v=daily-practice";
  });

  document.getElementById("show-how").addEventListener("click", () => {
    const panel = document.getElementById("how-to-play");
    panel.hidden = !panel.hidden;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Enter") handleKey("ENTER");
    else if (event.key === "Backspace") handleKey("⌫");
    else if (/^[a-zA-Z]$/.test(event.key)) handleKey(event.key.toUpperCase());
  });

  makeBoard(); makeKeyboard(); restore();
})();
