export interface Topic {
  id: string;
  label: string;
  category: string;
}

export const TOPICS: Topic[] = [
  // Sets & Functions
  { id: "sets_and_operations", label: "Sets & Operations", category: "Sets & Functions" },
  { id: "relations", label: "Relations", category: "Sets & Functions" },
  { id: "functions", label: "Functions", category: "Sets & Functions" },
  { id: "inverse_functions", label: "Inverse Functions", category: "Sets & Functions" },
  { id: "domain_and_range", label: "Domain & Range", category: "Sets & Functions" },
  { id: "composite_functions", label: "Composite Functions", category: "Sets & Functions" },

  // Algebra
  { id: "quadratic_equations", label: "Quadratic Equations", category: "Algebra" },
  { id: "complex_numbers", label: "Complex Numbers", category: "Algebra" },
  { id: "arithmetic_progression", label: "Arithmetic Progression", category: "Algebra" },
  { id: "geometric_progression", label: "Geometric Progression", category: "Algebra" },
  { id: "binomial_theorem", label: "Binomial Theorem", category: "Algebra" },
  { id: "permutations", label: "Permutations", category: "Algebra" },
  { id: "combinations", label: "Combinations", category: "Algebra" },
  { id: "probability", label: "Probability", category: "Algebra" },
  { id: "mathematical_induction", label: "Mathematical Induction", category: "Algebra" },
  { id: "inequalities", label: "Inequalities", category: "Algebra" },
  { id: "logarithms", label: "Logarithms", category: "Algebra" },
  { id: "partial_fractions", label: "Partial Fractions", category: "Algebra" },
  { id: "harmonic_progression", label: "Harmonic Progression", category: "Algebra" },
  { id: "series_sum", label: "Series Sum", category: "Algebra" },

  // Matrices & Determinants
  { id: "matrix_operations", label: "Matrix Operations", category: "Matrices" },
  { id: "determinants", label: "Determinants", category: "Matrices" },
  { id: "inverse_matrix", label: "Inverse Matrix", category: "Matrices" },
  { id: "linear_equations", label: "Linear Equations", category: "Matrices" },

  // Trigonometry
  { id: "trigonometric_identities", label: "Trigonometric Identities", category: "Trigonometry" },
  { id: "trigonometric_equations", label: "Trigonometric Equations", category: "Trigonometry" },
  { id: "inverse_trigonometry", label: "Inverse Trigonometry", category: "Trigonometry" },
  { id: "heights_and_distances", label: "Heights & Distances", category: "Trigonometry" },
  { id: "compound_angles", label: "Compound Angles", category: "Trigonometry" },
  { id: "multiple_angles", label: "Multiple Angles", category: "Trigonometry" },
  { id: "properties_of_triangles", label: "Properties of Triangles", category: "Trigonometry" },

  // Coordinate Geometry
  { id: "straight_lines", label: "Straight Lines", category: "Coordinate Geometry" },
  { id: "circles", label: "Circles", category: "Coordinate Geometry" },
  { id: "parabola", label: "Parabola", category: "Coordinate Geometry" },
  { id: "ellipse", label: "Ellipse", category: "Coordinate Geometry" },
  { id: "hyperbola", label: "Hyperbola", category: "Coordinate Geometry" },

  // Calculus
  { id: "limits", label: "Limits", category: "Calculus" },
  { id: "continuity", label: "Continuity", category: "Calculus" },
  { id: "differentiation", label: "Differentiation", category: "Calculus" },
  { id: "product_rule", label: "Product Rule", category: "Calculus" },
  { id: "chain_rule", label: "Chain Rule", category: "Calculus" },
  { id: "implicit_differentiation", label: "Implicit Differentiation", category: "Calculus" },
  { id: "applications_of_derivatives", label: "Applications of Derivatives", category: "Calculus" },
  { id: "maxima_minima", label: "Maxima & Minima", category: "Calculus" },
  { id: "basic_integration", label: "Basic Integration", category: "Calculus" },
  { id: "integration_by_substitution", label: "Integration by Substitution", category: "Calculus" },
  { id: "integration_by_parts", label: "Integration by Parts", category: "Calculus" },
  { id: "definite_integrals", label: "Definite Integrals", category: "Calculus" },
  { id: "area_under_curve", label: "Area Under Curve", category: "Calculus" },
  { id: "differential_equations", label: "Differential Equations", category: "Calculus" },
  { id: "rate_of_change", label: "Rate of Change", category: "Calculus" },
  { id: "tangent_and_normal", label: "Tangent & Normal", category: "Calculus" },
  { id: "rolles_theorem", label: "Rolle's Theorem", category: "Calculus" },
  { id: "mean_value_theorem", label: "Mean Value Theorem", category: "Calculus" },
  { id: "lhopital_rule", label: "L'Hôpital's Rule", category: "Calculus" },

  // Vectors & 3D
  { id: "vectors_basics", label: "Vectors Basics", category: "Vectors & 3D" },
  { id: "dot_product", label: "Dot Product", category: "Vectors & 3D" },
  { id: "cross_product", label: "Cross Product", category: "Vectors & 3D" },
  { id: "lines_in_3d", label: "Lines in 3D", category: "Vectors & 3D" },
  { id: "planes_in_3d", label: "Planes in 3D", category: "Vectors & 3D" },
  { id: "shortest_distance", label: "Shortest Distance", category: "Vectors & 3D" },
  { id: "direction_cosines", label: "Direction Cosines", category: "Vectors & 3D" },
  { id: "scalar_triple_product", label: "Scalar Triple Product", category: "Vectors & 3D" },
  { id: "vector_triple_product", label: "Vector Triple Product", category: "Vectors & 3D" },
];

export const CATEGORIES = [...new Set(TOPICS.map((t) => t.category))];

export function topicsByCategory(category: string) {
  return TOPICS.filter((t) => t.category === category);
}
