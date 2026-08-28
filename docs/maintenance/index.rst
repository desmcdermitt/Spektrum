.. role:: raw-html(raw)
   :format: html

Maintainer Notes
================

These notes are directed towards helping with the maintenance of the
Spektrum project.

Releasing a new version of Spektrum
-----------------------------------

**Pushing a tag to** ``liquidweb/Spektrum`` **is the release.** Nothing else
publishes. Travis builds every tag and uploads the result to PyPI; merging to
``master`` does not, and neither does running ``bumpversion``. A version bump
sitting on ``master`` with no tag is not a release — it is the state this
repository was in for two versions.

Both of those are still on PyPI's missing list:

===========  ==================  ======================================
Version      Reached PyPI        Why not
===========  ==================  ======================================
1.2.2        no                  tag left on an unmerged commit, pushed
                                 to a personal fork
1.3.0        no                  same
===========  ==================  ======================================

Two mistakes produced both, and they are easy to repeat by hand:

#. ``bumpversion`` tags the commit it is run on. On a branch, that is the
   pre-merge commit — and the merge rewrites it, so the tag is left pointing
   at a commit that never reaches ``master``.
#. ``git push origin --tags`` sends the tag to whatever ``origin`` is. For
   both maintainers ``origin`` is a personal fork. Travis watches
   ``liquidweb/Spektrum``, so it never sees the tag and never builds.

Notes are written as you go
^^^^^^^^^^^^^^^^^^^^^^^^^^^

``docs/release_notes/index.rst`` opens with a ``Next Release`` section. **Every
PR adds its own entry there**, in the PR that makes the change, while the person
writing it still knows what it meant. The release then renames that section to
the version it becomes.

A release with an empty ``Next Release`` is refused. Reconstructing months of
notes from ``git log`` at release time is how the log came to stop at 1.0.0
while ``setup.py`` said 1.3.0.

Use the script
^^^^^^^^^^^^^^

``tools/release.sh`` exists so that neither mistake above is reachable. It
refuses rather than warns, and it always names the fix. Run it with no
arguments and it works out what is needed:

.. code-block:: shell

     ./tools/release.sh

It reports which state the repository is in and does the next right thing:

===============================  =========================================
State                            What happens
===============================  =========================================
Nothing merged since the tag     Says so and exits. Not every fortnight
                                 produces a release.
Changes waiting                  Lists them, shows the candidate versions,
                                 asks for major/minor/patch, then releases.
``Next Release`` empty           Refuses. The merged changes never said
                                 what they changed.
A release PR already open        Tells you what to merge.
Merged but never tagged          Goes straight to tagging. This is the
                                 state that lost 1.2.2 and 1.3.0.
===============================  =========================================

In a Claude Code session, "let's cut a new release" reaches the same script
through ``.claude/skills/cut-a-release/``.

The subcommands are there for when you already know the state:

.. code-block:: shell

     ./tools/release.sh status                    # read-only drift report
     ./tools/release.sh release patch             # or: minor, major
     ./tools/release.sh publish                   # this is what publishes

**Phase 1 — release.** Cuts a branch named ``v<old>-to-v<new>``, renames
``Next Release`` to ``Release: <new>`` and opens a fresh empty one, bumps the
version, runs both suites and lint, makes **one** commit with the subject
``v<old> -> v<new>``, pushes to your fork and opens the PR. The subject is what
makes published versions visible in ``git log --oneline``.

No tag is created in this phase, and that is deliberate. There is nothing to
tag until the PR merges.

**Phase 2 — publish.** Run once that PR has merged:

.. code-block:: shell

     ./tools/release.sh publish

It reads the version from the canonical ``master`` rather than from your
checkout, checks the version files agree with each other and with the notes,
checks the version is not already on PyPI, asks you to type the version to
confirm, then tags the merge commit and pushes that tag to the canonical
remote. It then waits for the version to appear on PyPI and tells you where
the build is if it does not.

What the script checks
^^^^^^^^^^^^^^^^^^^^^^

Each of these refuses the release outright:

* No remote points at ``liquidweb/Spektrum``, or more than one does. The
  script never assumes a remote is called ``upstream``.
* The working tree is dirty when the branch is cut.
* ``docs/release_notes/index.rst`` has no section for the new version.
* ``setup.py``, ``docs/conf.py`` and ``.bumpversion.cfg`` disagree.
* The tag already exists — locally on a different commit, or on the remote.
* The version is already on PyPI. Versions there cannot be reused or
  replaced, ever.
* Either test suite fails, or flake8 does.

Doing it by hand
^^^^^^^^^^^^^^^^

If the script cannot run, the process it encodes is:

.. code-block:: shell

     # Phase 1, on a branch off the canonical master
     git fetch upstream
     git checkout -b v1.3.1-to-v1.3.2 upstream/master
     # rename the "Next Release" heading to "Release: 1.3.2" and open a
     # fresh empty "Next Release" above it, then:
     bumpversion --allow-dirty --no-commit --no-tag patch
     python -m pytest tests -q
     python -m spektrum -s tests/live/
     python -m flake8 spektrum tests
     git add docs/release_notes/index.rst setup.py docs/conf.py .bumpversion.cfg
     git commit -m 'v1.3.1 -> v1.3.2'
     # push to your fork, open the PR, get it merged

     # Phase 2, after the merge
     git fetch upstream
     git tag -a v<version> upstream/master -m 'v<version>'
     git push upstream v<version>          # upstream, never origin

The ``--no-commit --no-tag`` and the ``upstream/master`` in ``git tag`` are
the whole point. Dropping either reproduces 1.2.2 and 1.3.0.

Then confirm it actually published — a pushed tag is not proof:

.. code-block:: shell

     ./tools/release.sh status

If the version has not appeared, the build is at
https://app.travis-ci.com/github/liquidweb/Spektrum/builds. A dead credential
surfaces there as a failing deploy step on an otherwise green build.

The credential is a ``PYPI_TOKEN`` secret in Travis repository settings:

     https://app.travis-ci.com/github/liquidweb/Spektrum/settings

Travis mirrors GitHub repository permissions, so anyone with admin on
``liquidweb/Spektrum`` can read and replace it there. It was last exercised on
2025-06-11, so treat a deploy that fails on authentication as "rotate the
token", not as a mystery. Replacing it needs a PyPI account with maintainer
rights on the Spektrum project — worth confirming who holds that *before* a
release depends on it.
