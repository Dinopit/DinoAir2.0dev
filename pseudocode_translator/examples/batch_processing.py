#!/usr/bin/env python3
"""
Batch Processing Example

This example demonstrates how to process multiple pseudocode files
in a directory, with progress tracking and error handling.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from pseudocode_translator import PseudocodeTranslatorAPI
from pseudocode_translator.gui_worker import TranslationResult


class BatchProcessor:
    """Process multiple pseudocode files in batch"""
    
    def __init__(self, output_dir: Path = None, 
                 model: str = "qwen",
                 max_workers: int = 4):
        """
        Initialize batch processor
        
        Args:
            output_dir: Directory for output files (default: ./output)
            model: Model to use for translation
            max_workers: Maximum concurrent translations
        """
        self.translator = PseudocodeTranslatorAPI()
        self.translator.switch_model(model)
        self.output_dir = output_dir or Path("./output")
        self.output_dir.mkdir(exist_ok=True)
        self.max_workers = max_workers
        
        # Statistics
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "warnings": 0,
            "start_time": None,
            "end_time": None
        }
        
    def process_directory(self, input_dir: Path, 
                         pattern: str = "*.txt") -> Dict[str, any]:
        """
        Process all matching files in a directory
        
        Args:
            input_dir: Directory containing pseudocode files
            pattern: File pattern to match (default: *.txt)
            
        Returns:
            Dictionary with processing results
        """
        # Find all matching files
        files = list(input_dir.glob(pattern))
        if not files:
            print(f"No files matching '{pattern}' found in {input_dir}")
            return self.stats
        
        self.stats["total"] = len(files)
        self.stats["start_time"] = time.time()
        
        print(f"Found {len(files)} files to process")
        print(f"Using {self.max_workers} workers")
        print(f"Output directory: {self.output_dir}")
        print("-" * 50)
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(self._process_file, file): file
                for file in files
            }
            
            # Process completed tasks
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    success, warnings = future.result()
                    if success:
                        self.stats["successful"] += 1
                        if warnings:
                            self.stats["warnings"] += warnings
                except Exception as e:
                    print(f"Error processing {file.name}: {e}")
                    self.stats["failed"] += 1
        
        self.stats["end_time"] = time.time()
        self._print_summary()
        self._save_report()
        
        return self.stats
    
    def _process_file(self, file_path: Path) -> Tuple[bool, int]:
        """
        Process a single file
        
        Args:
            file_path: Path to pseudocode file
            
        Returns:
            Tuple of (success, warning_count)
        """
        print(f"Processing: {file_path.name}")
        
        try:
            # Read pseudocode
            with open(file_path, 'r', encoding='utf-8') as f:
                pseudocode = f.read()
            
            # Skip empty files
            if not pseudocode.strip():
                print(f"  ⚠️  Skipping empty file: {file_path.name}")
                return False, 0
            
            # Translate
            result = self.translator.translate(pseudocode)
            
            if result.success:
                # Save output
                output_file = self.output_dir / file_path.with_suffix('.py').name
                with open(output_file, 'w', encoding='utf-8') as f:
                    # Add header comment
                    f.write(f"# Generated from: {file_path.name}\n")
                    f.write(f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Model: {self.translator.get_current_model()}\n\n")
                    f.write(result.code)
                
                status = "✓" if not result.warnings else "⚠️"
                print(f"  {status} {file_path.name} → {output_file.name}")
                
                if result.warnings:
                    for warning in result.warnings:
                        print(f"    Warning: {warning}")
                
                return True, len(result.warnings)
            else:
                print(f"  ✗ {file_path.name}: Translation failed")
                for error in result.errors:
                    print(f"    Error: {error}")
                return False, 0
                
        except Exception as e:
            print(f"  ✗ {file_path.name}: {str(e)}")
            return False, 0
    
    def _print_summary(self):
        """Print processing summary"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        
        print("\n" + "=" * 50)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 50)
        print(f"Total files:      {self.stats['total']}")
        print(f"Successful:       {self.stats['successful']} "
              f"({self.stats['successful']/self.stats['total']*100:.1f}%)")
        print(f"Failed:           {self.stats['failed']}")
        print(f"Warnings:         {self.stats['warnings']}")
        print(f"Processing time:  {duration:.2f} seconds")
        print(f"Average time:     {duration/self.stats['total']:.2f} seconds/file")
        
    def _save_report(self):
        """Save detailed report"""
        report_file = self.output_dir / "batch_report.json"
        report = {
            "summary": self.stats,
            "configuration": {
                "model": self.translator.get_current_model(),
                "max_workers": self.max_workers,
                "output_directory": str(self.output_dir)
            },
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")


class InteractiveBatchProcessor(BatchProcessor):
    """Interactive batch processor with user confirmation"""
    
    def process_directory(self, input_dir: Path, 
                         pattern: str = "*.txt") -> Dict[str, any]:
        """Process directory with user interaction"""
        files = list(input_dir.glob(pattern))
        if not files:
            print(f"No files matching '{pattern}' found in {input_dir}")
            return self.stats
        
        # Show files to be processed
        print(f"\nFiles to process ({len(files)} total):")
        for i, file in enumerate(files[:10], 1):
            print(f"  {i}. {file.name}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        
        # Ask for confirmation
        response = input("\nProceed with batch processing? (y/n): ")
        if response.lower() != 'y':
            print("Batch processing cancelled.")
            return self.stats
        
        # Allow file exclusion
        print("\nEnter file numbers to exclude (comma-separated) or press Enter to process all:")
        exclude_input = input().strip()
        
        excluded_indices = set()
        if exclude_input:
            try:
                excluded_indices = {int(x.strip()) - 1 for x in exclude_input.split(',')}
            except ValueError:
                print("Invalid input. Processing all files.")
        
        # Filter files
        files_to_process = [f for i, f in enumerate(files) if i not in excluded_indices]
        
        # Process with parent method
        self.stats["total"] = len(files_to_process)
        self.stats["start_time"] = time.time()
        
        print(f"\nProcessing {len(files_to_process)} files...")
        print("-" * 50)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_file, file): file
                for file in files_to_process
            }
            
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    success, warnings = future.result()
                    if success:
                        self.stats["successful"] += 1
                        if warnings:
                            self.stats["warnings"] += warnings
                except Exception as e:
                    print(f"Error processing {file.name}: {e}")
                    self.stats["failed"] += 1
        
        self.stats["end_time"] = time.time()
        self._print_summary()
        self._save_report()
        
        return self.stats


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Batch process pseudocode files"
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing pseudocode files"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "-p", "--pattern",
        default="*.txt",
        help="File pattern to match (default: *.txt)"
    )
    parser.add_argument(
        "-m", "--model",
        choices=["qwen", "gpt2", "codegen"],
        default="qwen",
        help="Model to use (default: qwen)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Maximum concurrent workers (default: 4)"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive mode with file selection"
    )
    
    args = parser.parse_args()
    
    if not args.input_dir.exists():
        print(f"Error: Input directory '{args.input_dir}' does not exist")
        sys.exit(1)
    
    # Create processor
    if args.interactive:
        processor = InteractiveBatchProcessor(
            output_dir=args.output,
            model=args.model,
            max_workers=args.workers
        )
    else:
        processor = BatchProcessor(
            output_dir=args.output,
            model=args.model,
            max_workers=args.workers
        )
    
    # Process files
    try:
        stats = processor.process_directory(args.input_dir, args.pattern)
        
        # Exit with appropriate code
        if stats["failed"] == 0:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nBatch processing interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()