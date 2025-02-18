#
# Copyright 2022 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from ansible.module_utils.basic import AnsibleModule
import os.path

result = dict(
    rc=0,
    msg='',
    state='',
    output=''
)

def check_status_queue_managers(qmname, module):
    rc, stdout, stderr = module.run_command(['dspmq', '-m', qmname])

    if stdout is not None:
        if 'Running' in stdout:
            return True
   
    return False



def state_present(qmname, module):
    if module.params['unit_test'] is False:
        rc, stdout, stderr = module.run_command(['crtmqm', qmname])
        result['rc'] = rc

        if module.params['mqsc_file'] is not None:
            run_mqsc_file(qmname, module)

        if rc == 0:
            result['rc'] = rc
            result['msg'] = 'IBM MQ Queue Manager Created'
            result['state'] = 'present'
        elif rc == 8:
            module.exit_json(skipped=True, state='present', msg='IBM MQ Queue Manager already exists')
        elif rc > 0:
            module.fail_json(**result)

def run_mqsc_file(qmname, module):
    is_running = check_status_queue_managers(qmname, module)
    exists = os.path.isfile(module.params['mqsc_file'])

    if exists is True:
        if is_running:
            rc, stdout, stderr = module.run_command(["runmqsc", qmname, "-f", module.params['mqsc_file']])
            result['rc'] = rc
            result['output'] = stdout + stderr
            if rc == 0:
                result['msg'] = 'MQSC configuration successfully applied to Queue Manager'
        else:
            rc, stdout, stderr = module.run_command(['strmqm', qmname])
            rc, stdout, stderr = module.run_command(["runmqsc", qmname, "-f", module.params['mqsc_file']])
            result['rc'] = rc
            result['output'] = stdout + stderr
            rc, stdout, stderr = module.run_command(['endmqm', qmname])
            if rc == 0:
                result['msg'] = 'MQSC configuration successfully applied to Queue Manager'
    else:
        result['rc'] = 16    
        result['msg'] = 'MQSC file could not be found'


def state_running(qmname, module):
    result['msg'] = 'IBM MQ queue manager \'' + str(qmname) + '\' started'
    if module.params['unit_test'] is False:
        rc, stdout, stderr = module.run_command(['dspmq', '-m', qmname])

        if rc == 72:
            module.exit_json(skipped=True, state='absent', msg='IBM MQ queue manager does not exist. Please create it first to set it running.')
            
        rc, stdout, stderr = module.run_command(['strmqm', qmname])
        result['rc'] = rc

        if module.params['mqsc_file'] is not None:
            run_mqsc_file(qmname, module)

        if rc == 5 and module.params['mqsc_file'] is None:
            module.exit_json(skipped=True, state='running', msg='IBM MQ queue manager running')
        elif rc ==5 and module.params['mqsc_file'] is not None:
            result['msg'] += 'IBM MQ queue manager is running'
        elif rc > 0:
            module.fail_json(**result)

def state_stopped(qmname, module):
    if module.params['unit_test'] is False:
        
        if module.params['mqsc_file'] is not None:
            run_mqsc_file(qmname, module)

        rc, stdout, stderr = module.run_command(['endmqm', qmname])
        result['msg'] = stdout + stderr

        if rc == 16:
            result['state'] = 'absent'
            module.fail_json(**result)
        elif rc == 40:
            module.exit_json(skipped=True, state='present', msg = stdout + stderr)
        elif rc > 0:
            module.fail_json(**result)

def state_absent(qmname, module):
    result['msg'] = 'IBM MQ queue manager deleted.'
    if module.params['unit_test'] is False:
        rc, stdout, stderr = module.run_command(['dltmqm', qmname])
        result['msg'] = stdout + stderr
        result['rc'] = rc
        if rc == 5:
            module.exit_json(skipped=True, state='running', msg='IBM MQ queue manager running.')
        elif rc == 16:
            # Queue Manager does not exist
            module.exit_json(skipped=True, state='absent', msg='AMQ8118E: IBM MQ queue manager does not exist.')
        elif rc > 0:
            module.fail_json(**result)

def state_invalid(qmname, module):
    result['state'] = ''
    result['msg'] = 'Unrecognised State'
    result['rc'] = 16
    module.fail_json(**result)


def main():
    qmgr_attributes = dict(
        qmname=dict(type='list', required=True, max_len=48),
        state=dict(type='str', required=True),
        description=dict(type='str', required=False),
        unit_test=dict(type='bool', default=False, required=False),
        mqsc_file=dict(type='str', required=False)
    )

    module = AnsibleModule(
        argument_spec=qmgr_attributes
    )

    ops = {
        "present": state_present,
        "running":  state_running,
        "stopped":  state_stopped,
        "absent":   state_absent
    }

    if module.params['unit_test'] is False:
        for qmname in module.params['qmname']:
            ops.get(module.params['state'], state_invalid)(qmname, module)
    
    module.exit_json(**result)

if __name__ == '__main__':
    main()