#!/usr/bin/env python

import os
import pysftp

archs = ["rgbmask_results.tar","rgbmask_test_data.tar"]

h = os.getenv('SFTP_H')
u = os.getenv('SFTP_U')
p = os.getenv('SFTP_P')

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

with pysftp.Connection(host=h, username=u, password=p, cnopts=cnopts) as sftp:
    print("Connection succesfully established ... ")

    for f in archs:
        sftp.get(f, f)
        print("Fetched file " + f)
