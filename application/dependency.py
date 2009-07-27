# Copyright (C) 2009 Dan Pascu. See LICENSE for details.
#

"""Manage application dependencies at runtime"""


__all__ = ['ApplicationDependencies', 'PackageDependency', 'DependencyError']


class DependencyError(Exception): pass


class PackageDependency(object):
    """Describe a package dependency"""
    def __init__(self, name, required_version, version_attribute=None):
        """
        Take a package name, minimum required version and an optional
        version attribute to describe a package dependency. If the
        version_attribute argument is specified, it must be a string
        containing the path inside the package to a string attribute
        containing the package version. If not specified it defaults
        to 'package.__version__' where package is derived from name
        by stripping the 'python-' prefix if present.
        """
        if version_attribute is None:
            if name.startswith('python-'):
                module_name = name[7:]
            else:
                module_name = name
            version_attribute = '__version__'
        else:
            module_name, version_attribute = version_attribute.rsplit('.', 1)
        try:
            #Starting with python2.5 import can be expressed better like below. Replace it when we drop support for 2.4 -Dan
            #module = __import__(module_name, fromlist=module_name.rsplit('.', 1)[1:], level=0)
            module = __import__(module_name, {}, {}, module_name.rsplit('.', 1)[1:])
        except ImportError:
            version = None
        else:
            version = self.format_version(getattr(module, version_attribute, 'undefined'))
        self.name = name
        self.required_version = required_version
        self.installed_version = version

    def format_version(self, package_version):
        """Convert the version attribute value into a version string"""
        return package_version


class ApplicationDependencies(object):
    """Describe a collection of package dependencies for an application"""
    def __init__(self, *args, **kw):
        """
        Take PackageDependency instances as positional arguments and/or
        package_name='required_version' keyword arguments to create a
        collection of package dependencies
        """
        self.dependencies = [x for x in args if isinstance(x, PackageDependency)]
        if len(self.dependencies) != len(args):
            raise TypeError("positional arguments must be instances of PackageDependency")
        self.dependencies.extend((PackageDependency(name, version) for name, version in sorted(kw.iteritems())))

    def check(self):
        """Raise DependencyError if the dependencies are not satisfied"""
        from application.version import Version
        for dep in self.dependencies:
            if dep.installed_version is None:
                raise DependencyError("need %s version %s or higer but it's not installed" % (dep.name, dep.required_version))
            if Version.parse(dep.installed_version) < Version.parse(dep.required_version):
                raise DependencyError("need %s version %s or higer but only %s is installed" % (dep.name, dep.required_version, dep.installed_version))

