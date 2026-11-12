# 09 · Orchestrator–workers

A lead model plans sub-tasks at run time, workers handle one sub-task each (concurrently), and the lead combines the results. A feature request becomes five sub-tasks; a typo fix becomes one. Used in [9.4 Orchestrator–workers](../../docs/09-agent-design-patterns/09.4-orchestrator-workers.md).

## Run it

```bash
cd examples
python 09-orchestrator-workers/main.py
```

Output (offline, with `MockLLM`):

```text
Task: Record when each user last logged in, and show it on the admin users page.
  orchestrator planned 5 sub-task(s):
    - app/models/user.py: Add a nullable last_login timestamp field.
    - migrations/: Add a migration that creates the last_login column.
    - app/auth/login.py: Set last_login to the current UTC time on success.
    - app/admin/templates/users.html: Add a 'Last login' column.
    - tests/test_login.py: Test that a successful login sets last_login.
  summary:
    This change touches 5 files:
    - app/models/user.py: Added `last_login = Column(DateTime(timezone=True), nullable=True)` to User.
    - migrations/: New migration 0042_add_last_login adds a nullable last_login column to users.
    - app/auth/login.py: After a successful password check, set `user.last_login = datetime.now(UTC)` and save.
    - app/admin/templates/users.html: Added a 'Last login' column showing the date, or 'never' if empty.
    - tests/test_login.py: Added test_successful_login_sets_last_login and test_failed_login_leaves_it_unchanged.

Task: Fix the typo 'recieve' in the README.
  orchestrator planned 1 sub-task(s):
    - README.md: Replace 'recieve' with 'receive'.
  summary:
    This change touches 1 file:
    - README.md: Changed 'recieve' to 'receive' in the Notifications section.
```

The plan is validated before any worker runs: it must be JSON, have 1 to 6 sub-tasks, use only known files, and never give two workers the same file. In this demo the workers only describe their change; a real coding agent would give each worker file-editing tools.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 09-orchestrator-workers
```

## Things to try

- Script a plan that lists `README.md` twice. What happens, and why is that check there?
- Give the workers a cheaper model than the orchestrator. Which calls get cheaper?
- Let the orchestrator ask for a second round of sub-tasks after reading the first results.
