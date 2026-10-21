"""External comparison adapters; Rust JSONL remains the rules authority."""


def coordinate(move: int) -> str:
    """Rust row-major index 0 is external square a1."""
    if type(move) is not int or not 0 <= move < 64:
        raise ValueError("move must be an integer in 0..64")
    return f"{chr(ord('a') + move % 8)}{move // 8 + 1}"


def move_index(square: str) -> int | None:
    square = square.lower()
    if square in ("pa", "ps", "pass", "--"):
        return None
    if len(square) != 2 or square[0] not in "abcdefgh" or square[1] not in "12345678":
        raise ValueError(f"invalid engine move: {square!r}")
    return (int(square[1]) - 1) * 8 + ord(square[0]) - ord("a")
