from typing import List, Any

def format_table(headers: List[str], rows: List[List[Any]]) -> str:
    if not rows:
        return "No records found."
    
    # Calculate column widths
    col_widths = []
    for i in range(len(headers)):
        max_w = max(len(str(header)) for header in [headers[i]])
        for row in rows:
            max_w = max(max_w, len(str(row[i])))
        col_widths.append(max_w)

    # Create header string
    header_str = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    separator = "  ".join("-" * w for w in col_widths)
    
    # Create rows string
    row_strs = []
    for row in rows:
        row_strs.append("  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)))
    
    return f"{header_str}\n{separator}\n" + "\n".join(row_strs)