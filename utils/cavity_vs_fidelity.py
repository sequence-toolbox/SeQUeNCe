def get_fidelity_by_cavity(C: int):
    """
    C: the cavity cooperativity
    50 <= C <= 500
    """
    gama = 14
    gama_star = 32
    delta_omega = 0
    gama_prime = (C + 1) * gama
    tau = gama_prime + 2 * gama_star
    F_e = 0.5 * (1 + gama_prime ** 2 / (tau ** 2 + delta_omega ** 2))
    return F_e
