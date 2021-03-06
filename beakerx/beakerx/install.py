# Copyright 2017 TWO SIGMA OPEN SOURCE, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Installs BeakerX into a Jupyter and Python environment.'''

import argparse
import json
import os
import pkg_resources
import shutil
import subprocess
import sys
import tempfile

from traitlets.config.manager import BaseJSONConfigManager
from distutils import log


def _all_kernels():
    kernels = pkg_resources.resource_listdir(
        'beakerx', os.path.join('static', 'kernel'))
    return [kernel for kernel in kernels if kernel != 'base']


def _classpath_for(kernel):
    return pkg_resources.resource_filename(
        'beakerx', os.path.join('static', 'kernel', kernel, 'lib', '*'))


def _install_nbextension():
    subprocess.check_call(["jupyter", "nbextension", "install", "beakerx", "--py", "--sys-prefix"])
    subprocess.check_call(["jupyter", "nbextension", "enable", "beakerx", "--py", "--sys-prefix"])


def _copy_tree(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _install_css():
    log.info("installing custom CSS...")
    resource = os.path.join('static', 'custom')
    src_base = pkg_resources.resource_filename('beakerx', resource)
    dst_base = pkg_resources.resource_filename('notebook', resource)
    _copy_tree(os.path.join(src_base, 'fonts'), os.path.join(dst_base, 'fonts'))
    shutil.copyfile(os.path.join(src_base, 'custom.css'), os.path.join(dst_base, 'custom.css'))


def _install_kernels():
    base_classpath = _classpath_for('base')

    for kernel in _all_kernels():
        kernel_classpath = _classpath_for(kernel)
        classpath = os.pathsep.join([base_classpath, kernel_classpath])
        # TODO: replace with string.Template, though this requires the
        # developer install to change too, so not doing right now.
        template = pkg_resources.resource_string(
            'beakerx', os.path.join('static', 'kernel', kernel, 'kernel.json'))
        contents = template.decode().replace('__PATH__', classpath)
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'kernel.json'), 'w') as f:
                f.write(contents)
            install_cmd = [
                'jupyter', 'kernelspec', 'install',
                '--sys-prefix', '--replace',
                '--name', kernel, tmpdir
            ]
            subprocess.check_call(install_cmd)


def _pretty(it): 
    return json.dumps(it, indent=2)

def _install_kernelspec_manager(prefix, disable=False):
    CKSM = "beakerx.kernel_spec.BeakerXKernelSpec"
    KSMC = "kernel_spec_class"

    action_prefix = "Dis" if disable else "En"
    log.info("{}abling BeakerX server config...".format(action_prefix))
    path = os.path.join(prefix, "etc", "jupyter")
    if not os.path.exists(path):
        log.debug("Making directory {}...".format(path))
        os.makedirs(path)
    cm = BaseJSONConfigManager(config_dir=path)
    cfg = cm.get("jupyter_notebook_config")
    log.debug("Existing config in {}...\n{}".format(path, _pretty(cfg)))
    nb_app = cfg.setdefault("KernelSpecManager", {})
    if disable and nb_app.get(KSMC, None) == CKSM:
        nb_app.pop(KSMC)
    else:
        nb_app.update({KSMC: CKSM})

    log.debug("Writing config in {}...".format(path))
    cm.set("jupyter_notebook_config", cfg)
    cfg = cm.get("jupyter_notebook_config")

    log.debug("Verifying config in {}...\n{}".format(path, _pretty(cfg)))
    if disable:
        assert KSMC not in cfg["KernelSpecManager"]
    else:
        assert cfg["KernelSpecManager"][KSMC] == CKSM

    log.info("{}abled BeakerX server config".format(action_prefix))
    

def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",
                        help="location of the environment to install into",
                        default=sys.prefix)
    return parser


def install():
    try:
        parser = make_parser()
        args = parser.parse_args()
        _install_nbextension()
        _install_kernels()
        _install_css()
        _install_kernelspec_manager(args.prefix)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    install()
