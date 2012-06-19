class yumPackage(object):
    def __init__(self, name, epoch, version, release, arch, location, repourl):
        self.id = id
        self.name = name
        self.epoch = epoch
        self.version = version
        self.release = release
        self.arch = arch
        self.url = location
        self.repourl = repourl
        #self.md5 = ''
        #self.sha1 = ''
        self.sumtype = ''
        self.sum = ''
        self.packager = ''
        self.upstream = False   #exists upstream?
        self.downstream = False #exists downstream?
        self.matchpercent = 0   #upstream match percentage
        self.dmatchpercent = 0  #downstream match percentage
        self.upstreamtrove = '' #a full trovespec in string format
        self.localtrove = ''    #a full trovespec in string format

