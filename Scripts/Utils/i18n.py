# -*- coding: utf-8 -*-
"""
i18n.py

Internationalization utility for managing UI strings in multiple languages.
"""
import json
import logging
from pathlib import Path

class I18N:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(I18N, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'): return
        self.translations = {}
        self.load_translations()
        
        # Load language from config
        self.current_lang = self._load_lang_from_config()
        self._initialized = True

    def _load_lang_from_config(self):
        config_path = Path(__file__).parent.parent.parent / "Resources" / "config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("language", "ko")
        except Exception:
            pass
        return "ko"

    def load_translations(self):
        lang_dir = Path(__file__).parent.parent.parent / "Resources" / "Language"
        for lang_file in lang_dir.glob("*.json"):
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self.translations[lang_file.stem] = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load translation file {lang_file}: {e}")

    def set_language(self, lang):
        if lang in self.translations:
            self.current_lang = lang
            # Save to config
            self._save_lang_to_config(lang)
        else:
            logging.warning(f"Language '{lang}' not found. Staying with '{self.current_lang}'.")

    def _save_lang_to_config(self, lang):
        config_path = Path(__file__).parent.parent.parent / "Resources" / "config.json"
        try:
            config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            config["language"] = lang
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save language to config: {e}")

    def t(self, key_path, **kwargs):
        """
        Translates a key path (e.g., 'ui.title') to the current language.
        """
        try:
            keys = key_path.split('.')
            data = self.translations.get(self.current_lang, {})
            for k in keys:
                if isinstance(data, dict):
                    if k in data:
                        data = data[k]
                    else:
                        return key_path # Key not found in dict
                else:
                    return key_path # Current level is not a dict, can't go deeper
            
            if isinstance(data, str):
                return data.format(**kwargs)
            return data
        except Exception:
            return key_path

# Global instance
_i18n_instance = I18N()

def t(key_path, **kwargs):
    return _i18n_instance.t(key_path, **kwargs)

def set_language(lang):
    _i18n_instance.set_language(lang)

def get_current_language():
    return _i18n_instance.current_lang
