# -*- coding: utf-8 -*-
""" Test module for C/C++  based packages. """

import re

from FedoraReview import CheckBase, Mock, RpmFile, RegistryBase


class Registry(RegistryBase):
    """ Register all checks in this file. """

    group = 'C/C++'

    def is_applicable(self):
        """Need more comprehensive check and return True in valid cases"""
        if self.is_user_enabled():
            return self.user_enabled_value()
        archs = self.checks.spec.expand_tag('BuildArchs')
        if len(archs) == 1 and archs[0].lower() == 'noarch':
            return False
        if self.checks.buildsrc.is_available:
            src = self.checks.buildsrc
        else:
            src = self.checks.sources
        rpms = self.checks.rpms
        if rpms.find_re(r'/usr/(lib|lib64)/[\w\-]*\.so\.[0-9]') or \
            rpms.find('*.h') or rpms.find('*.a') or \
                src.find('*.c') or src.find('*.C') or src.find('*.cpp'):
                    return True
        return False


class CCppCheckBase(CheckBase):
    ''' Common base class for module tests (a. k. a. checks). '''

    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)


class CheckLDConfig(CCppCheckBase):
    '''
    MUST: Every binary RPM package (or subpackage) which stores shared
    library files (not just symlinks) in any of the dynamic linker's
    default paths, must call ldconfig in %post and %postun.
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   '/Guidelines#Shared_Libraries'
        self.text = 'ldconfig called in %post and %postun if required.'
        self.automatic = True
        self.type = 'MUST'
        self.sofiles_regex = r'/usr/(lib|lib64)/[\w\-]*\.so\.[0-9]'

    def is_applicable(self):
        ''' check if this test is applicable '''
        return bool(self.rpms.find_re(self.sofiles_regex))

    def run_on_applicable(self):
        ''' Run the test, called if is_applicable() is True. '''
        bad_pkgs = []
        for pkg in self.spec.packages:
            nvr = self.spec.get_package_nvr(pkg)
            rpm = RpmFile(pkg, nvr.version, nvr.release)
            if not self.rpms.find_re(self.sofiles_regex, pkg):
                continue
            if not rpm.post or '/sbin/ldconfig' not in rpm.post or \
                not rpm.postun or '/sbin/ldconfig' not in rpm.postun:
                    bad_pkgs.append(pkg)
        if bad_pkgs:
            self.set_passed(self.FAIL,
                            '/sbin/ldconfig not called in '
                            + ', '.join(bad_pkgs))
        else:
            self.set_passed(self.PASS)


class CheckHeaderFiles(CCppCheckBase):
    '''
    MUST: Header files must be in a -devel package
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#DevelPackages'
        self.text = 'Header files in -devel subpackage, if present.'
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        ''' check if this test is applicable '''
        return self.rpms.find('*.h')

    def run_on_applicable(self):
        ''' Run the test, called if is_applicable() is True. '''
        passed = True
        extra = ""
        for pkg in self.spec.packages:
            for path in self.rpms.find_all('*.h', pkg):
                # header files (.h) under /usr/src/debug/* will be in
                #  the -debuginfo package.
                if path.startswith('/usr/src/debug/') and '-debuginfo' in pkg:
                    continue
                # All other .h files should be in a -devel package.
                if '-devel' not in pkg:
                    passed = False
                    extra += "%s : %s\n" % (pkg, path)
        self.set_passed(passed, extra)


class CheckNoStaticExecutables(CCppCheckBase):
    ''' We do not packaga static executables, do we? '''

    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#Staticly_Linking_Executables'
        self.text = 'Package contains no static executables.'
        self.automatic = False
        self.type = 'MUST'


class CheckSoFiles(CCppCheckBase):
    '''
    MUST: If a package contains library files with a suffix (e.g.
    libfoo.so.1.1), then library files that end in .so (without suffix)
    must go in a -devel package.
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#DevelPackages'
        self.text = 'Development (unversioned) .so files ' \
                    'in -devel subpackage, if present.'
        self.automatic = True
        self.type = 'MUST'
        # we ignore .so files in private directories
        self.bad_re = re.compile(r'/usr/(lib|lib64)/[\w\-]*\.so$')

    def run(self):
        ''' Run the test, always called '''
        if not self.rpms.find('*.so'):
            self.set_passed(self.NA)
            return
        passed = 'pass'
        in_libdir = False
        in_private = False
        bad_list = []
        attachments = []
        extra = None
        for pkg in self.spec.packages:
            if pkg.endswith('-devel'):
                continue
            for path in self.rpms.find_all('*.so', pkg):
                bad_list.append("%s: %s" % (pkg, path))
                if self.bad_re.search(path):
                    in_libdir = True
                else:
                    in_private = True

        if in_private and not in_libdir:
            extra = "Unversioned so-files in private" \
                    " %_libdir subdirectory (see attachment)." \
                    " Verify they are not in ld path. "
            passed = 'pending'

        if in_libdir:
            extra = "Unversioned so-files directly in %_libdir."
            passed = 'fail'

        if bad_list:
            attachments = [self.Attachment('Unversioned so-files',
                                           "\n".join(bad_list))]

        self.set_passed(passed, extra, attachments)


class CheckLibToolArchives(CCppCheckBase):
    '''
    MUST: Packages must NOT contain any .la libtool archives,
    these must be removed in the spec if they are built.
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#StaticLibraries'
        self.text = 'Package does not contain any libtool archives (.la)'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        ''' Run the test, called if is_applicable() is True. '''
        if not self.rpms.find('*.la'):
            self.set_passed(self.PASS)
        else:
            extra = ""
            for pkg in self.spec.packages:
                for path in self.rpms.find_all('*.la', pkg):
                    extra += "%s : %s\n" % (pkg, path)
            self.set_passed(self.FAIL, extra)


class CheckRPATH(CCppCheckBase):
    ''' Thou shall not use bad RPATH. '''

    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#Beware_of_Rpath'
        self.text = 'Rpath absent or only used for internal libs.'
        self.automatic = True
        self.type = 'MUST'
        self.needs.append('CheckRpmlint')

    def run_on_applicable(self):
        ''' Run the test, called if is_applicable() is True. '''
        if self.checks.checkdict['CheckRpmlint'].is_disabled:
            self.set_passed(self.PENDING, 'Rpmlint run disabled')
            return
        for line in Mock.rpmlint_output:
            if 'binary-or-shlib-defines-rpath' in line:
                self.set_passed(self.PENDING, 'See rpmlint output')
                return
        self.set_passed(self.PASS)


class CheckBundledGnulib(CCppCheckBase):
    ''' Make sure there is a Provides: matching bundled gnulib. '''

    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:' \
                   'No_Bundled_Libraries#Requirement_if_you_bundle'
        self.text = 'Provides: bundled(gnulib) in place as required.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        try:
            if not self.buildsrc.find('*00gnulib.m4'):
                self.set_passed(self.NA)
                return
        except LookupError:
            self.set_passed(self.PENDING, "Sources not installed")
            return
        for pkg in self.spec.packages:
            if 'bundled(gnulib)' in self.rpms.get(pkg).provides:
                self.set_passed(self.PASS)
                break
        else:
            self.set_passed(self.FAIL,
                            'Bundled gnulib but no '
                            'Provides: bundled(gnulib)')


class CheckNoKernelModules(CCppCheckBase):
    '''
    At one point (pre Fedora 8), packages containing "addon" kernel modules
    were permitted.  This is no longer the case. Fedora strongly encourages
    kernel module packagers to submit their code into the upstream kernel tree.
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#No_External_Kernel_Modules'
        self.text = 'Package does not contain kernel modules.'
        self.automatic = False
        self.type = 'MUST'


# vim: set expandtab ts=4 sw=4:
