# Simple config module for iLOrest compatibility

import os
import json

class Config:
    """Basic configuration handling"""
    def __init__(self):
        self.config_data = {}
    
    def get(self, key, default=None):
        return self.config_data.get(key, default)
    
    def set(self, key, value):
        self.config_data[key] = value

# Default config instance
default_config = Config()

# Make it available for direct import
__all__ = ['Config', 'default_config']