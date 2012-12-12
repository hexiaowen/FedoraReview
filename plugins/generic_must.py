#-*- coding: utf-8 -*-

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>


''' Generic MUST checks, default Generic group. '''

import os
import os.path
import re
import rpm

from glob import glob
from StringIO import StringIO
from subprocess import Popen, PIPE
try:
    from subprocess import check_output          # pylint: disable=E0611
except ImportError:
    from FedoraReview.el_compat import check_output


from FedoraReview import CheckBase, Mock, ReviewDirs
from FedoraReview import ReviewError             # pylint: disable=W0611
from FedoraReview import RegistryBase, Settings


def in_list(what, list_):
    ''' test if 'what' is in each item in list_. '''
    for item in list_:
        if not item:
            return False
        if not what in item:
            return False
    return True


class Registry(RegistryBase):
    ''' Module registration, register all checks. '''
    group = 'Generic'

    def register_flags(self):
        epel5 = self.Flag('EPEL5', 'Review package for EPEL5', __file__)
        self.checks.flags.add(epel5)

    def is_applicable(self):
        return True


class GenericMustCheckbase(CheckBase):
    ''' Base class for all generic tests. '''

    def __init__(self, checks):
        CheckBase.__init__(self, checks, __file__)


class CheckApprovedLicense(GenericMustCheckbase):
    '''
    MUST: The package must be licensed with a Fedora approved license and
    meet the Licensing Guidelines .
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines'
        self.text = 'Package is licensed with an open-source'       \
                    ' compatible license and meets other legal'     \
                    ' requirements as defined in the legal section' \
                    ' of Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'


class CheckBundledLibs(GenericMustCheckbase):
    '''
    MUST: Packages must NOT bundle copies of system libraries.
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging:Guidelines#Duplication_of_system_libraries'
        self.text = 'Package contains no bundled libraries.'
        self.automatic = False
        self.type = 'MUST'


class CheckBuildCompilerFlags(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Compiler_flags
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Compiler_flags'
        self.text = '%build honors applicable compiler flags or ' \
                    'justifies otherwise.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        archs = self.checks.spec.expand_tag('BuildArchs')
        if len(archs) == 1 and archs[0].lower() == 'noarch':
            self.set_passed(self.NA)
            return
        self.set_passed(self.PENDING)


class CheckBuildRequires(GenericMustCheckbase):
    '''
    MUST: All build dependencies must be listed in BuildRequires,
    except for any that are listed in the exceptions section of the
    Packaging Guidelines Inclusion of those as BuildRequires is
    optional. Apply common sense.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Exceptions_2
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Exceptions_2'
        self.text = 'All build dependencies are listed in BuildRequires,' \
                    ' except for any that are  listed in the exceptions' \
                    ' section of Packaging Guidelines.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):

        if  self.checks.checkdict['CheckBuild'].is_pending:
            self.set_passed('pending', 'Using prebuilt rpms.')
        elif self.checks.checkdict['CheckBuild'].is_passed:
            brequires = self.spec.build_requires
            pkg_by_default = ['bash', 'bzip2', 'coreutils', 'cpio',
                'diffutils', 'fedora-release', 'findutils', 'gawk',
                'gcc', 'gcc-c++', 'grep', 'gzip', 'info', 'make',
                'patch', 'redhat-rpm-config', 'rpm-build', 'sed',
                'shadow-utils', 'tar', 'unzip', 'util-linux-ng',
                'which', 'xz']
            intersec = list(set(brequires).intersection(set(pkg_by_default)))
            if intersec:
                self.set_passed(False, 'These BR are not needed: %s' % (
                ' '.join(intersec)))
            else:
                self.set_passed(True)
        else:
            self.set_passed(False,
                            'The package did not build '
                            'BR could therefore not be checked or the'
                            ' package failed to build because of'
                            ' missing BR')


class CheckChangelogFormat(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Changelogs
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Changelogs'
        self.text = 'Changelog in prescribed format.'
        self.automatic = False
        self.type = 'MUST'


class CheckCodeAndContent(GenericMustCheckbase):
    '''
    MUST: The package must contain code, or permissable content.
    http://fedoraproject.org/wiki/Packaging/Guidelines#CodeVsContent
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#CodeVsContent'
        self.text = 'Sources contain only permissible' \
                    ' code or content.'
        self.automatic = False
        self.type = 'MUST'


class CheckConfigNoReplace(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Configuration_files'
        self.text = '%config files are marked noreplace or the reason' \
                    ' is justified.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        rc = self.NA
        extra = ''
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if line.startswith('%config'):
                    if not line.startswith('%config(noreplace)'):
                        extra += line
                    else:
                        rc = self.PASS
        self.set_passed(self.FAIL if extra else rc, extra)


class CheckCleanBuildroot(GenericMustCheckbase):
    ''' Check that buildroot is cleaned as appropriate. '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.text = 'Package does not run rm -rf %{buildroot}' \
                    ' (or $RPM_BUILD_ROOT) at the beginning of %install.'
        self.automatic = True

    def run(self):
        has_clean = False
        regex = 'rm\s+\-[rf][rf]\s+(%{buildroot}|$RPM_BUILD_ROOT)'
        regex  = rpm.expandMacro(regex)
        install_sec = self.spec.get_section('%install', raw=True)
        has_clean = install_sec and re.search(regex, install_sec)
        if self.flags['EPEL5']:
            self.text = 'EPEL5: Package does run rm -rf %{buildroot}' \
                  ' (or $RPM_BUILD_ROOT) at the beginning of %install.'
        if has_clean and self.flags['EPEL5']:
            self.set_passed(self.PASS)
        elif has_clean and not self.flags['EPEL5']:
            self.set_passed(self.PENDING,
                           'rm -rf %{buildroot} present but not required')
        elif not has_clean and self.flags['EPEL5']:
            self.set_passed(self.FAIL)
        else:
            self.set_passed(self.PASS)


class CheckDefattr(GenericMustCheckbase):
    '''
    MUST: Permissions on files must be set properly.  Executables
    should be set with executable permissions, for example.  Every
    %files section must include a %defattr(...) line.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions
    Update: 29-04-2011 This is only for pre rpm 4.4 that this is needed
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilePermissions'
        self.text = 'Each %files section contains %defattr if rpm < 4.4'
        self.automatic = True

    def run(self):
        has_defattr = False
        for pkg in self.spec.packages:
            if pkg.endswith('-debuginfo'):
                #auto-generated %defattr, ignore
                continue
            for line in self.spec.get_files(pkg):
                if line.startswith('%defattr('):
                    has_defattr = True
                    break
        if has_defattr and self.flags['EPEL5']:
            self.set_passed(self.PASS)
        elif has_defattr and not self.flags['EPEL5']:
            self.set_passed(self.PENDING,
                            '%defattr present but not needed')
        elif not has_defattr and self.flags['EPEL5']:
            self.set_passed(self.FAIL,
                            '%defattr missing, required by EPEL5')
        else:
            self.set_passed(self.PASS)


class CheckDescMacros(GenericMustCheckbase):
    ''' Macros is description etc. should be expandable. '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Source_RPM_Buildtime_Macros'
        self.text = 'Macros in Summary, %description expandable at' \
                    ' SRPM build time.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        bad_tags = []
        for pkg_name in self.spec.packages:
            if '%' in self.spec.expand_tag('Summary', pkg_name):
                bad_tags.append(pkg_name + ' (summary)')
            if '%' in self.spec.expand_tag('Description', pkg_name):
                bad_tags.append(pkg_name + ' (description)')
        if bad_tags:
            self.set_passed(self.PENDING,
                            'Macros in: ' + ', '.join(bad_tags))
        else:
            self.set_passed(self.PASS)


class CheckDesktopFile(GenericMustCheckbase):
    '''
    MUST: Packages containing GUI applications must include a
    %{name}.desktop file. If you feel that your packaged GUI
    application does not need a .desktop file, you must put a
    comment in the spec file with your explanation.
    http://fedoraproject.org/wiki/Packaging/Guidelines#desktop
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#desktop'
        self.text = 'Package contains desktop file if it is a GUI' \
                    ' application.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        have_desktop = self.rpms.find('*.desktop')
        self.set_passed(True if have_desktop else 'inconclusive')


class CheckDesktopFileInstall(GenericMustCheckbase):
    '''
    MUST: Packages containing GUI applications must include a
    %{name}.desktop file, and that file must be properly installed
    with desktop-file-install in the %install section.
    http://fedoraproject.org/wiki/Packaging/Guidelines#desktop
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#desktop'
        self.text = 'Package installs a  %{name}.desktop using' \
                    ' desktop-file-install' \
                    ' if there is such a file.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.rpms.find('*.desktop'):
            self.set_passed('not_applicable')
            return
        pattern = r'(desktop-file-install|desktop-file-validate)' \
                   '.*(desktop|SOURCE)'
        found = self.spec.find_re(re.compile(pattern))
        self.set_passed(self.PASS if found else self.FAIL)


class CheckDevelFilesInDevel(GenericMustCheckbase):
    '''
    MUST: Development files must be in a -devel package
    '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#DevelPackages'
        self.text = 'Development files must be in a -devel package'
        self.automatic = False
        self.type = 'MUST'


class CheckDirectoryRequire(GenericMustCheckbase):
    ''' Package should require directories it uses. '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package requires other packages for directories it uses.'
        self.automatic = False
        self.type = 'MUST'


class CheckDocRuntime(GenericMustCheckbase):
    '''
    MUST: If a package includes something as %doc, it must not affect
    the runtime of the application.  To summarize: If it is in %doc,
    the program must run properly if it is not present.
    http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#PackageDocumentation'
        self.text = 'Package uses nothing in %doc for runtime.'
        self.automatic = False
        self.type = 'MUST'


class CheckExcludeArch(GenericMustCheckbase):
    '''
    MUST: If the package does not successfully compile, build or work
    on an architecture, then those architectures should be listed in
    the spec in ExcludeArch.  Each architecture listed in ExcludeArch
    MUST have a bug filed in bugzilla, describing the reason that the
    package does not compile/build/work on that architecture.  The bug
    number MUST be placed in a comment, next to the corresponding
    ExcludeArch line.
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Architecture_Build_Failures'
        self.text = 'Package is not known to require ExcludeArch.'
        self.automatic = False
        self.type = 'MUST'


class CheckFileDuplicates(GenericMustCheckbase):
    '''
    MUST: A Fedora package must not list a file more than once in the
    spec file's %files listings.  (Notable exception: license texts in
    specific situations)
    http://fedoraproject.org/wiki/Packaging/Guidelines#DuplicateFiles
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#DuplicateFiles'
        self.text = 'Package does not contain duplicates in %files.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        filename = os.path.join(Mock.resultdir, 'build.log')
        try:
            stream = open(filename)
        except IOError:
            self.set_passed('inconclusive')
            return
        content = stream.read()
        stream.close()
        for line in content.split('\n'):
            if 'File listed twice' in line:
                self.set_passed(False, line)
                return
        self.set_passed(True)


class CheckFilePermissions(GenericMustCheckbase):
    '''
    MUST: Permissions on files must be set properly.  Executables
    should be set with executable permissions, for example. Every
    %files section must include a %defattr(...) line
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilePermissions'
        self.text = 'Permissions on files are set properly.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        for line in Mock.rpmlint_output:
            if 'non-standard-executable-perm' in line:
                self.set_passed(False, 'See rpmlint output')
                return
        self.set_passed(True)


class CheckFullVerReqSub(GenericMustCheckbase):
    '''
    MUST: In the vast majority of cases, devel packages must require the base
    package using a fully versioned dependency:
    Requires: %{name}%{?_isa} = %{version}-%{release}
    '''

    HDR = 'No Requires: %{name}%{?_isa} = %{version}-%{release} in '
    REGEX = r'Requires:\s*%{name}\s*=\s*%{version}-%{release}'

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#RequiringBasePackage'
        self.text = 'Fully versioned dependency in subpackages,' \
                    ' if present.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        bad_pkgs = []
        regex = re.compile(self.REGEX)
        for pkg in self.spec.packages:
            if not pkg.endswith('-devel'):
                continue
            requires = ' '.join(self.spec.get_requires(pkg))
            if not regex.search(requires):
                bad_pkgs.append(pkg)
        if bad_pkgs:
            self.set_passed(self.PENDING,
                            self.HDR + ' , '.join(bad_pkgs))
        else:
            self.set_passed(self.PASS)


class CheckGuidelines(GenericMustCheckbase):
    '''
    MUST: The package complies to the Packaging Guidelines.
    http://fedoraproject.org/wiki/Packaging:Guidelines
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package complies to the Packaging Guidelines'
        self.automatic = False
        self.type = 'MUST'


class CheckIllegalSpecTags(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Tags
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.text = 'Spec file lacks Packager, Vendor, PreReq tags.'
        self.automatic = True

    def run(self):
        passed = True
        output = ''
        for tag in ('Packager', 'Vendor', 'PreReq'):
            value = self.spec.expand_tag(tag)
            if value:
                passed = False
                output += 'Found : %s: %s\n' % (tag, value)
        if not passed:
            self.set_passed(passed, output)
        else:
            self.set_passed(passed)


class CheckLargeDocs(GenericMustCheckbase):
    '''
    MUST: Large documentation files must go in a -doc subpackage.
    (The definition of large is left up to the packager's best
    judgement, but is not restricted to size. Large can refer to
    either size or quantity).
    http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#PackageDocumentation'
        self.text = 'Large documentation files are in a -doc' \
                    ' subpackage, if required.'
        self.automatic = False
        self.type = 'MUST'


class CheckLicenseField(GenericMustCheckbase):

    '''
    MUST: The License field in the package spec file must match the
    actual license.
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/' \
                   'LicensingGuidelines#ValidLicenseShortNames'
        self.text = 'License field in the package spec file' \
                    ' matches the actual license.'
        self.automatic = True
        self.type = 'MUST'

    @staticmethod
    def _write_license(files_by_license, filename):
        ''' Dump files_by_license to filename. '''
        with open(filename, 'w') as f:
            for license_ in files_by_license.iterkeys():
                f.write('\n' + license_ + '\n')
                f.write('-' * len(license_) + '\n')
                for path in sorted(files_by_license[license_]):
                    f.write(path + '\n')

    @staticmethod
    def _get_source_dir():
        ''' Decide which directory to run licensecheck on. This can be
        either patched sources, or we use vanilla unpacked upstream
        tarballs if first option fails '''
        s = Mock.get_builddir('BUILD') + '/*'
        globs = glob(s)
        if globs and len(globs) > 0:
            msg = 'Checking patched sources after %prep for licenses.'
            source_dir = globs[0]
        else:
            msg = 'There is no build directory. Running licensecheck ' \
                   'on vanilla upstream sources.'
            source_dir = ReviewDirs.upstream_unpacked
        return (source_dir, msg)

    def run(self):

        def license_is_valid(_license):
            ''' Test that license from licencecheck is parsed OK. '''
            return not 'UNKNOWN'  in _license and \
                  not 'GENERATED' in _license

        def parse_licenses(raw_text):
            ''' Convert licensecheck output to files_by_license. '''
            files_by_license = {}
            raw_file = StringIO(raw_text)
            while True:
                line = raw_file.readline()
                if not line:
                    break
                try:
                    file_, license_ = line.split(':')
                except ValueError:
                    continue
                file_ = file_.strip()
                license_ = license_.strip()
                if not license_is_valid(license_):
                    license_ = 'Unknown or generated'
                if not license in files_by_license.iterkeys():
                    files_by_license[license_] = []
                files_by_license[license_].append(file_)
            return files_by_license

        try:
            source_dir, msg = self._get_source_dir()
            self.log.debug("Scanning sources in " + source_dir)
            licenses = []
            if os.path.exists(source_dir):
                cmd = 'licensecheck -r ' + source_dir
                out = check_output(cmd, shell=True)
                self.log.debug("Got license reply, length: %d" % len(out))
                licenses = parse_licenses(out)
                filename = os.path.join(ReviewDirs.root,
                                        'licensecheck.txt')
                self._write_license(licenses, filename)
            else:
                self.log.error('Source directory %s does not exist!' %
                                source_dir)
            if not licenses:
                msg += ' No licenses found.'
                msg += ' Please check the source files for licenses manually.'
                self.set_passed(False, msg)
            else:
                msg += ' Licenses found: "' \
                         + '", "'.join(licenses.iterkeys()) + '".'
                msg += ' %d files have unknown license.' % len(licenses)
                msg += ' Detailed output of licensecheck in ' + filename
                self.set_passed('inconclusive', msg)
        except OSError, e:
            self.log.error('OSError: %s' % str(e))
            msg = ' Programmer error: ' + e.strerror
            self.set_passed('inconclusive', msg)


class CheckLicensInDoc(GenericMustCheckbase):
    '''
    MUST: If (and only if) the source package includes the text of the
    license(s) in its own file, then that file, containing the text of
    the license(s) for the package must be included in %doc.
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text
    '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#License_Text'
        self.text = 'If (and only if) the source package includes' \
                    ' the text of the license(s) in its own file,' \
                    ' then that file, containing the text of the'  \
                    ' license(s) for the package is included in %doc.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        """ Check if there is a license file and if it is present in the
        %doc section.
        """

        licenses = []
        for potentialfile in ['COPYING', 'LICEN', 'copying', 'licen']:
            pattern = '*' + potentialfile + '*'
            licenses.extend(self.rpms.find_all(pattern))
        licenses = filter(lambda l: not self.rpms.find(l + '/*'),
                          licenses)
        licenses = map(lambda f: f.split('/')[-1], licenses)
        if licenses == []:
            self.set_passed('inconclusive')
            return

        docs = []
        for pkg in self.spec.packages:
            rpm_path = Mock.get_package_rpm_path(pkg, self.spec)
            cmd = 'rpm -qldp ' + rpm_path
            doclist = check_output(cmd.split())
            docs.extend(doclist.split())
        docs = map(lambda f: f.split('/')[-1], docs)

        for _license in licenses:
            if not _license in docs:
                self.log.debug("Cannot find " + _license +
                               " in doclist")
                self.set_passed(False,
                                "Cannot find %s in rpm(s)" % _license)
                return
        self.set_passed(True)


class CheckLicenseInSubpackages(GenericMustCheckbase):
    ''' License should always be installed when subpackages.'''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#Subpackage_Licensing'
        self.text = 'License file installed when any subpackage' \
                    ' combination is installed.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        '''Check if subpackages exists'''
        return len(self.spec.packages) > 1


class CheckLocale(GenericMustCheckbase):
    '''
    MUST: The spec file MUST handle locales properly.  This is done by
    using the %find_lang macro. Using %{_datadir}/locale/* is strictly
    forbidden.
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Handling_Locale_Files'
        self.text = 'The spec file handles locales properly.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        return self.rpms.find('/usr/share/locale/*/LC_MESSAGES/*.mo')


class CheckMacros(GenericMustCheckbase):
    '''
    MUST: Each package must consistently use macros.
    http://fedoraproject.org/wiki/Packaging/Guidelines#macros
    http://fedoraproject.org/wiki/Packaging:RPMMacros
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/' \
                   'wiki/Packaging/Guidelines#macros'
        self.text = 'Package consistently uses macro' \
                    ' is (instead of hard-coded directory names).'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        br_tag1 = self.spec.find_all_re('.*%{buildroot}.*', True)
        br_tag2 = self.spec.find_all_re('.*\$RPM_BUILD_ROOT.*', True)
        if br_tag1 and br_tag2:
            self.set_passed(False,
                            'Using both %{buildroot} and $RPM_BUILD_ROOT')
        else:
            self.set_passed('inconclusive')


class CheckMakeinstall(GenericMustCheckbase):
    ''' Thou shall not use %makeinstall. '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#Why_the_.25makeinstall_macro_should_not_be_used'
        self.text = "Package use %makeinstall only when make install' \
                    ' DESTDIR=... doesn't work."
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        regex = re.compile(r'^(%makeinstall.*)')
        res = self.spec.find_re(regex)
        if res:
            self.set_passed(False, res.group(0))
            return True
        else:
            return False


class CheckMultipleLicenses(GenericMustCheckbase):
    ''' If multiple licenses, we should provide a break-down. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#Multiple_Licensing_Scenarios'
        self.text = 'If the package is under multiple licenses, the licensing'\
                    ' breakdown must be documented in the spec.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        license_ = self.spec.expand_tag('License').lower().split()
        return 'and' in license_ or 'or' in license_


class CheckNameCharset(GenericMustCheckbase):
    '''
    MUST:all Fedora packages must be named using only the following
         ASCII characters...
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/NamingGuidelines'
        self.text = 'Package is named using only allowed ASCII characters.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        allowed_chars = 'abcdefghijklmnopqrstuvwxyz' \
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._+'
        output = ''
        passed = True
        for char in self.spec.name:
            if not char in allowed_chars:
                output += '^'
                passed = False
            else:
                output += ' '
        if passed:
            self.set_passed(passed)
        else:
            self.set_passed(passed, '%s\n%s' % (self.spec.name, output))


class CheckNaming(GenericMustCheckbase):
    '''
    MUST: The package must be named according to the Package Naming
    Guidelines.
    http://fedoraproject.org/wiki/Packaging/NamingGuidelines
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/NamingGuidelines'
        self.text = 'Package is named according to the Package Naming' \
                    ' Guidelines.'
        self.automatic = False
        self.type = 'MUST'


class CheckNoConfigInUsr(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Configuration_files'
        self.text = 'No %config files under /usr.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if line.startswith('%config'):
                    return True
        return False

    def run_on_applicable(self):
        passed = True
        extra = ''
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if line.startswith('%config'):
                    l = line.replace("%config", "")
                    l = l.replace("(noreplace)", "").strip()
                    if l.startswith('/usr'):
                        passed = False
                        extra += line

        self.set_passed(passed, extra)


class CheckNoConflicts(GenericMustCheckbase):
    '''
    Whenever possible, Fedora packages should avoid conflicting
    with each other
    http://fedoraproject.org/wiki/Packaging/Guidelines#Conflicts
    http://fedoraproject.org/wiki/Packaging:Conflicts
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/' \
                   'wiki/Packaging/Guidelines#Conflicts'
        self.text = 'Package does not generate any conflict.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if self.spec.expand_tag('Conflicts'):
            self.set_passed(False,
                            'Package contains Conflicts: tag(s)'
                            ' needing fix or justification.')
        else:
            self.set_passed('inconclusive',
                            'Package contains no Conflicts: tag(s)')


class CheckObeysFHS(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Filesystem_Layout
    http://www.pathname.com/fhs/
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Filesystem_Layout'
        self.text = 'Package obeys FHS, except libexecdir and /usr/target.'
        self.automatic = False
        self.type = 'MUST'


class CheckObsoletesForRename(GenericMustCheckbase):
    ''' If package is a rename, we should provide Obsoletes: etc. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines' \
                   'Renaming.2FReplacing_Existing_Packages'
        self.text = 'If the package is a rename of another package, proper' \
                    ' Obsoletes and Provides are present.'
        self.automatic = False
        self.type = 'MUST'


class CheckOwnDirs(GenericMustCheckbase):
    '''
    MUST: A package must own all directories that it creates.  If it
    does not create a directory that it uses, then it should require a
    package which does create that directory.
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package must own all directories that it creates.'
        self.automatic = False
        self.type = 'MUST'


class CheckOwnOther(GenericMustCheckbase):
    '''
    MUST: Packages must not own files or directories already owned by
    other packages.  The rule of thumb here is that the first package
    to be installed should own the files or directories that other
    packages may rely upon.  This means, for example, that no package
    in Fedora should ever share ownership with any of the files or
    directories owned by the filesystem or man package.  If you feel
    that you have a good reason to own a file or directory that
    another package owns, then please present that at package review
    time.
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package does not own files or directories' \
                    ' owned by other packages.'
        self.automatic = False
        self.type = 'MUST'


class CheckRelocatable(GenericMustCheckbase):
    '''
    MUST: If the package is designed to be relocatable,
    the packager must state this fact in the request for review,
    along with the rationalization for relocation of that specific package.
    Without this, use of Prefix: /usr is considered a blocker.
    http://fedoraproject.org/wiki/Packaging/Guidelines#RelocatablePackages
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#RelocatablePackages'
        self.text = 'Package is not relocatable.'
        self.automatic = False
        self.type = 'MUST'

    def run_on_applicable(self):
        if self.spec.find_re('^Prefix:'):
            self.set_passed(self.FAIL, 'Package has a "Prefix:" tag')
        else:
            self.set_passed(self.PASS)


class CheckReqPkgConfig(GenericMustCheckbase):
    '''
    rpm in EPEL5 and below does not automatically create dependencies
    for pkgconfig files.  Packages containing pkgconfig(.pc) files
    must Requires: pkgconfig (for directory ownership and usability).
    http://fedoraproject.org/wiki/EPEL/GuidelinesAndPolicies#EL5
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'EPEL/GuidelinesAndPolicies#EL5'
        self.text = 'EPEL5: Package requires pkgconfig, if .pc files' \
                    ' are present.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.rpms.find('*.pc') or not self.flags['EPEL5']:
            self.set_passed('not_applicable')
            return
        result = self.FAIL
        for line in self.spec.get_requires():
            if 'pkgconfig' in line:
                result = self.PASS
                break
        self.set_passed(result)


class CheckRequires(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Requires
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Requires'
        self.text = 'Requires correct, justified where necessary.'
        self.automatic = False
        self.type = 'MUST'


class CheckSourceMD5(GenericMustCheckbase):
    '''
    MUST: The sources used to build the package must match the
    upstream source, as provided in the spec URL. Reviewers should use
    md5sum for this task.  If no upstream URL can be specified for
    this package, please see the Source URL Guidelines for how to deal
    with this.
    http://fedoraproject.org/wiki/Packaging/SourceURL
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'Sources used to build the package match the' \
                    ' upstream source, as provided in the spec URL.'
        self.automatic = True

    def make_diff(self, sources):
        """
        For all sources, run a diff -r between upstream and what's in the
        srpm. Return (passed, text) where passed is True/False
        and text is either the possibly large diff output or None
        """
        for s in sources:
            s.extract()
            upstream = s.extract_dir
            local = self.srpm.extract(s.filename)
            if not local:
                self.log.warn(
                    "Cannot extract local source: " + s.filename)
                return(False, None)
            cmd = '/usr/bin/diff -U2 -r %s %s' % (upstream, local)
            self.log.debug(' Diff cmd: ' + cmd)
            try:
                p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
                output = p.communicate()[0]
            except OSError:
                self.log.error("Cannot run diff", exc_info=True)
                return (False, None)
            if output and len(output) > 0:
                return (False, output)
        return (True, None)

    def check_checksums(self, sources):
        ''' For all sources, compare checksum with upstream. '''
        text = ''
        all_sources_passed = True
        for source in sources:
            if source.local:
                self.log.debug('Skipping md5-test for '
                                + source.filename)
                continue
            if source.local_src:
                text += "Using local file " + source.local_src + \
                        " as upstream\n"
            local = self.srpm.check_source_checksum(source.filename)
            upstream = source.check_source_checksum()
            text += source.url + ' :\n'
            text += '  CHECKSUM({0}) this package     : {1}\n'.\
                    format(Settings.checksum.upper(), local)
            text += '  CHECKSUM({0}) upstream package : {1}\n'.\
                    format(Settings.checksum.upper(), upstream)
            if local != upstream:
                all_sources_passed = False
        return (all_sources_passed, text)

    def run(self):
        sources = self.sources.get_all()
        if sources == []:
            self.log.debug('No testable sources')
            self.set_passed(self.PENDING, 'Package has no sources or they'
                            ' are generated by developer')
            return
        msg = 'Check did not complete'
        passed = True
        text = ''
        try:
            passed, text = self.check_checksums(self.sources.get_all())
            if not passed:
                passed, diff = self.make_diff(self.sources.get_all())
                if passed:
                    text += 'However, diff -r shows no differences\n'
                    msg = 'checksum differs but diff -r is OK'
                elif not diff:
                    msg += 'checksum differs and there are problems '\
                           'running diff. Please verify manually.\n'
                else:
                    p = os.path.join(ReviewDirs.root, 'diff.txt')
                    with open(p, 'w') as f:
                        f.write(diff)
                    text += 'diff -r also reports differences\n'
                    msg = 'Upstream MD5sum check error, diff is in ' + p
        except AttributeError as e:
            self.log.debug("CheckSourceMD5(): Attribute error " + str(e),
                           exc_info=True)
            msg = 'Internal Error!'
            passed = False
        finally:
            if passed:
                msg = None
            if text:
                attachments = [
                    self.Attachment('MD5-sum check', text, 10)]
            else:
                attachments = []
            self.set_passed(passed, msg, attachments)


class CheckSpecLegibility(GenericMustCheckbase):
    '''
    MUST: The spec file must be written in American English
    http://fedoraproject.org/wiki/Packaging/Guidelines#summary

    MUST: The spec file for the package MUST be legible.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Spec_Legibility
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Spec_Legibility'
        self.text = 'Spec file is legible and written in American English.'
        self.automatic = False
        self.type = 'MUST'


class CheckSpecName(GenericMustCheckbase):
    '''
    MUST: The spec file name must match the base package %{name},
    in the format %{name}.spec unless your package has an exemption.
    http://fedoraproject.org/wiki/Packaging/NamingGuidelines#Spec_file_name
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                    'Packaging/NamingGuidelines#Spec_file_name'
        self.text = 'Spec file name must match the spec package' \
                    ' %{name}, in the format %{name}.spec.'
        self.automatic = True

    def run(self):
        spec_name = '%s.spec' % self.spec.name
        if os.path.basename(self.spec.filename) == spec_name:
            self.set_passed(True)
        else:
            self.set_passed(False, '%s should be %s ' %
                (os.path.basename(self.spec.filename), spec_name))


class CheckSystemdScripts(GenericMustCheckbase):
    '''
    http://fedoraproject.org/wiki/Packaging:Systemd
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains  systemd file(s) if in need.'
        self.automatic = False
        self.type = 'MUST'


class CheckUTF8Filenames(GenericMustCheckbase):
    '''
    MUST: All filenames in rpm packages must be valid UTF-8.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilenameEncoding
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilenameEncoding'
        self.text = 'File names are valid UTF-8.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        for line in Mock.rpmlint_output:
            if 'wrong-file-end-of-line-encoding' in line or \
            'file-not-utf8' in line:
                self.set_passed(False)
        self.set_passed(True)


class CheckUsefulDebuginfo(GenericMustCheckbase):
    '''
    Packages should produce useful -debuginfo packages, or explicitly
    disable them when it is not possible to generate a useful one but
    rpmbuild would do it anyway.  Whenever a -debuginfo package is
    explicitly disabled, an explanation why it was done is required in
    the specfile.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Debuginfo_packages
    http://fedoraproject.org/wiki/Packaging:Debuginfo
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Debuginfo_packages'
        self.text = 'Useful -debuginfo package or justification' \
                    ' otherwise.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        for path in Mock.get_package_rpm_paths(self.spec):
            if not path.endswith('noarch.rpm'):
                return True
        return False


class CheckNoNameConflict(GenericMustCheckbase):
    '''
    Check that there isn't already a package with this name.
    '''
    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = "https://fedoraproject.org/wiki/Packaging/" \
                   "NamingGuidelines#Conflicting_Package_Names"
        self.text = 'Package do not use a name that already exist'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        import fedora.client
        import pycurl
        p = fedora.client.PackageDB()
        name = self.spec.name.lower()
        try:
            p.get_package_info(name)
            self.set_passed(
                     self.FAIL,
                    'A package already exist with this name, please check'
                        ' https://admin.fedoraproject.org/pkgdb/acls/name/'
                        + name)
        except fedora.client.AppError:
            self.set_passed(self.PASS)
        except pycurl.error:
            self.set_passed(self.PENDING,
                            "Couldn't connect to PackageDB, check manually")


class CheckSourcedirMacroUse(GenericMustCheckbase):
    ''' Check for usage of %_sourcedir macro. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines' \
                   '#Improper_use_of_.25_sourcedir'
        self.text = 'Only use %_sourcedir in very specific situations.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        text = ''.join(self.spec.lines)
        if '%_sourcedir' in text or '$RPM_SOURCE_DIR' in text or \
        '%{_sourcedir}' in text:
            self.set_passed(self.PENDING,
                            '%_sourcedir/$RPM_SOURCE_DIR is used.')
        else:
            self.set_passed(self.NA)


class CheckUpdateIconCache(GenericMustCheckbase):
    ''' Check that gtk-update-icon-cache is run if required. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#Icon_Cache'
        self.text = 'gtk-update-icon-cache is invoked when required'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('/usr/share/icons/*', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('gtk-update-icon-cache',
                                [rpm_pkg.postun, rpm_pkg.posttrans]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "icons in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckUpdateDesktopDatabase(GenericMustCheckbase):
    ''' Check that update-desktop-database is run if required. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#Icon_Cache'
        self.text = 'update-desktop-database is invoked when required'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        install = self.spec.get_section('%install', raw=True)
        for pkg in self.spec.packages:
            if self.rpms.find('*.desktop', pkg):
                using.append(pkg)
                if not 'update-desktop-database' in install and \
                not 'desktop-file-validate' in install:
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "desktop file(s) in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGioQueryModules(GenericMustCheckbase):
    ''' Check that update-desktop-database is run if required. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GIO_modules'
        self.text = 'gio-querymodules is invoked as required'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        libdir = Mock.rpm_eval('%{_libdir}')
        gio_pattern = os.path.join(libdir, 'gio/modules/', '*')
        for pkg in self.spec.packages:
            if self.rpms.find(gio_pattern, pkg):
                using.append(pkg)
                rpmpkg = self.rpms.get(pkg)
                if not in_list('gio-querymodules',
                                [rpmpkg.post, rpmpkg.postun]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "gio module file(s) in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGtkQueryModules(GenericMustCheckbase):
    ''' Check that gtk-query-immodules is run if required. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GIO_modules'
        self.text = 'gtk-query-immodules is invoked when required'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        libdir = Mock.rpm_eval('%{_libdir}')
        pattern = os.path.join(libdir, 'gtk-3.0/', '*')
        for pkg in self.spec.packages:
            if self.rpms.find(pattern, pkg):
                using.append(pkg)
                rpmpkg = self.rpms.get(pkg)
                if not in_list('gtk-query-immodules',
                                [rpmpkg.postun, rpmpkg.posttrans]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "Gtk module file(s) in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGlibCompileSchemas(GenericMustCheckbase):
    ''' Check that glib-compile-schemas is run if required. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GSettings_Schema'
        self.text = 'glib-compile-schemas is run if required'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('*.gschema.xml', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('glib-compile-schemas',
                                [rpm_pkg.postun, rpm_pkg.posttrans]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = 'gschema file(s) in ' + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGconfSchemaInstall(GenericMustCheckbase):
    ''' Check that gconf schemas are properly installed. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GConf'
        self.text = 'GConf schemas are properly installed'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('/etc/gconf/schemas/*.schemas', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('%gconf_schema',
                                [rpm_pkg.post, rpm_pkg.pre]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = 'gconf file(s) in ' + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckInfoInstall(GenericMustCheckbase):
    ''' Check that info files are properly installed. '''

    def __init__(self, base):
        GenericMustCheckbase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#Texinfo'
        self.text = 'Texinfo files are properly installed'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('/usr/share/info/*', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('install-info',
                                [rpm_pkg.post, rpm_pkg.preun]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = 'Texinfo .info file(s) in ' + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)



#
# vim: set expandtab: ts=4:sw=4: