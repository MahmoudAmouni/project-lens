"""Rank the rows of several tables together, so "the most expensive item" is found across every sheet at once."""


def rank_across_tables(results: list[dict], descending: bool, keep: int) -> list[dict]:
    """The best `keep` rows of all results together, by each result's sort column. Each row says its table.

    Every result already holds its own best rows (sorted, cut at the limit), so the overall best are among them.
    Rows with no number in the sort column come last."""
    numbered, others = [], []
    for result in results:
        column = result.get("sort_column")
        for row in result["rows"]:
            ranked_row = {"document": result["document"], "table_id": result["table_id"], **row}
            value = row.get(column)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numbered.append((value, ranked_row))
            else:
                others.append(ranked_row)
    numbered.sort(key=lambda item: item[0], reverse=descending)
    return ([row for _, row in numbered] + others)[:keep]


def keep_overall_best(results: list[dict], best: list[dict]) -> None:
    """Cut every result's rows to the rows in `best`, so the saved table holds the overall best only."""
    wanted = {(row["document"], row["table_id"], row["row"]) for row in best}
    for result in results:
        table = (result["document"], result["table_id"])
        result["rows"] = [row for row in result["rows"] if (*table, row["row"]) in wanted]
