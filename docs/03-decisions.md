# 03 — Decisions (open and closed)

> The owner decides. When a decision is made, move it to "Closed" with the date and the reason.
> Business decisions are parked and kept privately by the owner, outside this repo.

## Open

### D8. Company / legal entity
Only relevant if the business side is ever resumed.

## Closed

- 2026-10-17 — **Name: Sandstorm Secure.** Repo: `Sandstorm-Secure`.
- 2026-10-17 — **No private or personal information in the repo.** Business notes and personal
  context live outside it. A device to protect goes in `blocked_devices` in the local config.
- 2026-10-15 — **Goal = a working app + portfolio piece, not business validation.**
- 2026-10-15 — **Use Google AMAPI, not a self-built de-Googled MDM.** A self-hosted MDM with our
  own Device Owner agent was considered and rejected for now: we would own all the
  security-critical code, and AMAPI lets Google do the enforcement.
- 2026-10-15 — **App shape: local FastAPI dashboard over a tested Python core.** Never hosted.
- 2026-10-15 — **Test device: Pixel_6 emulator only.** No real phone is wiped or enrolled.
- 2026-10-15 — **Support both fully-managed and work-profile modes** (fully managed first).
- 2026-10-15 — **Mock landing page + sign-up form that sends nothing.**
- 2026-10-15 — **Demo mode with labelled sample data** as the last milestone, for the portfolio.
- 2026-10-15 — **Private GitHub repo** on the owner's personal account; public only after a privacy
  pass. Claude Code does all git work.
- 2026-10-15 — **Android only.** iOS needs Apple certificates and Apple Business Manager.
- 2026-10-09 — **No custom OS / leased hardware.** OEM can lock bootloaders; leasing has
  depreciation and theft risk.
- 2026-10-09 — **No law firms / military / regulated clients.** Too much legal risk.
