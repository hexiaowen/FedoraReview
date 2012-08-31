#!/usr/bin/python -tt
#-*- coding: utf-8 -*-
#
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
'''
Tools for helping Fedora package reviewers
'''

import sys
import os.path

from FedoraReview import BugException, BugzillaBug, Checks, \
          ChecksLister, CleanExitError, FedoraReviewError, \
          NameBug, ReviewDirs, ResultDirNotEmptyError, \
          ReviewDirExistsError, Settings, SettingsError, UrlBug

from FedoraReview import __version__, build_full


class ConfigError(FedoraReviewError):
    def __init__(self, what):
        FedoraReviewError.__init__(self, 'Configuration error: ' + what)


class HandledError(FedoraReviewError):
    def __init__(self, msg='Errors encountered, goodbye'):
        FedoraReviewError.__init__(self, msg)


class ReviewHelper(object):

    def __init__(self):
        self.bug = None
        self.checks = None
        self.log = Settings.get_logger()
        self.verbose = False
        self.outfile = None
        self.prebuilt = False

    def __download_sources(self):
        #self.sources = Sources(self.checks.spec)
        self.sources.extract_all()
        return True

    def __do_report(self):
        ''' Create a review report'''
        self.log.info('Getting .spec and .srpm Urls from : '
                       + self.bug.get_location())

        Settings.dump()
        if not self.bug.find_urls():
            self.log.error( 'Cannot find .spec or .srpm URL(s)')
            raise HandledError()

        if not ReviewDirs.is_inited:
            wd = self.bug.get_dirname()
            ReviewDirs.workdir_setup(wd)

        if not self.bug.download_files():
            self.log.error('Cannot download .spec and .srpm')
            raise HandledError()

        Settings.name = self.bug.get_name()
        self.__run_checks(self.bug.spec_file, self.bug.srpm_file)

    def __list_checks(self):
        """ List all the checks available.
        """

        def check_match(check):
           return check.group == group and check.defined_in == f

        checks_list = list(ChecksLister().get_checks().itervalues())
        files = list(set([c.defined_in for c in checks_list]))
        for f in sorted(files):
            print 'File:  ' + f
            files_per_src = filter(lambda c: c.defined_in == f,
                                   checks_list)
            groups = list(set([c.group for c in files_per_src]))
            for group in sorted(groups):
                checks = filter(check_match, checks_list)
                if checks == []:
                    continue
                print 'Group: ' + group
                for c in sorted(checks):
                      print '    ' + c.name
        deps_list = filter(lambda c: c.needs != [] and
                               c.needs != ['CheckBuildCompleted'],
                           checks_list)
        for dep in deps_list:
            print'Dependencies: ' +  dep.name + ': ' + \
                os.path.basename(dep.defined_in)
            for needed in dep.needs:
                print '     ' + needed
        deprecators =  filter(lambda c: c.deprecates != [], checks_list)
        for dep in deprecators:
            print 'Deprecations: ' + dep.name + ': ' + \
                os.path.basename(dep.defined_in)
            for victim in dep.deprecates:
                print '    ' + victim

    def __print_version(self):
        print('fedora-review version ' + __version__ + ' ' + build_full)

    def __run_checks(self, spec, srpm):
        self.checks = Checks(spec, srpm )
        if Settings.no_report:
            self.outfile = '/dev/null'
        else:
            self.outfile = ReviewDirs.report_path(self.checks.spec.name)
        with open(self.outfile,"w") as output:
            if Settings.nobuild:
                self.checks.srpm.is_build = True
            self.log.info('Running checks and generate report\n')
            self.checks.run_checks(output=output,
                                   writedown=not Settings.no_report)
            output.close()
        if not Settings.no_report:
            print "Review in: " + self.outfile

    def run(self):
        self.log.debug( "Command  line: " + ' '.join(sys.argv))
        try:
            Settings.init()
            make_report = True
            if Settings.list_checks:
                self.__list_checks()
                make_report = False
            elif Settings.version:
                self.__print_version()
                make_report = False
            elif Settings.url:
                self.log.info("Processing bug on url: " + Settings.url )
                self.bug = UrlBug(Settings.url)
            elif Settings.bug:
                self.log.info("Processing bugzilla bug: " + Settings.bug )
                self.bug = BugzillaBug(Settings.bug, user=Settings.user)
            elif Settings.name:
                self.log.info("Processing local files: " + Settings.name )
                self.bug = NameBug(Settings.name)
            if make_report:
                self.__do_report()
            return 0
        except BugException as err:
            print str(err)
            return 2
        except HandledError as err:
            print str(err)
            return 2
        except SettingsError as err:
            self.log.error("Incompatible settings: " + str(err))
            return 2
        except ReviewDirExistsError as err:
            print("The directory %s is in the way, please remove." %
                  err.value)
            return 4
        except ResultDirNotEmptyError:
            print("The resultdir is not empty, I cannot handle this.")
            return 4
        except CleanExitError as err:
            self.log.debug('Processing CleanExit')
            return 2
        except:
            self.log.debug("Exception down the road...", exc_info=True)
            self.log.error('Exception down the road...'
                           '(logs in ~/.cache/fedora-review.log)')
            return 1
        return 0


if __name__ == "__main__":
    review = ReviewHelper()
    review.run()

# vim: set expandtab: ts=4:sw=4:
