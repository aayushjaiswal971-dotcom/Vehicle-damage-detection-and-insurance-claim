import torch
import torchvision
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
import cv2
import numpy as np

class MaskRCNNSegmenter:
    def __init__(self, model_path=None, num_classes=7):
        self.model_path = model_path
        self.num_classes = num_classes
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    def load_model(self):
        """Load Mask R-CNN model"""
        try:
            if self.model_path and torch.cuda.is_available():
                self.model = self._get_model(self.num_classes)
                self.model.load_state_dict(torch.load(self.model_path))
                print(f"Mask R-CNN loaded from {self.model_path}")
            else:
                print("Using pretrained Mask R-CNN")
                self.model = maskrcnn_resnet50_fpn(pretrained=True)
            
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            print(f"Error loading Mask R-CNN: {e}")
            self.model = maskrcnn_resnet50_fpn(pretrained=True)
            self.model.to(self.device)
            self.model.eval()
    
    def _get_model(self, num_classes):
        """Create Mask R-CNN model"""
        model = maskrcnn_resnet50_fpn(pretrained=True)
        
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
        
        in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
        hidden_layer = 256
        model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes)
        
        return model
    
    def segment(self, image, detections):
        """
        Perform pixel-level segmentation on detected regions
        Returns refined masks and damage areas
        """
        if self.model is None:
            self.load_model()
        
        # Convert to tensor
        img_tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        img_tensor = img_tensor.unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            predictions = self.model(img_tensor)
        
        masks = []
        pred = predictions[0]
        
        if len(pred['masks']) > 0:
            for i, (mask, score) in enumerate(zip(pred['masks'], pred['scores'])):
                if score > 0.5:
                    mask_np = mask[0].cpu().numpy()
                    mask_binary = (mask_np > 0.5).astype(np.uint8)
                    
                    mask_info = {
                        'mask': mask_binary,
                        'score': float(score),
                        'area': np.sum(mask_binary),
                        'bbox': pred['boxes'][i].cpu().numpy().tolist()
                    }
                    masks.append(mask_info)
        
        return masks
    
    def calculate_damage_ratio(self, masks, image_shape):
        """Calculate damage area ratio"""
        total_image_area = image_shape[0] * image_shape[1]
        total_damage_area = sum([m['area'] for m in masks])
        damage_ratio = total_damage_area / total_image_area if total_image_area > 0 else 0
        return damage_ratio
    
    def visualize_masks(self, image, masks):
        """Overlay masks on image"""
        img_copy = image.copy()
        
        for mask_info in masks:
            mask = mask_info['mask']
            color = np.random.randint(0, 255, 3).tolist()
            
            colored_mask = np.zeros_like(img_copy)
            colored_mask[mask == 1] = color
            
            img_copy = cv2.addWeighted(img_copy, 1, colored_mask, 0.5, 0)
        
        return img_copy
