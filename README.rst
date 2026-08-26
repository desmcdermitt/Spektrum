.. role:: raw-html(raw)
   :format: html

.. _GitHub: https://github.com/liquidweb/spektrum


Spektrum
========

Spektrum is a Python testing framework inspired from RSpec and Jasmine.
The library was created out of a desire to have a relatively flexible Python
testing framework that adopted a more code-centric approach to BDD.

Spektrum is open-source and is available on `GitHub`_. We love contributions!

Getting Started
~~~~~~~~~~~~~~~~

Install from PyPI::

    pip install spektrum

Tests are plain classes. A ``Spec`` subclass groups cases: every public method that is
not a lifecycle hook (``before_all``, ``before_each``, ``after_each``, ``after_all``) and
not underscore-prefixed is a case. Nested Spec subclasses become child specs::

    from spektrum import Spec, expect

    class Addition(Spec):
        def before_each(self):
            self.total = 1 + 1

        def sums_two_numbers(self):
            expect(self.total).to.equal(2)

Run them by pointing the CLI at a path::

    spektrum -s path/to/specs

Spektrum looks for a ``spec`` directory in the working directory when ``-s`` is omitted.
Add ``--show-all-expects`` to print a line per assertion rather than per case, and
``-c N`` to run with concurrency.

Selecting what runs
~~~~~~~~~~~~~~~~~~~~

While you iterate on one spec, narrow the run rather than sitting through the whole suite.

``-p`` selects by module path -- either a bare module or a class inside it::

    spektrum -s spec -p checkout                 # every spec in checkout.py
    spektrum -s spec -p checkout.PaymentFlow     # one class and its children

Prefix the value with ``re:`` to match class paths by regular expression. The pattern is
anchored at the end, so it must describe the *tail* of the path -- a pattern that merely
appears in the middle matches nothing, with no error to tell you so::

    spektrum -s spec -p "re:checkout\..*Payment"     # classes ending in Payment
    spektrum -s spec -p "re:checkout\..*Payment.*"   # and those only containing it

``-t`` selects by case name, as a comma-delimited list. A name matches in every spec that
defines it, so one name can run in several places::

    spektrum -s spec -t adds_item_to_cart
    spektrum -s spec -t adds_item_to_cart,removes_item_from_cart

``-t`` accepts ``re:`` as well. That pattern is anchored at *both* ends, and is tried
against the method name and against the spaced form Spektrum prints in its output::

    spektrum -s spec -t "re:adds item to cart"

``-m`` selects by the ``@metadata`` decorator and ``--exclude-by-metadata`` is its
complement, which is how you mark a slow or environment-dependent group and skip it while
working locally::

    spektrum -s spec -m suite=smoke
    spektrum -s spec --exclude-by-metadata suite=slow

``--dry-run`` reports the tree without executing anything or evaluating a single assertion
-- the quickest way to confirm a filter selects what you meant before you wait on a run.

Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~~

Spektrum writes xunit XML for CI systems that consume it::

    spektrum -s path/to/specs --xunit-results results.xml

``--coverage`` records coverage data for the code under test into ``.coverage``, for a
following ``coverage report``; it prints nothing itself. ``--live`` serves a live progress
view over HTTP while the run is in flight. Spektrum ships console, xunit, live and TestRail
reporters, the last through the ``--tr-*`` options.

Contributing
~~~~~~~~~~~~~~

See the `contributing guide
<https://github.com/liquidweb/spektrum/blob/master/CONTRIBUTING.md>`_ for setup, the test
suites, and what a change needs to prove before review.

Release Notes
~~~~~~~~~~~~~~

- `Release notes
  <https://github.com/liquidweb/spektrum/blob/master/docs/release_notes/index.rst>`__ are
  available in the documentation
