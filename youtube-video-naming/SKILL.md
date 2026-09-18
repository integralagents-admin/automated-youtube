---
name: youtube-video-naming
description: Name YouTube videos around viewer intent.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, titles, content strategy, marketing]
    related_skills: []
---

# YouTube Video Naming Skill

Create clear, compelling YouTube titles that express the lesson a viewer hopes to learn, the mistake they need to avoid, or the better approach they should consider. Titles must be grounded in the actual clip, specific enough to attract the right audience, and strong without inventing outcomes or using empty clickbait.

## When to Use

- A repurposed YouTube Short or longform clip needs a title.
- A source clip contains a business lesson, framework, warning, diagnosis, or recommendation.
- Existing titles are vague, descriptive, repetitive, or disconnected from viewer intent.

Do not use this skill to invent claims, promise guaranteed results, or title a clip before understanding its transcript-backed point.

## Prerequisites

- The clip’s transcript, selected insight, or editorial summary.
- The intended audience or business context when known.
- The clip’s actual recommendation, risk, problem, or question.

## Title Modes

Choose the mode that best matches the viewer’s reason to click.

### 1. Question-led learning

Use when the clip teaches a process, principle, or answer to a clear problem.

Pattern:

- `How to [achieve the desired outcome]`
- `How to [solve the specific business problem]`
- `What Actually Makes [system/process] Work?`
- `Why Does [problem] Keep Happening?`

Examples:

- `How to Scale With Ads`
- `How to Turn a CRM Into a Revenue-Focused AI Agent`
- `What Actually Makes a Webinar Funnel Work?`

The question or implied question must be answerable by the clip. Prefer the concrete desired outcome over a generic topic label.

### 2. Warning-led avoidance

Use when the clip identifies a damaging behavior, hidden failure mode, false assumption, or costly mistake.

Pattern:

- `The Way You’re [bad behavior] Is [damaging consequence]`
- `Stop [mistake] Before It [consequence]`
- `Why [common approach] Is Quietly Hurting Your Business`
- `The [mistake] That Keeps [audience] From [outcome]`

Examples:

- `The Way You’re Handling Leads Is Destroying the Business`
- `Why Scaling Ads Too Fast Can Kill Your ROAS`
- `Stop Measuring the Metric That’s Misleading You`

Use strong language only when the clip supports the severity. If the transcript shows a risk or tendency rather than certainty, use `can`, `may`, `keeps`, or `quietly` instead of claiming guaranteed destruction.

### 3. Suggestion or contrarian replacement

Use when the clip recommends replacing a familiar tactic with a specific alternative.

Pattern:

- `Stop Doing [old approach] and Do This Instead`
- `Forget [common tactic]: Try [better approach]`
- `Instead of [old approach], Build [alternative]`
- `The Better Way to [desired outcome]`

Examples:

- `Stop Doing VSL Funnels and Do This Instead`
- `Stop Chasing More Leads and Fix This First`
- `Instead of Hiring More People, Remove the Bottleneck`

Name both sides when possible: the familiar approach creates recognition, while the replacement creates curiosity and utility.

## Procedure

1. **Extract the viewer promise.** Write one sentence answering: “What will a qualified viewer understand or do differently after watching?” Use only transcript-backed information.
2. **Identify the dominant intent.** Classify the clip as primarily learning, avoidance, or replacement. If two apply, select the one with the clearest viewer benefit.
3. **Name the audience or context.** Add a useful qualifier such as `With Ads`, `For Agencies`, `In Your CRM`, or `At $200K/Month` when it improves relevance without making the title unwieldy.
4. **Draft three candidates.** Create one candidate in the selected mode and two alternatives using different verbs, consequences, or levels of specificity.
5. **Make the title outcome-oriented.** Replace broad labels like `Business Advice`, `Marketing Strategy`, or `AI Follow-Up` with the problem, outcome, mistake, or decision the clip addresses.
6. **Preserve tension without fabrication.** Highlight a real consequence, counterintuitive recommendation, or unresolved question. Never add numbers, guarantees, urgency, or claims absent from the source.
7. **Choose the strongest candidate.** Select the title that communicates the most useful reason to watch in the fewest words while remaining natural when spoken aloud.
8. **Check range across a batch.** Avoid giving every clip the same opener. Mix `How to`, `Why`, `Stop`, `The Way`, `Instead of`, and specific question forms when the content supports them.

## Quality Rules

- Lead with the viewer’s desired knowledge or problem, not the speaker’s name.
- Prefer concrete nouns and active verbs: `leads`, `ads`, `webinars`, `ROAS`, `CRM`, `closers`, `offers`.
- Keep one dominant idea per title.
- Use capitalization consistently; use sentence case or title case, but do not alternate randomly within a batch.
- Avoid filler such as `This Is Crazy`, `You Won’t Believe`, `Game Changer`, or `The Truth About` unless the rest of the title provides concrete meaning.
- Avoid vague titles such as `Important Business Lesson` or `My Thoughts on Marketing`.
- Do not duplicate a title or merely swap punctuation between near-identical titles.
- Do not use a warning title when the clip only explains a neutral process.
- Do not use a replacement title unless the clip actually recommends an alternative.
- Do not use a question title if the clip never answers the question.

## Output Format

For each clip, return:

```text
Chosen title: <final title>
Mode: <question-led | warning-led | suggestion-led>
Viewer intent: <one-sentence promise>
Why it fits: <one concise explanation grounded in the clip>
Alternatives:
- <candidate 2>
- <candidate 3>
```

## Verification

Before accepting a title, confirm:

- It communicates a clear viewer question, risk, or recommendation.
- The clip directly delivers the implied lesson.
- Every factual claim and degree of severity is supported by the source.
- The title is specific to the audience or business context when useful.
- It is not a near-duplicate of another title in the same batch.
- It contains no fabricated metric, guaranteed result, or empty clickbait.

For a batch, verify that every clip has exactly one chosen title, a recorded mode, and an intent statement, and that the chosen titles provide meaningful variation across the batch.
