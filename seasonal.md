Deploy 15 parallel subagents using the web search tooling in `@README.md` and `@job-search-skill.md` (don't use native websearch) to search live job boards (DO NOT USE THESE AS WEB SCRAPING DOESN'T WORK - Indeed, LinkedIn, Reed) and direct employer recruitment portals. Subagents should search strictly for **Christmas seasonal, festive temp, and holiday peak roles**, returning when they have five fitting roles (or fewer if genuinely unavailable).

---

### Mandatory JSON Persistence & Listing Verification (Subagent Instruction)

To prevent findings from being lost, truncated, or pointing to useless generic portals:

1. **Directory Creation:** Ensure a directory named `jobs/` exists in the current working directory.
2. **STRICT Direct Listing Requirement (CRITICAL):**
   * **No Generic Pages:** Do **NOT** return or save generic corporate `/careers`, landing pages, or search form URLs (e.g., `company.com/careers` or `jobs.company.com/search`).
   * **Verifiable Individual Role:** The `application_url` MUST point directly to a specific, live job posting with an active **"Apply Now"** button or specific role requisition ID.
   * **Validation Step:** Before saving any listing, the subagent **MUST inspect the target page content** to verify that:
     - A real, active job title and description are rendered on the page.
     - The job was posted within the **last 7 days** relative to the current date. Discard any listings older than 7 days, expired pages, or general search redirects.
3. **Saving Recommended Roles:** Every subagent that identifies any role meeting the flexible criteria **MUST save an actual `.json` file** inside the `jobs/` directory before returning.
4. **Naming Scheme:** Save as `jobs/agent_{agent_id}_{sanitized_role_title}.json` (or `jobs/agent_{agent_id}_matches.json` containing an array of all validated roles found by that subagent).
5. **Only Recommended Listings:** Do **not** dump clearly irrelevant roles (e.g., driver jobs, overnight shifts, perm roles) into these files.
6. **JSON Schema:** Each saved role must conform to:

```json
{
  "job_title": "string",
  "company_or_agency": "string",
  "hourly_rate_gbp": 0.00,
  "location": "string",
  "nearest_station": "string",
  "shift_hours": "string",
  "contract_type": "string",
  "expected_weekly_hours": 0,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "application_url": "string",
  "date_posted": "YYYY-MM-DD",
  "net_earnings_calculation": {
    "total_weeks": 0,
    "gross_total_gbp": 0.00,
    "estimated_tax_ni_deductions_gbp": 0.00,
    "net_take_home_gbp": 0.00,
    "high_earning_potential": true
  }
}

```

---

### Context

Flying to South East Asia on December 27, 2026. Flights are paid for, but I currently have £0 for the trip. I need to earn as much gross income as possible to target **£4,500 net** before departing.

**Background:**
Experienced with high-volume pub/bar shifts, cellar management, keyholding, and till balancing. Strong tech problem-solving background (troubleshooting EPOS, local networks, full-stack software development, hardware repairs, Windows/Linux sysadmin, Python/Bash scripting). Looking for fast-hiring seasonal roles where high energy, basic tech literacy, or frontline reliability gets me hired immediately (e.g., Christmas high-volume retail, festive stock replenishment, seasonal warehouse floor, holiday event staffing, Christmas pop-ups, temp admin).

**Constraints:** Age 23, Male, **cannot drive** (relying on public transport from Coulsdon South / East Croydon).

---

### Search Focus & Criteria

Find currently active **Christmas/Seasonal/Festive temporary** roles running through December 24–26, 2026. Target immediate-hire holiday peak positions using broad category search terms (e.g., *"Christmas retail assistant"*, *"festive team member"*, *"seasonal stock assistant"*, *"Christmas event staff"*, *"temp holiday admin"*). If roles say they end in January or later, that is fine (can leave early).

#### Criteria & Tolerance Rules (CRITICAL FOR AGENT EVALUATION):

* **Recency & Post Date (STRICT 7-DAY CUTOFF):**
* **MUST BE POSTED WITHIN THE PAST 7 DAYS.**
* Disqualify and discard any job listing where the `date_posted` is older than 7 days from today.


* **NO Sales-Focused or Commission Roles (STRICT BAN):**
* **EXCLUDE ALL** roles driven by sales targets, quotas, upsells, or commission-based pay structure.
* **EXCLUDE ALL** luxury/high-end retail sales positions requiring consultative selling (e.g., jewellery stores, luxury fashion/watches, high-end cosmetics, perfume pushers).
* **Target Instead:** High-volume operational roles, general supermarket/high-street floor assistance, till operation, stock replenishment, warehouse/sorting floor, bar/event staffing, or temp admin.


* **Shift Times & Unspecified Hours (IMPORTANT):**
* Target daytime shifts fitting roughly within **07:30 to 22:30**.
* **Assume Fit Unless Stated:** If a job listing does *not* explicitly state exact shift start/end times, **DO NOT DISCARD IT**. As long as it is a standard daytime retail, events, admin, or floor role (and NOT explicitly labeled as "night shift" or "overnight stock"), assume it fits the required transit window and include it.
* Disqualify ONLY if the listing explicitly mandates overnight shifts (e.g., 22:00–06:00) or driving/deliveries.


* **Pay Floor & Earnings Calculation:**
* Minimum pay rate: **£12.71/hr**.
* **Flexible Earnings Target:** Calculate the estimated total net take-home pay for the duration of the role. Do **NOT** discard good seasonal roles simply because a single role's base hours fall short of £4,500 net. Include any role that pays £12.71/hr+ with good hours (30–48+ hrs/week) as a viable foundation, and flag whether high hours/overtime can push earnings toward the target.


* **Start Dates:**
* Accept start dates from **immediate start through mid-November 2026**. Do NOT restrict search strictly to September/October starts if a strong November Christmas peak campaign is hiring now.


* **Location & Transit:**
* Central London (Zones 1–3) or South London accessible via Thameslink / Southern rail out of Coulsdon South or East Croydon (e.g., London Bridge, Blackfriars, Victoria, Croydon, Redhill, Gatwick corridor).


* **Live & Direct Postings Only:**
* Must be **actively hiring with open applications** posted within the last 7 days.
* ABSOLUTELY NO generic "join our talent pool" pages, "create job alert" forms, expired listings, dead links, or overall recruitment homepages.



---

### Required Output Format

For each verified seasonal role found, output:

1. **Job Title & Company / Agency** (Highlighting seasonal/Christmas context)
2. **Hourly Pay Rate** (including any festive peak bonuses or Sunday rates)
3. **Location / Station Accessibility**
4. **Shift Hours & Commute Fit** (Note exact times if listed; if times are unlisted, state *"Unspecified daytime hours – assumed fit"*).
5. **Seasonal Contract Dates / Expected Weekly Hours**
6. **Direct Application Link** (Must lead directly to the individual role listing, not a hub/search page)
7. **JSON File Path** (confirming where the record was saved)
8. **Net Earnings Calculation:** Estimated gross earnings to net take-home pay across the contract weeks, confirming whether it reaches or contributes significantly toward the £4,500 target.