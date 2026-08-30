import { render } from '@testing-library/vue'
import { expect, it } from 'vitest'
import App from '../App.vue'

it('provides labels, descriptions, landmarks, live regions and keyboard focus styles', () => {
  history.replaceState({}, '', '/signup'); const { container }=render(App)
  expect(container.querySelector('main#auth-main')).toBeTruthy(); expect(container.querySelector('h1')).toBeTruthy()
  for (const input of Array.from(container.querySelectorAll('input'))) expect(input.labels?.length).toBeGreaterThan(0)
  for (const input of Array.from(container.querySelectorAll('input[aria-describedby]'))) for (const id of (input.getAttribute('aria-describedby')||'').split(' ')) expect(container.querySelector(`#${id}`)).toBeTruthy()
  expect(container.querySelector('[aria-live="polite"]')).toBeTruthy(); expect(container.querySelector('.skip-link')).toBeTruthy()
})
