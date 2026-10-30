"""Academic demo datasets for instant testing and presentation showcase."""
from __future__ import annotations

from analyzer.file_processor import SourceFile

STUDENT_1_CODE = '''"""
Course: CS401 - Advanced Data Structures & Algorithms
Lab Assignment 03: Binary Search Implementation
Student: Subhashree M. (Roll: CS21B042)
"""

def binary_search(array: list[int], target: int) -> int:
    """Finds target in a sorted array and returns its index or -1 if not found."""
    low = 0
    high = len(array) - 1
    
    while low <= high:
        mid = (low + high) // 2
        guess = array[mid]
        
        if guess == target:
            return mid
        elif guess > target:
            high = mid - 1
        else:
            low = mid + 1
            
    return -1


def run_benchmark():
    dataset = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    query = 23
    result = binary_search(dataset, query)
    print(f"Target {query} found at index: {result}")


if __name__ == "__main__":
    run_benchmark()
'''

STUDENT_2_CODE = '''# Obfuscated version: Renamed identifiers, altered casing, stripped docstrings
def b_search(items, key):
    l = 0
    r = len(items) - 1
    
    while l <= r:
        m = (l + r) // 2
        val = items[m]
        
        if val == key:
            return m
        elif val > key:
            r = m - 1
        else:
            l = m + 1
            
    return -1


def execute_test():
    numbers = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    element = 23
    idx = b_search(numbers, element)
    print(f"Target {element} found at index: {idx}")


if __name__ == "__main__":
    execute_test()
'''

STUDENT_3_CODE = '''# Student: Alex Chen
# Lab 3: Binary Search
# Modified indentation & interspersed comments

def binary_search(array: list[int], target: int) -> int:
    # Set lower bound
    low = 0
    # Set upper bound
    high = len(array) - 1

    # Keep searching while pointers do not cross
    while low <= high:
        # Calculate middle index
        mid = (low + high) // 2
        guess = array[mid]

        if guess == target:
            # Target located
            return mid
        elif guess > target:
            # Look in left half
            high = mid - 1
        else:
            # Look in right half
            low = mid + 1

    # Element not found in list
    return -1


if __name__ == "__main__":
    test_arr = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    target_val = 23
    pos = binary_search(test_arr, target_val)
    print(f"Result index: {pos}")
'''

STUDENT_4_CODE = '''"""
Alternative Implementation: Sequential / Linear Search
Student: David K. (Roll: CS21B089)
Independent implementation using an entirely distinct algorithm paradigm.
"""

def linear_search(data_list: list[int], key_value: int) -> int:
    """Iterates through each element linearly until match is found."""
    for position, element in enumerate(data_list):
        if element == key_value:
            return position
    return -1


class SearchProfiler:
    def __init__(self, items):
        self.items = items
        self.lookups = 0

    def query(self, val):
        self.lookups += 1
        return linear_search(self.items, val)


if __name__ == "__main__":
    sample = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
    profiler = SearchProfiler(sample)
    ans = profiler.query(23)
    print(f"Linear search found at index: {ans} after {profiler.lookups} attempt(s)")
'''


def get_demo_files() -> list[SourceFile]:
    """Return 4 preloaded student files for instant showcase and testing."""
    return [
        SourceFile.from_text("student_1_binary_search.py", STUDENT_1_CODE, index=0),
        SourceFile.from_text("student_2_renamed_obfuscated.py", STUDENT_2_CODE, index=1),
        SourceFile.from_text("student_3_reformatted_comments.py", STUDENT_3_CODE, index=2),
        SourceFile.from_text("student_4_linear_search.py", STUDENT_4_CODE, index=3),
    ]
