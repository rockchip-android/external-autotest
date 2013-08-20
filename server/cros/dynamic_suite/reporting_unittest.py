#!/usr/bin/python
#
# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import mox

import common
from autotest_lib.server.cros.dynamic_suite import job_status, reporting
from autotest_lib.site_utils import phapi_lib
from chromite.lib import gdata_lib


class ReportingTest(mox.MoxTestBase):
    """Unittests to verify basic control flow for automatic bug filing."""

    # fake issue id to use in testing duplicate issues
    _FAKE_ISSUE_ID = 123

    # test report used to generate failure
    test_report = {
        'build':'build-build/R1-1',
        'chrome_version':'28.0',
        'suite':'suite',
        'test':'bad_test',
        'reason':'dreadful_reason',
        'owner':'user',
        'hostname':'myhost',
        'job_id':'myjob',
        'status': 'FAIL',
    }

    bug_template = {
        'labels': ['Cr-Internals-WebRTC'],
        'owner': 'myself',
        'status': 'Fixed',
        'summary': 'This is a short summary',
        'title': None,
    }

    def _get_failure(self):
        """Get a TestFailure so we can report it.

        @return: a failure object initialized with values from test_report.
        """
        expected_result = job_status.Status(self.test_report.get('status'),
            self.test_report.get('test'),
            reason=self.test_report.get('reason'),
            job_id=self.test_report.get('job_id'),
            owner=self.test_report.get('owner'),
            hostname=self.test_report.get('hostname'))

        return reporting.TestFailure(self.test_report.get('build'),
            self.test_report.get('chrome_version'),
            self.test_report.get('suite'), expected_result)


    def setUp(self):
        super(ReportingTest, self).setUp()
        self.mox.StubOutClassWithMocks(phapi_lib, 'ProjectHostingApiClient')
        self._orig_project_name = reporting.Reporter._project_name
        self._orig_username = reporting.Reporter._username
        self._orig_password = reporting.Reporter._password

        # We want to have some data so that the Reporter doesn't fail at
        # initialization.
        reporting.Reporter._project_name = 'project'
        reporting.Reporter._username = 'username'
        reporting.Reporter._password = 'password'


    def tearDown(self):
        reporting.Reporter._project_name = self._orig_project_name
        reporting.Reporter._username = self._orig_username
        reporting.Reporter._password = self._orig_password
        super(ReportingTest, self).tearDown()


    def testNewIssue(self):
        """Add a new issue to the tracker when a matching issue isn't found.

        Confirms that we call CreateTrackerIssue when an Issue search
        returns None.
        """
        self.mox.StubOutWithMock(reporting.Reporter, '_find_issue_by_marker')
        self.mox.StubOutWithMock(reporting.TestFailure, 'summary')

        client = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                   mox.IgnoreArg())
        client.create_issue(mox.IgnoreArg()).AndReturn(
            {'id': self._FAKE_ISSUE_ID})
        reporting.Reporter._find_issue_by_marker(mox.IgnoreArg()).AndReturn(
            None)
        reporting.TestFailure.summary().AndReturn('')

        self.mox.ReplayAll()
        bug_id = reporting.Reporter().report(self._get_failure())

        self.assertEqual(bug_id, self._FAKE_ISSUE_ID)


    def testDuplicateIssue(self):
        """Dedupe to an existing issue when one is found.

        Confirms that we call AppendTrackerIssueById with the same issue
        returned by the issue search.
        """
        self.mox.StubOutWithMock(reporting.Reporter, '_find_issue_by_marker')
        self.mox.StubOutWithMock(reporting.TestFailure, 'summary')

        issue = self.mox.CreateMock(gdata_lib.Issue)
        issue.id = self._FAKE_ISSUE_ID
        issue.labels = []

        client = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                   mox.IgnoreArg())
        client.update_issue(self._FAKE_ISSUE_ID, mox.IgnoreArg())
        reporting.Reporter._find_issue_by_marker(mox.IgnoreArg()).AndReturn(
            issue)

        reporting.TestFailure.summary().AndReturn('')

        self.mox.ReplayAll()
        bug_id = reporting.Reporter().report(self._get_failure())

        self.assertEqual(bug_id, self._FAKE_ISSUE_ID)


    def testSuiteIssueConfig(self):
        """Test that the suite bug template values are not overridden."""

        def check_suite_options(issue):
            """
            Checks to see if the options specified in bug_template reflect in
            the issue we're about to file, and that the autofiled label was not
            lost in the process.

            @param issue: issue to check labels on.
            """
            assert('autofiled' in issue.labels)
            for k, v in self.bug_template.iteritems():
                if (isinstance(v, list)
                    and all(item in getattr(issue, k) for item in v)):
                    continue
                if v and getattr(issue, k) is not v:
                    return False
            return True

        self.mox.StubOutWithMock(reporting.Reporter, '_find_issue_by_marker')
        self.mox.StubOutWithMock(reporting.TestFailure, 'summary')

        reporting.Reporter._find_issue_by_marker(mox.IgnoreArg()).AndReturn(
            None)
        reporting.TestFailure.summary().AndReturn('Summary')

        mock_host = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                      mox.IgnoreArg())
        bug = self.mox.CreateMockAnything()
        mock_host.create_issue(mox.IgnoreArg()).AndReturn(
            {'id': self._FAKE_ISSUE_ID})

        self.mox.ReplayAll()
        bug_id = reporting.Reporter().report(self._get_failure(),
                                             self.bug_template)

        self.assertEqual(bug_id, self._FAKE_ISSUE_ID)


    def testGenericBugCanBeFiled(self):
        """Test that we can use a Bug object to file a bug report."""
        self.mox.StubOutWithMock(reporting.Reporter, '_find_issue_by_marker')

        bug = reporting.Bug('title', 'summary', 'marker')

        reporting.Reporter._find_issue_by_marker(mox.IgnoreArg()).AndReturn(
            None)

        mock_host = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                      mox.IgnoreArg())
        mock_host.create_issue(mox.IgnoreArg()).AndReturn(
            {'id': self._FAKE_ISSUE_ID})

        self.mox.ReplayAll()
        bug_id = reporting.Reporter().report(bug)

        self.assertEqual(bug_id, self._FAKE_ISSUE_ID)


    def testWithSearchMarkerSetToNoneIsNotDeduped(self):
        """Test that we do not dedupe bugs that have no search marker."""

        bug = reporting.Bug('title', 'summary', search_marker=None)

        mock_host = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                      mox.IgnoreArg())
        mock_host.create_issue(mox.IgnoreArg()).AndReturn(
            {'id': self._FAKE_ISSUE_ID})

        self.mox.ReplayAll()
        bug_id = reporting.Reporter().report(bug)

        self.assertEqual(bug_id, self._FAKE_ISSUE_ID)


class FindIssueByMarkerTests(mox.MoxTestBase):
    """Tests the _find_issue_by_marker function."""

    def setUp(self):
        super(FindIssueByMarkerTests, self).setUp()
        self.mox.StubOutClassWithMocks(phapi_lib, 'ProjectHostingApiClient')
        self._orig_project_name = reporting.Reporter._project_name
        self._orig_username = reporting.Reporter._username
        self._orig_password = reporting.Reporter._password

        # We want to have some data so that the Reporter doesn't fail at
        # initialization.
        reporting.Reporter._project_name = 'project'
        reporting.Reporter._username = 'username'
        reporting.Reporter._password = 'password'


    def tearDown(self):
        reporting.Reporter._project_name = self._orig_project_name
        reporting.Reporter._username = self._orig_username
        reporting.Reporter._password = self._orig_password
        super(FindIssueByMarkerTests, self).tearDown()


    def testReturnNoneIfMarkerIsNone(self):
        """Test that we do not look up an issue if the search marker is None."""
        mock_host = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                      mox.IgnoreArg())

        self.mox.ReplayAll()
        result = reporting.Reporter()._find_issue_by_marker(None)
        self.assertTrue(result is None)


class AnchorSummaryTests(mox.MoxTestBase):
    """Tests the _anchor_summary function."""

    def setUp(self):
        super(AnchorSummaryTests, self).setUp()
        self.mox.StubOutClassWithMocks(phapi_lib, 'ProjectHostingApiClient')
        self._orig_project_name = reporting.Reporter._project_name
        self._orig_username = reporting.Reporter._username
        self._orig_password = reporting.Reporter._password

        # We want to have some data so that the Reporter doesn't fail at
        # initialization.
        reporting.Reporter._project_name = 'project'
        reporting.Reporter._username = 'username'
        reporting.Reporter._password = 'password'


    def tearDown(self):
        reporting.Reporter._project_name = self._orig_project_name
        reporting.Reporter._username = self._orig_username
        reporting.Reporter._password = self._orig_password
        super(AnchorSummaryTests, self).tearDown()


    def test_summary_returned_untouched_if_no_search_maker(self):
        """Test that we just return the summary if we have no search marker."""
        mock_host = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                      mox.IgnoreArg())

        bug = reporting.Bug('title', 'summary', None)

        self.mox.ReplayAll()
        result = reporting.Reporter()._anchor_summary(bug)

        self.assertEqual(result, 'summary')


    def test_append_anchor_to_summary_if_search_marker(self):
        """Test that we add an anchor to the search marker."""
        mock_host = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                      mox.IgnoreArg())

        bug = reporting.Bug('title', 'summary', 'marker')

        self.mox.ReplayAll()
        result = reporting.Reporter()._anchor_summary(bug)

        self.assertEqual(result, 'summary\n\n%smarker\n' %
                                 reporting.Reporter._SEARCH_MARKER)


class LabelUpdateTests(mox.MoxTestBase):
    """Test the _create_autofiled_count_update() function."""

    def setUp(self):
        super(LabelUpdateTests, self).setUp()
        self.mox.StubOutClassWithMocks(phapi_lib, 'ProjectHostingApiClient')
        self._orig_project_name = reporting.Reporter._project_name
        self._orig_username = reporting.Reporter._username
        self._orig_password = reporting.Reporter._password

        # We want to have some data so that the Reporter doesn't fail at
        # initialization.
        reporting.Reporter._project_name = 'project'
        reporting.Reporter._username = 'username'
        reporting.Reporter._password = 'password'


    def tearDown(self):
        reporting.Reporter._project_name = self._orig_project_name
        reporting.Reporter._username = self._orig_username
        reporting.Reporter._password = self._orig_password
        super(LabelUpdateTests, self).tearDown()


    def _create_count_label(self, n):
        return '%s%d' % (reporting.Reporter._AUTOFILED_COUNT, n)


    def _test_count_label_update(self, labels, remove, create):
        """Utility to test _create_autofiled_count_update().

        @param labels    Input list of labels.
        @param remove    List of labels expected to be removed in
                         the result.
        @param create    Single label expected to be created in the
                         result.
        """
        client = phapi_lib.ProjectHostingApiClient(mox.IgnoreArg(),
                                                   mox.IgnoreArg())
        self.mox.ReplayAll()
        issue = self.mox.CreateMock(gdata_lib.Issue)
        issue.labels = labels

        reporter = reporting.Reporter()
        new_labels = reporter._create_autofiled_count_update(issue)
        expected = map(lambda l: '-' + l, remove)
        expected.append(create)
        self.assertEqual(new_labels, expected)


    def testCountLabelIncrement(self):
        """Test that incrementing an autofiled-count label should work."""
        n = 3
        old_label = self._create_count_label(n)
        new_label = self._create_count_label(n + 1)
        self._test_count_label_update([old_label], [old_label], new_label)


    def testCountLabelIncrementPredefined(self):
        """Test that Reporter._PREDEFINED_LABELS has a sane autofiled-count."""
        self._test_count_label_update(
                reporting.Reporter._PREDEFINED_LABELS,
                [self._create_count_label(1)],
                self._create_count_label(2))


    def testCountLabelCreate(self):
        """Test that old bugs should get a correct autofiled-count."""
        self._test_count_label_update([], [],
                                      self._create_count_label(2))


    def testCountLabelIncrementMultiple(self):
        """Test that duplicate autofiled-count labels are handled."""
        old_count1 = self._create_count_label(2)
        old_count2 = self._create_count_label(3)
        new_count = self._create_count_label(4)
        self._test_count_label_update([old_count1, old_count2],
                                      [old_count1, old_count2],
                                      new_count)


    def testCountLabelSkipUnknown(self):
        """Test that autofiled-count increment ignores unknown labels."""
        old_count = self._create_count_label(3)
        new_count = self._create_count_label(4)
        self._test_count_label_update(['unknown-label', old_count],
                                      [old_count], new_count)


    def testCountLabelSkipMalformed(self):
        """Test that autofiled-count increment ignores unusual labels."""
        old_count = self._create_count_label(3)
        new_count = self._create_count_label(4)
        self._test_count_label_update(
                [reporting.Reporter._AUTOFILED_COUNT + 'bogus',
                 self._create_count_label(8) + '-bogus',
                 old_count],
                [old_count], new_count)


if __name__ == '__main__':
    unittest.main()
