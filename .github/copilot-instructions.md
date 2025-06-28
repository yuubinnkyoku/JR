# JR West Delay Bot Instructions

## High-level architecture

This is a Python-based Discord bot that provides train delay information for JR West.

-   **`main.py`**: The main application file. It contains the Discord bot logic, including commands and event handlers.
-   **External APIs**: The bot fetches data from the JR West train guide API (`https://www.train-guide.westjr.co.jp/api/v3/`).
-   **Dependencies**: The project uses `discord.py` for the bot and `requests` for making HTTP requests to the API. Dependencies are managed in `pyproject.toml`.
-   **Configuration**: The Discord bot token is managed in `env/config.py`.

## Core commands

-   **Running the bot**: The main entry point is `main.py`. To run the bot, execute `python main.py`.
-   **Dependencies**: Install dependencies using `pip install -r requirements.txt` (or from `pyproject.toml` if using a modern package manager like Poetry or PDM).
-   **Testing**: There is no formal test suite. `test.py` is a simple script for fetching line data and is not a test file.

## Repo-specific style rules

-   **Formatting**: Follow standard Python formatting (PEP 8).
-   **Typing**: Use type hints for function signatures.
-   **Error Handling**: Wrap API calls and other potentially failing operations in `try...except` blocks. Log errors or send them to the Discord channel.
-   **Naming**: Use descriptive names for variables and functions.
