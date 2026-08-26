import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

for (const viewport of [{name:'mobile',width:375,height:812},{name:'tablet',width:768,height:1024},{name:'desktop',width:1440,height:900}]) test(`${viewport.name} login is responsive and accessible`, async ({page}) => {
  await page.setViewportSize(viewport); await page.goto('/login'); await expect(page.getByRole('heading',{name:'Welcome back'})).toBeVisible(); await expect(page.locator('body')).not.toHaveCSS('overflow-x','scroll'); expect((await new AxeBuilder({page}).analyze()).violations).toEqual([])
})
test('keyboard flow and focus restoration', async ({page}) => { await page.goto('/login'); await page.keyboard.press('Tab'); await expect(page.locator('.skip-link')).toBeFocused(); await page.getByRole('button',{name:'Sign in'}).click(); await expect(page.getByLabel('Email address')).toBeFocused() })
test('Google starts through the Klyrow broker route', async ({page}) => { await page.goto('/login'); const target=page.waitForRequest(req=>req.url().includes('/auth/google')); await page.getByRole('button',{name:'Continue with Google'}).click(); expect((await target).url()).toContain('/auth/google?return_to=') })
test('no auth secrets or tokens are written to browser storage', async ({page}) => { await page.goto('/login'); expect(await page.evaluate(()=>({local:[...Object.keys(localStorage)],session:[...Object.keys(sessionStorage)]}))).toEqual({local:[],session:[]}); const source=await page.locator('html').evaluate(()=>document.documentElement.outerHTML); expect(source).not.toMatch(/client_secret|refresh_token|access_token/) })
