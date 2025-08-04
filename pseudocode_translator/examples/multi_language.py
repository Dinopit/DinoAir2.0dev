#!/usr/bin/env python3
"""
Multi-Language Translation Example

This example demonstrates how to translate pseudocode into multiple
programming languages with language-specific optimizations.
"""

from pseudocode_translator import SimpleTranslator
from typing import Dict, List
import json


def example_1_basic_multi_language():
    """Example 1: Translate to multiple languages"""
    print("\n=== Example 1: Basic Multi-Language Translation ===")
    
    translator = SimpleTranslator()
    
    pseudocode = """
    FUNCTION greet(name)
        RETURN "Hello, " + name + "!"
    END FUNCTION
    
    FUNCTION main()
        PRINT greet("World")
    END FUNCTION
    """
    
    languages = ["python", "javascript", "java", "cpp", "go"]
    
    print("Original pseudocode:")
    print(pseudocode)
    print("\n" + "-" * 50)
    
    for lang in languages:
        print(f"\n{lang.upper()} Translation:")
        result = translator.translate(pseudocode, target_language=lang)
        if result.code:
            print(result.code)
        print("-" * 50)


def example_2_language_specific_features():
    """Example 2: Use language-specific features"""
    print("\n=== Example 2: Language-Specific Features ===")
    
    translator = SimpleTranslator()
    
    pseudocode = """
    CREATE a Person class with:
        - name: string
        - age: integer
        - email: optional string
        
        METHOD __init__(name: string, age: integer, email: optional string = None)
            SET self.name TO name
            SET self.age TO age
            SET self.email TO email
        END METHOD
        
        METHOD can_vote() -> boolean
            RETURN self.age >= 18
        END METHOD
        
        ASYNC METHOD fetch_profile() -> dictionary
            # Simulate async operation
            AWAIT delay(1000)
            RETURN {
                "name": self.name,
                "age": self.age,
                "email": self.email,
                "can_vote": self.can_vote()
            }
        END METHOD
    END CLASS
    """
    
    # Language-specific options
    language_options = {
        "python": {
            "type_hints": True,
            "docstring_style": "google",
            "async_syntax": "async/await"
        },
        "typescript": {
            "strict_types": True,
            "interface_style": True,
            "access_modifiers": True
        },
        "java": {
            "version": "17",
            "use_records": False,
            "getter_setter": True
        },
        "rust": {
            "derive_traits": ["Debug", "Clone"],
            "error_handling": "Result",
            "ownership": "smart"
        }
    }
    
    for lang, options in language_options.items():
        print(f"\n{lang.upper()} with specific features:")
        print(f"Options: {json.dumps(options, indent=2)}")
        
        result = translator.translate(
            pseudocode,
            target_language=lang,
            options=options
        )
        
        if result.code:
            print("\nGenerated code:")
            print(result.code)
        print("-" * 70)


def example_3_algorithm_in_multiple_languages():
    """Example 3: Complex algorithm in multiple languages"""
    print("\n=== Example 3: Algorithm Implementation ===")
    
    translator = SimpleTranslator()
    
    # Binary search algorithm
    pseudocode = """
    FUNCTION binary_search(array: list of integers, target: integer) -> integer
        SET left TO 0
        SET right TO length(array) - 1
        
        WHILE left <= right
            SET mid TO (left + right) // 2
            
            IF array[mid] == target THEN
                RETURN mid
            ELSE IF array[mid] < target THEN
                SET left TO mid + 1
            ELSE
                SET right TO mid - 1
            END IF
        END WHILE
        
        RETURN -1  # Not found
    END FUNCTION
    
    FUNCTION test_binary_search()
        SET test_array TO [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
        SET test_cases TO [(5, 2), (15, 7), (1, 0), (19, 9), (4, -1)]
        
        FOR EACH (target, expected) IN test_cases
            SET result TO binary_search(test_array, target)
            IF result == expected THEN
                PRINT "✓ Found " + target + " at index " + result
            ELSE
                PRINT "✗ Test failed for " + target
            END IF
        END FOR
    END FUNCTION
    """
    
    # Languages with different syntax styles
    languages = {
        "python": "Dynamic typing with clear syntax",
        "go": "Static typing with simple syntax",
        "rust": "Memory-safe with ownership",
        "javascript": "Dynamic with modern ES6+ features",
        "kotlin": "Null-safe with concise syntax"
    }
    
    for lang, description in languages.items():
        print(f"\n{lang.upper()} - {description}:")
        
        result = translator.translate(
            pseudocode,
            target_language=lang,
            options={
                "optimize": True,
                "include_tests": True
            }
        )
        
        if result.code:
            # Show first 20 lines
            lines = result.code.split('\n')
            for i, line in enumerate(lines[:20]):
                print(f"{i+1:3d} | {line}")
            if len(lines) > 20:
                print(f"... ({len(lines) - 20} more lines)")
        print("-" * 70)


def example_4_web_application_components():
    """Example 4: Web application components in different languages"""
    print("\n=== Example 4: Web Application Components ===")
    
    translator = SimpleTranslator()
    
    # REST API endpoint
    pseudocode = """
    CREATE a UserController class with:
        - userService: UserService instance
        
        ASYNC METHOD get_user(id: string) -> Response
            TRY
                SET user TO AWAIT userService.find_by_id(id)
                IF user IS None THEN
                    RETURN Response(
                        status=404,
                        body={"error": "User not found"}
                    )
                END IF
                RETURN Response(
                    status=200,
                    body=user.to_dict()
                )
            CATCH Exception as e
                RETURN Response(
                    status=500,
                    body={"error": str(e)}
                )
            END TRY
        END METHOD
        
        ASYNC METHOD create_user(data: dictionary) -> Response
            TRY
                # Validate input
                IF "email" NOT IN data OR "name" NOT IN data THEN
                    RETURN Response(
                        status=400,
                        body={"error": "Missing required fields"}
                    )
                END IF
                
                # Check if user exists
                SET existing TO AWAIT userService.find_by_email(data["email"])
                IF existing IS NOT None THEN
                    RETURN Response(
                        status=409,
                        body={"error": "User already exists"}
                    )
                END IF
                
                # Create new user
                SET user TO AWAIT userService.create(data)
                RETURN Response(
                    status=201,
                    body=user.to_dict()
                )
            CATCH Exception as e
                RETURN Response(
                    status=500,
                    body={"error": str(e)}
                )
            END TRY
        END METHOD
    END CLASS
    """
    
    # Web framework specific translations
    frameworks = {
        "python": {
            "framework": "FastAPI",
            "async": True,
            "type_hints": True,
            "decorators": ["@app.get", "@app.post"]
        },
        "javascript": {
            "framework": "Express.js",
            "async": True,
            "middleware": True
        },
        "typescript": {
            "framework": "NestJS",
            "decorators": True,
            "dependency_injection": True
        },
        "go": {
            "framework": "Gin",
            "error_handling": "explicit",
            "context": True
        }
    }
    
    for lang, config in frameworks.items():
        print(f"\n{lang.upper()} with {config['framework']}:")
        print(f"Configuration: {json.dumps(config, indent=2)}")
        
        result = translator.translate(
            pseudocode,
            target_language=lang,
            options=config
        )
        
        if result.code:
            print("\nGenerated controller code:")
            # Show first 30 lines for web components
            lines = result.code.split('\n')
            for line in lines[:30]:
                print(line)
            if len(lines) > 30:
                print(f"... ({len(lines) - 30} more lines)")
        print("-" * 70)


def example_5_data_processing_pipeline():
    """Example 5: Data processing pipeline in multiple languages"""
    print("\n=== Example 5: Data Processing Pipeline ===")
    
    translator = SimpleTranslator()
    
    pseudocode = """
    CREATE a DataPipeline class with:
        - steps: list of processing steps
        
        METHOD add_step(step: function)
            APPEND step TO self.steps
        END METHOD
        
        METHOD process(data: list) -> list
            SET result TO data
            FOR EACH step IN self.steps
                SET result TO map(step, result)
            END FOR
            RETURN result
        END METHOD
        
        STATIC METHOD clean_text(text: string) -> string
            # Remove extra whitespace
            SET text TO trim(text)
            # Convert to lowercase
            SET text TO lowercase(text)
            # Remove special characters
            SET text TO regex_replace(text, "[^a-z0-9\\s]", "")
            RETURN text
        END METHOD
        
        STATIC METHOD tokenize(text: string) -> list
            RETURN split(text, " ")
        END METHOD
        
        STATIC METHOD remove_stopwords(tokens: list) -> list
            SET stopwords TO ["the", "is", "at", "which", "on", "a", "an"]
            RETURN filter(lambda token: token NOT IN stopwords, tokens)
        END METHOD
    END CLASS
    
    FUNCTION example_usage()
        SET pipeline TO new DataPipeline()
        pipeline.add_step(DataPipeline.clean_text)
        pipeline.add_step(DataPipeline.tokenize)
        pipeline.add_step(DataPipeline.remove_stopwords)
        
        SET texts TO [
            "The quick brown fox jumps over the lazy dog!",
            "Python is a great programming language.",
            "Data processing pipelines are useful."
        ]
        
        SET processed TO pipeline.process(texts)
        FOR EACH result IN processed
            PRINT result
        END FOR
    END FUNCTION
    """
    
    # Functional vs OOP languages
    language_styles = {
        "python": {
            "style": "mixed",
            "use_comprehensions": True,
            "use_generators": True
        },
        "scala": {
            "style": "functional",
            "use_implicits": True,
            "collection_methods": True
        },
        "rust": {
            "style": "functional",
            "use_iterators": True,
            "error_handling": "Result"
        },
        "javascript": {
            "style": "functional",
            "use_arrow_functions": True,
            "use_array_methods": True
        }
    }
    
    for lang, options in language_styles.items():
        print(f"\n{lang.upper()} - {options['style']} style:")
        
        result = translator.translate(
            pseudocode,
            target_language=lang,
            options=options
        )
        
        if result.code:
            print(result.code)
        print("-" * 70)


def compare_language_features():
    """Compare how different languages handle the same concepts"""
    print("\n=== Language Feature Comparison ===")
    
    translator = SimpleTranslator()
    
    # Test various language features
    features = {
        "Optional Types": """
            FUNCTION get_middle_name(full_name: string) -> optional string
                SET parts TO split(full_name, " ")
                IF length(parts) >= 3 THEN
                    RETURN parts[1]
                ELSE
                    RETURN None
                END IF
            END FUNCTION
        """,
        
        "Error Handling": """
            FUNCTION divide_safe(a: number, b: number) -> result
                IF b == 0 THEN
                    RETURN Error("Division by zero")
                ELSE
                    RETURN Ok(a / b)
                END IF
            END FUNCTION
        """,
        
        "Generics": """
            CLASS Container<T> with:
                - value: T
                
                METHOD get() -> T
                    RETURN self.value
                END METHOD
                
                METHOD set(new_value: T)
                    SET self.value TO new_value
                END METHOD
            END CLASS
        """,
        
        "Pattern Matching": """
            FUNCTION describe_number(n: integer) -> string
                MATCH n
                    CASE 0:
                        RETURN "zero"
                    CASE 1:
                        RETURN "one"
                    CASE x IF x < 0:
                        RETURN "negative"
                    CASE x IF x > 100:
                        RETURN "large"
                    CASE _:
                        RETURN "other"
                END MATCH
            END FUNCTION
        """
    }
    
    languages = ["python", "rust", "typescript", "swift", "kotlin"]
    
    for feature_name, pseudocode in features.items():
        print(f"\n{'=' * 70}")
        print(f"Feature: {feature_name}")
        print(f"{'=' * 70}")
        
        for lang in languages:
            print(f"\n{lang.upper()}:")
            result = translator.translate(
                pseudocode,
                target_language=lang,
                options={"feature_specific": True}
            )
            
            if result.code:
                print(result.code)
            else:
                print("(Feature not directly supported)")
            print("-" * 40)


def main():
    """Run all multi-language examples"""
    print("Pseudocode Translator - Multi-Language Examples")
    print("=" * 70)
    
    examples = [
        example_1_basic_multi_language,
        example_2_language_specific_features,
        example_3_algorithm_in_multiple_languages,
        example_4_web_application_components,
        example_5_data_processing_pipeline,
        compare_language_features
    ]
    
    for example in examples:
        try:
            example()
            print("\n" + "=" * 70)
            input("\nPress Enter to continue to next example...")
        except KeyboardInterrupt:
            print("\n\nExamples interrupted by user")
            break
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
    
    print("\nMulti-language examples completed!")
    print("\nKey insights:")
    print("- Each language has unique features and idioms")
    print("- The translator adapts output to language conventions")
    print("- Type systems vary significantly between languages")
    print("- Error handling approaches differ across languages")
    print("- Modern features like async/await have different syntax")


if __name__ == "__main__":
    main()