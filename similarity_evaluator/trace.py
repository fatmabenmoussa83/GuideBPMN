"""Small, dependency-free tracing utility shared by every module."""

TRACE_ENABLED = True


def trace(module: str, message: str):
    if TRACE_ENABLED:
        print(f"  [{module:<10}] {message}")


def section(module: str, title: str):
    if TRACE_ENABLED:
        print(f"\n  [{module:<10}] ==== {title} ====")


def trace_table(module: str, rows, headers, max_rows=30):
    if not TRACE_ENABLED:
        return
    rows = [list(map(lambda x: str(x), row)) for row in list(rows)[:max_rows]]
    headers = list(map(str, headers))
    if not rows:
        trace(module, "(empty table)")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, value in enumerate(row[:len(widths)]):
            widths[i] = min(55, max(widths[i], len(value)))
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)
    trace(module, fmt.format(*headers))
    trace(module, "-+-".join("-" * w for w in widths))
    for row in rows:
        clipped = [v[:widths[i]] for i, v in enumerate(row[:len(widths)])]
        trace(module, fmt.format(*clipped))

