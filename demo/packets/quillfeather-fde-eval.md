# Packet: Quillfeather Labs / Forward Deployed Engineer, Evaluation Tooling

*(Fictional demo packet. Company, role and candidate are invented.)*

## Role
- company: Quillfeather Labs
- title: Forward Deployed Engineer, Evaluation Tooling
- ats: greenhouse
- slug: quillfeather

## Apply URL
https://boards.example.com/quillfeather/jobs/4401

## What this team wants
The posting stresses turning vague customer complaints into measurable checks, and time on
site with customers. Lead with the evaluation harness and the customer-facing part of it.

## Form fields
| Field | Value |
|---|---|
| Will you now or in the future require visa sponsorship? | Yes |
| What is the earliest you could start? | Within 30 days of an offer. |
| Location | London (relocating from Springfield) |

## Cover letter
*(311 words)*

Dear Quillfeather Labs hiring team,

I'm applying for the Forward Deployed Engineer role on Evaluation Tooling. For the last three years I've built the evaluation harness behind a customer support assistant at Example Studio Co., and the part of that job I'd most like to keep doing is sitting with a customer until their own idea of a good answer is written down as a test.

The harness started as a spreadsheet of forty questions. It's now a versioned suite of about two thousand graded cases that runs on every prompt or model change. Each case stores the input and the expected behaviour with the reason a reviewer gave for its grade. When a release regressed, the team could see which customer workflow broke before anyone filed a ticket. I wrote the grading rubric with the support leads rather than for them, which is why they still maintain it without me.

Forward deployed work suits how I like to operate. I'd rather spend a week inside one customer's data than a month on a generic dashboard. On my last engagement I flew out to a regional office, watched agents use the assistant for two days and came back with eleven failure patterns nobody had logged. Seven of them became permanent test categories.

I also care about the dull parts that make evaluation trustworthy. Graders drift, so I keep a small human-labelled anchor set and track agreement over time. Prompts change silently, so every run stores the exact prompt and model version next to its scores.

Your posting asks for someone who can turn ambiguous customer complaints into measurable checks and ship the tooling that runs them. That's the work I've been doing, and I'd like to do it with a team whose product is evaluation itself.

Thanks for reading. I'm happy to walk through the harness design in detail.

Robin Example

## Likely supplementary questions + answers

### 1. Why Quillfeather Labs? *(~90 words)*
Because evaluation is your product and not a side project. In my current job I've had to argue for every hour spent on test suites, and I'd like to work somewhere that treats a graded case as a deliverable. Your customers are teams who already know their assistant fails in ways they can't name yet. Helping them name those failures and then measure them is the part of my job I'd keep if I could only keep one.

### 2. Describe an evaluation system you built end to end. *(~80 words)*
The support assistant harness at Example Studio Co. I collected real tickets with the support leads and turned each into a graded case with a written reason. A nightly run scores every prompt and model change against about two thousand cases, with a human-labelled anchor set to catch grader drift. Regressions show up by customer workflow, so the team knows who is affected before shipping.

## Resume to upload
`demo/resume/robin-example-resume.txt`

## Unverified claims I avoided
- No percentage improvement for the harness: none was measured.
- No team size: the candidate had no direct reports.

## Revision log
- 2026-09-30: cut a third-paragraph list of three to two items (lint: tricolon).
