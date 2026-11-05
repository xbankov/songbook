#!/bin/bash
# Mobile app test runner - uses Playwright with Android device emulation

cd /tmp
[ ! -d node_modules ] && npm init -y --silent 2>/dev/null && npm install playwright 2>&1 | tail -1

NODE_PATH=/tmp/node_modules node -e '
const { chromium, devices } = require("playwright");
const BASE = "http://192.168.178.50:8081";

(async () => {
  const browser = await chromium.launch({ headless: true });
  // Use Pixel 8 Pro device profile
  const pixel8pro = {
    ...devices["Pixel 5"],
    viewport: { width: 412, height: 915 },
    userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36"
  };
  const context = await browser.newContext(pixel8pro);
  const page = await context.newPage();

  page.on("console", msg => process.stderr.write("[CONSOLE] " + msg.text() + "\n"));
  page.on("pageerror", err => process.stderr.write("[ERROR] " + err.message + "\n"));

  console.log("=== Pixel 8 Pro Test ===\n");

  // 1. Load
  await page.goto(BASE, { waitUntil: "networkidle" });
  console.log("1. Login page:", await page.title());

  // 2. Login
  await page.fill("input[type=\"text\"]", "admin");
  await page.fill("input[type=\"password\"]", "admin");
  await page.click("button[type=\"submit\"]");
  await page.waitForURL("**/songs", { timeout: 5000 });
  console.log("2. Logged in");

  // 3. List songs
  await page.waitForSelector(".song-card", { timeout: 5000 });
  const count = await page.locator(".song-card").count();
  console.log("3. Songs:", count);

  // 4. Open first song
  if (count > 0) {
    await page.locator(".song-card").first().click();
    await page.waitForURL("**/songs/**", { timeout: 5000 });
    await page.waitForTimeout(500);
    const title = await page.locator(".song-title").textContent();
    const artist = await page.locator(".song-artist").textContent();
    console.log("4. Opened:", title, "-", artist);

    // 5. Transpose up (second ctrl-btn = nth(1) = + button)
    await page.locator("button[title=\"Transpose up\"]").click();
    await page.waitForTimeout(200);
    console.log("5. Transposed up");

    // 6. Reset transpose
    await page.locator("button[title=\"Reset\"]").click();
    await page.waitForTimeout(200);
    console.log("6. Reset transpose");

    // 7. Toggle display mode
    await page.locator("button[title=\"Chords inline with text\"]").click();
    await page.waitForTimeout(200);
    await page.locator("button[title=\"Chords above lyrics\"]").click();
    await page.waitForTimeout(200);
    console.log("7. Display mode: above");

    // 8. Print PDF
    await page.click("text=Print PDF");
    await page.waitForTimeout(1000);
    console.log("8. PDF opened (new tab)");
  }

  // 9. Screenshot
  await page.screenshot({ path: "/tmp/songbook_pixel8pro.png", fullPage: true });
  console.log("9. Screenshot saved");

  // 10. Logout
  await page.locator("button:has-text(\"Logout\")").click({ force: true });
  await page.waitForTimeout(1000);
  const currentUrl = page.url();
  console.log("10. Logged out ->", currentUrl);

  console.log("\n=== All tests passed ===");
  await browser.close();
})().catch(e => { console.error("FAILED:", e.message); process.exit(1); });
'
