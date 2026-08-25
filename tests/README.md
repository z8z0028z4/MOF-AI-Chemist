# Tests / 測試入口

Use [README_TESTING.md](README_TESTING.md) as the canonical testing guide.

請以 [README_TESTING.md](README_TESTING.md) 作為目前測試策略、marker、mock/external API 原則與執行指令的唯一入口。

Quick commands:

```bash
# From repository root
pytest tests -v
pytest --cov=backend --cov-report=term-missing tests

cd frontend
npm run build
```

Important:

- Default tests should not require real API keys or network.
- Real provider/network checks must be marked `external` and run opt-in.
- Do not rely on old references to `test_api.py`, `test_e2e.py`, or `quick_test.bat` unless those files are actually present.
