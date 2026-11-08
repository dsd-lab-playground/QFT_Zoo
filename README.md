# QFT Zoo

An open, community-curated catalogue of quantum field theories and their data:
symmetries, operator spectra, central charges, critical exponents, RG flows and
dualities.

**Website:** https://nathansbenjamin.github.io/QFT_Zoo/

Every theory is a small, human-readable YAML file in [`data/theories/`](data/theories).
The website is generated from these files automatically, and the whole dataset is
also published as a single JSON file
([`data/theories.json`](https://nathansbenjamin.github.io/QFT_Zoo/data/theories.json))
for use in your own code. The [landscape page](https://nathansbenjamin.github.io/QFT_Zoo/#/landscape)
plots every 2d CFT with known central charge and spectral gap.

2d CFTs can also carry a full torus partition function in
[`data/spectra/`](data/spectra): characters as exact q-series and the modular
invariant that combines them. The theory pages list the primaries, the Virasoro
primaries and the characters. Every spectrum is checked automatically: modular
invariance, non-negative integer degeneracies, a unique vacuum, and the spectral
gap stated in the theory file.

## Contributing

Anyone can propose additions or corrections. All changes are reviewed by the
maintainers before they appear on the site.

- **No git needed:** [suggest a theory](https://github.com/nathansbenjamin/QFT_Zoo/issues/new?template=new-theory.yml) or
  [report a problem](https://github.com/nathansbenjamin/QFT_Zoo/issues/new?template=correction.yml) through a short form.
- **Edit on GitHub:** every theory page has an *Edit this entry* button, and the
  home page has *Add a theory*. GitHub forks the repo and opens a pull request for you.
- **Work locally:** see [CONTRIBUTING.md](CONTRIBUTING.md).

Comments on the site itself go through the
[feedback form](https://github.com/nathansbenjamin/QFT_Zoo/issues/new?template=feedback.yml) and appear on the
site's Feedback page. `python scripts/fetch_feedback.py` prints them all as Markdown.

## Repository layout

```
data/theories/<id>.yaml   one file per theory  ← the actual content
data/spectra/             partition functions of 2d CFTs (characters + modular invariant)
data/operations/          pages explaining how composite theories are built (direct sum, ...)
data/TEMPLATE.yaml        starting point for a new entry
schema/                   JSON Schemas for theory files and spectrum files
scripts/build.py          validates the data and builds the site into _site/
scripts/zoo_spectrum.py   the checks run on every spectrum file
scripts/spectra/          the scripts that generated the spectrum files
site/                     the website (static HTML/CSS/JS; KaTeX for math)
tests/                    tests of the build checks (python tests/test_flows.py, tests/test_reps.py, tests/test_ope.py, tests/test_opfam.py)
docs/REPRESENTATIONS.md   how operators record their symmetry representations, and how tables are grouped
docs/THREE_POINT.md       how three-point functions record their operators, structures and coefficients, and how they are shown
data/three_point_structures.yaml
                          the standard three-point structures that values may name
.github/workflows/        validation on every PR; deploy to GitHub Pages on merge
```

## Running locally

```bash
pip install -r requirements.txt
python scripts/build.py --check   # validate only
python scripts/build.py --serve   # build and preview at http://localhost:8000
```

## How publishing works

Pull requests trigger an automated check (`scripts/build.py`) that validates every
entry against the schema and cross-checks references and relations. When a change
is merged into `main`, GitHub Actions rebuilds the site and publishes it to GitHub
Pages. There is no server and nothing to host.

To use a custom domain later: *Settings → Pages → Custom domain*, then add a
`CNAME` DNS record pointing to `nathansbenjamin.github.io`.
