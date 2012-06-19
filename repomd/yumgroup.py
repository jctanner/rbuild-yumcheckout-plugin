class yumGroup(object):
    def __init__(self, id):
        self.id = id        #string, not an int
        self.packages = []  #list of packages

    #add a single package
    def addpackage(self, package):
        self.packages.append(package)

    #add a list of packages
    def addpackages(self, packages):
        self.packages.append(list(packages))

