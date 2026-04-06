"""Shared Rich theme for xxcli terminal output."""

from rich.theme import Theme

xx_theme = Theme(
    {
        "xx.author": "bold",
        "xx.handle": "dim",
        "xx.content": "",
        "xx.metrics": "dim",
        "xx.accent": "cyan",
        "xx.success": "green",
        "xx.error": "red bold",
        "xx.warning": "yellow",
        "xx.info": "blue",
        "xx.key": "cyan",
        "xx.dim": "dim",
    }
)
