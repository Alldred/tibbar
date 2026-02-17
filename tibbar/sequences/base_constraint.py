# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Base class for constraint-based sequences."""

from constraint import Problem


class BaseConstraint:
    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.random = self.tibbar.random
        self.reset_problem()

    def get_rand_solution(self, problem: Problem | None = None) -> dict:
        _problem = problem if problem is not None else self.problem
        all_solutions_unsorted = _problem.getSolutions()
        if not all_solutions_unsorted:
            raise ValueError("No solutions")
        keys = sorted(all_solutions_unsorted[0].keys())
        all_solutions = sorted(
            all_solutions_unsorted,
            key=lambda d: tuple(d[k] for k in keys),
        )
        return self.random.choice(all_solutions)

    def reset_problem(self) -> None:
        self.problem = Problem()

    def new_problem(self) -> Problem:
        return Problem()
