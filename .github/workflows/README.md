# Workflows

* `tests.yml` --- lint, test matrix, and a build/import check. Runs on pushes
  to `main`, on pull requests, and on demand.
* `publish.yml` --- builds and publishes to PyPI when a GitHub release is
  published. Uses PyPI Trusted Publishing (OIDC): no API token is stored in
  this repository.
* `docs.yml` --- builds the documentation site and publishes it to GitHub
  Pages on pushes to `main`. A pull request builds the site but does not
  deploy it, so a broken build is caught before it can be published. The
  build treats warnings as errors.

## One-time setup required before the first documentation deployment

In the repository settings, under Pages, set the source to GitHub Actions.


## One-time setup required before the first release

1. Create the `pypi` environment in the repository settings.
2. Register the trusted publisher at
   <https://pypi.org/manage/account/publishing/> with:
   * owner `noahbenson`, repository `docshare`
   * workflow `publish.yml`
   * environment `pypi`
