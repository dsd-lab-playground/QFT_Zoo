<!-- Thanks for contributing to the QFT Zoo! -->

**What does this PR add or change?**


**Checklist**
- [ ] One theory per file, in `data/theories/<id>.yaml`, with `id` equal to the filename
- [ ] Every number has a `refs:` entry pointing to a reference (arXiv ID or DOI)
- [ ] Uncertainties use parenthesis notation, e.g. `'0.518148806(24)'`
- [ ] Relations point to existing entries (`flows_to` means *this* theory is the UV)
- [ ] I previewed the page locally (`python scripts/build.py --serve`), or I'm relying on the automated check

The automated check validates the data; a maintainer will review the physics before merging.
