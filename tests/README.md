These tests can be run using the [`pytest`](https://docs.pytest.org/en/8.0.x/) library. If you install the package and run pytest from the main `test` directory, It will recursively collect all of the functions prefixed with `test_` in each file and run them. It will additionally notify which, if any, tests have failed.

Examples:

```
pytest
```

```
pytest entanglement_management
```

```
pytest entanglement_management/test_swapping.py
```
