from datetime import datetime


class Logger:
    def __init__(self, is_verbose: bool) -> None:
        self.is_verbose: bool = is_verbose

    def message(self, text: str, force_display: bool = False) -> None:
        if self.is_verbose or force_display:
            timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            print(f"[{timestamp}]\t{text}")

    def warning(self, text: str) -> None:
        self.message(f"WARNING - {text}", force_display=True)
