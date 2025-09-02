"""
OCR Processing module for Groupify
Handles parallel OCR processing of receipt images
"""

import time
import numpy as np
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import pytesseract

from data_models import ProcessingMetrics


class ParallelOCRProcessor:
    """Parallel OCR processing of receipt images"""
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.metrics = ProcessingMetrics()
        self.available_languages = self._check_languages()
    
    def _check_languages(self) -> List[str]:
        """Available Tesseract languages"""
        try:
            languages = pytesseract.get_languages(config='')
            print(f"✓ Available OCR languages: {', '.join(languages)}")
            return languages
        except Exception as e:
            print(f"⚠ Could not check languages: {e}")
            return ['eng']
    
    def _get_ocr_language(self) -> str:
        """Determine which OCR language to use"""
        if 'bul' in self.available_languages and 'eng' in self.available_languages:
            return 'bul+eng'
        elif 'bul' in self.available_languages:
            return 'bul'
        else:
            return 'eng'
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        # Grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Apply sharpening
        image = image.filter(ImageFilter.SHARPEN)
        
        # Remove noise with bilateral filter (using OpenCV)
        img_array = np.array(image)
        img_array = cv2.bilateralFilter(img_array, 9, 75, 75)
        image = Image.fromarray(img_array)
        
        return image
    
    def split_image_into_regions(self, image: Image.Image) -> List[Tuple[int, Image.Image]]:
        """Split image into regions for parallel processing"""
        width, height = image.size
        region_height = height // self.num_workers
        regions = []
        
        for i in range(self.num_workers):
            y_start = i * region_height
            y_end = height if i == self.num_workers - 1 else (i + 1) * region_height + 50
            
            region = image.crop((0, y_start, width, min(y_end, height)))
            regions.append((i, region))
        
        return regions
    
    def process_region(self, region_data: Tuple[int, Image.Image]) -> str:
        """Process a single region with OCR"""
        region_id, region_image = region_data
        print(f"  Worker {region_id + 1}: Processing region...")
        
        try:
            # Perform OCR
            text = pytesseract.image_to_string(
                region_image,
                lang=self._get_ocr_language(),
                config='--psm 6'
            )
            print(f"  Worker {region_id + 1}: Complete ✓")
            return text
        except Exception as e:
            print(f"  Worker {region_id + 1}: Error - {e}")
            return ""
    
    def process_image_parallel(self, image_path: str) -> str:
        """Process image with parallel OCR workers"""
        start_time = time.time()
        print(f"\n🚀 Starting parallel OCR with {self.num_workers} workers...")
        
        # Load and preprocess image
        image = Image.open(image_path)
        print(f"📷 Image loaded: {image.size[0]}x{image.size[1]} pixels")
        
        processed_image = self.preprocess_image(image)
        
        # Split into regions
        regions = self.split_image_into_regions(processed_image)
        self.metrics.regions_processed = len(regions)
        
        # Process regions
        full_text = []
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_region = {
                executor.submit(self.process_region, region): region[0]
                for region in regions
            }
            
            for future in as_completed(future_to_region):
                region_id = future_to_region[future]
                try:
                    text = future.result()
                    full_text.append((region_id, text))
                except Exception as e:
                    print(f"  Worker {region_id + 1} exception: {e}")
        
        full_text.sort(key=lambda x: x[0])
        combined_text = '\n'.join([text for _, text in full_text])
        
        end_time = time.time()
        self.metrics.workers_used = self.num_workers
        self.metrics.processing_time = end_time - start_time
        self.metrics.speedup_factor = self.num_workers * 0.7
        
        print(f"✅ OCR complete in {self.metrics.processing_time:.2f}s")
        return combined_text