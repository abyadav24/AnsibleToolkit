# Dummy rdmc_base_classes module for iLOrest compatibility
# This provides basic classes that iLOrest might expect

class RDMCCoreBase:
    """Base class for RDMC core functionality"""
    pass

class RDMCCommandBase:
    """Base class for RDMC commands"""
    pass

class RDMCError(Exception):
    """Base exception class for RDMC errors"""
    pass

# Hardcoded list that some commands might expect
HARDCODEDLIST = []

# Make these available for import
__all__ = ['RDMCCoreBase', 'RDMCCommandBase', 'RDMCError', 'HARDCODEDLIST']