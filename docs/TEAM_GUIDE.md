# Lane Scorecard — the complete team guide

Written for teammates who are seeing this project for the first time. You do **not** need Claude, ChatGPT or any paid service to understand or run it. Every technical word is explained the first time it appears, and again in the [word list](#2-words-you-will-meet) below.

Read it in order the first time. It takes about 40 minutes. After that, use the table of contents to jump around.

## Contents

1. [The project in one minute](#1-the-project-in-one-minute)
2. [Words you will meet](#2-words-you-will-meet)
3. [The problem, and the people it is for](#3-the-problem-and-the-people-it-is-for)
4. [A tour of every screen](#4-a-tour-of-every-screen)
5. [How the score is calculated](#5-how-the-score-is-calculated)
6. [“Did last week's action work?” — the follow-up check](#6-did-last-weeks-action-work--the-follow-up-check)
7. [The collection staff page (worker mode)](#7-the-collection-staff-page-worker-mode)
8. [Run it on your own laptop, step by step](#8-run-it-on-your-own-laptop-step-by-step)
9. [Every folder and file, and what it does](#9-every-folder-and-file-and-what-it-does)
10. [Where AWS fits](#10-where-aws-fits)
11. [The hackathon: rules, judging and our risks](#11-the-hackathon-rules-judging-and-our-risks)
12. [The 3-minute video plan](#12-the-3-minute-video-plan)
13. [What is done and what is left](#13-what-is-done-and-what-is-left)
14. [Questions judges or interviewers may ask, with answers](#14-questions-judges-or-interviewers-may-ask-with-answers)
15. [What we must never claim](#15-what-we-must-never-claim)
16. [When something breaks](#16-when-something-breaks)

---

## 1. The project in one minute

Hostels put two bins on every floor: a **green bin for wet waste** (food, peels, tea leaves) and a **blue bin for dry waste** (packets, paper, bottles). Keeping them separate is called **waste segregation**. In practice people mix them, and nobody tells them.

Lane Scorecard is a small website that:

1. lets the **warden** (or a volunteer) record how clean each floor's two bins looked, in about two minutes;
2. lets **housekeeping and sanitation staff** report the bins at pickup using only pictures and Hindi voice, with no reading;
3. turns those reports into a **score out of 100** for each floor every week;
4. gives each floor **specific feedback**: what went wrong most often (for example “plastic bags went into the green bin”), why it matters, how the other floors did, and one thing to try — in English or Hindi;
5. then checks **whether that step worked** the next week — and refuses to claim a change that is within normal week-to-week ups and downs;
6. puts **worker safety first**: if staff flag broken glass, blades, needles or unwrapped sanitary waste, that floor's top action becomes making the bins safe to handle.

No student names are collected. Floors are compared with the hostel average, not ranked publicly. Recognition, not prizes or money.

It is entered in the **Waste & Energy** track of the WeMakeDevs × AWS **Environmental Hacks** hackathon (8–11 October 2026).

---

## 2. Words you will meet

| Word | Plain meaning |
|---|---|
| **Repository (repo)** | A project folder stored on GitHub, with the full history of every change. |
| **Commit** | One saved change in the repo's history, with a date and a message. |
| **Private repo** | Only people invited can see it. Ours is private until we submit. |
| **Collaborator** | A GitHub user invited to a repo who can push changes. |
| **Clone** | Download a copy of the repo to your laptop. |
| **Segregation** | Keeping wet and dry waste in separate bins. |
| **Bio / wet waste** | Food and other things that rot. Green bin. In the code this stream is called `bio`. |
| **Non-bio / dry waste** | Packets, paper, plastic, metal. Blue bin. In the code: `nonbio`. |
| **Floor** | One unit we score, for example “Bhaskar · First floor”. |
| **Check / observation** | One look at a floor's two bins, with a rating for each. |
| **Round** | When the check happened: `morning`, `evening`, or `collection` (a staff report at pickup). One check per floor, per day, per round. |
| **Rating** | How a bin looked: clean, a few wrong items, mixed, or not seen. |
| **Score** | A number from 0 to 100 for a floor's week. Higher is cleaner. |
| **Coverage** | Out of the bins we should have looked at, how many we actually saw. |
| **Operator / warden** | The person who signs in and manages the pilot. |
| **Operator access code** | The password for the warden's side. Never share it, never put it in the repo. |
| **Scorecard** | A small private web page for one floor's week, in English or Hindi, shareable by link. |
| **Worker link** | A secret web address for housekeeping staff. Opens the picture-only page. Can be switched off. |
| **Issue tag** | A picture button saying *what* was wrong: 🛍 plastic in the green (wet) bin, 🍛 food in the blue (dry) bin, or 👜 everything in one bag. Optional, on both the warden form and the worker page. |
| **Hazard / dangerous item** | Broken glass, blades, needles or unwrapped sanitary waste found in a bin. |
| **Demo workspace** | Fake, generated data for showing the app. Always labelled “simulated”. |
| **Pilot workspace** | Real observations only. Starts empty. |
| **Noise** | Up-and-down movement in a score that happens by chance, not because anything changed. |
| **Standard error** | A number that says how much a weekly average would wobble by chance. We use two of them as the “noise band”. |
| **Python** | The programming language the server is written in. |
| **FastAPI** | A Python library for building the web server and its API. |
| **API** | The set of web addresses the page calls to save and load data, for example `/api/pilot/checks`. |
| **SQLite** | A small database stored as one file. Used when running on a laptop. |
| **JavaScript** | The language that runs inside the browser and draws the screens (`web/app.js`, `web/worker.js`). |
| **pytest** | The tool that runs our automated tests. |
| **Playwright** | A tool that opens a real browser automatically and clicks through the app to test it. |
| **AWS** | Amazon Web Services: Amazon's rented computers and services. |
| **Lambda** | An AWS service that runs our server code only when a request arrives. |
| **API Gateway** | The AWS front door that gives our app a public web address and passes requests to Lambda. |
| **DynamoDB** | AWS's database. Replaces SQLite when deployed. |
| **S3** | AWS file storage. Stores bin photos privately. |
| **EventBridge** | AWS's scheduler. Runs the weekly scorecard job. |
| **CloudWatch** | AWS logs and monitoring. |
| **Bedrock / Nova** | AWS's AI models. Optional photo suggestions; switched off by default. |
| **SAM (Serverless Application Model)** | An AWS tool. `template.yaml` lists every AWS piece we need; `sam build` packages it; `sam deploy` creates it on AWS; `sam local` runs it on your laptop. |
| **Docker** | A program that runs a sealed mini-computer (a “container”). SAM uses it to run our Lambda exactly as AWS would. |
| **Virtual environment (`.venv`)** | A private folder of Python packages just for this project. |
| **`.gitignore`** | A list of files git must never upload (secrets, databases, build output). |

---

## 3. The problem, and the people it is for

**The problem.** Two labelled bins do not tell anyone whether waste is actually being separated, or whether it gets mixed again at collection. Residents get no feedback. Wardens have no evidence to act on. And when waste is mixed, someone sorts it by hand.

**The people** (these are our reasoning, not yet interviews — talk to real people before claiming them):

- **Warden** — has many jobs and little time. Wants one clear thing to do per floor and a printable sheet for the hostel meeting. *Decision we help with:* “Which floor needs attention this week, and what should I do?”
- **Housekeeping / sanitation staff** — see every bin at every pickup. When residents mix waste, they sort it by hand, sometimes with glass, blades or sanitary waste inside. Many do not read English; some do not read at all. Usually have WhatsApp on a basic Android phone.
- **Students** — do not read long notices and do not want to be shamed. Often unsure where greasy food-delivery containers go. A floor-level, non-public comparison and one short tip is what they will actually look at.

**What makes us different from other teams.** In the Waste & Energy track, other projects (for example SortSmart, Swachh.ai, Indohood, BinGo, KabadiPlus) focus on sorting advice for households, item classification, or reward points. We focus on two things nobody else in our track does: **checking whether an action actually worked**, and **giving the sanitation worker a voice**.

---

## 4. A tour of every screen

Open the app, sign in with the operator access code, then:

- **Workspace switch (top left)** — choose *Demo* (fake data, for showing) or *Your real pilot* (real data only).
- **Overview** — this week's community score, both-bins-clean rate, coverage, a four-week trend, and recent checks.
- **Record a check** — choose floor, date and round; tap a rating for each bin; optionally say whether collection kept them separate; optionally add a photo; tick “I personally checked these bins”. Save.
- **Weekly plan** — one card per floor: the action, the evidence behind it, and the **“vs last week”** line. A button records the next check for that floor. A button downloads the weekly report.
- **Scorecards** — the card uses the floor's most frequent issue tag to show four short parts: *What went wrong* (and in how many checks), *Why it matters*, *Other floors* (how many of the other floors avoided it; hidden if fewer than 2 other floors have checks), and *One thing to try*. With no tags, it shows a general tip for the weaker bin. Make a private card for a floor, open it, switch to Hindi, print it, copy its link, or share on WhatsApp. Cards are revoked automatically when data is corrected, so old numbers are never shared.
- **Observation log** — every check; correct or delete; download a CSV (spreadsheet).
- **Pilot setup** — add floors (only with permission), and create the **collection staff link**.
- **How it works** — the scoring rules in plain words.
- **Worker page** (`/w/<link>`) — the picture-only page for staff. See section 7.

---

## 5. How the score is calculated

Each bin rating becomes points:

| Rating | Points |
|---|---:|
| Clean | 100 |
| A few wrong items | 50 |
| Mixed | 0 |
| Not seen | not counted at all |

For each floor over seven days:

1. Average the green-bin points. Average the blue-bin points.
2. The floor score is the average of those two averages.
3. The community score is the average of all floors that have a score.

**Worked example.** First floor, three checks this week:

| Day | Green bin | Blue bin |
|---|---|---|
| Mon | Clean (100) | Mixed (0) |
| Wed | A few wrong (50) | Clean (100) |
| Fri | Clean (100) | Not seen |

Green average = (100 + 50 + 100) ÷ 3 = 83.3. Blue average = (0 + 100) ÷ 2 = 50 (Friday not counted). Floor score = (83.3 + 50) ÷ 2 = **66.7**. Coverage = 5 bins seen out of 6 expected = **83%**.

**Rule to remember:** a bin we did not see never counts as clean.

---

## 6. “Did last week's action work?” — the follow-up check

Every floor card says whether the floor is **clearly better**, **clearly worse**, or shows **no clear change** compared with the previous seven days.

**Why we can't just say “down 20 points”.** On our simulated data, with one check a day, a floor's weekly score jumps up and down by about **±30 points purely by chance**. If the app said “worse” every time the number dropped, it would mislead the warden most weeks.

**What the app does instead:**

1. It compares only **checks where both bins were seen**, so every number measures the same thing. (If one week's checks saw only the green bin and the next week's only the blue bin, the two weeks are not comparable.)
2. It needs at least **3 such checks in each week**. Otherwise: “too few checks”.
3. It works out the **noise band**: two standard errors of the difference between the two weeks' averages. Think of it as “how much the number usually moves even when nothing changed”.
4. It only says clearly better or clearly worse when the change is **at least 5 points and bigger than the noise band**. Otherwise: “no clear change”.
5. This is a **rule we chose for a small pilot**, not a statistical proof. Checks of the same floor on nearby days are not fully independent, so never call it “statistically significant”.

**Example.** Run `python scripts/followup_evidence.py` and read `docs/FOLLOWUP_EVIDENCE.md`: each row shows the displayed score change, the both-bin change, and the noise band. When the both-bin change is smaller than the noise band, the app says **no clear change**, even if the score dropped by 20 points.

**What this means for the pilot:** more checks per week make the noise band smaller. That is one reason the worker page matters: daily staff reports add a check every day.

You can regenerate the example table yourself: `python scripts/followup_evidence.py` writes `docs/FOLLOWUP_EVIDENCE.md`. Every row there is simulated.

The code is in `app/actions.py` (`outcome()` and `check_values()`), and the tests are in `tests/test_outcome.py`.

---

## 7. The collection staff page (worker mode)

**Why it exists.** The person who sorts mixed waste by hand is the one who sees it most, but had no way to report it.

**How the warden sets it up:** Pilot setup → *Collection staff link* → *Create worker link* → *Share on WhatsApp*. *New link* makes the old one stop working. *Turn off* disables it.

**What the worker sees** — no sign-in, no reading needed:

1. Big buttons with the floor names. (The name is read aloud when tapped.)
2. The **green bin** picture and three faces: 😊 साफ़ (clean), 😐 थोड़ा मिला (a few wrong), 😟 पूरा मिला हुआ (mixed).
3. The **blue bin** picture and the same three faces.
4. Optional picture tags for what was wrong: 🛍 plastic in the green bin, 🍛 food in the blue bin, 👜 all in one bag.
5. A red ⚠️ button for glass, blade, needle or unwrapped sanitary waste.
6. A big green ✓ भेजें (Send) button. Then a big ✅ and “धन्यवाद” (thank you).

Every tap is spoken in Hindi by the phone's built-in voice. The 🔊 button reads out the instructions. If the phone has no Hindi voice, it stays silent and still works by pictures.

**Rules built in:**

- Saved as that floor's **collection** check for today. A second report the same day replaces the first (the worker is correcting a mistake).
- Workers see only floor names — no scores, notes, photos or other data.
- At most 120 reports per hour per link.
- The worker cannot pick a date or send extra fields.
- If any report flags a dangerous item, that floor's weekly action becomes **“Make the bins safe to handle”** (shown first, marked *Worker safety*), and the weekly report has a **Dangerous items** column.

**Not yet tested with real staff.** The Hindi wording was written by us and should be checked by a Hindi speaker.

Code: `web/worker.html`, `web/worker.css`, `web/worker.js`; worker endpoints in `app/main.py` (search for “Worker link”); tests in `tests/test_worker.py`.

---

## 8. Run it on your own laptop, step by step

These steps are for Windows. Commands go into **PowerShell** (press Start, type PowerShell, open it).

**Once:**

1. Install **Git**: https://git-scm.com/download/win (keep the default options).
2. Install **Python 3.12**: https://www.python.org/downloads/ — tick **“Add python.exe to PATH”** on the first screen.
3. Accept the GitHub invitation email (or go to https://github.com/notifications).
4. Download the project:
   ```powershell
   cd $HOME\Desktop
   git clone https://github.com/techi101/lane-scorecard.git
   cd lane-scorecard
   ```
   `cd` means “go into this folder”. `git clone` downloads the repo.
5. Set it up:
   ```powershell
   .\setup.ps1
   ```
   This makes the `.venv` folder and installs the Python packages listed in `requirements.txt`. If PowerShell says scripts are blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and try again.

**Every time you want to use it:**

```powershell
.\start.ps1
```

The window prints an address (http://127.0.0.1:8765) and an **access code**. Open the address in your browser and paste the code. Keep the PowerShell window open; press `Ctrl+C` in it to stop. The code is stored in `.local\admin-code.txt` on your laptop only.

**Run the tests:**

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe tests\browser_check.py
```

The first line installs test tools. The second runs 47 automatic checks (expect “47 passed”). The third opens a hidden Microsoft Edge window and clicks through the whole app, saving screenshots in `artifacts\`.

**Run it as an AWS Lambda on your laptop** (no AWS account needed; needs **Docker Desktop**, https://www.docker.com/products/docker-desktop/, started first): follow “Run the Lambda locally” in [AWS.md](AWS.md). Three things trip people up, all explained there: run `scripts\prepare_aws.py` before building, the function is called `Web`, and use `--warm-containers EAGER`.

**Getting your changes to the team:**

```powershell
git pull                      # get everyone else's latest changes first
git add <the files you changed>
git commit -m "Short description of what you changed"
git push
```

Never use `git add .` without first running `git status` and checking the list. Never commit `.local\`, `.env`, codes, or anything from `artifacts\`.

---

## 9. Every folder and file, and what it does

```
lane-scorecard/
├── app/                      Python server code
│   ├── main.py               The web server: every API address, sign-in, checks, cards, worker link, CSV, report
│   ├── scoring.py            Turns ratings into points, floor scores, coverage, hazard counts
│   ├── actions.py            Chooses one next step per floor; the “vs last week” noise check
│   ├── report.py             Builds the printable weekly report for the warden
│   ├── storage.py            Saves and loads data (SQLite locally, DynamoDB on AWS)
│   ├── vision.py             Optional AWS Bedrock photo suggestion (off by default)
│   ├── lambda_handler.py     Lets the same server run inside AWS Lambda
│   └── maintenance.py        Removes expired sessions and abandoned photos
├── web/                      What the browser shows
│   ├── index.html, app.js, style.css    The warden's app
│   ├── worker.html, worker.js, worker.css  The picture-only staff page
│   └── mark.svg              The logo
├── tests/
│   ├── test_workflow.py      Main behaviour: scoring, sign-in, cards, CSV, photos, security
│   ├── test_outcome.py       The “vs last week” noise rules
│   ├── test_worker.py        The staff link and page
│   ├── test_issues.py        Issue tags and the four-part card
│   ├── test_cloud_contracts.py  Checks the AWS code talks to AWS correctly (using fakes)
│   └── browser_check.py      Clicks through the whole app in a real browser
├── scripts/
│   ├── followup_evidence.py  Regenerates docs/FOLLOWUP_EVIDENCE.md (simulated table)
│   ├── prepare_aws.py        Copies app/ and web/ into artifacts/aws-src for AWS packaging
│   ├── validate.py           Runs tests + JavaScript check + AWS template lint
│   ├── doctor.py             Checks your AWS setup before deploying
│   ├── evaluate_photos.py    Measures photo-suggestion accuracy on a labelled photo set
│   └── package_source.py     Makes a source-only zip
├── docs/                     Everything written for humans (this guide, writeup, AWS guide, demo script…)
├── template.yaml             The list of AWS pieces SAM creates
├── deploy.ps1                Stage → check → build → deploy to AWS (asks before creating anything)
├── setup.ps1, start.ps1      Set up and start on Windows
├── run.py, manage.py         Start the server / maintenance commands
└── requirements*.txt         Python packages the project needs
```

---

## 10. Where AWS fits

The hackathon says: *“Your project has to use AWS, and your demo video has to show it.”*

There are two accepted ways:

- **Build It** — run AWS's open-source tools on your laptop. No AWS account. **We can do this today:** `sam build` packages our Lambda, and `sam local start-api` runs it in Docker exactly as AWS would. We have tested the full warden flow and the worker flow this way.
- **Ship It** — deploy to real AWS within the free tier and give a working public address. **This needs an AWS account**, and it is what the strongest rival projects have.

What `template.yaml` creates when deployed:

| AWS piece | What it does for us |
|---|---|
| API Gateway | Gives the app its public web address |
| Lambda | Runs `app/` when someone opens a page or saves a check |
| DynamoDB | Stores floors, checks, cards, worker links |
| S3 | Stores bin photos privately |
| EventBridge | Makes the weekly scorecards automatically |
| CloudWatch | Keeps logs so we can show requests happening |
| Bedrock (optional) | Suggests a rating from a photo; a person always decides |

**Honest status (9 Oct 2026):** deployed. The live site is https://ss9ib2qbek.execute-api.us-east-1.amazonaws.com (stack `lane-scorecard` in us-east-1). Health reports DynamoDB storage, sign-in works, and logged-out requests are refused. Bedrock (AI photo suggestions) is switched off, so never say AI is used. The live operator code is in `.local/operator-code.txt` on the laptop that deployed it — never in the repo or chat.

**Redeploy after code changes:** `scripts\prepare_aws.py`, then `sam build --use-container`, then `sam deploy` with the `lane` profile. Run the tests first.

---

## 11. The hackathon: rules, judging and our risks

**Dates:** online 8–11 October 2026. Submit on Sunday 11 October; aim for **4 PM**, not the last minute. Check the event page again for the exact time.

**Judging (from the event page):**

1. Idea and impact — does it fix a real environmental problem, and what changes for people?
2. Built on AWS — mandatory to win a prize.
3. Design and usability — would someone outside the team know what to do?
4. Execution — does it work?
5. The demo video — three minutes: what it does, who it is for, where AWS fits.

**What we must submit:** a public repository, a demo video (YouTube, public or unlisted; check it opens when signed out), a short writeup including the list of AI tools used, through the submission form.

**Our biggest risk — read this.** The rules say: *“If you began the project before the hackathon opened, it does not qualify, even if you rewrote it,”* and a repository whose history does not match the event dates disqualifies the whole team. This project's code was started at about **02:50 AM IST on 8 October**; the event opened at **08:00 AM IST** that morning. We have written to the organisers. Until we have a **written** answer that clearly allows it, treat the entry as at risk. We never backdate commits or hide the start time — `docs/BUILD_RECORD.md` and the writeup state it openly.

---

## 12. The 3-minute video plan

The detailed script is in [DEMO_SCRIPT.md](DEMO_SCRIPT.md). The story in one line:

> “The person who sorts our mixed waste by hand can now report it without reading — and the warden finally learns whether the fix worked.”

1. **0:00–0:20** — the bins and the problem.
2. **0:20–0:55** — a housekeeping worker (with permission) using the picture page; let the Hindi voice be heard.
3. **0:55–1:50** — the warden's dashboard, a scorecard in Hindi.
4. **1:50–2:15** — the weekly plan: a worker-safety card, a “no clear change” card, and why we refuse to over-claim.
5. **2:15–2:40** — AWS: the real console if deployed; otherwise `sam build` and `sam local` with the Lambda in Docker, said honestly as a local run.
6. **2:40–3:00** — what we measured, and the limits.

Keep the **DEMO** label visible whenever demo data is on screen.

---

## 13. What is done and what is left

**Done and tested:**

- Warden app: floors, checks, scores, coverage, trends, scorecards (English/Hindi), weekly plan, report, CSV, corrections.
- Follow-up check with the noise band.
- Worker page with Hindi voice and danger button; worker-safety action.
- Security: sign-in, private links, rate limits, no student names.
- 47 automatic tests pass; real-browser check passes on desktop and phone sizes.
- AWS template valid; Lambda runs locally with SAM and Docker.

**Left, and who can do it:**

| Task | Needs |
|---|---|
| Written ruling from organisers on the start time | Team lead |
| AWS account so we can deploy a live address | Whoever owns the account |
| Talk to 1–2 housekeeping staff, with permission; test the worker page; film it | Anyone on the team |
| Real checks on 2–3 floors with the warden's permission | Anyone on the team |
| Check the Hindi wording | A Hindi speaker |
| Record and edit the video | Team |
| Make the repo public and submit the form | Team lead, after the ruling |

---

## 14. Questions judges or interviewers may ask, with answers

**Q: Isn't this just a dashboard?**
A: No. It closes the loop: record → action → check whether the action worked next week, and it gives sanitation staff a way to report without reading.

**Q: Why not use AI to rate bins from photos?**
A: We built it as an option with AWS Bedrock, but a person always makes the final rating. A wrong automatic rating would blame the wrong floor. We would turn it on only after testing it on labelled real photos.

**Q: How do you know the score really changed?**
A: We compare only checks where both bins were seen, and call a change clear only when it is at least 5 points and bigger than two standard errors of the difference between weeks. With one check a day, the weekly number often moves by about 30 points with no real change, so most single weeks show “no clear change”. We say openly that this is a pilot rule, not a statistical proof.

**Q: Why tags instead of free text?**
A: Research on feedback (for example UNDP's trial in Bhutan, as reported) points to specific feedback — what exactly went wrong and why — working better than generic tips. Three picture tags make that possible without reading, and the card text is a fixed, reviewed template, so nothing is invented.

**Q: Why should a worker use this?**
A: It takes four taps, needs no reading, speaks Hindi, and the danger button turns their safety problem into the warden's top action. We have not tested it with real staff yet — that is our next step.

**Q: What about privacy?**
A: No student names. Floor labels only. Scorecard and worker links are random and can be revoked. Reports exclude notes and photos.

**Q: Where exactly is AWS used?**
A: Lambda runs the server, API Gateway gives the address, DynamoDB stores data, S3 stores photos, EventBridge runs the weekly job, CloudWatch keeps logs, and Bedrock is optional. It is deployed on AWS at https://ss9ib2qbek.execute-api.us-east-1.amazonaws.com; health shows DynamoDB storage. Bedrock is built but switched off.

**Q: What would you build next?**
A: Amazon Polly for clearer Hindi voice on every phone; offline saving for basements with no signal; a picture poster with a QR code at each bin for students; a longer pilot.

**Q: Did you use AI tools?**
A: Yes, and we list them: OpenAI Codex for most of the implementation, Claude / Claude Code for research, planning, the follow-up check, the worker page and the local AWS run.

---

## 15. What we must never claim

- That waste reduced, or that scorecards caused any change. We have no real pilot data yet.
- That it is deployed on AWS, until it is.
- That workers or students tested it, until they have.
- That the photo AI is accurate.
- That the project started after kickoff.
- Anything shown in the demo workspace as real.

---

## 16. When something breaks

| Problem | Fix |
|---|---|
| `python` is not recognised | Reinstall Python and tick “Add python.exe to PATH”, then open a new PowerShell. |
| “running scripts is disabled” | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then `Y`. |
| Forgot the access code | Look in `.local\admin-code.txt` inside the project folder. |
| Port 8765 already in use | Another copy is running. Close that PowerShell window, or restart the laptop. |
| Browser test says Playwright needs browsers | Make sure Microsoft Edge is installed (it is on Windows by default). |
| `sam local` gives “Internal server error” | Docker Desktop is not running, or you skipped the env file. See [AWS.md](AWS.md). |
| Changes don't show up in `sam local` | Run `scripts\prepare_aws.py` and `sam build` again. |
| `git push` is rejected | Run `git pull` first, then push again. |

If you are stuck, write down the exact command you ran and the exact error text, and send both to the team.
