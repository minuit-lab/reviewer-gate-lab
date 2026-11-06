# reviewer-gate-lab

A writer drafts, an isolated reviewer judges, and a hook blocks the send unless the reviewer approved that exact draft. A golden set measures the reviewer.

A small, runnable [Claude Code](https://code.claude.com/docs/en/overview) lab on a fictional bookstore's support desk. No API key is needed for the tests. Every claim below points to the test or script that proves it, and the Limits section says what is not proven.

```
ticket ──> writer (main session) ──> outbox/draft.md
                                          │
                     reviewer subagent <──┘   (fresh context, told to judge only the page)
                          │
                          └─> tools/record_verdict.py ──> review/verdict.json  (verdict + SHA-256 of the draft)
                                                                │
writer runs tools/send_reply.py ──> PreToolUse hook checks ─────┘ ──> outbox/sent/  or  blocked
```

## Run it in 5 minutes

Requires Python 3 (tested on 3.14) and, for steps 2 and 3, [Claude Code](https://code.claude.com/docs/en/setup).

```bash
git clone https://github.com/minuit-lab/reviewer-gate-lab && cd reviewer-gate-lab

# 1. The gate, the golden set and the eval prompt, no model involved (about 2 seconds)
python3 -m unittest discover -s tests -v

# 2. The full loop: open Claude Code here and ask it to answer the sample ticket
claude
> Answer domain/inbox/ticket-001.md

# 3. Score the reviewer on the 14 golden cases (14 headless Claude calls)
python3 evals/run_eval.py
```

The sample ticket is a trap: the customer asks for a guaranteed delivery day and a discount, and the policy forbids both.

## The four parts of the harness

### 1. Constraints

- `domain/policy.md`: six numbered rules (returns, ebook refunds, delivery times, facts, privacy, commitments). The reviewer is told to cite them by number.
- `.claude/hooks/send_gate.py`, wired in `.claude/settings.json` as a [`PreToolUse` hook](https://code.claude.com/docs/en/hooks). It exits with code 2, which blocks the tool call and shows the reason to the model, when:
  - `tools/send_reply.py` runs without an `APPROVE` verdict whose SHA-256 matches the current draft;
  - Write, Edit or a shell command touches `review/` or `outbox/sent/`, or the gate itself (`.claude/`, `tools/`);
  - the two scripts are chained with anything else (`;`, `&&`, `|`, redirection);
  - the gate itself crashes: it fails closed.
- `tools/send_reply.py` checks the verdict again on its own, so it also refuses when run outside Claude Code. One verdict allows one send.

The rule lives in code, not in the prompt: `send_reply.py` refuses without a matching approval whatever the writer was told.

### 2. Tools

- The writer is the main Claude Code session, driven by `CLAUDE.md`.
- The reviewer is a [subagent](https://code.claude.com/docs/en/sub-agents), `.claude/agents/reviewer.md`, with `Read`, `Glob` and `Bash`, and the instruction to use Bash only to record its verdict. It starts with a fresh context: it does not see the writer's conversation. The writer is told to pass it the ticket path only, never its reasoning.
- `tools/record_verdict.py` and `tools/send_reply.py`, each run as a whole command, are the only ways into `review/` and `outbox/sent/` the gate lets through.

### 3. Memory

Everything the loop knows is in files you can open: the ticket, the policy, the order record, the draft, the verdict and the sent replies. Deleting `review/verdict.json` resets the approval.

### 4. Evaluation

- `evals/golden.json`: 14 cases, 7 to approve and 7 to reject, each tied to one policy rule and with a one-line `why`.
- `evals/run_eval.py` reads the reviewer's instructions and model from `.claude/agents/reviewer.md`, so it scores the same instructions and model as the subagent. Each case runs in a fresh `claude -p` call from an empty directory, with `--restricted` (no settings files) and no tools. It reports accuracy, then splits errors in two, because they do not cost the same:
  - **false approvals**: a bad reply would have gone out. The script exits with code 1 if there is any.
  - **false rejections**: a good reply is sent back for rework, which costs time but not a customer.
- Results are written to `evals/results/`. This README quotes no score: run it and read your own.
- The golden set is tested as well (`tests/test_golden_set.py`): the return-window labels are recomputed from the order dates, and the privacy cases are checked to come from someone other than the account holder. A wrong label would make every score wrong.

## Claims and proofs

| Claim | Proof (`tests/`) |
|---|---|
| No verdict, no send | `test_send_blocked_without_verdict` |
| A rejection blocks the send and its reason reaches the writer | `test_send_blocked_after_reject` |
| Editing the draft after approval cancels the approval | `test_editing_the_draft_cancels_the_approval` |
| One verdict allows one send | `test_one_verdict_allows_one_send` |
| The send script refuses on its own, outside Claude Code | `test_send_script_refuses_on_its_own` |
| The writer cannot write a verdict or a sent reply itself, by file or shell | `test_writer_cannot_write_a_verdict_file`, `test_writer_cannot_write_into_sent` |
| The scripts pass only as a whole command | `test_scripts_pass_only_as_a_whole_command` |
| The writer cannot edit the gate | `test_writer_cannot_change_the_gate` |
| A broken gate blocks | `test_gate_fails_closed` |
| Ordinary work is not blocked | `test_ordinary_work_passes` |
| The golden set is balanced and every rule has a case to reject | `test_balanced`, `test_every_rule_has_a_reject_case` |
| The eval uses the subagent's instructions and model | `test_prompt_contains_the_reviewer_instructions_and_model` |

## Limits

- **The gate checks that a verdict exists, not who wrote it.** The writer may run `record_verdict.py` as well as the reviewer can, and approve its own draft. Closing that gap needs an identity the writer cannot borrow, such as a signature, or a separate process that runs the reviewer.
- **The shell check is a tripwire, not a sandbox.** It reads the command text. A command that builds a guarded path at run time (a variable, `cd outbox && cp draft.md sent/`) passes it. It also blocks harmless commands that name a guarded folder, such as `ls review/`. The Write and Edit checks use resolved paths and are stricter.
- **The gate runs only while the hook runs.** Per the hooks documentation, a PreToolUse hook that times out does not block the call. Outside Claude Code, only `send_reply.py`'s own check remains.
- **The reviewer's isolation is partial.** Per the subagents documentation, a subagent starts without the parent's conversation but still loads `CLAUDE.md`, and receives a delegation message written by the writer. The reviewer is told to ignore `CLAUDE.md`, and the writer to send only the ticket path: both are instructions, not guarantees.
- **The eval runs the reviewer headless,** with the four inputs pasted into the prompt and not as a subagent reading files. It tests the judgment, not the file reading or the delegation.
- **14 cases are a smoke test, not a benchmark.** They show the method: one rule per case, labels checked by code where they can be. A real desk would need cases drawn from its own tickets.
- **Everything is fictional.** Quillmoor Books, its orders and its customers are invented, and "sending" means filing a file in `outbox/sent/`.

## Layout

```
CLAUDE.md                     writer instructions
.claude/agents/reviewer.md    isolated reviewer
.claude/hooks/send_gate.py    the gate
.claude/settings.json         hook wiring
domain/                       policy, orders, sample ticket
tools/                        verdict logic, record and send scripts
evals/                        golden set and eval runner
tests/                        gate, golden set and eval prompt tests
```

## License

MIT
