"""
Created on Oct 24, 2012

@author: nigel
"""
import logging
import time
from jcudc24ingesterapi.ingester_platform_api import get_properties

logger = logging.getLogger("dc24_ingester_platform.ingester.sampling")


class Sampler(object):
    """A Sampler is an object that takes a configuration and state
    and uses this to determine whether a dataset is due for a new sample"""
    state = None # Holds the state of the Sampler. This is persisted by the ingester.
    
    def __init__(self, config=None, state=None):
        self.state = {}
        if config != None:
            for param in get_properties(config):
                setattr(self, param, getattr(config, param))
            
    def sample(self, sample_time, dataset):
        """Returns True or False depending on whether a sample should be made"""
        raise NotImplementedError("sample is not implemented for "+str(type(self)))

class NoSuchSampler(Exception):
    """An exception that occurs when there is no sampler available."""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class PeriodicSampler(Sampler):
    rate = None # The rate of the sampler in s
    def sample(self, sampler_time, dataset):
        """Run only if the rate worth of seconds has passed since the last run
        >>> import datetime
        >>> s = PeriodicSampler()
        >>> s.rate = 10
        >>> dt = datetime.datetime.now()
        >>> s.sample(dt, None)
        True
        >>> s.sample(dt, None)
        False
        >>> dt = dt + datetime.timedelta(seconds=11)
        >>> s.sample(dt, None)
        True
        """
        run = False
        now = time.mktime(sampler_time.utctimetuple())
        if "last_run" not in self.state or (float(self.state["last_run"]) + self.rate) < now:
            run = True
        self.state["last_run"] = now
        
        return run

samplers = {"periodic_sampling":PeriodicSampler}

def create_sampler(sampler_config, state):
    """Create the correct configured sampler from the provided dict"""
    if sampler_config.__xmlrpc_class__ not in samplers:
        raise NoSuchSampler("Sampler '%s' not found"%(sampler_config.__xmlrpc_class__))
    return samplers[sampler_config.__xmlrpc_class__](sampler_config, state)
