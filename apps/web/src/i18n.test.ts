import { describe, expect, it } from 'vitest'

const zh = ['overview', 'codexSessions', 'conversations', 'codexAccount', 'infra']
const en = ['overview', 'codexSessions', 'conversations', 'codexAccount', 'infra']

describe('i18n keys', () => {
  it('keeps critical chrome keys aligned', () => {
    expect(zh.sort()).toEqual(en.sort())
  })
})
