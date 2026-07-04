def update_ratings(rating_a: int, rating_b: int, outcome_a: float, k: int = 32) -> tuple[int, int]:
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 - expected_a
    outcome_b = 1 - outcome_a
    return (
        round(rating_a + k * (outcome_a - expected_a)),
        round(rating_b + k * (outcome_b - expected_b)),
    )
