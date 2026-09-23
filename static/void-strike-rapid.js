(() => {
  // Power-ups are stationary while the player core is stationary, so they must be collectible by shooting.
  // Rapid Fire is truly automatic once activated: aim with the mouse and let the weapon spray on its own.
  let autoShotAt = 0;

  function powerUpHitLoop(now) {
    if (typeof running !== 'undefined' && running) {
      // Shoot a pickup to collect it.
      if (typeof bullets !== 'undefined' && typeof pickups !== 'undefined') {
        for (const b of bullets) {
          if (b.life <= 0) continue;
          for (const p of pickups) {
            if (p.collected) continue;
            const hitRadius = (b.r || 5) + (p.r || 16) + 5;
            if (Math.hypot(b.x - p.x, b.y - p.y) <= hitRadius) {
              b.life = 0;
              p.collected = true;
              collectPickup(p);
              break;
            }
          }
        }
      }

      // Truly automatic Rapid Fire: no need to hold the mouse button.
      if (typeof rapidFire !== 'undefined' && rapidFire.active) {
        // Prevent the original hold-click rapid-fire loop from doubling our shots.
        if (typeof mouse !== 'undefined') mouse.down = false;
        const intervalMs = Math.max(45, (rapidFire.interval || 0.07) * 1000);
        if (now - autoShotAt >= intervalMs) {
          fire();
          autoShotAt = now;
        }
      } else {
        autoShotAt = now;
      }
    }
    requestAnimationFrame(powerUpHitLoop);
  }

  requestAnimationFrame(powerUpHitLoop);
})();


