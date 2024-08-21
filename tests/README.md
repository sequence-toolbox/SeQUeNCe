These tests can be run using the [`pytest`](https://docs.pytest.org/en/8.0.x/) library. If you install the package and run pytest from the main `tests` directory, It will recursively collect all of the functions prefixed with `test_` in each file and run them. It will additionally notify which, if any, tests have failed.

Examples:

```bash
# run all tests
pytest tests
```

```bash
# run tests under entanglement_management folder
pytest tests/entanglement_management
```

```bash
# run tests in the test_swapping.py file
pytest tests/entanglement_management/test_swapping.py 
```
