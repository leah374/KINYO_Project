"""
Character Generator
Generate character images with face masking for safe video generation
Uses OpenAI-compatible API with prompt-controlled face grid
"""

import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = BASE_DIR / "assets" / "characters"
DEFAULT_BASE_URL = "https://ai.ktokenhub.app"
DEFAULT_IMAGE_MODEL = "gpt-image-2"

# Preset options
GENDER_OPTIONS = ["Male", "Female", "Non-binary"]
AGE_OPTIONS = ["Young Adult (20-30)", "Middle-aged (30-50)", "Senior (50+)"]
ETHNICITY_OPTIONS = ["East Asian", "Southeast Asian", "Caucasian", "African", "Hispanic", "South Asian"]
FACE_SHAPE_OPTIONS = ["Oval", "Round", "Square", "Heart", "Diamond"]
HAIRSTYLE_OPTIONS = [
    "Long straight black hair",
    "Long wavy hair",
    "Medium length hair",
    "Short hair",
    "Curly hair",
    "Bald"
]
CLOTHING_OPTIONS = ["Casual", "Formal", "Sporty", "Traditional", "Business Casual"]


def generate_character_prompts(
    gender: str,
    age: str,
    ethnicity: str,
    face_shape: str,
    hairstyle: str,
    clothing: str,
    custom_attributes: str = ""
) -> Dict[str, str]:
    """
    Generate 2 prompts for character images
    - front_masked: Front face with white grid mask overlay
    - front_full: Front full body
    
    Args:
        gender: Male, Female, or Non-binary
        age: Young Adult, Middle-aged, or Senior
        ethnicity: East Asian, Caucasian, etc.
        face_shape: Oval, Round, Square, etc.
        hairstyle: Long straight, Short, etc.
        clothing: Casual, Formal, etc.
        custom_attributes: Additional custom descriptions
    
    Returns:
        Dictionary with 2 prompt strings
    """
    
    base_description = (
        f"{ethnicity} {gender.lower()}, {age.lower()}, "
        f"{face_shape} face shape, {hairstyle}, "
        f"wearing {clothing.lower()} clothing"
    )
    
    if custom_attributes:
        base_description += f", {custom_attributes}"
    
    prompts = {
        "front_masked": f"""
Portrait photo, front view face close-up.

Subject: {base_description}.

IMPORTANT FACE PRIVACY MASK:
The subject's face should be covered with a DENSE WHITE GRID PATTERN.
- Medium thickness white grid lines, less-transparent (about 90% opacity)
- Dense grid pattern with smaller cell sizes, covering the entire face area
- Grid is less-transparent but more opaque, facial features slightly visible through the grid
- Face shape and general contours remain visible beneath the grid
- Professional privacy overlay style that provides stronger privacy protection

Looking directly at camera, neutral expression.
Clean white background, professional studio lighting.
Face should be centered in frame.
Vertical format 9:16, photorealistic, high quality.

Style: Editorial photography with semi-transparent dense white grid face overlay.
        """.strip(),
        
        "front_full": f"""
Full body photo, front view.

Subject: {base_description}.

IMPORTANT FACE PRIVACY MASK:
The subject's face should be covered with a DENSE WHITE GRID PATTERN.
- Medium thickness white grid lines, less-transparent (about 90% opacity)
- Dense grid pattern with smaller cell sizes, covering the entire face area
- Grid is less-transparent but more opaque, facial features slightly visible through the grid
- Face shape and general contours remain visible beneath the grid
- Professional privacy overlay style that provides stronger privacy protection

Standing facing camera, relaxed natural pose.
Clean white background, professional studio lighting.
Full body visible from head to toe.
Vertical format 9:16, photorealistic, high quality.

Style: Editorial photography with semi-transparent dense white grid face overlay.
        """.strip()
    }
    
    return prompts


def generate_character_images(
    prompts: Dict[str, str],
    output_dir: Path,
    character_id: str,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    image_model: str = DEFAULT_IMAGE_MODEL
) -> Dict[str, Path]:
    """
    Generate character images using OpenAI API
    
    Args:
        prompts: Dictionary of 2 prompts
        output_dir: Output directory
        character_id: Unique character identifier (e.g., "character_001" or "小明")
        api_key: OpenAI API key
        base_url: API base URL
        image_model: Image generation model
    
    Returns:
        Dictionary mapping view names to generated image paths
    """
    client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
    
    character_dir = Path(output_dir) / character_id
    character_dir.mkdir(parents=True, exist_ok=True)
    
    result_paths = {}
    
    for view_name, prompt in prompts.items():
        print(f"Generating {view_name}...")
        
        try:
            response = client.images.generate(
                model=image_model,
                prompt=prompt,
                size="1024x1792",
                quality="auto",
                n=1
            )
            
            image_b64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_b64)
            
            image_path = character_dir / f"{character_id}_{view_name}.png"
            image_path.write_bytes(image_bytes)
            
            result_paths[view_name] = image_path
            print(f"  ✓ Saved: {image_path}")
            
        except Exception as e:
            print(f"  ✗ Error generating {view_name}: {e}")
            raise
        
        time.sleep(0.5)
    
    return result_paths


def save_character_desc(
    character_dir: Path,
    character_id: str,
    char_config: Dict[str, str],
    image_paths: Dict[str, Path]
) -> Path:
    """
    Save character description JSON file
    
    Args:
        character_dir: Character directory
        character_id: Character ID or name
        char_config: Character configuration
        image_paths: Dictionary of image paths
    
    Returns:
        Path to the saved description file
    """
    base_description = (
        f"{char_config.get('ethnicity', '')} {char_config.get('gender', '').lower()}, "
        f"{char_config.get('age', '').lower()}, "
        f"{char_config.get('face_shape', '')} face shape, "
        f"{char_config.get('hairstyle', '')}, "
        f"wearing {char_config.get('clothing', '').lower()} clothing"
    )
    
    if char_config.get('custom_attributes'):
        base_description += f", {char_config.get('custom_attributes')}"
    
    desc_data = {
        "id": character_id,
        "name": char_config.get("name", ""),
        "gender": char_config.get("gender", ""),
        "age": char_config.get("age", ""),
        "ethnicity": char_config.get("ethnicity", ""),
        "face_shape": char_config.get("face_shape", ""),
        "hairstyle": char_config.get("hairstyle", ""),
        "clothing": char_config.get("clothing", ""),
        "custom_attributes": char_config.get("custom_attributes", ""),
        "description": base_description,
        "created_at": datetime.now().isoformat(),
        "images": {
            view: f"{character_id}_{view}.png"
            for view in image_paths.keys()
        }
    }
    
    desc_path = character_dir / f"{character_id}_desc.json"
    desc_path.write_text(json.dumps(desc_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return desc_path


def get_next_character_id(output_dir: Path) -> int:
    """
    Get the next available character number by checking existing directories
    
    Args:
        output_dir: Output directory containing character folders
    
    Returns:
        Next available character number (1 if no existing characters)
    """
    if not output_dir.exists():
        return 1
    
    max_num = 0
    for char_dir in output_dir.iterdir():
        if not char_dir.is_dir():
            continue
        
        name = char_dir.name
        if name.startswith("character_"):
            try:
                num = int(name.split("_")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                continue
    
    return max_num + 1


def run_character_generation(
    characters: List[Dict[str, str]],
    output_dir: Path,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Batch generate characters
    
    Args:
        characters: List of character configurations
            [
                {
                    "name": "小明",  # Optional, if None will use character_xxx
                    "gender": "Female",
                    "age": "Young Adult (20-30)",
                    "ethnicity": "East Asian",
                    "face_shape": "Oval",
                    "hairstyle": "Long straight black hair",
                    "clothing": "Casual",
                    "custom_attributes": ""
                },
                ...
            ]
        output_dir: Output directory
        api_key: API key
        base_url: API base URL
        progress_callback: Optional callback function(progress, message)
    
    Returns:
        {
            "success": True,
            "characters": [
                {
                    "id": "character_001" or "小明",
                    "config": {...},
                    "paths": {...}
                },
                ...
            ]
        }
    """
    results = []
    total = len(characters)
    
    start_num = get_next_character_id(Path(output_dir))
    auto_id_counter = 0
    
    for idx, char_config in enumerate(characters):
        custom_name = char_config.get("name")
        
        if custom_name:
            character_id = custom_name
        else:
            character_id = f"character_{start_num + auto_id_counter:03d}"
            auto_id_counter += 1
        
        if progress_callback:
            progress = max(0, int(idx / total * 100))
            progress_callback(progress, f"Generating {character_id}...")
        
        prompts = generate_character_prompts(
            gender=char_config.get("gender", "Female"),
            age=char_config.get("age", "Young Adult (20-30)"),
            ethnicity=char_config.get("ethnicity", "East Asian"),
            face_shape=char_config.get("face_shape", "Oval"),
            hairstyle=char_config.get("hairstyle", "Long straight black hair"),
            clothing=char_config.get("clothing", "Casual"),
            custom_attributes=char_config.get("custom_attributes", "")
        )
        
        try:
            paths = generate_character_images(
                prompts=prompts,
                output_dir=output_dir,
                character_id=character_id,
                api_key=api_key,
                base_url=base_url
            )
            
            character_dir = Path(output_dir) / character_id
            desc_path = save_character_desc(
                character_dir=character_dir,
                character_id=character_id,
                char_config=char_config,
                image_paths=paths
            )
            
            results.append({
                "id": character_id,
                "config": char_config,
                "paths": {k: str(v) for k, v in paths.items()},
                "desc_path": str(desc_path)
            })
            
            if progress_callback:
                progress_callback(int(idx / total * 100), f"✓ {character_id} completed")
                
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"✗ {character_id} failed: {e}")
            raise
    
    return {
        "success": True,
        "characters": results,
        "output_dir": str(output_dir),
        "total_generated": len(results)
    }


def list_generated_characters(output_dir: Path) -> List[Dict[str, Any]]:
    """
    List all generated characters with full description
    
    Returns:
        List of character info dictionaries with description loaded from desc.json
    """
    characters = []
    
    if not output_dir.exists():
        return characters
    
    for char_dir in sorted(output_dir.iterdir()):
        if not char_dir.is_dir():
            continue
        
        char_id = char_dir.name
        char_info = {
            "id": char_id,
            "path": str(char_dir),
            "images": {},
            "description": ""
        }
        
        desc_path = char_dir / f"{char_id}_desc.json"
        if desc_path.exists():
            try:
                desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
                char_info.update(desc_data)
            except Exception:
                pass
        
        for view in ["front_masked", "front_full"]:
            img_path = char_dir / f"{char_id}_{view}.png"
            if img_path.exists():
                char_info["images"][view] = str(img_path)
        
        if char_info["images"]:
            characters.append(char_info)
    
    return characters


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate character images with face masking")
    parser.add_argument("--gender", default="Female", choices=GENDER_OPTIONS)
    parser.add_argument("--age", default="Young Adult (20-30)", choices=AGE_OPTIONS)
    parser.add_argument("--ethnicity", default="East Asian", choices=ETHNICITY_OPTIONS)
    parser.add_argument("--face-shape", default="Oval", choices=FACE_SHAPE_OPTIONS)
    parser.add_argument("--hairstyle", default="Long straight black hair", choices=HAIRSTYLE_OPTIONS)
    parser.add_argument("--clothing", default="Casual", choices=CLOTHING_OPTIONS)
    parser.add_argument("--custom", default="", help="Custom attributes")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    
    args = parser.parse_args()
    
    api_key = os.getenv("K_TOKEN_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Set K_TOKEN_API_KEY or OPENAI_API_KEY")
        exit(1)
    
    config = {
        "gender": args.gender,
        "age": args.age,
        "ethnicity": args.ethnicity,
        "face_shape": args.face_shape,
        "hairstyle": args.hairstyle,
        "clothing": args.clothing,
        "custom_attributes": args.custom
    }
    
    result = run_character_generation(
        characters=[config],
        output_dir=Path(args.output_dir),
        api_key=api_key,
        base_url=args.base_url
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
