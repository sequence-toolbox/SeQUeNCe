These tests can be run using the [`pytest`](https://docs.pytest.org/en/8.0.x/) library. If you install the package and run pytest from the main `test` directory, It will recursively collect all of the functions prefixed with `test_` in each file and run them. It will additionally notify which, if any, tests have failed.

Examples:


```bash
# run all tests
pytest tests
```

```bash
# run tests under a folder
cd tests
pytest entanglement_management
```

```bash
# run tests in a file
cd entanglement_management
pytest test_swapping.py
```
