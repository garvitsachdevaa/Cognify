"""
Seed script — populates Postgres with a rich set of JEE Maths questions.
Run: python seed_questions.py   (from backend/ directory)
Clears ALL existing questions and re-seeds from scratch.
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from app.db import SessionLocal
from sqlalchemy import text as _text

# (question_text, [subtopics], difficulty 1-5)
SEED_QUESTIONS = [
    # Integration by Parts
    (r"Evaluate $\int x \cdot e^x \, dx$", ["integration_by_parts"], 2),
    (r"Evaluate $\int x \cdot \sin(x) \, dx$", ["integration_by_parts"], 2),
    (r"Evaluate $\int x^2 \cdot e^x \, dx$", ["integration_by_parts"], 3),
    (r"Evaluate $\int \ln(x) \, dx$", ["integration_by_parts"], 2),
    (r"Evaluate $\int x \cdot \cos(x) \, dx$", ["integration_by_parts"], 2),
    (r"Evaluate $\int x^2 \cdot \sin(x) \, dx$", ["integration_by_parts"], 3),
    (r"Evaluate $\int e^x \cdot \sin(x) \, dx$", ["integration_by_parts"], 4),
    (r"Evaluate $\int x \cdot \ln(x) \, dx$", ["integration_by_parts"], 3),
    (r"Evaluate $\int x^2 \cos(x) \, dx$", ["integration_by_parts"], 3),
    # Limits & Continuity
    (r"Find $\lim_{x \to 0} \frac{\sin x}{x}$", ["limits_continuity"], 1),
    (r"Find $\lim_{x \to 0} \frac{1 - \cos x}{x^2}$", ["limits_continuity"], 2),
    (r"Find $\lim_{x \to \infty} \left(1 + \frac{1}{x}\right)^x$", ["limits_continuity"], 3),
    (r"Find $\lim_{x \to 0} \frac{\tan x}{x}$", ["limits_continuity"], 1),
    (r"Find $\lim_{x \to 2} \frac{x^2 - 4}{x - 2}$", ["limits_continuity"], 1),
    (r"Find $\lim_{x \to 0} \frac{e^x - 1}{x}$", ["limits_continuity"], 2),
    (r"Evaluate $\lim_{x \to \infty} \frac{3x^2 + 2x}{2x^2 - 5}$", ["limits_continuity"], 2),
    (r"Find $\lim_{x \to 0} \frac{\sin(3x)}{x}$", ["limits_continuity"], 2),
    (r"Find $\lim_{x \to 0} \frac{x - \sin x}{x^3}$", ["limits_continuity"], 4),
    (r"Is $f(x) = \frac{|x|}{x}$ continuous at $x = 0$? Justify.", ["limits_continuity"], 3),
    # Differentiation
    (r"Differentiate $y = x^3 - 5x^2 + 6x$ with respect to $x$", ["differentiation_basics"], 1),
    (r"Find $\frac{dy}{dx}$ if $y = \sin(x^2)$", ["differentiation_basics"], 2),
    (r"Find $\frac{dy}{dx}$ if $y = e^x \cdot \ln(x)$", ["differentiation_basics"], 2),
    (r"Find $\frac{dy}{dx}$ if $y = \frac{x^2+1}{x-1}$", ["differentiation_basics"], 2),
    (r"Find the second derivative of $y = x^4 - 3x^2$", ["differentiation_basics"], 2),
    (r"Differentiate $y = \tan(3x + 1)$", ["differentiation_basics"], 2),
    (r"Find $\frac{dy}{dx}$ if $y = x^{\sin x}$ using logarithmic differentiation", ["differentiation_basics"], 4),
    (r"Differentiate $y = \frac{\sin x}{1 + \cos x}$", ["differentiation_basics"], 3),
    (r"Find $\frac{dy}{dx}$ using implicit differentiation: $x^2 + y^2 = 25$", ["differentiation_basics"], 2),
    (r"If $y = \ln(\sec x + \tan x)$, find $\frac{dy}{dx}$", ["differentiation_basics"], 3),
    # Quadratic Equations
    (r"Find roots of $x^2 - 5x + 6 = 0$", ["quadratic_equations"], 1),
    (r"Find roots of $2x^2 - 3x - 2 = 0$", ["quadratic_equations"], 2),
    (r"For what values of $k$ does $kx^2 + 4x + k = 0$ have equal roots?", ["quadratic_equations"], 3),
    (r"If $\alpha, \beta$ are roots of $3x^2 - 7x + 2 = 0$, find $\alpha^2 + \beta^2$", ["quadratic_equations"], 3),
    (r"Find roots of $x^2 + x + 1 = 0$", ["quadratic_equations"], 2),
    (r"If one root of $x^2 - 5x + k = 0$ is 2, find $k$", ["quadratic_equations"], 2),
    (r"Find the range of $k$ for which $x^2 - kx + k + 3 = 0$ has two positive roots", ["quadratic_equations"], 4),
    (r"Solve $|x^2 - 5x + 6| = x - 2$", ["quadratic_equations"], 3),
    (r"If $\alpha + \beta = 5$ and $\alpha\beta = 6$, form the quadratic equation with these roots", ["quadratic_equations"], 2),
    # Complex Numbers
    (r"Find the modulus of $z = 3 + 4i$", ["complex_numbers_basics"], 1),
    (r"Find the argument of $z = -1 + i$", ["complex_numbers_basics"], 2),
    (r"Simplify $(2 + 3i)(1 - 2i)$", ["complex_numbers_basics"], 2),
    (r"Find $z$ if $z + \bar{z} = 6$ and $z \cdot \bar{z} = 13$", ["complex_numbers_basics"], 3),
    (r"Express $\frac{1+i}{1-i}$ in the form $a + bi$", ["complex_numbers_basics"], 2),
    (r"Find all cube roots of unity", ["complex_numbers_basics"], 3),
    (r"If $z = \cos\theta + i\sin\theta$, find $z + \frac{1}{z}$", ["complex_numbers_basics"], 3),
    (r"If $|z - 1| = |z + 3|$, describe the locus of $z$", ["complex_numbers_basics"], 3),
    (r"Find the square root of $-8 - 6i$", ["complex_numbers_basics"], 3),
    # Basic Probability
    (r"A bag has 5 red and 3 blue balls. Two drawn without replacement. Find P(both red)", ["basic_probability"], 2),
    (r"Two dice are rolled. Find P(sum = 7)", ["basic_probability"], 2),
    (r"A card is drawn from a standard deck of 52. Find P(king or heart)", ["basic_probability"], 2),
    (r"P(A) = 0.4, P(B) = 0.3, P(A and B) = 0.1. Find P(A or B)", ["basic_probability"], 2),
    (r"Find P(at least one head) when 3 fair coins are tossed", ["basic_probability"], 2),
    (r"From 10 people, 3 are selected at random. Find P(a specific person is selected)", ["basic_probability"], 3),
    (r"Two cards drawn from a standard deck. Find P(both are aces)", ["basic_probability"], 3),
    (r"A box has 6 red, 4 blue, 2 green balls. One ball drawn randomly. Find P(not red)", ["basic_probability"], 1),
    (r"P(A) = 0.6, A and B are mutually exclusive, P(A or B) = 0.9. Find P(B)", ["basic_probability"], 2),
    (r"Three fair coins tossed simultaneously. Find P(exactly 2 heads)", ["basic_probability"], 2),
    (r"A number is chosen at random from 1 to 20. Find P(divisible by 3 or 5)", ["basic_probability"], 2),
    (r"Two dice are rolled. Find P(product of the two faces equals 12)", ["basic_probability"], 3),
    (r"In a class of 50: 30 like maths, 25 like science, 10 like both. Find P(a student likes at least one)", ["basic_probability"], 2),
    # Matrices
    (r"Find the determinant of $A = \begin{pmatrix}1&2\\3&4\end{pmatrix}$", ["matrix_operations"], 1),
    (r"Find the inverse of $A = \begin{pmatrix}2&1\\5&3\end{pmatrix}$", ["matrix_operations"], 2),
    (r"Find $x$ if $\det\begin{pmatrix}x&2\\3&x\end{pmatrix} = 10$", ["matrix_operations"], 2),
    (r"Find the rank of $\begin{pmatrix}1&2&3\\4&5&6\\7&8&9\end{pmatrix}$", ["matrix_operations"], 3),
    (r"If $A = \begin{pmatrix}0&1\\-1&0\end{pmatrix}$, find $A^{100}$", ["matrix_operations"], 4),
    (r"For what values of $k$ is $\begin{pmatrix}k&2\\3&k\end{pmatrix}$ singular?", ["matrix_operations"], 2),
    # Arithmetic Progression
    (r"Find the 10th term of the AP: 2, 5, 8, ...", ["arithmetic_progression"], 1),
    (r"Find the sum of the first 20 terms of AP: 3, 7, 11, ...", ["arithmetic_progression"], 2),
    (r"How many terms of AP 2, 5, 8, ... are needed so that their sum = 155?", ["arithmetic_progression"], 3),
    (r"The 5th term of an AP is 17 and the 9th term is 33. Find the AP.", ["arithmetic_progression"], 3),
    (r"Insert 4 arithmetic means between 3 and 23", ["arithmetic_progression"], 2),
    # Geometric Progression
    (r"Find the 8th term of GP: 3, 6, 12, ...", ["geometric_progression"], 1),
    (r"Find sum of infinite GP: $1 + \frac{1}{2} + \frac{1}{4} + \cdots$", ["geometric_progression"], 2),
    (r"The 4th and 7th terms of a GP are 8 and 64 respectively. Find the first term and common ratio.", ["geometric_progression"], 3),
    (r"If AM of two numbers is 10 and GM is 8, find the two numbers", ["geometric_progression"], 3),
    # Binomial Theorem
    (r"Find the 4th term in the expansion of $(x+2)^6$", ["binomial_theorem"], 2),
    (r"Find the middle term of $\left(x + \frac{1}{x}\right)^8$", ["binomial_theorem"], 3),
    (r"Find the coefficient of $x^3$ in the expansion of $(1+x)^7$", ["binomial_theorem"], 2),
    (r"Find the term independent of $x$ in $\left(x + \frac{1}{x}\right)^6$", ["binomial_theorem"], 3),
    (r"Find the greatest term in the expansion of $(1+x)^{10}$ when $x = \frac{1}{2}$", ["binomial_theorem"], 4),
    # Trigonometric Identities
    (r"Find $\sin(75^\circ)$ using addition formula", ["trigonometric_identities"], 2),
    (r"Prove that $\cos(3x) = 4\cos^3 x - 3\cos x$", ["trigonometric_identities"], 3),
    (r"Prove: $\frac{\sin 3A + \sin A}{\cos 3A - \cos A} = -\cot A$", ["trigonometric_identities"], 3),
    (r"Find the value of $\tan(15^\circ)$", ["trigonometric_identities"], 2),
    (r"Simplify $\frac{\sin A - \sin B}{\cos A + \cos B}$", ["trigonometric_identities"], 3),
    # Trigonometric Equations
    (r"Solve $\sin x = \frac{\sqrt{3}}{2}$ for $x \in [0, 2\pi]$", ["trigonometric_equations"], 2),
    (r"Find the general solution of $\tan x = 1$", ["trigonometric_equations"], 2),
    (r"Find all $x \in [0,2\pi]$ satisfying $\cos(2x) = \cos x$", ["trigonometric_equations"], 3),
    (r"Solve $2\cos^2 x - 3\cos x + 1 = 0$ for $x \in [0, 2\pi]$", ["trigonometric_equations"], 3),
    (r"Find the general solution of $\sin(2x) + \cos x = 0$", ["trigonometric_equations"], 3),
    # Coordinate Geometry
    (r"Find the distance between the points $(3,4)$ and $(0,0)$", ["distance_section_formula"], 1),
    (r"Find the midpoint of the line segment joining $(2,3)$ and $(4,7)$", ["distance_section_formula"], 1),
    (r"Find the point dividing segment joining $(1,2)$ and $(4,8)$ in ratio 2:1 internally", ["distance_section_formula"], 2),
    (r"Find equation of line through $(1,2)$ with slope 3", ["equation_of_line"], 1),
    (r"Find the angle between the lines $y = 2x+1$ and $y = 3x-2$", ["equation_of_line"], 2),
    (r"Find the equation of the perpendicular bisector of segment joining $(2,3)$ and $(6,7)$", ["equation_of_line"], 3),
    (r"Find equation of circle with centre $(2,3)$ and radius 5", ["circles"], 2),
    (r"Find the length of tangent from $(5,12)$ to circle $x^2 + y^2 = 169$", ["circles"], 3),
    (r"Find equation of parabola with focus $(2,0)$ and directrix $x = -2$", ["parabola"], 3),
    (r"Find the vertex and focus of the parabola $y^2 = 12x$", ["parabola"], 2),
]


def seed():
    db = SessionLocal()
    try:
        db.execute(_text("DELETE FROM attempts"))
        db.execute(_text("DELETE FROM user_skill"))
        db.execute(_text("DELETE FROM questions"))
        db.commit()

        for q_text, subtopics, difficulty in SEED_QUESTIONS:
            h = hashlib.sha256(q_text.encode()).hexdigest()[:32]
            db.execute(
                _text("""
                    INSERT INTO questions (text, subtopics, difficulty, source_url, text_hash)
                    VALUES (:t, CAST(:s AS jsonb), :d, 'seed', :h)
                    ON CONFLICT (text_hash) DO NOTHING
                """),
                {"t": q_text, "s": json.dumps(subtopics), "d": difficulty, "h": h},
            )
        db.commit()

        total = db.execute(_text("SELECT COUNT(*) FROM questions")).fetchone()[0]
        print(f"Seeded {total} questions")

        rows = db.execute(_text("""
            SELECT subtopics::text, COUNT(*) cnt
            FROM questions GROUP BY subtopics::text ORDER BY cnt DESC
        """)).fetchall()
        for r in rows:
            print(f"  {r[0]:<55s} {r[1]}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
