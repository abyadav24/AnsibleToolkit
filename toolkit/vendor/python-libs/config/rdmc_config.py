# RDMC Config submodule for iLOrest compatibility

class RdmcConfig:
    """RDMC Configuration class"""
    def __init__(self):
        self.config_dict = {}
    
    def get_config(self, key, default=None):
        return self.config_dict.get(key, default)
    
    def set_config(self, key, value):
        self.config_dict[key] = value

# Default instance
rdmc_config = RdmcConfig()

__all__ = ['RdmcConfig', 'rdmc_config']