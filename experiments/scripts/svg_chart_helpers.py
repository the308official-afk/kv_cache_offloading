"""Small SVG chart layout helpers shared by microbenchmark plotters."""

from __future__ import annotations


def visible_tick_indexes(count: int, *, max_labels: int = 11) -> set[int]:
    """Return evenly spaced tick indexes, always keeping first and last."""
    if count <= 0:
        return set()
    if count <= max_labels:
        return set(range(count))
    if max_labels <= 1:
        return {0}

    indexes = {0, count - 1}
    span = count - 1
    for step in range(1, max_labels - 1):
        indexes.add(round(step * span / (max_labels - 1)))
    return indexes


def visible_point_label_indexes(values: list[float], *, max_labels: int = 7) -> set[int]:
    """Return sparse point-label indexes, emphasizing endpoints and extremes."""
    count = len(values)
    if count <= 0:
        return set()
    if count <= max_labels:
        return set(range(count))

    indexes = {0, count - 1}
    numeric = [(idx, value) for idx, value in enumerate(values)]
    if numeric:
        indexes.add(max(numeric, key=lambda item: item[1])[0])
        indexes.add(min(numeric, key=lambda item: item[1])[0])

    for idx in visible_tick_indexes(count, max_labels=max_labels):
        indexes.add(idx)
        if len(indexes) >= max_labels:
            break
    return indexes


def numeric_label_positions(labels: list[str]) -> list[float] | None:
    """Parse labels into numeric x-axis positions when all labels are numeric."""
    parsed: list[float] = []
    for label in labels:
        try:
            parsed.append(float(str(label).replace(",", "")))
        except ValueError:
            return None
    if not parsed or min(parsed) == max(parsed):
        return None
    return parsed


def x_position_from_index(
    *,
    index: int,
    count: int,
    labels: list[str],
    left: int,
    plot_width: int,
) -> float:
    numeric_positions = numeric_label_positions(labels)
    if numeric_positions is not None:
        min_x = min(numeric_positions)
        max_x = max(numeric_positions)
        return left + ((numeric_positions[index] - min_x) / (max_x - min_x)) * plot_width
    return left + (index * (plot_width / max(count - 1, 1)) if count > 1 else plot_width / 2)
