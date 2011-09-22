# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server.cros.faftsequence import FAFTSequence


class firmware_CorruptFwA(FAFTSequence):
    """
    Servo based firmware A corruption test.
    """
    version = 1


    def confirm_fw_a_boot(self):
        if not self.crossystem_checker({'mainfw_act': 'A', 'tried_fwb': '0'}):
            self.faft_client.run_shell_command(
                    'chromeos-firmwareupdate --mode recovery')
            self.faft_client.software_reboot()
            self.wait_for_client_offline()
            self.wait_for_client()


    def setup(self):
        super(firmware_CorruptFwA, self).setup()
        self.confirm_fw_a_boot()


    def cleanup(self):
        self.confirm_fw_a_boot()
        super(firmware_CorruptFwA, self).cleanup()


    def run_once(self, host=None):
        self.register_faft_sequence((
            {   # Step 1, corrupt firmware A
                'state_checker': (self.crossystem_checker, {
                    'mainfw_act': 'A',
                    'tried_fwb': '0',
                }),
                'userspace_action': (self.faft_client.corrupt_firmware, 'a'),
            },
            {   # Step 2, expected firmware B boot and restore firmware A
                'state_checker': (self.crossystem_checker, {
                    'mainfw_act': 'B',
                    'tried_fwb': '0',
                }),
                'userspace_action': (self.faft_client.restore_firmware, 'a'),
            },
            {   # Step 3, expected firmware A boot, done
                'state_checker': (self.crossystem_checker, {
                    'mainfw_act': 'A',
                    'tried_fwb': '0',
                }),
            },
        ))
        self.run_faft_sequence()
