# Compatibility module for versioning
# This provides backward compatibility for the 'versioning' module

try:
    from packaging import version
    from packaging.version import Version, parse
    # Re-export common versioning functions
    __all__ = ['Version', 'parse', 'version']
except ImportError:
    # Fallback implementation
    class Version:
        def __init__(self, version_string):
            self.version_string = str(version_string)
        
        def __str__(self):
            return self.version_string
        
        def __eq__(self, other):
            return str(self) == str(other)
        
        def __lt__(self, other):
            return str(self) < str(other)
    
    def parse(version_string):
        return Version(version_string)
    
    version = parse
    __all__ = ['Version', 'parse', 'version']