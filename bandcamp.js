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
 *     - `x` fast-forward
 *     - `c` skip to next item
 *     - `v` equivalent to clicking "Buy Now" button
 */

// ======================================================================
// VARIABLES
// ======================================================================
const HOVER_DELAY = 100;
const SKIP_AMOUNT = 30;
let nowPlaying = null;
let hoverTimeout = null;
let isSkipping = false;

// ======================================================================
// MAIN SCRIPT
// ======================================================================

// Prevent script from running multiple times
if (window.bandcampDiggingToolLoaded) {
  console.log("⚠ Bandcamp Digging Tool already loaded");
} else {
  window.bandcampDiggingToolLoaded = true;
  void (async () => {
    await loadMoreItems();
    transcendGrid();
    init();
  })();
}

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

  // Remove existing listener if any, then add new one
  document.removeEventListener("keydown", handleKeydown);
  document.addEventListener("keydown", handleKeydown);

  items.forEach((item) => {
    const artContainer = item.querySelector(".collection-item-art-container");
    if (!artContainer) return;

    artContainer.addEventListener("mouseenter", () => handleMouseEnter(item));
    artContainer.addEventListener("mouseleave", () => handleMouseLeave(item));
  });

  console.log(`✓ Hover preview enabled on ${items.length} items`);
}

function handleKeydown(e) {
  if (!nowPlaying) return;

  if (e.key === "z") {
    e.preventDefault();
    const audio = document.querySelector("audio");
    if (audio) audio.currentTime = Math.max(0, audio.currentTime - SKIP_AMOUNT);
  } else if (e.key === "x") {
    e.preventDefault();
    const audio = document.querySelector("audio");
    if (audio) audio.currentTime = Math.min(audio.duration, audio.currentTime + SKIP_AMOUNT);
  } else if (e.key === "c") {
    e.preventDefault();
    skipToNextItem();
  } else if (e.key === "v") {
    e.preventDefault();
    const buyButton = nowPlaying.querySelector(".buy-now a");
    if (buyButton) buyButton.click();
  }
}

function skipToNextItem() {
  if (isSkipping) return;
  isSkipping = true;

  const items = Array.from(document.querySelectorAll(".collection-item-container"));
  const currentIndex = items.indexOf(nowPlaying);
  const nextItem = items[currentIndex + 1];

  if (nextItem) {
    startPlayback(nextItem);
    nextItem.querySelector(".collection-item-art-container")
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  setTimeout(() => isSkipping = false, 300);
}

function startPlayback(item) {
  // Stop previous item if different
  if (nowPlaying && nowPlaying !== item) {
    const prevPlayLink = nowPlaying.querySelector(".track_play_auxiliary");
    if (prevPlayLink && nowPlaying.classList.contains("playing")) {
      prevPlayLink.click();
    }
  }

  // Start new item
  const playLink = item.querySelector(".track_play_auxiliary");
  if (!playLink) return;

  if (!item.classList.contains("playing")) playLink.click();
  nowPlaying = item;

  // Seek to middle when ready
  const checkAudio = setInterval(() => {
    const audio = document.querySelector("audio");
    if (audio?.readyState >= 2) {
      audio.currentTime = audio.duration / 2;
      clearInterval(checkAudio);
    }
  }, 100);

  setTimeout(() => clearInterval(checkAudio), 3000);
}

function handleMouseEnter(item) {
  hoverTimeout = setTimeout(() => startPlayback(item), HOVER_DELAY);
}

function handleMouseLeave(item) {
  clearTimeout(hoverTimeout);
  hoverTimeout = null;

  if (nowPlaying === item) {
    const playLink = item.querySelector(".track_play_auxiliary");
    if (playLink && item.classList.contains("playing")) playLink.click();
    nowPlaying = null;
  }
}

async function loadMoreItems(maxItems = 500) {
  let previousCount = 0;
  let noChangeCount = 0;

  console.log("Loading more items...");

  while (true) {
    const currentCount = document.querySelectorAll(".collection-item-container").length;

    if (currentCount >= maxItems) {
      console.log(`Reached ${currentCount} items (max: ${maxItems})`);
      break;
    }

    if (currentCount === previousCount) {
      if (++noChangeCount >= 3) {
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

    const showMoreButton = document.querySelector(".expand-container .show-more");
    if (showMoreButton?.offsetParent) {
      console.log("Clicking show more button...");
      showMoreButton.click();
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    await new Promise((resolve) => setTimeout(resolve, 1500));
  }

  window.scrollTo(0, 0);
}
