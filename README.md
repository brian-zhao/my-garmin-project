# Garmin Running Analytics

Analyse your running economy across shoes and pace zones using data from
Garmin Connect. Tracks stride length, vertical oscillation, and vertical
ratio — the key metrics for understanding how efficiently you run.

---

## What does it do?

- Connects to your Garmin account and pulls all your running data
- Groups your laps into **pace zones** (easy, tempo, threshold, race pace, etc.)
- For each shoe, calculates your **running economy** per zone:
  - **Vertical ratio** — how much energy goes up vs forward *(lower = better)*
  - **Stride length** — how far each stride carries you
  - **Vertical oscillation** — how much you bounce
- Ranks your shoes so you can see which ones make you run most efficiently

---

## Requirements

- **Python 3.9 or higher** — [download here](https://www.python.org/downloads/)
- A **Garmin Connect account** with activity history
- A running watch that records **running dynamics** (stride, cadence, vertical)

---

## Getting started (first time only)

### Step 1 — Download the project

Save all the project files into a folder on your computer, e.g.:

```
~/garmin-analytics/
```

### Step 2 — Open a terminal

- **Mac**: Press `Cmd + Space`, type `Terminal`, press Enter
- **Windows**: Press `Win + R`, type `cmd`, press Enter

Navigate to the project folder:

```bash
cd ~/garmin-analytics
```

### Step 3 — Run setup

```bash
python setup.py
```

This will:
1. Install the required Python package (`garminconnect`) automatically
2. Ask for your Garmin email and password and save them locally
3. Test your login to make sure everything works

> **MFA / Two-factor authentication:** If your Garmin account has 2FA enabled,
> you will be prompted to enter a one-time code during the first login.
> After that, a token is saved locally so you won't need to log in again.

---

## Running the app

Every time you want to use the app, just run:

```bash
python run.py
```

You'll see a simple menu:

```
  🏃 Garmin Running Analytics
  ====================================================

    1.  Refresh data from Garmin
    2.  Top shoes by pace zone
    3.  Compare specific shoes
    0.  Exit
```

---

## Menu options

### Option 1 — Refresh data from Garmin

Fetches all your activity data from Garmin Connect and saves it to
`gear_analysis.csv`. **Run this first** before using options 2 or 3.

This takes **1–3 minutes** depending on how many activities you have.
You only need to re-run this when you want to include new activities.

---

### Option 2 — Top shoes by pace zone

Shows your best shoes for each pace zone, ranked by running economy.

You will be asked:
- **Minimum laps** — only include shoes with enough data (default: 10 laps)
- **Number of shoes** — how many top shoes to show per zone (default: 3)

**Example output:**

```
  Zone 5 (3:44–4:03)
  #   Shoe                  Vert Ratio   Laps  Avg Pace  Stride (cm)  Vert Osc (cm)
  ----------------------------------------------------------------------------------
  1   Superblast 2               6.80%     42      3:52        145.7           9.87
  2   Boston 13                  6.81%     32      3:53        142.4           9.70
  3   Vaporfly3                  7.00%     49      3:50        145.1          10.30
```

---

### Option 3 — Compare specific shoes

Compare a set of shoes you choose, side by side across all pace zones.

You will be asked:
- **Which shoes** to compare (pick from a numbered list)
- **Data source:**
  - *Saved data* (fast — uses `gear_analysis.csv`)
  - *Live from Garmin* (slower — lets you filter by date, e.g. last 3 months)

If you choose live data, you can optionally enter a start date like `2026-02-01`
to only include recent activities.

---

## Pace zones explained

| Zone | Pace range | Typical use |
|------|-----------|-------------|
| Zone 1 | Slower than 5:15 /km | Easy / recovery runs |
| Zone 2 | 4:39 – 5:15 /km | Aerobic base |
| Zone 3 | 4:17 – 4:39 /km | Tempo runs |
| Zone 4 | 4:03 – 4:17 /km | Threshold |
| Zone 5 | 3:44 – 4:03 /km | Race pace |
| Zone 6 | Faster than 3:44 /km | Intervals / sprints |

---

## Understanding vertical ratio

**Vertical ratio** is the key running economy metric in this app.

It measures how much of your movement is vertical (bouncing) compared to
your stride length. A lower number means more of your energy is going
forward rather than up and down.

- **Good range**: 6–8%
- **Lower is better** — elite runners typically run at 6–7% at race pace
- The same shoe will show a lower vertical ratio at faster paces — this is normal

---

## The data file — gear_analysis.csv

After running option 1, a file called `gear_analysis.csv` is saved in the
project folder. You can open this in **Excel** or **Google Sheets** for your
own analysis.

| Column | What it means |
|--------|--------------|
| `gear` | Shoe name |
| `zone` | Pace zone |
| `laps` | Number of laps recorded in this zone |
| `total_distance_km` | Total distance in this zone |
| `avg_pace` | Average pace (min:sec per km) |
| `avg_stride_length_cm` | Average stride length |
| `avg_vertical_osc_cm` | Average vertical oscillation |
| `avg_vertical_ratio_pct` | Average vertical ratio (running economy) |

---

## Troubleshooting

**"No .env file found"**
→ Run `python setup.py` first.

**"429 Too Many Requests"**
→ Garmin has rate-limited your account. Wait 30–60 minutes and try again.
   This usually happens after several failed login attempts.

**"No data found — run Refresh Data first"**
→ Select option 1 from the menu to fetch your data before running analyses.

**Login prompts for MFA code**
→ Enter the code sent to your email or phone. After this, a token is saved
   and you won't be asked again until the token expires (~30 days).

**A shoe is missing from the list**
→ The shoe may not be registered in Garmin Connect, or it may be listed
   under a different name. Check your gear at connect.garmin.com/gear.

---

## File overview

```
garmin-analytics/
├── run.py                 ← START HERE — the main app
├── setup.py               ← First-time setup wizard
├── garmin_auth.py         ← Handles Garmin login (don't edit)
├── gear_enum.py           ← Your gear names and IDs (don't edit)
├── interval_analysis.py   ← Core data analysis engine (don't edit)
├── gear_ranking.py        ← Ranking logic (don't edit)
├── gear_analysis.csv      ← Generated data file (open in Excel)
├── .env                   ← Your credentials (never share this file)
└── .gitignore             ← Keeps credentials out of version control
```

---

## Privacy

Your Garmin credentials are stored **only on your computer** in the `.env`
file and never sent anywhere other than Garmin's own servers. The token
cache in `~/.garminconnect` also stays on your machine.
