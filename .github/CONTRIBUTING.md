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

1. Create a release on Github on https://github.com/Cornices/cornice/releases/new
2. Create a new tag `X.Y.Z` (*This tag will be created from the target when you publish this release.*)
3. Generate release notes
4. Publish release
