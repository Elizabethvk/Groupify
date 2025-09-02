"""
Groupify - Smart Bill Splitter with Parallel OCR

python3 main.py                          # Interactive CLI mode
python3 main.py receipt.jpg              # Process image and start CLI
python3 main.py receipt.jpg --quick      # Quick mode - just show results
python3 main.py --help                   # Show help
"""

import os
import sys
import argparse
from ocr_processor import ParallelOCRProcessor
from receipt_parser import ReceiptParser
from cli_interface import GroupifyCLI

def quick_process(image_path: str, workers: int = 4):
    """Quick processing mode - just show results"""
    print(f"🚀 Quick processing: {image_path}")
    
    processor = ParallelOCRProcessor(num_workers=workers)
    parser = ReceiptParser()
    
    # Process image
    ocr_text = processor.process_image_parallel(image_path)
    receipt = parser.parse(ocr_text)
    
    # Display results
    if receipt.items:
        print(f"\n📋 Found {len(receipt.items)} items:")
        for i, item in enumerate(receipt.items, 1):
            print(f"  {i:2}. {item.name[:40]:40} {item.price:7.2f} {receipt.currency}")
        print(f"\n💰 Total: {receipt.total:.2f} {receipt.currency}")
        
        m = processor.metrics
        print(f"\n⚡ Processed in {m.processing_time:.2f}s using {m.workers_used} workers")
        print(f"   Speedup: {m.speedup_factor:.1f}x")
    else:
        print("\n⚠ No items found in receipt")
        print("Try:")
        print("  • Better image quality/lighting")
        print("  • Different OCR settings")
        print("  • Manual item entry in interactive mode")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Groupify - Smart Bill Splitter with Parallel OCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Interactive mode
  python main.py receipt.jpg        # Process image then interactive
  python main.py receipt.jpg --quick # Quick mode - show results only
  python main.py --workers 8        # Use 8 parallel workers
        """
    )
    
    parser.add_argument(
        'image',
        nargs='?',
        help='Receipt image to process'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel OCR workers (default: 4)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode - process image and show results only'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='Groupify 1.0'
    )
    
    args = parser.parse_args()
    
    if args.workers < 1 or args.workers > 16:
        print("⚠ Workers must be between 1 and 16")
        args.workers = max(1, min(16, args.workers))
    
    if args.quick and args.image:
        if not os.path.exists(args.image):
            print(f"❌ File not found: {args.image}")
            sys.exit(1)
        
        quick_process(args.image, args.workers)
        return
    
    cli = GroupifyCLI()
    cli.processor = ParallelOCRProcessor(num_workers=args.workers)
    
    if args.image:
        if os.path.exists(args.image):
            cli.process_receipt(args.image)
        else:
            print(f"⚠ File not found: {args.image}")
    
    cli.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)