# -*- coding: utf-8 -*-
from conf import JudgeConf as jcnf
import os

class Diff(object):

    def __init__(self):
        std = None
        ans = None
        stdfile = ''  #std's file path
        ansfile = ''  #submission's answer file path

    def diff(self, stdfile=None, ansfile=None):
        if stdfile:
            self.stdfile = stdfile
        if ansfile:
            self.ansfile = ansfile

        try:
            self.std = open(self.stdfile, 'rU')
            self.ans = open(self.ansfile, 'rU')
        except:
            return jcnf.JUDGE_RES['wa']

        stdsize = os.stat(stdfile).st_size
        anssize = os.stat(ansfile).st_size

        if anssize>jcnf.OLE_THRESHOLD and anssize>stdsize*jcnf.OLE_RATIO:
            return jcnf.JUDGE_RES['ole']

        # Add PE, 2013/12/15
        pe = False
        while True:
            stdl = self.std.readline()
            ansl = self.ans.readline()

            if (not stdl) and (not ansl):
                return jcnf.JUDGE_RES['ac']

            if (not stdl) or (not ansl):
                break

            stdl = stdl.rstrip('\r\n');
            ansl = ansl.rstrip('\r\n');

            no_blank_stdl = stdl.replace(' ', '')
            no_blank_ansl = ansl.replace(' ', '')
            
            if no_blank_stdl == no_blank_ansl and ansl != stdl:
                pe = True
                break

            if (ansl != stdl):
                break

        if pe:
            return jcnf.JUDGE_RES['pe']

        return jcnf.JUDGE_RES['wa']  # TODO should we judge PE?
