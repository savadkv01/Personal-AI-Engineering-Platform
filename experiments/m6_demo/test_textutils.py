from experiments.m6_demo.textutils import slugify
import pytest

def test_slugify():
    assert slugify('Hello, World!') == 'hello-world'
    assert slugify('Python 3.8') == 'python-38'
    assert slugify('123 ABC abc!@#') == '123-abc-abc'
