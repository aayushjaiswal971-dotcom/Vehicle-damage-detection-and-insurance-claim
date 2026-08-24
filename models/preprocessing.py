import cv2
import numpy as np

class ImagePreprocessor:
    def __init__(self, target_size=(640, 640)):
        self.target_size = target_size
    
    def preprocess(self, image_path):
        """
        Preprocess image for damage detection
        - Resize to target size
        - Noise reduction
        - Contrast enhancement
        """
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        
        # Resize
        img_resized = cv2.resize(img, self.target_size)
        
        # Noise reduction using bilateral filter
        img_denoised = cv2.bilateralFilter(img_resized, 9, 75, 75)
        
        # Contrast enhancement using CLAHE
        lab = cv2.cvtColor(img_denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        img_enhanced = cv2.merge([l_enhanced, a, b])
        img_enhanced = cv2.cvtColor(img_enhanced, cv2.COLOR_LAB2BGR)
        
        return img_enhanced, img_resized
    
    def save_preprocessed(self, image, output_path):
        cv2.imwrite(output_path, image)
