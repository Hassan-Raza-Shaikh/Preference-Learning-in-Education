"""Taxonomy derivation: map a problem's course/lesson to subject, topic and solution method.

Method labels are only assigned where the lesson makes the method unambiguous.
Lessons that mix methods (e.g. generic "two-variable systems") are labelled ["mixed"]
so downstream code can decide whether to verify the method from the solution text.
"""

# lessonId -> (topic, [methods]) for the systems-of-equations lessons.
# Methods use a controlled vocabulary so LLM-generated alternates can extend the list.
SYSTEMS_LESSONS = {
    "3KAZWfAj-a1xK-JGENtXHuqY": ("systems_of_equations", ["graphing"]),          # ElemAlg 5.1
    "4zdGE5Ei-8wVl-cZKs8Ew4Tw": ("systems_of_equations", ["substitution"]),      # ElemAlg 5.2
    "5ltDIouE-DMTy-nCCjmYpcqe": ("systems_of_equations", ["elimination"]),       # ElemAlg 5.3
    "6oUDx9FP-hLMS-jvmoCOwcM6": ("systems_of_equations", ["mixed"]),             # ElemAlg 5.4 applications
    "7bIqnFKK-kkEc-OVYV2Gxz8M": ("systems_of_equations", ["mixed"]),             # ElemAlg 5.5 mixture
    "1Xdf5hSE-1jt6-QS11MXdWU0": ("systems_of_inequalities", ["graphing"]),       # ElemAlg 5.6
    "1KMKWDko-uOWb-Ct5i8zDpJ3": ("systems_of_equations", ["mixed"]),             # IntAlg 4.1 two-var
    "2ZVevoun-iny5-EkBQXQ0LGY": ("systems_of_equations", ["mixed"]),             # IntAlg 4.2 applications
    "0FaEcs1a-iNFJ-gKaXDikMMA": ("systems_of_equations", ["mixed"]),             # IntAlg 4.3 mixture
    "15Enzgt5-JkPp-IuvKcY2z1l": ("systems_of_equations", ["mixed"]),             # IntAlg 4.4 three-var
    "4CyxN2i9-RL22-U4IY5GoNfA": ("systems_of_equations", ["matrices"]),          # IntAlg 4.5
    "4y6AShCa-27lB-qRezy0yMei": ("systems_of_equations", ["cramers_rule"]),      # IntAlg 4.6 determinants
    "55H3eILK-oFWG-ZccJ0OQLiK": ("systems_of_inequalities", ["graphing"]),       # IntAlg 4.7
    "5nAAxKhT-x2dY-6Rbz2pSivj": ("nonlinear_systems", ["mixed"]),               # IntAlg 11.5
    "3aMZNfMb-negJ-8QWkColcJN": ("systems_of_equations", ["mixed"]),             # CollAlg 7.1 two-var
    "4q5nZauP-1cJW-SPjxuTKxSO": ("systems_of_equations", ["mixed"]),             # CollAlg 7.2 three-var
    "63meyj47-76Du-3OIso8ikv7": ("nonlinear_systems", ["mixed"]),               # CollAlg 7.3
    "19TtHZ3i-e6bp-RkinOCKNtx": ("systems_of_equations", ["matrices"]),          # CollAlg 7.5
    "5jWomuQb-zLms-pvKcgRHvn6": ("systems_of_equations", ["gaussian_elimination"]),  # CollAlg 7.6
    "3BQInFnI-o1w1-YlOnrFwJf2": ("systems_of_equations", ["inverse_matrix"]),    # CollAlg 7.7
    "3Vwnph6Y-8qd1-KWLU6rYV5u": ("systems_of_equations", ["cramers_rule"]),      # CollAlg 7.8
    "1Gld8WGt-4kH1-eTIIKJapPE": ("systems_of_equations", ["mixed"]),             # PreCalc 9.1 two-var
    "7LKfL5EA-NRtR-wvxHK37xun": ("systems_of_equations", ["mixed"]),             # PreCalc 9.2 three-var
    "0FGiQEOT-8xMS-EXTYEofIOl": ("nonlinear_systems", ["mixed"]),               # PreCalc 9.3
    "6ixmGxqc-VtKA-46bfoPXh4G": ("systems_of_equations", ["matrices"]),          # PreCalc 9.5
    "3yI1wb2J-VQJW-mqsijIUx0j": ("systems_of_equations", ["gaussian_elimination"]),  # PreCalc 9.6
    "2eq6xYSq-GAsz-hiLumqxyjY": ("systems_of_equations", ["inverse_matrix"]),    # PreCalc 9.7
    "1cDQ1ynl-ysgp-soSElnCJso": ("systems_of_equations", ["cramers_rule"]),      # PreCalc 9.8
}

# courseName -> coarse subject label.
COURSE_SUBJECT = {
    "OpenStax: Elementary Algebra": "algebra",
    "OpenStax: Intermediate Algebra": "algebra",
    "OpenStax: College Algebra": "algebra",
    "Solid Foundations: Algebra": "algebra",
    "SJSU 1018": "algebra",
    "SJSU 1019S": "algebra",
    "OpenStax: Pre-Calculus": "precalculus",
    "Pre-Calculus Essentials (UC Berkeley Math 1B)": "precalculus",
    "Solid Foundations: Trigonometry": "trigonometry",
    "OpenStax: Calculus Volume 1": "calculus",
    "SJSU Calculus 1 (Quiz Collection)": "calculus",
    "Solid Foundations: Calculus Part 1": "calculus",
    "Mission College: Introductory Statistics": "statistics",
    "OpenStax: Introductory Stats": "statistics",
    "Data 8 Discussion Worksheets": "data_science",
    "Combined Data100 Worksheets": "data_science",
    "OpenStax: College Physics": "physics",
    "OpenStax: University Physics": "physics",
    "Math Basics for Physics": "physics",
    "Chemistry 1A Summer Content": "chemistry",
    "Matematik 4": "mathematics",
}

# courseName -> ISO language.
COURSE_LANGUAGE = {"Matematik 4": "se"}


def derive_taxonomy(course_name, lesson_id):
    """Return (subject, topic, methods, language)."""
    subject = COURSE_SUBJECT.get(course_name, "unknown")
    language = COURSE_LANGUAGE.get(course_name, "en")
    if lesson_id in SYSTEMS_LESSONS:
        topic, methods = SYSTEMS_LESSONS[lesson_id]
    else:
        topic, methods = None, []
    return subject, topic, methods, language
