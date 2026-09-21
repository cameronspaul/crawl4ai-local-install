Deploy 15 parallel subagents using the web search tooling in `@README.md` and `@job-search-skill.md` (don't use native websearch) to search live job boards (DO NOT USE THESE AS WEB SCRAPING DOESN'T WORK - Indeed, LinkedIn, Reed) and direct employer recruitment portals. Subagents should search strictly for **Christmas seasonal, festive temp, and holiday peak roles**, returning when they have five fitting roles (or fewer if genuinely unavailable).

### Mandatory JSON Persistence (Subagent Instruction)

To prevent findings from being lost or truncated during subagent context handoff back to the orchestrator:

* **Directory Creation:** Ensure a directory named `jobs/` exists in the current working directory.
* **Saving Recommended Roles:** Every subagent that identifies any role meeting 100% of the criteria **MUST save an actual `.json` file** inside the `jobs/` directory before returning.
* **Naming Scheme:** Save as `jobs/agent_{agent_id}_{sanitized_role_title}.json` (or `jobs/agent_{agent_id}_matches.json` containing an array of all validated roles found by that subagent).
* **Only Recommended Listings:** Do **not** dump rejected or discarded roles into these files. Only write roles that strictly meet the £4,500 net target, location/transit constraints, and Christmas shift window.
* **JSON Schema:** Each saved role must conform to:

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
    "exceeds_threshold": true
  }
}

```

---

### Context

Flying to South East Asia on December 27, 2026. Flights are paid for, but I currently have £0 for the trip. I need to make at least £5,000–£6,000 gross to net at least **£4,500** before departing.

**Background:**
Experienced with high-volume pub/bar shifts, cellar management, keyholding, and till balancing (PJFRFC and The Garibaldi). Strong tech problem-solving background (troubleshooting EPOS, local networks, full-stack software development, hardware repairs, Windows/Linux sysadmin, Python/Bash scripting). Looking for fast-hiring seasonal roles where high energy, basic tech literacy, or frontline reliability gets me hired immediately (e.g., Christmas retail, festive stock replenishment, seasonal warehouse floor, holiday event staffing, Christmas pop-ups, temp admin). Basically just any temp stuff that goes around which any normal basic human can do. 

**Constraints:** Age 23, Male, **cannot drive** (relying on public transport from Coulsdon South / East Croydon).

---

### Search Focus & Criteria

Find currently active **Christmas/Seasonal/Festive temporary** roles running through December 24–26, 2026. Target immediate-hire holiday peak positions using broad category search terms (e.g., *"Christmas retail assistant"*, *"festive team member"*, *"seasonal stock assistant"*, *"Christmas event staff"*, *"temp holiday admin"*). If the roles say that they end in like January and stuff, that's fine, because we can just leave beforehand anyway. 

#### Criteria Rules:

* **Role Types (Strictly Christmas & Seasonal):** Focus exclusively on Christmas temp roles, seasonal retail/stock ops, festive hospitality/events, temporary winter warehouse/fulfillment, and holiday peak admin. Prioritize mass-hire seasonal campaigns. No generic long-term perm roles unless structured as a fixed-term seasonal contract.
* **Pay Floor & Earnings Target (Strict):**
* Minimum pay rate: **£12.71/hr**.
* **Minimum Net Take-Home Requirement:** ONLY return jobs where the realistic total net take-home pay (after estimated UK income tax and NI deductions) will exceed **£4,500** total before December 26, 2026. Discard if total hours/weeks cannot hit £4,500 net.


* **Working Hours & Shift Window (Strict):**
* **No night shifts** or overnight stock replenishment.
* **Earliest shift start:** 08:00 AM (earliest rail arrival into London).
* **Latest shift end:** 22:00 (10:00 PM) hard finish (rail transit back to Coulsdon/South London).
* Shifts must fit entirely within **08:00–22:00**.
* **No delivery driver/courier jobs.**


* **Timeline & Dates:** Seasonal start dates between **immediate start and early October 2026**, with fixed contract end dates between **December 24–26, 2026**.
* **Location & Commute:** Central London (Zones 1–3) or South London (direct via Thameslink/Southern rail out of Coulsdon South / East Croydon, e.g., London Bridge, Blackfriars, Victoria, Croydon hubs).
* **Volume:** 30–40+ contracted/expected weekly hours during the Christmas peak (or high-volume seasonal agency platforms).
* **Live Listings Only:** Must be **actively hiring with open applications** posted within the last 7 days. Do NOT return talent pools, "register interest" alerts, or expired Christmas postings.

---

### Required Output Format

For each verified, live seasonal role found, double-check all strict criteria first. In addition to saving the `.json` file to `jobs/`, output:

1. **Job Title & Company / Agency** (Highlighting seasonal/Christmas context)
2. **Hourly Pay Rate** (including any festive peak bonuses or Sunday rates)
3. **Location / Station Accessibility**
4. **Shift Hours & Commute Fit** (explicitly confirm the 07:00–22:00 window fit)
5. **Seasonal Contract Dates / Weekly Hours** (Start date through Dec 24–26)
6. **Direct Application Link**
7. **JSON File Path** (confirming where the record was saved)
8. **Net Earnings Calculation:** Full breakdown of gross earnings to net take-home pay (factoring in realistic tax/NI deductions across the remaining contract weeks) explicitly proving total earnings exceed £4,500.