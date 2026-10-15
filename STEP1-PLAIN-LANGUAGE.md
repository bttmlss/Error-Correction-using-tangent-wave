# Step 1 in Plain Language

**By Adrian, 2026-10-15.** A non-technical companion to `STEP1-INTERPRETATION.md`
and `STEP1-SIGMA-CLARIFICATION.md`. All numbers below come from the 3,700-call
Step 1 run (`step1_partial.jsonl`) analyzed with the frozen v13 code.

---

Bro, here's what's happening right now. 😭🔬

You're discovering that the AI might not be controllable in the way your experiment assumed it was.

## 1. What you were trying to do

Imagine you're teaching a student to edit a paragraph. You tell them:

- "Add 2 words."
- "Add 4 words."
- "Add 8 words."

You expect the size of their change to roughly match the size of your instruction. Bigger command, bigger adjustment.

That's the basic idea behind proportional control: you give the system a command, measure what it does, and use the difference to calculate the next command.

## 2. What your AI actually did

Your 3,700-call experiment tested whether the model follows those instructions reliably.

**When told to add words**, the model often added roughly one or two words whether you requested 1, 2, 4, or 8. It didn't scale its response with the size of the command. (At +8, 87 out of 200 responses added exactly one word.)

**When told to remove words**, it behaved more predictably with smaller requests (−1, −2, −4 tracked at roughly 0.7–1.0 words removed per word requested), but at −8 it sometimes removed far more than requested — responses ranged from −1 all the way to −56. The results became extremely spread out.

In plain English, the same kind of instruction doesn't produce a reliably scaled response. Sometimes the model makes a tiny edit; sometimes it makes a much larger one.

## 3. Why that matters for your research

Your controller was supposed to work like a thermostat.

If the room is too cold, turn the heat up a little or a lot depending on how cold it is. If it's too hot, turn it down accordingly.

But imagine the thermostat tells the heater to increase by 2 degrees and it barely responds, then tells it to decrease by 2 degrees and it drops 10 degrees. You can't fix that simply by finding one magic setting. The relationship between the instruction and the result isn't behaving consistently enough.

That's what Step 1 exposed in this particular AI editing setup.

## 4. So did the experiment fail?

No. The calibration raised a problem that the experiment was designed to detect.

You completed 3,700 calls, with zero recorded errors and zero held-out rows entering the analysis. The frozen analysis flagged the directional asymmetry (163% positive-vs-negative difference, far beyond the 20% warning threshold).

The jitter comparison, however, couldn't be calculated because the analysis ran into a rank-deficient design matrix. That question remains unanswered; it wasn't a failed jitter result — no gate was ever evaluated.

So Step 2 is paused. The code and data stay frozen, and no more calls are authorized.

## 5. Here's the bigger picture, my guy

You started by asking, essentially, "Can external feedback help an AI correct its own output?"

But you've uncovered a more basic question:

**Can the AI reliably respond to the external correction signal in the first place?**

That's an important distinction for your tangent-wave research. You haven't disproved external correction, and you haven't proven that every model or prompt behaves this way. You've found that this particular interface doesn't give you a reliable control handle under the tested conditions.

Now you know something you didn't know before spending those calls.

The next step isn't to crank up the gain. It's to understand the limitation you've uncovered before deciding what the experiment should test next. 💡

---

**Record:** calibration flagged · jitter gate blocked (not failed) · Step 2 on hold ·
code and data frozen · no new calls authorized.
