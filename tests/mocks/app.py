from blue_lugia.app import App
from blue_lugia.state import StateManager


class MockApp(App):
    def save_exception(self, e: Exception, state: StateManager) -> None:
        pass
