# The settings object does not print its secrets (#930)

*2026-10-12T16:45:37Z by Showboat 0.6.1*
<!-- showboat-id: b0af4fb3-ff07-47fb-9a66-25b047516bb0 -->

A pydantic model prints every field value in its repr. This demo gives the backend a made-up value for each of the thirteen settings the issue names, from an empty directory so no .env is read, and counts how many of those values come out when the settings are printed. Each value says which setting it stands for; none is real.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo930/env.sh; PY=$WT/backend/.venv/bin/python; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"; echo "the settings given a value: $SECRETS" | fold -s -w 110
```

```output
main:   911df24
branch: feature/issue-930-settings-repr
the settings given a value: MONGODB_URI DATABASE_URL OPENAI_API_KEY OPENAI_AUTOAUTHOR_API_KEY AI_API_KEY 
BETTER_AUTH_SECRET AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY CLOUDINARY_API_KEY CLOUDINARY_API_SECRET 
STRIPE_WEBHOOK_SECRET STRIPE_SECRET_KEY SENTRY_DSN
```

Before. On main, printing the settings prints all thirteen: directly, and through a log line that names them.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo930/env.sh; PY=$WT/backend/.venv/bin/python; echo -n 'repr(settings):             '; with_secrets $MAIN $PY -c 'from app.core.config import settings; print(repr(settings))' 2>&1 | found; echo -n 'a log line naming settings: '; with_secrets $MAIN $PY -c 'import logging; from app.core.config import settings; logging.basicConfig(); logging.getLogger("app").error("config is %s", settings)' 2>&1 | found
```

```output
repr(settings):             13 of 13 secret values printed
a log line naming settings: 13 of 13 secret values printed
```

The failure the issue came from: a test that reads a setting before the field exists, and next to it a comparison that fails with the settings in it. pytest renders the object when it explains the failure. On main its output holds every value.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo930/env.sh; PY=$WT/backend/.venv/bin/python; cat $D/case/test_missing_setting.py | tail -8; echo; echo -n 'main, pytest -vv:   '; with_secrets $MAIN $PY -m pytest $D/case -vv -p no:cacheprovider --rootdir $D/case 2>&1 | found
```

```output


def test_a_setting_that_does_not_exist_yet():
    assert settings.STRIPE_TAX_ENABLED is True


def test_a_comparison_that_fails_with_settings_in_it():
    assert settings == "anything"

main, pytest -vv:   13 of 13 secret values printed
```

After. The same three on this branch print none of them. The tests fail as before; their output no longer carries the values.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo930/env.sh; PY=$WT/backend/.venv/bin/python; echo -n 'repr(settings):             '; with_secrets $WT $PY -c 'from app.core.config import settings; print(repr(settings))' 2>&1 | found; echo -n 'a log line naming settings: '; with_secrets $WT $PY -c 'import logging; from app.core.config import settings; logging.basicConfig(); logging.getLogger("app").error("config is %s", settings)' 2>&1 | found; echo -n 'pytest -vv:                 '; with_secrets $WT $PY -m pytest $D/case -vv -p no:cacheprovider --rootdir $D/case 2>&1 | tee $D/pytest-branch.out | found; echo "pytest still reports: $(tail -1 $D/pytest-branch.out | tr -d '=' | sed -E 's/ in [0-9.]+s//; s/^ +//')"; grep -m1 'AttributeError: ' $D/pytest-branch.out | sed 's/^E *//'
```

```output
repr(settings):             0 of 13 secret values printed
a log line naming settings: 0 of 13 secret values printed
pytest -vv:                 0 of 13 secret values printed
pytest still reports: 2 failed 
AttributeError: 'Settings' object has no attribute 'STRIPE_TAX_ENABLED'
```

What is not a secret is still printed, and the hidden values are still there to be used: only the printing changed.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo930/env.sh; PY=$WT/backend/.venv/bin/python; with_secrets $WT $PY -c 'from app.core.config import settings; print("OPENAI_API_KEY reads back as:", settings.OPENAI_API_KEY); print(repr(settings))' | fold -s -w 150 | head -9
```

```output
OPENAI_API_KEY reads back as: LIVE-VALUE-OF-OPENAI_API_KEY-0123456789
Settings(ENVIRONMENT='test', DATABASE_NAME='auto_author_test', AI_MODEL_DEFAULT='gpt-4', AI_MODEL_LONG_OUTPUT='gpt-4o', 
AI_MAX_OUTPUT_TOKENS_DEFAULT=4000, AI_MAX_OUTPUT_TOKENS_LONG=8000, BETTER_AUTH_ISSUER='better-auth', JWT_ALGORITHM='HS256', API_V1_PREFIX='/api/v1', 
BACKEND_CORS_ORIGINS=['http://localhost:3000', 'http://localhost:8000'], E2E_ALLOW_BYPASS='', BYPASS_AUTH=False, E2E_EXEMPT_EMAILS='', 
AI_MAX_RETRIES=3, AI_REQUEST_TIMEOUT_SECONDS=120.0, MAX_QUESTION_REGENERATION_COUNT=5, AI_QUOTA_ENABLED=True, AI_QUOTA_FREE_DAILY=10, 
AI_QUOTA_FREE_MONTHLY=100, AI_QUOTA_PRO_DAILY=50, AI_QUOTA_PRO_MONTHLY=500, PLAN_ENFORCEMENT_ENABLED=True, EXPORT_TIMEOUT_SECONDS=120, 
EXPORT_MAX_WORKERS=2, AWS_REGION='us-east-1', AWS_S3_BUCKET='', CLOUDINARY_CLOUD_NAME='', BILLING_ENABLED=True, STRIPE_PRICE_ID_PRO='', 
STRIPE_AUTOMATIC_TAX=False, GIT_SHA='')
```

The same behaviour as tests, with a guard: any setting whose name marks it as a credential must be declared hidden, so a new one cannot be added without it.

```bash
cd /home/frankbria/projects/worktrees/issue-930-settings-repr/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo930 uv run pytest tests/test_core/test_settings_repr.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed -E 's/ in [0-9.]*s//'
```

```output
============================== 20 passed ==============================
```
