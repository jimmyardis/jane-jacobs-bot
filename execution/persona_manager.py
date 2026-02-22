#!/usr/bin/env python3
"""
Persona configuration manager for historical figure chatbot template.
Loads, validates, and provides typed access to persona configs.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class PersonaConfigError(Exception):
    """Raised when persona configuration is invalid or missing"""
    pass


class PersonaManager:
    """Manages persona configuration loading and validation"""

    REQUIRED_FIELDS = [
        'id',
        'metadata.name',
        'metadata.birth_year',
        'corpus.collection_name',
        'persona.system_prompt_template',
        'widget.conversation_starters',
        'widget.ui.header_title'
    ]

    @staticmethod
    def load_persona(persona_id: str, personas_dir: str = "personas") -> Dict[str, Any]:
        """
        Load and validate persona configuration

        Args:
            persona_id: Persona identifier (e.g., 'jane-jacobs')
            personas_dir: Base directory containing persona configs

        Returns:
            Complete persona configuration dictionary

        Raises:
            PersonaConfigError: If config file not found or invalid
        """
        # Determine base path (support both relative and absolute paths)
        if not os.path.isabs(personas_dir):
            # Get the project root (parent of execution/)
            project_root = Path(__file__).parent.parent
            config_path = project_root / personas_dir / persona_id / "persona.json"
        else:
            config_path = Path(personas_dir) / persona_id / "persona.json"

        if not config_path.exists():
            raise PersonaConfigError(
                f"Persona config not found: {config_path}\n"
                f"Make sure '{persona_id}' directory exists in '{personas_dir}' "
                f"with a persona.json file."
            )

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise PersonaConfigError(
                f"Invalid JSON in {config_path}: {e}"
            )

        # Inject persona_id if not present
        if 'id' not in config:
            config['id'] = persona_id

        # Validate required fields
        PersonaManager._validate_config(config)

        return config

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """
        Validate that all required fields are present

        Raises:
            PersonaConfigError: If required fields are missing
        """
        missing_fields = []

        for field_path in PersonaManager.REQUIRED_FIELDS:
            parts = field_path.split('.')
            current = config

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    missing_fields.append(field_path)
                    break

        if missing_fields:
            raise PersonaConfigError(
                f"Missing required fields in persona.json:\n" +
                "\n".join(f"  - {field}" for field in missing_fields)
            )

        # Validate conversation starters is a list with 4 items
        starters = config.get('widget', {}).get('conversation_starters', [])
        if not isinstance(starters, list) or len(starters) != 4:
            raise PersonaConfigError(
                "widget.conversation_starters must be an array of exactly 4 questions"
            )

    @staticmethod
    def build_system_prompt(config: Dict[str, Any]) -> str:
        """
        Build system prompt from template with variable substitution

        Args:
            config: Persona configuration dictionary

        Returns:
            Complete system prompt string with all variables substituted
        """
        template = config['persona']['system_prompt_template']
        current_year = datetime.now().year

        # Prepare substitution dictionary
        metadata = config['metadata']
        subs = {
            'name': metadata['name'],
            'birth_year': metadata['birth_year'],
            'death_year': metadata.get('death_year', ''),
            'current_age': metadata.get('current_age', current_year - metadata['birth_year']),
            'current_year': current_year,
            'famous_work': metadata.get('famous_work', '')
        }

        # Format lists if present
        if 'voice_characteristics' in config['persona']:
            subs['voice_characteristics'] = '\n'.join(
                f"- {c}" for c in config['persona']['voice_characteristics']
            )

        if 'constraints' in config['persona']:
            subs['constraints'] = '\n'.join(
                f"- {c}" for c in config['persona']['constraints']
            )

        if 'frameworks' in config['persona']:
            subs['frameworks'] = ', '.join(config['persona']['frameworks'])

        # Perform substitution
        try:
            return template.format(**subs)
        except KeyError as e:
            raise PersonaConfigError(
                f"System prompt template references undefined variable: {e}"
            )

    @staticmethod
    def get_collection_name(config: Dict[str, Any]) -> str:
        """
        Get ChromaDB collection name for persona

        Args:
            config: Persona configuration dictionary

        Returns:
            Collection name string (e.g., 'jane_jacobs_corpus')
        """
        return config['corpus']['collection_name']

    @staticmethod
    def get_corpus_paths(config: Dict[str, Any], personas_dir: str = "personas") -> Dict[str, Path]:
        """
        Get corpus directory paths for persona

        Args:
            config: Persona configuration dictionary
            personas_dir: Base directory containing persona configs

        Returns:
            Dictionary with 'raw', 'cleaned', and 'base' Path objects
        """
        persona_id = config['id']

        # Determine base path
        if not os.path.isabs(personas_dir):
            project_root = Path(__file__).parent.parent
            base_path = project_root / personas_dir / persona_id / "corpus"
        else:
            base_path = Path(personas_dir) / persona_id / "corpus"

        return {
            'raw': base_path / 'raw',
            'cleaned': base_path / 'cleaned',
            'base': base_path
        }

    @staticmethod
    def get_sources_config(persona_id: str, personas_dir: str = "personas") -> Optional[Dict[str, Any]]:
        """
        Load sources.json configuration for corpus acquisition

        Args:
            persona_id: Persona identifier
            personas_dir: Base directory containing persona configs

        Returns:
            Sources configuration dictionary, or None if file doesn't exist
        """
        # Determine base path
        if not os.path.isabs(personas_dir):
            project_root = Path(__file__).parent.parent
            sources_path = project_root / personas_dir / persona_id / "sources.json"
        else:
            sources_path = Path(personas_dir) / persona_id / "sources.json"

        if not sources_path.exists():
            return None

        try:
            with open(sources_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise PersonaConfigError(
                f"Invalid JSON in {sources_path}: {e}"
            )

    @staticmethod
    def list_available_personas(personas_dir: str = "personas") -> list[str]:
        """
        List all available persona IDs in the personas directory

        Args:
            personas_dir: Base directory containing persona configs

        Returns:
            List of persona IDs (directory names that contain persona.json)
        """
        # Determine base path
        if not os.path.isabs(personas_dir):
            project_root = Path(__file__).parent.parent
            personas_path = project_root / personas_dir
        else:
            personas_path = Path(personas_dir)

        if not personas_path.exists():
            return []

        personas = []
        for item in personas_path.iterdir():
            if item.is_dir() and (item / "persona.json").exists():
                personas.append(item.name)

        return sorted(personas)


# Convenience function for quick loading
def load_persona(persona_id: str = None) -> Dict[str, Any]:
    """
    Load persona configuration (convenience wrapper)

    Args:
        persona_id: Persona identifier, or None to use PERSONA_ID env var

    Returns:
        Persona configuration dictionary
    """
    if persona_id is None:
        persona_id = os.getenv("PERSONA_ID", "jane-jacobs")

    return PersonaManager.load_persona(persona_id)


if __name__ == "__main__":
    # Test loading Jane Jacobs config
    import sys

    try:
        persona_id = sys.argv[1] if len(sys.argv) > 1 else "jane-jacobs"
        print(f"Loading persona: {persona_id}")

        config = PersonaManager.load_persona(persona_id)
        print(f"✓ Loaded: {config['metadata']['name']}")
        print(f"  Collection: {PersonaManager.get_collection_name(config)}")
        print(f"  Conversation starters: {len(config['widget']['conversation_starters'])}")

        print(f"\n✓ System prompt preview:")
        prompt = PersonaManager.build_system_prompt(config)
        print(prompt[:300] + "...")

        print(f"\n✓ Available personas: {', '.join(PersonaManager.list_available_personas())}")

    except PersonaConfigError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
