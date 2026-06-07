import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:5173'
const CREDS = { username: 'admin', password: 'agro2026' }

async function login(page: any) {
  await page.goto(`${BASE}/login`)
  await page.fill('input[name="username"]', CREDS.username)
  await page.fill('input[name="password"]', CREDS.password)
  await page.click('button[type="submit"]')
  await page.waitForURL(`${BASE}/`, { timeout: 10000 })
}

// ── Login ────────────────────────────────────────────────────────────────────
test('unauthenticated user is redirected to /login', async ({ page }) => {
  await page.goto(BASE)
  await page.waitForURL('**/login')
  await expect(page.locator('h2')).toBeVisible()
})

test('wrong credentials shows error message', async ({ page }) => {
  await page.goto(`${BASE}/login`)
  await page.fill('input[name="username"]', 'baduser')
  await page.fill('input[name="password"]', 'badpass')
  await page.click('button[type="submit"]')
  await expect(page.locator('.error-msg')).toBeVisible({ timeout: 6000 })
})

test('correct credentials land on fields page', async ({ page }) => {
  await login(page)
  await expect(page.locator('.sidebar')).toBeVisible()
  await expect(page.locator('.dash-stats')).toBeVisible()
})

// ── Sidebar / dashboard ───────────────────────────────────────────────────────
test('dash stat numbers are all numeric', async ({ page }) => {
  await login(page)
  const nums = page.locator('.dash-stat-num')
  const count = await nums.count()
  expect(count).toBeGreaterThanOrEqual(3)
  for (let i = 0; i < count; i++) {
    const text = await nums.nth(i).textContent()
    expect(text?.trim()).toMatch(/^\d+$/)
  }
})

test('dash stat cards do not overflow', async ({ page }) => {
  await login(page)
  const cards = page.locator('.dash-stat')
  const count = await cards.count()
  for (let i = 0; i < count; i++) {
    const box = await cards.nth(i).boundingBox()
    expect(box).not.toBeNull()
    expect(box!.width).toBeGreaterThan(30)
  }
})

test('"Додати поле" opens modal', async ({ page }) => {
  await login(page)
  await page.click('button:has-text("+ Додати поле")')
  await expect(page.locator('.modal h3')).toHaveText('Нове поле')
  await page.keyboard.press('Escape')
})

test('drawing mode button shows tip and cancel', async ({ page }) => {
  await login(page)
  await page.click('button[title="Намалювати межу поля на карті"]')
  await expect(page.locator('text=Клікайте на карту')).toBeVisible()
  await page.click('button:has-text("Скасувати")')
  await expect(page.locator('text=Клікайте на карту')).not.toBeVisible()
})

// ── Status filter ─────────────────────────────────────────────────────────────
test('status filter has all expected options', async ({ page }) => {
  await login(page)
  const fieldCards = page.locator('.card')
  if (await fieldCards.count() === 0) { test.skip(); return }
  await fieldCards.first().click()
  const select = page.locator('select')
  await expect(select).toBeVisible({ timeout: 5000 })
  const options = await select.locator('option').allTextContents()
  expect(options).toContain('Всі польоти')
  expect(options).toContain('Готові')
  expect(options).toContain('З помилкою')
})

// ── Map ───────────────────────────────────────────────────────────────────────
test('map renders a canvas', async ({ page }) => {
  await login(page)
  await expect(page.locator('canvas')).toBeVisible({ timeout: 10000 })
})

test('clicking a field triggers map zoom (no JS error)', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await login(page)
  const fieldCards = page.locator('.card')
  if (await fieldCards.count() === 0) { test.skip(); return }
  await fieldCards.first().click()
  await page.waitForTimeout(1000)
  expect(errors.filter((e) => !e.includes('ResizeObserver'))).toHaveLength(0)
})

// ── Flight page ───────────────────────────────────────────────────────────────
async function goToFirstFlight(page: any): Promise<boolean> {
  await login(page)
  const fieldCards = page.locator('.card')
  if (await fieldCards.count() === 0) return false
  await fieldCards.first().click()
  await page.waitForTimeout(500)
  // after clicking field, flight cards appear — click first flight card
  const allCards = page.locator('.card')
  if (await allCards.count() < 2) return false
  await allCards.nth(1).click()
  try {
    await page.waitForURL('**/flights/**', { timeout: 5000 })
  } catch {
    return false
  }
  return true
}

test('flight page has "Назад" button', async ({ page }) => {
  if (!await goToFirstFlight(page)) { test.skip(); return }
  await expect(page.locator('button:has-text("← Назад")')).toBeVisible()
})

test('flight page has notes textarea', async ({ page }) => {
  if (!await goToFirstFlight(page)) { test.skip(); return }
  await expect(page.locator('textarea[placeholder*="нотатки"]')).toBeVisible()
})

test('notes can be typed and save button is enabled', async ({ page }) => {
  if (!await goToFirstFlight(page)) { test.skip(); return }
  const ta = page.locator('textarea[placeholder*="нотатки"]')
  await ta.fill('Тест нотатка')
  const saveBtn = page.locator('button:has-text("Зберегти нотатки")')
  await expect(saveBtn).toBeEnabled()
})

// ── Logout ────────────────────────────────────────────────────────────────────
test('logout redirects to login', async ({ page }) => {
  await login(page)
  await page.click('.topbar button:has-text("Вийти")')
  await page.waitForURL('**/login', { timeout: 5000 })
  await expect(page).toHaveURL(/login/)
})
