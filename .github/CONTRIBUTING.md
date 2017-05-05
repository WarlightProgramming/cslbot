Thanks for your interest in contributing to the CSL project!

## Contributing to the cslbot Project

#### **Do you need troubleshooting help?**

First, you should check the [project wiki](https://github.com/knyte/cslbot/wiki).
It is the single authoritative source of information for the CSL framework.

This file is probably not relevant to you. **Do not** create an Issue
unless you've found a bug or have a feature enhancement. Instead, contact the
project maintainer or seek help in Warlight's Programming subforum.

Once you receive help or solve your problem, if your problem was not documented 
on the project wiki, it would be appreciated if you edit the wiki to then
include helpful and pertinent information.

#### **Did you find a bug?**

* **Make sure it wasn't already reported** by searching our
  [existing Issues](https://github.com/knyte/cslbot/issues).

* Open a [new Issue](https://github.com/knyte/cslbot/issues/new) with **a
  concise and complete title** and enough information to reproduce the issue. If
  applicable, include a code sample or a sample League Cluster as well as details
  about the expecte and actual behavior. Identify exactly what's broken.

#### **Do you have an idea for a feature?**

* **If you're not going to use it yourself**, don't create an Issue.

* **Make sure it wasn't already suggested** by searching our
  [existing Issues](https://github.com/knyte/cslbot/issues).

* Open a [new Issue](https://github.com/knyte/cslbot/issues/new). Be
  descriptive about what sort of behavior the suggested feature would have and
  what sorts of use cases it would apply in. If possible,
  [insert images](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
  or supply links to existing League Clusters or anything else that helps
  explain why the feature will be worth adding and how it might be used.

* Features that can be implemented downstream (i.e., in Google Sheets) or only
  apply in your unique situation will likely receive lower probability.

#### **Did you fix a bug, add a feature, or otherwise improve the repo?**

* **Don't create a new Issue** if there isn't already one for the bug or the
  feature request. When possible, it's best to have the entire conversation in
  one thread instead of hopping between multiple threads.

* **Make sure your code is tested**; untested code will not be pulled into the
  project. Using nosetests and the --with-coverage flag is the easiest way to
  make sure you've tested any new code you've added- make sure every *branch*
  (not just every line) is tested. The cover library does not test every
  branch by default, so you can either use a
  [.coveragerc file](https://coverage.readthedocs.io/en/latest/config.html)
  or also use the --cover-branches flag. Your terminal command should look
  like:

```
nosetests --with-coverage --cover-branches
```

* **Make sure your code style is consistent with the project**. Code that
  adds issues that pop up on static analysis will be asked to be modified.

* [Create a Pull Request](https://github.com/knyte/cslbot/compare) using your
  forked version of the project. Be descriptive but concise about what your
  change does, how the implementation works, and any new restrictions it
  creates for future code or for Clusters and Interfaces.

## Style Contributions

**Do not create Issues for style warnings that pop up on pylint or static
analysis**. Those issues are already known; only acknowledge them in the
ticketing system if you've got a Pull Request that fixes them.

In order to be accepted, contributions must significantly improve
some aspect of the project for developers/maintainers and/or users.

Proposals that improve project style (e.g., fixing whitespace, changing camelCase
to snake\_case, improving maintainability) will only be accepted if they're
thorough- i.e., they don't just fix the issue in one place but everywhere in
the project where it's found. Fixing whitespace on one line of one file will
not be substantial enough to get accepted, but converting the whole repository
to better match Python-wide style guidelines or to improve code optimization or
readability will likely be accepted. 
