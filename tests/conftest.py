"""Pytest configuration for the scraper test suite.

The legacy standalone test scripts (test_feature_extractor, test_make_normalizer,
test_dealers) call sys.exit() at module level and are not pytest-collectable.
They must be run directly :

    python3 tests/test_feature_extractor.py
    python3 tests/test_make_normalizer.py

Pytest-style tests (test_extract_description and onwards) collect and run normally :

    pytest tests/ -v
"""
collect_ignore = [
    'test_feature_extractor.py',
    'test_make_normalizer.py',
    'test_dealers.py',
]
