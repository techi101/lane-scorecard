# How to test Lane Scorecard

Two parts: **A** — click through the live site by hand (~25 minutes, a laptop and a phone). **B** — automatic tests on your own laptop (~5 minutes).

**Golden rule:** test only in the **Demo** workspace. **Your real pilot** is for real campus bin checks only. Never type test data there.

Live site: https://ss9ib2qbek.execute-api.us-east-1.amazonaws.com

---

## Part A — the live site, by hand

### Step 0 — the access code
Ask the team lead for the **operator access code** in a private message. It is never in this repo, a group chat or a screenshot. Anyone with it can change the real pilot, so do not forward it.

### Step 1 — sign in (laptop)
1. Open the live site.
2. Paste a **wrong** code. ✅ “That access code is not correct.”
3. Paste the **right** code. ✅ The dashboard opens.

### Step 2 — switch to Demo
Top-left **Workspace** → **Demo**. ✅ A “DEMO / simulated” label, 6 locations, scores filled in.

### Step 3 — add a test location
1. **Pilot setup** → *Location name* `TEST · <your name>` → tick the permission box → **Add location**. ✅ “Location added”.
2. Add the same name again. ✅ Refused: it already exists.

Use your own name in the label so testers don't collide with each other.

### Step 4 — record a check as the pilot lead
1. **Record a check** → your test location, today, *Morning*.
2. Green (bio) bin **A few wrong items**, blue (non-bio) **Clean**.
3. *What was wrong?* → tick **🛍 Plastic in the green (wet) bin** → tick *I personally checked these bins* → save. ✅ “Observation saved”.
4. Save another *Morning* check for the same place and day. ✅ Refused (one check per round).
5. Record an *Evening* check with **🍛 Food in the blue bin** ticked.

### Step 5 — weekly plan and report
1. **Weekly plan** → find your location. ✅ Specific advice such as “Plastic bags or wrappers went into the green bin… Seen in 1 of 2 checks”, and a “vs last week” line (“No score last week to compare with yet” is correct for a new location).
2. **Download weekly report** → open the file. ✅ Columns *Location, Score, Checks, Coverage, Dangerous items, Vs last week*; no private notes or photos.

### Step 6 — scorecard (and Hindi)
1. **Scorecards** → create a card for your location → open it. ✅ A score out of 100 and four parts: *What went wrong*, *Why it matters*, *Other locations* (only when 2+ other locations have checks), *One thing to try*.
2. Click **हिन्दी**. ✅ All text in Hindi.
3. Copy the link → open it in a private/incognito window. ✅ It opens without signing in.

### Step 7 — worker page (phone)
1. Laptop: **Pilot setup → Collection staff link → Create worker link** → **Copy link** or **Share on WhatsApp** to yourself.
2. Phone: open it. ✅ Location buttons appear; tapping one speaks it aloud (volume up — if silent, the phone has no Hindi voice and the page must still work). ✅ **Send** stays grey until a location and both bin faces are chosen.
3. Tap your location → 😐 green → 😟 blue → **🍛 Food in blue bin** → red **⚠️** → **✓ भेजें**. ✅ Big ✅ and “धन्यवाद”, then the page resets.
4. Laptop: **Weekly plan**. ✅ Your location shows **Worker safety — Make the bins safe to handle** first.
5. Laptop: **New link**; reload the old link on the phone. ✅ “This link is not working”.

### Step 8 — collection follow-up
1. Record another check for your location with *Kept separate during collection* = **No — mixed**.
2. **Weekly plan** → its action becomes *Keep collection separate* → **Track the collection fix** → **Record the fix** (e.g. “spoke to the collection team”) → save.
3. ✅ Status **More checks needed**. It only becomes *Ready for operator review* after collection stayed separate on 3 different days. That is correct.

### Step 9 — observation log and CSV
**Observation log** ✅ shows your checks, including the worker's *collection* round. **Download CSV** → open in Excel ✅ columns include `hazard`, `reporter` (`worker`) and `issues`.

### Step 9b — Photos
Record a check in your test location with a photo for one bin (any bin photo with no people). Open **Photos**. ✅ The photo shows with your location, the date, the round and the bin. Press **Delete photo** → **Cancel** ✅ it stays; press it again → confirm ✅ “Photo deleted” and it disappears, while the check is still in the Observation log with the same ratings.

### Step 10 — My Bin Guide
Open `<live site>/guide`. ✅ The page loads and says AI is **not available** (correct — AI is switched off).

### Step 11 — security
1. **Sign out**, reopen the site. ✅ The sign-in screen.
2. In a private window open `<live site>/api/pilot/dashboard`. ✅ An error, not data.

### Step 12 — clean up
Demo → **Pilot setup** → **Remove** next to your test location. ✅ Its checks and cards disappear.

---

## Part B — automatic tests on your laptop

First do the one-time setup in [TEAM_GUIDE.md, section 8](TEAM_GUIDE.md#8-run-it-on-your-own-laptop-step-by-step) (Git, Python 3.12, `git clone`, `setup.ps1`). Then, in PowerShell:

```powershell
cd $HOME\Desktop\lane-scorecard
git pull
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe tests\browser_check.py
.venv\Scripts\python.exe tests\browser_followups.py
```

| Line | What it does | Expect |
|---|---|---|
| `cd …` | Go into the project folder | — |
| `git pull` | Download the team's latest changes | “Already up to date” or a list of files |
| `pip install -r requirements-dev.txt` | Install the test tools (once) | Finishes without red errors |
| `pytest -q` | Run all automatic checks | `77 passed` (or more, if tests were added) |
| `browser_check.py` | Hidden Edge browser clicks through the whole pilot lead app | `"result": "PASS"` and `"browser_errors": []` |
| `browser_followups.py` | Same, for collection follow-ups | `"result": "PASS"` |

These run on your laptop only, with their own throwaway data. They never touch the live site.

---

## If something fails

Send the team: **(1)** the step number, **(2)** what you expected, **(3)** what happened, with a screenshot. For Part B, copy the last 20 lines of the PowerShell output.
