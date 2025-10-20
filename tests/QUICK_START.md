# Quick Start: Running Tests

## ⚠️ IMPORTANT: ACSM Download Limits

The real ACSM file has **limited downloads per device**. Most tests use dummy data to avoid exhausting these downloads.

## Safe Testing (Recommended)

```bash
# Run all tests EXCEPT the real ACSM processing test
pytest tests/ -m "not real_acsm"
```

This skips the one test that actually processes the real ACSM file.

## When You Need to Test Real ACSM Processing

```bash
# Run ONLY the real ACSM processing test
pytest tests/test_lambda.py::TestLambdaACSM::test_acsm_content_upload -v
```

Use this sparingly to avoid hitting download limits.

## All Tests (Use Carefully)

```bash
# Run everything including real ACSM processing
pytest tests/
```

⚠️ This will consume one ACSM download from your device limit.

## Quick Examples

```bash
# Run only basic tests
pytest tests/test_lambda.py::TestLambdaBasic -v

# Run with output visible
pytest tests/ -m "not real_acsm" -s

# Run specific test
pytest tests/test_lambda.py::TestLambdaBasic::test_health_check -v

# See available markers
pytest --markers
```

## Manual Testing

For one-off manual tests, use the Python script:

```bash
# Test with bundled asset (WARNING: uses real ACSM)
python tests/manual_test.py asset

# Test basic connectivity (safe - no ACSM processing)
python tests/manual_test.py basic
```

## What Changed from Shell Scripts?

- **Shell tests** → Now Python pytest scripts
- **All tests used real ACSM** → Now only 1 test uses real ACSM (marked with `@pytest.mark.real_acsm`)
- **Hard to debug** → Now easy to debug with pytest's features
- **All or nothing** → Now granular control with markers and filters

See `TEST_GUIDE.md` for complete documentation.
