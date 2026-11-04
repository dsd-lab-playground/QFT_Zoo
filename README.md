# QFT Zoo

An open, community-curated catalogue of quantum field theories and their data:
symmetries, operator spectra, central charges, critical exponents, RG flows and
dualities.

**Website:** https://nathansbenjamin.github.io/QFT_Zoo/

Every theory is a small, human-readable YAML file in [`data/theories/`](data/theories).
The website is generated from these files automatically, and the whole dataset is
also published as a single JSON file
([`data/theories.json`](https://nathansbenjamin.github.io/QFT_Zoo/data/theories.json))
for use in your own code.

## Contributing

Anyone can propose additions or corrections. All changes are reviewed by the
maintainers before they appear on the site.

- **No git needed:** [suggest a theory](https://github.com/nathansbenjamin/QFT_Zoo/issues/new?template=new-theory.yml) or
  [report a problem](https://github.com/nathansbenjamin/QFT_Zoo/issues/new?template=correction.yml) through a short form.
- **Edit on GitHub:** every theory page has an *Edit this entry* button, and the
  home page has *Add a theory*. GitHub forks the repo and opens a pull request for you.
- **Work locally:** see [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository layout

```
data/theories/<id>.yaml   one file per theory  ← the actual content
data/TEMPLATE.yaml        starting point for a new entry
schema/                   JSON Schema that every entry must satisfy
scripts/build.py          validates the data and builds the site into _site/
site/                     the website (static HTML/CSS/JS; KaTeX for math)
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
