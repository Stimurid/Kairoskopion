# Kairoskopion staging — tester guide

This is the **operator/staging preview** of Kairoskopion. Not a public
product release. Soft-auth, no password, no email verification.
Acceptable only for trusted testers chosen by the operator.

---

## 1. URL

`<STAGING_URL>` — the operator will share this with you in a private
channel. Treat the link like a password: anyone with it can hit the
gate.

## 2. Create an account

On first visit you see a **Welcome / Continue** gate.

### Sign up
1. Enter a **Display name** (required). This is what shows in the top
   bar.
2. Enter an **Email** (optional, but recommended). Email is used ONLY
   so you can continue from a different device / browser later.
3. Click **Create workspace**.

> Email is optional. If you skip it, your workspace lives in this
> browser's `localStorage` only — clear the cache and you lose access.
> If you provide an email, you can later return from any device by
> typing it into the **Continue** tab.

### Continue (existing account)
- Switch to the **Continue** tab.
- Type the email you used at signup.
- Get a new session token immediately. No code, no email confirmation.

## 3. Security limitation — please read

- **No password.** A logged-in browser is the whole identity.
- **No email verification.** Anyone who learns your tester email can
  hit `/auth/continue` and immediately operate your workspace.
- **No rate limit on signup/continue.** Brute-force on email guesses
  is technically possible.
- **No session expiry.** Tokens live until you click **Sign out** or
  the operator revokes them server-side.

The disclaimer is also visible in the gate UI:

> "This staging login has no password and no email confirmation.
> Anyone who knows your email can access your workspace. Use only with
> trusted testers."

If any of this is uncomfortable for your real article content, ask
the operator for a separate staging instance.

## 4. Create a case

A **Case** is one positioning project for one piece of writing.

- Click **+ New** in the left sidebar.
- The case opens with the **Intake** view.

You can keep multiple cases at once. Each shows its current stage
(empty / article model / scenario / pathways / venue pool / ...) in
the sidebar.

## 5. Paste a fragment and analyse it

Inside the Intake view:

1. Paste your text in the big textarea. Russian or English. Anything
   from a 200-word abstract to a partial draft works.
2. Optional: switch the **input type** chip from `Auto-detect` to
   `Article / Abstract` if you know what it is.
3. Leave **No search** selected for the first run.
4. Click **Analyze**.

What happens behind the scenes:

- Backend builds a **PreliminaryArticleModel** from your text using
  an LLM. This takes **60–120 seconds** when the LLM is healthy.
- The view auto-routes to **Article Model** once the model is ready.

> A banner at the top of every case view says:
> "Preliminary positioning — this is not a submission
> recommendation. Outputs are evidence-traceable hypotheses, not
> decisions. Unknowns are marked explicitly."
> Take that seriously. None of this output is a final venue pick.

## 6. What the views mean

### Article Model
Card with:
- **Object** — what the article is about (continental philosophy,
  early modern history, etc.).
- **Problem** — the central question.
- **Thesis / core claims** — the main positions in plain prose.
- **Method** — how the article argues (conceptual, textual, empirical,
  ...).
- **Novelty** — what kind of new contribution it makes.
- **Discipline** — which academic worlds the article might fit.
- **Protected core** — things in the article that should NOT be
  rewritten away for venue fit.
- **Unknowns** — fields the system could not extract from your text.
  Honest absence, not silent failure.

If the LLM returns a thin/incomplete response, the card shows:
> "Extraction produced a shallow model — key fields are missing.
> You can edit fields manually, or go back and try a shorter/cleaner
> input."

This is the system saying **"I tried but I am not confident."**
**Honest unknown is the expected state for some inputs.** It is NOT
a bug if the model is mostly empty — pick another fragment or refine
your text and retry.

### Pathways (Disciplinary trajectories)
Up to 10 academic worlds the article could enter, each with:
- **Discipline name** + fit badge (`strong / medium / weak / unknown`)
  + core-risk badge.
- **Reasoning** — a short paragraph explaining *why* the system
  thinks this discipline is a possible home for your article.
- **Adaptations needed** — what would change about the article to
  fit this world.
- **Example venues** (when populated) and **strategic notes**.

The reasoning paragraph is the most important part for cross-checking
the system's judgment.

### Venue Pool
Discovered venue candidates with confidence + status + identifiers
(OpenAlex ID, ISSN, DOAJ, ...). Each candidate is a hypothesis, not
a recommendation. Some candidates will have lots of unknowns — that
is expected for a first deterministic pass.

### Other views
**Scenario / Selected Venue / Fit / Mismatch / Adaptation / Pack /
Dossier** — later stages of the canonical pipeline. They light up as
you progress through the cockpit. None of them produce a "submit
here" verdict at this preview stage.

## 7. Suggested tester prompts to try

To stress the system, try at least one of each kind:

1. **Weird humanities fragment.** Anything where the discipline is
   not obvious — a continental-philosophy meditation on a strange
   object, a media-archaeology riff, a literary-theory hybrid.
2. **Short abstract.** 150–300 words, normal academic register.
3. **Incomplete idea.** 4–6 sentences that hint at an article but
   don't fully argue it.
4. **Russian-language fragment.** Especially with mixed-language
   theoretical vocabulary (Делёз, schizo-образ, dispositif).
5. **English fragment** in your own discipline.

For each fragment, check whether the **Pathways view reasoning**
makes sense to you as a human in that discipline. That is the
clearest cross-check on whether the model "got" your text.

## 8. What to report back

Helpful feedback for the operator:

- **Wrong discipline.** "It put my Foucault paper in Education
  pathway as strong fit — wrong."
- **Missing venue type.** "No journal in my actual field appeared in
  Venue Pool."
- **Hallucinated certainty.** Anything where the system claims a
  fact (e.g. a journal's policy, an editor's name) that you know
  isn't true. Quote the exact UI text.
- **UI confusion.** Anything where you cannot figure out what a
  view means or where to click next.
- **Slow / failed run.** Time-stamp and how long you waited.
  Especially "LLM-attempted but UNKNOWN everywhere" — that means
  the LLM JSON-validation fell back.

Format: free-form text is fine. Screenshot helps. Don't paste secrets
(e.g. your full unpublished manuscript) unless you trust the channel.

## 9. Sign out

Click **Sign out** in the top-right. This revokes your token
server-side. Your workspace data persists; just `localStorage` is
cleared. Use the **Continue** tab to come back.

## 10. Known limitations (today)

- **LLM JSON validation is not robust.** Some fragments will produce
  a fully populated ArticleModel; others will silently fall to
  "shallow model" with `UNKNOWN` everywhere. This is the
  dual-execution agent design — it never fabricates — but it means
  the LLM-rich output is intermittent. Operator is working on repair
  / visible-fallback so the failure mode is explicit instead of
  silent.
- **No human-readable model view yet.** The Article Model view is
  cards-with-fields, not prose. An author-facing "explain my article
  back to me in a paragraph" view is on the next-pass backlog
  precisely so non-technical authors can validate the system's
  interpretation.
- **No prompt correction surface in the UI yet.** If the system gets
  the discipline wrong, you cannot yet feed that correction back
  into a re-run; you can only retry with a different / clearer
  fragment.
- **Backend tests do not exercise live LLM.** CI deterministic
  tests pass; live LLM smoke is manual and run by the operator.

End of guide.
