# Workflows

* `tests.yml` --- lint, test matrix, and a build/import check. Runs on pushes
  to `main`, on pull requests, on demand, and as a reusable workflow called by
  `publish.yml`.
* `publish.yml` --- builds and publishes to PyPI when a GitHub release is
  published. It runs `tests.yml` first, so a release passes the same lint,
  the same matrix, and the same build check as an ordinary push before
  anything is uploaded; it then checks the distribution metadata and that the
  release tag matches `docshare.__version__`. Uses PyPI Trusted Publishing
  (OIDC): no API token is stored in this repository.
* `docs.yml` --- builds the documentation site and publishes it to GitHub
  Pages on pushes to `main`. A pull request builds the site but does not
  deploy it, so a broken build is caught before it can be published. The
  build treats warnings as errors.

## One-time setup required before the first documentation deployment

In the repository settings, under Pages, set the source to GitHub Actions.


## One-time setup required before the first release

Publishing uses PyPI Trusted Publishing, in which PyPI trusts a short-lived
OpenID Connect token minted by GitHub for this one workflow rather than a
long-lived API token stored as a secret. Nothing needs to be kept in the
repository, and a token cannot leak because there is none.

Order matters: register the publisher on PyPI *before* creating the release,
because the first release will fail if PyPI does not yet know about it.

1. On PyPI, go to <https://pypi.org/manage/account/publishing/>. Because
   `docshare` has never been uploaded, use the *pending* publisher form, which
   reserves the name and the trust relationship together. Fill in:

   * PyPI project name: `docshare`
   * Owner: `noahbenson`
   * Repository name: `docshare`
   * Workflow name: `publish.yml` (the file name, not the `name:` inside it)
   * Environment name: `pypi`

   Once the first release is published the pending publisher becomes an
   ordinary one, listed under the project's own publishing settings.

2. On GitHub, under Settings -> Environments, create an environment named
   `pypi`. The name must match the one registered on PyPI exactly. Nothing
   needs to be configured inside it; the environment exists so that PyPI can
   require it and so that a protection rule can be added later. Restricting
   its deployment branches to tags, or adding a required reviewer, is worth
   doing if a release should not be publishable from an arbitrary branch.

3. Releasing: set the version in `src/docshare/__init__.py`, commit, tag with
   `v<version>` (the tag check compares the tag with `v` removed against
   `docshare.__version__`), push the tag, and publish a GitHub release from
   it. Publishing the release --- not pushing the tag --- is what runs the
   workflow. A draft release does nothing until it is published.

No secrets are involved at any point. If the upload is rejected with an
"invalid publisher" or "not a trusted publisher" error, the five values in
step 1 did not all match; the workflow's job summary prints the claims GitHub
actually sent, which is the quickest way to see which one is wrong.
