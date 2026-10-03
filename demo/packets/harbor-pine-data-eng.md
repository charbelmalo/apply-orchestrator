# Packet: Harbor & Pine Analytics / Senior Data Engineer

*(Fictional demo packet. This one deliberately contains a claim the profile rules out,
so the demo shows the truthfulness guardrail blocking it before any browser opens.)*

## Role
- company: Harbor & Pine Analytics
- title: Senior Data Engineer
- ats: lever
- slug: harbor-pine

## Apply URL
https://careers.example.com/harbor-pine/l1/apply

## Form fields
| Field | Value |
|---|---|
| Location | Berlin (relocating from Springfield) |

## Cover letter
*(245 words)*

Dear Harbor & Pine Analytics hiring team,

I'm applying for the Senior Data Engineer role on the Data Platform team in Berlin. During my PhD I designed streaming pipelines for sensor data, and since then I've spent six years building the batch and streaming jobs that feed analytics and model training at Example Studio Co.

My current pipelines move about four terabytes a day from event logs into a warehouse that analysts query directly. I rebuilt the ingestion layer last year after a schema change upstream silently dropped a column for nine days. The fix wasn't clever. Every source now has a contract with typed fields and a test that fails loudly when a producer changes shape. Since then we've caught fourteen breaking changes before they reached a report.

I like data work that ends in someone trusting a number. Before I hand over a table I write down where each column comes from and what would make it wrong. Analysts read those notes more often than the reports themselves.

Your posting mentions moving batch jobs to an event-driven design while keeping historical reports stable. I've done that migration once and would plan it differently the second time. I'd start with a replay harness that compares old and new outputs row by row before anything is switched over, and I'd keep both paths running until the numbers agree for a full month.

I'd be glad to talk through the details whenever suits you.

Robin Example

## Resume to upload
`demo/resume/robin-example-resume.txt`

## Unverified claims I avoided
- (none noted: the reviewer missed the PhD line; the guardrail did not)

## Revision log
- 2026-09-30: first draft.
