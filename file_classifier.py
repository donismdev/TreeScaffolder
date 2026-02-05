# -*- coding: utf-8 -*-
"""
file_classifier.py

A module for classifying file paths based on extensions using a JSON configuration.
It maps file extensions to icon (emoji) strings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set

class FileTypeClassifier:
    """
    Classifies file paths into predefined categories (icons) based on their extensions.
    The mapping is loaded from a JSON configuration file.
    """
    
    DEFAULT_CONFIG_FILENAME = "file_type_icons.json"
    GENERIC_FILE_ICON = "📄"
    FOLDER_ICON = "📁"

    def __init__(self, config_filepath: Path | str | None = None):
        self._extension_to_icon: Dict[str, str] = {}
        self._load_config(config_filepath)

    def _load_config(self, config_filepath: Path | str | None):
        """
        Loads the icon-to-extensions mapping from the JSON file and builds
        the internal extension-to-icon lookup.
        """
        if config_filepath is None:
            config_filepath = Path(__file__).parent / self.DEFAULT_CONFIG_FILENAME
        else:
            config_filepath = Path(config_filepath)
            
        if not config_filepath.exists():
            raise FileNotFoundError(f"Config file not found: {config_filepath}")
            
        try:
            with open(config_filepath, 'r', encoding='utf-8') as f:
                icon_to_extensions: Dict[str, List[str]] = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON config file '{config_filepath}': {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading config file '{config_filepath}': {e}")
            
        self._build_lookup(icon_to_extensions)

    def _build_lookup(self, icon_to_extensions: Dict[str, List[str]]):
        """
        Builds the internal `_extension_to_icon` dictionary from the loaded config.
        Ensures case-insensitivity and handles multi-suffix extensions.
        """
        for icon, extensions in icon_to_extensions.items():
            for ext in extensions:
                # Store extensions in lowercase for case-insensitive lookup
                self._extension_to_icon[ext.lower()] = icon

    def classify_path(self, path: Path, is_planned_dir: bool = False) -> str:
        """
        Classifies a given path (file or directory) and returns its corresponding icon string.

        Args:
            path: The pathlib.Path object to classify.
            is_planned_dir: If True, forces classification as a directory, even if it doesn't exist yet.

        Returns:
            An emoji string representing the file type.
        """
        if is_planned_dir or path.is_dir():
            return self.FOLDER_ICON
            
        # For files, check against known extensions
        # Handle multi-suffix extensions like ".build.cs"
        file_name_lower = path.name.lower()
        
        # Check full name for multi-suffix matches first
        # Sort by length to check for ".build.cs" before ".cs"
        for ext_key in sorted(self._extension_to_icon.keys(), key=len, reverse=True):
            if file_name_lower.endswith(ext_key):
                return self._extension_to_icon[ext_key]
        
        return self.GENERIC_FILE_ICON

if __name__ == "__main__":
    # Example usage:
    classifier = FileTypeClassifier()

    print(f"Folder: {classifier.classify_path(Path('C:/Users'))}")
    print(f"Python script: {classifier.classify_path(Path('my_script.py'))}")
    print(f"C++ source: {classifier.classify_path(Path('main.cpp'))}")
    print(f"Header: {classifier.classify_path(Path('my_header.h'))}")
    print(f"Config: {classifier.classify_path(Path('config.json'))}")
    print(f"Image: {classifier.classify_path(Path('picture.png'))}")
    print(f"Archive: {classifier.classify_path(Path('archive.zip'))}")
    print(f"Build script: {classifier.classify_path(Path('MyProject.build.cs'))}")
    print(f"Executable: {classifier.classify_path(Path('app.exe'))}")
    print(f"Unknown file: {classifier.classify_path(Path('unknown.xyz'))}")
    print(f"File with no suffix: {classifier.classify_path(Path('LICENSE'))}")

    # Test case sensitivity
    print(f"Python script (uppercase): {classifier.classify_path(Path('MY_SCRIPT.PY'))}")

    # Test multi-level directory
    print(f"Nested folder: {classifier.classify_path(Path('dir1/dir2'))}")
