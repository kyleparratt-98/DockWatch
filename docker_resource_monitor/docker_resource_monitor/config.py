"""
Configuration management for Docker Resource Monitor.
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Predefined color themes for validation
VALID_COLOR_THEMES = {"default", "dark", "light", "monochrome"}

# Try to use tomllib (Python 3.11+), fallback to tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        logger.error("tomli package is required for Python < 3.11")
        raise ImportError(
            "Please install tomli: pip install tomli"
        )


@dataclass
class Config:
    """Configuration class for Docker Resource Monitor."""
    
    # Default values
    refresh_interval: int = 2
    color_theme: str = "default"
    container_filter: List[str] = field(default_factory=list)
    use_docker_api: bool = False
    warning_banner: str = ""
    
    def _validate_refresh_interval(self, value: int) -> None:
        """Validate refresh interval value."""
        if not isinstance(value, int) or value < 1:
            raise ValueError(
                f"refresh_interval must be a positive integer, got {value}"
            )
    
    def _validate_color_theme(self, value: str) -> None:
        """Validate color theme value."""
        if value not in VALID_COLOR_THEMES:
            raise ValueError(
                f"color_theme must be one of {VALID_COLOR_THEMES}, got '{value}'"
            )
    
    def load_from_file(self, path: str) -> None:
        """
        Load configuration from a TOML file.
        
        Args:
            path: Path to the configuration file.
            
        Raises:
            FileNotFoundError: If the configuration file does not exist.
            tomllib.TOMLDecodeError: If the TOML file is malformed.
            ValueError: If configuration values are invalid.
        """
        config_path = Path(path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        try:
            with open(config_path, 'rb') as f:
                config_data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Failed to parse TOML configuration file: {e}")
            raise
        
        # Store original values for rollback on validation failure
        original_values = {
            'refresh_interval': self.refresh_interval,
            'color_theme': self.color_theme,
            'container_filter': self.container_filter.copy(),
            'use_docker_api': self.use_docker_api,
            'warning_banner': self.warning_banner,
        }
        
        try:
            # Update configuration from file with validation
            if 'refresh_interval' in config_data:
                refresh_value = int(config_data['refresh_interval'])
                self._validate_refresh_interval(refresh_value)
                self.refresh_interval = refresh_value
            
            if 'color_theme' in config_data:
                theme_value = str(config_data['color_theme'])
                self._validate_color_theme(theme_value)
                self.color_theme = theme_value
            
            if 'container_filter' in config_data:
                filter_value = config_data['container_filter']
                if not isinstance(filter_value, list):
                    filter_value = [filter_value]
                self.container_filter = [str(item) for item in filter_value]
            
            if 'use_docker_api' in config_data:
                self.use_docker_api = bool(config_data['use_docker_api'])
            
            if 'warning_banner' in config_data:
                self.warning_banner = str(config_data['warning_banner'])
                
        except (ValueError, TypeError) as e:
            # Rollback to original values on validation failure
            logger.warning(f"Invalid configuration value: {e}, rolling back to previous values")
            self.refresh_interval = original_values['refresh_interval']
            self.color_theme = original_values['color_theme']
            self.container_filter = original_values['container_filter']
            self.use_docker_api = original_values['use_docker_api']
            self.warning_banner = original_values['warning_banner']
            raise
    
    def get_refresh_interval(self) -> int:
        """
        Get the refresh interval in seconds.
        
        Returns:
            Refresh interval in seconds.
        """
        return self.refresh_interval
    
    def get_color_theme(self) -> str:
        """
        Get the color theme name.
        
        Returns:
            Color theme name.
        """
        return self.color_theme
    
    def get_container_filter(self) -> Tuple[str, ...]:
        """
        Get the list of container IDs/names to filter.
        
        Returns:
            Tuple of container IDs/names (immutable).
        """
        return tuple(self.container_filter)
    
    def get_use_docker_api(self) -> bool:
        """
        Check if Docker API fallback should be used.
        
        Returns:
            True if Docker API should be used, False otherwise.
        """
        return self.use_docker_api
    
    def set_use_docker_api(self, value: bool) -> None:
        """
        Set whether to use Docker API fallback.
        
        Args:
            value: True to use Docker API, False to use direct filesystem access.
        """
        self.use_docker_api = bool(value)
    
    def get_warning_banner(self) -> str:
        """
        Get the current warning banner text.
        
        Returns:
            Warning banner text.
        """
        return self.warning_banner
    
    def set_warning_banner(self, value: str) -> None:
        """
        Set the warning banner text.
        
        Args:
            value: Warning banner text.
        """
        self.warning_banner = str(value)
    
    def __str__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"Config(refresh_interval={self.refresh_interval}, "
            f"color_theme='{self.color_theme}', "
            f"container_filter={self.container_filter}, "
            f"use_docker_api={self.use_docker_api}, "
            f"warning_banner='{self.warning_banner}')"
        )


def load_default_config() -> Config:
    """
    Load default configuration.
    
    Returns:
        Default configuration instance.
    """
    config = Config()
    
    # Try to load from default config file if it exists
    default_config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'config.toml'
    )
    
    if os.path.exists(default_config_path):
        try:
            config.load_from_file(default_config_path)
            logger.info(f"Configuration loaded from {default_config_path}")
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {default_config_path}")
        except tomllib.TOMLDecodeError as e:
            logger.warning(f"Malformed TOML configuration file {default_config_path}: {e}")
        except ValueError as e:
            logger.warning(f"Invalid configuration values in {default_config_path}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error loading configuration from {default_config_path}: {e}")
    
    return config
