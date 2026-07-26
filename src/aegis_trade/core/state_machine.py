from typing import TypeVar, Generic, Mapping, Protocol
from aegis_trade.core.exceptions import StateMachineError

StateT = TypeVar("StateT")
EventT = TypeVar("EventT")

class TransitionValidator(Protocol, Generic[StateT, EventT]):
    def validate(self, current_state: StateT, event: EventT, context: Mapping[str, str]) -> None:
        ...

class StateMachineEngine(Generic[StateT, EventT]):
    """
    Generic core engine for state machines.
    Maintains strict separation of concerns by operating on generic State/Event types.
    """
    def __init__(
        self, 
        initial_state: StateT, 
        transitions: dict[tuple[StateT, EventT], StateT],
        validators: list[TransitionValidator[StateT, EventT]] | None = None
    ):
        self._current_state = initial_state
        self._transitions = transitions
        self._validators = validators or []
        
    @property
    def current_state(self) -> StateT:
        return self._current_state
        
    def transition(self, event: EventT, context: Mapping[str, str] | None = None) -> StateT:
        context = context or {}
        
        if (self._current_state, event) not in self._transitions:
            raise StateMachineError(f"Invalid transition from {self._current_state} with event {event}")
            
        next_state = self._transitions[(self._current_state, event)]
        
        for validator in self._validators:
            validator.validate(self._current_state, event, context)
            
        self._current_state = next_state
        return self._current_state

# Alias for backward compatibility
BaseStateMachine = StateMachineEngine
