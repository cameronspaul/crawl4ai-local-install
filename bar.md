Deploy 15 parallel web search tooling to search live job boards and direct employer portals for entry-level and experienced bar roles fitting the criteria below. Do not return talent pools or "register interest" listings—only active, immediate-hire vacancies posted within the last 7 days. Use @readme.md for the webscraping tools.

### Candidate Profile Context
* **Experience:** Practical, high-volume pub experience (cellar maintenance, till balancing, peak-time line service, keyholding) at PJFRFC and The Garibaldi. Hands-on EPOS and local network troubleshooting background.
* **Constraints:** 23-year-old male, non-driver. Relies strictly on direct train/Thameslink routes out of South London (Coulsdon South / East Croydon).
* **Goal:** Save a minimum total net take-home pay of £4,500 prior to a scheduled flight departure on December 27, 2026. (Plan is to resign on or before December 24–26, 2026, regardless of contract length).

### Targeted Role Criteria

* **Target Roles:** Bar Staff, Bartender, Pub Team Member, Taproom Assistant, Event Bar Crew, or Cellar/Floor Runner. 
* **Excluded Roles:** 
  * Senior positions (e.g., Head Bartender, General Manager, Assistant Manager).
  * High-end craft cocktail / mixologist roles requiring specialized menu expertise.
* **Earnings, Pay Floor & Contract Flexibility:**
  * **Pay Rate Handling:** If a listing states hourly pay, use that rate. If no pay rate is explicitly stated in the listing, assume the statutory minimum threshold of **£12.71/hr**.
  * **Contract Term Flexibility:** Permanent roles, part-time roles, or contracts extending into 2027 are fully acceptable (candidate will give notice and resign before departure on December 27, 2026).
  * **Net Requirement:** The total estimated net take-home pay (after UK Income Tax and Class 1 National Insurance) MUST exceed **£4,500** based on expected weekly hours worked between the start date and December 24, 2026. Discard any role where remaining hours/weeks cannot hit £4,500 net.
* **Shifts & Weekly Hours:**
  * No shift time or finish time restrictions (open to lates, early opens, split shifts, or double turns).
  * Target volume: 30+ hours per week (or flexible part-time hours where total hours prior to Dec 27 meet the net target).
* **Location & Access:** Central London (Zones 1–3) or South London directly accessible via train/Thameslink from Coulsdon South or East Croydon (e.g., London Bridge, Blackfriars, Victoria, Clapham Junction, Croydon hubs).

---

### Mandatory JSON Persistence (Subagent Instruction)

To prevent loss of findings during execution:

* **Directory Setup:** Verify or create a directory named `jobs/` in the working directory.
* **Save Condition:** For every role meeting 100% of the criteria, write a `.json` file to `jobs/` before returning.
* **Naming Scheme:** `jobs/agent_{agent_id}_{sanitized_role_title}.json`
* **Filtering:** Only write records for validated roles that meet all pay, location, and earnings targets.
* **JSON Structure:**

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