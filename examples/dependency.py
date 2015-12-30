#!/usr/bin/python

from application.dependency import ApplicationDependencies, PackageDependency, DependencyError
from application import log


# helper function to display results
def dependency_list(dependencies):
    return ', '.join("%s>=%s" % (dep.name, dep.required_version) for dep in dependencies.dependencies)

# Use case for packages that have a package.__version__ string attribute with
# the version number and for which the dist name and the package name are the
# same or the dist name is the package name prefixed with 'python-'. This is
# the case with python-application which has application.__version__. This is
# also the case with twisted which has twisted.__version__

log.msg("")
log.msg("The following dependency check will succeed:")

package_requirements = {'python-application': '1.1.4'}

dependencies = ApplicationDependencies(**package_requirements)
try:
    dependencies.check()
except DependencyError, e:
    log.fatal(str(e))
else:
    log.msg("%s satisfied" % dependency_list(dependencies))

log.msg("")
log.msg("The following dependency check will succeed if twisted>=2.5.0 is installed:")

package_requirements = {'python-application': '1.1.4',
                        'twisted': '2.5.0'}

dependencies = ApplicationDependencies(**package_requirements)
try:
    dependencies.check()
except DependencyError, e:
    log.fatal(str(e))
else:
    log.msg("%s satisfied" % dependency_list(dependencies))


# Use case for packages that have a string version defined but it's either in
# a different place or the dist name doesn't match the package name. This is
# the case with dnspython which satisfies both conditions. The dist name
# (dnspython) and the package name (dns) are not the same, not is the dist
# name derived from the python package name by prefixing 'python-'. Also the
# version is available from 'dns.version.version'

log.msg("")
log.msg("The following dependency check will succeed if dns-python>=1.6.0 is installed:")

dns_dependency = PackageDependency('dnspython', '1.6.0', 'dns.version.version')
dependencies = ApplicationDependencies(dns_dependency)
try:
    dependencies.check()
except DependencyError, e:
    log.fatal(str(e))
else:
    log.msg("%s satisfied" % dependency_list(dependencies))


# Use case for packages that have a custom version attribute that is not a
# string or is differently formatted than a version number. We can again use
# twisted, which in addition to twisted.__version__ which is a string as seen
# above it also has a twisted.version object which is an instance of
# twisted.version.Version. For the sake of this example let's assume that
# twisted.__version__ is unavailable and we have to use twisted.version.

class TwistedDependency(PackageDependency):
    def __init__(self, required_version):
        PackageDependency.__init__(self, 'twisted', required_version, 'twisted.version')

    def format_version(self, package_version):
        # we overwrite this method that allows us to take the Version instance
        # that twisted.version provides and format it as a string that we can
        # check using ApplicationDependencies.
        if package_version == 'undefined':
            return package_version
        else:
            return package_version.short()

log.msg("")
log.msg("The following dependency check will succeed if twisted>=2.5.0 is installed:")

dependencies = ApplicationDependencies(TwistedDependency('2.5.0'))
try:
    dependencies.check()
except DependencyError, e:
    log.fatal(str(e))
else:
    log.msg("%s satisfied" % dependency_list(dependencies))


# The following example will combine all above elements to show how we can
# pass complex arguments to ApplicationDependencies

log.msg("")
log.msg("The following dependency check will fail:")

package_requirements = {'python-application': '1.1.4',
                        'foobar': '7.0.0'}
package_dependencies = [PackageDependency('dnspython', '1.6.0', 'dns.version.version'),
                        TwistedDependency('2.5.0')]

dependencies = ApplicationDependencies(*package_dependencies, **package_requirements)
try:
    dependencies.check()
except DependencyError, e:
    log.fatal(str(e))
else:
    log.msg("%s satisfied" % dependency_list(dependencies))

log.msg("")

