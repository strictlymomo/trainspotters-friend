/**
 * BANDCAMP DIGGING TOOL
 * Browse any user's collection with ease
 *
 * How To Use This:
 *   1. Open a URL (e.g. https://bandcamp.com/noemsel)
 *   2. Run this script in the dev tools console
 *   3. Hover over a record to hear it instantaneously
 *   4. Keys
 *     - `z` rewind
 *     -  k` fast-forward
 *     - `c` equivalent to clicking "Buy Now" button
 */

// ======================================================================
// VARIABLES
// ======================================================================
const HOVER_DELAY = 100; // Duration in milliseconds to wait before starting playback on hover
const REWIND_KEY = "z";
const FAST_FORWARD_KEY = "x";
const BUY_NOW_KEY = "c";
const SKIP_AMOUNT = 30;
let nowPlaying = null; // currently playing collection item element
let hoverTimeout = null; // Timer ID reference - used to cancel the hover timeout if mouse leaves early

// ======================================================================
// MAIN SCRIPT
// ======================================================================

void (async () => {
  await loadMoreItems();
  transcendGrid();
  init();
})();

// ======================================================================
// METHODS
// ======================================================================

/**
 * Injects CSS to make the collection grid full-width for a more immersive digging experience
 */
function transcendGrid() {
  const style = document.createElement("style");
  style.textContent = `
    .fan-container .grid { width: 100% !important; }
    @media (min-width: 1232px) {
      ol.collection-grid { width: 100% !important; }
    }
  `;
  document.head.appendChild(style);
}

/**
 * Sets up enhanced functionality to dig through collection items
 */
function init() {
  const items = document.querySelectorAll(".collection-item-container");

  if (items.length === 0) {
    return;
  }

  document.addEventListener("keydown", handleKeydown);

  items.forEach((item) => {
    const artContainer = item.querySelector(".collection-item-art-container");
    if (!artContainer) return;

    artContainer.addEventListener("mouseenter", () => handleMouseEnter(item));
    artContainer.addEventListener("mouseleave", () => handleMouseLeave(item));
  });

  console.log(`✓ Hover preview enabled on ${items.length} items`);
}

/**
 * Handles keyboard shortcuts
 */
function handleKeydown(e) {
  const audio = document.querySelector("audio");
  if (!audio || !nowPlaying) return;

  switch (e.key) {
    case REWIND_KEY:
      e.preventDefault();
      audio.currentTime = Math.max(0, audio.currentTime - SKIP_AMOUNT);
      break;

    case FAST_FORWARD_KEY:
      e.preventDefault();
      audio.currentTime = Math.min(
        audio.duration,
        audio.currentTime + SKIP_AMOUNT
      );
      break;

    case BUY_NOW_KEY:
      e.preventDefault();
      const buyButton = nowPlaying.querySelector(".buy-now a");
      if (buyButton) {
        buyButton.click();
      }
      break;
  }
}

/**
 * Stops playback of the previously playing item if it's different from current
 */
function stopPreviousItem(item) {
  if (nowPlaying && nowPlaying !== item) {
    const prevPlayLink = nowPlaying.querySelector(".track_play_auxiliary");
    if (prevPlayLink && nowPlaying.classList.contains("playing")) {
      prevPlayLink.click();
    }
  }
}

/**
 * Seeks the audio element to the middle of the track
 * Returns true if successful, false if audio not ready
 */
function seekToMiddle() {
  const audio = document.querySelector("audio");
  if (audio && audio.readyState >= 2) {
    const seekTime = audio.duration / 2;
    if (seekTime && !isNaN(seekTime)) {
      audio.currentTime = seekTime;
    }
    return true;
  }
  return false;
}

/**
 * Starts playback of an item and seeks to the middle
 */
function startPlayback(item) {
  stopPreviousItem(item);

  const playLink = item.querySelector(".track_play_auxiliary");
  if (!playLink) return;

  if (!item.classList.contains("playing")) {
    playLink.click();
  }

  nowPlaying = item;

  const checkAudio = setInterval(() => {
    if (seekToMiddle()) {
      clearInterval(checkAudio);
    }
  }, 100);

  setTimeout(() => clearInterval(checkAudio), 3000);
}

/**
 * Initiates playback after a hover delay
 */
function handleMouseEnter(item) {
  hoverTimeout = setTimeout(() => startPlayback(item), HOVER_DELAY);
}

/**
 * Stops playback when mouse leaves and clears any pending hover timeout
 */
function handleMouseLeave(item) {
  if (hoverTimeout) {
    clearTimeout(hoverTimeout);
    hoverTimeout = null;
  }

  if (nowPlaying === item) {
    const playLink = item.querySelector(".track_play_auxiliary");
    if (playLink && item.classList.contains("playing")) {
      playLink.click();
    }
    nowPlaying = null;
  }
}

/**
 * Automatically scrolls and clicks "show more" to load all collection items
 * Stops after reaching maxItems or when no new items load after 3 attempts
 */
async function loadMoreItems(maxItems = 500) {
  let previousCount = 0;
  let noChangeCount = 0;

  console.log("Loading more items...");

  while (true) {
    const currentCount = document.querySelectorAll(
      ".collection-item-container"
    ).length;

    if (currentCount >= maxItems) {
      console.log(`Reached ${currentCount} items (max: ${maxItems})`);
      break;
    }

    if (currentCount === previousCount) {
      noChangeCount++;
      if (noChangeCount >= 3) {
        console.log(`No more items to load (${currentCount} total)`);
        break;
      }
    } else {
      noChangeCount = 0;
    }

    previousCount = currentCount;
    console.log(`Loaded ${currentCount} items so far...`);

    window.scrollTo(0, document.body.scrollHeight);
    await new Promise((resolve) => setTimeout(resolve, 500));

    const showMoreButton = document.querySelector(
      ".expand-container .show-more"
    );
    if (showMoreButton && showMoreButton.offsetParent !== null) {
      console.log("Clicking show more button...");
      showMoreButton.click();
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    await new Promise((resolve) => setTimeout(resolve, 1500));
  }

  window.scrollTo(0, 0);
}
