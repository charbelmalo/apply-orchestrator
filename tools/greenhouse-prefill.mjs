// Prefill a Greenhouse application from an answers file, then STOP.
//
//   npm i -D @playwright/test && npx playwright install chromium
//   node tools/greenhouse-prefill.mjs run/answers.json run/prefill.png
//
// The answers file comes from `python3 -m applyorch answers ...`.
// This script never clicks Submit and never touches legal fields (arbitration,
// attestations): those are the applicant's own act. It leaves a visible browser
// window open for a human to review every field, tick the legal boxes and submit.
//
// Not exercised by the test suite (it needs a live posting and a browser).
// It is the scripted alternative to the computer-use agent for Greenhouse forms,
// whose field ids are stable once resolved by the answers builder.
import { chromium } from '@playwright/test'
import fs from 'node:fs'

const answers = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const shot = process.argv[3] || 'prefill.png'
const filled = [], missed = []

const browser = await chromium.launch({ headless: false, args: ['--window-size=1500,1150'] })
const page = await (await browser.newContext({ viewport: { width: 1500, height: 1080 } })).newPage()

await page.goto(answers.url, { waitUntil: 'domcontentloaded', timeout: 90000 })
await page.waitForTimeout(3000)

// Some postings hide the form behind an Apply button.
for (const label of ['Apply', 'Apply for this job', 'Apply Now']) {
  const b = page.getByRole('button', { name: label, exact: false }).first()
  if (await b.count() && await b.isVisible().catch(() => false)) {
    await b.click().catch(() => {}); await page.waitForTimeout(2000); break
  }
}

async function fillText (name, value) {
  for (const sel of [`#${name}`, `[name="${name}"]`, `textarea[name="${name}"]`]) {
    const el = page.locator(sel).first()
    if (await el.count().catch(() => 0)) {
      try {
        await el.scrollIntoViewIfNeeded({ timeout: 4000 })
        await el.fill(value, { timeout: 8000 })
        filled.push(name); return
      } catch { /* try the next selector */ }
    }
  }
  missed.push(name)
}

async function pickSelect (name, value) {
  // Greenhouse renders these as native selects on some postings and comboboxes on others.
  const native = page.locator(`select[name="${name}"], select#${name}`).first()
  if (await native.count().catch(() => 0)) {
    try { await native.selectOption({ label: value }, { timeout: 6000 }); filled.push(name); return } catch {}
  }
  const combo = page.locator(`#${name}, [name="${name}"]`).first()
  if (await combo.count().catch(() => 0)) {
    try {
      await combo.scrollIntoViewIfNeeded({ timeout: 4000 })
      await combo.click({ timeout: 6000 })
      await page.waitForTimeout(500)
      const opt = page.getByRole('option', { name: value, exact: true }).first()
      if (await opt.count()) { await opt.click({ timeout: 5000 }); filled.push(name); return }
    } catch {}
  }
  missed.push(name)
}

for (const [k, v] of Object.entries(answers.text || {})) await fillText(k, v)
for (const [k, v] of Object.entries(answers.long || {})) await fillText(k, v)
for (const [k, v] of Object.entries(answers.select || {})) await pickSelect(k, v)

if (answers.resume && fs.existsSync(answers.resume)) {
  const input = page.locator('input[type="file"]').first()
  if (await input.count().catch(() => 0)) {
    try { await input.setInputFiles(answers.resume); filled.push('resume') } catch { missed.push('resume') }
  } else missed.push('resume (no file input found)')
}

console.log('FILLED : ' + filled.join(', '))
console.log('MISSED : ' + (missed.length ? missed.join(', ') : 'nothing'))
console.log('LEFT FOR YOU (legally binding, by design): ' + (answers.skip_legal || []).join(', '))
console.log('NOT SUBMITTED. Review every field, tick the legal boxes yourself, then click Submit.')

await page.screenshot({ path: shot, fullPage: true }).catch(() => {})
await page.waitForTimeout(60 * 60 * 1000) // hold the window open for review
