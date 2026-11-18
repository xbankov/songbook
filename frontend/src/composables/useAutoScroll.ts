import { onBeforeUnmount, ref, type Ref } from 'vue'

// One autoscroll for the song view and the play view (#144). It advances by
// fractional pixels on requestAnimationFrame, so the text moves continuously
// instead of jumping ten times a second.

export const MIN_SCROLL_SPEED = 0.1
export const MAX_SCROLL_SPEED = 10
export const SCROLL_SPEED_STEP = 0.1
const DEFAULT_SCROLL_SPEED = 1
const SPEED_STORAGE_KEY = 'songbook:autoscroll-speed'

function clampSpeed(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_SCROLL_SPEED
  return Math.round(
    Math.max(MIN_SCROLL_SPEED, Math.min(MAX_SCROLL_SPEED, value)) * 10,
  ) / 10
}

function storedSpeed(): number {
  try {
    const raw = localStorage.getItem(SPEED_STORAGE_KEY)
    return raw === null ? DEFAULT_SCROLL_SPEED : clampSpeed(Number(raw))
  } catch {
    return DEFAULT_SCROLL_SPEED
  }
}

// Shared across views, so the chosen speed survives switching between the song
// page and performance mode.
const speed = ref(storedSpeed())

export function useAutoScroll(target?: Ref<HTMLElement | null>) {
  const autoScroll = ref(false)
  let frame: number | null = null
  let lastTime = 0
  let position: number | null = null

  function scroller(): HTMLElement | null {
    // An explicit target that is temporarily null must not fall back to the
    // document (e.g. the performance stage disappearing mid-route-change).
    if (target) return target.value
    return document.scrollingElement as HTMLElement | null
  }

  function markManualScroll() {
    // Start the next frame from where the user left the page.
    position = null
  }

  function listenForManualScroll() {
    window.addEventListener('wheel', markManualScroll, { passive: true })
    window.addEventListener('touchstart', markManualScroll, { passive: true })
    window.addEventListener('pointerdown', markManualScroll, { passive: true })
    window.addEventListener('pointermove', markManualScroll, { passive: true })
    window.addEventListener('keydown', markManualScroll)
  }

  function stopListeningForManualScroll() {
    window.removeEventListener('wheel', markManualScroll)
    window.removeEventListener('touchstart', markManualScroll)
    window.removeEventListener('pointerdown', markManualScroll)
    window.removeEventListener('pointermove', markManualScroll)
    window.removeEventListener('keydown', markManualScroll)
  }

  function tick(now: number) {
    frame = null
    if (!autoScroll.value) return
    const element = scroller()
    if (!element) {
      stop()
      return
    }
    if (!lastTime) lastTime = now
    // Clamp a long gap (background tab, stalled frame) so it does not jump.
    const seconds = Math.min((now - lastTime) / 1000, 0.1)
    lastTime = now

    const maxScroll = element.scrollHeight - element.clientHeight
    if (maxScroll <= 0 || element.scrollTop >= maxScroll - 1) {
      stop()
      return
    }

    // Keep a fractional position so every frame can move the page by a
    // fraction of a pixel; flooring would fall back to ~10 jumps per second.
    // User input resets it, so a manual scroll is never overwritten.
    if (position === null) position = element.scrollTop
    // Speed 1 means the old 1px per 100ms (10px per second).
    position = Math.min(position + speed.value * 10 * seconds, maxScroll)
    element.scrollTop = position
    frame = requestAnimationFrame(tick)
  }

  function start() {
    if (autoScroll.value) return
    autoScroll.value = true
    lastTime = 0
    position = null
    listenForManualScroll()
    frame = requestAnimationFrame(tick)
  }

  function stop() {
    autoScroll.value = false
    if (frame !== null) cancelAnimationFrame(frame)
    frame = null
    lastTime = 0
    position = null
    stopListeningForManualScroll()
  }

  function toggle() {
    if (autoScroll.value) stop()
    else start()
  }

  function setSpeed(value: number) {
    speed.value = clampSpeed(value)
    try {
      localStorage.setItem(SPEED_STORAGE_KEY, String(speed.value))
    } catch {
      // Private mode or a full storage quota: the speed still applies.
    }
  }

  function changeSpeed(delta: number) {
    setSpeed(speed.value + delta)
  }

  onBeforeUnmount(stop)

  return { autoScroll, speed, toggle, start, stop, setSpeed, changeSpeed }
}
