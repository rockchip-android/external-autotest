# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A module providing the summary for multiple test results.

This firmware_summary module is used to collect the test results of
multiple rounds from the logs generated by different firmware versions.
The test results of the various validators of every gesture are displayed.
In addition, the test results of every validator across all gestures are
also summarized.

Usage:
$ python firmware_summary log_directory


A typical summary output looks like

Test Summary (by gesture)            :  fw_2.41   fw_2.42     count
---------------------------------------------------------------------
one_finger_tracking
  CountTrackingIDValidator           :     1.00      0.90        12
  LinearityBothEndsValidator         :     0.97      0.89        12
  LinearityMiddleValidator           :     1.00      1.00        12
  NoGapValidator                     :     0.74      0.24        12
  NoReversedMotionBothEndsValidator  :     0.68      0.34        12
  NoReversedMotionMiddleValidator    :     1.00      1.00        12
  ReportRateValidator                :     1.00      1.00        12
one_finger_to_edge
  CountTrackingIDValidator           :     1.00      1.00         4
  LinearityBothEndsValidator         :     0.88      0.89         4
  LinearityMiddleValidator           :     1.00      1.00         4
  NoGapValidator                     :     0.50      0.00         4
  NoReversedMotionMiddleValidator    :     1.00      1.00         4
  RangeValidator                     :     1.00      1.00         4

  ...


Test Summary (by validator)          :   fw_2.4  fw_2.4.a     count
---------------------------------------------------------------------
  CountPacketsValidator              :     1.00      0.82         6
  CountTrackingIDValidator           :     0.92      0.88        84

  ...

"""


import getopt
import os
import sys

import firmware_log

from common_util import print_and_exit
from firmware_constants import OPTIONS
from test_conf import (log_root_dir, segment_weights, validator_weights)


class FirmwareSummary:
    """Summary for touch device firmware tests."""

    def __init__(self, log_dir, debug_flag=False,
                 segment_weights=segment_weights,
                 validator_weights=validator_weights):
        """ segment_weights and validator_weights are passed as arguments
        so that it is possible to assign arbitrary weights in unit tests.
        """
        if os.path.isdir(log_dir):
            self.log_dir = log_dir
        else:
            error_msg = 'Error: The test result directory does not exist: %s'
            print error_msg % log_dir
            sys.exit(-1)

        self.slog = firmware_log.SummaryLog(log_dir, segment_weights,
                                            validator_weights, debug_flag)

    def _print_summary_title(self, summary_title_str):
        """Print the summary of the test results by gesture."""
        # Create a flexible column title format according to the number of
        # firmware versions which could be 1, 2, or more.
        #
        # A typical summary title looks like
        # Test Summary ()          :    fw_11.26             fw_11.23
        #                               mean  ssd  count     mean ssd count
        # ----------------------------------------------------------------------
        #
        # The 1st line above is called title_fw.
        # The 2nd line above is called title_statistics.
        #
        # As an example for 2 firmwares, title_fw_format looks like:
        #     '{0:<37}:  {1:>12}  {2:>21}'
        title_fw_format_list = ['{0:<37}:',]
        for i in range(len(self.slog.fws)):
            format_space = 12 if i == 0 else (12 + 9)
            title_fw_format_list.append('{%d:>%d}' % (i + 1, format_space))
        title_fw_format = ' '.join(title_fw_format_list)

        # As an example for 2 firmwares, title_statistics_format looks like:
        #     '{0:>47} {1:>6} {2:>5} {3:>8} {4:>6} {5:>5}'
        title_statistics_format_list = []
        for i in range(len(self.slog.fws)):
            format_space = (12 + 35) if i == 0 else 8
            title_statistics_format_list.append('{%d:>%d}' % (3 * i,
                                                              format_space))
            title_statistics_format_list.append('{%d:>%d}' % (3 * i + 1 , 6))
            title_statistics_format_list.append('{%d:>%d}' % (3 * i + 2 , 5))
        title_statistics_format = ' '.join(title_statistics_format_list)

        # Create title_fw_list
        # As an example for two firmware versions, it looks like
        #   ['Test Summary (by gesture)', 'fw_2.4', 'fw_2.5']
        title_fw_list = [summary_title_str,] + self.slog.fws

        # Create title_statistics_list
        # As an example for two firmware versions, it looks like
        #   ['mean', 'ssd', 'count', 'mean', 'ssd', 'count', ]
        title_statistics_list = ['mean', 'ssd', 'count'] * len(self.slog.fws)

        # Print the title.
        title_fw = title_fw_format.format(*title_fw_list)
        title_statistics = title_statistics_format.format(
                *title_statistics_list)
        print '\n\n', title_fw
        print title_statistics
        print '-' * len(title_statistics)

    def _print_statistics_score(self, stat):
        """Print the score statistics including average, ssd, and counts.

        stat: a list about score statistics, [average, ssd, count]
        """
        # Create a flexible format to print scores, ssd, and counts according to
        # the number of firmware versions which could be 1, 2, or more.
        # As an example with 2 firmware versions, the format looks like
        #   '  {0:<35}:  {1:>8.2f} {2:>6.2f} {3:>5} {4:>8.2f} {5:>6.2f} {6:>5}'
        if len(stat) <= 1:
            return

        statistics_format_list = ['  {0:<35}:',]
        score_ssd_count_format = '{%d:>8.2f} {%d:>6.2f} {%d:>5}'
        for i in range(len(self.slog.fws)):
            statistics_format_list.append(
                    score_ssd_count_format % (i * 3 + 1, i * 3 + 2, i * 3 + 3))
        statistics_format = ' '.join(statistics_format_list)
        print statistics_format.format(*tuple(stat))

    def _print_result_stats(self, gesture=None):
        """Print the result statistics of validators."""
        for validator in self.slog.validators:
            stat_score_data = [validator,]
            for fw in self.slog.fws:
                result = self.slog.get_result(fw=fw, gesture=gesture,
                                              validator=validator)
                if result:
                    fw_stat_score = result.stat_score.all_data
                    if fw_stat_score:
                        stat_score_data += fw_stat_score
            # Print the score statistics of all firmwares on the same row.
            self._print_statistics_score(stat_score_data)

    def _print_result_stats_by_gesture(self):
        """Print the summary of the test results by gesture."""
        self._print_summary_title('Test Summary (by gesture)')
        for gesture in self.slog.gestures:
            print gesture
            self._print_result_stats(gesture=gesture)

    def _print_result_stats_by_validator(self):
        """Print the summary of the test results by validator. The validator
        results of all gestures are combined to compute the statistics.
        """
        self._print_summary_title('Test Summary (by validator)')
        self._print_result_stats()

    def _print_final_weighted_averages(self):
        """Print the final weighted averages of all validators."""
        title_str = 'Test Summary (final weighted averages)'
        print '\n\n' + title_str
        print '-' * len(title_str)
        weighted_average = self.slog.get_final_weighted_average()
        for fw in self.slog.fws:
            print '%s: %4.3f' % (fw, weighted_average[fw])

    def print_result_summary(self):
        """Print the summary of the test results."""
        self._print_result_stats_by_gesture()
        self._print_result_stats_by_validator()
        self._print_final_weighted_averages()


def _usage_and_exit():
    """Print the usage message and exit."""
    prog = sys.argv[0]
    print 'Usage: $ python %s [options]\n' % prog
    print 'options:'
    print '  -D, --%s' % OPTIONS.DEBUG
    print '        enable debug flag'
    print '  -d, --%s' % OPTIONS.DIR
    print '        specify which log directory to derive the summary'
    print '  -h, --%s' % OPTIONS.HELP
    print '        show this help'
    print '  -m, --%s' % OPTIONS.METRICS
    print '        display the detailed summary metrics of various validators'
    print
    print 'Examples:'
    print '    # Specify the log root directory.'
    print '    $ python %s -d /tmp' % prog
    print '    # Turn on the metrics flag.'
    print '    $ python %s -m' % prog
    sys.exit(-1)


def _parsing_error(msg):
    """Print the usage and exit when encountering parsing error."""
    print 'Error: %s' % msg
    _usage_and_exit()


def _parse_options():
    """Parse the options."""
    # Set the default values of options.
    options = {OPTIONS.DEBUG: False,
               OPTIONS.DIR: log_root_dir,
               OPTIONS.METRICS: False,
    }

    try:
        short_opt = 'Dd:hm'
        long_opt = [OPTIONS.DEBUG,
                    OPTIONS.DIR + '=',
                    OPTIONS.HELP,
                    OPTIONS.METRICS,
        ]
        opts, args = getopt.getopt(sys.argv[1:], short_opt, long_opt)
    except getopt.GetoptError, err:
        _parsing_error(str(err))

    for opt, arg in opts:
        if opt in ('-h', '--%s' % OPTIONS.HELP):
            _usage_and_exit()
        elif opt in ('-D', '--%s' % OPTIONS.DEBUG):
            options[OPTIONS.DEBUG] = True
        elif opt in ('-d', '--%s' % OPTIONS.DIR):
            options[OPTIONS.DIR] = arg
            if not os.path.isdir(arg):
                print 'Error: the log directory %s does not exist.' % arg
                _usage_and_exit()
        elif opt in ('-m', '--%s' % OPTIONS.METRICS):
            options[OPTIONS.METRICS] = True
        else:
            msg = 'This option "%s" is not supported.' % opt
            _parsing_error(opt)

    return options


if __name__ == '__main__':
    options = _parse_options()
    summary = FirmwareSummary(options[OPTIONS.DIR],
                              debug_flag=options[OPTIONS.DEBUG])
    summary.print_result_summary()
