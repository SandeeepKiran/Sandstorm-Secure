# Sandstorm Secure: launch video plan

## Answers
- **What is it:** A local Android phone-management (MDM) CLI and dashboard built on Google's Android Management API.
- **Who is it for:** People who manage a few Android phones and want them locked down (forced VPN, no USB data, app allow-list, remote wipe), and anyone who looks at the portfolio.
- **What sets it apart:** Honest by design. Every status comes from the Google API (demo uses labelled sample data). The dashboard runs only on `127.0.0.1` because it can wipe phones. A wipe needs the device ID typed in.
- **Best claim:** "Flip a switch. The policy JSON follows." The demo really rewrites the policy JSON live.
- **Visual hook:** Policy keys typing out (`"usbFileTransferDisabled": true`) under a big "Lock down Android phones."
- **Real UI shown:** The v5.1.0 static demo pages (`demo/policies.html`, `demo/enroll.html`, `demo/index.html`), driven live in iframes with the repo's sample data.
- **Tone:** `polished` with `app-store` feature cards. Calm, product-grade, no jokes.
- **Share caption:** see `share-copy.txt`.

## Angle
Earlier launch video (docs/media) told "pick rules, scan QR, see compliance". This one leads with **the rules themselves** (policy JSON) and ends on **the safety rails** (typed device ID to wipe, dashboard only on 127.0.0.1).

## Visual identity
Stage in the app's sidebar navy `#0b1220` with a soft dot grid. Brand sand `#c8a165` only for the logo mark and eyebrows. Primary blue `#2563eb` / `#3b82f6`. Inter (self-hosted from `demo/vendor`). App windows are light theme, as the product defaults.

## Storyboard (30 fps, 1920x1080, 23.0 s)
| # | Time | Scene | On screen | Motion / sound |
|---|---|---|---|---|
| 1 | 0.0-3.1 | Hook | "Lock down **Android** phones." / "Write the rules. Google enforces them." over typed policy keys | Title rises, keys type out with quiet ticks, riser into reveal |
| 2 | 3.1-6.3 | Reveal | Sand shield mark, "Sandstorm Secure", "Android phone management on Google's official API.", chips: Forced VPN, USB data block, App allow-list, Remote wipe | Mark pops in, chips stagger; kick and bass start |
| 3 | 6.3-11.0 | 01 / Policies | Real Policies page; cursor turns off "Block USB file transfer" (7.9 s) and "Block screenshots" (9.0 s). Side card shows the page's live JSON preview; changed lines light up. Real "unsaved changes" bar appears | Click ticks on A5; hats start |
| 4 | 11.0-15.0 | 02 / Enroll | "One QR code puts a phone under a policy." Real Enroll page; cursor clicks Generate QR code (12.3 s); stepper completes, sample QR appears; camera pushes in | Click tick, soft swell |
| 5 | 15.0-19.4 | 03 / Devices | "See which phones comply." Real Devices page with summary cards; cursor opens the Moto G54 row menu (16.4 s); red ring on the Danger zone; "Wipe one? Type its device ID first." | Click tick |
| 6 | 19.4-23.0 | Outro | Mark, name, "The dashboard runs only on 127.0.0.1.", URL button `sandeeepkiran.github.io/Sandstorm-Secure`, "Live demo with sample data - Open source, AGPL-3.0" | Low D chord rings out, fade |

Transitions dip through the background (out 0.3 s, then in 0.35 s), never a cross-dissolve of two busy layouts.

## Music cue guidance
Original synth score from `work/music.py`: D minor, 120 BPM, Dm-Bb-F-C. Pad only in the hook, kick + bass from the reveal, offbeat hats from the first feature, click ticks on A5, low D hit on the outro.
