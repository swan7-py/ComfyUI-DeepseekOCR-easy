import os
import torch
from pathlib import Path
from typing import List, Tuple

from pdf2image import convert_from_path
from pypdf import PdfReader
from PIL import Image
import numpy as np

from comfy.utils import ProgressBar

# ==============================
# Helper: PDF → List[PIL.Image]
# ==============================

def load_pdf_as_images(pdf_path: str, start_page: int, end_page: int) -> List[Image.Image]:
    # Normalize path (handle both Windows \ and Linux /)
    pdf_path = os.path.normpath(pdf_path.strip())
    
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("File must be a PDF (.pdf)")

    try:
        total_pages = len(PdfReader(pdf_path).pages)
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {e}")

    if not (1 <= start_page <= end_page <= total_pages):
        raise ValueError(f"Invalid page range: {start_page}-{end_page} for {total_pages} pages")

    images = convert_from_path(
        pdf_path,
        first_page=start_page,
        last_page=end_page,
        fmt='png',
        thread_count=1
    )
    return images

# ==============================
# Helper: PIL → ComfyUI Tensor
# ==============================

def load_pdf_as_images(pdf_path: str, start_page: int, end_page: int) -> List[Image.Image]:
    # Strip whitespace and resolve path
    pdf_path = pdf_path.strip().strip('"').strip("'")
    if not pdf_path:
        raise ValueError("PDF path is empty.")
    
    # Use os.path.abspath to resolve relative paths and normalize separators
    # This handles "M:\file.pdf" correctly on Windows
    if os.path.isabs(pdf_path):
        resolved_path = pdf_path
    else:
        resolved_path = os.path.abspath(pdf_path)
    
    
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"PDF file not found at: '{resolved_path}' (input was: '{pdf_path}')")
    
    if not resolved_path.lower().endswith('.pdf'):
        raise ValueError("File must be a PDF (.pdf)")

    try:
        total_pages = len(PdfReader(resolved_path).pages)
    except Exception as e:
        raise ValueError(f"Failed to read PDF file: {e}")

    if not (1 <= start_page <= end_page <= total_pages):
        raise ValueError(f"Invalid page range: {start_page}-{end_page} for {total_pages} pages")

    images = convert_from_path(
        resolved_path,
        first_page=start_page,
        last_page=end_page,
        fmt='png',
        thread_count=1
    )
    return images

# ==============================
# Helper: PIL → ComfyUI Tensor
# ==============================

def pil_to_tensor(pil_image: Image.Image) -> torch.Tensor:
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    img_array = np.array(pil_image).astype(np.float32) / 255.0
    img_tensor = torch.from_numpy(img_array)[None,]  # [1, H, W, C]
    return img_tensor

# ==============================
# Node: Load PDF from Absolute Path
# ==============================

class LoadPDFtoImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pdf_absolute_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": r"e.g., M:\docs\file.pdf or /home/user/file.pdf"
                }),
                "start_page": ("INT", {"default": 1, "min": 1, "max": 9999}),
                "end_page": ("INT", {"default": 1, "min": 1, "max": 9999}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "load_pdf"
    CATEGORY = "SwanOCR"

    def load_pdf(self, pdf_absolute_path: str, start_page: int, end_page: int) -> Tuple[List[torch.Tensor]]:
        pil_images = load_pdf_as_images(pdf_absolute_path, start_page, end_page)
        tensors = [pil_to_tensor(img) for img in pil_images]
        return (tensors,)

# ==============================
# Node: DeepSeek OCR from Images
# ==============================

class DeepSeekOCRNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "mode": (["Tiny", "Small", "Base", "Large", "Gundam"], {"default": "Gundam"}),
                "task_type": (["document", "without layouts", "other image", "figures in document", "general"], {"default": "document"}),
                "custom_prompt": ("STRING", {"default": "", "multiline": False, "placeholder": "Enter custom prompt (optional)"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("markdown_text",)
    FUNCTION = "process_images"
    OUTPUT_NODE = True
    CATEGORY = "SwanOCR"

    def process_images(self, images: List[torch.Tensor], mode: str, task_type: str, custom_prompt: str) -> Tuple[str]:
        from modelscope import AutoModel, AutoTokenizer
        import shutil
        import folder_paths
        import os

        model_path = os.path.join(folder_paths.models_dir, "DeepSeek-OCR-Latest-BF16.I64")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"DeepSeek OCR model not found at: {model_path}")

        print(f"[DeepSeekOCR] Loading model from {model_path}...")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            use_safetensors=True
        ).eval().cuda()

        output_dir = folder_paths.get_output_directory()
        result_dir = os.path.join(output_dir, "deepseek_ocr_results")
        os.makedirs(result_dir, exist_ok=True)


        task_prompts = {
            "document": "<image>\n<|grounding|>Convert the document to markdown.",
            "without layouts": "<image>\nFree OCR.",
            "other image": "<image>\n<|grounding|>OCR this image.",
            "figures in document": "<image>\nParse the figure.",
            "general": "<image>\nDescribe this image in detail.",
        }

        prompt = custom_prompt if custom_prompt else task_prompts.get(task_type, task_prompts["document"])

        print(f"[DeepSeekOCR] Using prompt: {prompt}")

        all_md_content = []
        pbar = ProgressBar(len(images))

        for idx, img_tensor in enumerate(images):
            img_np = (img_tensor.squeeze().cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np, mode='RGB')

            temp_img_path = os.path.join(result_dir, f"temp_page_{idx+1}.png")
            pil_img.save(temp_img_path)

            base_size, image_size, crop_mode = self.get_mode_params(mode)

            try:
                model.infer(
                    tokenizer,
                    prompt=prompt,  
                    image_file=temp_img_path,
                    output_path=result_dir,
                    base_size=base_size,
                    image_size=image_size,
                    crop_mode=crop_mode,
                    save_results=True,
                    test_compress=True
                )

                md_path = os.path.join(result_dir, "result.mmd")
                if os.path.exists(md_path):
                    with open(md_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    all_md_content.append(f"--- Page {idx+1} ---\n{md_content}")
                    shutil.move(md_path, os.path.join(result_dir, f"page_{idx+1}.mmd"))
                else:
                    all_md_content.append(f"--- Page {idx+1} ---\n[OCR failed]\n")
            except Exception as e:
                print(f"[DeepSeekOCR] Error on page {idx+1}: {e}")
                all_md_content.append(f"--- Page {idx+1} ---\n[Error: {str(e)}]\n")

            pbar.update(1)

        full_md = "\n".join(all_md_content)
        final_md_path = os.path.join(output_dir, "deepseek_ocr_output.md")
        with open(final_md_path, 'w', encoding='utf-8') as f:
            f.write(full_md)

        print(f"[DeepSeekOCR] Final Markdown saved to: {final_md_path}")

        del model, tokenizer
        torch.cuda.empty_cache()

        return (full_md,)

    @staticmethod
    def get_mode_params(mode: str) -> Tuple[int, int, bool]:
        mode_params = {
            "Tiny": (512, 512, False),
            "Small": (640, 640, False),
            "Base": (1024, 1024, False),
            "Large": (1280, 1280, False),
            "Gundam": (1024, 640, True)
        }
        return mode_params.get(mode, (1024, 640, True))


# ==============================
# Registration
# ==============================

NODE_CLASS_MAPPINGS = {
    "LoadPDFtoImage": LoadPDFtoImage,
    "DeepSeekOCRNode": DeepSeekOCRNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadPDFtoImage": "📄 Load PDF from Path",
    "DeepSeekOCRNode": "🧠 DeepSeek OCR (Images → Markdown)",
}