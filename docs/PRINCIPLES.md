# Principles of the QFT Zoo

The Zoo aims to be a reference that high-energy theorists can standardize around: principled in what it records,
uniform in how it records it, and written in the best concepts and notation of the field. These principles come from
David Simmons-Duffin's review of the site (November 2026). Every contributor, human or agent, follows them; the more
specific documents (CONTRIBUTING.md, docs/REPRESENTATIONS.md, docs/THREE_POINT.md) apply them.

## 1. Data first, presentation derived

- Record what a thing *is*, as structured data, and derive the page from it by a written, predictable policy. Never
  encode meaning in free text that the site then parses, and never patch the display with heuristics or inferences.
- An operator carries its representation of the full symmetry group: scaling dimension, Lorentz representation, parity
  (on par with spin), and an irrep of each factor of the global symmetry. Tables group by global irrep, then parity,
  then sort by spin and Δ (docs/REPRESENTATIONS.md).
- The object is the three-point function: ⟨O₁O₂O₃⟩ of an unordered triple of operators is a linear combination of
  coefficients times structures. Each recorded number is the coefficient of one structure, the structure is taken from
  the same source as the number (its basis, notation and normalization), and the value records the operator order its
  structure assumes (docs/THREE_POINT.md).
- A tower of operators known exactly as a function of a label is one family record; operators known one by one stay
  individual.
- What isn't known is recorded as unknown, never guessed. A claim inferred by argument says so.

## 2. The field's best concepts and standard notation

- Use the established concept and its standard name: the actual spacetime symmetry group (in Euclidean and Lorentzian
  signature where both exist; two Virasoro algebras in 2d; supercharges as part of the spacetime symmetry), the
  standard names of superconformal multiplets, the standard notation for three-point structures.
- What is "standard" is decided by the literature, not by whichever paper we happened to read first: survey how the
  field writes the thing (reviews, lecture notes, the most-cited papers), adopt the most widely used convention, and
  record the choice and the evidence in the relevant document. Papers that discuss a topic (e.g. a classification of
  multiplets, an embedding-space formalism) are sources for it, not automatically the standard. A choice made before
  such a survey is provisional and says so.
- Where the literature offers several equivalent conventions, choose one site-wide by what is most widely used, write
  it down, and use it everywhere. A letter is a convention, not information (λ versus f for OPE coefficients).
- Three-point structures come from the same source as their coefficients and are written in its notation; only simple
  structures with no source-specific notation (three scalars) are written in a common notation.
- Sources' own bases and normalizations may be kept when they differ, but each value then says exactly which one it is
  in, and values in different conventions are never silently compared. Converting to a common convention is fine
  when the relation is exact and stated.
- Label everything by what it is. A label must identify its object without opening a reference: write a structure
  out; name an operator by its standard name; never label by a bare symbol plus a citation.

## 3. Uniformity

- One concept, one representation, everywhere: names ("3d Ising CFT", "3d free scalar"), units and normalizations,
  methods, citations, tables. The same kind of thing looks the same on every page.
- Short names only where an abbreviation is in wide use (SYM, QED₃, YM); otherwise short but complete. The full name
  is always one hover away.
- Methods are treated on the same footing: every determination is its own row with its own method and source, the best
  shown first and the rest folded. A value computed from another takes the method of its input. A determination
  clearly superseded by a better one of the same kind is removed.

## 4. Sources

- Every value and claim cites a published source, as a numbered citation linked to the page's reference list, with a
  locator (section, equation, table, page) wherever the paper is long or the claim isn't its main result.
- Explanatory links (Wikipedia) are welcome for concepts; they never replace a citation.

## 5. Presentation

- Concise. A page shows the data and the minimum needed to read it; longer explanation folds away. No mini-essays.
- Consistent visual language: no decoration that carries no meaning (no alternating row colours, no "not a CFT"
  badges, no "Supercharges: 0").
- Diagrams follow the physics: RG-flow height follows the quantity that decreases along flows (c, F, a); an arrow
  starts at a point on its source and ends at an arrowhead; lines are straight unless a bend is needed to tell them
  apart.

## 6. Process

- Changes to what data means go through the data model (schema, validation, documentation), piloted on a few entries
  before migrating all, with checks that could fail (no value changes, counts preserved, independent re-derivation of
  any normalization).
- When in doubt about a convention, find what the literature does; don't invent.
