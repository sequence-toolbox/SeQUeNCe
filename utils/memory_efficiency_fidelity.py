def get_fidelity_by_efficiency(e: float, C: int):
    """
    e: efficiency of memory
    0 <= e <= 1
    C: the cavity cooperativity
    100 <= C <= 500
    """
    return 0.5 + 0.5 * (49 * C ** 2) / (4 * (379 / 3) ** 2 * e ** 2 + 28 * C * (379 / 3) * e + 49 * C ** 2)


print(get_fidelity_by_efficiency(0.2, 100))
