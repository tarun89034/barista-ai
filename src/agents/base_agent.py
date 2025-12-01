"""Base Agent class for all Barista AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from datetime import datetime


class BaseAgent(ABC):
    """Abstract base class for all agents in the Barista AI system.
    
    This class provides common functionality for logging, error handling,
    and state management that all agents can inherit.
    
    Attributes:
        name (str): The name of the agent.
        logger (logging.Logger): Logger instance for the agent.
        state (Dict[str, Any]): Agent state dictionary.
        created_at (datetime): Timestamp when agent was created.
    """
    
    def __init__(self, name: str, log_level: str = "INFO"):
        """Initialize the base agent.
        
        Args:
            name: Name of the agent.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        self.name = name
        self.state: Dict[str, Any] = {}
        self.created_at = datetime.now()
        
        # Set up logging
        self.logger = self._setup_logger(log_level)
        self.logger.info(f"{self.name} initialized at {self.created_at}")
    
    def _setup_logger(self, log_level: str) -> logging.Logger:
        """Set up logger for the agent.
        
        Args:
            log_level: Logging level as string.
            
        Returns:
            Configured logger instance.
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create console handler if not already exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(getattr(logging, log_level.upper()))
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """Process the agent's main task.
        
        This method must be implemented by all subclasses.
        
        Returns:
            Result of the agent's processing.
        """
        pass
    
    def validate_input(self, data: Any) -> bool:
        """Validate input data.
        
        Args:
            data: Input data to validate.
            
        Returns:
            True if validation passes, False otherwise.
        """
        if data is None:
            self.logger.error("Input data is None")
            return False
        return True
    
    def update_state(self, key: str, value: Any) -> None:
        """Update agent state.
        
        Args:
            key: State key.
            value: State value.
        """
        self.state[key] = value
        self.logger.debug(f"State updated: {key} = {value}")
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from agent state.
        
        Args:
            key: State key.
            default: Default value if key not found.
            
        Returns:
            State value or default.
        """
        return self.state.get(key, default)
    
    def clear_state(self) -> None:
        """Clear agent state."""
        self.state.clear()
        self.logger.debug("Agent state cleared")
    
    def handle_error(self, error: Exception, context: Optional[str] = None) -> None:
        """Handle errors with logging.
        
        Args:
            error: Exception that occurred.
            context: Optional context information.
        """
        error_msg = f"Error in {self.name}"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"
        
        self.logger.error(error_msg, exc_info=True)
        self.update_state("last_error", str(error))
        self.update_state("last_error_time", datetime.now())
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information.
        
        Returns:
            Dictionary containing agent information.
        """
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "state": self.state,
            "uptime": (datetime.now() - self.created_at).total_seconds()
        }
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}')"