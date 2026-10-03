# Packet: Lumen Orchard / Applied AI Engineer

*(Fictional demo packet. Company, role and candidate are invented.)*

## Role
- company: Lumen Orchard
- title: Applied AI Engineer
- ats: ashby
- slug: lumen-orchard

## Apply URL
https://jobs.example.com/lumen-orchard/a1/application

## Form fields
| Field | Value |
|---|---|
| Location | Springfield (open to relocation) |

## Cover letter
*(271 words)*

Hello Lumen Orchard team,

I'd like to be considered for the Applied AI Engineer role on the Agents team. Most of my recent work sits where an agent meets messy internal documents, and the lesson I keep relearning is that the agent is rarely the weak part. Retrieval is.

At Example Studio Co. I built a retrieval layer for an internal assistant that answers production questions from about ninety thousand pages of wiki and ticket history. The first version scored well in demos and poorly in use. I added a small labelled set of real questions from staff and measured recall at each stage. Chunking turned out to matter most. Switching from fixed windows to section-aware chunks lifted top-five recall more than any model change we tried.

On the agent side I care about stopping conditions. An agent that can call tools needs to know when it has enough to answer and when it should hand the question to a person. I've shipped two tool-using agents with an explicit budget and a visible trace, so a reviewer can see each call and why it was made. Both run with a human approval step before anything is written back to a shared system.

Your posting talks about grounding answers in customer files. Returning the cited passage beside every claim is how I'd want to build it, and I'd enjoy the evaluation side of that work as much as the product side.

I'm based in Springfield and open to relocating. I'll need visa sponsorship, which I've noted in the form.

Thanks for your time. I'd welcome a conversation about the role.

Robin Example

## Resume to upload
`demo/resume/robin-example-resume.txt`

## Unverified claims I avoided
- No recall numbers: the labelled set is small and the figure would overstate precision.

## Revision log
- 2026-09-30: first draft.
