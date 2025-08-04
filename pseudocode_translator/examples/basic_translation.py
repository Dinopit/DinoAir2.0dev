#!/usr/bin/env python3
"""
Basic Translation Examples

This script demonstrates the simplest ways to use the Pseudocode Translator API.
Perfect for getting started with the library.
"""

from pseudocode_translator import PseudocodeTranslatorAPI


def example_1_simple_function():
    """Example 1: Translate a simple function"""
    print("\n=== Example 1: Simple Function ===")
    
    translator = PseudocodeTranslatorAPI()
    
    pseudocode = """
    create a function called add_numbers that:
    - takes two parameters a and b
    - returns their sum
    """
    
    result = translator.translate(pseudocode)
    
    if result.success:
        print("Generated Code:")
        print(result.code)
    else:
        print("Translation failed:")
        for error in result.errors:
            print(f"  - {error}")


def example_2_class_creation():
    """Example 2: Create a class with methods"""
    print("\n=== Example 2: Class Creation ===")
    
    translator = PseudocodeTranslatorAPI()
    
    pseudocode = """
    Create a Dog class that:
    - has name and age attributes
    - has a bark method that prints "Woof! My name is {name}"
    - has a get_dog_years method that returns age * 7
    - has a birthday method that increases age by 1
    """
    
    result = translator.translate(pseudocode)
    
    if result.success:
        print("Generated Code:")
        print(result.code)
        
        # Execute the generated code
        print("\nTesting the generated code:")
        exec(result.code)
        
        # Test the class
        dog = Dog("Buddy", 3)
        dog.bark()
        print(f"Dog years: {dog.get_dog_years()}")
        dog.birthday()
        print(f"Age after birthday: {dog.age}")


def example_3_algorithm():
    """Example 3: Implement an algorithm"""
    print("\n=== Example 3: Algorithm Implementation ===")
    
    translator = PseudocodeTranslatorAPI()
    
    pseudocode = """
    implement a function called is_prime that:
    - takes a number n as input
    - returns True if n is prime, False otherwise
    - handle edge cases: numbers less than 2 are not prime
    - optimize by only checking up to square root of n
    """
    
    result = translator.translate(pseudocode)
    
    if result.success:
        print("Generated Code:")
        print(result.code)
        
        # Test the function
        print("\nTesting the generated function:")
        exec(result.code)
        
        test_numbers = [2, 3, 4, 17, 20, 29, 100]
        for num in test_numbers:
            print(f"is_prime({num}) = {is_prime(num)}")


def example_4_mixed_pseudocode():
    """Example 4: Mix English and Python"""
    print("\n=== Example 4: Mixed Pseudocode ===")
    
    translator = PseudocodeTranslatorAPI()
    
    pseudocode = """
    def process_list(numbers):
        # first, remove all negative numbers
        
        # then sort the remaining numbers in descending order
        
        # calculate the average of the top 3 numbers
        # if less than 3 numbers, use all of them
        
        return average
    """
    
    result = translator.translate(pseudocode)
    
    if result.success:
        print("Generated Code:")
        print(result.code)
        
        # Test the function
        print("\nTesting with sample data:")
        exec(result.code)
        
        test_lists = [
            [1, -2, 3, -4, 5, 6, 7, 8, 9, 10],
            [5, 2],
            [-1, -2, -3]
        ]
        
        for lst in test_lists:
            try:
                result = process_list(lst)
                print(f"process_list({lst}) = {result}")
            except Exception as e:
                print(f"process_list({lst}) raised: {e}")


def example_5_error_handling():
    """Example 5: Generate code with error handling"""
    print("\n=== Example 5: Error Handling ===")
    
    translator = PseudocodeTranslatorAPI()
    
    pseudocode = """
    create a function safe_divide that:
    - takes two parameters: numerator and denominator
    - returns numerator divided by denominator
    - if denominator is zero, raise ZeroDivisionError with message "Cannot divide by zero"
    - if inputs are not numbers, raise TypeError with message "Inputs must be numbers"
    - round result to 2 decimal places
    """
    
    result = translator.translate(pseudocode)
    
    if result.success:
        print("Generated Code:")
        print(result.code)
        
        # Test error handling
        print("\nTesting error handling:")
        exec(result.code)
        
        test_cases = [
            (10, 3),
            (10, 0),
            ("10", 3),
            (10, 2)
        ]
        
        for num, den in test_cases:
            try:
                result = safe_divide(num, den)
                print(f"safe_divide({num}, {den}) = {result}")
            except Exception as e:
                print(f"safe_divide({num}, {den}) raised: {type(e).__name__}: {e}")


def example_6_data_structures():
    """Example 6: Working with data structures"""
    print("\n=== Example 6: Data Structures ===")
    
    translator = PseudocodeTranslatorAPI()
    
    pseudocode = """
    create a function analyze_students that:
    - takes a list of student dictionaries with keys: name, grade, subjects
    - returns a dictionary with:
      - 'honor_roll': list of student names with grade >= 90
      - 'average_grade': average grade of all students
      - 'popular_subjects': list of subjects taken by more than half the students
    - handle empty list by returning None
    """
    
    result = translator.translate(pseudocode)
    
    if result.success:
        print("Generated Code:")
        print(result.code)
        
        # Test with sample data
        print("\nTesting with sample data:")
        exec(result.code)
        
        students = [
            {'name': 'Alice', 'grade': 95, 'subjects': ['Math', 'Science', 'English']},
            {'name': 'Bob', 'grade': 85, 'subjects': ['Math', 'History', 'English']},
            {'name': 'Charlie', 'grade': 92, 'subjects': ['Math', 'Science', 'Art']},
            {'name': 'Diana', 'grade': 88, 'subjects': ['Science', 'English', 'Music']}
        ]
        
        analysis = analyze_students(students)
        print(f"Analysis: {analysis}")


def main():
    """Run all examples"""
    print("Pseudocode Translator - Basic Examples")
    print("=" * 50)
    
    examples = [
        example_1_simple_function,
        example_2_class_creation,
        example_3_algorithm,
        example_4_mixed_pseudocode,
        example_5_error_handling,
        example_6_data_structures
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
        
        print("\n" + "-" * 50)
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    main()