export interface Topic {
  id: string;
  label: string;
  category: string;
}

export const TOPICS: Topic[] = [
  // Sets & Functions
  { id: "sets_and_operations",       label: "Sets & Operations",         category: "Sets & Functions" },
  { id: "power_sets",                label: "Power Sets",                category: "Sets & Functions" },
  { id: "relations",                 label: "Relations",                 category: "Sets & Functions" },
  { id: "functions_domain_range",    label: "Functions (Domain & Range)", category: "Sets & Functions" },
  { id: "inverse_functions",         label: "Inverse Functions",         category: "Sets & Functions" },
  { id: "composition_of_functions",  label: "Composition of Functions",  category: "Sets & Functions" },

  // Algebra
  { id: "quadratic_equations",       label: "Quadratic Equations",       category: "Algebra" },
  { id: "complex_numbers_basics",    label: "Complex Numbers (Basics)",  category: "Algebra" },
  { id: "complex_numbers_geometry",  label: "Complex Numbers (Geometry)", category: "Algebra" },
  { id: "de_moivre_theorem",         label: "De Moivre's Theorem",       category: "Algebra" },
  { id: "arithmetic_progression",    label: "Arithmetic Progression",    category: "Algebra" },
  { id: "geometric_progression",     label: "Geometric Progression",     category: "Algebra" },
  { id: "harmonic_progression",      label: "Harmonic Progression",      category: "Algebra" },
  { id: "binomial_theorem",          label: "Binomial Theorem",          category: "Algebra" },
  { id: "permutations",              label: "Permutations",              category: "Algebra" },
  { id: "combinations",              label: "Combinations",              category: "Algebra" },
  { id: "basic_probability",         label: "Probability (Basic)",       category: "Algebra" },
  { id: "conditional_probability",   label: "Conditional Probability",   category: "Algebra" },
  { id: "mathematical_induction",    label: "Mathematical Induction",    category: "Algebra" },
  { id: "inequalities",              label: "Inequalities",              category: "Algebra" },

  // Matrices
  { id: "matrix_basics",             label: "Matrices",                  category: "Matrices" },
  { id: "determinants",              label: "Determinants",              category: "Matrices" },
  { id: "inverse_matrix",            label: "Inverse Matrix",            category: "Matrices" },
  { id: "linear_systems",            label: "Linear Systems",            category: "Matrices" },

  // Trigonometry
  { id: "trig_ratios",               label: "Trigonometric Ratios",      category: "Trigonometry" },
  { id: "trig_identities",           label: "Trigonometric Identities",  category: "Trigonometry" },
  { id: "compound_angles",           label: "Compound Angles",           category: "Trigonometry" },
  { id: "multiple_angles",           label: "Multiple Angles",           category: "Trigonometry" },
  { id: "trig_equations",            label: "Trigonometric Equations",   category: "Trigonometry" },
  { id: "inverse_trig",              label: "Inverse Trigonometry",      category: "Trigonometry" },
  { id: "heights_distances",         label: "Heights & Distances",       category: "Trigonometry" },

  // Coordinate Geometry
  { id: "straight_lines",            label: "Straight Lines",            category: "Coordinate Geometry" },
  { id: "circles",                   label: "Circles",                   category: "Coordinate Geometry" },
  { id: "parabola",                  label: "Parabola",                  category: "Coordinate Geometry" },
  { id: "ellipse",                   label: "Ellipse",                   category: "Coordinate Geometry" },
  { id: "hyperbola",                 label: "Hyperbola",                 category: "Coordinate Geometry" },

  // Differential Calculus
  { id: "limits",                    label: "Limits",                    category: "Differential Calculus" },
  { id: "continuity",                label: "Continuity",                category: "Differential Calculus" },
  { id: "differentiation_basics",    label: "Differentiation",           category: "Differential Calculus" },
  { id: "product_rule",              label: "Product Rule",              category: "Differential Calculus" },
  { id: "chain_rule",                label: "Chain Rule",                category: "Differential Calculus" },
  { id: "implicit_differentiation",  label: "Implicit Differentiation",  category: "Differential Calculus" },
  { id: "higher_order_derivatives",  label: "Higher Order Derivatives",  category: "Differential Calculus" },
  { id: "applications_of_derivatives", label: "Applications of Derivatives", category: "Differential Calculus" },
  { id: "rolle_mean_value",          label: "Rolle's & Mean Value Theorem", category: "Differential Calculus" },

  // Integral Calculus
  { id: "basic_integration",         label: "Basic Integration",         category: "Integral Calculus" },
  { id: "integration_by_substitution", label: "Integration by Substitution", category: "Integral Calculus" },
  { id: "integration_by_parts",      label: "Integration by Parts",      category: "Integral Calculus" },
  { id: "partial_fractions",         label: "Partial Fractions",         category: "Integral Calculus" },
  { id: "definite_integrals",        label: "Definite Integrals",        category: "Integral Calculus" },
  { id: "area_under_curves",         label: "Area Under Curves",         category: "Integral Calculus" },
  { id: "differential_equations_basics", label: "Differential Equations", category: "Integral Calculus" },
  { id: "separable_ode",             label: "Separable ODE",             category: "Integral Calculus" },
  { id: "linear_ode",                label: "Linear ODE",                category: "Integral Calculus" },

  // Vectors & 3D
  { id: "vectors_basics",            label: "Vectors Basics",            category: "Vectors & 3D" },
  { id: "position_vector",           label: "Position Vector",           category: "Vectors & 3D" },
  { id: "dot_product",               label: "Dot Product",               category: "Vectors & 3D" },
  { id: "cross_product",             label: "Cross Product",             category: "Vectors & 3D" },
  { id: "direction_ratios",          label: "Direction Ratios",          category: "Vectors & 3D" },
  { id: "vector_equation_of_line",   label: "Equation of a Line",        category: "Vectors & 3D" },
  { id: "vector_equation_of_plane",  label: "Equation of a Plane",       category: "Vectors & 3D" },
  { id: "shortest_distance",         label: "Shortest Distance",         category: "Vectors & 3D" },
  { id: "angle_between_lines_planes", label: "Angle between Lines & Planes", category: "Vectors & 3D" },
];

export const CATEGORIES = [...new Set(TOPICS.map((t) => t.category))];

export function topicsByCategory(category: string) {
  return TOPICS.filter((t) => t.category === category);
}
