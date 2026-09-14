Deploy 15 parallel subagents using the web search tooling in @README.md (don't use the native websearch) to search live job boards (DO NOT USE THESE AS WEB SCRAPING DOESN'T WORK - Indeed UK, Totaljobs, LinkedIn) and direct employer portals. Sub agents should only return when they have five jobs that fit or if they genuinely don't then it's Okay, return what they have, even if it's zero, that's fine.

### Mandatory JSON Persistence (Subagent Instruction)

To prevent findings from being lost or truncated during subagent context handoff back to the orchestrator:

* **Directory Creation:** Ensure a directory named `jobs/` exists in the current working directory.
* **Saving Recommended Roles:** Every subagent that identifies any role meeting 100% of the criteria **MUST save an actual `.json` file** inside the `jobs/` directory before returning.
* **Naming Scheme:** Save as `jobs/agent_{agent_id}_{sanitized_role_title}.json` (or `jobs/agent_{agent_id}_matches.json` containing an array of all validated roles found by that subagent).
* **Only Recommended Listings:** Do **not** dump rejected or discarded roles into these files. Only write roles that strictly meet the £4,500 net target, location/transit constraints, and shift window.
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

Here's a brief summary about me. Don't take this as gospel for finding exact roles to that. It's just so you have some context.

"
Flying to South East Asia on the twenty seventh of december twenty twenty six. I already have paid for the ticket, however at the moment we have zero pounds to go out there with. I want to go for roughly three months and in my mind I want to make at least five to six thousand pounds.

My background.
With extensive experience managing high-volume shifts, cellar operations, and till balancing as a trusted keyholder at PJFRFC and The Garibaldi, I bring practical, fast-paced frontline reliability backed by serious technical depth. Alongside handling busy floor service and customer rushes, I have routinely acted as the on-site technical contact—troubleshooting EPOS till hardware, digital booking platforms, and local network issues to keep operations running smoothly. Beyond the bar, I am an advanced technical problem solver with a background spanning full-stack software development, hardware repairs, system administration across Windows and Linux, and automation scripting in Python and Bash. This combination allows me to stay calm and customer-focused under pressure while quickly mastering, maintaining, and debugging any digital systems or proprietary tech put in front of me. Also on the tech tangent, I'm like the hub of family and friends where they come to me if they have any single tech problem with anything, phones, TVs, printers, literally everthing. Basically my ego makes me think that I can do any sort of temp administrator jobs in like offices where you just sort of sit at a computer and just crunch numbers all day. as the ego thinking that just supermarket stuff as well is just really easy, As well as like a worker in a clothes shop where you just sort of do stock and stuff. etc

I can NOT drive, im 23, male.

"

Find currently active, entry-level roles available through December 27, 2026. Prioritize seasonal, temporary, and fixed-term contracts, but also include part-time and permanent positions (I will just put in my leave for the 27th December 2026) vacancies meeting these criteria or stuff around my description:

### Criteria

* **Role Types:** Target entry-level, no-experience roles—such as retail, hospitality, admin, or seasonal work—using broad category terms (e.g., "supermarket assistant") rather than company-specific queries to avoid redundant searches and save compute. NO WAREHOUSE
* **Pay Floor & Earnings Target (Strict):**
* Anything above £12.71/hr.
* **Minimum Net Take-Home Requirement:** ONLY return jobs where the realistic total net take-home pay (after estimated UK income tax and National Insurance deductions) will exceed **£4,500** between the start date and 24–26 December 2026. If the combination of hours and weeks remaining cannot hit £4,500 net, discard the listing.
* **Working Hours & Shift Window (Strict):**
* **No night shifts.**
* **Earliest shift start:** 07:00 AM (due to earliest inbound train arrival into London).
* **Latest shift end:** 22:00 (10:00 PM) hard finish (due to return rail transit limits back to South London/Coulsdon).
* Shifts must fall entirely within the **07:00–22:00 window**. Filter out any roles requiring overnight turns, 06:00 starts, or closes past 22:00.
* **Timeline & Start Date:** Start date is flexible: **immediate start up through early October 2026**. Fixed contract end date on or before **December 24–26** (hard stop: departure flight on December 27).
* **Location & Commute:** Central London (Zones 1–3) or South London (readily accessible via Thameslink/Southern rail lines out of Coulsdon South / East Croydon, e.g., London Bridge, Blackfriars, Victoria, Croydon hubs).
* **Volume:** Target 30–40 contracted hours per week (or high-volume agency shift platforms).
* **Listings:** Don't give me companies or jobs that are NOT listing yet (e.g., M&S "register your interest" / talent pool alerts). Must be actively hiring with immediate open applications. As well as within 7 days eg 1 week of being posted.

### Required Output Format

For each verified, live role found, Check first to see if all the criteria have been met. Otherwise don't you dare show it. In addition to saving the `.json` file to `jobs/`, output:

1. **Job Title & Company / Agency**
2. **Hourly Pay Rate** (and shift differentials/overtime if applicable)
3. **Location / Station Accessibility**
4. **Shift Hours & Commute Fit** (explicitly confirm shift pattern fits within the 07:00–22:00 bracket)
5. **Contract Dates / Expected Weekly Hours**
6. **Direct Application Link**
7. **JSON File Path** (confirm the filepath where the structured record was written)
8. **Net Earnings Calculation:** Full breakdown of gross earnings to net take-home pay (factoring in realistic tax/NI deductions across the remaining weeks) explicitly proving the total exceeds £4,500.