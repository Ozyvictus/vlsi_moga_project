"""A compact, self-contained real-coded NSGA-II implementation.

Implements non-dominated sorting, crowding distance, binary tournament
selection, simulated binary crossover (SBX), and polynomial mutation.
"""

from __future__ import annotations

import numpy as np


def dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """True when a is no worse than b in every objective and better in one."""
    return bool(np.all(a <= b) and np.any(a < b))


def non_dominated_sort(F: np.ndarray) -> list[list[int]]:
    """Vectorized non-dominated sorting; returns fronts as lists of indices."""
    n = len(F)
    # domination[p, q] is True when solution p dominates solution q.
    no_worse = np.all(F[:, None, :] <= F[None, :, :], axis=2)
    strictly_better = np.any(F[:, None, :] < F[None, :, :], axis=2)
    domination = no_worse & strictly_better

    domination_count = domination.sum(axis=0).astype(int)
    dominated = [np.flatnonzero(domination[p]).tolist() for p in range(n)]
    current = np.flatnonzero(domination_count == 0).tolist()

    fronts: list[list[int]] = []
    while current:
        fronts.append(current)
        next_front: list[int] = []
        for p in current:
            for q in dominated[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    next_front.append(q)
        current = next_front

    return fronts


def crowding_distance(F: np.ndarray, front: list[int]) -> dict[int, float]:
    """Calculate objective-space crowding distance for one non-dominated front."""
    distances = {idx: 0.0 for idx in front}
    if len(front) <= 2:
        for idx in front:
            distances[idx] = float("inf")
        return distances

    front_values = F[front]
    n_objectives = F.shape[1]

    for objective in range(n_objectives):
        order_local = np.argsort(front_values[:, objective])
        ordered_indices = [front[i] for i in order_local]
        distances[ordered_indices[0]] = float("inf")
        distances[ordered_indices[-1]] = float("inf")

        low = front_values[order_local[0], objective]
        high = front_values[order_local[-1], objective]
        span = high - low
        if span <= 1e-14:
            continue

        for position in range(1, len(ordered_indices) - 1):
            idx = ordered_indices[position]
            if np.isinf(distances[idx]):
                continue
            previous_value = F[ordered_indices[position - 1], objective]
            next_value = F[ordered_indices[position + 1], objective]
            distances[idx] += (next_value - previous_value) / span

    return distances


def rank_and_crowding(F: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[list[int]]]:
    """Return each individual's front rank and crowding distance."""
    fronts = non_dominated_sort(F)
    ranks = np.empty(len(F), dtype=int)
    distances = np.zeros(len(F), dtype=float)
    for rank, front in enumerate(fronts):
        for idx in front:
            ranks[idx] = rank
        front_distances = crowding_distance(F, front)
        for idx, distance in front_distances.items():
            distances[idx] = distance
    return ranks, distances, fronts


def tournament_select(
    ranks: np.ndarray, distances: np.ndarray, rng: np.random.Generator
) -> int:
    """Binary tournament: lower rank wins, then higher crowding distance."""
    a, b = rng.integers(0, len(ranks), size=2)
    if ranks[a] < ranks[b]:
        return int(a)
    if ranks[b] < ranks[a]:
        return int(b)
    if distances[a] > distances[b]:
        return int(a)
    if distances[b] > distances[a]:
        return int(b)
    return int(a if rng.random() < 0.5 else b)


def sbx_crossover(
    parent_a: np.ndarray,
    parent_b: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    rng: np.random.Generator,
    probability: float = 0.9,
    eta: float = 15.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulated binary crossover for bounded real-valued chromosomes."""
    child_a = parent_a.copy()
    child_b = parent_b.copy()
    if rng.random() > probability:
        return child_a, child_b

    for j in range(len(parent_a)):
        if rng.random() > 0.5 or abs(parent_a[j] - parent_b[j]) < 1e-14:
            continue

        y1 = min(parent_a[j], parent_b[j])
        y2 = max(parent_a[j], parent_b[j])
        rand = rng.random()

        beta = 1.0 + (2.0 * (y1 - lower[j]) / (y2 - y1))
        alpha = 2.0 - beta ** (-(eta + 1.0))
        if rand <= 1.0 / alpha:
            beta_q = (rand * alpha) ** (1.0 / (eta + 1.0))
        else:
            beta_q = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1.0))
        c1 = 0.5 * ((y1 + y2) - beta_q * (y2 - y1))

        beta = 1.0 + (2.0 * (upper[j] - y2) / (y2 - y1))
        alpha = 2.0 - beta ** (-(eta + 1.0))
        if rand <= 1.0 / alpha:
            beta_q = (rand * alpha) ** (1.0 / (eta + 1.0))
        else:
            beta_q = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1.0))
        c2 = 0.5 * ((y1 + y2) + beta_q * (y2 - y1))

        c1 = np.clip(c1, lower[j], upper[j])
        c2 = np.clip(c2, lower[j], upper[j])
        if rng.random() < 0.5:
            child_a[j], child_b[j] = c2, c1
        else:
            child_a[j], child_b[j] = c1, c2

    return child_a, child_b


def polynomial_mutation(
    chromosome: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    rng: np.random.Generator,
    probability: float | None = None,
    eta: float = 20.0,
) -> np.ndarray:
    """Polynomial mutation for bounded real-valued chromosomes."""
    mutated = chromosome.copy()
    if probability is None:
        probability = 1.0 / len(mutated)

    for j in range(len(mutated)):
        if rng.random() >= probability or upper[j] <= lower[j]:
            continue

        y = mutated[j]
        delta1 = (y - lower[j]) / (upper[j] - lower[j])
        delta2 = (upper[j] - y) / (upper[j] - lower[j])
        rand = rng.random()
        mutation_power = 1.0 / (eta + 1.0)

        if rand < 0.5:
            xy = 1.0 - delta1
            value = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta + 1.0))
            delta_q = value ** mutation_power - 1.0
        else:
            xy = 1.0 - delta2
            value = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta + 1.0))
            delta_q = 1.0 - value ** mutation_power

        y += delta_q * (upper[j] - lower[j])
        mutated[j] = np.clip(y, lower[j], upper[j])

    return mutated


def evaluate_population(population: np.ndarray, objective_function) -> np.ndarray:
    """Evaluate all chromosomes using a function returning objective values."""
    return np.asarray([objective_function(individual) for individual in population], dtype=float)


def environmental_selection(
    population: np.ndarray, objectives: np.ndarray, population_size: int
) -> tuple[np.ndarray, np.ndarray]:
    """Select the next generation by fronts, then crowding distance."""
    _, _, fronts = rank_and_crowding(objectives)
    selected: list[int] = []

    for front in fronts:
        remaining = population_size - len(selected)
        if remaining <= 0:
            break
        if len(front) <= remaining:
            selected.extend(front)
        else:
            distances = crowding_distance(objectives, front)
            front_by_crowding = sorted(front, key=lambda i: distances[i], reverse=True)
            selected.extend(front_by_crowding[:remaining])
            break

    return population[selected], objectives[selected]


def run_nsga2(
    objective_function,
    lower_bounds: np.ndarray,
    upper_bounds: np.ndarray,
    population_size: int = 120,
    generations: int = 180,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[tuple[int, float, float]]]:
    """Run NSGA-II and return Pareto decision vectors, objectives, and history."""
    if population_size < 4:
        raise ValueError("population_size must be at least 4")
    if generations < 1:
        raise ValueError("generations must be positive")

    rng = np.random.default_rng(seed)
    lower = np.asarray(lower_bounds, dtype=float)
    upper = np.asarray(upper_bounds, dtype=float)
    if lower.shape != upper.shape or np.any(lower >= upper):
        raise ValueError("Bounds must have identical shapes and lower < upper")

    population = rng.uniform(lower, upper, size=(population_size, len(lower)))
    objectives = evaluate_population(population, objective_function)
    history: list[tuple[int, float, float]] = []

    for generation in range(generations + 1):
        history.append((
            generation,
            float(np.min(objectives[:, 0])),
            float(np.min(objectives[:, 1])),
        ))
        if generation == generations:
            break

        ranks, distances, _ = rank_and_crowding(objectives)
        offspring: list[np.ndarray] = []
        while len(offspring) < population_size:
            parent_a_idx = tournament_select(ranks, distances, rng)
            parent_b_idx = tournament_select(ranks, distances, rng)
            child_a, child_b = sbx_crossover(
                population[parent_a_idx], population[parent_b_idx],
                lower, upper, rng,
            )
            child_a = polynomial_mutation(child_a, lower, upper, rng)
            child_b = polynomial_mutation(child_b, lower, upper, rng)
            offspring.extend((child_a, child_b))

        offspring_array = np.asarray(offspring[:population_size], dtype=float)
        offspring_objectives = evaluate_population(offspring_array, objective_function)

        combined_population = np.vstack((population, offspring_array))
        combined_objectives = np.vstack((objectives, offspring_objectives))
        population, objectives = environmental_selection(
            combined_population, combined_objectives, population_size
        )

    # The first front of the final population is the returned Pareto set.
    final_front = non_dominated_sort(objectives)[0]
    pareto_X = population[final_front]
    pareto_F = objectives[final_front]
    sort_order = np.argsort(pareto_F[:, 0])
    return pareto_X[sort_order], pareto_F[sort_order], history
