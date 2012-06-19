from linkparser import *
from yumpackage import *
from yumgroup import *


import urllib2
from urllib2 import urlopen
import re

from xml.dom.minidom import parse, parseString

import StringIO
import gzip

class yumRepo(object):
    def __init__(self, url):
        #self.id = id
        self.url = url
        self.repodataurl = ""
        self.metafiles = []
        self.primarymetafiles = []
        self.groupmetafiles = []
        self.packages = []
        self.groups = []

        #generated
        self.uniquepackages = []
        self.latestpackages = []
        self.upstreamtroves = []
        self.localtroves = []
        self.missingtroves = []

        #self.getUrl()
        self.findMetaFiles()
        self.parseRepomd()
        self.parsePrimaryXML()
        self.parseCompsXML()

    def getUrl(self):
        print self.url

    def addPackage(self, package):
        print "INFO: adding %s" % package.name
        self.packages.append(package)

    def listPackages(self):
        for pkg in self.packages:
            print "%s-%s-%s-%s.rpm" % (pkg.name, pkg.version, pkg.release, pkg.arch)


    def uniquepPackages(self):
        pass

    def findLatestPackageVer(self, pkgname, arch):
        latestpkg = yumPackage(pkgname, '0', '0', '0', '0', '', '')
        for pkg in self.packages:
            if (pkg.name == pkgname) and (pkg.arch == arch):
                if (pkg.version > latestpkg.version):
                    if (pkg.release >= latestpkg.release):
                        if (pkg.epoch >= latestpkg.epoch):
                            latestpkg.version = pkg.version
                            latestpkg.release = pkg.release
                            latestpkg.epoch = pkg.epoch
                            latestpkg.arch = pkg.arch
                            latestpkg.repourl = pkg.repourl
                            latestpkg.url = pkg.url
                            print "INFO:    %s is latest for %s " % (latestpkg.url, self.url)
                            #epdb.st()
                else:
                    #epdb.st()
                    print "INFO:    %s !> %s" % (pkg.url, latestpkg.url)
        return latestpkg

    def addGroup(self, group):
        self.groups.append(group)

    def parseRepomd(self):
        for filename in self.metafiles:
            if re.search('repomd', filename):
                print "INFO: repomd file = %s" % filename
                # get repomd
                #import epdb; epdb.st()
                compdom = parse(urlopen(self.repodataurl + "/" + filename))
                for node in compdom.getElementsByTagName('data'):
                    nodetype = node.attributes['type'].value
                    #from conary.lib import epdb; epdb.st()
                    #method 1
                    #nodelocation = node.childNodes[1].attributes['href'].value
                    #method 2
                    nodelocation = node.getElementsByTagName('location')[0].attributes['href'].nodeValue

                    print "INFO: xmlurl -- %s %s" % (nodetype, nodelocation)

                    if nodetype.encode('utf8') in "primary":
                        print "INFO: add %s as primary" % nodelocation
                        self.primarymetafiles.append(nodelocation.encode('utf8'))
                    if nodetype.encode('utf8') in "group":
                        print "INFO: add %s as comps" % nodelocation
                        self.groupmetafiles.append(nodelocation.encode('utf8'))

                # get primary filename
                # get comps filename

        #import epdb; epdb.st()

    def findMetaFiles(self):
        #epdb.st()
        repourl = self.url + "/repodata"
        #epdb.st()
        print "INFO: attemping to parse %s" % repourl
        req = urllib2.Request(repourl)
        response = urllib2.urlopen(req)

        if response.code is "200":
            print "ERROR: repository does not have a repodata directory"
            return
        self.repodataurl = repourl

        data = response.read()
        parser = linkParser()
        parser.parse(data)
        for filename in parser.get_hyperlinks():
            #print filename
            if re.search('xml', filename):
                print "INFO: add %s to metafiles" % filename
                self.metafiles.append(filename)

        # HTML != XML ... can't use parse
        #compdom = parse(urlopen(repourl)) 
        #compdom = parse(response.read())

        #import epdb; epdb.st()

    def parsePrimaryXML(self):
        print "INFO: parsing primary.xml"
        for filename in self.primarymetafiles:
            #import epdb; epdb.st()
            if filename.endswith('.gz'):
                print "INFO: %s is compressed, retrieving %s " % (filename, (self.url + "/" + filename))
                resp = urlopen(self.url + "/" + filename)
                output = StringIO.StringIO()
                output.write(resp.read())
                output.seek(0)
                decompressed = gzip.GzipFile(fileobj=output)
                #xml = decompressed.read()
                #compdom = parse(decompressed.read())
                #compdom = parse(xml)
                compdom = parse(decompressed)
                for node in compdom.getElementsByTagName('package'):
                    #epdb.st()

                    pkgname = node.getElementsByTagName('name')[0].childNodes[0].nodeValue.encode('utf8')
                    pkgarch = node.getElementsByTagName('arch')[0].childNodes[0].nodeValue.encode('utf8')
                    pkgepoch = node.getElementsByTagName('version')[0].attributes['epoch'].value.encode('utf8')
                    pkgvers = node.getElementsByTagName('version')[0].attributes['ver'].value.encode('utf8')
                    pkgrel = node.getElementsByTagName('version')[0].attributes['rel'].value.encode('utf8')
                    pkgloc = node.getElementsByTagName('location')[0].attributes['href'].value.encode('utf8')
                    pkgsumtype = node.getElementsByTagName('checksum')[0].attributes['type'].value.encode('utf8')
                    pkgsum = node.getElementsByTagName('checksum')[0].childNodes[0].nodeValue.encode('utf8')
                    try:
                        pkgpackager = node.getElementsByTagName('packager')[0].childNodes[0].nodeValue.encode('utf8')
                    except:
                        pkgpackager = 'none'

                    #from conary.lib import epdb; epdb.st()

                    # name, epoch, version, release, arch, location
                    package = yumPackage(pkgname, pkgepoch, pkgvers, pkgrel, pkgarch, pkgloc, self.url)
                    package.sumtype = pkgsumtype
                    package.sum = pkgsum
                    package.packager = pkgpackager
                    self.addPackage(package)
            else:
                print "INFO: %s is not compressed" % filename

    def parseCompsXML(self):
        """
        missingpackages = ['bsh-groupfile',
                           'ctdb',
                           'ctdb-devel',
                           'ecs-groupfile',
                           'kernel-debug',
                           'kernel-debug-devel',
                           'kernel-xen',
                           'kernel-xen-devel',
                           'kmod-be2iscsi-xen-rhel5u5',
                           'kmod-be2net-xen-rhel5u5',
                           'kmod-cmirror',
                           'kmod-cmirror-xen',
                           'kmod-gfs kmod-gfs-xen',
                           'kmod-gnbd kmod-gnbd-xen',
                           'kmod-igb-xen-rhel5u5',
                           'kmod-lpfc-xen-rhel5u5',
                           'serviceguard',
                           'sgcmom',
                           'vmware-open-vm-tools-common',
                           'vmware-open-vm-tools-nox',
                           'kmod-gfs',
                           'kmod-gfs-xen',
                           'kmod-gnbd',
                           'kmod-gnbd-xen'
                          ]
        """
        missingpackages = []

        """
        conflictpackages = ['samba3x', 'samba3x-client', 'samba3x-common',
                            'samba3x-swat', 'samba3x-winbind'
                            'postgresql184', 'postgresql84-contrib', 'postgresql84-devel'
                            'postgresql84-docs', 'postgresql84-plperl', 'postgresql84-plpython'
                            'postgresql84-pltcl', 'postgresql84-python', 'postgresql84-server',
                            'postgresql84-tcl','postgresql84-test',
                            'php53', 'php53-bcmath', 'php53-cli', 'php53-dba', 'php53-devel',
                            'php53-gd', 'php53-imap', 'php53-ldap', 'php53-mbstring',
                            'php53-mysql', 'php53-odbc', 'php53-pdo', 'php53-pgsql'
                            'php53-snmp', 'php53-soap', 'php53-xml', 'php53-xmlrpc',
                            'freeradius2', 'freeradius2-ldap', 'freeradius2-utils',
                            'bind97', 'bind97-devel', 'bind97-utils'
                            ]
        """
        conflictpackages = []

        """
        badpackages = ['cisco-vm-grub-config']
        """
        badpackages = []
        
        excludepackages = list(missingpackages)
        excludepackages += list(conflictpackages)
        excludepackages += badpackages


        #debug
        excludepackages = conflictpackages
        #excludegroups = ['cisco-patchbundle-nonreboot']    
        excludegroups = []


        for filename in self.groupmetafiles:
            print "DEBUG: handling %s" % filename

            try:
                print "DEBUG: getting comps from %s" % (self.url + "/" + filename)
            except:
                epdb.st()

            print "DEBUG: getting comps from %s" % (self.url + "/" + filename)
            compdom = parse(urlopen(self.url + "/" + filename))
            for node in compdom.getElementsByTagName('group'):
                #find the id for this group in the dom
                group_id = node.getElementsByTagName('id')[0].childNodes[0].nodeValue

                conarygroupname = "" + group_id.encode('utf-8')
                conarygroupname = conarygroupname.lower()
                conarygroupname = re.sub('\s+','-',conarygroupname)
                conarygroupname = re.sub('/','-',conarygroupname)
                conarygroupname = re.sub('\(','',conarygroupname)
                conarygroupname = re.sub('\)','',conarygroupname)
                grp = yumGroup(conarygroupname)

                print "DEBUG: processing group - %s" % grp.id

                packages = node.getElementsByTagName('packagereq')
                for package in packages:
                    #use the value of the first index for each package name
                    pname = package.childNodes[0].nodeValue
                    print "DEBUG: \tpackage: %s" % pname
                    #add packagename to the yumgroup object
                    if pname.encode('utf-8') not in excludepackages:
                        grp.addpackage(pname.encode('utf-8'))

                #add this group to the list of all groups
                if conarygroupname not in excludegroups:
                    #grpMap.append(grp) 
                    self.groups.append(grp)

            print "DEBUG: comps processed from % s" % self.url

    def findLatestPackages(self):
        self.latestpackages = []
        latesthash = {}
        #for pkg in self.uniquepackages:
        #for pkg in self.uniquepackages:
        for pkg in self.packages:
            key = pkg.name + "-" + pkg.arch
            if not latesthash.has_key(key):
                latesthash[key] = pkg
            else:
                #if key is "kernel-x86_64":
                #    epdb.st()
                #if self.pkgIsOlder(latesthash[key], pkg):
                if self.pkgIsNewer(pkg, latesthash[key]):
                    latesthash[key] = pkg

        for key in latesthash.keys():
            self.latestpackages.append(latesthash[key])
        #epdb.st()

    def pkgIsNewer(self, p, q):
        # p is newer than q ?
        if p.name == q.name:
            if p.version > q.version:
                return True
            elif p.version == q.version:
                if p.release > q.release:
                    return True
                elif p.release == q.release:
                    if p.epoch > q.epoch:
                        return True
                    elif p.epoch == q.epoch:
                        return False
                    else:
                        return False
                else:
                    return False
            else:
                return False
