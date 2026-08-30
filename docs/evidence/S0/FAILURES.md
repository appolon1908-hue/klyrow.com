# S0 Failures and Recovery Evidence

## S0-T1 — no-commit merge staged in the wrong isolated worktree

- Class: implementation / operator targeting
- R1: Detected immediately when the new S0 worktree could not see the staged files; inspected `MERGE_HEAD` and both worktree states.
- Recovery: Aborted the uncommitted merge in the clean K0 worktree and repeated the same no-commit merge in `/root/klyrow-s0`.
- Impact: No commit or push occurred, no user worktree was touched, and the subsequent combined suite passed 178 tests.

## S0-T2 — push rejected after concurrent remote update

- Class: environmental / concurrent branch update
- Error:

  ```text
  ! [rejected] phase-s0/contract-conformance -> phase-s0/contract-conformance (fetch first)
  Updates were rejected because the remote contains work that you do not have locally.
  ```

- R1: Fetched and inspected remote commit `79f27ec`; it added overlapping conformance tests and both workflow integrations.
- Recovery: Preserved both histories with a normal merge. Resolved the add/add conflict by retaining the stronger AST discovery and incorporating the remote strict xfails and workflow steps. No force-push or history rewrite was used.
- Result: `186 passed, 5 xfailed`; merge commit `0cd48c6` pushed successfully.

## S0 gate — Node unavailable locally

- Class: environmental
- Observation: No local `node` executable was available for `validate-codestra-smtp-integration.mjs`.
- Recovery: Did not claim a local pass. The pushed GitHub Node 22 workflow executed the validator and completed successfully in run `33314274184`.
- Impact: None; both GitHub validation workflows are green on the gate commit.

