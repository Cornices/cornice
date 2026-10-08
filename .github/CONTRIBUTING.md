How to contribute
=================

Thanks for your interest in contributing!

## Reporting Bugs

Report bugs at https://github.com/Cornices/cornice/issues/new

If you are reporting a bug, please include:

 - Any details about your local setup that might be helpful in troubleshooting.
 - Detailed steps to reproduce the bug or even a PR with a failing tests if you can.


## Ready to contribute?

### Getting Started

 -  Fork the repo on GitHub and clone locally:

```bash
git clone git@github.com:Cornices/cornice.git
git remote add {your_name} git@github.com:{your_name}/cornice.git
```

## Testing

 -  `make test` to run all the tests

## Submitting Changes

```bash
git checkout main
git pull origin main
git checkout -b issue_number-bug-title
git commit # Your changes
git push -u {your_name} issue_number-bug-title
```

Then you can create a Pull-Request.
Please create your pull-request as soon as you have at least one commit even if it has only failing tests. This will allow us to help and give guidance.

You will be able to update your pull-request by pushing commits to your branch.


## Releasing

The version comes from the git tag (`setuptools-scm`). Publishing a GitHub release creates that tag, and the tag push uploads the package to PyPI.

A pre-release tag looks like `X.Y.Zrc1`. PyPI keeps it off the default install, so `pip install cornice` stays on the latest stable version until a final tag is published.

1. Open a pull request with the generated release notes and any packaging metadata for that version.
2. After it merges, open https://github.com/Cornices/cornice/releases/new
3. Target `main`. Set the tag to `X.Y.Z` or `X.Y.ZrcN` (*the tag is created from that target when the release is published*).
4. Generate the release notes. For an `rc` tag, mark the release as a pre-release and leave it as a draft until the notes look right.
5. Publish the release.
