import unittest, random, threading, time
import ddr_compress.scheduler as sch
from ddr_compress.dbi import Base,File,Observation
from ddr_compress.dbi import DataBaseInterface,jdpol2obsnum
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine,func
import numpy as n,os,sys

class TestDBI(unittest.TestCase):
    def setUp(self):
        """
        create an in memory DB and open a connection to it
        """
        self.dbi = DataBaseInterface(test=True)
        self.session = self.dbi.Session()
        self.jd = 2456785.12345
        self.pol = 'xx'
        self.filename='/data0/zen.2456785.123456.uv'
        self.host = 'pot0'
        self.length = 10/60./24
#    def test_obsnum(self):
#        obsnum = jdpol2obsnum(self.jd,self.pol,self.length)
#        outjd,outpol = obsnum2jdpol(obsnum,self.length)
#        self.assertEqual(self.pol,outpol)
#        self.assertEqual(self.jd,outjd)
    def test_obsnum_increment(self):
        dt = 10/60./24  
        jds = n.arange(0,5)*dt+2456446.1234
        obsnums=[]
        for jd in jds:
            obsnums.append(jdpol2obsnum(jd,'I',dt))
        delta = n.diff(obsnums)
        for d in delta:
            self.assertEqual(d,1)

    def test_add_observation(self):
        """
        use the dbi to create a record.
        basically tests the same as test_Observation_and_file
        but with the dbi wrapper
        """
        obsnum = self.dbi.add_observation(
                    self.jd,self.pol,self.filename,self.host)
        OBS = self.session.query(Observation).filter(Observation.obsnum==obsnum).one()
        self.assertEqual(OBS.julian_date,self.jd)
    def test_add_file(self):
        """
        todo update from code
        """
        #first add the observation
        obsnum = self.dbi.add_observation(self.jd,self.pol,self.filename,self.host)
        #then add a file to it
        filenum = self.dbi.add_file(obsnum,self.host,self.filename+'cRRE')
        #then grab the file record back
        FILE = self.session.query(File).filter(File.filenum==filenum).one()
        #and check that its right
        self.assertEqual(FILE.filename,self.filename+'cRRE')


    def test_add_files(self):
        #first add the observation
        obsnum = self.dbi.add_observation(self.jd,self.pol,self.filename,self.host,self.length)

        #add two subsequent products
        files = ['/data0/zen.2456785.123456.uvc','/data0/zen.2456785.323456.uvcR']
        for filename in files:
            filenum = self.dbi.add_file(obsnum,self.host,filename)
        #how I get all the files for a given obs
        OBS = self.session.query(Observation).filter(Observation.obsnum==obsnum).one()

        self.assertEqual(len(OBS.files),3)#check that we got three files


    def test_add_observations(self):
        #form up the observation list
        obslist =[]
        jds = n.arange(0,10)*self.length+2456446.1234
        pols = ['xx','yy','xy','yx']
        for pol in pols:
            for jdi in xrange(len(jds)):
                obslist.append({'julian_date':jds[jdi],
                                'pol':pol,
                                'host':self.host,
                                'filename':self.filename,
                                'length':self.length})
                if jdi!=0:
                    obslist[-1]['neighbor_low'] = jds[jdi-1]
                if jdi<len(jds[:-1]):
                    obslist[-1]['neighbor_high'] = jds[jdi+1]
        obsnums = self.dbi.add_observations(obslist)
        nobs = self.session.query(func.count(Observation.obsnum)).scalar()
        self.assertEqual(len(obslist),nobs) #did we add observations?
        #did they get the proper neighbor assignments
        for obsnum in obsnums:
            OBS = self.session.query(Observation).filter(Observation.obsnum==obsnum).one()
            #find the original record we put into add_observations and check that the neighbors match
            for obs in obslist:
                if obs['julian_date']==OBS.julian_date:
                    if obs.has_key('neighbor_low'):
                        self.assertEqual(OBS.low_neighbors[0].julian_date,
                                        obs['neighbor_low'])
                    if obs.has_key('neighbor_high'):
                        self.assertEqual(OBS.high_neighbors[0].julian_date,
                                        obs['neighbor_high'])
                    break
                            
                    
                
        

    def test_list_observations(self):
        #form up the observation list
        obslist =[]
        jds = n.arange(0,10)*self.length+2456446.1234
        pols = ['xx','yy','xy','yx']
        for pol in pols:
            for jdi in xrange(len(jds)):
                obslist.append({'julian_date':jds[jdi],
                                'pol':pol,
                                'host':self.host,
                                'filename':self.filename,
                                'length':self.length})
                if jdi!=0:
                    obslist[-1]['neighbor_low'] = jds[jdi-1]
                if jdi<len(jds[:-1]):
                    obslist[-1]['neighbor_high'] = jds[jdi+1]
        obsnums = self.dbi.add_observations(obslist)   
        observations = self.dbi.list_observations()
        self.assertEqual(n.sum(n.array(observations)-n.array(obsnums)),0)


    def test_get_neighbors(self):
        """
        First set up a likely triplet of observations
        """
        #form up the observation list
        obslist =[]
        jds = n.arange(0,10)*self.length+2456446.1234
        pols = ['xx','yy','xy','yx']
        for pol in pols:
            for jdi in xrange(len(jds)):
                obslist.append({'julian_date':jds[jdi],
                                'pol':pol,
                                'host':self.host,
                                'filename':self.filename,
                                'length':self.length})
                if jdi!=0:
                    obslist[-1]['neighbor_low'] = jds[jdi-1]
                if jdi!=(len(jds)-1):
                    obslist[-1]['neighbor_high'] = jds[jdi+1]
        obsnums = self.dbi.add_observations(obslist)
        obsnums.sort()
        i = 5# I have ten time stamps. this guys should have plenty of neighbors
        mytestobsnum = obsnums[i] #choose a middle obs
        neighbors = self.dbi.get_neighbors(mytestobsnum)
        self.assertEqual(len(neighbors),2)
    
        self.assertEqual(neighbors[0],obsnums[i-1])#low
        self.assertEqual(neighbors[1],obsnums[i+1])#high

    def test_set_obs_status(self):
        """
        set the status with the dbi function then check it with 
        under the hood stuff
        """
        #first create an observation in the first place
        obsnum = self.dbi.add_observation(
                    self.jd,self.pol,self.filename,self.host)
        # then set the status to something else
        self.dbi.set_obs_status(obsnum,'UV')
        # get the status back out 
        OBS = self.session.query(Observation).filter(Observation.obsnum==obsnum).one()
        self.assertEqual(OBS.status,'UV')
    def test_get_obs_status(self):
        """
        set the status with the dbi function (cause I tested it with more basic tests already)
        """
        #first create an observation in the first place
        obsnum = self.dbi.add_observation(
                    self.jd,self.pol,self.filename,self.host)
        # then set the status to something else
        self.dbi.set_obs_status(obsnum,'UV')
        #then get the status back
        status = self.dbi.get_obs_status(obsnum)
        self.assertEqual(status,'UV')



    def test_get_input_file(self):
        """
        create an observation
        add the initial file
        get the pot host and path
        """
        #first add the observation
        obsnum = self.dbi.add_observation(
                    self.jd,self.pol,self.filename,self.host)
        #then add a file to it
        host,path,filename = self.dbi.get_input_file(obsnum)
        self.assertEqual(host,self.host)
        self.assertEqual(path,os.path.dirname(self.filename))
        self.assertEqual(filename,os.path.basename(self.filename))
    def test_get_output_location(self):
        """
        create an observation
        add the initial file
        get the pot host and path
        """
        #first add the observation
        obsnum = self.dbi.add_observation(
                    self.jd,self.pol,self.filename,self.host)
        host,path = self.dbi.get_output_location(obsnum)
        self.assertEqual(host,self.host)
        self.assertEqual(path,os.path.dirname(self.filename))
       
    def test_still_path(self):
        """
        """
        obsnum = self.dbi.add_observation(
                    self.jd,self.pol,self.filename,self.host)
        self.dbi.set_obs_still_path(obsnum,'/data/')
        still_path = self.dbi.get_obs_still_path(obsnum)
        self.assertEqual(still_path,'/data/')
    def test_obs_pid(self):
        """
        """
        obsnum = self.dbi.add_observation(
                    self.jd,self.pol,self.filename,self.host)
        self.dbi.set_obs_pid(obsnum,9999)
        pid = self.dbi.get_obs_pid(obsnum)
        self.assertEqual(pid,9999)

if __name__=='__main__':
    unittest.main()
