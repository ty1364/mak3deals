(function () {
  const puzzleDate = window.DAILY_PUZZLE_DATE;
  const board = document.getElementById("daily-board");
  const keyboard = document.getElementById("daily-keyboard");
  const message = document.getElementById("daily-message");
  const shareButton = document.getElementById("share-result");
  const streakCount = document.getElementById("streak-count");
  const storageKey = `mak3deals-dailydrop-${puzzleDate}`;
  const statsKey = "mak3deals-dailydrop-stats";
  const rows = [];
  const keys = {};
  let currentGuess = "";
  let rowIndex = 0;
  let finished = false;

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

  function saveState(answer) {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    saved.guesses = saved.guesses || [];
    saved.guesses.push({ guess: currentGuess, pattern: rows[rowIndex].map((cell) => [...cell.classList].find((item) => ["correct", "present", "absent"].includes(item))) });
    if (answer) saved.answer = answer;
    localStorage.setItem(storageKey, JSON.stringify(saved));
  }

  function finish(won, answer) {
    finished = true;
    shareButton.disabled = false;
    const stats = JSON.parse(localStorage.getItem(statsKey) || "{}");
    if (stats.lastDate !== puzzleDate) {
      stats.streak = stats.lastDate && isYesterday(stats.lastDate) ? (stats.streak || 0) + 1 : 1;
      stats.lastDate = puzzleDate;
      localStorage.setItem(statsKey, JSON.stringify(stats));
    }
    streakCount.textContent = stats.streak || 1;
    setMessage(won ? `You found ${answer}. New puzzle tomorrow.` : `The word was ${answer}. New puzzle tomorrow.`);
  }

  function isYesterday(previous) {
    const then = new Date(`${previous}T00:00:00`);
    const now = new Date(`${puzzleDate}T00:00:00`);
    return Math.round((now - then) / 86400000) === 1;
  }

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
    saveState(result.answer);
    currentGuess = "";
    if (result.won || rowIndex === 5) finish(result.won, result.answer || "the daily word");
    else { rowIndex += 1; setMessage("Keep going. The board is giving you clues."); }
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
    streakCount.textContent = stats.streak || 0;
    (saved.guesses || []).forEach((item) => {
      if (rowIndex > 5) return;
      paintResult(item.guess, item.pattern);
      rowIndex += 1;
    });
    if (saved.answer) finish(saved.guesses?.some((item) => item.guess === saved.answer), saved.answer);
    else if (rowIndex) setMessage("Keep going. The board is giving you clues.");
  }

  shareButton.addEventListener("click", async () => {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    const squares = (saved.guesses || []).map((item) => item.pattern.map((state) => state === "correct" ? "🟨" : state === "present" ? "🟩" : "⬜").join("")).join("\n");
    const text = `DealDrop Daily ${puzzleDate}\n${squares}\nPlay: ${location.origin}/daily`;
    try { await navigator.clipboard.writeText(text); setMessage("Result copied. Send it to somebody who thinks they can beat you."); }
    catch (_) { setMessage(text); }
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
