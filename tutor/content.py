"""Human-authored concept cards for each solution method.

These texts contain NO problem-specific numbers, so they need no sympy check. They are
written by the project team and should be reviewed by a teacher before use with learners.
Every number a learner sees comes from the verified engine (see explanations.py).
"""

METHODS = ["substitution", "elimination", "graphing",
           "cramers_rule", "inverse_matrix", "gaussian_elimination"]

LABEL = {
    "substitution": "Substitution",
    "elimination": "Elimination",
    "graphing": "Graphing",
    "cramers_rule": "Cramer's rule",
    "inverse_matrix": "Matrix inverse",
    "gaussian_elimination": "Gaussian elimination",
}

# Our skill id -> the matching OATutor skill tag (skillModel.json / bkt-params),
# so OATutor's knowledge-tracing parameters and later school data line up.
OATUTOR_SKILL = {
    "substitution": "solve_a_system_of_equations_by_substitution",
    "elimination": "solve_a_system_of_equations_by_elimination",
    "graphing": "solve_a_system_of_linear_equations_by_graphing",
    "cramers_rule": "solving_systems_with_cramer's_rule",
    "inverse_matrix": "solving_a_system_of_linear_equations_using_the_inverse_of_a_matrix",
    "gaussian_elimination": "solving_systems_with_gaussian_elimination",
}

CONCEPT = {
    "substitution": {
        "idea": "Turn two unknowns into one. Use one equation to say what one variable "
                "equals, then put that expression into the other equation.",
        "why": "Both equations describe the same pair of numbers, so an expression that is "
               "true in one can replace the variable in the other.",
        "steps": ["Pick an equation and solve it for one variable.",
                  "Substitute that expression into the other equation.",
                  "Solve the resulting one-variable equation.",
                  "Put that value back into your expression to get the other variable.",
                  "Check both values in both original equations."],
        "handy_when": "a variable already has coefficient 1 or -1.",
    },
    "elimination": {
        "idea": "Add or subtract the equations so that one variable cancels out.",
        "why": "Adding equal amounts to both sides keeps an equation true, so the sum or "
               "difference of two true equations is also true.",
        "steps": ["Multiply one or both equations so one variable has matching coefficients.",
                  "Subtract (or add) the equations to cancel that variable.",
                  "Solve for the remaining variable.",
                  "Substitute back into an original equation to find the other variable.",
                  "Check both values in both original equations."],
        "handy_when": "coefficients already match or are easy multiples of each other.",
    },
    "graphing": {
        "idea": "Each equation is a straight line; the solution is the point where the lines cross.",
        "why": "A point lies on a line exactly when its coordinates satisfy that line's "
               "equation, so the crossing point satisfies both.",
        "steps": ["Rewrite each equation in slope-intercept form, y = mx + b.",
                  "Use the slope and intercept of each line to sketch it.",
                  "Find the intersection point (set the two y-expressions equal to pin it down exactly).",
                  "Check the point in both original equations."],
        "handy_when": "you want to see the situation, e.g. no solution means parallel lines.",
    },
    "cramers_rule": {
        "idea": "Each variable equals a ratio of two determinants.",
        "why": "It is a closed-form formula that comes from solving the general system with "
               "letters instead of numbers.",
        "steps": ["Compute D, the determinant of the coefficient matrix (it must not be 0).",
                  "For each variable, replace its column with the constants and compute that determinant.",
                  "Divide: variable = (its determinant) / D.",
                  "Check the values in the original equations."],
        "handy_when": "the system is small and you want a formula-based approach.",
    },
    "inverse_matrix": {
        "idea": "Write the system as A·v = b and multiply both sides by the inverse of A.",
        "why": "Multiplying by A⁻¹ undoes A, just as dividing by a number undoes multiplying by it.",
        "steps": ["Write the coefficient matrix A and the constant vector b.",
                  "Check det(A) is not 0, then find A⁻¹.",
                  "Compute v = A⁻¹ b.",
                  "Read off the variables and check them."],
        "handy_when": "you need to solve several systems that share the same coefficients.",
    },
    "gaussian_elimination": {
        "idea": "Use row operations on the augmented matrix to reach a staircase (echelon) form, "
                "then solve from the bottom up.",
        "why": "Row operations (swap rows, scale a row, add a multiple of one row to another) "
               "never change the solution of the system.",
        "steps": ["Write the augmented matrix [A | b].",
                  "Use row operations to make zeros below each pivot, column by column.",
                  "Solve the last row, then back-substitute upwards.",
                  "Check the values in the original equations."],
        "handy_when": "the system is large (three or more variables).",
    },
}

# Scaffolding levels ("arms") the tutor can choose between. Order = most to least support.
ARMS = ["example", "faded", "outline", "none"]
ARM_LABEL = {
    "example": "See a fully worked example first",
    "faded": "Start me off (first steps done)",
    "outline": "Just remind me of the method",
    "none": "Let me try on my own",
}
