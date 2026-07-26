import logging
from typing import Optional

logger = logging.getLogger(__name__)

class QlibAdapter:
    """
    Anti-Corruption Layer (ACL) for Microsoft Qlib.
    Encapsulates all Qlib interactions to prevent Qlib types from leaking into Aegis core.
    """
    def __init__(self):
        self._initialized = False

    def initialize(self, provider_uri: Optional[str] = None) -> bool:
        """
        Initializes the Qlib backend.
        Returns True if successful, False otherwise.
        """
        try:
            import qlib
            # Minimal initialization. For full backtesting, provider_uri points to dataset.
            qlib.init(provider_uri=provider_uri or "~/.qlib/qlib_data/cn_data")
            self._initialized = True
            logger.info("QlibAdapter: Successfully initialized Microsoft Qlib.")
            return True
        except ImportError:
            logger.error("QlibAdapter: pyqlib is not installed.")
            return False
        except Exception as e:
            logger.error(f"QlibAdapter: Failed to initialize Qlib. Error: {e}")
            return False

    def is_available(self) -> bool:
        """
        Returns whether Qlib is correctly installed and initialized.
        """
        return self._initialized
