const { chromium } = require('playwright');
const { devices } = require('playwright');

const BASE = 'http://192.168.178.50:8081';
const API = 'http://192.168.178.50:8000';

(async () => {
  const device = devices['Pixel 5'];
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    ...device,
    locale: 'en-US',
  });
  const page = await context.newPage();

  // Capture console logs
  page.on('console', msg => console.log(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => console.log(`[PAGE ERROR] ${err.message}`));

  console.log('=== Mobile Test: Songbook PWA ===\n');

  // 1. Load the app
  console.log('1. Loading app...');
  await page.goto(BASE, { waitUntil: 'networkidle' });
  console.log(`   Title: ${await page.title()}`);
  console.log(`   URL: ${page.url()}`);
  console.log('   OK - Login page loaded\n');

  // 2. Login
  console.log('2. Logging in...');
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/songs', { timeout: 5000 });
  console.log(`   Redirected to: ${page.url()}`);
  console.log('   OK - Logged in\n');

  // 3. Check songs list
  console.log('3. Songs list...');
  await page.waitForSelector('.song-card', { timeout: 5000 });
  const songCount = await page.locator('.song-card').count();
  console.log(`   ${songCount} songs displayed`);

  // 4. Open a song
  console.log('\n4. Opening first song...');
  await page.locator('.song-card').first().click();
  await page.waitForURL('**/songs/**', { timeout: 5000 });
  await page.waitForTimeout(500);
  const songTitle = await page.locator('.song-title').textContent();
  const artist = await page.locator('.song-artist').textContent();
  console.log(`   Song: ${songTitle} - ${artist}`);

  // 5. Test transpose
  console.log('\n5. Testing transpose...');
  const upBtn = page.locator('.transpose-control .ctrl-btn').nth(2); // + button
  await upBtn.click();
  await page.waitForTimeout(200);
  console.log('   OK - Transposed up');

  // 6. Test display mode toggle
  console.log('\n6. Testing display mode toggle...');
  const inlineBtn = page.locator('.mode-toggle .ctrl-btn').nth(1);
  await inlineBtn.click();
  await page.waitForTimeout(200);
  console.log('   OK - Switched to inline mode');
  const aboveBtn = page.locator('.mode-toggle .ctrl-btn').nth(0);
  await aboveBtn.click();
  await page.waitForTimeout(200);
  console.log('   OK - Switched back to above mode');

  // 7. Take screenshot
  console.log('\n7. Taking screenshot...');
  await page.screenshot({ path: '/tmp/songbook_mobile.png', fullPage: true });
  console.log('   Saved to /tmp/songbook_mobile.png');

  // 8. Test navigation
  console.log('\n8. Testing navigation...');
  await page.click('text=Songbooks');
  await page.waitForURL('**/songbooks', { timeout: 3000 });
  console.log(`   Songbooks page: ${page.url()}`);
  await page.click('text=Songs');
  await page.waitForURL('**/songs', { timeout: 3000 });
  console.log('   OK - Navigation works\n');

  // 9. Test logout/login flow
  console.log('9. Testing logout...');
  await page.click('text=Logout');
  await page.waitForURL('**/login', { timeout: 3000 });
  console.log(`   Redirected to login: ${page.url()}`);
  console.log('   OK - Logout works\n');

  console.log('=== All mobile tests passed ===');

  await browser.close();
})().catch(err => {
  console.error('TEST FAILED:', err);
  process.exit(1);
});
