# textutils Module

The `textutils` module provides a function to slugify text. This is useful for creating URL-friendly strings from arbitrary text.

## Installation

No installation is required as the module is part of the project.

## Usage

To use the `slugify` function, import it into your Python script or interactive session:

```python
from experiments.m6_demo.textutils import slugify
```

### Example

Here's how you can use the `slugify` function:

```python
result = slugify('Hello, World!')
print(result)  # Output: hello-world
```

## Testing

The module includes a test file to ensure the functionality works as expected. You can run the tests using pytest:

```sh
pytest experiments/m6_demo/test_textutils.py
```

This will execute the tests and provide feedback on whether the `slugify` function is working correctly.
