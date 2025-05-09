import os
import sys

print("Python path:", sys.path)
print("Current working directory:", os.getcwd())


def test_simple():
    print("Running test_simple")
    assert True
