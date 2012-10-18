rbuild-yumcheckout-plugin
=========================

rbuild-yumcheckout-plugin

```
[rba.admin@devimage Development]$ rbuild help yumcheckout
Usage: rbuild yumcheckout [<options>] --yumurl=<yumrepourl>

Options:

  Command Options:
    --dryrun            pretend to make checkouts
    --factory=FACTORY   choose the default factory for recipes
    --groups            checkout and create group recipes
    --packages          checkout and create the latest NEVRA packages
    --templatedir=TEMPLATEDIR
                        not yet implemented
    --upstreamlabel=UPSTREAMLABEL
    --yumurl=YUMURL     the http url for a yum repository

(Use --verbose to get a full option listing)
```

Example
-------------------------

rbuild yumcheckout --yumurl=http://172.16.176.13/repos/test --packages
