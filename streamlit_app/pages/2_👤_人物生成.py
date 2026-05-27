"""
Character Generator Page
Generate character images with face masking for safe video generation
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from visual_agent.agent.character_generator import (
    GENDER_OPTIONS, AGE_OPTIONS, ETHNICITY_OPTIONS,
    FACE_SHAPE_OPTIONS, HAIRSTYLE_OPTIONS, CLOTHING_OPTIONS,
    run_character_generation, list_generated_characters
)


def render_character_config(char_index: int) -> dict:
    """Render single character configuration UI"""
    st.markdown(f"#### Character {char_index}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        gender = st.selectbox(
            "Gender",
            options=GENDER_OPTIONS,
            index=0,
            key=f"char_{char_index}_gender"
        )
        
        age = st.selectbox(
            "Age",
            options=AGE_OPTIONS,
            index=0,
            key=f"char_{char_index}_age"
        )
        
        ethnicity = st.selectbox(
            "Ethnicity",
            options=ETHNICITY_OPTIONS,
            index=0,
            key=f"char_{char_index}_ethnicity"
        )
    
    with col2:
        face_shape = st.selectbox(
            "Face Shape",
            options=FACE_SHAPE_OPTIONS,
            index=0,
            key=f"char_{char_index}_face_shape"
        )
        
        hairstyle = st.selectbox(
            "Hairstyle",
            options=HAIRSTYLE_OPTIONS,
            index=0,
            key=f"char_{char_index}_hairstyle"
        )
    
    with col3:
        clothing = st.selectbox(
            "Clothing Style",
            options=CLOTHING_OPTIONS,
            index=0,
            key=f"char_{char_index}_clothing"
        )
    
    name = st.text_input(
        "Character Name (Optional)",
        placeholder="e.g., 小明, John, or leave empty for auto-naming",
        key=f"char_{char_index}_name",
        help="If empty, will use character_xxx format"
    )
    
    custom_attrs = st.text_area(
        "Custom Attributes (Optional)",
        placeholder="e.g., wearing glasses, beard, specific clothing color",
        height=68,
        key=f"char_{char_index}_custom"
    )
    
    return {
        "name": name.strip() if name.strip() else None,
        "gender": gender,
        "age": age,
        "ethnicity": ethnicity,
        "face_shape": face_shape,
        "hairstyle": hairstyle,
        "clothing": clothing,
        "custom_attributes": custom_attrs
    }


def display_character_images(char_path: Path, char_id: str):
    """Display 2 character images side by side"""
    cols = st.columns(2)
    
    views = [
        ("front_masked", "Front (Masked)"),
        ("front_full", "Front (Full)")
    ]
    
    for col, (view_name, caption) in zip(cols, views):
        img_path = char_path / f"{char_id}_{view_name}.png"
        if img_path.exists():
            col.image(str(img_path), caption=caption, use_container_width=True)
        else:
            col.info(f"{caption}\nNot generated")


def main():
    st.set_page_config(
        page_title="Character Generator - KINYO AI",
        page_icon="👤",
        layout="wide"
    )
    
    SessionStateManager.init_session_state()
    config = ConfigManager()
    
    st.title("👤 Character Generator")
    
    with st.sidebar:
        st.markdown("### Settings")
        
        num_characters = st.number_input(
            "Number of Characters",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
            help="How many characters to generate"
        )
        
        st.markdown("### Output")
        output_dir = st.text_input(
            "Output Directory",
            value=str(config.get_path("assets") / "characters"),
            help="Where to save generated characters"
        )
        
        st.markdown("---")
        
        generate = st.button("🎨 Generate Characters", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        st.markdown("### Info")
        st.markdown("""
        **Generated Images:**
        - Front face with **white grid mask** (privacy protection)
        - Front full body
        
        **Usage:**
        Generated characters can be used for video production without privacy concerns.
        """)
    
    # Character Configuration
    st.markdown("### Character Configuration")
    st.markdown("Configure each character's appearance. The front face will have a privacy grid mask.")
    
    characters = []
    for i in range(1, num_characters + 1):
        with st.expander(f"Character {i}", expanded=(i == 1)):
            char_config = render_character_config(i)
            characters.append(char_config)
    
    # Generate Characters
    if generate:
        api_key = config.get_api_key("k_token") or os.getenv("K_TOKEN_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("K_TOKEN_BASE_URL", "https://ai.ktokenhub.app")
        
        if not api_key:
            st.error("❌ No API key found. Please set K_TOKEN_API_KEY in .env file or Settings page.")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def progress_callback(progress, message):
            progress_bar.progress(progress)
            status_text.text(message)
        
        with st.spinner("Generating characters..."):
            try:
                result = run_character_generation(
                    characters=characters,
                    output_dir=Path(output_dir),
                    api_key=api_key,
                    base_url=base_url,
                    progress_callback=progress_callback
                )
                
                if result["success"]:
                    progress_bar.progress(100)
                    st.success(f"✓ Generated {len(result['characters'])} characters!")
                    
                    SessionStateManager.set("generated_characters", result["characters"])
                    
                    st.markdown("---")
                    st.markdown("### Generated Characters")
                    
                    for char in result["characters"]:
                        with st.expander(f"{char['id']}", expanded=True):
                            char_path = Path(list(char["paths"].values())[0]).parent
                            display_character_images(char_path, char['id'])
                            
                            if char.get('config'):
                                st.markdown("**Character Description:**")
                                st.write(f"- **Gender**: {char['config'].get('gender', '-')}")
                                st.write(f"- **Age**: {char['config'].get('age', '-')}")
                                st.write(f"- **Ethnicity**: {char['config'].get('ethnicity', '-')}")
                                if char['config'].get('custom_attributes'):
                                    st.write(f"- **Custom**: {char['config'].get('custom_attributes')}")
                else:
                    st.error("Generation failed")
                    
            except Exception as e:
                st.error(f"Error during generation: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
    
    # Display Existing Characters
    st.markdown("---")
    st.markdown("### Existing Characters")
    
    characters_dir = Path(output_dir)
    existing_chars = list_generated_characters(characters_dir)
    
    if existing_chars:
        st.markdown(f"Found **{len(existing_chars)}** generated characters")
        
        for char_info in existing_chars:
            char_id = char_info['id']
            with st.expander(f"{char_id}", expanded=False):
                char_path = Path(char_info["path"])
                display_character_images(char_path, char_id)
                
                if char_info.get('description'):
                    st.markdown("**Description:**")
                    st.write(char_info['description'])
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{char_id}"):
                        import shutil
                        shutil.rmtree(char_path)
                        st.success(f"Deleted {char_id}")
                        st.rerun()
    else:
        st.info("No characters generated yet. Configure and click 'Generate Characters' to start.")


if __name__ == "__main__":
    main()
