from transformers import ViTImageProcessor, ViTModel, AutoProcessor, AutoTokenizer, CLIPModel
from PIL import Image
import os
import torch
import numpy as np
from scipy.stats import hmean


__all__ = ["compute_metrics"]


def _cosine_similarity(embed1, embed2):
    return torch.nn.functional.cosine_similarity(embed1, embed2, dim=0).item()


def _cosine_similarities(gen_embeds, train_embeds):
    similarity_scores = [] # one score per generated image 
    
    for gen_embed in gen_embeds:
        scores = []  # one score per train image
        for train_embed in train_embeds:
            scores.append(_cosine_similarity(gen_embed, train_embed))
        
        similarity_scores.append(np.mean(scores))
        
    return similarity_scores


def _get_img_img_similarities(generated_imgs, train_imgs):
    model_id = "facebook/dino-vits16"
    processor = ViTImageProcessor.from_pretrained(model_id)
    model = ViTModel.from_pretrained(model_id, add_pooling_layer=False)
    
    generated_img_inputs = processor(images=generated_imgs, return_tensors="pt")
    generated_img_embeds = model(**generated_img_inputs).last_hidden_state[:, 0]
    
    train_img_inputs = processor(images=train_imgs, return_tensors="pt")    
    train_img_embeds = model(**train_img_inputs).last_hidden_state[:, 0]
    
    return np.array(_cosine_similarities(generated_img_embeds, train_img_embeds))
    
    
def _get_img_text_similarities(imgs, prompts):
    model_id = "openai/clip-vit-large-patch14"
    processor = AutoProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=False)
    similarity_scores = []
    
    for img, text in zip(imgs, prompts):
        text_inputs = tokenizer(text, padding=True, return_tensors="pt")
        text_embed = torch.squeeze(model.get_text_features(**text_inputs))
        
        img_inputs = processor(images=img, return_tensors="pt")
        img_embed = torch.squeeze(model.get_image_features(**img_inputs))

        similarity_scores.append(_cosine_similarity(text_embed, img_embed))
    
    return np.array(similarity_scores)
    

def _load_images(path): 
    paths = [os.path.join(path, f) for f in os.listdir(path) if f.split(".")[-1].lower() in ["png", "jpg"]]
    imgs = [Image.open(p).convert("RGB") for p in paths]
    return imgs


def compute_metrics(train_img_path, gen_img_path, prompts):
    gen_imgs = _load_images(gen_img_path)
    train_imgs = _load_images(train_img_path)
    
    img_img_similarities = _get_img_img_similarities(gen_imgs, train_imgs)
    img_text_similarities = _get_img_text_similarities(gen_imgs, prompts)
    
    # replace negative values by 0 so that the harmonic mean can be computed
    img_img_similarities[img_img_similarities < 0] = 0
    img_text_similarities[img_text_similarities < 0] = 0
    harmonic_means = hmean([img_img_similarities, img_text_similarities])  # create the "micro" harmonic mean, i.e. combine the 2 scores on a per-image level
    return np.mean(harmonic_means)
    
    